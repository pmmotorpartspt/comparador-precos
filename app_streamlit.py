# -*- coding: utf-8 -*-
"""
app_streamlit.py - Comparador de Preços v4.9.0
Versão corrigida com session state robusto e sistema de checkpoints
Pedro - PM Motorparts
"""

import streamlit as st
import io
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import traceback

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Comparador de Preços - PM Motorparts",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# IMPORTS DO PROJETO
# ============================================================================

from core.feed import parse_feed
from core.excel import ExcelBuilder, create_single_ref_excel
from core.selenium_utils import build_driver
from core.normalization import normalize_reference

from scrapers.wrs import WRSScraper
from scrapers.omniaracing import OmniaRacingScraper
from scrapers.genialmotor import GenialMotorScraper
from scrapers.jbsmotos import JBSMotosScraper
from scrapers.mmgracingstore import MMGRacingStoreScraper
from scrapers.emmoto import EMMotoScraper

# ============================================================================
# CONSTANTES
# ============================================================================

AVAILABLE_SCRAPERS = {
    "WRS": WRSScraper,
    "OmniaRacing": OmniaRacingScraper,
    "GenialMotor": GenialMotorScraper,
    "JBS Motos": JBSMotosScraper,
    "MMG Racing": MMGRacingStoreScraper,
    "EM Moto": EMMotoScraper,
}

# ============================================================================
# INICIALIZAÇÃO DO SESSION STATE
# ============================================================================

# Inicializar TODAS as variáveis de session state no início
if 'busca_resultados' not in st.session_state:
    st.session_state.busca_resultados = None
    
if 'busca_excel' not in st.session_state:
    st.session_state.busca_excel = None
    
if 'busca_ref' not in st.session_state:
    st.session_state.busca_ref = None

if 'comp_produtos' not in st.session_state:
    st.session_state.comp_produtos = []
    
if 'comp_historico' not in st.session_state:
    st.session_state.comp_historico = []
    
if 'comp_excel_buffer' not in st.session_state:
    st.session_state.comp_excel_buffer = None
    
if 'comp_processando' not in st.session_state:
    st.session_state.comp_processando = False
    
if 'comp_progresso' not in st.session_state:
    st.session_state.comp_progresso = 0

if 'comp_builder' not in st.session_state:
    st.session_state.comp_builder = None

# ============================================================================
# CSS CUSTOMIZADO
# ============================================================================

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
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER PRINCIPAL
# ============================================================================

st.markdown('<div class="main-header">🏍️ Comparador de Preços</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">PM Motorparts - Comparação Multi-Loja Automática v4.9.0</div>', 
            unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - CONFIGURAÇÕES
# ============================================================================

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
        default=list(AVAILABLE_SCRAPERS.keys()),
        help="Seleciona as lojas onde queres pesquisar preços"
    )
    
    st.divider()
    
    st.subheader("🔧 Opções")
    use_cache = st.toggle("Usar cache (21 dias)", value=True, 
                          help="Cache evita pesquisas repetidas e acelera o processo")
    headless = st.toggle("Modo headless", value=True,
                        help="Executar navegador em background (mais rápido)")
    
    st.divider()
    
    # Info sobre versão
    st.info("""
    **v4.9.0 - Melhorias:**
    - ✅ Session state robusto
    - ✅ Sistema de checkpoints
    - ✅ Download durante processamento
    - ✅ Recuperação automática
    """)


# ============================================================================
# MODO 1: BUSCA RÁPIDA
# ============================================================================

if modo == "🔍 Busca Rápida (1 Ref)":
    st.header("🔍 Busca Rápida de Referência")
    
    # Verificar se há resultados guardados
    if st.session_state.busca_excel is not None:
        st.success("✅ **Última busca disponível**")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.info(f"📦 Referência: **{st.session_state.busca_ref}**")
        with col2:
            st.download_button(
                label="📥 Download Excel",
                data=st.session_state.busca_excel,
                file_name=f"busca_{st.session_state.busca_ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        with col3:
            if st.button("🔄 Nova Busca", type="secondary"):
                st.session_state.busca_resultados = None
                st.session_state.busca_excel = None
                st.session_state.busca_ref = None
                st.rerun()
        
        # Mostrar resultados guardados
        if st.session_state.busca_resultados:
            st.divider()
            st.subheader("📊 Resultados da Última Busca")
            df = pd.DataFrame(st.session_state.busca_resultados)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Estatísticas
            found_count = sum(1 for r in st.session_state.busca_resultados 
                            if r["Preço"] != "Não encontrado" and not r["Preço"].startswith("Erro"))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lojas Pesquisadas", len(st.session_state.busca_resultados))
            with col2:
                st.metric("Encontrado em", found_count)
            with col3:
                if found_count > 0:
                    st.metric("Taxa Sucesso", f"{found_count/len(st.session_state.busca_resultados)*100:.0f}%")
        
        st.stop()  # Parar aqui se há resultados guardados
    
    # Formulário de busca
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ref_input = st.text_input(
            "Referência do Produto",
            placeholder="Ex: 07BB37LA, P-HF1595, H.085.LR1X",
            help="Introduz a referência exata do produto"
        )
    
    with col2:
        your_price = st.number_input(
            "Teu Preço (opcional)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            help="Para comparar com a concorrência"
        )
    
    if st.button("🚀 Buscar Agora", type="primary", use_container_width=True):
        
        # Validações
        if not ref_input or not ref_input.strip():
            st.error("⚠️ Introduz uma referência!")
        elif not selected_stores:
            st.error("⚠️ Seleciona pelo menos uma loja!")
        else:
            try:
                # Iniciar busca
                with st.spinner("🌐 A iniciar navegador..."):
                    driver = build_driver(headless=headless)
                
                # Normalizar referência
                ref_norm, _ = normalize_reference(ref_input.strip())
                ref_parts = ref_norm.replace("-", "").lower()
                
                st.divider()
                st.subheader("🔍 A pesquisar...")
                
                # Containers para progresso
                results = []
                progress_bar = st.progress(0)
                status_container = st.container()
                
                # Criar scrapers
                scrapers = {}
                for store_name in selected_stores:
                    scraper_class = AVAILABLE_SCRAPERS[store_name]
                    scrapers[store_name] = scraper_class()
                
                # Processar cada loja
                for idx, (store_name, scraper) in enumerate(scrapers.items()):
                    progress = (idx + 1) / len(scrapers)
                    progress_bar.progress(progress)
                    
                    with status_container:
                        status_msg = st.info(f"🏪 A pesquisar em **{store_name}**...")
                        
                        try:
                            result = scraper.search_with_cache(
                                driver=driver,
                                ref_norm=ref_norm,
                                ref_parts=ref_parts,
                                ref_raw=ref_input.strip(),
                                use_cache=use_cache
                            )
                            
                            if result and result.price_num is not None:
                                # Calcular diferença se tiver preço próprio
                                price_diff = ""
                                if your_price > 0:
                                    try:
                                        diff = float(result.price_num) - your_price
                                        price_diff = f"{diff:+.2f}€"
                                    except:
                                        price_diff = "—"
                                
                                results.append({
                                    "Loja": store_name,
                                    "Preço": f"{result.price_num:.2f}€",
                                    "Diferença": price_diff,
                                    "Confiança": f"{result.confidence:.0%}" if result.confidence else "—",
                                    "URL": result.url
                                })
                                status_msg.success(f"✅ **{store_name}** - Encontrado!")
                            else:
                                results.append({
                                    "Loja": store_name,
                                    "Preço": "Não encontrado",
                                    "Diferença": "—",
                                    "Confiança": "—",
                                    "URL": "—"
                                })
                                status_msg.warning(f"❌ **{store_name}** - Não encontrado")
                        
                        except Exception as e:
                            results.append({
                                "Loja": store_name,
                                "Preço": f"Erro: {str(e)[:30]}",
                                "Diferença": "—",
                                "Confiança": "—",
                                "URL": "—"
                            })
                            status_msg.error(f"⚠️ **{store_name}** - Erro: {str(e)[:30]}")
                
                # Fechar navegador
                driver.quit()
                progress_bar.empty()
                
                # Guardar resultados no session state
                st.session_state.busca_resultados = results
                st.session_state.busca_ref = ref_norm
                
                # Criar Excel
                excel_buffer = create_single_ref_excel(
                    ref=ref_input.strip(),
                    ref_norm=ref_norm,
                    your_price=your_price,
                    store_names=selected_stores,
                    results=results
                )
                st.session_state.busca_excel = excel_buffer.getvalue()
                
                # Forçar atualização da página para mostrar resultados
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erro crítico: {str(e)}")
                with st.expander("🔍 Detalhes do erro"):
                    st.code(traceback.format_exc())


# ============================================================================
# MODO 2: COMPARAÇÃO COMPLETA
# ============================================================================

else:  # "📊 Comparação Completa (Feed XML)"
    st.header("📊 Comparação Completa - Feed XML")
    
    # Verificar se há processamento guardado
    if st.session_state.comp_excel_buffer is not None:
        st.success("✅ **Comparação disponível para download**")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.info(f"📦 Processadas **{len(st.session_state.comp_historico)}** referências")
        with col2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Download Excel",
                data=st.session_state.comp_excel_buffer,
                file_name=f"comparador_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        with col3:
            if st.button("🔄 Nova Comparação", type="secondary"):
                # Limpar session state
                st.session_state.comp_produtos = []
                st.session_state.comp_historico = []
                st.session_state.comp_excel_buffer = None
                st.session_state.comp_processando = False
                st.session_state.comp_progresso = 0
                st.session_state.comp_builder = None
                st.rerun()
        
        # Mostrar histórico
        if st.session_state.comp_historico:
            with st.expander("📋 Histórico de Processamento", expanded=True):
                for linha in st.session_state.comp_historico:
                    st.text(linha)
        
        st.stop()  # Parar aqui se há resultados guardados
    
    # Upload do ficheiro
    st.subheader("📁 Upload do Feed XML")
    
    uploaded_file = st.file_uploader(
        "Arrasta o ficheiro feed.xml aqui",
        type=['xml'],
        help="Ficheiro XML com os produtos para comparar"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Ficheiro: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        try:
            # Guardar temporariamente
            tmp_path = Path(tempfile.gettempdir()) / f"feed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            tmp_path.write_bytes(uploaded_file.read())
            
            # Parse feed
            with st.spinner("📖 A ler feed XML..."):
                all_products = parse_feed(tmp_path)
            
            st.info(f"✅ Feed lido: **{len(all_products)} produtos encontrados**")
            
            # Preview produtos
            with st.expander("🔍 Ver produtos do feed", expanded=False):
                for idx, p in enumerate(all_products[:20], 1):
                    st.text(f"{idx}. {p.ref_raw} - {p.title[:60]}")
                if len(all_products) > 20:
                    st.text(f"... + {len(all_products) - 20} produtos")
            
            st.divider()
            
            # Seleção de refs
            st.subheader("📌 Escolhe as Refs para Processar")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.warning("⚠️ **Máximo 10 refs por processamento** (evita timeout)")
            with col2:
                st.info(f"📊 Total disponível: {len(all_products)} refs")
            
            ref_selection = st.selectbox(
                "Escolhe o grupo de referências",
                [
                    "Primeiros 10",
                    "Refs 11-20",
                    "Refs 21-30",
                    "Refs 31-40",
                    "Refs 41-50",
                    "Custom (escolher refs específicas)"
                ],
                help="Processa até 10 refs de cada vez"
            )
            
            # Determinar produtos selecionados
            products = []
            
            if ref_selection == "Primeiros 10":
                products = all_products[:10]
            elif ref_selection == "Refs 11-20":
                products = all_products[10:20] if len(all_products) > 10 else []
            elif ref_selection == "Refs 21-30":
                products = all_products[20:30] if len(all_products) > 20 else []
            elif ref_selection == "Refs 31-40":
                products = all_products[30:40] if len(all_products) > 30 else []
            elif ref_selection == "Refs 41-50":
                products = all_products[40:50] if len(all_products) > 40 else []
            elif ref_selection == "Custom (escolher refs específicas)":
                st.info("💡 **Exemplo:** 1,5,10,25,33 (usa números de 1 a " + str(len(all_products)) + ")")
                custom_input = st.text_input(
                    "Números das refs (separados por vírgula):",
                    placeholder="1,5,10,25,33",
                    help="Máximo 10 referências"
                )
                
                if custom_input.strip():
                    try:
                        indices = [int(x.strip()) - 1 for x in custom_input.split(",")]
                        
                        # Validar índices
                        invalid = [i+1 for i in indices if i < 0 or i >= len(all_products)]
                        if invalid:
                            st.error(f"❌ Números inválidos: {invalid}")
                            st.stop()
                        
                        if len(indices) > 10:
                            st.error(f"❌ Máximo 10 refs! Selecionaste {len(indices)}")
                            st.stop()
                        
                        products = [all_products[i] for i in indices]
                        
                    except ValueError:
                        st.error("❌ Formato inválido! Usa números separados por vírgula")
                        st.stop()
            
            # Mostrar seleção
            if products:
                st.success(f"📌 **{len(products)} produtos selecionados** para processamento")
                
                with st.expander("🔍 Ver produtos selecionados", expanded=True):
                    for idx, p in enumerate(products, 1):
                        st.text(f"{idx}. {p.ref_raw} - {p.title[:60]}")
            else:
                if ref_selection != "Custom (escolher refs específicas)":
                    st.warning("⚠️ Não há produtos neste intervalo")
                st.stop()
            
            st.divider()
            
            # Botão iniciar comparação
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                start_button = st.button(
                    "🚀 Iniciar Comparação", 
                    type="primary", 
                    use_container_width=True,
                    disabled=not selected_stores or not products
                )
            
            if start_button:
                if not selected_stores:
                    st.error("⚠️ Seleciona pelo menos uma loja!")
                    st.stop()
                
                # Guardar produtos no session state
                st.session_state.comp_produtos = products
                st.session_state.comp_processando = True
                st.session_state.comp_historico = []
                
                # Container principal de processamento
                process_container = st.container()
                
                with process_container:
                    st.divider()
                    st.header("⚙️ Processamento em Curso")
                    
                    # Criar driver
                    with st.spinner("🌐 A iniciar navegador..."):
                        driver = build_driver(headless=headless)
                    
                    # Criar scrapers
                    scrapers = {}
                    for store_name in selected_stores:
                        scraper_class = AVAILABLE_SCRAPERS[store_name]
                        scrapers[store_name.lower().replace(" ", "")] = scraper_class()
                    
                    # Criar Excel builder
                    builder = ExcelBuilder(list(scrapers.keys()))
                    builder._create_headers()
                    st.session_state.comp_builder = builder
                    
                    # Progress containers
                    overall_progress = st.progress(0)
                    overall_status = st.empty()
                    
                    # Container para download parcial
                    download_container = st.container()
                    
                    # Histórico visual
                    historico_container = st.container()
                    
                    # Processar cada REF (ref-por-ref, não loja-por-loja)
                    for ref_idx, product in enumerate(products):
                        
                        # Update overall progress
                        progress_pct = (ref_idx + 1) / len(products)
                        overall_progress.progress(progress_pct)
                        overall_status.info(
                            f"📦 Produto {ref_idx + 1}/{len(products)}: **{product.ref_raw}** - {product.title[:50]}"
                        )
                        
                        # Container para esta ref
                        with st.expander(f"🔍 Ref {ref_idx + 1}: {product.ref_raw}", 
                                       expanded=(ref_idx == 0)):  # Expandir só a primeira
                            
                            store_progress = st.progress(0)
                            store_status = st.empty()
                            results_text = st.empty()
                            
                            # Resultados desta ref
                            product_results = {}
                            successful_stores = []
                            
                            # Processar cada LOJA para esta REF
                            for store_idx, (store_key, scraper) in enumerate(scrapers.items()):
                                
                                store_pct = (store_idx + 1) / len(scrapers)
                                store_progress.progress(store_pct)
                                
                                # Nome da loja para display
                                store_display = [k for k, v in AVAILABLE_SCRAPERS.items() 
                                               if k.lower().replace(" ", "") == store_key][0]
                                
                                store_status.text(f"🏪 A pesquisar em {store_display}... ({store_idx + 1}/{len(scrapers)})")
                                
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
                                        successful_stores.append(store_display)
                                    else:
                                        product_results[store_key] = None
                                        
                                except Exception as e:
                                    product_results[store_key] = None
                                    st.warning(f"⚠️ Erro em {store_display}: {str(e)[:50]}")
                            
                            # Mostrar resultado desta ref
                            found = len(successful_stores)
                            total = len(scrapers)
                            
                            if found > 0:
                                store_status.success(
                                    f"✅ Ref completa! Encontrado em {found}/{total} lojas: " + 
                                    ", ".join(successful_stores)
                                )
                            else:
                                store_status.warning(f"❌ Não encontrado em nenhuma loja")
                        
                        # Adicionar produto ao Excel
                        builder.add_product(product, product_results)
                        
                        # Atualizar histórico
                        found = sum(1 for r in product_results.values() if r)
                        total = len(product_results)
                        hist_line = f"✅ Ref {ref_idx + 1}: {product.ref_raw} - {product.title[:40]} ({found}/{total} lojas)"
                        st.session_state.comp_historico.append(hist_line)
                        
                        # Guardar Excel parcial no session state
                        partial_buffer = builder.to_buffer()
                        st.session_state.comp_excel_buffer = partial_buffer.getvalue()
                        
                        # Mostrar botão de download parcial
                        with download_container:
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.info(f"💾 **{ref_idx + 1} de {len(products)}** refs processadas")
                            with col2:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                st.download_button(
                                    label=f"📥 Download Parcial ({ref_idx + 1}/{len(products)})",
                                    data=st.session_state.comp_excel_buffer,
                                    file_name=f"comparador_parcial_{timestamp}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"partial_download_{ref_idx}"
                                )
                    
                    # Fechar driver
                    driver.quit()
                    
                    # Processamento completo
                    overall_progress.progress(1.0)
                    overall_status.success(f"✅ **Comparação Completa!** {len(products)} refs processadas")
                    
                    # Marcar como não processando
                    st.session_state.comp_processando = False
                    st.session_state.comp_progresso = 100
                    
                    # Forçar rerun para mostrar resultado final
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Erro crítico: {str(e)}")
            with st.expander("🔍 Detalhes do erro"):
                st.code(traceback.format_exc())
            
            # Limpar estado em caso de erro
            st.session_state.comp_processando = False
            
            # Cleanup do ficheiro temporário se existir
            try:
                if 'tmp_path' in locals() and tmp_path.exists():
                    tmp_path.unlink()
            except:
                pass


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Comparador de Preços v4.9.0</strong> | PM Motorparts</p>
    <p style='font-size: 0.9rem;'>✅ Session State Robusto | ✅ Sistema de Checkpoints | ✅ Download Parcial</p>
    <p style='font-size: 0.8rem;'>Desenvolvido para Pedro - Otimizado para Streamlit Cloud</p>
</div>
""", unsafe_allow_html=True)
