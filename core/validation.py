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
    reason: str

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 3),
            "match_type": self.match_type.value,
            "matched_parts": self.matched_parts,
            "reason": self.reason,
        }


def validate_product_match(
    our_parts: List[str],
    page_identifiers: Dict[str, List[str]],
    page_url: str,
    page_text: str,
) -> ValidationResult:
    """
    Valida se um produto de página corresponde à referência do feed.

    our_parts:
        Lista de referências normalizadas, onde o primeiro elemento é a principal.
        Para referências compostas X+Y, our_parts já vem preparado com:
            [ref_concatenada, parte_X, parte_Y, ...]
    """
    if not our_parts:
        return ValidationResult(
            False, 0.0, MatchType.NO_MATCH, [], "Sem partes para validar"
        )

    our_main_ref = our_parts[0]
    is_composite = len(our_parts) > 1

    page_skus = [norm_token(s) for s in page_identifiers.get("sku", [])]
    page_codes = [norm_token(c) for c in page_identifiers.get("codes", [])]
    page_url_norm = norm_token(page_url or "")

    # 1. MATCH EXATO EM SKU (100%)
    if our_main_ref in page_skus:
        return ValidationResult(
            True,
            1.0,
            MatchType.SKU_MATCH,
            [our_main_ref],
            f"SKU exato: {our_main_ref}",
        )

    # 2. MATCH EXATO EM CODES (95%)
    if our_main_ref in page_codes:
        return ValidationResult(
            True,
            0.95,
            MatchType.EXACT_MATCH,
            [our_main_ref],
            f"Código exato: {our_main_ref}",
        )

    # 3. REFERÊNCIA PRINCIPAL NO URL (90%)
    if our_main_ref and our_main_ref in page_url_norm:
        return ValidationResult(
            True,
            0.90,
            MatchType.EXACT_MATCH,
            [our_main_ref],
            f"Ref principal no URL: {our_main_ref}",
        )

    # 4. MATCH MULTI-PARTES (para referências compostas)
    matched_parts: List[str] = []
    if is_composite:
        for part in our_parts[1:]:
            # Ignorar pedaços demasiado curtos
            if len(part) < 3:
                continue
            if part in page_skus or part in page_codes or (part in page_url_norm):
                matched_parts.append(part)

        if len(matched_parts) >= 2:
            # Quanto mais partes alinharem, maior a confiança, mas limitado a 0.95
            confidence = min(0.95, 0.75 + (len(matched_parts) * 0.1))
            return ValidationResult(
                True,
                confidence,
                MatchType.STRONG_MATCH,
                matched_parts,
                f"Múltiplas partes coincidentes: {matched_parts}",
            )

        # IMPORTANTE: para referências compostas, se não existirem pelo menos 2 partes
        # claramente presentes na página, não continuamos para fuzzy.
        return ValidationResult(
            False,
            0.0,
            MatchType.NO_MATCH,
            matched_parts,
            "Ref composta sem todas as partes necessárias na página",
        )

    # 5. MATCH FUZZY (apenas para referências simples)
    text_codes = extract_alphanumeric_codes(page_text or "", min_length=5)
    best_match_score = 0.0
    best_match: Optional[str] = None

    for text_code in text_codes:
        if len(text_code) < 5:
            continue
        common = sum(1 for c in our_main_ref if c in text_code)
        score = common / max(len(our_main_ref), len(text_code))
        if score > best_match_score:
            best_match_score = score
            best_match = text_code

    if best_match_score >= 0.7 and best_match:
        confidence = 0.60 + (best_match_score * 0.15)
        is_valid = confidence >= 0.65
        return ValidationResult(
            is_valid,
            confidence,
            MatchType.FUZZY_MATCH,
            [best_match],
            f"Match fuzzy: {best_match} ({best_match_score:.2f})",
        )

    return ValidationResult(
        False, best_match_score, MatchType.NO_MATCH, [], "Nenhum match válido"
    )


def extract_codes_from_text(text: str, min_length: int = 4) -> List[str]:
    """Alias para extract_alphanumeric_codes"""
    return extract_alphanumeric_codes(text, min_length)
