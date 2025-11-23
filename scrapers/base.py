# -*- coding: utf-8 -*-
"""
scrapers/base.py
Classe base para scrapers de lojas.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, List

from selenium import webdriver

# Imports do core
from core.cache import StoreCache
from core.validation import ValidationResult
from core.normalization import normalize_ref_for_cache


@dataclass
class SearchResult:
    url: str
    price_text: str
    price_num: Optional[float]
    validation: ValidationResult

    @property
    def confidence(self) -> float:
        return self.validation.confidence if self.validation else 0.0

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
        float ou None
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


class BaseScraper:
    """
    Classe base para scrapers de lojas.
    """

    name: str = "BASE"
    base_url: str = ""

    def __init__(self, cache_dir: str = "cache", cache_ttl_hours: int = 24):
        """
        Args:
            cache_dir: diretório base onde será criada a subpasta da loja.
            cache_ttl_hours: TTL padrão para cache de resultados.
        """
        self.cache = StoreCache(self.name, cache_dir, cache_ttl_hours)
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "found": 0,
            "not_found": 0,
            "errors": 0,
        }

    def build_search_url(self, ref_raw: str) -> str:
        """
        Cada loja deve implementar:
            Dado ref_raw (com hífens, etc), devolver URL de pesquisa.
        """
        raise NotImplementedError("Cada scraper deve implementar build_search_url()")

    def search_product(
        self, driver: webdriver.Chrome, ref_parts: List[str], ref_raw: str
    ) -> Optional[SearchResult]:
        """
        Cada loja deve implementar:
            Executar a pesquisa no site, navegar se necessário, e devolver SearchResult.
            Use ref_raw para pesquisar (mantém hífens) e ref_parts para validar.
        """
        raise NotImplementedError("Cada scraper deve implementar search_product()")

    def search_with_cache(
        self,
        driver: webdriver.Chrome,
        ref_norm: str,
        ref_parts: List[str],
        ref_raw: str = "",
        use_cache: bool = True,
    ) -> Optional[SearchResult]:
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
                        confidence=result.confidence,
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
                        confidence=0.0,
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
