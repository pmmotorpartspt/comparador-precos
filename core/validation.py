# -*- coding: utf-8 -*-
"""core/validation.py - Validação de produtos"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from .normalization import norm_token, extract_alphanumeric_codes

class MatchType(Enum):
    EXACT_MATCH = "EXACT_MATCH"
    SKU_MATCH = "SKU_MATCH"
    STRONG_MATCH = "STRONG_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    NO_MATCH = "NO_MATCH"

@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    match_type: MatchType
    matched_parts: List[str]
    reason: str = ""

def validate_product_match(our_parts: List[str], page_identifiers: Dict[str, List[str]], page_url: str, page_text: str) -> ValidationResult:
    """Valida se produto corresponde à referência"""
    if not our_parts:
        return ValidationResult(False, 0.0, MatchType.NO_MATCH, [], "Sem partes para validar")
    
    our_main_ref = our_parts[0]
    page_skus = [norm_token(s) for s in page_identifiers.get("sku", [])]
    page_codes = [norm_token(c) for c in page_identifiers.get("codes", [])]
    
    # 1. EXACT MATCH DO SKU (100%)
    if our_main_ref in page_skus:
        return ValidationResult(True, 1.0, MatchType.SKU_MATCH, [our_main_ref], f"SKU exato: {our_main_ref}")
    
    # 2. MATCH EXATO EM CODES (95%)
    if our_main_ref in page_codes:
        return ValidationResult(True, 0.95, MatchType.EXACT_MATCH, [our_main_ref], f"Código exato: {our_main_ref}")
    
    # 3. MATCH NO URL (90%)
    url_normalized = norm_token(page_url)
    if our_main_ref in url_normalized:
        return ValidationResult(True, 0.90, MatchType.STRONG_MATCH, [our_main_ref], "Ref no URL")
    
    # 4. MATCH DE MÚLTIPLAS PARTES
    if len(our_parts) > 1:
        matches = []
        for part in our_parts:
            if len(part) >= 3 and (part in page_skus or part in page_codes):
                matches.append(part)
        if len(matches) >= 2:
            confidence = min(0.95, 0.75 + (len(matches) * 0.1))
            return ValidationResult(True, confidence, MatchType.STRONG_MATCH, matches, f"Múltiplas partes: {matches}")
    
    # 5. FUZZY MATCH NO TEXTO
    text_codes = extract_alphanumeric_codes(page_text, min_length=5)
    best_match_score = 0.0
    best_match = None
    for text_code in text_codes:
        if len(text_code) >= 5:
            common = sum(1 for c in our_main_ref if c in text_code)
            score = common / max(len(our_main_ref), len(text_code))
            if score > best_match_score:
                best_match_score = score
                best_match = text_code
    
    if best_match_score >= 0.7:
        confidence = 0.60 + (best_match_score * 0.15)
        is_valid = confidence >= 0.65
        return ValidationResult(is_valid, confidence, MatchType.FUZZY_MATCH, [best_match] if best_match else [], f"Match fuzzy: {best_match} ({best_match_score:.2f})")
    
    return ValidationResult(False, best_match_score, MatchType.NO_MATCH, [], "Nenhum match válido")

def extract_codes_from_text(text: str, min_length: int = 4) -> List[str]:
    """Alias para extract_alphanumeric_codes"""
    return extract_alphanumeric_codes(text, min_length)
