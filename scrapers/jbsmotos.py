# -*- coding: utf-8 -*-
"""
scrapers/jbsmotos.py
Scraper para JBS-Motos.pt

Site PrestaShop com busca simples.
Estratégia:
1. Abrir página de pesquisa direta com query
2. Extrair produtos da página de resultados (class="product-miniature")
3. Visitar cada produto, verificar referência
4. Validar match e extrair preço
"""
import re
from typing import Optional, List, Dict

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
from .base import BaseScraper, SearchResult, extract_price_from_html, parse_price_to_float


class JBSMotosScraper(BaseScraper):
    """Scraper para JBS-Motos.pt"""
    
    def __init__(self):
        super().__init__(
            name="jbsmotos",
            base_url=STORE_URLS["jbsmotos"]
        )
    
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str],
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto no JBS Motos.
        
        Args:
            driver: WebDriver Selenium
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original (para pesquisar com hífens)
            
        Returns:
            SearchResult se encontrado, None caso contrário
        """
        # Usar ref_raw se disponível (mantém hífens), senão juntar ref_parts
        if ref_raw:
            ref_query = ref_raw
        else:
            ref_query = "".join(ref_parts)
        
        print(f"[JBS] Procurando: {ref_query}")
        
        # Abrir página de resultados
        success = self._open_search_results(driver, ref_query)
        if not success:
            print(f"[JBS] ❌ Falha ao abrir página de resultados")
            return None
        
        # Extrair links de produtos
        product_links = self._extract_product_links(driver)
        
        if not product_links:
            print(f"[JBS] ⚠️  Nenhum produto encontrado")
            return None
        
        print(f"[JBS] Encontrados {len(product_links)} produto(s)")
        
        # Visitar cada link até encontrar match válido
        for idx, url in enumerate(product_links[:10], 1):  # Máximo 10
            print(f"[JBS] [{idx}] Analisando: {url}")
            
            prod_html = get_page_html(driver, url)
            if not prod_html:
                print(f"[JBS]     ❌ Falha ao carregar página")
                continue
            
            # Extrair referência da página
            page_ref = self._extract_reference(prod_html)
            
            # Extrair preço
            price_text = extract_price_from_html(prod_html)
            
            if not price_text:
                print(f"[JBS]     ⚠️  Preço não encontrado")
                continue
            
            print(f"[JBS]     💰 Preço: {price_text}")
            
            # Extrair identificadores para validação
            identifiers = self._extract_identifiers(prod_html, page_ref)
            
            # Validar match
            soup = BeautifulSoup(prod_html, "lxml")
            full_text = soup.get_text(" ", strip=True)
            
            validation = validate_product_match(
                our_parts=ref_parts,
                page_identifiers=identifiers,
                page_url=url,
                page_text=full_text
            )
            
            print(f"[JBS]     {'✅' if validation.is_valid else '❌'} Validação: {validation.confidence:.2f} - {validation.match_type}")
            
            if validation.is_valid:
                return SearchResult(
                    url=url,
                    price_text=price_text,
                    price_num=parse_price_to_float(price_text),
                    validation=validation
                )
        
        print(f"[JBS] ❌ Nenhum produto válido encontrado")
        return None
    
    def _open_search_results(self, driver: webdriver.Chrome, query: str) -> bool:
        """
        Abre página de resultados de busca.
        
        URL pattern: https://jbs-motos.pt/pt/search?controller=search&s=P-HF1595
        
        Args:
            driver: WebDriver
            query: Query de busca
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # URL de busca (língua portuguesa)
            search_url = f"{self.base_url}pt/search?controller=search&s={query}"
            driver.get(search_url)
            
            # Aceitar cookies se aparecerem
            try_accept_cookies(driver)
            
            # Esperar pela página carregar (produtos ou mensagem "sem resultados")
            WebDriverWait(driver, 10).until(
                lambda d: (
                    len(d.find_elements(By.CSS_SELECTOR, ".product-miniature")) > 0 or
                    "Resultados da pesquisa" in d.page_source
                )
            )
            
            return True
        
        except Exception as e:
            print(f"[JBS] ❌ Erro ao abrir resultados: {e}")
            return False
    
    def _extract_product_links(self, driver: webdriver.Chrome) -> List[str]:
        """
        Extrai links de produtos da página de resultados.
        
        Produtos no JBS Motos têm:
        - Classe "product-miniature"
        - Link dentro de <h3><a>
        
        Args:
            driver: WebDriver
            
        Returns:
            Lista de URLs (sem duplicados)
        """
        links = []
        seen = set()
        
        try:
            # Encontrar todos os produtos
            products = driver.find_elements(By.CSS_SELECTOR, ".product-miniature")
            
            for product in products:
                try:
                    # Procurar link dentro do título (h3 > a)
                    link_elem = product.find_element(By.CSS_SELECTOR, "h3 a")
                    href = link_elem.get_attribute("href")
                    
                    if href and href not in seen:
                        seen.add(href)
                        links.append(href)
                
                except Exception:
                    continue
        
        except Exception as e:
            print(f"[JBS] ⚠️  Erro ao extrair links: {e}")
        
        return links
    
    def _extract_reference(self, html: str) -> Optional[str]:
        """
        Extrai referência da página do produto.
        
        No JBS Motos, a referência está em:
        <span itemprop="sku">P-HF1595</span>
        
        Args:
            html: HTML da página
            
        Returns:
            Referência ou None
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Procurar por itemprop="sku"
        sku_tag = soup.find(attrs={"itemprop": "sku"})
        if sku_tag:
            ref = sku_tag.get_text(strip=True)
            if ref:
                return ref.upper()
        
        return None
    
    def _extract_identifiers(self, html: str, page_ref: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Extrai identificadores da página (códigos, SKU, referência).
        
        Args:
            html: HTML da página
            page_ref: Referência extraída da página (se disponível)
            
        Returns:
            Dict {"sku": [...], "codes": [...]}
        """
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "codes": []}
        
        # 1. Referência da página (prioritário)
        if page_ref:
            ids["sku"].append(page_ref)
            ids["codes"].append(page_ref)
        
        # 2. Título da página
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Extrair códigos alfanuméricos do título
            pattern = re.compile(r"\b([A-Z0-9][\w\-\.+]{2,})\b", re.I)
            for match in pattern.finditer(title):
                code = match.group(1).upper()
                from core.normalization import norm_token
                if len(norm_token(code)) >= 3:
                    ids["codes"].append(code)
        
        # 3. Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            content = meta_desc.get("content", "")
            pattern = re.compile(r"\b([A-Z0-9][\w\-\.+]{3,})\b", re.I)
            for match in pattern.finditer(content):
                code = match.group(1).upper()
                from core.normalization import norm_token
                if len(norm_token(code)) >= 3:
                    ids["codes"].append(code)
        
        # 4. JSON-LD (se existir)
        import json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                
                def scan(obj):
                    if isinstance(obj, dict):
                        if obj.get("@type") == "Product":
                            # SKU/MPN
                            for key in ["sku", "mpn"]:
                                value = obj.get(key)
                                if value and isinstance(value, str):
                                    ids["sku"].append(value.upper())
                                    ids["codes"].append(value.upper())
                        
                        # Recursão
                        for value in obj.values():
                            scan(value)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            scan(item)
                
                scan(data)
            
            except Exception:
                continue
        
        return ids
