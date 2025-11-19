# -*- coding: utf-8 -*-
"""
app_streamlit.py - Comparador de Preços VERSÃO WEB
Interface web bonita com Streamlit
"""

import streamlit as st
import io
import tempfile
from pathlib import Path
from datetime import datetime

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
from selenium_utils_streamlit import build_driver

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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🏍️ Comparador de Preços</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">PM Motorparts - Comparação Multi-Loja Automática</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    st.subheader("🏪 Lojas")
    selected_stores = st.multiselect(
        "Seleciona as lojas",
        options=list(AVAILABLE_SCRAPERS.keys()),
        default=list(AVAILABLE_SCRAPERS.keys())
    )
    
    st.subheader("🎛️ Opções")
    
    max_products = st.number_input(
        "Limitar produtos",
        min_value=0,
        max_value=1000,
        value=0,
        help="0 = todos"
    )
    
    use_cache = st.checkbox("Usar cache", value=True)
    headless = st.checkbox("Modo invisível", value=True)

# Upload
st.header("📁 Upload do Feed XML")

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
    <p><strong>Comparador de Preços v4.6</strong> | PM Motorparts</p>
</div>
""", unsafe_allow_html=True)
