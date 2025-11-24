# -*- coding: utf-8 -*-
"""
core/feed.py
Parser de feeds XML com lógica para busca automática de referência.
v4.9.1 - Corrigido parser de preços para Black Friday
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


def parse_feed(feed_path: Union[str, Path]) -> List[FeedProduct]:
    """
    Parse do feed.xml e extrai produtos com suas referências.
    
    1. Tenta campo <g:mpn> (mais confiável)
    2. Se não tem, procura no <g:description> por "Ref Fabricante: XXX"
    3. Se não encontrar, usa <g:id> como fallback
    
    Args:
        feed_path: Caminho do feed.xml ou string com conteúdo XML
        
    Returns:
        Lista de FeedProduct com refs normalizadas
    """
    products = []
    
    # Se receber string, assumir que é conteúdo XML
    if isinstance(feed_path, str) and feed_path.strip().startswith('<?xml'):
        root = ET.fromstring(feed_path)
    else:
        # É um path
        feed_path = Path(feed_path)
        if not feed_path.exists():
            print(f"[ERRO] Feed não encontrado: {feed_path}")
            return products
        
        tree = ET.parse(feed_path)
        root = tree.getroot()
    
    # Namespaces comuns em feeds do Google
    ns = {
        'g': 'http://base.google.com/ns/1.0',
        'atom': 'http://www.w3.org/2005/Atom'
    }
    
    # Procurar items/entry no feed
    items = root.findall('.//item') or root.findall('.//entry', ns)
    
    for item in items:
        # ID do produto
        id_elem = item.find('g:id', ns) or item.find('id')
        if id_elem is None:
            continue
        product_id = id_elem.text.strip()
        
        # Título
        title_elem = item.find('title') or item.find('g:title', ns)
        title = title_elem.text.strip() if title_elem is not None else "Sem título"
        
        # Link
        link_elem = item.find('link') or item.find('g:link', ns)
        link = link_elem.text.strip() if link_elem is not None else ""
        
        # Preço
        price_elem = item.find('g:price', ns)
        price_text = price_elem.text.strip() if price_elem is not None else ""
        price_num = parse_price(price_text) if price_text else None
        
        # LÓGICA DE BUSCA DA REFERÊNCIA
        # 1. Tentar g:mpn (mais confiável)
        mpn_elem = item.find('g:mpn', ns)
        ref_raw = None
        
        if mpn_elem is not None and mpn_elem.text:
            ref_raw = mpn_elem.text.strip()
        
        # 2. Se não tem MPN, procurar na description
        if not ref_raw:
            desc_elem = item.find('g:description', ns) or item.find('description')
            if desc_elem is not None and desc_elem.text:
                ref_raw = extract_ref_from_description(desc_elem.text)
        
        # 3. Fallback: usar o ID
        if not ref_raw:
            ref_raw = product_id
        
        # Normalizar referência
        ref_norm, ref_parts = normalize_reference(ref_raw)
        
        # Criar produto
        product = FeedProduct(
            id=product_id,
            title=title,
            link=link,
            price_text=price_text,
            price_num=price_num,
            ref_raw=ref_raw,
            ref_norm=ref_norm,
            ref_parts=ref_parts
        )
        products.append(product)
    
    return products


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
