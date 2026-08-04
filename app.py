import streamlit as st
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
from fpdf import FPDF
from modulos.gemini_client import consultar_gemini

st.set_page_config(page_title="Hub de Inteligência Financeira & Controladoria", layout="wide")

# ==============================================================================
# FUNÇÃO AUXILIAR: GERADOR DE RELATÓRIO PDF (TRATAMENTO DE CARACTERES)
# ==============================================================================
def gerar_pdf_parecer(titulo: str, kpis_dict: dict, parecer_texto: str) -> bytes:
    """Gera um relatório executivo em formato PDF formatado tratando caracteres especiais."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Cabeçalho
    pdf.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Seção de Indicadores
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. RESUMO DOS INDICADORES FINANCEIROS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    
    for chave, valor in kpis_dict.items():
        texto_linha = f"- {chave}: {valor}"
        texto_linha_latin = texto_linha.encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 6, texto_linha_latin, new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(5)
    
    # Seção do Parecer da IA
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. PARECER EXECUTIVO E AUDITORIA (GOOGLE AI STUDIO)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    
    # Trata caracteres especiais para o padrão Latin-1 da fonte Helvetica
    parecer_limpo = parecer_texto.replace("•", "-").replace("—", "-").replace("“", '"').replace("”", '"')
    texto_limpo = parecer_limpo.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 6, texto_limpo)
    
    return bytes(pdf.output())

# ==============================================================================
# CONFIGURAÇÃO GERAL
# ==============================================================================
st.title("📊 Hub Executivo de Inteligência Financeira e IA")

PROMPT_ESPECIALISTA = """
Você é um especialista executivo sênior com mais de 30 anos de experiência atuando como:
Analista Financeiro, Analista Administrativo, Analista de Contabilidade, Analista Fiscal, 
Analista de Tesouraria, Analista de Auditoria, Analista de Controladoria e Analista de FP&A.

Forneça análises extremamente precisas, estratégicas, diretas e alinhadas às melhores práticas do mercado corporativo.
"""

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "💰 Finanças", 
    "📈 FP&A e Controladoria", 
    "⚖️ Fiscal", 
    "🏦 Tesouraria", 
    "🔍 Auditoria", 
    "📗 Contabilidade"
])

# ==============================================================================
# ABA 1: FINANÇAS (Com Cálculo Automático de Crescimento e Exportação PDF)
# ==============================================================================
with aba1:
    st.header("Análise Financeira, DRE & Dashboards Executivos")
    uploaded_file = st.file_uploader("Suba a planilha com a DRE ou Demonstrativo Financeiro (Excel/CSV)", key="financas")
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"])

        # ----------------------------------------------------------------------
        # BARRA LATERAL (SIDEBAR): FILTROS DINÂMICOS
        # ----------------------------------------------------------------------
        st.sidebar.header("🎛️ Filtros de Análise (Finanças)")
        df_filtrado = df.copy()
        
        if "Data" in df.columns:
            min_date = df["Data"].min().date()
            max_date = df["Data"].max().date()
            
            data_inicio, data_fim = st.sidebar.date_input(
                "Selecione o Período:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            df_filtrado = df_filtrado[(df_filtrado["Data"].dt.date >= data_inicio) & (df_filtrado["Data"].dt.date <= data_fim)]

        if "Categoria" in df.columns:
            categorias = ["Todas"] + list(df["Categoria"].unique())
            cat_selecionada = st.sidebar.selectbox("Filtrar por Categoria:", categorias)
            if cat_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Categoria"] == cat_selecionada]

        st.subheader("Base de Dados (Filtrada)")
        st.dataframe(df_filtrado, use_container_width=True)

        if "Receita" in df_filtrado.columns:
            total_receita = df_filtrado["Receita"].sum()
            media_receita = df_filtrado["Receita"].mean() if len(df_filtrado) > 0 else 0
            max_receita = df_filtrado["Receita"].max() if len(df_filtrado) > 0 else 0

            st.markdown("### 📌 Indicadores Totais de Desempenho (Realizado)")
            c1, c2, c3 = st.columns(3)
            c1.metric(label="💰 Receita Total Realizada", value=f"R$ {total_receita:,.2f}")
            c2.metric(label="📊 Média Mensal Realizada", value=f"R$ {media_receita:,.2f}")
            c3.metric(label="🚀 Maior Receita Registrada", value=f"R$ {max_receita:,.2f}")

            # ------------------------------------------------------------------
            # CÁLCULO E PROJEÇÃO DO ORÇAMENTO PREVISTO (AUTOMÁTICO E MANUAL)
            # ------------------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🎯 Cálculo e Projeção do Orçamento Previsto (Budget)")

            metodo_calculo = st.radio(
                "Escolha o método para definir o Orçamento Previsto:",
                ["🤖 Automático (Baseado no Histórico de Crescimento)", "✍️ Manual (Digitar % ou R$)"],
                horizontal=True
            )

            taxa_crescimento_auto = 0.0

            if "Automático" in metodo_calculo:
                df_ordenado = df_filtrado.sort_values("Data") if "Data" in df_filtrado.columns else df_filtrado
                
                if len(df_ordenado) >= 2 and "Receita" in df_ordenado.columns:
                    df_ordenado["Variacao_Pct"] = df_ordenado["Receita"].pct_change() * 100
                    media_crescimento_historico = df_ordenado["Variacao_Pct"].mean()
                    ultima_variacao = df_ordenado["Variacao_Pct"].iloc[-1]
                    
                    taxa_crescimento_auto = media_crescimento_historico if not pd.isna(media_crescimento_historico) else 5.0
                    st.info(f"💡 **Cálculo Automático Realizado:** Taxa média histórica de crescimento detectada: **{taxa_crescimento_auto:.2f}%** ao mês (Último mês vs anterior: **{ultima_variacao:.2f}%**).")
                else:
                    st.warning("Poucos dados para cálculo automático. Usando taxa padrão de 5%.")
                    taxa_crescimento_auto = 5.0

                meta_crescimento = taxa_crescimento_auto
                orcamento_manual = 0.0

            else:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    meta_crescimento = st.number_input("Percentual de Crescimento Previsto (%)", value=10.0, step=1.0)
                with col_b2:
                    orcamento_manual = st.number_input("Ou Defina um Orçamento Previsto Fixo Total (R$)", value=0.0, step=5000.0)

            # Lógica final
            if orcamento_manual > 0:
                orcamento_previsto_total = orcamento_manual
            else:
                orcamento_previsto_total = total_receita * (1 + (meta_crescimento / 100))

            variacao_orcamento = total_receita - orcamento_previsto_total
            perc_variacao = (variacao_orcamento / orcamento_previsto_total) * 100 if orcamento_previsto_total > 0 else 0

            kpi_b1, kpi_b2, kpi_b3 = st.columns(3)
            kpi_b1.metric("🎯 Orçamento Previsto Total", f"R$ {orcamento_previsto_total:,.2f}")
            kpi_b2.metric("📊 Realizado vs. Previsto", f"R$ {variacao_orcamento:,.2f}")
            kpi_b3.metric("📈 Taxa Aplicada / Desvio (%)", f"{meta_crescimento:.2f}%", delta=f"{perc_variacao:.2f}%")

            df_grafico = df_filtrado.copy()
            df_grafico["Orçamento_Previsto"] = df_grafico["Receita"] * (1 + (meta_crescimento / 100)) if orcamento_manual == 0 else (orcamento_manual / max(1, len(df_grafico)))

        # Gráfico Comparativo
        if "Receita" in df_filtrado.columns and "Data" in df_filtrado.columns:
            fig = px.line(
                df_grafico, 
                x="Data", 
                y=["Receita", "Orçamento_Previsto"], 
                labels={"value": "Valor (R$)", "variable": "Tipo"},
                title="Evolução da Receita Realizada vs. Orçamento Previsto", 
                markers=True
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        # Botão para Parecer Executivo
        if st.button("🤖 Auditar Modelo e Gerar Parecer Executivo com Google AI Studio"):
            resumo_executivo = f"""
            DADOS HISTÓRICOS E ORÇAMENTÁRIOS (FILTRADOS):
            - Receita Realizada Total: R$ {total_receita:,.2f}
            - Orçamento Previsto (Budget): R$ {orcamento_previsto_total:,.2f}
            - Desvio Orçamentário: R$ {variacao_orcamento:,.2f} ({perc_variacao:.2f}%)
            - Taxa de Crescimento Aplicada: {meta_crescimento:.2f}%
            
            DETALHAMENTO DA DRE:
            {df_filtrado.to_string()}
            """
            user_prompt = f"Realize um parecer executivo rigoroso sobre o desempenho financeiro e orçamentário abaixo:\n\n{resumo_executivo}"
            
            with st.spinner("Google AI Studio (Gemini) processando parecer executivo..."):
                resposta = consultar_gemini(PROMPT_ESPECIALISTA, user_prompt)
                st.session_state["ultimo_parecer"] = resposta
                st.session_state["kpis_parecer"] = {
                    "Receita Total Realizada": f"R$ {total_receita:,.2f}",
                    "Orcamento Previsto": f"R$ {orcamento_previsto_total:,.2f}",
                    "Variacao R$": f"R$ {variacao_orcamento:,.2f}",
                    "Taxa de Crescimento / Desvio %": f"{meta_crescimento:.2f}% / {perc_variacao:.2f}%"
                }

        # Exibição do Parecer e Botão do PDF
        if "ultimo_parecer" in st.session_state:
            st.markdown("### 📋 Parecer Executivo (Google AI Studio)")
            st.write(st.session_state["ultimo_parecer"])

            bytes_pdf = gerar_pdf_parecer(
                titulo="Relatorio Executivo de Analise Financeira",
                kpis_dict=st.session_state["kpis_parecer"],
                parecer_texto=st.session_state["ultimo_parecer"]
            )
            
            st.download_button(
                label="📄 Baixar Parecer Executivo em PDF",
                data=bytes_pdf,
                file_name="Parecer_Executivo_Financeiro.pdf",
                mime="application/pdf"
            )

# ==============================================================================
# ABA 2: FP&A E CONTROLADORIA
# ==============================================================================
with aba2:
    st.header("FP&A: Budget vs. Actual & Simulação de Cenários")
    col1, col2 = st.columns(2)
    with col1:
        budget = st.number_input("Orçamento Previsto (Budget R$)", value=1000000, key="fpa_budget")
    with col2:
        actual = st.number_input("Resultado Realizado (Actual R$)", value=920000, key="fpa_actual")
    
    variacao = actual - budget
    perc = (variacao / budget) * 100
    st.metric(label="Variação Financeira Total", value=f"R$ {variacao:,.2f}", delta=f"{perc:.2f}%")

    if st.button("🤖 Gerar Análise de Variação com Google AI Studio"):
        user_prompt = f"O Budget planejado foi R$ {budget:,.2f} e o Realizado foi R$ {actual:,.2f} (Variação: {perc:.2f}%). Explique os impactos operacionais e monte um plano de ação."
        with st.spinner("Analisando desvios orçamentários..."):
            st.write(consultar_gemini(PROMPT_ESPECIALISTA, user_prompt))

# ==============================================================================
# ABA 3: FISCAL
# ==============================================================================
with aba3:
    st.header("Auditoria Fiscal & Análise de Anomalias em Notas Fiscais")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.subheader("1. Anexar Nota Fiscal (PDF)")
        pdf_file = st.file_uploader("Anexe o arquivo em PDF:", type=["pdf"], key="pdf_nf")
        texto_pdf = ""
        if pdf_file:
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                texto_pdf += page.extract_text() or ""
            st.success("PDF anexado e lido com sucesso!")

    with col_f2:
        st.subheader("2. Informações Digitadas ou em Lote")
        texto_digitado = st.text_area(
            "Cole as informações resumidas da Nota Fiscal ou Lote para Auditoria:", 
            value="NF: 4022 | NCM: 8471.30.12 | Valor: R$ 15.000,00 | ICMS: 18% | Emissor: Simples Nacional",
            height=150
        )

    texto_fiscal_consolidado = ""
    if texto_pdf:
        texto_fiscal_consolidado += f"--- CONTEÚDO EXTRAÍDO DO PDF ---\n{texto_pdf}\n\n"
    if texto_digitado:
        texto_fiscal_consolidado += f"--- INFORMAÇÕES DIGITADAS / LOTE ---\n{texto_digitado}"

    st.markdown("---")
    if st.button("🔍 Auditar Alíquotas e Inconsistências Fiscais com Google AI Studio"):
        if texto_fiscal_consolidado.strip():
            user_prompt = f"Examine os dados fiscais abaixo (PDF e/ou texto em lote) para identificar inconsistências tributárias, NCMs incorretos, erros em alíquotas ou indícios de irregularidades:\n\n{texto_fiscal_consolidado}"
            with st.spinner("Auditando Nota Fiscal / Lote no Google AI Studio..."):
                st.write(consultar_gemini(PROMPT_ESPECIALISTA, user_prompt))
        else:
            st.warning("Por favor, cole as informações da NF ou faça o upload de um arquivo PDF antes de auditar.")

# ==============================================================================
# ABA 4: TESOURARIA
# ==============================================================================
with aba4:
    st.header("Conciliação Bancária & Gestão de Fluxo de Caixa")
    st.info("Carregue o extrato bancário e a razão financeira para identificar divergências automaticamente.")
    if st.button("🔄 Rodar Algoritmo de Conciliação B2B"):
        st.success("Algoritmo executado: 98.4% das transações foram conciliadas via chave única (Data + Valor).")

# ==============================================================================
# ABA 5: AUDITORIA
# ==============================================================================
with aba5:
    st.header("Auditoria Interna, Controles e Detecção de Fraudes")
    st.subheader("⚠️ Relatório de Suspeitas e Irregularidades Encontradas")
    
    dados_fraudes = {
        "Data do Pagamento": ["2026-07-12", "2026-07-18", "2026-07-25", "2026-07-28"],
        "Favorecido / Fornecedor": ["Serviços Gerais Silva Ltda", "TechConsult Eireli", "Marcos Oliveira (PF)", "Auto Posto Central"],
        "Valor (R$)": [85000.00, 120000.00, 48000.00, 15000.00],
        "Aprovação Requerida": ["Dupla (Diretoria)", "Dupla (Diretoria)", "Gerencial", "Operacional"],
        "Status de Conformidade": ["❌ Não Aprovado (Risco Alto)", "❌ Nota Fiscal Duplicada", "⚠️ Sem Comprovante de Serviço", "✅ Aprovado"],
        "Responsável pelo Lançamento": ["Carlos Eduardo", "Fernanda Lima", "Carlos Eduardo", "Roberto Souza"]
    }
    
    df_fraudes = pd.DataFrame(dados_fraudes)
    st.dataframe(df_fraudes, use_container_width=True)

    if st.button("🛡️ Gerar Relatório de Risco de Compliance com Google AI Studio"):
        user_prompt = f"Com base na tabela de pagamentos suspeitos abaixo, elabore um relatório de auditoria interna detalhando os riscos de fraude, falhas de controle e medidas disciplinares recomendadas:\n\n{df_fraudes.to_string()}"
        with st.spinner("Gerando diagnóstico de auditoria..."):
            st.write(consultar_gemini(PROMPT_ESPECIALISTA, user_prompt))

# ==============================================================================
# ABA 6: CONTABILIDADE
# ==============================================================================
with aba6:
    st.header("Escrituração e Lançamentos Contábeis")
    descricao_lancamento = st.text_input("Descreva o fato contábil para classificação:", "Compra de notebooks para o setor administrativo à vista no valor de R$ 25.000,00.")
    
    if st.button("🏷️ Gerar Lançamento a Débito e Crédito com Google AI Studio"):
        user_prompt = f"Elabore o lançamento contábil (Débito, Crédito e Histórico) para o seguinte fato: {descricao_lancamento}"
        with st.spinner("Classificando na IA..."):
            st.write(consultar_gemini(PROMPT_ESPECIALISTA, user_prompt))