# -*- coding: utf-8 -*-
"""
app_streamlit.py - Comparador de Preços VERSÃO WEB v2
Interface web com:
1. Modo Completo (Feed XML)
2. Modo Busca Rápida (Ref Individual)
"""

import streamlit as st
import io
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configurar página (tem de ser a primeira chamada Streamlit)
st.set_page_config(
    page_title="Comparador de Preços - PM Motorparts",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports do projeto
from core.feed import parse_feed
from core.excel import ExcelBuilder
from core.selenium_utils import build_driver
from core.normalization import normalize_reference

from scrapers.wrs import WRSScraper
from scrapers.omniaracing import OmniaRacingScraper
from scrapers.genialmotor import GenialMotorScraper
from scrapers.jbsmotos import JBSMotosScraper
from scrapers.mmgracingstore import MMGRacingStoreScraper
from scrapers.emmoto import EMMotoScraper

AVAILABLE_SCRAPERS = {
    "WRS": WRSScraper,
    "OmniaRacing": OmniaRacingScraper,
    "GenialMotor": GenialMotorScraper,
    "JBS Motos": JBSMotosScraper,
    "MMG Racing": MMGRacingStoreScraper,
    "EM Moto": EMMotoScraper,
}

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .quick-result {
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .result-found {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .result-not-found {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🏍️ Comparador de Preços</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">PM Motorparts - Comparação Multi-Loja Automática</div>', unsafe_allow_html=True)

# Sidebar - Modo de Operação
with st.sidebar:
    st.header("⚙️ Configurações")
    
    modo = st.radio(
        "Modo de Operação",
        ["🔍 Busca Rápida (1 Ref)", "📊 Comparação Completa (Feed XML)"],
        help="Busca Rápida: procura 1 ref em tempo real\nComparação Completa: processa feed XML completo"
    )
    
    st.divider()
    
    st.subheader("🏪 Lojas")
    selected_stores = st.multiselect(
        "Seleciona as lojas",
        options=list(AVAILABLE_SCRAPERS.keys()),
        default=list(AVAILABLE_SCRAPERS.keys())
    )
    
    st.divider()
    
    st.subheader("🎛️ Opções")
    use_cache = st.checkbox("Usar cache", value=True)
    headless = st.checkbox("Modo invisível", value=True)

# ============================================================================
# MODO 1: BUSCA RÁPIDA (1 REF)
# ============================================================================

if modo == "🔍 Busca Rápida (1 Ref)":
    st.header("🔍 Busca Rápida de Referência")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ref_input = st.text_input(
            "Referência do Produto",
            placeholder="Ex: 07BB37LA, P-HF1595, H.085.LR1X",
            help="Cola a referência que queres pesquisar"
        )
    
    with col2:
        your_price = st.number_input(
            "Teu Preço (opcional)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            help="Para calcular diferenças"
        )
    
    if st.button("🚀 Buscar Agora", type="primary", use_container_width=True):
        
        if not ref_input or not ref_input.strip():
            st.error("⚠️ Introduz uma referência!")
        elif not selected_stores:
            st.error("⚠️ Seleciona pelo menos uma loja!")
        else:
            # Normalizar ref
            ref_norm, ref_parts = normalize_reference(ref_input.strip())
            
            st.info(f"🔎 A procurar: **{ref_input}** (normalizado: {ref_norm})")
            
            # Criar driver
            with st.spinner("🌐 A iniciar navegador..."):
                driver = build_driver(headless=headless)
            
            # Criar scrapers
            scrapers = {}
            for store_name in selected_stores:
                scraper_class = AVAILABLE_SCRAPERS[store_name]
                scrapers[store_name] = scraper_class()
            
            # Buscar em cada loja
            results = []
            
            progress_bar = st.progress(0)
            
            for idx, (store_name, scraper) in enumerate(scrapers.items()):
                progress = (idx + 1) / len(scrapers)
                progress_bar.progress(progress)
                
                with st.status(f"🏪 {store_name}...", expanded=False) as status:
                    try:
                        result = scraper.search_with_cache(
                            driver=driver,
                            ref_norm=ref_norm,
                            ref_parts=ref_parts,
                            ref_raw=ref_input.strip(),
                            use_cache=use_cache
                        )
                        
                        if result:
                            # Calcular diferença se preço fornecido
                            diff_pct = None
                            diff_text = ""
                            if your_price > 0 and result.price_num:
                                diff_pct = ((result.price_num - your_price) / your_price) * 100
                                if diff_pct > 0:
                                    diff_text = f"+{diff_pct:.1f}% 🟢"
                                else:
                                    diff_text = f"{diff_pct:.1f}% 🔴"
                            
                            results.append({
                                "Loja": store_name,
                                "Preço": result.price_text,
                                "Diferença": diff_text if diff_text else "—",
                                "Confiança": f"{result.confidence:.0%}",
                                "URL": result.url
                            })
                            status.update(label=f"✅ {store_name}", state="complete")
                        else:
                            results.append({
                                "Loja": store_name,
                                "Preço": "Não encontrado",
                                "Diferença": "—",
                                "Confiança": "—",
                                "URL": "—"
                            })
                            status.update(label=f"❌ {store_name}", state="error")
                    
                    except Exception as e:
                        results.append({
                            "Loja": store_name,
                            "Preço": f"Erro: {str(e)[:50]}",
                            "Diferença": "—",
                            "Confiança": "—",
                            "URL": "—"
                        })
                        status.update(label=f"⚠️ {store_name}", state="error")
            
            driver.quit()
            progress_bar.empty()
            
            # Mostrar resultados
            st.divider()
            st.subheader("📊 Resultados")
            
            # Criar DataFrame
            df = pd.DataFrame(results)
            
            # Mostrar tabela
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Estatísticas rápidas
            found_count = sum(1 for r in results if r["Preço"] != "Não encontrado" and not r["Preço"].startswith("Erro"))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lojas Pesquisadas", len(scrapers))
            with col2:
                st.metric("Encontrado em", found_count)
            with col3:
                if found_count > 0:
                    st.metric("Taxa Sucesso", f"{found_count/len(scrapers)*100:.0f}%")

# ============================================================================
# MODO 2: COMPARAÇÃO COMPLETA (FEED XML)
# ============================================================================

else:  # Modo Comparação Completa
    st.header("📁 Upload do Feed XML")
    
    max_products = st.number_input(
        "Limitar produtos (0 = todos)",
        min_value=0,
        max_value=1000,
        value=0,
        help="Útil para testar com poucos produtos"
    )
    
    uploaded_file = st.file_uploader(
        "Arrasta o ficheiro feed.xml aqui",
        type=['xml']
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Ficheiro: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        if st.button("🚀 Comparar Preços", type="primary", use_container_width=True):
            
            if not selected_stores:
                st.error("⚠️ Seleciona pelo menos uma loja!")
            else:
                try:
                    # Guardar ficheiro temporário
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = Path(tmp_file.name)
                    
                    # Parse feed
                    with st.spinner("📖 A ler feed XML..."):
                        products = parse_feed(tmp_path)
                        
                        if not products:
                            st.error("❌ Nenhum produto válido!")
                            st.stop()
                        
                        st.success(f"✅ {len(products)} produtos encontrados")
                    
                    # Limitar
                    if max_products > 0 and max_products < len(products):
                        products = products[:max_products]
                        st.info(f"ℹ️ Limitado a {max_products} produtos")
                    
                    # Criar driver
                    with st.spinner("🌐 A iniciar navegador..."):
                        driver = build_driver(headless=headless)
                    
                    # Criar scrapers
                    scrapers = {}
                    for store_name in selected_stores:
                        scraper_class = AVAILABLE_SCRAPERS[store_name]
                        scrapers[store_name.lower().replace(" ", "")] = scraper_class()
                    
                    # Processar lojas
                    results_by_store = {}
                    
                    for store_display_name in selected_stores:
                        store_key = store_display_name.lower().replace(" ", "")
                        scraper = scrapers[store_key]
                        
                        st.subheader(f"🏪 {store_display_name}")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        store_results = {}
                        
                        for idx, product in enumerate(products):
                            progress = (idx + 1) / len(products)
                            progress_bar.progress(progress)
                            status_text.text(f"{idx + 1}/{len(products)}: {product.title[:50]}...")
                            
                            result = scraper.search_with_cache(
                                driver=driver,
                                ref_norm=product.ref_norm,
                                ref_parts=product.ref_parts,
                                ref_raw=product.ref_raw,
                                use_cache=use_cache
                            )
                            
                            if result:
                                store_results[product.ref_norm] = result.to_dict()
                        
                        # Stats
                        stats = scraper.stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Buscas", stats['total_searches'])
                        with col2:
                            found = stats['found']
                            total = stats['total_searches']
                            st.metric("Encontrados", f"{found} ({found/total*100:.1f}%)" if total > 0 else "0")
                        with col3:
                            st.metric("Cache", stats['cache_hits'])
                        
                        results_by_store[store_key] = store_results
                        st.divider()
                    
                    driver.quit()
                    
                    # Gerar Excel
                    with st.spinner("📊 A gerar Excel..."):
                        excel_buffer = io.BytesIO()
                        
                        # Criar Excel builder
                        builder = ExcelBuilder(list(scrapers.keys()))
                        
                        # Adicionar produtos
                        for product in products:
                            results = {}
                            for store_key in scrapers.keys():
                                if product.ref_norm in results_by_store.get(store_key, {}):
                                    results[store_key] = results_by_store[store_key][product.ref_norm]
                            
                            builder.add_product(product, results)
                        
                        # Salvar para stream
                        builder.wb.save(excel_buffer)
                        excel_buffer.seek(0)
                    
                    st.success("🎉 Comparação concluída!")
                    
                    # Download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comparador_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=excel_buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                    
                    tmp_path.unlink()
                    
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
                    import traceback
                    with st.expander("🔍 Detalhes"):
                        st.code(traceback.format_exc())

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Comparador de Preços v4.7</strong> | PM Motorparts</p>
    <p style='font-size: 0.9rem;'>🔍 Busca Rápida | 📊 Análise Completa</p>
</div>
""", unsafe_allow_html=True)
