# -*- coding: utf-8 -*-
"""
scrapers/wrs.py
Scraper para WRS.it - VERSÃO CORRIGIDA (Nov 2025)

Usa o sistema SniperFast de search que a WRS implementa.
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
from .base import BaseScraper, SearchResult, parse_price_to_float


CODE_SCAN = re.compile(r"[A-Z0-9][A-Z0-9\.\-_+]{2,}", re.I)


class WRSScraper(BaseScraper):
    """Scraper para WRS.it"""
    
    def __init__(self):
        super().__init__(
            name="wrs",
            base_url=STORE_URLS["wrs"]
        )
    
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str],
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto no WRS.it usando SniperFast search
        
        Args:
            driver: WebDriver Selenium
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original com hífens (para pesquisar!)
            
        Returns:
            SearchResult se encontrado, None caso contrário
        """
        # Usar ref_raw se disponível (mantém hífens), senão ref_parts
        if ref_raw:
            ref_query = ref_raw  # Ex: "P-HF1595" (com hífen original!)
        else:
            ref_query = "+".join(ref_parts)  # Fallback para ref normalizada
        
        print(f"  [WRS] Procurando: {ref_query}")
        
        # Abrir homepage
        driver.get(f"{self.base_url}en/")
        
        # Aceitar cookies
        try_accept_cookies(driver)
        
        import time
        time.sleep(0.5)
        
        # Procurar campo de busca
        search_box = None
        selectors = [
            (By.CSS_SELECTOR, "input[name='s']"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.CSS_SELECTOR, "input.form-search-control"),
        ]
        
        for by, selector in selectors:
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                if search_box.is_displayed():
                    print(f"  [WRS] Campo encontrado: {selector}")
                    break
            except Exception:
                search_box = None
        
        if not search_box:
            print(f"  [WRS] ⚠️  Campo busca não encontrado")
            return None
        
        try:
            # Preencher e fazer pesquisa
            search_box.clear()
            search_box.send_keys(ref_query)
            time.sleep(2.5)  # Esperar SniperFast abrir (aumentado para mais segurança)
            
            # Esperar resultados SniperFast aparecerem
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#sniperfast_results .sniperfast_product"))
                )
                print(f"  [WRS] ✓ SniperFast abriu com resultados")
            except Exception:
                print(f"  [WRS] ⚠️  SniperFast não abriu - sem resultados?")
                return None
            
            # Extrair produtos do SniperFast
            soup = BeautifulSoup(driver.page_source, "lxml")
            products = soup.select(".sniperfast_product")
            
            if not products:
                print(f"  [WRS] ❌ Nenhum produto encontrado no SniperFast")
                return None
            
            print(f"  [WRS] Encontrados {len(products)} produto(s) no SniperFast")
            
            # Processar cada produto
            for idx, product in enumerate(products[:5], 1):
                # Extrair link
                link = product.select_one("a")
                if not link or not link.get("href"):
                    continue
                
                url = link["href"]
                if not url.startswith("http"):
                    url = self.base_url.rstrip("/") + url
                
                print(f"  [WRS] [{idx}] Analisando: {url[:80]}...")
                
                # Carregar página do produto
                prod_html = get_page_html(driver, url)
                if not prod_html:
                    print(f"  [WRS]     ⚠️  Falhou carregar HTML")
                    continue
                
                # Extrair preço e validar
                identifiers = self._extract_identifiers(prod_html)
                price_text = self._extract_price_wrs(prod_html, url)
                
                if not price_text:
                    print(f"  [WRS]     ❌ Sem preço")
                    continue
                
                print(f"  [WRS]     💰 Preço: {price_text}")
                
                # Validar produto
                prod_soup = BeautifulSoup(prod_html, "lxml")
                validation = validate_product_match(
                    our_parts=ref_parts,
                    page_identifiers=identifiers,
                    page_url=url,
                    page_text=prod_soup.get_text(" ", strip=True)
                )
                
                print(f"  [WRS]     {'✅' if validation.is_valid else '❌'} Validação: {validation.confidence:.2f} - {validation.reason}")
                
                if validation.is_valid:
                    return SearchResult(
                        url=url,
                        price_text=price_text,
                        price_num=parse_price_to_float(price_text),
                        validation=validation
                    )
        
        except Exception as e:
            print(f"  [WRS] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"  [WRS] ⚠️  Nenhum match encontrado")
        return None
    
    def _extract_price_wrs(self, html: str, url: str = "") -> Optional[str]:
        """
        Extrai preço da página de produto WRS
        
        Args:
            html: HTML da página
            url: URL da página
            
        Returns:
            Preço formatado ou None
        """
        soup = BeautifulSoup(html, "lxml")
        
        # MÉTODO 1: Meta tag itemprop="price"
        meta = soup.select_one('meta[itemprop="price"]')
        if meta:
            price = meta.get("content")
            if price:
                try:
                    price_float = float(price)
                    return f"€{price_float:.2f}"
                except ValueError:
                    pass
        
        # MÉTODO 2: span.product-price (atributo content)
        price_span = soup.select_one("span.product-price")
        if price_span:
            price = price_span.get("content")
            if price:
                try:
                    price_float = float(price)
                    return f"€{price_float:.2f}"
                except ValueError:
                    pass
            
            # Texto do span
            price_text = price_span.get_text(strip=True)
            if price_text and ("€" in price_text or "EUR" in price_text):
                return price_text
        
        # MÉTODO 3: span.current-price > span.product-price
        current_price = soup.select_one("span.current-price")
        if current_price:
            inner_span = current_price.select_one("span.product-price")
            if inner_span:
                price_text = inner_span.get_text(strip=True)
                if price_text and ("€" in price_text or "EUR" in price_text):
                    return price_text
        
        # MÉTODO 4: JSON-LD
        import json
        for script_tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script_tag.string or "")
                
                def find_price(obj):
                    if isinstance(obj, dict):
                        if obj.get("@type") == "Product":
                            offers = obj.get("offers", {})
                            if isinstance(offers, dict):
                                price = offers.get("price")
                                if price:
                                    return f"€{float(price):.2f}"
                        
                        for v in obj.values():
                            result = find_price(v)
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
                pass
        
        return None
    
    def _extract_identifiers(self, html: str) -> Dict[str, List[str]]:
        """Extrai identificadores da página WRS."""
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "mpn": [], "codes": []}
        
        if soup.title and soup.title.string:
            ids["codes"].extend(CODE_SCAN.findall(soup.title.string.upper()))
        
        for meta in soup.find_all("meta", attrs={"name": re.compile("keywords", re.I)}):
            content = meta.get("content", "")
            ids["codes"].extend(CODE_SCAN.findall(content.upper()))
        
        for meta in soup.find_all("meta", attrs={"property": re.compile("^og:(title|description)$", re.I)}):
            content = meta.get("content", "")
            ids["codes"].extend(CODE_SCAN.findall(content.upper()))
        
        full_text = soup.get_text(" ", strip=True).upper()
        ids["codes"].extend(CODE_SCAN.findall(full_text))
        
        for key in ids:
            ids[key] = list(dict.fromkeys(ids[key]))
        
        return ids