"""Monitor de Inflação — IPCA e IPCA-15 | Forluz · Diretoria de Investimentos e Controle (DIC)."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from inflacao import calculos, dados
from inflacao import graficos as g

RAIZ = Path(__file__).resolve().parent
FUSO = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title="Monitor de Inflação | Forluz", page_icon=str(RAIZ / "assets" / "logo_forluz.png"),
                   layout="wide")

# --------------------------------------------------------------------------------------------- séries do relatório
SERIES = {
    "ipca": "Índice cheio",
    "adm": "Administrados",
    "energia": "Administrados – Energia elétrica",
    "gasolina": "Administrados – Gasolina",
    "livres": "Preços livres",
    "alim_dom": "Alimentação no domicílio",
    "industriais": "Bens industriais",
    "ex3_industriais": "Bens industriais subjacentes",
    "servicos": "Serviços",
    "ex3_servicos": "Serviços subjacentes",
    "intensivos_trabalho": "Serviços intensivos em trabalho",
    "ex0": "Núcleo EX0",
    "ex3": "Núcleo EX3",
    "ms": "Núcleo MS",
    "dp": "Núcleo DP",
    "p55": "Núcleo P55",
    "media_nucleos": "Média dos núcleos",
}

# (chave, rótulo, recuo, tipo) — tipo: "i" índice, "c" componente com contribuição, "n" núcleo/sem contribuição
LINHAS_TABELA = [
    ("ipca", "{indice}", 0, "i"),
    ("alim_bebidas", "Alimentação e bebidas", 0, "c"),
    ("alim_dom_sub", "Alimentação no domicílio", 1, "c"),
    ("alim_fora", "Alimentação fora do domicílio", 1, "c"),
    ("habitacao", "Habitação", 0, "c"),
    ("energia", "Energia elétrica residencial", 1, "c"),
    ("artigos_res", "Artigos de residência", 0, "c"),
    ("vestuario", "Vestuário", 0, "c"),
    ("transportes", "Transportes", 0, "c"),
    ("gasolina", "Gasolina", 1, "c"),
    ("saude", "Saúde e cuidados pessoais", 0, "c"),
    ("despesas_pessoais", "Despesas pessoais", 0, "c"),
    ("educacao", "Educação", 0, "c"),
    ("comunicacao", "Comunicação", 0, "c"),
    None,
    ("adm", "Preços administrados", 0, "c"),
    ("livres", "Preços livres", 0, "c"),
    None,
    ("nao_duraveis", "Bens não duráveis", 0, "c"),
    ("semiduraveis", "Bens semiduráveis", 0, "c"),
    ("duraveis", "Bens duráveis", 0, "c"),
    None,
    ("servicos", "Serviços", 0, "c"),
    ("ex3_servicos", "Serviços subjacentes", 1, "c"),
    ("intensivos_trabalho", "Serviços intensivos em trabalho", 1, "c"),
    None,
    ("industriais", "Industriais", 0, "c"),
    ("ex3_industriais", "Industriais subjacentes", 1, "c"),
    None,
    ("difusao", "Difusão (%)", 0, "d"),
    ("ex0", "IPCA EX0", 0, "n"),
    ("ex3", "IPCA EX3", 0, "n"),
    ("ms", "IPCA MS", 0, "n"),
    ("dp", "IPCA DP", 0, "n"),
    ("p55", "IPCA P55", 0, "n"),
    ("media_nucleos", "Média dos núcleos*", 0, "m"),
]

CSS = f"""
<style>
.block-container {{padding-top: 3.2rem; max-width: 1400px;}}
.cab {{display:flex; align-items:center; gap:18px; border-bottom:4px solid {g.LARANJA}; padding-bottom:10px; margin-bottom:6px;}}
.cab img {{height:58px;}}
.cab h1 {{font-size:1.75rem; color:{g.AZUL}; margin:0; padding:0; font-weight:700;}}
.cab .sub {{color:#666; font-size:.92rem; margin-top:2px;}}
.kpi {{border:1px solid #E6E6E6; border-top:4px solid {g.LARANJA}; border-radius:8px; padding:10px 14px; background:white;}}
.kpi .r {{color:#666; font-size:.8rem; text-transform:uppercase; letter-spacing:.03em;}}
.kpi .v {{color:{g.AZUL}; font-size:1.65rem; font-weight:700; line-height:1.2;}}
.kpi .d {{color:#888; font-size:.78rem;}}
table.tab {{border-collapse:collapse; width:100%; font-size:.86rem;}}
table.tab th {{background:{g.AZUL}; color:white; padding:6px 8px; text-align:right; font-weight:600; position:sticky; top:0;}}
table.tab th:first-child {{text-align:left;}}
table.tab td {{padding:4px 8px; text-align:right; border-bottom:1px solid #EFEFEF; white-space:nowrap;}}
table.tab td:first-child {{text-align:left;}}
table.tab tr.i td {{background:#FDF1E4; font-weight:700; border-bottom:2px solid {g.LARANJA};}}
table.tab tr.m td {{font-weight:700; border-top:2px solid {g.CINZA};}}
table.tab tr.sub td:first-child {{padding-left:26px; color:#444;}}
table.tab tr.sep td {{border-bottom:1px dashed {g.CINZA}; padding:0; height:2px;}}
table.tab td.neg {{color:{g.AZUL};}}
.rod {{color:#777; font-size:.8rem; border-top:1px solid #E6E6E6; margin-top:28px; padding-top:8px;}}
div[data-testid="stTabs"] button[aria-selected="true"] p {{color:{g.LARANJA}; font-weight:700;}}
</style>
"""


# --------------------------------------------------------------------------------------------- dados (com cache)
@st.cache_data(ttl=600, show_spinner=False)
def periodo_disponivel(indice: str) -> str:
    """Consulta leve (10 min de cache): detecta automaticamente nova divulgação do IBGE."""
    return dados.ultimo_periodo(indice)


@st.cache_data(show_spinner=False, max_entries=4)
def calcular(indice: str, fim: str):
    """Cache por (índice, último mês divulgado): uma nova divulgação gera nova chave e recarrega tudo."""
    d = dados.carregar_indice(indice, fim)
    mensal, pesos = calculos.series_mensais(d)
    return d, mensal, pesos, datetime.now(FUSO)


@st.cache_data(ttl=3600, show_spinner=False)
def oficiais_ipca():
    return dados.sgs_oficiais_ipca("01/01/2019")


def logo_b64() -> str:
    return base64.b64encode((RAIZ / "assets" / "logo_forluz.png").read_bytes()).decode()


# --------------------------------------------------------------------------------------------- componentes
def kpi(rotulo: str, valor: str, detalhe: str = ""):
    st.markdown(f'<div class="kpi"><div class="r">{rotulo}</div><div class="v">{valor}</div>'
                f'<div class="d">{detalhe}</div></div>', unsafe_allow_html=True)


def tabela_resumo(v: dict, pesos: pd.DataFrame, contrib: pd.DataFrame, indice: str, n_meses: int = 3) -> str:
    mensal, ano, doze = v["mes"], v["ano"], v["12m"]
    ult = mensal["ipca"].dropna().index[-n_meses:]
    ref = ult[-1]
    cab = "".join(f"<th>{g.rotulo_mes(d)}</th>" for d in ult)
    html = [f'<table class="tab"><tr><th>{indice} (%)</th>{cab}<th>No ano</th><th>12 meses</th>'
            f'<th>Peso {g.rotulo_mes(ref)}</th><th>Contribuição {g.rotulo_mes(ref)} (p.p.)</th></tr>']

    def cel(x, casas=2):
        return f'<td class="{"neg" if pd.notna(x) and x < 0 else ""}">{g.fmt(x, casas)}</td>'

    for linha in LINHAS_TABELA:
        if linha is None:
            html.append(f'<tr class="sep"><td colspan="{n_meses + 5}"></td></tr>')
            continue
        chave, rotulo, recuo, tipo = linha
        classe = {"i": "i", "m": "m"}.get(tipo, "sub" if recuo else "")
        celulas = "".join(cel(mensal.at[d, chave], 1 if tipo == "d" else 2) for d in ult)
        if tipo == "d":
            celulas += "<td>–</td>" * 4
        else:
            celulas += cel(ano.at[ref, chave]) + cel(doze.at[ref, chave])
            if tipo in ("c", "i"):
                celulas += cel(pesos.at[ref, chave], 2) + cel(contrib.at[ref, chave], 2)
            else:
                celulas += "<td>–</td><td>–</td>"
        html.append(f'<tr class="{classe}"><td>{rotulo.format(indice=indice)}</td>{celulas}</tr>')
    html.append("</table>")
    return "".join(html)


# --------------------------------------------------------------------------------------------- página
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    f'<div class="cab"><img src="data:image/png;base64,{logo_b64()}"/>'
    f'<div><h1>Monitor de Inflação — IPCA e IPCA-15</h1>'
    f'<div class="sub">Produzido pela Diretoria de Investimentos e Controle – DIC · Forluz</div></div></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Configurações")
    indice = st.radio("Índice", ["IPCA", "IPCA-15"], horizontal=True)
    n_meses = st.slider("Janela dos gráficos (meses)", 12, 60, 24, step=6)
    rotulos = st.toggle("Mostrar valores nas barras", value=True)
    st.divider()
    if st.button("🔄 Atualizar dados agora", width="stretch", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.caption("O relatório verifica automaticamente a cada 10 minutos se o IBGE divulgou um novo mês "
               "(divulgações às 9h) e recalcula tudo quando há dado novo.")

try:
    fim = periodo_disponivel(indice)
    with st.spinner(f"Carregando {indice} no SIDRA/IBGE e calculando núcleos…"):
        d, mensal, pesos, quando = calcular(indice, fim)
except Exception as e:  # noqa: BLE001
    st.error(f"Não foi possível acessar as APIs do IBGE/BCB no momento. Tente novamente em instantes.\n\n{e}")
    st.stop()

fonte = None
if indice == "IPCA":
    try:
        mensal, fonte = calculos.aplicar_oficiais(mensal, oficiais_ipca())
    except Exception:  # noqa: BLE001 — sem SGS, segue com o cálculo próprio (idêntico à metodologia do BCB)
        fonte = None

v = calculos.visoes(mensal)
contrib = calculos.contribuicao_series(mensal, pesos)
ref = mensal["ipca"].dropna().index[-1]
janela = mensal.index[mensal.index > ref - pd.DateOffset(months=n_meses)]

with st.sidebar:
    st.divider()
    st.markdown(f"**Último dado:** {g.rotulo_mes(ref, True)} ({indice})")
    st.caption(f"Dados carregados em {quando:%d/%m/%Y %H:%M}")

aba = st.tabs(["Visão geral", "Tabela resumo", "Grupos especiais e núcleos", "Difusão", "Contribuições",
               "Metodologia"])

# ---------------------------------------------------------------- Visão geral
with aba[0]:
    c = st.columns(5)
    with c[0]:
        kpi(f"{indice} · {g.rotulo_mes(ref, True)}", f"{g.fmt(v['mes'].at[ref, 'ipca'])}%", "variação mensal")
    with c[1]:
        kpi("Acumulado no ano", f"{g.fmt(v['ano'].at[ref, 'ipca'])}%", f"jan–{g.rotulo_mes(ref)}")
    with c[2]:
        kpi("Acumulado em 12 meses", f"{g.fmt(v['12m'].at[ref, 'ipca'])}%",
            f"mês anterior: {g.fmt(v['12m']['ipca'].shift(1).at[ref])}%")
    with c[3]:
        kpi("Média dos núcleos", f"{g.fmt(v['mes'].at[ref, 'media_nucleos'])}%",
            f"12 meses: {g.fmt(v['12m'].at[ref, 'media_nucleos'])}%")
    with c[4]:
        kpi("Difusão", f"{g.fmt(v['mes'].at[ref, 'difusao'], 1)}%", "subitens com alta no mês")

    st.plotly_chart(g.barras(v["mes"].loc[janela, "ipca"], f"{indice} — variação mensal (%)", "Variação mensal",
                             rotulos), width="stretch")
    st.plotly_chart(g.barras(v["ano"].loc[janela, "ipca"], f"{indice} — acumulado no ano (%)", "Acumulado no ano",
                             rotulos), width="stretch")
    st.plotly_chart(g.barras(v["12m"].loc[janela, "ipca"], f"{indice} — acumulado em 12 meses (%)",
                             "Acumulado em 12 meses", rotulos), width="stretch")

# ---------------------------------------------------------------- Tabela resumo
with aba[1]:
    st.markdown(f"#### {indice}: variação por grupo e classificação especial")
    st.markdown(tabela_resumo(v, pesos, contrib, indice), unsafe_allow_html=True)
    st.caption("*Média dos núcleos: EX0, EX3, MS, DP e P55. Contribuição = peso × variação no mês ÷ 100 "
               "(pontos percentuais do índice cheio). Peso e contribuição referem-se ao último mês da tabela.")

# ---------------------------------------------------------------- Grupos especiais e núcleos
with aba[2]:
    escolha = st.selectbox("Série", list(SERIES), format_func=SERIES.get, index=1)
    anualizada = st.toggle("Média móvel de 3 meses anualizada (MM3 a.a.)", value=False,
                           help="Desligado: média simples das 3 últimas variações mensais. "
                                "Ligado: variação acumulada em 3 meses, anualizada (sem ajuste sazonal).")
    nome = SERIES[escolha]
    if escolha in pesos.columns and pd.notna(pesos.at[ref, escolha]):
        st.caption(f"Peso no {indice} em {g.rotulo_mes(ref, True)}: {g.fmt(pesos.at[ref, escolha])}% · "
                   f"Contribuição no mês: {g.fmt(contrib.at[ref, escolha])} p.p.")
    chave_mm3 = "mm3_saar" if anualizada else "mm3"
    titulo_mm3 = "média móvel 3 meses anualizada (%)" if anualizada else "média móvel de 3 meses (% a.m.)"
    for chave, titulo, rotulo in [("mes", "variação mensal (%)", "Variação mensal"),
                                  ("ano", "acumulado no ano (%)", "Acumulado no ano"),
                                  ("12m", "acumulado em 12 meses (%)", "Acumulado em 12 meses"),
                                  (chave_mm3, titulo_mm3, "MM3")]:
        st.plotly_chart(g.barras(v[chave].loc[janela, escolha], f"{nome} — {titulo}", rotulo, rotulos, altura=320),
                        width="stretch")

# ---------------------------------------------------------------- Difusão
with aba[3]:
    dif = mensal.loc[janela, "difusao"]
    mm3 = mensal["difusao"].rolling(3).mean()
    st.plotly_chart(g.barras_com_media(dif, mm3, f"Difusão do {indice} — % de subitens com variação positiva",
                                       "Difusão", "Média móvel 3 meses", rotulos, altura=420),
                    width="stretch")
    st.caption("Difusão = percentual dos subitens efetivamente pesquisados no mês com variação positiva "
               "(não ponderado).")

# ---------------------------------------------------------------- Contribuições
with aba[4]:
    datas = list(d["V"].index[::-1])
    c1, c2 = st.columns([1, 2])
    with c1:
        mes_c = st.selectbox("Mês de referência", datas, format_func=lambda x: g.rotulo_mes(x, True))
    with c2:
        busca = st.text_input("Filtrar por nome", placeholder="ex.: gasolina, aluguel, plano de saúde…")
    tab_c = calculos.contribuicoes(d, mes_c)
    total = mensal.at[mes_c, "ipca"]
    st.caption(f"{indice} em {g.rotulo_mes(mes_c, True)}: {g.fmt(total)}%. "
               "Contribuição = peso mensal × variação mensal ÷ 100, em pontos percentuais (p.p.).")
    sub = st.tabs(["Grupo", "Subgrupo", "Item", "Subitem"])
    for nivel, t in zip(["Grupo", "Subgrupo", "Item", "Subitem"], sub):
        with t:
            df = tab_c[tab_c["nivel"] == nivel].sort_values("contribuicao", ascending=False)
            if busca:
                df = df[df["componente"].str.contains(busca, case=False, na=False)]
            colunas = ["codigo", "componente", "peso", "variacao", "contribuicao"]
            if nivel != "Grupo":
                colunas.insert(2, "grupo")
            estilo = (df[colunas].style
                      .format({"peso": "{:.4f}", "variacao": "{:.2f}", "contribuicao": "{:.4f}"},
                              decimal=",", thousands=".", na_rep="–")
                      .map(lambda x: f"color: {g.AZUL}" if pd.notna(x) and x < 0 else "",
                           subset=["variacao", "contribuicao"]))
            st.dataframe(
                estilo, hide_index=True, width="stretch", height=min(480, 38 + 35 * len(df)),
                column_config={
                    "codigo": st.column_config.TextColumn("Código", width="small"),
                    "componente": st.column_config.TextColumn(nivel, width="medium"),
                    "grupo": st.column_config.TextColumn("Grupo", width="medium"),
                    "peso": st.column_config.Column("Peso (%)", width="small"),
                    "variacao": st.column_config.Column("Variação (%)", width="small"),
                    "contribuicao": st.column_config.Column("Contrib. (p.p.)", width="small"),
                },
            )
            st.caption(f"{len(df)} componentes · soma das contribuições: "
                       f"{g.fmt(df['contribuicao'].sum(), 3)} p.p. · clique no cabeçalho para reordenar")
            n = 9 if nivel == "Grupo" else 10
            st.plotly_chart(g.contribuicoes_horizontais(df, f"Maiores contribuições positivas e negativas — "
                                                            f"{nivel.lower()}", n), width="stretch")

# ---------------------------------------------------------------- Metodologia
with aba[5]:
    st.markdown(f"""
**Fontes (APIs, atualização automática)**
- **IBGE / SIDRA** — tabelas 7060 (IPCA) e 7062 (IPCA-15): variação e peso mensais do índice geral, grupos,
  subgrupos, itens e subitens. Tabelas 1419 e 1705 (estrutura anterior) são usadas apenas como histórico para os
  núcleos DP (48 meses) e MS (12 meses).
- **Banco Central / SGS** — séries oficiais dos grupos especiais e núcleos do IPCA (códigos da Nota Técnica BCB nº 57).

**Cálculos** — seguem a *Nota Técnica BCB nº 57 (dez/2025): Núcleos de inflação e outras séries analíticas
derivadas do IPCA — metodologia consolidada*, com os vetores de agregação oficiais (arquivo `Vetores_NT_57.xlsx`):
- **Administrados, livres, serviços, bens industriais, duráveis/semi/não duráveis, EX0, EX3, serviços subjacentes
  (EX3 Serviços) e industriais subjacentes (EX3 Industriais):** Σ(peso × variação) ÷ Σ peso dos componentes do vetor.
- **MS:** média aparada 20%/20% dos itens, com suavização (média geométrica de 12 meses) de combustíveis domésticos,
  energia elétrica, transporte público, combustíveis de veículos, serviços pessoais, fumo, cursos regulares, cursos
  diversos e comunicação.
- **DP:** peso de cada item dividido pelo desvio-padrão de (variação do item − variação do índice) nos 48 meses
  anteriores.
- **P55:** variação do subitem no percentil 55 da distribuição ponderada.
- **Difusão:** % de subitens pesquisados com variação positiva.
- **Média dos núcleos:** média simples de EX0, EX3, MS, DP e P55 (nos acumulados, média dos acumulados de cada núcleo).
- **Serviços intensivos em trabalho** (boxe RI dez/2013): mão de obra, médico, dentista, fisioterapeuta, psicólogo,
  costureira, manicure, cabeleireiro e barbeiro, empregado doméstico.
- **Acumulados:** no ano e em 12 meses por capitalização composta das variações mensais.
- **Contribuição:** peso mensal × variação mensal ÷ 100 (p.p.).

**Validação** — para o IPCA, todas as séries calculadas reproduzem exatamente (2 casas decimais) as séries oficiais do
BCB desde 2021. No IPCA, o relatório exibe o valor oficial do SGS quando já publicado e o cálculo próprio
(idêntico) enquanto o BCB não atualiza. Para o IPCA-15, o BCB não publica essas séries: todas são calculadas aqui
com a mesma metodologia.
""")
    if fonte is not None:
        st.caption(f"Fonte dos valores de {g.rotulo_mes(ref, True)}: " + ", ".join(
            f"{SERIES.get(k, k)} = {fonte.at[ref, k]}" for k in ["adm", "ex0", "ms", "dp", "p55"]))

st.markdown(
    f'<div class="rod">Fontes: IBGE (SIDRA) e Banco Central do Brasil (SGS). Metodologia: Nota Técnica BCB nº 57. '
    f'Elaboração: Forluz — Diretoria de Investimentos e Controle (DIC). Dados de {indice} até '
    f'{g.rotulo_mes(ref, True)}.</div>',
    unsafe_allow_html=True,
)
