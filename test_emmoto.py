# -*- coding: utf-8 -*-
"""
test_emmoto.py - Script de Teste Rápido para EM Moto

Uso:
  python test_emmoto.py H.094.L4K
  python test_emmoto.py P-HF1595
"""

import sys
from pathlib import Path

# Adicionar pasta do projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.emmoto import EMMotoScraper
from core.selenium_utils import build_driver
from core.normalization import normalize_reference


def test_scraper(ref: str):
    """
    Testa o scraper da EM Moto com uma referência específica
    
    Args:
        ref: Referência a pesquisar (ex: "H.094.L4K")
    """
    print("=" * 70)
    print(f"🧪 TESTE DO SCRAPER EM MOTO")
    print(f"🔍 Referência: {ref}")
    print("=" * 70)
    
    # Normalizar referência
    ref_parts, ref_raw = normalize_reference(ref)
    print(f"\n✅ Normalização:")
    print(f"   Partes: {ref_parts}")
    print(f"   Raw: {ref_raw}")
    
    # Criar scraper
    scraper = EMMotoScraper()
    print(f"\n✅ Scraper criado: {scraper.name}")
    print(f"   URL base: {scraper.base_url}")
    
    # Criar driver (Chrome visível para debug)
    print(f"\n🌐 Iniciando Chrome...")
    driver = build_driver(headless=False)  # Visível para debug
    
    try:
        # Executar pesquisa
        print(f"\n🔎 Iniciando pesquisa...")
        print("-" * 70)
        
        result = scraper.search_product(
            driver=driver,
            ref_parts=ref_parts,
            ref_raw=ref_raw
        )
        
        print("-" * 70)
        
        # Mostrar resultado
        if result:
            print(f"\n✅ PRODUTO ENCONTRADO!")
            print(f"   💰 Preço: {result.price_text}")
            print(f"   💯 Confiança: {result.confidence:.2f}")
            print(f"   🔗 URL: {result.url}")
            print(f"   📝 Razão: {result.validation.reason}")
            
            # Mostrar estatísticas do scraper
            print(f"\n📊 Estatísticas:")
            for key, value in scraper.stats.items():
                print(f"   {key}: {value}")
            
            return True
        else:
            print(f"\n❌ PRODUTO NÃO ENCONTRADO")
            print(f"   Possíveis razões:")
            print(f"   - Produto não existe na loja")
            print(f"   - Referência incorreta")
            print(f"   - Site bloqueou o acesso")
            
            # Mostrar estatísticas do scraper
            print(f"\n📊 Estatísticas:")
            for key, value in scraper.stats.items():
                print(f"   {key}: {value}")
            
            return False
    
    except Exception as e:
        print(f"\n❌ ERRO DURANTE O TESTE:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"\n🔚 Fechando Chrome...")
        driver.quit()
        print(f"✅ Teste concluído!")
        print("=" * 70)


def main():
    """Função principal do script de teste"""
    if len(sys.argv) < 2:
        print("Uso: python test_emmoto.py <REFERENCIA>")
        print("\nExemplos:")
        print("  python test_emmoto.py H.094.L4K")
        print("  python test_emmoto.py P-HF1595")
        print("  python test_emmoto.py H085LR1X")
        sys.exit(1)
    
    ref = sys.argv[1]
    success = test_scraper(ref)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
