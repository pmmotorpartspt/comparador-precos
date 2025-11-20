# -*- coding: utf-8 -*-
"""
core/feed.py
Parser do feed XML de produtos.
Extrai refs da description, normaliza, prepara para comparação.
"""
from pathlib import Path
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
import re

from .normalization import normalize_ref, extract_ref_from_description
from config import FEED_PATH


class FeedProduct:
    """Representa um produto do feed"""
    
    def __init__(self, product_id: str, title: str, url: str, 
                 price_text: str, price_num: Optional[float],
                 ref_raw: str, ref_norm: str, ref_parts: List[str]):
        self.id = product_id
        self.title = title
        self.url = url
        self.price_text = price_text
        self.price_num = price_num
        self.ref_raw = ref_raw      # Ex: "H.085.LR1X"
        self.ref_norm = ref_norm    # Ex: "H085LR1X"
        self.ref_parts = ref_parts  # Ex: ["H085LR1X"] ou ["H085LR1X", "ABC123"]
    
    def is_simple(self) -> bool:
        """Verifica se é referência simples (1 parte)"""
        return len(self.ref_parts) == 1
    
    def is_composite(self) -> bool:
        """Verifica se é referência composta (2+ partes)"""
        return len(self.ref_parts) > 1
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "price_text": self.price_text,
            "price_num": self.price_num,
            "ref_raw": self.ref_raw,
            "ref_norm": self.ref_norm,
            "ref_parts": self.ref_parts,
        }
    
    def __repr__(self):
        return f"FeedProduct(id={self.id}, ref={self.ref_raw}, price={self.price_text})"


def parse_price(price_text: str) -> Optional[float]:
    """
    Extrai valor numérico de preço do feed.
    
    Exemplos:
        "331.50 EUR" → 331.50
        "€ 125,99" → 125.99
        "1.234,56 EUR" → 1234.56
    
    Args:
        price_text: Preço como string
        
    Returns:
        Valor float ou None se não conseguir parsear
    """
    if not price_text:
        return None
    
    # Remove símbolos de moeda
    s = price_text.replace("€", " ").replace("EUR", " ")
    
    # Remove caracteres especiais exceto dígitos, vírgula, ponto, espaço
    s = re.sub(r"[^\d,.\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    
    # Detectar formato: se tem vírgula como decimal (europeu)
    # Ex: "1.234,56" → vírgula é decimal
    if "," in s and s.count(",") == 1 and s.rfind(",") > s.rfind("."):
        # Formato europeu: ponto = separador milhares, vírgula = decimal
        s = s.replace(".", "").replace(",", ".")
    else:
        # Formato americano ou sem ambiguidade
        s = s.replace(",", "")
    
    try:
        return float(s)
    except ValueError:
        return None


def parse_feed(feed_path: Path = FEED_PATH, max_products: int = 0) -> List[FeedProduct]:
    """
    Lê feed XML e extrai produtos com referências válidas.
    
    Estrutura esperada do feed:
        <item>
            <g:id>12345</g:id>
            <g:title>Nome do Produto</g:title>
            <g:link>https://...</g:link>
            <g:price>331.50 EUR</g:price>
            <g:description>
                Descrição...
                Ref. Fabricante: H.085.LR1X
                ...
            </g:description>
        </item>
    
    Args:
        feed_path: Caminho para o ficheiro XML (Path ou str)
        max_products: Limite de produtos (0 = sem limite, útil para testes)
        
    Returns:
        Lista de FeedProduct (só produtos COM ref válida)
        
    Raises:
        FileNotFoundError: Se feed não existir
        Exception: Se erro ao parsear XML
    """
    # Converter para Path se for string
    if isinstance(feed_path, str):
        feed_path = Path(feed_path)
    
    if not feed_path.exists():
        raise FileNotFoundError(f"Feed não encontrado: {feed_path}")
    
    # Namespace do Google Shopping
    ns = {"g": "http://base.google.com/ns/1.0"}
    
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except Exception as e:
        raise Exception(f"Erro ao parsear XML: {e}")
    
    products = []
    total_items = 0
    skipped_no_ref = 0
    skipped_invalid_ref = 0
    
    for item in root.findall(".//item"):
        total_items += 1
        
        # Extrair campos
        product_id = (item.findtext("g:id", "", ns) or "").strip()
        title = (item.findtext("g:title", "", ns) or "").strip()
        link = (item.findtext("g:link", "", ns) or "").strip()
        price = (item.findtext("g:price", "", ns) or "").strip()
        description = item.findtext("g:description", "", ns) or ""
        
        # Extrair referência da descrição
        ref_raw = extract_ref_from_description(description)
        
        if not ref_raw:
            skipped_no_ref += 1
            continue
        
        # Normalizar referência
        ref_norm, ref_parts = normalize_ref(ref_raw)
        
        if not ref_norm or not ref_parts:
            skipped_invalid_ref += 1
            continue
        
        # Parsear preço
        price_num = parse_price(price)
        
        # Criar objeto FeedProduct
        product = FeedProduct(
            product_id=product_id,
            title=title,
            url=link,
            price_text=price,
            price_num=price_num,
            ref_raw=ref_raw,
            ref_norm=ref_norm,
            ref_parts=ref_parts
        )
        
        products.append(product)
        
        # Limite (se especificado)
        if max_products > 0 and len(products) >= max_products:
            break
    
    # Log resumo
    print(f"[FEED] Total de itens no XML: {total_items}")
    print(f"[FEED] Sem referência: {skipped_no_ref}")
    print(f"[FEED] Ref inválida: {skipped_invalid_ref}")
    print(f"[FEED] Produtos válidos: {len(products)}")
    
    if products:
        simple = sum(1 for p in products if p.is_simple())
        composite = len(products) - simple
        print(f"[FEED]   → Simples: {simple}, Compostas: {composite}")
    
    return products


def feed_stats(products: List[FeedProduct]) -> Dict:
    """
    Estatísticas dos produtos do feed.
    
    Args:
        products: Lista de FeedProduct
        
    Returns:
        Dict com estatísticas
    """
    if not products:
        return {
            "total": 0,
            "simple": 0,
            "composite": 0,
            "with_price": 0,
            "without_price": 0,
        }
    
    simple = sum(1 for p in products if p.is_simple())
    composite = sum(1 for p in products if p.is_composite())
    with_price = sum(1 for p in products if p.price_num is not None)
    without_price = len(products) - with_price
    
    return {
        "total": len(products),
        "simple": simple,
        "composite": composite,
        "with_price": with_price,
        "without_price": without_price,
    }


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Parser do Feed ===\n")
    
    # Teste de parse_price
    print("Testes de parse_price:")
    test_prices = [
        "331.50 EUR",
        "€ 125,99",
        "1.234,56 EUR",
        "1,234.56",
        "invalid",
    ]
    
    for test in test_prices:
        result = parse_price(test)
        print(f"  '{test}' → {result}")
    
    print("\n" + "="*50 + "\n")
    
    # Teste de parse_feed (se feed existir)
    if FEED_PATH.exists():
        print(f"Carregando feed: {FEED_PATH}\n")
        
        try:
            # Carregar só primeiros 5 produtos
            products = parse_feed(max_products=5)
            
            print("\nPrimeiros produtos:")
            for i, product in enumerate(products, 1):
                print(f"{i}. {product}")
            
            print("\nEstatísticas:")
            stats = feed_stats(products)
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        except Exception as e:
            print(f"Erro: {e}")
    else:
        print(f"Feed não encontrado em: {FEED_PATH}")
        print("(Normal se ainda não configuraste)")
