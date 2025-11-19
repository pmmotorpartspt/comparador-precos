# -*- coding: utf-8 -*-
"""
core/selenium_utils.py
Utilitários Selenium partilhados: driver, throttling, circuit breaker.
VERSÃO OTIMIZADA PARA STREAMLIT CLOUD
"""
import time
import random
from collections import deque
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    HEADLESS, WINDOW_SIZE, PAGE_LOAD_TIMEOUT, USER_AGENT_LANGS,
    MIN_GAP_SECONDS, PAUSE_RANGE, SLOW_MODE_MULTIPLIER,
    MAX_RETRIES, BACKOFF_BASE,
    CIRCUIT_BREAKER_WINDOW, CIRCUIT_BREAKER_THRESHOLD
)


# ============================================================================
# RATE LIMITING & CIRCUIT BREAKER (globais para toda sessão)
# ============================================================================

_last_navigation_time = 0.0
_min_gap = MIN_GAP_SECONDS
_fail_window = deque(maxlen=CIRCUIT_BREAKER_WINDOW)


def throttle() -> None:
    """
    Rate limiting: garante gap mínimo entre navegações.
    
    Calcula tempo desde última navegação, espera se necessário,
    adiciona pausa aleatória extra.
    """
    global _last_navigation_time
    
    # Calcular quanto tempo passou desde última navegação
    elapsed = time.time() - _last_navigation_time
    need_to_wait = max(0.0, _min_gap - elapsed)
    
    if need_to_wait > 0:
        time.sleep(need_to_wait)
    
    # Pausa aleatória adicional (parece mais humano)
    time.sleep(random.uniform(*PAUSE_RANGE))
    
    _last_navigation_time = time.time()


def set_slow_mode(enable: bool) -> None:
    """
    Ativa/desativa modo lento (gap duplicado).
    
    Args:
        enable: True = modo lento, False = modo normal
    """
    global _min_gap
    _min_gap = MIN_GAP_SECONDS * (SLOW_MODE_MULTIPLIER if enable else 1.0)


def record_navigation_result(success: bool) -> None:
    """
    Regista resultado de navegação para circuit breaker.
    
    Analisa janela deslizante de resultados. Se taxa de falha
    exceder threshold, ativa modo lento automaticamente.
    
    Args:
        success: True se navegação bem-sucedida, False se falhou
    """
    _fail_window.append(0 if success else 1)
    
    # Só analisar se janela tiver dados suficientes
    if len(_fail_window) >= 10:
        fail_rate = sum(_fail_window) / len(_fail_window)
        
        if fail_rate > CIRCUIT_BREAKER_THRESHOLD:
            set_slow_mode(True)
            # Log (opcional)
            # print(f"[CIRCUIT BREAKER] Taxa de falha {fail_rate:.1%} > {CIRCUIT_BREAKER_THRESHOLD:.0%}, modo lento ativado")
        else:
            set_slow_mode(False)


def get_rate_limiting_stats() -> dict:
    """
    Retorna estatísticas de rate limiting.
    
    Returns:
        Dict com min_gap atual e taxa de falha recente
    """
    fail_rate = sum(_fail_window) / len(_fail_window) if _fail_window else 0.0
    
    return {
        "min_gap_seconds": _min_gap,
        "slow_mode": _min_gap > MIN_GAP_SECONDS,
        "recent_fail_rate": fail_rate,
        "window_size": len(_fail_window),
    }


# ============================================================================
# DRIVER MANAGEMENT
# ============================================================================

def build_driver(headless: bool = HEADLESS) -> webdriver.Chrome:
    """
    Cria instância do Chrome WebDriver com configurações otimizadas.
    VERSÃO OTIMIZADA PARA STREAMLIT CLOUD
    
    Args:
        headless: Se True, Chrome invisível. Se False, Chrome visível.
        
    Returns:
        webdriver.Chrome configurado
    """
    opts = Options()
    
    # Headless (sempre True em produção cloud)
    if headless:
        opts.add_argument("--headless=new")
    
    # Performance e stealth
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={WINDOW_SIZE}")
    opts.add_argument(f"--lang={USER_AGENT_LANGS}")
    
    # Anti-detecção
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    
    # ✅ CORRIGIDO: Service com tratamento de erro para cloud
    try:
        # Tentar com ChromeDriverManager (funciona local e alguns clouds)
        service = Service(ChromeDriverManager().install())
    except Exception as e:
        # Fallback: tentar sem especificar service (usa chromedriver do PATH)
        print(f"⚠️  ChromeDriverManager falhou ({e}), usando chromedriver do sistema")
        service = None
    
    # Criar driver
    try:
        if service:
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)
    except Exception as e:
        # Último fallback: tentar com options mínimas
        print(f"⚠️  Tentativa com service falhou, usando configuração básica")
        opts_basic = Options()
        opts_basic.add_argument("--headless=new")
        opts_basic.add_argument("--no-sandbox")
        opts_basic.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=opts_basic)
    
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    # Script anti-detecção
    try:
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    except Exception:
        pass  # Não crítico se falhar
    
    return driver


def safe_get(driver: webdriver.Chrome, url: str, 
             retries: int = MAX_RETRIES) -> bool:
    """
    Navega para URL com retry automático e rate limiting.
    
    Args:
        driver: Instância do WebDriver
        url: URL para carregar
        retries: Número de tentativas (padrão: MAX_RETRIES)
        
    Returns:
        True se carregou com sucesso, False se todas tentativas falharam
    """
    for attempt in range(retries):
        try:
            # Rate limiting
            throttle()
            
            # Navegar
            driver.get(url)
            
            # Esperar página completamente carregada
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Pequena pausa extra (garante JS assíncronos)
            time.sleep(0.4)
            
            # Sucesso!
            record_navigation_result(True)
            return True
        
        except Exception as e:
            # Falhou
            record_navigation_result(False)
            
            # Se não é última tentativa, fazer backoff exponencial
            if attempt < retries - 1:
                wait_time = (BACKOFF_BASE ** attempt) + random.random()
                time.sleep(wait_time)
            # else: última tentativa falhou, retornar False
    
    # Todas tentativas falharam
    return False


def get_page_html(driver: webdriver.Chrome, url: str) -> Optional[str]:
    """
    Wrapper conveniente: navega e retorna HTML ou None.
    
    Args:
        driver: Instância do WebDriver
        url: URL para carregar
        
    Returns:
        HTML da página como string, ou None se falhou
    """
    success = safe_get(driver, url)
    
    if success:
        return driver.page_source
    else:
        return None


# ============================================================================
# COOKIES & POPUPS
# ============================================================================

def try_accept_cookies(driver: webdriver.Chrome, timeout: int = 3) -> bool:
    """
    Tenta clicar em botão de aceitar cookies (genérico).
    
    Procura por seletores comuns de botões de cookies.
    Não faz raise de exceção se não encontrar.
    
    Args:
        driver: Instância do WebDriver
        timeout: Segundos para esperar (padrão: 3)
        
    Returns:
        True se clicou, False se não encontrou
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    
    # Seletores comuns de botões de cookies
    selectors = [
        (By.ID, "onetrust-accept-btn-handler"),
        (By.CSS_SELECTOR, "button[class*='accept-cookie']"),
        (By.CSS_SELECTOR, "button[class*='cookie-accept']"),
        (By.CSS_SELECTOR, "a[class*='accept-cookie']"),
        (By.XPATH, "//button[contains(., 'Aceitar')]"),
        (By.XPATH, "//button[contains(., 'Accept')]"),
        (By.XPATH, "//button[contains(., 'OK')]"),
    ]
    
    for by, selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            element.click()
            time.sleep(0.5)  # Dar tempo para popup fechar
            return True
        except Exception:
            continue
    
    return False


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Selenium Utils ===\n")
    
    # Testar criação de driver
    print("Criando driver...")
    driver = build_driver(headless=True)
    print("✅ Driver criado")
    
    # Testar navegação
    print("\nTestando navegação...")
    test_url = "https://www.google.com"
    success = safe_get(driver, test_url)
    
    if success:
        print(f"✅ Navegação bem-sucedida para {test_url}")
        print(f"   Título: {driver.title}")
    else:
        print(f"❌ Falhou ao navegar para {test_url}")
    
    # Estatísticas
    stats = get_rate_limiting_stats()
    print(f"\nEstatísticas de rate limiting:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Fechar driver
    driver.quit()
    print("\n✅ Driver fechado")
