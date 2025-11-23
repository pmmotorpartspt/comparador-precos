# -*- coding: utf-8 -*-
"""
core/feed.py
Parser do feed XML, extraindo produtos e referências.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .normalization import normalize_reference
from .config import FEED_PATH


@dataclass
class FeedProduct:
    """Representa um produto vindo do feed XML"""

    id: str
    title: str
    link: str
    price_text: str
    price_num: Optional[float]
    ref_raw: str
    ref_norm: str
    ref_parts: List[str]

    def to_dict(self):
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
            </g:description>
        </item>

    Args:
        feed_path: Caminho para o ficheiro XML do feed
        max_products: Se > 0, limita o número de produtos (para testes)

    Returns:
        Lista de FeedProduct com referências válidas.
    """
    products: List[FeedProduct] = []

    if not feed_path.exists():
        print(f"[AVISO] Feed não encontrado em: {feed_path}")
        print("(Normal se ainda não configuraste)")
        return products

    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except ET.ParseError:
        print(f"[ERRO] Falha ao parsear XML em: {feed_path}")
        return products

    # Os items podem estar dentro de <channel> ou diretamente sob root
    items = root.findall(".//item")

    for idx, item in enumerate(items):
        if max_products and idx >= max_products:
            break

        # Extrair campos básicos
        id_el = item.find("./{*}id")
        title_el = item.find("./title")
        link_el = item.find("./link")
        price_el = item.find("./{*}price")
        desc_el = item.find("./description")

        if id_el is None or title_el is None or link_el is None:
            continue

        prod_id = id_el.text or ""
        title = title_el.text or ""
        link = link_el.text or ""
        price_text = price_el.text if price_el is not None else ""
        price_num = parse_price(price_text) if price_text else None
        description = desc_el.text or ""

        # Procurar referência do fabricante dentro da descrição
        # Aceita vários formatos de label
        ref_raw = ""
        ref_norm = ""
        ref_parts: List[str] = []

        # Padrões típicos no feed
        patterns = [
            r"Ref\.?\s*Fabricante[:\s]+([A-Za-z0-9\.\-\/\+\_]+)",
            r"Ref\.?\s*do\s*Fabricante[:\s]+([A-Za-z0-9\.\-\/\+\_]+)",
            r"Referencia[:\s]+([A-Za-z0-9\.\-\/\+\_]+)",
        ]

        for pat in patterns:
            m = re.search(pat, description, flags=re.IGNORECASE)
            if m:
                ref_raw = m.group(1).strip()
                break

        if not ref_raw:
            # Sem referência do fabricante, ignorar produto
            continue

        ref_norm, ref_parts = normalize_reference(ref_raw)

        # Validar que temos pelo menos uma parte
        if not ref_parts:
            continue

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

    return products
