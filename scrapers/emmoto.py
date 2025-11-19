# -*- coding: utf-8 -*-
"""
scrapers/emmoto.py
Scraper para EM Moto (em-moto.com) - Nov 2025

Características:
- Site Magento com pesquisa direta por URL
- Estrutura de produtos bem definida
- Preços em data-price-amount
"""
import re
from typing import Optional, List, Dict
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validation import validate_product_match
from core.selenium_utils import get_page_html, try_accept_cookies
from config import STORE_URLS
from .base import BaseScraper, SearchResult, parse_price_to_float


CODE_SCAN = re.compile(r"[A-Z0-9][A-Z0-9\.\-_+]{2,}", re.I)


class EMMotoScraper(BaseScraper):
    """Scraper para EM Moto"""
    
    def __init__(self):
        super().__init__(
            name="emmoto",
            base_url=STORE_URLS.get("emmoto", "https://em-moto.com/")
        )
    
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str],
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto na EM Moto
        
        Estratégia:
        1. Vai direto para URL de pesquisa com a referência
        2. Extrai lista de produtos dos resultados
        3. Valida cada produto contra a referência
        4. Retorna o primeiro match válido
        
        Args:
            driver: WebDriver Selenium
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original (para pesquisar)
            
        Returns:
            SearchResult se encontrado, None caso contrário
        """
        # Usar ref_raw se disponível, senão juntar ref_parts
        if ref_raw:
            ref_query = ref_raw
        else:
            ref_query = "+".join(ref_parts)
        
        print(f"  [EM Moto] Procurando: {ref_query}")
        
        # Construir URL de pesquisa
        search_url = f"{self.base_url}en/catalogsearch/result/?q={quote_plus(ref_query)}"
        
        try:
            # Ir direto para página de resultados
            driver.get(search_url)
            
            # Aceitar cookies se aparecerem
            try_accept_cookies(driver)
            
            import time
            time.sleep(1.5)  # Esperar página carregar
            
            # Verificar se há resultados
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".products.list.items.product-items"))
                )
                print(f"  [EM Moto] ✓ Página de resultados carregada")
            except Exception:
                print(f"  [EM Moto] ❌ Sem resultados para esta pesquisa")
                return None
            
            # Extrair HTML
            soup = BeautifulSoup(driver.page_source, "lxml")
            
            # Procurar produtos
            products = soup.select("li.item.product.product-item")
            
            if not products:
                print(f"  [EM Moto] ❌ Nenhum produto encontrado")
                return None
            
            print(f"  [EM Moto] Encontrados {len(products)} produto(s)")
            
            # Processar cada produto
            for idx, product in enumerate(products[:5], 1):  # Limitar a 5 primeiros
                try:
                    # Extrair URL do produto
                    link = product.select_one("a.product-item-link")
                    if not link or not link.get("href"):
                        continue
                    
                    url = link["href"]
                    if not url.startswith("http"):
                        url = self.base_url.rstrip("/") + url
                    
                    # Extrair nome do produto (para debug)
                    product_name = link.get_text(strip=True)
                    print(f"  [EM Moto] [{idx}] {product_name[:60]}...")
                    print(f"  [EM Moto]       URL: {url[:80]}...")
                    
                    # Extrair preço da listagem (mais rápido)
                    price_text = self._extract_price_from_listing(product)
                    
                    if not price_text:
                        # Se não encontrou na listagem, tentar na página do produto
                        print(f"  [EM Moto]       Carregando página do produto...")
                        prod_html = get_page_html(driver, url)
                        if prod_html:
                            price_text = self._extract_price_from_product_page(prod_html)
                    
                    if not price_text:
                        print(f"  [EM Moto]       ❌ Sem preço")
                        continue
                    
                    print(f"  [EM Moto]       💰 Preço: {price_text}")
                    
                    # Extrair identificadores da página do produto (para validação robusta)
                    prod_html = get_page_html(driver, url)
                    if not prod_html:
                        print(f"  [EM Moto]       ⚠️  Falhou carregar página")
                        continue
                    
                    identifiers = self._extract_identifiers(prod_html)
                    prod_soup = BeautifulSoup(prod_html, "lxml")
                    
                    # Validar produto
                    validation = validate_product_match(
                        our_parts=ref_parts,
                        page_identifiers=identifiers,
                        page_url=url,
                        page_text=prod_soup.get_text(" ", strip=True)
                    )
                    
                    print(f"  [EM Moto]       {'✅' if validation.is_valid else '❌'} Validação: {validation.confidence:.2f} - {validation.reason}")
                    
                    if validation.is_valid:
                        return SearchResult(
                            url=url,
                            price_text=price_text,
                            price_num=parse_price_to_float(price_text),
                            validation=validation
                        )
                
                except Exception as e:
                    print(f"  [EM Moto]       ⚠️  Erro ao processar produto: {e}")
                    continue
            
            print(f"  [EM Moto] ⚠️  Nenhum match válido encontrado")
            return None
        
        except Exception as e:
            print(f"  [EM Moto] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_price_from_listing(self, product_element) -> Optional[str]:
        """
        Extrai preço da listagem de produtos (mais rápido)
        
        Args:
            product_element: Elemento BeautifulSoup do produto
            
        Returns:
            Preço formatado ou None
        """
        # MÉTODO 1: data-price-amount no span.price-wrapper
        price_wrapper = product_element.select_one("span.price-wrapper[data-price-amount]")
        if price_wrapper:
            price_amount = price_wrapper.get("data-price-amount")
            if price_amount:
                try:
                    price_float = float(price_amount)
                    return f"€{price_float:.2f}"
                except ValueError:
                    pass
        
        # MÉTODO 2: Texto do span.price dentro de special-price (preço promocional)
        special_price = product_element.select_one("span.special-price span.price")
        if special_price:
            price_text = special_price.get_text(strip=True)
            if price_text and "€" in price_text:
                return price_text
        
        # MÉTODO 3: Preço regular (se não há promocional)
        regular_price = product_element.select_one("span.price-wrapper span.price")
        if regular_price:
            price_text = regular_price.get_text(strip=True)
            if price_text and "€" in price_text:
                return price_text
        
        return None
    
    def _extract_price_from_product_page(self, html: str) -> Optional[str]:
        """
        Extrai preço da página individual do produto
        
        Args:
            html: HTML da página do produto
            
        Returns:
            Preço formatado ou None
        """
        soup = BeautifulSoup(html, "lxml")
        
        # MÉTODO 1: Meta tag product:price:amount (Open Graph)
        meta_price = soup.select_one('meta[property="product:price:amount"]')
        if meta_price:
            price = meta_price.get("content")
            if price:
                try:
                    price_float = float(price)
                    return f"€{price_float:.2f}"
                except ValueError:
                    pass
        
        # MÉTODO 2: data-price-amount no price-wrapper
        price_wrapper = soup.select_one("span.price-wrapper[data-price-amount]")
        if price_wrapper:
            price_amount = price_wrapper.get("data-price-amount")
            if price_amount:
                try:
                    price_float = float(price_amount)
                    return f"€{price_float:.2f}"
                except ValueError:
                    pass
        
        # MÉTODO 3: Texto do preço especial (se houver promoção)
        special_price = soup.select_one("span.special-price span.price")
        if special_price:
            price_text = special_price.get_text(strip=True)
            if price_text and "€" in price_text:
                return price_text
        
        # MÉTODO 4: Preço normal
        normal_price = soup.select_one(".price-box span.price")
        if normal_price:
            price_text = normal_price.get_text(strip=True)
            if price_text and "€" in price_text:
                return price_text
        
        # MÉTODO 5: JSON-LD (fallback)
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
        """
        Extrai identificadores da página para validação
        
        Args:
            html: HTML da página
            
        Returns:
            Dicionário com listas de identificadores (sku, mpn, codes)
        """
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "mpn": [], "codes": []}
        
        # Extrair do título
        if soup.title and soup.title.string:
            ids["codes"].extend(CODE_SCAN.findall(soup.title.string.upper()))
        
        # Extrair de meta keywords
        for meta in soup.find_all("meta", attrs={"name": re.compile("keywords", re.I)}):
            content = meta.get("content", "")
            ids["codes"].extend(CODE_SCAN.findall(content.upper()))
        
        # Extrair de Open Graph
        for meta in soup.find_all("meta", attrs={"property": re.compile("^og:(title|description)$", re.I)}):
            content = meta.get("content", "")
            ids["codes"].extend(CODE_SCAN.findall(content.upper()))
        
        # Procurar data-product-sku (específico Magento)
        for element in soup.find_all(attrs={"data-product-sku": True}):
            sku = element.get("data-product-sku", "").strip().upper()
            if sku:
                ids["sku"].append(sku)
                ids["codes"].append(sku)
        
        # Extrair do texto da página (breadcrumbs, descrições, etc)
        full_text = soup.get_text(" ", strip=True).upper()
        ids["codes"].extend(CODE_SCAN.findall(full_text))
        
        # Remover duplicados mantendo ordem
        for key in ids:
            ids[key] = list(dict.fromkeys(ids[key]))
        
        return ids
