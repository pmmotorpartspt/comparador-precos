# -*- coding: utf-8 -*-
"""
scrapers/base.py
Classe base abstrata para todos os scrapers de lojas.

Cada loja herda BaseScraper e implementa apenas:
- search_product() - como buscar produto naquela loja específica
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from dataclasses import dataclass

from selenium import webdriver

# Imports do core (assumindo estrutura: comparador_v4/core/ e comparador_v4/scrapers/)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cache import StoreCache
from core.validation import ValidationResult


@dataclass
class SearchResult:
    """Resultado de uma busca de produto"""
    url: str                      # URL do produto encontrado
    price_text: str               # Preço formatado (ex: "€ 365.50")
    price_num: Optional[float]    # Preço numérico (para cálculos)
    validation: ValidationResult  # Resultado da validação
    
    @property
    def confidence(self) -> float:
        """Atalho para confiança da validação"""
        return self.validation.confidence
    
    def to_dict(self) -> Dict:
        """Converte para dicionário (para cache e Excel)"""
        return {
            "url": self.url,
            "price_text": self.price_text,
            "price_num": self.price_num,
            "confidence": self.confidence,
        }


class BaseScraper(ABC):
    """
    Classe base para scrapers de lojas.
    
    Providencia:
    - Sistema de cache automático
    - Estatísticas de performance
    - Interface uniforme
    
    Cada loja herda e implementa:
    - search_product() - lógica específica de busca
    """
    
    def __init__(self, name: str, base_url: str):
        """
        Args:
            name: Nome da loja (ex: "wrs", "omniaracing")
            base_url: URL base da loja
        """
        self.name = name
        self.base_url = base_url
        self.cache = StoreCache(name)
        
        # Estatísticas
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "found": 0,
            "not_found": 0,
            "errors": 0,
        }
    
    @abstractmethod
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str], 
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto na loja (IMPLEMENTAR em cada scraper).
        
        Args:
            driver: WebDriver do Selenium (já inicializado)
            ref_parts: Lista de partes normalizadas (ex: ["H085LR1X"])
            ref_raw: Referência original com hífens (ex: "H.085.LR1X" ou "P-HF1595")
            
        Returns:
            SearchResult se encontrado e válido, None se não encontrado
            
        Nota:
            Esta função NÃO deve lidar com cache - isso é automático!
            Só implementar a lógica de busca específica da loja.
            Use ref_raw para pesquisar (mantém hífens) e ref_parts para validar.
        """
        raise NotImplementedError("Cada scraper deve implementar search_product()")
    
    def search_with_cache(self, driver: webdriver.Chrome,
                         ref_norm: str, ref_parts: List[str],
                         ref_raw: str = "",
                         use_cache: bool = True) -> Optional[SearchResult]:
        """
        Wrapper que adiciona cache à busca.
        
        Args:
            driver: WebDriver do Selenium
            ref_norm: Referência normalizada (para cache key)
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original (para pesquisar com hífens)
            use_cache: Se False, ignora cache e força busca
            
        Returns:
            SearchResult se encontrado, None se não
        """
        self.stats["total_searches"] += 1
        
        # Tentar cache primeiro
        if use_cache:
            cached = self.cache.get(ref_norm)
            if cached:
                self.stats["cache_hits"] += 1
                
                # Converter CacheEntry para SearchResult
                # (ValidationResult não é guardado em cache, criar dummy)
                from core.validation import ValidationResult, MatchType
                dummy_validation = ValidationResult(
                    is_valid=bool(cached.url),
                    match_type=MatchType.EXACT_MATCH,
                    confidence=cached.confidence,
                    matched_parts=[ref_norm] if cached.url else [],
                    reason="From cache"
                )
                
                if cached.url:
                    return SearchResult(
                        url=cached.url,
                        price_text=cached.price_text or "",
                        price_num=cached.price_num,
                        validation=dummy_validation
                    )
                else:
                    # Cache hit mas produto não foi encontrado na última vez
                    self.stats["not_found"] += 1
                    return None
        
        # Cache miss - fazer busca real
        self.stats["cache_misses"] += 1
        
        try:
            result = self.search_product(driver, ref_parts, ref_raw)
            
            if result:
                self.stats["found"] += 1
                
                # Guardar em cache
                if use_cache:
                    self.cache.put(
                        ref_norm=ref_norm,
                        url=result.url,
                        price_text=result.price_text,
                        price_num=result.price_num,
                        confidence=result.confidence
                    )
            else:
                self.stats["not_found"] += 1
                
                # Guardar "não encontrado" em cache (evita buscas repetidas)
                if use_cache:
                    self.cache.put(
                        ref_norm=ref_norm,
                        url=None,
                        price_text=None,
                        price_num=None,
                        confidence=0.0
                    )
            
            return result
        
        except Exception as e:
            self.stats["errors"] += 1
            print(f"[ERRO] {self.name}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """
        Retorna estatísticas do scraper.
        
        Returns:
            Dict com estatísticas de performance
        """
        stats = self.stats.copy()
        stats["store"] = self.name
        
        # Calcular taxas
        if stats["total_searches"] > 0:
            stats["hit_rate"] = stats["cache_hits"] / stats["total_searches"]
            stats["success_rate"] = stats["found"] / stats["total_searches"]
        else:
            stats["hit_rate"] = 0.0
            stats["success_rate"] = 0.0
        
        return stats
    
    def save_cache(self):
        """Salva cache no disco"""
        self.cache.save()
    
    def clear_cache(self):
        """Limpa cache (útil para --refresh)"""
        self.cache.clear()
        self.cache.save()
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name})"


# ============================================================================
# HELPER: Extração de Preço (comum a todas lojas)
# ============================================================================

import re
import json
from bs4 import BeautifulSoup

PRICE_REGEX = re.compile(r"(€|\bEUR\b)\s*([\d\.\,]+)")


def extract_price_from_html(html: str) -> Optional[str]:
    """
    Extrai preço de HTML (tenta múltiplos métodos).
    
    Ordem de prioridade:
    1. JSON-LD structured data (Product schema)
    2. Meta tag itemprop="price"
    3. Regex no texto
    
    Args:
        html: HTML da página
        
    Returns:
        Preço formatado (ex: "€ 365.50") ou None
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Método 1: JSON-LD
    for script_tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script_tag.string or "")
            
            def find_price(obj):
                """Recursivamente procura price em objeto JSON"""
                if isinstance(obj, dict):
                    # Product schema
                    if obj.get("@type") == "Product":
                        offers = obj.get("offers", {})
                        if isinstance(offers, dict):
                            price = offers.get("price")
                            currency = offers.get("priceCurrency", "EUR")
                            if price:
                                return f"{currency} {price}"
                    
                    # Recursão em todos valores
                    for value in obj.values():
                        result = find_price(value)
                        if result:
                            return result
                
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_price(item)
                        if result:
                            return result
                
                return None
            
            price = find_price(data)
            if price:
                return price
        
        except Exception:
            continue
    
    # Método 2: Meta itemprop
    meta = soup.find(attrs={"itemprop": "price"})
    if meta:
        content = meta.get("content") or meta.get_text(strip=True)
        if content:
            return f"€ {content}"
    
    # Método 3: Regex no texto
    text = soup.get_text(" ", strip=True)
    match = PRICE_REGEX.search(text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    
    return None


def parse_price_to_float(price_text: str) -> Optional[float]:
    """
    Converte string de preço em float.
    
    Args:
        price_text: Ex: "€ 365.50", "1.234,56 EUR"
        
    Returns:
        Float ou None
    """
    if not price_text:
        return None
    
    # Remove símbolos
    s = price_text.replace("€", " ").replace("EUR", " ")
    s = re.sub(r"[^\d,.\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    
    # Detectar formato europeu (vírgula = decimal)
    if "," in s and s.count(",") == 1 and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    
    try:
        return float(s)
    except ValueError:
        return None
