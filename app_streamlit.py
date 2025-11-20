# -*- coding: utf-8 -*-
"""
app_streamlit.py - Comparador de Preços VERSÃO WEB v4.8.3
v4.8.3: Session state FUNCIONAL + Downloads simples (sem auto-download JS)
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
    .download-highlight {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
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
    
    st.subheader("🔧 Opções")
    use_cache = st.toggle("Usar cache (21 dias)", value=True, help="Cache acelera buscas repetidas")
    headless = st.toggle("Modo headless", value=True, help="Navegador invisível (mais rápido)")


# ============================================================================
# MODO 1: BUSCA RÁPIDA - COM SESSION STATE SIMPLIFICADO
# ============================================================================

if modo == "🔍 Busca Rápida (1 Ref)":
    st.header("🔍 Busca Rápida de Referência")
    
    # 🆕 Inicializar session state (SEMPRE primeiro)
    if 'busca_resultados' not in st.session_state:
        st.session_state.busca_resultados = None
        st.session_state.busca_excel = None
        st.session_state.busca_filename = None
    
    # 🆕 MOSTRAR RESULTADOS GUARDADOS (se existirem)
    if st.session_state.busca_resultados is not None:
        st.divider()
        
        # Título destaque
        st.success("✅ **Resultados da Última Busca**")
        
        results = st.session_state.busca_resultados
        
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
            st.metric("Lojas Pesquisadas", len(results))
        with col2:
            st.metric("Encontrado em", found_count)
        with col3:
            if found_count > 0:
                st.metric("Taxa Sucesso", f"{found_count/len(results)*100:.0f}%")
        
        # 🎯 DOWNLOAD SIMPLES (sem JavaScript)
        if found_count > 0 and st.session_state.busca_excel:
            st.divider()
            
            # Destaque visual
            st.markdown('<div class="download-highlight">', unsafe_allow_html=True)
            st.markdown("### 📥 Ficheiro Excel Pronto!")
            st.markdown("**Clica no botão abaixo para descarregar**")
            
            st.download_button(
                label="📥 DOWNLOAD EXCEL",
                data=st.session_state.busca_excel,
                file_name=st.session_state.busca_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão nova busca
        st.divider()
        if st.button("🔄 Nova Busca", use_container_width=True):
            st.session_state.busca_resultados = None
            st.session_state.busca_excel = None
            st.session_state.busca_filename = None
            st.rerun()
        
        st.stop()  # Parar aqui para não mostrar form de busca
    
    # FORMULÁRIO DE BUSCA (só aparece se não há resultados)
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
            
            # 💾 GUARDAR EM SESSION STATE
            st.session_state.busca_resultados = results
            
            # 🆕 GERAR EXCEL e GUARDAR
            found_count = sum(1 for r in results if r["Preço"] != "Não encontrado" and not r["Preço"].startswith("Erro"))
            
            if found_count > 0:
                from core.excel import create_single_ref_excel
                
                excel_buffer = create_single_ref_excel(
                    ref=ref_input.strip(),
                    ref_norm=ref_norm,
                    your_price=your_price,
                    store_names=selected_stores,
                    results=results
                )
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"busca_{ref_norm}_{timestamp}.xlsx"
                
                st.session_state.busca_excel = excel_buffer.getvalue()
                st.session_state.busca_filename = filename
            
            # RERUN para mostrar resultados (com download)
            st.rerun()


# ============================================================================
# MODO 2: COMPARAÇÃO COMPLETA (FEED XML) - REF-POR-REF + SESSION STATE
# ============================================================================

else:  # Modo Comparação Completa
    st.header("📁 Upload do Feed XML")
    
    # Inicializar session state
    if 'comp_historico' not in st.session_state:
        st.session_state.comp_historico = []
    if 'comp_excel' not in st.session_state:
        st.session_state.comp_excel = None
    if 'comp_filename' not in st.session_state:
        st.session_state.comp_filename = None
    if 'comp_processando' not in st.session_state:
        st.session_state.comp_processando = False
    
    # 🆕 MOSTRAR RESULTADOS GUARDADOS (se existirem)
    if st.session_state.comp_historico and not st.session_state.comp_processando:
        st.divider()
        
        st.success("✅ **Processamento Concluído!**")
        
        # Histórico
        with st.expander("📝 Histórico do Processamento", expanded=True):
            for item in st.session_state.comp_historico:
                st.text(item)
        
        # 🎯 DOWNLOAD SIMPLES
        if st.session_state.comp_excel:
            st.divider()
            
            # Destaque visual
            st.markdown('<div class="download-highlight">', unsafe_allow_html=True)
            st.markdown("### 📥 Ficheiro Excel Completo Pronto!")
            st.markdown(f"**{len(st.session_state.comp_historico)} referências processadas**")
            
            st.download_button(
                label="📥 DOWNLOAD EXCEL COMPLETO",
                data=st.session_state.comp_excel,
                file_name=st.session_state.comp_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Botão nova comparação
        st.divider()
        if st.button("🔄 Nova Comparação", use_container_width=True):
            st.session_state.comp_historico = []
            st.session_state.comp_excel = None
            st.session_state.comp_filename = None
            st.session_state.comp_processando = False
            st.rerun()
        
        st.stop()  # Parar aqui
    
    # FORMULÁRIO DE UPLOAD (só aparece se não há resultados)
    uploaded_file = st.file_uploader(
        "Arrasta o ficheiro feed.xml aqui",
        type=['xml']
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Ficheiro: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        try:
            # Guardar ficheiro temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = Path(tmp_file.name)
            
            # Parse feed
            with st.spinner("📖 A ler feed XML..."):
                all_products = parse_feed(tmp_path)
                
                if not all_products:
                    st.error("❌ Nenhum produto válido!")
                    st.stop()
                
                st.success(f"✅ {len(all_products)} produtos encontrados no feed")
            
            # 🆕 SELETOR DE REFS
            st.divider()
            st.subheader("📋 Selecionar Produtos")
            
            st.warning(f"⚠️ **Limite:** 10 refs por execução (evitar timeout ~10-15 min)")
            
            # Opções de seleção
            ref_selection = st.radio(
                "Produtos a processar:",
                [
                    "Primeiros 10",
                    "Refs 11-20",
                    "Refs 21-30",
                    "Refs 31-40",
                    "Custom (escolher refs específicas)"
                ],
                help="Escolhe quais produtos processar (máximo 10 de cada vez)"
            )
            
            # Determinar produtos selecionados
            products = []
            
            if ref_selection == "Primeiros 10":
                products = all_products[:10]
            elif ref_selection == "Refs 11-20":
                products = all_products[10:20]
            elif ref_selection == "Refs 21-30":
                products = all_products[20:30]
            elif ref_selection == "Refs 31-40":
                products = all_products[30:40]
            elif ref_selection == "Custom (escolher refs específicas)":
                # Input manual
                st.info("💡 **Exemplo:** 1,5,10,25,33 (usa números de 1 a " + str(len(all_products)) + ")")
                custom_input = st.text_input(
                    "Números das refs (separados por vírgula):",
                    placeholder="1,5,10,25,33"
                )
                
                if custom_input.strip():
                    try:
                        # Parse dos números
                        indices = [int(x.strip()) - 1 for x in custom_input.split(",")]
                        
                        # Validar
                        invalid = [i+1 for i in indices if i < 0 or i >= len(all_products)]
                        if invalid:
                            st.error(f"❌ Números inválidos: {invalid}")
                            st.stop()
                        
                        if len(indices) > 10:
                            st.error(f"❌ Máximo 10 refs! Tens {len(indices)}")
                            st.stop()
                        
                        # Selecionar produtos
                        products = [all_products[i] for i in indices]
                        
                    except ValueError:
                        st.error("❌ Formato inválido! Usa números separados por vírgula (ex: 1,5,10)")
                        st.stop()
            
            # Mostrar seleção
            if products:
                st.info(f"📌 **{len(products)} produtos selecionados** para processamento")
                
                with st.expander("🔍 Ver produtos selecionados"):
                    for idx, p in enumerate(products, 1):
                        st.text(f"{idx}. {p.ref_raw} - {p.title[:60]}")
            else:
                st.warning("⚠️ Escolhe refs custom ou usa outra opção")
                st.stop()
            
            st.divider()
            
            # Botão iniciar
            if st.button("🚀 Comparar Preços", type="primary", use_container_width=True):
                
                if not selected_stores:
                    st.error("⚠️ Seleciona pelo menos uma loja!")
                    st.stop()
                
                # Limpar histórico anterior
                st.session_state.comp_historico = []
                st.session_state.comp_processando = True
                
                # Criar driver
                with st.spinner("🌐 A iniciar navegador..."):
                    driver = build_driver(headless=headless)
                
                # Criar scrapers
                scrapers = {}
                for store_name in selected_stores:
                    scraper_class = AVAILABLE_SCRAPERS[store_name]
                    scrapers[store_name.lower().replace(" ", "")] = scraper_class()
                
                # 🆕 PROCESSAR REF-POR-REF (não loja-por-loja)
                st.divider()
                st.header("⚙️ Processamento")
                
                # Criar Excel builder
                builder = ExcelBuilder(list(scrapers.keys()))
                builder._create_headers()
                
                # Progress containers
                overall_progress = st.progress(0)
                overall_status = st.empty()
                
                # Container para download parcial
                download_container = st.empty()
                
                # Processar cada REF (loop externo)
                for ref_idx, product in enumerate(products):
                    
                    # Update overall progress
                    progress_pct = (ref_idx + 1) / len(products)
                    overall_progress.progress(progress_pct)
                    overall_status.info(f"📦 Produto {ref_idx + 1}/{len(products)}: **{product.ref_raw}** - {product.title[:50]}")
                    
                    # Container para progresso desta ref
                    ref_progress = st.expander(f"🔍 Ref {ref_idx + 1}: {product.ref_raw}", expanded=(ref_idx == len(products) - 1))
                    
                    with ref_progress:
                        store_progress_bar = st.progress(0)
                        store_status = st.empty()
                        
                        # Resultados desta ref em todas as lojas
                        product_results = {}
                        
                        # Processar cada LOJA para esta ref (loop interno)
                        for store_idx, (store_key, scraper) in enumerate(scrapers.items()):
                            
                            # Update progress
                            store_pct = (store_idx + 1) / len(scrapers)
                            store_progress_bar.progress(store_pct)
                            
                            # Nome display
                            store_display = [k for k, v in AVAILABLE_SCRAPERS.items() if k.lower().replace(" ", "") == store_key][0]
                            store_status.text(f"🏪 {store_display}... ({store_idx + 1}/{len(scrapers)})")
                            
                            try:
                                result = scraper.search_with_cache(
                                    driver=driver,
                                    ref_norm=product.ref_norm,
                                    ref_parts=product.ref_parts,
                                    ref_raw=product.ref_raw,
                                    use_cache=use_cache
                                )
                                
                                if result:
                                    product_results[store_key] = result.to_dict()
                                else:
                                    product_results[store_key] = None
                                    
                            except Exception as e:
                                product_results[store_key] = None
                                st.warning(f"⚠️ Erro em {store_display}: {str(e)[:50]}")
                        
                        store_status.success(f"✅ Ref completa! Encontrado em {sum(1 for r in product_results.values() if r)} lojas")
                    
                    # 🆕 CHECKPOINT: Adicionar produto ao Excel
                    builder.add_product(product, product_results)
                    
                    # HISTÓRICO
                    found = sum(1 for r in product_results.values() if r)
                    total = len(product_results)
                    hist_line = f"✅ Ref {ref_idx + 1}: {product.ref_raw} ({found}/{total} lojas)"
                    st.session_state.comp_historico.append(hist_line)
                    
                    # 🆕 DOWNLOAD PARCIAL sempre disponível
                    if ref_idx >= 0:  # Sempre (mesmo após 1ª ref)
                        partial_buffer = builder.to_buffer()
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"comparador_parcial_{ref_idx + 1}refs_{timestamp}.xlsx"
                        
                        with download_container.container():
                            st.success(f"💾 **{ref_idx + 1}/{len(products)} refs processadas**")
                            st.download_button(
                                label=f"📥 Download Parcial ({ref_idx + 1}/{len(products)} refs)",
                                data=partial_buffer,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"partial_{ref_idx}",
                                use_container_width=True,
                                help="Descarrega progresso atual (cada linha tem todas as lojas)"
                            )
                
                # Fechar driver
                driver.quit()
                
                # 💾 GUARDAR EXCEL FINAL
                final_buffer = builder.to_buffer()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_filename = f"comparador_{timestamp}.xlsx"
                
                st.session_state.comp_excel = final_buffer.getvalue()
                st.session_state.comp_filename = final_filename
                st.session_state.comp_processando = False
                
                # Cleanup
                tmp_path.unlink()
                
                # RERUN para mostrar histórico + download
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Erro: {e}")
            import traceback
            with st.expander("🔍 Detalhes"):
                st.code(traceback.format_exc())

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Comparador de Preços v4.8.3</strong> | PM Motorparts</p>
    <p style='font-size: 0.9rem;'>✅ Session State Funcional | 📥 Downloads Simples</p>
</div>
""", unsafe_allow_html=True)
