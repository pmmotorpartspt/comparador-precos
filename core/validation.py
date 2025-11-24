# -*- coding: utf-8 -*-
"""
core/validation.py - Validação de produtos
v4.9.1 - Corrigido fuzzy match para refs compostas
"""
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
    """
    Valida se produto corresponde à referência.
    v4.9.1: Corrigido para não aplicar fuzzy match em refs compostas
    
    Args:
        our_parts: Lista de partes da nossa ref ["ABC123DEF456", "ABC123", "DEF456"]
        page_identifiers: Dict com SKUs e códigos extraídos da página
        page_url: URL da página
        page_text: Texto completo da página
        
    Returns:
        ValidationResult com resultado da validação
    """
    if not our_parts:
        return ValidationResult(False, 0.0, MatchType.NO_MATCH, [], "Sem partes para validar")
    
    our_main_ref = our_parts[0]  # Ref completa concatenada
    is_composite = len(our_parts) > 2  # Se tem mais de 2 partes, é composta (ref completa + partes individuais)
    
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
    
    # 4. MATCH DE MÚLTIPLAS PARTES (refs compostas)
    if is_composite:
        # Para refs compostas, verificar se TODAS as partes individuais estão presentes
        individual_parts = our_parts[1:]  # Pular a primeira que é a concatenação
        matches = []
        
        for part in individual_parts:
            if len(part) >= 3:  # Partes muito curtas podem dar falsos positivos
                # Verificar se esta parte está presente em SKUs, códigos ou URL
                if part in page_skus or part in page_codes or part in url_normalized:
                    matches.append(part)
        
        # Para refs compostas, EXIGIR que TODAS as partes estejam presentes
        if len(matches) == len(individual_parts):
            # Todas as partes encontradas - validação forte
            confidence = 0.85  # Um pouco menor que match exato, mas ainda alta
            return ValidationResult(
                True, confidence, MatchType.STRONG_MATCH, matches, 
                f"Ref composta completa: todas {len(matches)} partes encontradas"
            )
        elif len(matches) > 0:
            # Apenas algumas partes encontradas - NÃO validar
            # Isto evita o problema de aceitar "ABC123" quando procuramos "ABC123+DEF456"
            confidence = 0.30 + (len(matches) * 0.1)  # Confiança baixa
            return ValidationResult(
                False, confidence, MatchType.PARTIAL_MATCH, matches,
                f"Ref composta incompleta: apenas {len(matches)}/{len(individual_parts)} partes"
            )
    
    # 5. FUZZY MATCH NO TEXTO
    # IMPORTANTE: NÃO aplicar fuzzy match para refs compostas!
    if is_composite:
        # Para refs compostas, se chegou aqui é porque não encontrou match exato
        # NÃO tentar fuzzy match com a concatenação pois pode dar falsos positivos
        return ValidationResult(
            False, 0.0, MatchType.NO_MATCH, [],
            "Ref composta não encontrada (fuzzy desativado para compostas)"
        )
    
    # Para refs simples, continuar com fuzzy match
    text_codes = extract_alphanumeric_codes(page_text, min_length=5)
    best_match_score = 0.0
    best_match = None
    
    for text_code in text_codes:
        if len(text_code) >= 5:
            # Calcular similaridade
            common = sum(1 for c in our_main_ref if c in text_code)
            score = common / max(len(our_main_ref), len(text_code))
            
            # Para refs simples, também verificar se não é substring de algo maior
            # Isto evita match de "ABC123" com "ABC123XYZ789"
            if score > best_match_score:
                # Verificar se o match não é parte de um código maior
                len_diff = abs(len(our_main_ref) - len(text_code))
                if len_diff <= 3:  # Tolerância de 3 caracteres
                    best_match_score = score
                    best_match = text_code
                elif score >= 0.85:  # Se similaridade muito alta, aceitar mesmo com diferença de tamanho
                    best_match_score = score * 0.9  # Penalizar um pouco
                    best_match = text_code
    
    # Threshold mais rigoroso para evitar falsos positivos
    if best_match_score >= 0.75:  # Aumentado de 0.70 para 0.75
        confidence = 0.55 + (best_match_score * 0.20)  # Ajustado para dar menos confiança
        is_valid = confidence >= 0.70  # Threshold mais alto para validação
        return ValidationResult(
            is_valid, confidence, MatchType.FUZZY_MATCH, 
            [best_match] if best_match else [], 
            f"Match fuzzy: {best_match} (score: {best_match_score:.2f})"
        )
    
    return ValidationResult(False, best_match_score, MatchType.NO_MATCH, [], "Nenhum match válido")


def extract_codes_from_text(text: str, min_length: int = 4) -> List[str]:
    """
    Alias para extract_alphanumeric_codes.
    
    Args:
        text: Texto para extrair códigos
        min_length: Comprimento mínimo dos códigos
        
    Returns:
        Lista de códigos extraídos
    """
    return extract_alphanumeric_codes(text, min_length)


# ============================================================================
# TESTES
# ============================================================================

if __name__ == "__main__":
    print("=== Teste Validação v4.9.1 ===\n")
    
    # Simular dados de página
    page_identifiers = {
        "sku": ["71821AKN", "OTHERSKU"],
        "codes": ["71821AKN", "CODE123"]
    }
    page_url = "https://loja.com/product/71821akn"
    page_text = "Produto 71821AKN disponível. Código: 71821AKN. Outros: 71821AKNXYZ"
    
    # Teste 1: Ref simples
    print("Teste 1: Ref simples")
    result = validate_product_match(
        ["71821AKN"],
        page_identifiers,
        page_url,
        page_text
    )
    print(f"  Válido: {result.is_valid}, Confiança: {result.confidence:.2%}, Razão: {result.reason}\n")
    
    # Teste 2: Ref composta - apenas primeira parte presente
    print("Teste 2: Ref composta (71821AKN+71614MI) - só primeira parte")
    result = validate_product_match(
        ["71821AKN71614MI", "71821AKN", "71614MI"],  # Ref composta
        page_identifiers,
        page_url,
        page_text
    )
    print(f"  Válido: {result.is_valid}, Confiança: {result.confidence:.2%}, Razão: {result.reason}")
    print(f"  ✅ Correto: Deve ser FALSO (falta segunda parte)\n")
    
    # Teste 3: Ref composta - ambas partes presentes
    page_identifiers_complete = {
        "sku": ["71821AKN", "71614MI"],
        "codes": []
    }
    print("Teste 3: Ref composta - ambas partes presentes")
    result = validate_product_match(
        ["71821AKN71614MI", "71821AKN", "71614MI"],
        page_identifiers_complete,
        page_url,
        "Produto 71821AKN e 71614MI disponíveis"
    )
    print(f"  Válido: {result.is_valid}, Confiança: {result.confidence:.2%}, Razão: {result.reason}")
    print(f"  ✅ Correto: Deve ser VERDADEIRO (ambas partes presentes)\n")
    
    # Teste 4: Fuzzy match não deve funcionar para compostas
    print("Teste 4: Fuzzy match desativado para compostas")
    result = validate_product_match(
        ["ABC123DEF456", "ABC123", "DEF456"],
        {"sku": [], "codes": []},
        "https://loja.com/product",
        "Produto ABC123DEF456XYZ disponível"  # Similar mas não exato
    )
    print(f"  Válido: {result.is_valid}, Confiança: {result.confidence:.2%}, Razão: {result.reason}")
    print(f"  ✅ Correto: Deve ser FALSO (fuzzy desativado para compostas)")
