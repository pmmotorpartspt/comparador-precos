# -*- coding: utf-8 -*-
"""
scrapers/genialmotor.py
Scraper para GenialMotor.it
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
        """Busca produto no GenialMotor."""
        
        if ref_raw:
            ref_query = ref_raw
        else:
            ref_query = "+".join(ref_parts)
        
        search_url = f"{self.base_url}en/search?s={ref_query}"
        
        html = get_page_html(driver, search_url)
        if not html:
            return None
        
        identifiers = self._extract_identifiers(html)
        price_text = extract_price_from_html(html)
        
        validation = validate_product_match(
            our_parts=ref_parts,
            page_identifiers=identifiers,
            page_url=driver.current_url,
            page_text=BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        )
        
        if validation.is_valid and price_text:
            return SearchResult(
                url=driver.current_url,
                price_text=price_text,
                price_num=parse_price_to_float(price_text),
                validation=validation
            )
        
        candidate_urls = self._extract_candidate_urls(html, ref_parts, driver.current_url)
        
        print(f"[GenialMotor DEBUG] Ref: {ref_raw if ref_raw else ref_parts}")
        print(f"[GenialMotor DEBUG] Candidatos: {len(candidate_urls)}")
        if candidate_urls:
            for i, u in enumerate(candidate_urls[:3], 1):
                print(f"[GenialMotor DEBUG]   [{i}] {u[:80]}")
        
        max_urls = MAX_URLS_COMPOSITE if len(ref_parts) > 1 else MAX_URLS_SIMPLE
        candidate_urls = candidate_urls[:max_urls]
        
        for url in candidate_urls:
            prod_html = get_page_html(driver, url)
            if not prod_html:
                continue
            
            prod_identifiers = self._extract_identifiers(prod_html)
            prod_price = extract_price_from_html(prod_html)
            
            if not prod_price:
                continue
            
            prod_validation = validate_product_match(
                our_parts=ref_parts,
                page_identifiers=prod_identifiers,
                page_url=url,
                page_text=BeautifulSoup(prod_html, "lxml").get_text(" ", strip=True)
            )
            
            if prod_validation.is_valid:
                return SearchResult(
                    url=url,
                    price_text=prod_price,
                    price_num=parse_price_to_float(prod_price),
                    validation=prod_validation
                )
        
        return None
    
    def _extract_identifiers(self, html: str) -> Dict[str, List[str]]:
        """Extrai identificadores (SKU, MPN, códigos)."""
        soup = BeautifulSoup(html, "lxml")
        ids = {"sku": [], "mpn": [], "codes": []}
        
        import json
        for script_tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script_tag.string or "")
                
                def scan_json(obj):
                    if isinstance(obj, dict):
                        if obj.get("@type") == "Product":
                            for key in ["sku", "mpn", "gtin13", "gtin14", "productID"]:
                                value = obj.get(key)
                                if isinstance(value, str) and value.strip():
                                    target = "sku" if key == "sku" else "mpn" if key == "mpn" else "codes"
                                    ids[target].append(value.strip().upper())
                        
                        for v in obj.values():
                            scan_json(v)
                    
                    elif isinstance(obj, list):
                        for item in obj:
                            scan_json(item)
                
                scan_json(data)
            
            except:
                continue
        
        for attr, target in [("sku", "sku"), ("mpn", "mpn")]:
            tag = soup.find(attrs={"itemprop": attr})
            if tag:
                value = tag.get("content") or tag.get_text(strip=True)
                if value:
                    ids[target].append(value.strip().upper())
        
        h1 = soup.find("h1")
        if h1:
            ids["codes"].extend(TOKEN_RE.findall(h1.get_text(" ", strip=True).upper()))
        
        full_text = soup.get_text(" ", strip=True).upper()
        ids["codes"].extend(TOKEN_RE.findall(full_text))
        
        for img in soup.find_all("img"):
            src = (img.get("src") or "").upper()
            ids["codes"].extend(TOKEN_RE.findall(src))
        
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
        """Extrai URLs candidatos. FALLBACK: pega todos os produtos se não encontrar específicos."""
        soup = BeautifulSoup(html, "lxml")
        candidates_specific = []
        all_product_links = []
        
        from core.normalization import norm_token
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            
            if href.startswith("http"):
                url = href
            else:
                url = self.base_url.rstrip("/") + "/" + href.lstrip("/")
            
            if any(x in url.lower() for x in ["/cart", "/login", "/wishlist", "/compare", "/search", "/category", "/brand", "/contact"]):
                continue
            
            is_product = any(pattern in url.lower() for pattern in ["/product", "-p-", "-p.html", ".html"]) or (a.parent and a.parent.find("img"))
            
            if is_product:
                all_product_links.append(url)
            
            link_text = (a.get_text(" ", strip=True) or "").upper()
            url_upper = url.upper()
            
            if len(ref_parts) == 1:
                target = norm_token(ref_parts[0])
                if target in norm_token(link_text) or target in norm_token(url_upper):
                    candidates_specific.append(url)
            else:
                part_combos = [
                    "+".join(ref_parts),
                    "+".join(reversed(ref_parts))
                ]
                
                for combo in part_combos:
                    if norm_token(combo) in norm_token(link_text) or norm_token(combo) in norm_token(url_upper):
                        candidates_specific.append(url)
                        break
        
        if candidates_specific:
            candidates = candidates_specific
        elif all_product_links:
            candidates = all_product_links[:10]
        else:
            candidates = []
        
        seen = set()
        unique = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        
        return unique


if __name__ == "__main__":
    print("=== Teste GenialMotor ===")
    from core.selenium_utils import build_driver
    
    scraper = GenialMotorScraper()
    driver = build_driver(headless=True)
    
    try:
        result = scraper.search_product(driver, ["SPM04D"], ref_raw="SPM04D")
        
        if result:
            print(f"✅ Encontrado: {result.url}")
            print(f"   Preço: {result.price_text}")
        else:
            print("❌ Não encontrado")
    
    finally:
        driver.quit()
        scraper.save_cache()
