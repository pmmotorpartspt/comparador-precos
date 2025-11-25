# -*- coding: utf-8 -*-
"""
core/validation.py - Validação de produtos
v4.9.2 - NOVA CORREÇÃO: Rejeita kits quando procura ref simples
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
    
    v4.9.2: NOVA CORREÇÃO CRÍTICA
    - Se procuramos ref SIMPLES (ex: "110A26310")
    - Mas página tem ref COMPOSTA (ex: "110A26310+110A26385" - kit)
    - REJEITAR! Não queremos comparar preço individual com preço de kit
    
    v4.9.1: 
    - Corrigido para não aplicar fuzzy match em refs compostas
    
    Args:
        our_parts: Lista de partes da nossa ref 
                   Simples: ["110A26310"]
                   Composta: ["110A26310110A26385", "110A26310", "110A26385"]
        page_identifiers: Dict com SKUs e códigos extraídos da página
                         Exemplo: {"sku": ["110A26310+110A26385"], "codes": [...]}
        page_url: URL da página
        page_text: Texto completo da página
        
    Returns:
        ValidationResult com resultado da validação
    """
    if not our_parts:
        return ValidationResult(False, 0.0, MatchType.NO_MATCH, [], "Sem partes para validar")
    
    our_main_ref = our_parts[0]  # Ref completa concatenada
    is_composite = len(our_parts) > 2  # Se tem mais de 2 partes, é composta (ref completa + partes individuais)
    
    # Normalizar identificadores da página
    page_skus = [norm_token(s) for s in page_identifiers.get("sku", [])]
    page_codes = [norm_token(c) for c in page_identifiers.get("codes", [])]
    
    # =========================================================================
    # NOVA VALIDAÇÃO v4.9.2: REJEITAR KITS QUANDO PROCURAMOS REF SIMPLES
    # =========================================================================
    
    if not is_composite:  # NÓS procuramos ref SIMPLES
        # Verificar se página tem refs compostas (com +) que contenham a nossa ref
        
        # Verificar em CODES
        for code in page_identifiers.get("codes", []):
            if '+' in code:  # Página tem ref composta!
                # Normalizar e split por +
                code_norm = norm_token(code)
                parts_in_page = [p.strip() for p in code_norm.split('+') if p.strip()]
                
                # Verificar se nossa ref está dentro desta composta
                if our_main_ref in parts_in_page:
                    # ENCONTRÁMOS A NOSSA REF MAS É PARTE DE KIT!
                    return ValidationResult(
                        False, 0.4, MatchType.PARTIAL_MATCH, [],
                        f"Ref simples encontrada em kit {code} - rejeitado (não comparar peça com kit)"
                    )
        
        # Verificar em SKUs
        for sku in page_identifiers.get("sku", []):
            if '+' in sku:  # SKU é composto (kit)
                sku_norm = norm_token(sku)
                parts_in_sku = [p.strip() for p in sku_norm.split('+') if p.strip()]
                
                if our_main_ref in parts_in_sku:
                    # ENCONTRÁMOS A NOSSA REF MAS É PARTE DE KIT!
                    return ValidationResult(
                        False, 0.4, MatchType.PARTIAL_MATCH, [],
                        f"Ref simples encontrada em kit SKU {sku} - rejeitado (não comparar peça com kit)"
                    )
        
        # Verificar no URL (algumas lojas põem refs compostas no URL)
        url_normalized = norm_token(page_url)
        if '+' in page_url:  # URL tem +, pode ser ref composta
            # Extrair possíveis refs compostas do URL
            import re
            # Padrão: algo+algo (refs compostas no URL)
            composite_pattern = re.compile(r'([A-Z0-9]+\+[A-Z0-9]+)', re.I)
            url_composites = composite_pattern.findall(page_url)
            
            for url_comp in url_composites:
                url_comp_norm = norm_token(url_comp)
                parts_in_url = [p.strip() for p in url_comp_norm.split('+') if p.strip()]
                
                if our_main_ref in parts_in_url:
                    return ValidationResult(
                        False, 0.4, MatchType.PARTIAL_MATCH, [],
                        f"Ref simples encontrada em kit no URL {url_comp} - rejeitado"
                    )
    
    # =========================================================================
    # VALIDAÇÃO NORMAL (se passou o check acima)
    # =========================================================================
    
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
    print("=" * 70)
    print("TESTES DE VALIDAÇÃO v4.9.2")
    print("=" * 70)
    
    # Teste 1: Ref simples vs ref simples (deve aceitar)
    print("\n🧪 TESTE 1: Ref simples encontra ref simples")
    print("-" * 70)
    result = validate_product_match(
        our_parts=["110A26310"],  # Procuramos ref simples
        page_identifiers={
            "sku": ["110A26310"],  # Página tem ref simples
            "codes": ["110A26310", "BREMBO", "RCS19"]
        },
        page_url="https://loja.com/brembo-110a26310",
        page_text="Brembo 110A26310 RCS19"
    )
    print(f"Resultado: {'✅ ACEITA' if result.is_valid else '❌ REJEITA'}")
    print(f"Confiança: {result.confidence:.2f}")
    print(f"Tipo: {result.match_type.value}")
    print(f"Razão: {result.reason}")
    assert result.is_valid, "ERRO: Devia aceitar ref simples vs ref simples!"
    
    # Teste 2: Ref simples vs kit (deve REJEITAR) - NOVO v4.9.2
    print("\n🧪 TESTE 2: Ref simples encontra KIT (deve REJEITAR)")
    print("-" * 70)
    result = validate_product_match(
        our_parts=["110A26310"],  # Procuramos ref simples (bomba só)
        page_identifiers={
            "sku": ["110A26310+110A26385"],  # Página tem KIT (bomba + reservatório)
            "codes": ["110A26310+110A26385", "BREMBO", "KIT"]
        },
        page_url="https://loja.com/kit-110a26310-110a26385",
        page_text="Kit Brembo 110A26310+110A26385"
    )
    print(f"Resultado: {'✅ ACEITA' if result.is_valid else '❌ REJEITA'}")
    print(f"Confiança: {result.confidence:.2f}")
    print(f"Tipo: {result.match_type.value}")
    print(f"Razão: {result.reason}")
    assert not result.is_valid, "ERRO: Devia REJEITAR ref simples vs kit!"
    
    # Teste 3: Ref composta vs ref composta completa (deve aceitar)
    print("\n🧪 TESTE 3: Ref composta encontra ref composta completa")
    print("-" * 70)
    result = validate_product_match(
        our_parts=["110A26310110A26385", "110A26310", "110A26385"],  # Procuramos kit
        page_identifiers={
            "sku": ["110A26310+110A26385"],  # Página tem kit (ordem pode ser diferente)
            "codes": ["110A26310", "110A26385", "KIT"]
        },
        page_url="https://loja.com/kit",
        page_text="Kit 110A26310 e 110A26385"
    )
    print(f"Resultado: {'✅ ACEITA' if result.is_valid else '❌ REJEITA'}")
    print(f"Confiança: {result.confidence:.2f}")
    print(f"Tipo: {result.match_type.value}")
    print(f"Razão: {result.reason}")
    assert result.is_valid, "ERRO: Devia aceitar ref composta completa!"
    
    # Teste 4: Ref composta vs ref parcial (deve REJEITAR)
    print("\n🧪 TESTE 4: Ref composta encontra só UMA parte (deve REJEITAR)")
    print("-" * 70)
    result = validate_product_match(
        our_parts=["110A26310110A26385", "110A26310", "110A26385"],  # Procuramos kit
        page_identifiers={
            "sku": ["110A26310"],  # Página tem só primeira parte
            "codes": ["110A26310", "BREMBO"]
        },
        page_url="https://loja.com/110a26310",
        page_text="Brembo 110A26310"
    )
    print(f"Resultado: {'✅ ACEITA' if result.is_valid else '❌ REJEITA'}")
    print(f"Confiança: {result.confidence:.2f}")
    print(f"Tipo: {result.match_type.value}")
    print(f"Razão: {result.reason}")
    assert not result.is_valid, "ERRO: Devia REJEITAR ref composta incompleta!"
    
    # Teste 5: Ref simples vs kit no URL (deve REJEITAR)
    print("\n🧪 TESTE 5: Ref simples encontra kit no URL (deve REJEITAR)")
    print("-" * 70)
    result = validate_product_match(
        our_parts=["110A26310"],  # Procuramos ref simples
        page_identifiers={
            "sku": [],
            "codes": ["KIT", "BREMBO"]
        },
        page_url="https://loja.com/kit-110A26310+110A26385",  # Kit no URL
        page_text="Kit Brembo"
    )
    print(f"Resultado: {'✅ ACEITA' if result.is_valid else '❌ REJEITA'}")
    print(f"Confiança: {result.confidence:.2f}")
    print(f"Tipo: {result.match_type.value}")
    print(f"Razão: {result.reason}")
    assert not result.is_valid, "ERRO: Devia REJEITAR kit no URL!"
    
    print("\n" + "=" * 70)
    print("✅ ✅ ✅  TODOS OS TESTES PASSARAM!  ✅ ✅ ✅")
    print("=" * 70)
    print("\nv4.9.2 implementado com sucesso:")
    print("  ✅ Rejeita kits quando procura ref simples")
    print("  ✅ Aceita kits quando procura ref composta completa")
    print("  ✅ Rejeita refs compostas incompletas")
    print("  ✅ Detecta kits em SKU, codes e URL")
    print("=" * 70)
