"""Coleta de dados nas APIs do IBGE (SIDRA) e do Banco Central (SGS)."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd
import requests

SIDRA_URL = "https://apisidra.ibge.gov.br/values"
SIDRA_META_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

HEADERS = {"User-Agent": "Forluz-DIC-Relatorio-Inflacao/1.0"}


@dataclass(frozen=True)
class Indice:
    nome: str
    tabela_atual: int        # estrutura POF 2017-2018
    tabela_anterior: int     # estrutura POF 2008-2009 (histórico para núcleos DP/MS)
    inicio_atual: str
    var_mensal: int
    var_peso: int


INDICES = {
    "IPCA": Indice("IPCA", 7060, 1419, "202001", 63, 66),
    "IPCA-15": Indice("IPCA-15", 7062, 1705, "202002", 355, 357),
}

# Séries oficiais do BCB (SGS) — Nota Técnica BCB nº 57 (dez/2025), Anexo II. Só existem para o IPCA.
SGS_IPCA = {
    "ipca": 433,
    "adm": 4449,
    "livres": 11428,
    "alim_dom": 27864,
    "servicos": 10844,
    "industriais": 27863,
    "nao_duraveis": 10841,
    "semiduraveis": 10842,
    "duraveis": 10843,
    "ex0": 11427,
    "ex3": 27839,
    "dp": 16122,
    "ma": 11426,
    "ms": 4466,
    "p55": 28750,
    "difusao": 21379,
    "ex3_servicos": 29683,
    "ex3_industriais": 29684,
}


def _log(msg: str):
    """Registro de tempos (aparece nos logs do Streamlit Cloud em 'Manage app')."""
    print(f"[inflacao] {time.strftime('%H:%M:%S')} {msg}", flush=True)


def _get(url: str, tentativas: int = 3, timeout: tuple[int, int] = (10, 60)):
    """GET com limite de conexão/leitura (s) e poucas tentativas, para falhar rápido se a API travar."""
    erro = None
    for i in range(tentativas):
        inicio = time.time()
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            erro = e
            _log(f"tentativa {i + 1}/{tentativas} falhou em {time.time() - inicio:.1f}s: {url[:110]} ({e})")
            if i < tentativas - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"Falha ao acessar {url}: {erro}")


def ultimo_periodo(indice: str) -> str:
    """Último mês disponível no SIDRA (AAAAMM). Chamada leve, usada para detectar nova divulgação."""
    meta = _get(SIDRA_META_URL.format(tabela=INDICES[indice].tabela_atual), tentativas=2, timeout=(10, 20))
    return str(meta["periodicidade"]["fim"])


def _meses(inicio: str, fim: str) -> list[str]:
    """Lista de meses AAAAMM entre inicio e fim (inclusive)."""
    datas = pd.period_range(f"{inicio[:4]}-{inicio[4:]}", f"{fim[:4]}-{fim[4:]}", freq="M")
    return [p.strftime("%Y%m") for p in datas]


def _sidra_bloco(tabela: int, variaveis: list[int], periodos: list[str], categorias: str) -> pd.DataFrame:
    url = (f"{SIDRA_URL}/t/{tabela}/n1/all/v/{','.join(map(str, variaveis))}"
           f"/p/{','.join(periodos)}/c315/{categorias}/h/n")
    dados = _get(url)
    df = pd.DataFrame(dados)[["V", "D2C", "D3C", "D4N"]]
    df.columns = ["valor", "variavel", "periodo", "componente"]
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")  # '...' / '-' = não pesquisado
    return df


def sidra(tabela: int, variaveis: list[int], inicio: str, fim: str, bloco: int = 18,
          categorias: str = "all") -> pd.DataFrame:
    """Baixa as categorias (por padrão: geral, grupos, subgrupos, itens e subitens) em blocos de meses."""
    meses = _meses(inicio, fim)
    blocos = [meses[i:i + bloco] for i in range(0, len(meses), bloco)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        partes = list(ex.map(lambda b: _sidra_bloco(tabela, variaveis, b, categorias), blocos))
    return pd.concat(partes, ignore_index=True)


def _codigo(componente: str) -> str:
    return "0" if componente.lower().startswith("índice geral") else componente.split(".", 1)[0]


def _pivotar(df: pd.DataFrame, var_mensal: int, var_peso: int):
    df = df.copy()
    df["codigo"] = df["componente"].map(_codigo)
    df["data"] = pd.to_datetime(df["periodo"], format="%Y%m")
    nomes = df.drop_duplicates("codigo", keep="last").set_index("codigo")["componente"]
    v = df[df["variavel"] == str(var_mensal)].pivot_table(index="data", columns="codigo", values="valor", aggfunc="first")
    w = df[df["variavel"] == str(var_peso)].pivot_table(index="data", columns="codigo", values="valor", aggfunc="first")
    return v.sort_index(), w.sort_index(), nomes


def carregar_indice(indice: str, fim: str | None = None, inicio_historico: str = "201601") -> dict:
    """Retorna variações (V) e pesos (W) mensais por componente, juntando a estrutura atual e a anterior.

    A estrutura anterior (POF 2008-2009) é usada apenas como histórico para os núcleos DP (janela de 48 meses)
    e MS (suavização de 12 meses), conforme a NT BCB nº 57.
    """
    cfg = INDICES[indice]
    inicio = time.time()
    fim = fim or ultimo_periodo(indice)
    atual = sidra(cfg.tabela_atual, [cfg.var_mensal, cfg.var_peso], cfg.inicio_atual, fim)
    v, w, nomes = _pivotar(atual, cfg.var_mensal, cfg.var_peso)
    _log(f"{indice}: estrutura atual baixada em {time.time() - inicio:.1f}s")

    # Da estrutura anterior bastam o índice geral, os itens e o subitem usado nas proxies (≈10x menos dados)
    meta_ant = _get(SIDRA_META_URL.format(tabela=cfg.tabela_anterior), timeout=(10, 30))
    fim_ant = str(meta_ant["periodicidade"]["fim"])
    cats = [str(c["id"]) for c in meta_ant["classificacoes"][0]["categorias"]
            if _codigo(c["nome"]) == "0" or len(_codigo(c["nome"])) == 4 or _codigo(c["nome"]) == "8104002"]
    ant = sidra(cfg.tabela_anterior, [cfg.var_mensal, cfg.var_peso], inicio_historico, fim_ant,
                categorias=",".join(cats))
    v_ant, w_ant, _ = _pivotar(ant, cfg.var_mensal, cfg.var_peso)
    _log(f"{indice}: carga completa em {time.time() - inicio:.1f}s")
    v_ant, w_ant = _proxies_pof2020(v_ant, w_ant)
    v_ant = v_ant[v_ant.index < v.index.min()]
    w_ant = w_ant[w_ant.index < v.index.min()]

    return {
        "indice": indice,
        "V": v,
        "W": w,
        "V_hist": pd.concat([v_ant, v]).sort_index(),
        "W_hist": pd.concat([w_ant, w]).sort_index(),
        "nomes": nomes,
        "fim": fim,
    }


def _proxies_pof2020(v: pd.DataFrame, w: pd.DataFrame):
    """Tabela 4/8 da NT 57: proxies para 8101 e 8104 na estrutura jan/12–dez/19."""
    v, w = v.copy(), w.copy()
    if {"8101", "8104", "8104002"}.issubset(v.columns):
        a, b = w["8101"] * v["8101"], w["8104002"] * v["8104002"].fillna(0)
        wb = w["8104002"].fillna(0)
        v["8101"] = (a + b) / (w["8101"] + wb)
        c = w["8104"] * v["8104"] - b
        v["8104"] = c / (w["8104"] - wb)
        w["8101"], w["8104"] = w["8101"] + wb, w["8104"] - wb
    return v, w


def sgs(codigo: int, inicio: str = "01/01/2015") -> pd.Series:
    # Séries do SGS são opcionais (o cálculo próprio é idêntico): uma tentativa curta para não atrasar a página
    dados = _get(f"{SGS_URL.format(codigo=codigo)}?formato=json&dataInicial={inicio}", tentativas=1,
                 timeout=(5, 15))
    s = pd.DataFrame(dados)
    if s.empty:
        return pd.Series(dtype=float)
    s["data"] = pd.to_datetime(s["data"], format="%d/%m/%Y")
    return pd.to_numeric(s.set_index("data")["valor"], errors="coerce").rename(codigo)


def sgs_oficiais_ipca(inicio: str = "01/01/2019") -> pd.DataFrame:
    def baixar(codigo):
        try:
            return sgs(codigo, inicio)
        except Exception:  # noqa: BLE001 — série indisponível não deve derrubar o relatório
            return pd.Series(dtype=float)

    with ThreadPoolExecutor(max_workers=len(SGS_IPCA)) as ex:
        series = dict(zip(SGS_IPCA, ex.map(baixar, SGS_IPCA.values())))
    return pd.DataFrame(series).sort_index()


