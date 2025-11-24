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

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cache import StoreCache
from core.validation import ValidationResult
from core.normalization import normalize_ref_for_cache

import re


@dataclass
class SearchResult:
    """
    Resultado de uma pesquisa numa loja:
    - url: URL final do produto
    - price_text: preço como string visível
    - price_num: preço convertido para float (quando possível)
    - validation: resultado da validação de referência
    """
    url: str
    price_text: str
    price_num: Optional[float]
    validation: ValidationResult

    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "price_text": self.price_text,
            "price_num": self.price_num,
            "validation": self.validation.to_dict() if self.validation else None,
        }


def parse_price_to_float(price_text: str) -> Optional[float]:
    """
    Converte string de preço em float.
    
    Trata múltiplos números na mesma string (ex: preço antigo + preço atual)
    escolhendo sempre o ÚLTIMO número detetado, que na maioria dos sites
    corresponde ao preço atual.
    
    Args:
        price_text: Ex: "€ 365.50", "1.234,56 EUR", "De 200,00€ por 150,00€"
        
    Returns:
        Float ou None
    """
    if not price_text:
        return None
    
    # Remove símbolos de moeda mais comuns
    s = price_text.replace("€", " ").replace("EUR", " ")
    
    # Manter apenas dígitos, vírgula, ponto, espaços e hífen
    s = re.sub(r"[^\d,\.\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    
    # Extrair todos os blocos numéricos
    nums = re.findall(r"\d+[.,]?\d*", s)
    if not nums:
        return None
    
    # Política: usar sempre o último número (normalmente o preço atual)
    raw = nums[-1]
    
    # Detetar formato europeu (vírgula como separador decimal)
    if "," in raw and raw.count(",") == 1 and raw.rfind(",") > raw.rfind("."):
        # Ex: "1.234,56" → vírgula é decimal
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # Formato americano ou sem ambiguidade
        raw = raw.replace(",", "")
    
    try:
        return float(raw)
    except ValueError:
        return None


class BaseScraper(ABC):
    """
    Classe base abstrata para scrapers de lojas.
    """

    def __init__(self, name: str, base_url: str):
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
    def search_product(self, driver: webdriver.Chrome, ref_parts: List[str], ref_raw: str) -> Optional[SearchResult]:
        """
        Implementado em cada scraper concreto.
        
        Args:
            driver: instância de WebDriver
            ref_parts: lista de partes normalizadas da referência
            ref_raw: referência original (para pesquisa, com hífens se necessário)
        
        Returns:
            SearchResult ou None se não encontrar produto válido
        """
        raise NotImplementedError
    
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
                
                from core.validation import ValidationResult, MatchType
                dummy_validation = ValidationResult(
                    is_valid=bool(cached.url),
                    match_type=MatchType.EXACT_MATCH,
                    confidence=cached.confidence,
                    matched_parts=[ref_norm] if cached.url else [],
                    reason="From cache",
                )
                
                if cached.url:
                    return SearchResult(
                        url=cached.url,
                        price_text=cached.price_text or "",
                        price_num=cached.price_num,
                        validation=dummy_validation,
                    )
                else:
                    self.stats["not_found"] += 1
                    return None
        
        # Cache miss - fazer busca real
        self.stats["cache_misses"] += 1
        
        try:
            result = self.search_product(driver, ref_parts, ref_raw)
            
            if result:
                self.stats["found"] += 1
                
                if use_cache:
                    self.cache.put(
                        ref_norm=ref_norm,
                        url=result.url,
                        price_text=result.price_text,
                        price_num=result.price_num,
                        confidence=result.validation.confidence,
                    )
            else:
                self.stats["not_found"] += 1
                
                if use_cache:
                    self.cache.put(
                        ref_norm=ref_norm,
                        url=None,
                        price_text=None,
                        price_num=None,
                        confidence=0.0,
                    )
            
            return result
        
        except Exception as e:
            self.stats["errors"] += 1
            print(f"[ERRO] {self.name}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do scraper."""
        stats = self.stats.copy()
        stats["store"] = self.name
        
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
        """Limpa cache"""
        self.cache.clear()
