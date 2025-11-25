# -*- coding: utf-8 -*-
"""
core/feed.py
Parser de feeds XML - v4.9.1 HOTFIX
Corrigido: Mantém lógica original de extração da descrição + parser Black Friday
"""
from pathlib import Path
from typing import List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET
import re

from .normalization import normalize_reference, extract_ref_from_description


@dataclass
class FeedProduct:
    """Produto lido do feed XML."""
    id: str
    title: str
    link: str
    price_text: str
    price_num: Optional[float]
    ref_raw: str          # Referência original (com hífens/pontos)
    ref_norm: str         # Referência normalizada (sem caracteres especiais)
    ref_parts: List[str]  # Lista de partes para busca
    
    def is_simple(self) -> bool:
        """Verifica se é ref simples (não composta)."""
        return "+" not in self.ref_raw
    
    def is_composite(self) -> bool:
        """Verifica se é ref composta (tem +)."""
        return "+" in self.ref_raw


def parse_price(price_text: str) -> Optional[float]:
    """
    Extrai valor numérico de preço do feed.
    v4.9.1: Melhorado para lidar com preços promocionais (Black Friday)
    
    Exemplos:
        "331.50 EUR" → 331.50
        "€ 125,99" → 125.99
        "1.234,56 EUR" → 1234.56
        "~~200,00€~~ 150,00€" → 150.00 (pega o último/atual)
        "De: 89.90 Por: 69.90" → 69.90
        "Antes 200€ - Agora 150€" → 150.00
    
    Args:
        price_text: Preço como string
        
    Returns:
        Valor float ou None se não conseguir parsear
    """
    if not price_text:
        return None
    
    # NOVO: Detectar preços promocionais e pegar o último/atual
    text_lower = price_text.lower()
    
    # Padrões de preço promocional
    if any(marker in price_text for marker in ["~~", "Agora", "agora", "Por:", "por:", "→"]):
        # Tem marcador de promoção - vamos pegar o último preço
        
        # Extrair todos os números que parecem preços (com vírgula ou ponto decimal)
        # Padrão: número com possível separador de milhares e decimal
        price_pattern = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)'
        matches = re.findall(price_pattern, price_text)
        
        if matches:
            # Pegar o último match (preço atual)
            last_price = matches[-1]
            
            # Processar este preço individual
            return _parse_single_price(last_price)
    
    # Se tem "Desde" ou "A partir de", pegar o único preço mencionado
    if any(marker in text_lower for marker in ["desde", "a partir de", "from"]):
        price_pattern = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)'
        matches = re.findall(price_pattern, price_text)
        if matches:
            return _parse_single_price(matches[0])
    
    # Caso normal: processar o texto completo
    return _parse_single_price(price_text)


def _parse_single_price(price_str: str) -> Optional[float]:
    """
    Helper: Parse de um único valor de preço.
    
    Args:
        price_str: String com um único preço
        
    Returns:
        Float ou None
    """
    if not price_str:
        return None
        
    # Remove símbolos de moeda e espaços
    s = price_str
    s = re.sub(r'[€$£¥₹¢]', '', s)  # Remove símbolos de moeda
    s = re.sub(r'(EUR|USD|GBP)', '', s, flags=re.IGNORECASE)  # Remove códigos de moeda
    s = s.strip()
    
    if not s:
        return None
    
    # Detectar formato: Europeu vs Americano
    # Europeu: 1.234,56 (ponto para milhares, vírgula para decimal)
    # Americano: 1,234.56 (vírgula para milhares, ponto para decimal)
    
    # Se tem tanto vírgula quanto ponto, ver qual vem por último
    has_comma = ',' in s
    has_dot = '.' in s
    
    if has_comma and has_dot:
        # Tem ambos - o que vier por último é o separador decimal
        last_comma = s.rfind(',')
        last_dot = s.rfind('.')
        
        if last_comma > last_dot:
            # Vírgula é decimal (formato europeu)
            s = s.replace('.', '').replace(',', '.')
        else:
            # Ponto é decimal (formato americano)
            s = s.replace(',', '')
    elif has_comma:
        # Só tem vírgula
        comma_count = s.count(',')
        if comma_count == 1:
            # Uma vírgula - verificar se é decimal ou milhares
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Parece decimal (ex: 123,45)
                s = s.replace(',', '.')
            else:
                # Parece milhares (ex: 1,234)
                s = s.replace(',', '')
        else:
            # Múltiplas vírgulas - são milhares
            s = s.replace(',', '')
    # Se só tem ponto, deixa como está (formato americano)
    
    # Limpar espaços internos (alguns sites usam espaço como separador de milhares)
    s = s.replace(' ', '')
    
    try:
        value = float(s)
        # Validação de sanidade - preços muito altos provavelmente são erros
        if value > 100000:  # Mais de 100k€ é suspeito para peças de moto
            return None
        return value
    except (ValueError, TypeError):
        return None


def parse_feed(feed_path: Union[str, Path], max_products: int = 0) -> List[FeedProduct]:
    """
    Parse do feed.xml e extrai produtos.
    IMPORTANTE: Referências SEMPRE vêm da descrição (campo "Ref Fabricante:")
    
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
        feed_path: Caminho do ficheiro XML (Path ou str)
        max_products: Limite de produtos (0 = sem limite, útil para testes)
        
    Returns:
        Lista de FeedProduct (só produtos COM ref válida)
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
    
    # IMPORTANTE: Procurar SEMPRE por .//item (não .//entry)
    for item in root.findall(".//item"):
        total_items += 1
        
        # Extrair campos básicos
        product_id = (item.findtext("g:id", "", ns) or "").strip()
        title = (item.findtext("g:title", "", ns) or "").strip()
        link = (item.findtext("g:link", "", ns) or "").strip()
        price = (item.findtext("g:price", "", ns) or "").strip()
        description = item.findtext("g:description", "", ns) or ""
        
        # SEMPRE extrair referência da DESCRIÇÃO (não de g:mpn)
        # Procura por "Ref. Fabricante: XXX" ou "Ref Fabricante: XXX"
        ref_raw = extract_ref_from_description(description)
        
        if not ref_raw:
            skipped_no_ref += 1
            continue
        
        # Normalizar referência
        ref_norm, ref_parts = normalize_reference(ref_raw)
        
        if not ref_norm:
            skipped_invalid_ref += 1
            continue
        
        # Parse do preço (com suporte Black Friday)
        price_num = parse_price(price) if price else None
        
        # Criar produto
        product = FeedProduct(
            id=product_id,
            title=title,
            link=link,
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


# ============================================================================
# TESTES
# ============================================================================

if __name__ == "__main__":
    # Teste do parser de preços Black Friday
    test_prices = [
        ("150,00 EUR", 150.0),
        ("€ 1.234,56", 1234.56),
        ("~~200,00€~~ 150,00€", 150.0),
        ("De: 89.90 Por: 69.90", 69.90),
        ("Antes 200€ - Agora 150€", 150.0),
        ("Desde 45,00€", 45.0),
        ("$1,234.56", 1234.56),
        ("1 234,56 €", 1234.56),  # Espaço como separador de milhares
    ]
    
    print("=== Teste Parser Preços Black Friday ===\n")
    for price_str, expected in test_prices:
        result = parse_price(price_str)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{price_str}' → {result} (esperado: {expected})")
