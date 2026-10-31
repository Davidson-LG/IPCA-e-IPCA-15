"""Validação dos cálculos.

1) IPCA-15: compara com a tabela de referência (ago/26–out/26) usada na especificação do relatório.
2) IPCA: compara o cálculo próprio com as séries oficiais do BCB/SGS (NT 57) em todos os meses disponíveis.

Uso:  python scripts/validar.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from inflacao import calculos, dados  # noqa: E402

REFERENCIA_IPCA15 = {  # ago/26, set/26, out/26
    "ipca": (-0.40, 0.70, 0.32),
    "alim_bebidas": (-0.57, 0.40, 0.88),
    "alim_dom_sub": (-0.97, 0.44, 1.01),
    "alim_fora": (0.42, 0.34, 0.56),
    "habitacao": (-1.41, 2.07, -0.10),
    "energia": (-6.25, 7.42, -0.89),
    "artigos_res": (0.04, 0.55, 0.28),
    "vestuario": (-0.20, 0.41, 0.53),
    "transportes": (-1.00, 0.60, 0.05),
    "gasolina": (-1.23, 0.30, 0.92),
    "saude": (0.40, 0.13, 0.15),
    "despesas_pessoais": (0.66, 0.96, 0.55),
    "educacao": (0.46, 0.03, 0.09),
    "comunicacao": (-0.02, 0.54, 0.43),
    "adm": (-1.13, 1.28, 0.15),
    "livres": (-0.14, 0.50, 0.38),
    "nao_duraveis": (-0.61, 0.61, 0.64),
    "semiduraveis": (-0.17, 0.32, 0.37),
    "duraveis": (-0.16, 0.07, 0.18),
    "servicos": (0.11, 0.63, 0.25),
    "ex3_servicos": (0.50, 0.28, 0.46),
    "industriais": (0.07, 0.41, 0.20),
    "ex3_industriais": (0.08, 0.05, 0.22),
    "difusao": (52, 54, 59),
    "ex0": (0.09, 0.55, 0.23),
    "ex3": (0.33, 0.19, 0.36),
    "ms": (0.36, 0.29, 0.28),
    "dp": (0.15, 0.32, 0.30),
    "p55": (0.25, 0.35, 0.38),
    "media_nucleos": (0.24, 0.34, 0.31),
}


def validar_ipca15():
    d = dados.carregar_indice("IPCA-15")
    mensal, _ = calculos.series_mensais(d)
    datas = pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01"])
    linhas = []
    for chave, ref in REFERENCIA_IPCA15.items():
        calc = mensal.loc[datas, chave].round(2).tolist()
        dif = [round(c - r, 2) for c, r in zip(calc, ref)]
        linhas.append([chave, *ref, *calc, max(abs(x) for x in dif)])
    df = pd.DataFrame(linhas, columns=["serie", "ref_ago", "ref_set", "ref_out", "calc_ago", "calc_set", "calc_out", "dif_max"])
    print("\n=== IPCA-15: cálculo x tabela de referência ===")
    print(df.to_string(index=False))
    return df


def validar_ipca():
    d = dados.carregar_indice("IPCA")
    mensal, _ = calculos.series_mensais(d)
    oficiais = dados.sgs_oficiais_ipca("01/01/2020")
    linhas = []
    for col in oficiais.columns.intersection(mensal.columns):
        a = pd.concat([mensal[col].round(2), oficiais[col]], axis=1, keys=["calc", "sgs"]).dropna()
        a = a[a.index >= "2021-01-01"]
        dif = (a["calc"] - a["sgs"]).abs()
        linhas.append([col, len(a), round(dif.max(), 2), round((dif > 0.011).mean() * 100, 1), str(a.index.max().date())])
    df = pd.DataFrame(linhas, columns=["serie", "meses", "dif_abs_max", "%_meses_dif>0,01", "ultimo_sgs"])
    print("\n=== IPCA: cálculo próprio x BCB/SGS (desde jan/21) ===")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    validar_ipca15()
    validar_ipca()
