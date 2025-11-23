# -*- coding: utf-8 -*-
"""
scrapers/genialmotor.py
Scraper para GenialMotor.it

Estratégia (do código original que funciona):
1. Busca direta: /en/search?s=REF
2. Se página de busca já é produto → valida
3. Senão: extrai links candidatos, visita até 3-4 URLs
4. Para no primeiro match válido

CORREÇÃO v4.2: Fallback para pegar todos os links de produtos quando
não encontra candidatos específicos (ex: SPM04D onde a ref só aparece num badge)
"""
import re
from typing import Optional, List, Dict
from bs4 import BeautifulSoup

from selenium import webdriver

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validation import validate_product_match, extract_codes_from_text
from core.selenium_utils import get_page_html
from config import STORE_URLS, MAX_URLS_SIMPLE, MAX_URLS_COMPOSITE
from .base import BaseScraper, SearchResult, extract_price_from_html, parse_price_to_float


# Padrão para extrair códigos alfanuméricos
TOKEN_RE = re.compile(r"[A-Z0-9][A-Z0-9\.\-_+]{2,}", re.I)


class GenialMotorScraper(BaseScraper):
    """Scraper para GenialMotor.it"""
    
    def __init__(self):
        super().__init__(
            name="genialmotor",
            base_url=STORE_URLS["genialmotor"]
        )
    
    def search_product(self, driver: webdriver.Chrome, 
                      ref_parts: List[str],
                      ref_raw: str = "") -> Optional[SearchResult]:
        """
        Busca produto no GenialMotor.
        
        Args:
            driver: WebDriver Selenium
            ref_parts: Partes normalizadas (para validação)
            ref_raw: Referência original (para pesquisar com hífens)
            
        Returns:
            SearchResult se encontrado e válido, None caso contrário
        """
        # Usar ref_raw se disponível (mantém hífens), senão ref_parts
        if ref_raw:
            ref_query = ref_raw
        else:
            ref_query = "+".join(ref_parts)
        
        search_url = f"{self.base_url}en/search?s={ref_query}"
        
        # Carregar página de busca
        html = get_page_html(driver, search_url)
        if not html:
            return None
        
        # Extrair identificadores e preço da página atual
        identifiers = self._extract_identifiers(html)
        price_text = extract_price_from_html(html)
        
        # VALIDAR: às vezes a busca redireciona direto para produto
        validation = validate_product_match(
            our_parts=ref_parts,
            page_identifiers=identifiers,
            page_url=driver.current_url,
            page_text=BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        )
        
        if validation.is_valid and price_text:
            # Match direto na página de busca!
            return SearchResult(
                url=driver.current_url,
                price_text=price_text,
                price_num=parse_price_to_float(price_text),
                validation=validation
            )
        
        # Não é match direto - extrair links candidatos
        candidate_urls = self._extract_candidate_urls(html, ref_parts, driver.current_url)
        
        # Limitar número de URLs a visitar
        max_urls = MAX_URLS_COMPOSITE if len(ref_parts) > 1 else MAX_URLS_SIMPLE
        candidate_urls = candidate_urls[:max_urls]
        
        # Visitar cada candidato até encontrar match
        for url in candidate_urls:
            prod_html = get_page_html(driver, url)
            if not prod_html:
                continue
            
            # Extrair dados da página de produto
            prod_identifiers = self._extract_identifiers(prod_html)
            prod_price = extract_price_from_html(prod_html)
            
            if not prod_price:
                continue
            
            # Validar
            prod_validation = validate_product_match(
                our_parts=ref_parts,
                page_identifiers=prod_identifiers,
                page_url=url,
                page_text=BeautifulSoup(prod_html, "lxml").get_text(" ", strip=True)
            )
            
            if prod_validation.is_valid:
                # Match encontrado!
                return SearchResult(
                    url=url,
                    price_text=prod_price,
                    price_num=parse_price_to_float(prod_price),
                    validation=prod_validation
                )
        
        # Nenhum match encontrado
        return None
    
    def _extract_identifiers(self, html: str) -> Dict[str, List[str]]:
        """
        Extrai identificadores estruturados da página (SKU, MPN, códigos).
        
        Baseado no código original GenialMotor que funciona.
        
        Args:
            html: HTML da página
            
        Returns:
            Dict {"sku": [...], "mpn": [...], "codes": [...]}
        """
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "mpn": [], "codes": []}
        
        # 1. JSON-LD structured data
        import json
        for script_tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script_tag.string or "")
                
                def scan_json(obj):
                    """Recursivamente procura SKU/MPN em JSON"""
                    if isinstance(obj, dict):
                        # Product schema
                        if obj.get("@type") == "Product":
                            for key in ["sku", "mpn", "gtin13", "gtin14", "productID"]:
                                value = obj.get(key)
                                if isinstance(value, str) and value.strip():
                                    target = "sku" if key == "sku" else "mpn" if key == "mpn" else "codes"
                                    ids[target].append(value.strip().upper())
                        
                        # Recursão
                        for v in obj.values():
                            scan_json(v)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            scan_json(item)
                
                scan_json(data)
            
            except Exception:
                continue
        
        # 2. Meta tags itemprop
        for attr, target in [("sku", "sku"), ("mpn", "mpn")]:
            tag = soup.find(attrs={"itemprop": attr})
            if tag:
                value = tag.get("content") or tag.get_text(strip=True)
                if value:
                    ids[target].append(value.strip().upper())
        
        # 3. Título H1
        h1 = soup.find("h1")
        if h1:
            ids["codes"].extend(TOKEN_RE.findall(h1.get_text(" ", strip=True).upper()))
        
        # 4. Todo o texto da página
        full_text = soup.get_text(" ", strip=True).upper()
        ids["codes"].extend(TOKEN_RE.findall(full_text))
        
        # 5. URLs de imagens
        for img in soup.find_all("img"):
            src = (img.get("src") or "").upper()
            ids["codes"].extend(TOKEN_RE.findall(src))
        
        # Remover duplicados (manter ordem)
        for key in ids:
            seen = set()
            unique = []
            for code in ids[key]:
                if code not in seen:
                    seen.add(code)
                    unique.append(code)
            ids[key] = unique
        
        return ids
    
    def _extract_candidate_urls(self, html: str, ref_parts: List[str], 
                               current_url: str) -> List[str]:
        """
        Extrai URLs candidatos da página de resultados.
        
        CORREÇÃO v4.2: Se não encontrar candidatos específicos (ref no link/URL),
        faz fallback para pegar TODOS os links de produtos e deixa a validação decidir.
        
        Args:
            html: HTML da página de busca
            ref_parts: Partes da referência procurada
            current_url: URL atual (para resolver relativos)
            
        Returns:
            Lista de URLs candidatos (sem duplicados)
        """
        soup = BeautifulSoup(html, "lxml")
        candidates = []
        
        # MÉTODO 1: Procurar links que mencionem as partes da ref (método original)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            
            # Converter para URL absoluto
            if href.startswith("http"):
                url = href
            else:
                url = self.base_url.rstrip("/") + "/" + href.lstrip("/")
            
            # Filtrar URLs irrelevantes
            if any(x in url.lower() for x in ["/cart", "/login", "/wishlist", "/compare", "/search"]):
                continue
            
            # Verificar se URL ou texto do link contém partes da ref
            link_text = (a.get_text(" ", strip=True) or "").upper()
            url_upper = url.upper()
            
            from core.normalization import norm_token
            
            if len(ref_parts) == 1:
                # Ref simples: procurar a parte
                target = norm_token(ref_parts[0])
                if target in norm_token(link_text) or target in norm_token(url_upper):
                    candidates.append(url)
            
            else:
                # Ref composta: procurar qualquer combinação
                # Ex: "H085LR1X+ABC123" ou "ABC123+H085LR1X"
                part_combos = [
                    "+".join(ref_parts),
                    "+".join(reversed(ref_parts))
                ]
                
                for combo in part_combos:
                    if norm_token(combo) in norm_token(link_text) or \
                       norm_token(combo) in norm_token(url_upper):
                        candidates.append(url)
                        break
        
        # MÉTODO 2 (FALLBACK): Se não encontrou candidatos, pegar TODOS os links de produtos
        if not candidates:
            # Procurar padrões típicos de URLs de produtos do GenialMotor
            product_patterns = [
                "/product",
                "/p-",
                "/item",
                "-p.html",
                ".html"
            ]
            
            for a in soup.find_all("a", href=True):
                href = a["href"]
                
                # Converter para URL absoluto
                if href.startswith("http"):
                    url = href
                else:
                    url = self.base_url.rstrip("/") + "/" + href.lstrip("/")
                
                # Filtrar URLs irrelevantes
                if any(x in url.lower() for x in ["/cart", "/login", "/wishlist", "/compare", "/search", "/category", "/brand"]):
                    continue
                
                # Verificar se é link de produto
                is_product_link = any(pattern in url.lower() for pattern in product_patterns)
                
                # Ou se tem imagem de produto próxima
                if not is_product_link:
                    parent = a.parent
                    if parent and parent.find("img"):
                        is_product_link = True
                
                if is_product_link:
                    candidates.append(url)
        
        # Remover duplicados mantendo ordem
        seen = set()
        unique = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        
        return unique


# ============================================================================
# TESTE
# ============================================================================
if __name__ == "__main__":
    print("=== Teste GenialMotor Scraper ===\n")
    
    from core.selenium_utils import build_driver
    
    scraper = GenialMotorScraper()
    driver = build_driver(headless=True)
    
    try:
        # Teste com ref fake
        print("Testando busca por 'H.085.LR1X'...")
        result = scraper.search_product(driver, ["H085LR1X"])
        
        if result:
            print(f"✅ Produto encontrado!")
            print(f"   URL: {result.url}")
            print(f"   Preço: {result.price_text}")
            print(f"   Confiança: {result.confidence:.2f}")
        else:
            print("❌ Produto não encontrado")
        
        # Estatísticas
        print(f"\nEstatísticas: {scraper.get_stats()}")
    
    finally:
        driver.quit()
        scraper.save_cache()
