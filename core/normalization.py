# -*- coding: utf-8 -*-
"""
core/normalization.py
Normalização de referências de produtos e extração de refs do campo description.
"""
import re
from typing import List, Optional, Tuple


# Padrões para extrair referência do campo <g:description>
REF_PATS = [
    re.compile(r"(?i)\bref\.\s*fabricante\s*:\s*([^\r\n<]+)"),      # Ref. Fabricante:
    re.compile(r"(?i)\bref\s+fabricante\s*:\s*([^\r\n<]+)"),        # Ref Fabricante:
    re.compile(r"(?i)\bref\s+do\s+fabricante\s*:\s*([^\r\n<]+)"),  # Ref do Fabricante:
]

PLUS_SPACES = re.compile(r"\s+")


def extract_ref_from_description(desc: str) -> Optional[str]:
    """
    Extrai referência do campo <g:description>.
    Procura por: "Ref Fabricante:", "Ref. Fabricante:", "Ref do Fabricante:"
    
    Args:
        desc: Texto da description
        
    Returns:
        Referência encontrada ou None
    """
    if not desc:
        return None
    
    for pat in REF_PATS:
        m = pat.search(desc)
        if m:
            ref = m.group(1).strip()
            # Substituir múltiplos espaços por "+" (para refs compostas)
            ref = PLUS_SPACES.sub("+", ref)
            return ref
    
    return None


def norm_token(s: str) -> str:
    """
    Normaliza um token (remove hífens, pontos, espaços, underscores).
    Converte para maiúsculas.
    
    Args:
        s: String a normalizar
        
    Returns:
        String normalizada em maiúsculas sem caracteres especiais
    """
    if not s:
        return ""
    s = s.replace("-", "").replace(".", "").replace(" ", "").replace("_", "").replace("+", "")
    return s.upper()


def normalize_reference(ref: str) -> Tuple[str, List[str]]:
    """
    Normaliza uma referência e retorna partes.
    
    Args:
        ref: Referência original (pode ter hífens, pontos, espaços, +)
        
    Returns:
        Tupla (ref_normalizada, [lista_de_partes])
        
    Examples:
        "H.085.LR1X" -> ("H085LR1X", ["H085LR1X"])
        "ABC123+DEF456" -> ("ABC123DEF456", ["ABC123DEF456", "ABC123", "DEF456"])
    """
    if not ref:
        return "", []
    
    # Se tem "+", é ref composta
    if "+" in ref:
        parts_raw = [p.strip() for p in ref.split("+") if p.strip()]
        parts_norm = [norm_token(p) for p in parts_raw if norm_token(p)]
        # Ref normalizada = todas as partes juntas
        ref_norm = "".join(parts_norm)
        # Lista de partes = ref completa + partes individuais
        return ref_norm, [ref_norm] + parts_norm
    
    # Ref simples
    normalized = norm_token(ref)
    parts = [normalized] if normalized else []
    return normalized, parts


def normalize_ref(ref: str) -> Tuple[str, List[str]]:
    """
    Alias para normalize_reference (compatibilidade).
    
    Args:
        ref: Referência original
        
    Returns:
        Tupla (ref_normalizada, [lista_de_partes])
    """
    return normalize_reference(ref)


def split_reference_parts(ref: str) -> List[str]:
    """
    Divide referência em partes lógicas (usado para validação).
    
    Args:
        ref: Referência normalizada
        
    Returns:
        Lista de partes possíveis
        
    Examples:
        "H085LR1X" -> ["H085LR1X", "H085", "LR1X"]
        "ABC123" -> ["ABC123", "ABC", "123"]
    """
    if not ref:
        return []
    
    parts = [ref]
    
    # Tentar pattern: Letras+Números+LetrasNúmeros
    match = re.match(r'^([A-Z]+\d+)([A-Z0-9]+)$', ref)
    if match:
        parts.extend([match.group(1), match.group(2)])
        return parts
    
    # Tentar pattern: Letras+Números
    match = re.match(r'^([A-Z]+)(\d+)$', ref)
    if match:
        parts.extend([match.group(1), match.group(2)])
        return parts
    
    return parts


def extract_alphanumeric_codes(text: str, min_length: int = 3) -> List[str]:
    """
    Extrai códigos alfanuméricos de um texto (usado para validação).
    
    Args:
        text: Texto onde procurar códigos
        min_length: Comprimento mínimo dos códigos
        
    Returns:
        Lista de códigos encontrados (normalizados)
    """
    if not text:
        return []
    
    pattern = re.compile(r'\b([A-Z0-9][\w\-\.]{%d,})\b' % (min_length - 1), re.I)
    codes = []
    seen = set()
    
    for match in pattern.finditer(text):
        code = norm_token(match.group(1))
        if code and len(code) >= min_length and code not in seen:
            seen.add(code)
            codes.append(code)
    
    return codes


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Normalização ===\n")
    
    # Teste extract_ref_from_description
    print("Teste extract_ref_from_description:")
    test_descs = [
        "Produto X\nRef Fabricante: H.085.LR1X\nOutras infos",
        "Descrição\nRef. Fabricante: ABC-123\nMais texto",
        "Info\nRef do Fabricante: P-HF1595\nFim",
        "Sem referência aqui",
    ]
    
    for desc in test_descs:
        ref = extract_ref_from_description(desc)
        print(f"  {desc[:30]}... -> {ref}")
    
    print("\n" + "="*50 + "\n")
    
    # Teste normalize_reference
    print("Teste normalize_reference:")
    test_refs = [
        "H.085.LR1X",
        "P-HF1595",
        "ABC123+DEF456",
        "AC05-M8",
    ]
    
    for ref in test_refs:
        norm, parts = normalize_reference(ref)
        print(f"  '{ref}' -> norm='{norm}', parts={parts}")
