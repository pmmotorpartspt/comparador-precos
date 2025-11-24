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


class FeedParseError(Exception):
    """Erro ao parsear feed"""
    pass


class InvalidFeedStructure(Exception):
    """Estrutura inesperada no feed"""
    pass


class MissingReferenceError(Exception):
    """Produto sem referência do fabricante"""
    pass


class InvalidReferenceError(Exception):
    """Referência não pôde ser normalizada"""
    pass


class EmptyFeedError(Exception):
    """Feed sem produtos válidos"""
    pass


class DuplicateIdWarning(Warning):
    """ID duplicado no feed"""
    pass


class DuplicateRefWarning(Warning):
    """Referência duplicada no feed"""
    pass


class PriceParseWarning(Warning):
    """Falha ao parsear preço"""
    pass


class DescriptionWarning(Warning):
    """Problemas na description"""
    pass


class LinkWarning(Warning):
    """Problema com link do produto"""
    pass


class FeedStats:
    """Estatísticas do feed"""

    def __init__(self):
        self.total_items = 0
        self.valid_products = 0
        self.missing_refs = 0
        self.invalid_refs = 0
        self.duplicate_ids = 0
        self.duplicate_refs = 0
        self.price_parse_errors = 0
        self.description_warnings = 0
        self.link_warnings = 0

    def to_dict(self) -> Dict:
        return {
            "total_items": self.total_items,
            "valid_products": self.valid_products,
            "missing_refs": self.missing_refs,
            "invalid_refs": self.invalid_refs,
            "duplicate_ids": self.duplicate_ids,
            "duplicate_refs": self.duplicate_refs,
            "price_parse_errors": self.price_parse_errors,
            "description_warnings": self.description_warnings,
            "link_warnings": self.link_warnings,
        }


def feed_stats(products: List["FeedProduct"]) -> Dict:
    """
    Gera estatísticas simples a partir da lista de produtos final.
    """
    stats = FeedStats()
    stats.total_items = len(products)
    stats.valid_products = len(products)

    unique_ids = set()
    unique_refs = set()

    for p in products:
        if p.id in unique_ids:
            stats.duplicate_ids += 1
        else:
            unique_ids.add(p.id)

        if p.ref_norm in unique_refs:
            stats.duplicate_refs += 1
        else:
            unique_refs.add(p.ref_norm)

        if p.price_num is None:
            stats.price_parse_errors += 1

    return stats.to_dict()


def parse_price(price_text: str) -> Optional[float]:
    """
    Extrai valor numérico de preço do feed.
    
    Exemplos:
        "331.50 EUR" → 331.50
        "€ 125,99" → 125.99
        "1.234,56 EUR" → 1234.56
        "De 200,00 EUR por 150,00 EUR" → 150.00
    
    Args:
        price_text: Preço como string
        
    Returns:
        Valor float ou None se não conseguir parsear.
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
    
    # Detetar formato: vírgula como decimal (europeu)
    if "," in raw and raw.count(",") == 1 and raw.rfind(",") > raw.rfind("."):
        # Formato europeu: ponto = separador milhares, vírgula = decimal
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # Formato americano ou sem ambiguidade
        raw = raw.replace(",", "")
    
    try:
        return float(raw)
    except ValueError:
        return None


class FeedProduct:
    """
    Representa um produto do feed, já com referência normalizada e separada.
    """

    __slots__ = (
        "id",
        "title",
        "link",
        "price_text",
        "price_num",
        "ref_raw",
        "ref_norm",
        "ref_parts",
    )

    def __init__(
        self,
        id: str,
        title: str,
        link: str,
        price_text: str,
        price_num: Optional[float],
        ref_raw: str,
        ref_norm: str,
        ref_parts: List[str],
    ):
        self.id = id
        self.title = title
        self.link = link
        self.price_text = price_text
        self.price_num = price_num
        self.ref_raw = ref_raw
        self.ref_norm = ref_norm
        self.ref_parts = ref_parts

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "price_text": self.price_text,
            "price_num": self.price_num,
            "ref_raw": self.ref_raw,
            "ref_norm": self.ref_norm,
            "ref_parts": self.ref_parts,
        }

    def __repr__(self):
        return f"FeedProduct(id={self.id}, ref={self.ref_raw}, price={self.price_text})"


def _get_text(el: Optional[ET.Element]) -> str:
    """Helper para extrair texto limpo de um elemento XML."""
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def parse_feed(feed_path: Path = FEED_PATH, max_products: int = 0) -> List["FeedProduct"]:
    """
    Lê o feed XML e devolve uma lista de FeedProduct prontos para comparação.

    Regras:
    - Só entram produtos com referência válida e normalizável.
    - Referência vem da description (Ref. Fabricante, Ref do Fabricante, etc.).
    - Price é lido do campo de preço e convertido para float se possível.
    """
    if not feed_path.exists():
        raise FileNotFoundError(f"Feed não encontrado em: {feed_path}")

    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise FeedParseError(f"Erro ao parsear XML: {e}")

    items = root.findall(".//item")
    if not items:
        raise EmptyFeedError("Nenhum item encontrado no feed")

    products: List[FeedProduct] = []
    seen_ids = set()
    seen_refs = set()

    for idx, item in enumerate(items):
        if max_products and len(products) >= max_products:
            break

        # Campos obrigatórios básicos
        id_el = item.find("./{*}id") or item.find("./id")
        title_el = item.find("./title")
        link_el = item.find("./link")
        price_el = item.find("./{*}price") or item.find("./price")
        desc_el = item.find("./description")

        prod_id = _get_text(id_el)
        title = _get_text(title_el)
        link = _get_text(link_el)
        price_text = _get_text(price_el)
        description = _get_text(desc_el)

        if not prod_id or not title or not link:
            continue

        # Verificar IDs duplicados
        if prod_id in seen_ids:
            # Apenas conta estatística, mas não falha
            # (IDs duplicados podem existir em alguns feeds mal construídos)
            pass
        else:
            seen_ids.add(prod_id)

        # Extrair referência do fabricante a partir da description
        if not description:
            raise DescriptionWarning(f"Produto {prod_id} sem description")

        ref_raw = extract_ref_from_description(description)
        if not ref_raw:
            # Sem referência = produto não é útil para o comparador
            continue

        ref_norm, ref_parts = normalize_ref(ref_raw)
        if not ref_norm or not ref_parts:
            # Referência não pôde ser normalizada
            continue

        # Verificar refs duplicadas
        if ref_norm in seen_refs:
            # Não bloqueia, mas sinaliza
            pass
        else:
            seen_refs.add(ref_norm)

        # Parse preço
        price_num = parse_price(price_text) if price_text else None

        product = FeedProduct(
            id=prod_id,
            title=title,
            link=link,
            price_text=price_text,
            price_num=price_num,
            ref_raw=ref_raw,
            ref_norm=ref_norm,
            ref_parts=ref_parts,
        )
        products.append(product)

    if not products:
        raise EmptyFeedError("Nenhum produto com referência válida foi encontrado no feed")

    return products


if __name__ == "__main__":
    # Pequeno teste manual quando corrido diretamente
    fp = FEED_PATH
    if fp.exists():
        try:
            products = parse_feed(fp, max_products=20)
            print(f"Total produtos lidos: {len(products)}")
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
