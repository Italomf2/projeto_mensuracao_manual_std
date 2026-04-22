# ============================================================
# DASHBOARD MANUAL SANTANDER – RECUPERAÇÃO DE CRÉDITO
# Autor: Planejamento Call Center
# Ferramenta: Python + Pandas + Streamlit
#
# COMO RODAR:
#   streamlit run dashboard_manual_santander.py
#
# DEPENDÊNCIAS:
#   pip install streamlit pandas openpyxl plotly
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DA PÁGINA (deve ser o PRIMEIRO comando Streamlit)
# ============================================================
st.set_page_config(
    page_title="Dashboard Manual – Santander",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ESTILO VISUAL CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
    /* Fundo escuro profissional */
    .stApp { background-color: #0f1117; color: #e0e0e0; }

    /* Cabeçalho principal */
    .titulo-principal {
        font-size: 26px; font-weight: 800;
        color: #EC0000; letter-spacing: 1px;
        border-bottom: 2px solid #EC0000;
        padding-bottom: 8px; margin-bottom: 20px;
    }

    /* Cartões de KPI */
    .kpi-card {
        background: #1c1f2e;
        border-left: 4px solid #EC0000;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }
    .kpi-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #ffffff; }
    .kpi-sub   { font-size: 13px; color: #aaa; margin-top: 4px; }

    /* Tabelas */
    .dataframe th { background-color: #1c1f2e !important; color: #EC0000 !important; }
    .dataframe td { background-color: #161925 !important; color: #e0e0e0 !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #161925; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# ➊ CONFIGURAÇÃO DO ARQUIVO DE DADOS
# ============================================================
# ⚠️ ALTERE AQUI O CAMINHO DO ARQUIVO A CADA MÊS:
#   - Pode ser um diretório de rede: r"\\servidor\pasta\BASE_MANUAL_MAIO_2026.xlsx"
#   - Ou um caminho local
CAMINHO_ARQUIVO = "https://docs.google.com/spreadsheets/d/1hT-yz_kGjKu4FMpzE11_b8bq1YwbYobH/export?format=xlsx"
# ⚠️ A CADA MÊS: substitua o ID do Drive (parte entre /d/ e /export) pelo do novo arquivo

# ============================================================
# ➋ LEITURA DOS DADOS
# ============================================================
@st.cache_data(show_spinner="Carregando base de dados...", ttl=3600)
def carregar_dados(caminho: str) -> pd.DataFrame:
    """
    Lê o arquivo .xlsx – funciona tanto com caminho local quanto com URL do Google Drive.
    ttl=3600 significa que o cache expira em 1h, forçando releitura automática.
    """
    import io, requests
    if caminho.startswith("http"):
        # Baixa o arquivo da URL (Google Drive público) para a memória
        resposta = requests.get(caminho, timeout=60)
        resposta.raise_for_status()
        df = pd.read_excel(io.BytesIO(resposta.content), dtype={"CPF/CNPJ_TRAT.": str})
    else:
        df = pd.read_excel(caminho, dtype={"CPF/CNPJ_TRAT.": str})

    # Garante que DATA_REFERENCIA seja do tipo data para ordenação correta
    df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], dayfirst=True)

    # Campos numéricos que devem ser zero quando NaN
    cols_numericas = ["ACIONAMENTO","ATENDIDO","ALÔ","CPC","PROPOSTA","TENTATIVA U.","ACIONADO $","SOMA CONTABIL","SOMA DIVIDA"]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# Tenta carregar – mostra erro amigável se arquivo não existir
try:
    df_raw = carregar_dados(CAMINHO_ARQUIVO)
except Exception as e:
    st.error(f"❌ Não foi possível carregar o arquivo.\n\nVerifique se o link do Google Drive está correto e com acesso público.\n\nDetalhe: {e}")
    st.stop()

# ============================================================
# ➌ SIDEBAR – FILTROS PRINCIPAIS
# ============================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b8/Banco_Santander_Logotipo.svg", width=180)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔎 Filtros")

# ── FILTRO DE DATA: slider de intervalo ──────────────────────
# Pega todas as datas únicas ordenadas do arquivo
datas_disponiveis = sorted(df_raw["DATA_REFERENCIA"].dt.date.unique())

# Slider com dois pontos: data inicial e data final do período desejado
# Por padrão: seleciona do primeiro ao último dia disponível
idx_inicio, idx_fim = st.sidebar.select_slider(
    "📅 Período de Referência",
    options=datas_disponiveis,                          # cada ponto é uma data real do arquivo
    value=(datas_disponiveis[0], datas_disponiveis[-1]),# padrão: período completo
    format_func=lambda d: d.strftime("%d/%m/%Y"),       # exibe no formato brasileiro
)

# Converte as datas escolhidas para Timestamp para comparar com a coluna do DataFrame
data_inicio = pd.Timestamp(idx_inicio)
data_fim    = pd.Timestamp(idx_fim)

# Rótulo legível para o cabeçalho do dashboard
periodo_label = f"{idx_inicio.strftime('%d/%m/%Y')} → {idx_fim.strftime('%d/%m/%Y')}"

# ── FILTRO SEGMENTO: multiselect (vários ao mesmo tempo) ─────
lista_segmentos = sorted(df_raw["SEGMENTO"].dropna().unique().tolist())
segmento_filtro = st.sidebar.multiselect(
    "👥 Segmento",
    options=lista_segmentos,
    default=lista_segmentos,   # começa com todos selecionados
)
# Se o usuário desmarcar tudo, volta a mostrar todos (evita tela vazia)
if not segmento_filtro:
    segmento_filtro = lista_segmentos

# ── FILTRO MACRO: multiselect ─────────────────────────────────
lista_macros = sorted(df_raw["MACRO"].dropna().unique().tolist())
macro_filtro = st.sidebar.multiselect(
    "🗺️ Macro Região",
    options=lista_macros,
    default=lista_macros,
)
if not macro_filtro:
    macro_filtro = lista_macros

# ── FILTRO TIPO: multiselect ──────────────────────────────────
lista_tipos = sorted(df_raw["TIPO"].dropna().unique().tolist())
tipo_filtro = st.sidebar.multiselect(
    "🏢 Tipo (PF/PJ)",
    options=lista_tipos,
    default=lista_tipos,
)
if not tipo_filtro:
    tipo_filtro = lista_tipos

# ── FILTRO OPERADOR: multiselect ──────────────────────────────
lista_operadores = sorted(df_raw["OPERADOR"].dropna().unique().tolist())
operador_filtro = st.sidebar.multiselect(
    "🧑‍💼 Operador",
    options=lista_operadores,
    default=lista_operadores,
)
if not operador_filtro:
    operador_filtro = lista_operadores

st.sidebar.markdown("---")
st.sidebar.caption("⚡ Para atualizar os dados, clique em 'Clear cache' ou reinicie o app após rodar o fluxo Alteryx.")

# ============================================================
# ➍ FILTRAGEM DOS DADOS
# ============================================================
# Filtra pelo INTERVALO DE DATAS selecionado no slider
# e pelos valores selecionados em cada multiselect
df_dia = df_raw[
    (df_raw["DATA_REFERENCIA"] >= data_inicio) &
    (df_raw["DATA_REFERENCIA"] <= data_fim) &
    (df_raw["SEGMENTO"].isin(segmento_filtro)) &
    (df_raw["MACRO"].isin(macro_filtro)) &
    (df_raw["TIPO"].isin(tipo_filtro)) &
    (df_raw["OPERADOR"].isin(operador_filtro))
].copy()

# Quando o período tem MAIS DE UM DIA, usamos o último dia de cada CPF
# para ter os valores acumulados mais recentes (não somar duplicatas por dia)
if data_inicio != data_fim:
    # Pega para cada CPF apenas o registro do último dia do período filtrado
    df_dia = (
        df_dia
        .sort_values("DATA_REFERENCIA")
        .groupby("CPF/CNPJ_TRAT.", as_index=False)
        .last()   # última data disponível para cada CPF dentro do período
    )

# ============================================================
# ➎ CÁLCULOS GERAIS DO DIA FILTRADO
# ============================================================
total_base        = df_dia["CPF/CNPJ_TRAT."].nunique()    # tamanho fixo da carteira
total_acionamentos= int(df_dia["ACIONAMENTO"].sum())
total_atendidos   = int(df_dia["ATENDIDO"].sum())
total_alo         = int(df_dia["ALÔ"].sum())
total_cpc         = int(df_dia["CPC"].sum())
total_proposta    = int(df_dia["PROPOSTA"].sum())
total_tentativa_u = int(df_dia["TENTATIVA U."].sum())     # CPFs com ao menos 1 acionamento
total_acionado_r  = df_dia["ACIONADO $"].sum()            # R$ já acionados
total_base_r      = df_dia["SOMA CONTABIL"].sum()         # R$ total da carteira

pct_base_trabalhada = (total_tentativa_u / total_base * 100) if total_base > 0 else 0
pct_base_r          = (total_acionado_r  / total_base_r * 100) if total_base_r > 0 else 0

# ============================================================
# ➏ CABEÇALHO DO DASHBOARD
# ============================================================
st.markdown(f"""
<div class="titulo-principal">
    🏦 SANTANDER – PAINEL OPERAÇÃO MANUAL &nbsp;|&nbsp;
    Período: {periodo_label}
</div>
""", unsafe_allow_html=True)

# ============================================================
# ➐ KPIs PRINCIPAIS – LINHA 1 (QUANTIDADE #)
# ============================================================
st.markdown("#### 📊 Quantidade # – Funil do Dia")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

def kpi(col, label, valor, sub=""):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{valor}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

kpi(c1, "BASE TOTAL",      f"{total_base:,.0f}",          "CPFs/CNPJs")
kpi(c2, "ACIONAMENTOS",    f"{total_acionamentos:,.0f}",   "Finalizações CRM")
kpi(c3, "ATENDIDOS",       f"{total_atendidos:,.0f}",      "Atenderam a ligação")
kpi(c4, "ALÔ",             f"{total_alo:,.0f}",            "Confirmaram voz")
kpi(c5, "CPC",             f"{total_cpc:,.0f}",            "Contato c/ titular")
kpi(c6, "PROPOSTA",        f"{total_proposta:,.0f}",       "Propostas enviadas")
kpi(c7, "% BASE TRAB.",    f"{pct_base_trabalhada:.1f}%",  f"{total_tentativa_u} únicos")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# ➑ KPIs PRINCIPAIS – LINHA 2 (CONTÁBIL $)
# ============================================================
st.markdown("#### 💰 Contábil $ – Saldos")

d1, d2, d3 = st.columns(3)
kpi(d1, "VALOR BASE (R$)",    f"R$ {total_base_r:,.2f}",    "Saldo total da carteira")
kpi(d2, "ACIONADO $ (R$)",    f"R$ {total_acionado_r:,.2f}", "Saldo já acionado")
kpi(d3, "% BASE R$ TRAB.",    f"{pct_base_r:.1f}%",          "do total da carteira")

st.markdown("---")

# ============================================================
# ➒ TABELA RESUMO POR OPERADOR (igual à visão atual que você envia por email)
# ============================================================
st.markdown("#### 👤 Ranking por Operador")

tab_qtd, tab_r = st.tabs(["📋 Quantidade #", "💰 Contábil $"])

# Agrupa por OPERADOR + ESTRATÉGIA
grp_op = df_dia.groupby(["OPERADOR","ESTRATÉGIA"], as_index=False).agg(
    BASE=("CPF/CNPJ_TRAT.", "nunique"),
    TENTATIVAS=("ACIONAMENTO", "sum"),
    ATENDIDO=("ATENDIDO", "sum"),
    ALÔ=("ALÔ", "sum"),
    CPC=("CPC", "sum"),
    PROPOSTA=("PROPOSTA", "sum"),
    TENTATIVA_U=("TENTATIVA U.", "sum"),
    SOMA_CONTABIL=("SOMA CONTABIL", "sum"),
    ACIONADO_R=("ACIONADO $", "sum"),
)
grp_op["% BASE TRABALHADA"] = (grp_op["TENTATIVA_U"] / grp_op["BASE"] * 100).round(1).astype(str) + "%"
grp_op["% CONTÁBIL TRABALHADO"] = (grp_op["ACIONADO_R"] / grp_op["SOMA_CONTABIL"] * 100).round(1).astype(str) + "%"

with tab_qtd:
    cols_qtd = ["OPERADOR","ESTRATÉGIA","BASE","TENTATIVAS","ATENDIDO","ALÔ","CPC","PROPOSTA","TENTATIVA_U","% BASE TRABALHADA"]
    st.dataframe(grp_op[cols_qtd].rename(columns={"TENTATIVA_U":"TENTATIVA U."}),
                 use_container_width=True, hide_index=True)

with tab_r:
    cols_r = ["OPERADOR","ESTRATÉGIA","BASE","SOMA_CONTABIL","ACIONADO_R","% CONTÁBIL TRABALHADO"]
    st.dataframe(
        grp_op[cols_r].rename(columns={
            "SOMA_CONTABIL": "VALOR BASE (R$)",
            "ACIONADO_R":    "ACIONADO $ (R$)"
        }).style.format({
            "VALOR BASE (R$)": "R$ {:,.2f}",
            "ACIONADO $ (R$)": "R$ {:,.2f}",
        }),
        use_container_width=True, hide_index=True
    )

st.markdown("---")

# ============================================================
# ➓ GRÁFICOS – ROW 1
# ============================================================
g1, g2 = st.columns(2)

# ── Funil de conversão ──────────────────────────────────────
with g1:
    st.markdown("##### 🔻 Funil de Conversão (Acumulado até o dia)")
    etapas  = ["ACIONAMENTOS","ATENDIDOS","ALÔ","CPC","PROPOSTA"]
    valores = [total_acionamentos, total_atendidos, total_alo, total_cpc, total_proposta]
    fig_funil = go.Figure(go.Funnel(
        y=etapas, x=valores,
        textinfo="value+percent initial",
        marker=dict(color=["#EC0000","#c00000","#900000","#600000","#300000"])
    ))
    fig_funil.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"), margin=dict(l=10,r=10,t=10,b=10)
    )
    st.plotly_chart(fig_funil, use_container_width=True)

# ── % Base trabalhada por operador ──────────────────────────
with g2:
    st.markdown("##### 📈 % Base Trabalhada por Operador")
    grp_op["pct_num"] = grp_op["TENTATIVA_U"] / grp_op["BASE"] * 100
    fig_bar = px.bar(
        grp_op.sort_values("pct_num", ascending=True),
        x="pct_num", y="OPERADOR",
        orientation="h",
        color="pct_num",
        color_continuous_scale=["#300000","#EC0000"],
        text=grp_op.sort_values("pct_num")["% BASE TRABALHADA"],
        labels={"pct_num": "% Base Trabalhada"},
    )
    fig_bar.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"), showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=10,r=10,t=10,b=10)
    )
    fig_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================
# ⓫ GRÁFICOS – ROW 2
# ============================================================
g3, g4 = st.columns(2)

# ── Evolução diária do funil (linha do tempo) ───────────────
with g3:
    st.markdown("##### 📅 Evolução Diária – Funil Acumulado")
    # Aplica os filtros de segmento/macro/tipo mas mostra TODAS as datas do período
    df_tempo = df_raw[
        (df_raw["SEGMENTO"].isin(segmento_filtro)) &
        (df_raw["MACRO"].isin(macro_filtro)) &
        (df_raw["TIPO"].isin(tipo_filtro))
    ].copy()

    evol = df_tempo.groupby("DATA_REFERENCIA", as_index=False).agg(
        ACIONAMENTO=("ACIONAMENTO","sum"),
        ATENDIDO=("ATENDIDO","sum"),
        ALÔ=("ALÔ","sum"),
        CPC=("CPC","sum"),
        PROPOSTA=("PROPOSTA","sum"),
    )
    evol["DATA"] = evol["DATA_REFERENCIA"].dt.strftime("%d/%m")

    fig_linha = px.line(
        evol, x="DATA",
        y=["ACIONAMENTO","ATENDIDO","ALÔ","CPC","PROPOSTA"],
        markers=True,
        color_discrete_sequence=["#EC0000","#ff6666","#ffaa00","#00bcd4","#4caf50"],
    )
    fig_linha.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10,r=10,t=30,b=10)
    )
    st.plotly_chart(fig_linha, use_container_width=True)

# ── Distribuição de saldo por segmento ──────────────────────
with g4:
    st.markdown("##### 🥧 Saldo Contábil por Segmento")
    pizza = df_dia.groupby("SEGMENTO")["SOMA CONTABIL"].sum().reset_index()
    fig_pizza = px.pie(
        pizza, values="SOMA CONTABIL", names="SEGMENTO",
        color_discrete_sequence=["#EC0000","#c00000","#ff6666"],
        hole=0.4,
    )
    fig_pizza.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"),
        margin=dict(l=10,r=10,t=10,b=10)
    )
    st.plotly_chart(fig_pizza, use_container_width=True)

st.markdown("---")

# ============================================================
# ⓬ GRÁFICOS – ROW 3
# ============================================================
g5, g6 = st.columns(2)

# ── Penetração por Macro ─────────────────────────────────────
with g5:
    st.markdown("##### 🗺️ Penetração de Base por Macro Região")
    macro_grp = df_dia.groupby("MACRO", as_index=False).agg(
        BASE=("CPF/CNPJ_TRAT.","nunique"),
        TENTATIVA_U=("TENTATIVA U.","sum"),
        ACIONADO_R=("ACIONADO $","sum"),
        SOMA_CONTABIL=("SOMA CONTABIL","sum"),
    )
    macro_grp["% PENETRAÇÃO"] = macro_grp["TENTATIVA_U"] / macro_grp["BASE"] * 100
    fig_macro = px.bar(
        macro_grp, x="MACRO", y="% PENETRAÇÃO",
        color="MACRO",
        color_discrete_sequence=["#EC0000","#c00000","#ff6666"],
        text=macro_grp["% PENETRAÇÃO"].round(1).astype(str) + "%",
    )
    fig_macro.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"), showlegend=False,
        margin=dict(l=10,r=10,t=10,b=10)
    )
    fig_macro.update_traces(textposition="outside")
    st.plotly_chart(fig_macro, use_container_width=True)

# ── Ajuizados vs Gatilho ─────────────────────────────────────
with g6:
    st.markdown("##### ⚖️ Ajuizados & Gatilhos na Base")
    # reset_index() sem rename – compatível com qualquer versão do pandas
    aj  = df_dia[["Ajuizado"]].rename(columns={"Ajuizado":"Status"}).copy()
    aj["Tipo"] = "Ajuizado"
    gat = df_dia[["GATILHO"]].rename(columns={"GATILHO":"Status"}).copy()
    gat["Tipo"] = "Gatilho"
    df_aj_gat = (
        pd.concat([aj, gat])
        .groupby(["Tipo","Status"], as_index=False)
        .size()
        .rename(columns={"size":"QTD"})
    )
    fig_aj = px.bar(
        df_aj_gat, x="Tipo", y="QTD", color="Status",
        barmode="group",
        color_discrete_map={"SIM":"#EC0000","NÃO":"#4a4a6a"},
        text="QTD",
    )
    fig_aj.update_layout(
        paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
        font=dict(color="#e0e0e0"),
        margin=dict(l=10,r=10,t=10,b=10)
    )
    fig_aj.update_traces(textposition="outside")
    st.plotly_chart(fig_aj, use_container_width=True)

st.markdown("---")

# ============================================================
# ⓭ EVOLUÇÃO DA PENETRAÇÃO DE BASE (%) DIA A DIA
# ============================================================
st.markdown("#### 📉 Evolução da % Base Trabalhada por Operador (ao longo do mês)")

df_evol_op = df_raw[
    (df_raw["SEGMENTO"].isin(segmento_filtro)) &
    (df_raw["MACRO"].isin(macro_filtro)) &
    (df_raw["TIPO"].isin(tipo_filtro))
].copy()

evol_op = df_evol_op.groupby(["DATA_REFERENCIA","OPERADOR"], as_index=False).agg(
    BASE=("CPF/CNPJ_TRAT.","nunique"),
    TENTATIVA_U=("TENTATIVA U.","sum"),
)
evol_op["% TRAB."] = evol_op["TENTATIVA_U"] / evol_op["BASE"] * 100
evol_op["DATA"]    = evol_op["DATA_REFERENCIA"].dt.strftime("%d/%m")

fig_evol_op = px.line(
    evol_op, x="DATA", y="% TRAB.", color="OPERADOR",
    markers=True,
    labels={"% TRAB.": "% Base Trabalhada"},
)
fig_evol_op.update_layout(
    paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
    font=dict(color="#e0e0e0"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=10,r=10,t=30,b=10)
)
st.plotly_chart(fig_evol_op, use_container_width=True)

st.markdown("---")

# ============================================================
# ⓮ TOP EVENTOS (o que os operadores mais registraram no CRM)
# ============================================================
st.markdown("#### 🗂️ Top Eventos Registrados no CRM")
ev_grp = df_dia[df_dia["EVENTO"] != ""].groupby("EVENTO")["CPF/CNPJ_TRAT."].count().reset_index(name="QTD")
ev_grp = ev_grp.sort_values("QTD", ascending=True)
fig_ev = px.bar(
    ev_grp, x="QTD", y="EVENTO", orientation="h",
    color="QTD", color_continuous_scale=["#300000","#EC0000"],
    text="QTD",
)
fig_ev.update_layout(
    paper_bgcolor="#1c1f2e", plot_bgcolor="#1c1f2e",
    font=dict(color="#e0e0e0"), showlegend=False,
    coloraxis_showscale=False,
    margin=dict(l=10,r=10,t=10,b=10)
)
fig_ev.update_traces(textposition="outside")
st.plotly_chart(fig_ev, use_container_width=True)

# ============================================================
# ⓯ BASE DETALHADA (EXPLORADOR)
# ============================================================
st.markdown("---")
st.markdown("#### 🔍 Explorador de Clientes (Dia Selecionado)")
with st.expander("Clique para expandir a base completa filtrada"):
    colunas_exibir = [
        "Nome do Cliente","CPF/CNPJ_TRAT.","SEGMENTO","MACRO","OPERADOR",
        "SOMA CONTABIL","SOMA DIVIDA","MAX ATRASO","Ajuizado","GATILHO",
        "ACIONAMENTO","ATENDIDO","ALÔ","CPC","PROPOSTA","TENTATIVA U.","EVENTO"
    ]
    st.dataframe(
        df_dia[[c for c in colunas_exibir if c in df_dia.columns]],
        use_container_width=True, hide_index=True
    )

# ============================================================
# ⓰ RODAPÉ
# ============================================================
st.markdown(f"""
<div style="text-align:center; color:#555; font-size:11px; margin-top:30px;">
    Planejamento Call Center Santander &nbsp;|&nbsp;
    Dados: {CAMINHO_ARQUIVO} &nbsp;|&nbsp;
    Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)
