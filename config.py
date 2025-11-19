# -*- coding: utf-8 -*-
"""
Comparador v4 - Configurações Centralizadas
Todos os paths, timeouts e constantes num só lugar
"""
from pathlib import Path

# ============================================================================
# PATHS - Alterar aqui se mudares de pasta
# ============================================================================
BASE_DIR = Path(r"C:\PMprecos")
FEED_PATH = BASE_DIR / "feed.xml"
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

# Garantir que pastas existem
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Excel de saída
EXCEL_OUTPUT = OUTPUT_DIR / "comparador_todas_lojas.xlsx"

# ============================================================================
# SELENIUM - Configurações do Chrome
# ============================================================================
HEADLESS = True  # Chrome invisível (True) ou visível (False)
WINDOW_SIZE = "1400,950"
PAGE_LOAD_TIMEOUT = 35  # segundos
USER_AGENT_LANGS = "en,it,pt"

# ============================================================================
# RATE LIMITING - Proteção anti-bloqueio
# ============================================================================
MIN_GAP_SECONDS = 7.5  # Tempo mínimo entre navegações
PAUSE_RANGE = (0.7, 1.5)  # Pausa aleatória adicional (min, max)
SLOW_MODE_MULTIPLIER = 2.0  # Quanto abrandar em modo lento

# Retry de navegação
MAX_RETRIES = 2  # Tentativas de carregar página
BACKOFF_BASE = 2  # Base para exponential backoff

# ============================================================================
# CIRCUIT BREAKER - Detecção de falhas
# ============================================================================
CIRCUIT_BREAKER_WINDOW = 20  # Janela de análise (últimos N pedidos)
CIRCUIT_BREAKER_THRESHOLD = 0.30  # 30% de falhas = ativar modo lento

# ============================================================================
# CACHE - Persistência em disco com TTL (Time To Live)
# ============================================================================
CACHE_ENABLED = True  # Pode ser desativado via CLI

# TTL (Time To Live) - Expiração do cache
# Produtos ENCONTRADOS: guardados 10 dias (preços mudam em campanhas)
# Produtos NÃO ENCONTRADOS: guardados 4 dias (stock novo pode chegar)
CACHE_TTL_FOUND_DAYS = 10       # Cache para produtos encontrados (em dias)
CACHE_TTL_NOT_FOUND_DAYS = 4    # Cache para produtos não encontrados (em dias)

# ============================================================================
# VALIDAÇÃO - Limites por tipo de referência
# ============================================================================
MAX_URLS_SIMPLE = 3  # Máximo de URLs a visitar para ref simples (X)
MAX_URLS_COMPOSITE = 4  # Máximo de URLs a visitar para ref composta (X+Y)

# ============================================================================
# LOJAS - URLs Base
# ============================================================================
STORE_URLS = {
    "wrs": "https://www.wrs.it/",
    "omniaracing": "https://www.omniaracing.net/",
    "genialmotor": "https://www.genialmotor.it/",
    "jbsmotos": "https://jbs-motos.pt/",
    "mmgracingstore": "https://mmgracingstore.com/",
    "emmoto": "https://em-moto.com/",
    "bicaracing": "https://www.bicaracing.com/",
    "unobike": "https://www.unobike.com/",
}

# ============================================================================
# LOGGING - Níveis de verbosidade
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
SHOW_PROGRESS_BAR = True  # Barra de progresso visual
