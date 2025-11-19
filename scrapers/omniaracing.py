# -*- coding: utf-8 -*-
"""
scrapers/omniaracing.py
Scraper para OmniaRacing.net

Estratégia (do código original que funciona):
1. Preencher campo de busca + Enter
2. Esperar resultados aparecerem
3. Extrair links com href contendo "-p-"
4. Visitar cada link, validar
5. Tentar EN primeiro, depois IT se falhar
"""
import re
from typing import Optional, List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validation import validate_product_match, extract_codes_from_text
from core.selenium_utils import get_page_html, try_accept_cookies
from config import STORE_URLS
from .base import BaseScraper, SearchResult, extract_price_from_html, parse_price_to_float


# Padrões para detectar códigos
CODE_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9\.\-_+]{2,}", re.I)
TITLE_REF_PATTERN = re.compile(r"-\s*([A-Z0-9][A-Z0-9\.\-_+]*)\s*$")
IMG_REF_PATTERN = re.compile(r"/([A-Z0-9][A-Z0-9\.\-_+]{3,})[lm]\.webp$", re.I)


class OmniaRacingScraper(BaseScraper):
    """Scraper para OmniaRacing.net"""
    
    def __init__(self):
        super().__init__(
            name="omniaracing",
            base_url=STORE_URLS["omniaracing"]
        )
    
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str],
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto no OmniaRacing.
        
        Tenta EN primeiro, depois IT se falhar.
        
        Args:
            driver: WebDriver Selenium
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original (para pesquisar com hífens)
            
        Returns:
            SearchResult se encontrado, None caso contrário
        """
        # Usar ref_raw se disponível (mantém hífens), senão ref_parts
        if ref_raw:
            ref_query = ref_raw
        else:
            ref_query = "+".join(ref_parts)
        
        # Tentar em ambos idiomas
        for lang in ["en", "it"]:
            result = self._try_search_in_language(driver, ref_query, ref_parts, lang)
            if result:
                return result
        
        return None
    
    def _try_search_in_language(self, driver: webdriver.Chrome,
                                ref_query: str, ref_parts: List[str],
                                lang: str) -> Optional[SearchResult]:
        """
        Tenta busca num idioma específico.
        
        Args:
            driver: WebDriver
            ref_query: Query de busca (ex: "H085LR1X")
            ref_parts: Partes da ref
            lang: Idioma ("en" ou "it")
            
        Returns:
            SearchResult se encontrado, None caso contrário
        """
        # Abrir página de resultados
        success = self._open_search_results(driver, ref_query, lang)
        if not success:
            return None
        
        # Extrair links de produtos (hrefs com "-p-")
        product_links = self._extract_product_links(driver)
        
        if not product_links:
            return None
        
        # Visitar cada link até encontrar match
        for url in product_links[:14]:  # Máximo 14 como no original
            prod_html = get_page_html(driver, url)
            if not prod_html:
                continue
            
            # Extrair dados
            identifiers = self._extract_identifiers(prod_html)
            price_text = extract_price_from_html(prod_html)
            
            if not price_text:
                continue
            
            # Validar
            soup = BeautifulSoup(prod_html, "lxml")
            full_text = soup.get_text(" ", strip=True)
            
            validation = validate_product_match(
                our_parts=ref_parts,
                page_identifiers=identifiers,
                page_url=url,
                page_text=full_text
            )
            
            if validation.is_valid:
                return SearchResult(
                    url=url,
                    price_text=price_text,
                    price_num=parse_price_to_float(price_text),
                    validation=validation
                )
        
        return None
    
    def _open_search_results(self, driver: webdriver.Chrome,
                            query: str, lang: str) -> bool:
        """
        Abre página de resultados de busca.
        
        Método 1: Preencher campo de busca + Enter
        Método 2 (fallback): URL direta
        
        Args:
            driver: WebDriver
            query: Query de busca
            lang: Idioma
            
        Returns:
            True se conseguiu abrir resultados, False caso contrário
        """
        # Ir para homepage
        driver.get(self.base_url)
        
        # Tentar aceitar cookies
        try_accept_cookies(driver)
        
        import time
        time.sleep(0.5)
        
        # Tentar encontrar campo de busca
        search_box = None
        selectors = [
            (By.CSS_SELECTOR, "input[name='keywords']"),
            (By.CSS_SELECTOR, "input[id*='search']"),
            (By.CSS_SELECTOR, "input[class*='search']"),
            (By.CSS_SELECTOR, "input[type='search']"),
        ]
        
        for by, selector in selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                if search_box.is_displayed():
                    break
            except Exception:
                search_box = None
        
        if search_box:
            # Método 1: Preencher campo + Enter
            try:
                search_box.clear()
                search_box.send_keys(query)
                time.sleep(0.3)
                search_box.send_keys(Keys.ENTER)
                
                # Esperar resultados aparecerem (links com "-p-")
                WebDriverWait(driver, 8).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "a[href*='-p-']")) > 0
                )
                return True
            
            except Exception:
                pass
        
        # Método 2 (fallback): URL direta
        try:
            search_url = f"{self.base_url}index.php?keywords={query}&action=advanced_search&language={lang}"
            driver.get(search_url)
            
            WebDriverWait(driver, 8).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "a[href*='-p-']")) > 0
            )
            return True
        
        except Exception:
            return False
    
    def _extract_product_links(self, driver: webdriver.Chrome) -> List[str]:
        """
        Extrai links de produtos da página de resultados.
        
        Args:
            driver: WebDriver
            
        Returns:
            Lista de URLs (sem duplicados)
        """
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='-p-']")
        
        links = []
        seen = set()
        
        for anchor in anchors:
            try:
                href = anchor.get_attribute("href") or ""
                
                if href and "omniaracing.net" in href and href not in seen:
                    seen.add(href)
                    links.append(href)
            
            except Exception:
                continue
        
        return links
    
    def _extract_identifiers(self, html: str) -> Dict[str, List[str]]:
        """
        Extrai identificadores da página (códigos, SKU, MPN).
        
        Baseado no código original OmniaRacing.
        
        Args:
            html: HTML da página
            
        Returns:
            Dict {"sku": [...], "mpn": [...], "codes": [...]}
        """
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "mpn": [], "codes": []}
        
        # 1. Meta description (procurar bloco de códigos)
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            content = meta_desc.get("content", "")
            # Padrão: procurar blocos separados por vírgula/ponto-vírgula
            pattern = re.compile(r"(?:^|[,;])\s*([A-Z0-9][A-Z0-9\.\-_+]{3,}(?:\s+[A-Z0-9][A-Z0-9\.\-_+]{3,}){0,19})\s*(?:[,;]|$)")
            match = pattern.search(content)
            if match:
                block = match.group(1).strip()
                for token in block.split():
                    from core.normalization import norm_token
                    if len(norm_token(token)) >= 3:
                        ids["codes"].append(token.upper())
        
        # 2. Título (últimas palavras após hífen)
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.string or ""
            match = TITLE_REF_PATTERN.search(title)
            if match:
                from core.normalization import norm_token
                code = match.group(1).strip().upper()
                if len(norm_token(code)) >= 3:
                    ids["codes"].append(code)
        
        # 3. URLs de imagens (padrão específico OmniaRacing)
        for img in soup.find_all("img"):
            src = img.get("src", "")
            match = IMG_REF_PATTERN.search(src)
            if match:
                from core.normalization import norm_token
                code = match.group(1).strip().upper()
                if len(norm_token(code)) >= 3:
                    ids["codes"].append(code)
        
        # 4. JSON-LD (SKU/MPN)
        import json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                
                def scan(obj):
                    if isinstance(obj, dict):
                        if obj.get("@type") == "Product":
                            for key in ["sku", "mpn"]:
                                value = obj.get(key)
                                if isinstance(value, str) and value.strip():
                                    ids[key].append(value.strip().upper())
                        
                        for v in obj.values():
                            scan(v)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            scan(item)
                
                scan(data)
            
            except Exception:
                continue
        
        # 5. Texto completo (códigos gerais)
        full_text = soup.get_text(" ", strip=True).upper()
        ids["codes"].extend(CODE_PATTERN.findall(full_text))
        
        # Remover duplicados
        for key in ids:
            ids[key] = list(dict.fromkeys(ids[key]))
        
        return ids


# ============================================================================
# TESTE
# ============================================================================
if __name__ == "__main__":
    print("=== Teste OmniaRacing Scraper ===\n")
    
    from core.selenium_utils import build_driver
    
    scraper = OmniaRacingScraper()
    driver = build_driver(headless=True)
    
    try:
        print("Testando busca...")
        result = scraper.search_product(driver, ["H085LR1X"])
        
        if result:
            print(f"✅ Encontrado!")
            print(f"   URL: {result.url}")
            print(f"   Preço: {result.price_text}")
        else:
            print("❌ Não encontrado")
        
        print(f"\nStats: {scraper.get_stats()}")
    
    finally:
        driver.quit()
        scraper.save_cache()
