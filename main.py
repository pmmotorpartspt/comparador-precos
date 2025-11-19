# -*- coding: utf-8 -*-
"""
main.py - Comparador de Preços Multi-Loja v4.1
FICHEIRO COMPLETO ATUALIZADO - Copia este ficheiro inteiro!

LOCALIZAÇÃO: main.py (raiz do projeto)
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FEED_PATH, EXCEL_OUTPUT, HEADLESS
from core.feed import parse_feed, feed_stats
from core.excel import build_excel
from core.selenium_utils import build_driver, get_rate_limiting_stats

from scrapers.wrs import WRSScraper
from scrapers.omniaracing import OmniaRacingScraper
from scrapers.genialmotor import GenialMotorScraper
from scrapers.jbsmotos import JBSMotosScraper
from scrapers.mmgracingstore import MMGRacingStoreScraper
from scrapers.emmoto import EMMotoScraper

AVAILABLE_SCRAPERS = {
    "wrs": WRSScraper,
    "omniaracing": OmniaRacingScraper,
    "genialmotor": GenialMotorScraper,
    "jbsmotos": JBSMotosScraper,
    "mmgracingstore": MMGRacingStoreScraper,
    "emmoto": EMMotoScraper,
}


def parse_args():
    """Parse argumentos da linha de comando"""
    
    parser = argparse.ArgumentParser(
        description="Comparador de Preços Multi-Loja",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  py main.py                              # Todas as lojas, todos os produtos
  py main.py --stores wrs                 # Só WRS
  py main.py --max 10                     # Primeiros 10 produtos
  py main.py --headful                    # Ver Chrome (para debug)
  py main.py --nocache                    # Ignorar cache completamente
  py main.py --refresh                    # Limpar e reconstruir cache
        """
    )
    
    parser.add_argument(
        "--stores",
        nargs="+",
        choices=list(AVAILABLE_SCRAPERS.keys()),
        default=list(AVAILABLE_SCRAPERS.keys()),
        help="Lojas a processar (padrão: todas)"
    )
    
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        metavar="N",
        help="Processar só os primeiros N produtos (0 = sem limite)"
    )
    
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Mostrar Chrome (útil para debug)"
    )
    
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--nocache",
        action="store_true",
        help="Ignorar cache completamente (força busca em tudo)"
    )
    cache_group.add_argument(
        "--refresh",
        action="store_true",
        help="Limpar cache e revalidar tudo"
    )
    
    return parser.parse_args()


def main():
    """Função principal"""
    
    args = parse_args()
    
    print("=" * 70)
    print("🔍 COMPARADOR DE PREÇOS MULTI-LOJA v4.1")
    print("=" * 70)
    
    use_cache = not args.nocache
    headless = not args.headful
    
    if args.refresh:
        use_cache = True
        print("\n⚠️  Modo REFRESH ativo: cache será limpo e revalidado")
    
    if not use_cache:
        print("\n⚠️  Cache DESATIVADO")
    
    print(f"\n📦 Feed: {FEED_PATH}")
    print(f"📊 Output: {EXCEL_OUTPUT}")
    print(f"🏪 Lojas: {', '.join(args.stores)}")
    print(f"🖥️  Chrome: {'Visível' if not headless else 'Invisível'}")
    
    # 1. CARREGAR FEED
    print("\n" + "-" * 70)
    print("📖 CARREGANDO FEED...")
    print("-" * 70)
    
    try:
        products = parse_feed(FEED_PATH, max_products=args.max)
    except Exception as e:
        print(f"\n❌ ERRO ao carregar feed: {e}")
        return 1
    
    if not products:
        print("\n❌ Nenhum produto válido encontrado no feed!")
        return 1
    
    stats = feed_stats(products)
    print(f"\n✅ {stats['total']} produtos carregados")
    print(f"   → Refs simples: {stats['simple']}")
    print(f"   → Refs compostas: {stats['composite']}")
    
    # 2. INICIALIZAR SCRAPERS
    print("\n" + "-" * 70)
    print("🔧 INICIALIZANDO SCRAPERS...")
    print("-" * 70)
    
    scrapers = {}
    for store_name in args.stores:
        scraper_class = AVAILABLE_SCRAPERS[store_name]
        scraper = scraper_class()
        
        if args.refresh:
            scraper.clear_cache()
            print(f"   🗑️  Cache de {store_name} limpo")
        
        scrapers[store_name] = scraper
    
    print(f"\n✅ {len(scrapers)} scrapers prontos")
    
    # 3. INICIALIZAR DRIVER SELENIUM
    print("\n" + "-" * 70)
    print("🌐 INICIALIZANDO CHROME...")
    print("-" * 70)
    
    try:
        driver = build_driver(headless=headless)
        print("✅ Chrome pronto")
    except Exception as e:
        print(f"\n❌ ERRO ao inicializar Chrome: {e}")
        return 1
    
    # 4. PROCESSAR PRODUTOS
    print("\n" + "-" * 70)
    print("🔍 PROCESSANDO PRODUTOS...")
    print("-" * 70)
    
    results_by_store = {name: {} for name in args.stores}
    
    try:
        for idx, product in enumerate(products, 1):
            print(f"\n[{idx:03d}/{len(products)}] {product.ref_raw}")
            print(f"           {product.title[:50]}...")
            
            for store_name, scraper in scrapers.items():
                try:
                    result = scraper.search_with_cache(
                        driver=driver,
                        ref_norm=product.ref_norm,
                        ref_parts=product.ref_parts,
                        ref_raw=product.ref_raw,  # ← CORRIGIDO! Mantém hífens
                        use_cache=use_cache
                    )
                    
                    if result:
                        results_by_store[store_name][product.ref_norm] = result.to_dict()
                        
                        emoji = "💾" if scraper.stats["cache_hits"] > scraper.stats["cache_misses"] else "🔍"
                        confidence = f"({result.confidence:.0%})" if result.confidence < 1.0 else ""
                        print(f"  {emoji} {store_name:12s} → {result.price_text:12s} {confidence}")
                    else:
                        results_by_store[store_name][product.ref_norm] = None
                        print(f"  ❌ {store_name:12s} → Não encontrado")
                
                except Exception as e:
                    print(f"  ⚠️  {store_name:12s} → Erro: {e}")
                    results_by_store[store_name][product.ref_norm] = None
    
    finally:
        print("\n" + "-" * 70)
        print("🔒 FINALIZANDO...")
        print("-" * 70)
        
        try:
            driver.quit()
            print("✅ Chrome fechado")
        except Exception:
            pass
        
        for scraper in scrapers.values():
            scraper.save_cache()
        print("✅ Caches salvos")
    
    # 5. GERAR EXCEL
    print("\n" + "-" * 70)
    print("📊 GERANDO EXCEL...")
    print("-" * 70)
    
    try:
        build_excel(
            products=products,
            store_names=list(scrapers.keys()),
            results_by_store=results_by_store,
            output_path=EXCEL_OUTPUT
        )
        print(f"✅ Excel gerado: {EXCEL_OUTPUT}")
    except Exception as e:
        print(f"\n❌ ERRO ao gerar Excel: {e}")
        return 1
    
    # 6. ESTATÍSTICAS FINAIS
    print("\n" + "=" * 70)
    print("📊 ESTATÍSTICAS FINAIS")
    print("=" * 70)
    
    for store_name, scraper in scrapers.items():
        stats = scraper.stats
        total = stats["total_searches"]
        found = stats["found"]
        not_found = stats["not_found"]
        cache_hits = stats["cache_hits"]
        cache_misses = stats["cache_misses"]
        
        print(f"\n{store_name.upper()}:")
        print(f"  Total buscas: {total}")
        print(f"  Encontrados: {found} ({found/total*100:.1f}%)" if total > 0 else "  Encontrados: 0")
        print(f"  Não encontrados: {not_found}")
        print(f"  Cache hits: {cache_hits}")
        print(f"  Cache misses: {cache_misses}")
        print(f"  Taxa cache: {cache_hits/(cache_hits+cache_misses)*100:.1f}%" if (cache_hits+cache_misses) > 0 else "  Taxa cache: N/A")
    
    rl_stats = get_rate_limiting_stats()
    print(f"\n🕒 RATE LIMITING:")
    print(f"  Min gap: {rl_stats['min_gap_seconds']:.1f}s")
    print(f"  Slow mode: {'SIM' if rl_stats['slow_mode'] else 'NÃO'}")
    print(f"  Taxa de falha recente: {rl_stats['recent_fail_rate']*100:.1f}%")
    print(f"  Janela de análise: {rl_stats['window_size']} requests")
    
    print("\n" + "=" * 70)
    print("✅ CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo utilizador (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
