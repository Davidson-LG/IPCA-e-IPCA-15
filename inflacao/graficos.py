"""Gráficos Plotly no padrão visual Forluz."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

LARANJA = "#F08921"
CINZA = "#999999"
AZUL = "#12239E"
TEXTO = "#2B2B2B"
GRADE = "#ECECEC"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_mes(d: pd.Timestamp, ano_completo: bool = False) -> str:
    return f"{MESES[d.month - 1]}/{d.year if ano_completo else str(d.year)[2:]}"


def fmt(x: float, casas: int = 2) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _layout(fig: go.Figure, titulo: str, altura: int, sufixo: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=15, color=AZUL)),
        height=altura,
        margin=dict(l=8, r=8, t=48, b=8),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color=TEXTO),
        separators=",.",
        bargap=0.25,
        showlegend=False,
        hoverlabel=dict(bgcolor="white", bordercolor=LARANJA, font=dict(color=TEXTO, size=13)),
    )
    fig.update_xaxes(showgrid=False, linecolor=CINZA, tickfont=dict(size=11, color="#555"), type="category")
    fig.update_yaxes(gridcolor=GRADE, zeroline=True, zerolinecolor=CINZA, zerolinewidth=1,
                     ticksuffix=sufixo, tickfont=dict(size=11, color="#555"))
    return fig


def barras(serie: pd.Series, titulo: str, nome: str, rotulos: bool = True, altura: int = 340,
           sufixo: str = "%", casas: int = 2) -> go.Figure:
    """Barras mensais: laranja para valores positivos, azul para negativos; valor exato no hover."""
    s = serie.dropna()
    x = [rotulo_mes(d) for d in s.index]
    texto = [fmt(v, casas) for v in s.values]
    fig = go.Figure(go.Bar(
        x=x, y=s.values, name=nome,
        marker=dict(color=np.where(s.values >= 0, LARANJA, AZUL), cornerradius=4),
        text=texto if rotulos else None,
        textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color=TEXTO),
        customdata=[[rotulo_mes(d, True), t] for d, t in zip(s.index, texto)],
        hovertemplate=f"<b>%{{customdata[0]}}</b><br>{nome}: <b>%{{customdata[1]}}{sufixo}</b><extra></extra>",
    ))
    if rotulos and len(s):
        faixa = s.max() - min(s.min(), 0)
        fig.update_yaxes(range=[min(s.min(), 0) - faixa * 0.12, max(s.max(), 0) + faixa * 0.15])
    return _layout(fig, titulo, altura, sufixo)


def barras_com_media(serie: pd.Series, media: pd.Series, titulo: str, nome: str, nome_media: str,
                     rotulos: bool = True, altura: int = 360) -> go.Figure:
    fig = barras(serie, titulo, nome, rotulos, altura, sufixo="%", casas=1)
    m = media.reindex(serie.dropna().index)
    fig.add_trace(go.Scatter(
        x=[rotulo_mes(d) for d in m.index], y=m.values, mode="lines", name=nome_media,
        line=dict(color=AZUL, width=2),
        customdata=[fmt(v, 1) for v in m.values],
        hovertemplate=f"{nome_media}: <b>%{{customdata}}%</b><extra></extra>",
    ))
    fig.update_traces(selector=dict(type="bar"), marker_color=LARANJA)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"),
                      hovermode="x unified")
    vals = pd.concat([serie, m]).dropna()
    fig.update_yaxes(range=[0, vals.max() * 1.15])
    return fig


def contribuicoes_horizontais(df: pd.DataFrame, titulo: str, n: int = 10, altura: int = 520) -> go.Figure:
    """Maiores contribuições positivas e negativas do mês."""
    pos = df[df["contribuicao"] > 0].nlargest(n, "contribuicao")
    neg = df[df["contribuicao"] < 0].nsmallest(n, "contribuicao")
    sel = pd.concat([pos, neg]).sort_values("contribuicao")
    fig = go.Figure(go.Bar(
        y=sel["componente"], x=sel["contribuicao"], orientation="h",
        marker=dict(color=np.where(sel["contribuicao"] >= 0, LARANJA, AZUL), cornerradius=4),
        text=[fmt(v, 3) for v in sel["contribuicao"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=10, color=TEXTO),
        customdata=np.stack([sel["peso"].map(lambda v: fmt(v, 4)), sel["variacao"].map(fmt),
                             sel["contribuicao"].map(lambda v: fmt(v, 3))], axis=-1),
        hovertemplate=("<b>%{y}</b><br>Peso: %{customdata[0]}%<br>Variação: %{customdata[1]}%"
                       "<br>Contribuição: <b>%{customdata[2]} p.p.</b><extra></extra>"),
    ))
    fig = _layout(fig, titulo, altura, "")
    lo, hi = min(sel["contribuicao"].min(), 0), max(sel["contribuicao"].max(), 0)
    folga = (hi - lo) * 0.18
    fig.update_xaxes(type="linear", showgrid=True, gridcolor=GRADE, zeroline=True, zerolinecolor=CINZA,
                     range=[lo - (folga if lo < 0 else 0), hi + folga], title_text="p.p.")
    fig.update_yaxes(type="category", gridcolor="rgba(0,0,0,0)", ticksuffix="", automargin=True)
    fig.update_layout(margin=dict(l=8, r=40, t=48, b=8))
    return fig
