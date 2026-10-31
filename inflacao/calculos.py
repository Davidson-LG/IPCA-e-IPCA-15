"""Cálculo dos grupos especiais, núcleos de inflação e contribuições.

Metodologia: Nota Técnica BCB nº 57 (dez/2025) — "Núcleos de inflação e outras séries analíticas derivadas
do IPCA: metodologia consolidada" — e vetores de agregação oficiais (arquivo de apoio Vetores_NT_57.xlsx).
Para o IPCA-15 aplica-se exatamente a mesma metodologia, pois o BCB não publica essas séries para esse índice.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

VETORES = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "vetores_bcb_jan20.csv", dtype={"codigo": str})

# Itens com variações suavizadas no núcleo MS (NT 57, Tabela 5 — estrutura jan/20–presente)
ITENS_SUAVIZADOS_MS = ["2201", "2202", "5101", "5104", "7101", "7202", "8101", "8104", "9101"]

NUCLEOS_MEDIA = ["ex0", "ex3", "ms", "dp", "p55"]

# Componentes individuais usados no relatório (código SIDRA)
COMPONENTES = {
    "ipca": "0",
    "energia": "2202",      # Energia elétrica residencial
    "gasolina": "5104001",  # Gasolina
    "alim_bebidas": "1",
    "alim_dom_sub": "11",
    "alim_fora": "12",
    "habitacao": "2",
    "artigos_res": "3",
    "vestuario": "4",
    "transportes": "5",
    "saude": "6",
    "despesas_pessoais": "7",
    "educacao": "8",
    "comunicacao": "9",
}

# Agregações por vetor de 0/1 (NT 57 §2.1.2)
AGREGACOES = ["adm", "livres", "alim_dom", "servicos", "industriais", "comercializaveis", "nao_comercializaveis",
              "nao_duraveis", "semiduraveis", "duraveis", "ex_fe", "ex0", "ex1", "ex2", "ex3", "ex3_servicos",
              "ex3_industriais", "intensivos_trabalho"]


def _codigos(V: pd.DataFrame, tamanho: int) -> list[str]:
    return [c for c in V.columns if len(c) == tamanho and c != "0"]


def agregar(V: pd.DataFrame, W: pd.DataFrame, codigos) -> tuple[pd.Series, pd.Series]:
    """Variação mensal e peso de uma agregação: Σ(w·v)/Σw sobre os componentes indicados."""
    cols = [c for c in codigos if c in V.columns and c in W.columns]
    v, w = V[cols], W[cols]
    ok = v.notna() & w.notna()
    peso = w.where(ok).sum(axis=1)
    var = (v * w).where(ok).sum(axis=1) / peso
    return var.where(peso > 0), peso


def media_aparada(v: pd.Series, w: pd.Series, corte: float = 20.0) -> float:
    """Média aparada simétrica com correção dos pesos dos itens limítrofes (NT 57 §2.3)."""
    ok = v.notna() & w.notna() & (w > 0)
    v, w = v[ok], w[ok]
    if v.empty:
        return np.nan
    ordem = v.sort_values(kind="mergesort").index
    v, w = v[ordem], w[ordem] / w.sum() * 100
    acum = w.cumsum()
    mantido = (np.minimum(acum, 100 - corte) - np.maximum(acum - w, corte)).clip(lower=0)
    return float((v * mantido).sum() / mantido.sum())


def percentil(v: pd.Series, w: pd.Series, p: float = 0.55) -> float:
    """Variação do subitem no percentil p da distribuição ponderada (NT 57 §2.5)."""
    ok = v.notna() & w.notna() & (w > 0)
    v, w = v[ok], w[ok]
    if v.empty:
        return np.nan
    ordem = v.sort_values(kind="mergesort").index
    v, w = v[ordem], w[ordem] / w.sum()
    k = int(np.argmax(w.cumsum().values >= p - 1e-12))
    return float(v.iloc[k])


def nucleo_ma(V, W, corte=20.0) -> pd.Series:
    itens = _codigos(V, 4)
    return pd.Series({d: media_aparada(V.loc[d, itens], W.loc[d, itens], corte) for d in V.index})


def nucleo_ms(V, W, V_hist) -> pd.Series:
    """MA após substituir, para itens de variação infrequente, a variação do mês pela média geométrica de 12 meses."""
    itens = _codigos(V, 4)
    suav = [c for c in ITENS_SUAVIZADOS_MS if c in V_hist.columns]
    media12 = ((1 + V_hist[suav] / 100).rolling(12, min_periods=12).apply(np.prod, raw=True) ** (1 / 12) - 1) * 100
    Vs = V[itens].copy()
    Vs[suav] = media12.reindex(V.index)[suav]
    return pd.Series({d: media_aparada(Vs.loc[d], W.loc[d, itens]) for d in V.index})


def nucleo_dp(V, W, V_hist) -> pd.Series:
    """Dupla ponderação: peso original / volatilidade relativa (desvio-padrão de v_i − v_IPCA nos 48 meses
    anteriores ao mês de referência — validado contra a série 16122 do SGS)."""
    itens = [c for c in _codigos(V, 4) if c in V_hist.columns]
    dif = V_hist[itens].sub(V_hist["0"], axis=0)
    sigma = dif.rolling(48, min_periods=48).std(ddof=1).shift(1).reindex(V.index)
    wa = W[itens] / sigma
    ok = V[itens].notna() & wa.notna()
    return (V[itens] * wa).where(ok).sum(axis=1) / wa.where(ok).sum(axis=1)


def nucleo_p55(V, W) -> pd.Series:
    sub = _codigos(V, 7)
    return pd.Series({d: percentil(V.loc[d, sub], W.loc[d, sub]) for d in V.index})


def difusao(V) -> pd.Series:
    """Percentual de subitens (efetivamente pesquisados) com variação positiva (NT 57 §2.6)."""
    sub = V[_codigos(V, 7)]
    return (sub > 0).where(sub.notna()).sum(axis=1) / sub.notna().sum(axis=1) * 100


def series_mensais(dados: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Variação mensal (%) e peso (%) de todas as séries do relatório."""
    V, W, Vh = dados["V"], dados["W"], dados["V_hist"]
    var, peso = {}, {}
    for chave, cod in COMPONENTES.items():
        var[chave], peso[chave] = V.get(cod), W.get(cod)
    for chave in AGREGACOES:
        cods = VETORES.loc[VETORES[chave] == 1, "codigo"]
        var[chave], peso[chave] = agregar(V, W, cods)
    var["ma"] = nucleo_ma(V, W)
    var["ms"] = nucleo_ms(V, W, Vh)
    var["dp"] = nucleo_dp(V, W, Vh)
    var["p55"] = nucleo_p55(V, W)
    var["difusao"] = difusao(V)
    mensal = pd.DataFrame(var).sort_index()
    mensal["media_nucleos"] = mensal[NUCLEOS_MEDIA].mean(axis=1, skipna=False)
    return mensal, pd.DataFrame(peso).sort_index()


def aplicar_oficiais(mensal: pd.DataFrame, oficiais: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Usa os valores oficiais do SGS quando disponíveis; mantém o cálculo próprio caso o BCB ainda não tenha publicado."""
    out = mensal.copy()
    fonte = pd.DataFrame("Cálculo próprio (metodologia BCB)", index=mensal.index, columns=mensal.columns)
    for col in oficiais.columns.intersection(out.columns):
        s = oficiais[col].reindex(out.index)
        tem = s.notna()
        out.loc[tem, col] = s[tem]
        fonte.loc[tem, col] = "BCB/SGS (oficial)"
    out["media_nucleos"] = out[NUCLEOS_MEDIA].mean(axis=1, skipna=False)
    return out, fonte


def acumulado_ano(mensal: pd.DataFrame) -> pd.DataFrame:
    fator = 1 + mensal / 100
    return (fator.groupby(mensal.index.year).cumprod() - 1) * 100


def acumulado_12m(mensal: pd.DataFrame) -> pd.DataFrame:
    fator = 1 + mensal / 100
    return (fator.rolling(12, min_periods=12).apply(np.prod, raw=True) - 1) * 100


def media_movel_3m(mensal: pd.DataFrame, anualizada: bool = False) -> pd.DataFrame:
    if anualizada:
        fator = (1 + mensal / 100).rolling(3, min_periods=3).apply(np.prod, raw=True)
        return (fator ** 4 - 1) * 100
    return mensal.rolling(3, min_periods=3).mean()


def visoes(mensal: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Mês, ano, 12 meses e MM3. Para a média dos núcleos, o acumulado é a média dos acumulados de cada núcleo."""
    base = mensal.drop(columns=["difusao"])
    ano, doze = acumulado_ano(base), acumulado_12m(base)
    ano["media_nucleos"] = ano[NUCLEOS_MEDIA].mean(axis=1, skipna=False)
    doze["media_nucleos"] = doze[NUCLEOS_MEDIA].mean(axis=1, skipna=False)
    return {
        "mes": mensal,
        "ano": ano,
        "12m": doze,
        "mm3": media_movel_3m(mensal),
        "mm3_saar": media_movel_3m(base, anualizada=True),
    }


def contribuicoes(dados: dict, data: pd.Timestamp) -> pd.DataFrame:
    """Peso, variação e contribuição (peso × variação / 100, em p.p.) de cada componente no mês."""
    V, W, nomes = dados["V"], dados["W"], dados["nomes"]
    df = pd.DataFrame({"peso": W.loc[data], "variacao": V.loc[data]})
    df = df[df.index != "0"].dropna(how="all")
    df["contribuicao"] = df["peso"] * df["variacao"] / 100
    df["nivel"] = df.index.map(lambda c: {1: "Grupo", 2: "Subgrupo", 4: "Item", 7: "Subitem"}.get(len(c)))
    df["componente"] = df.index.map(lambda c: nomes.get(c, c).split(".", 1)[-1])
    df["grupo"] = df.index.map(lambda c: nomes.get(c[0], c[0]).split(".", 1)[-1])
    df.index.name = "codigo"
    return df.reset_index()


def contribuicao_series(mensal: pd.DataFrame, pesos: pd.DataFrame) -> pd.DataFrame:
    """Contribuição em p.p. das séries agregadas para a variação do índice cheio no mês."""
    cols = pesos.columns.intersection(mensal.columns)
    return mensal[cols] * pesos[cols] / 100
