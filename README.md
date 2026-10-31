# Monitor de Inflação — IPCA e IPCA-15

Relatório interativo (Streamlit) de análise da inflação brasileira, produzido pela **Forluz — Diretoria de
Investimentos e Controle (DIC)**. Todos os dados vêm de APIs públicas e se atualizam sozinhos quando o IBGE divulga um
novo mês.

## O que o relatório mostra

O seletor **IPCA / IPCA-15** fica na barra lateral.

| Aba | Conteúdo |
|---|---|
| Visão geral | Indicadores do mês; barras de variação mensal, acumulado no ano e acumulado em 12 meses (janela padrão de 24 meses, ajustável) |
| Tabela resumo | Variação por grupo e classificação especial nos últimos 3 meses, no ano e em 12 meses, com peso e contribuição para o índice cheio |
| Grupos especiais e núcleos | Para cada série: variação mensal, no ano, em 12 meses e média móvel de 3 meses (simples ou anualizada) |
| Difusão | Percentual de subitens com alta, com média móvel de 3 meses |
| Contribuições | Tabelas roláveis por grupo, subgrupo, item e subitem (peso, variação e contribuição) e as maiores contribuições positivas e negativas |
| Metodologia | Fontes e regras de cálculo |

Séries: administrados, energia elétrica, gasolina, preços livres, alimentação no domicílio, bens industriais,
industriais subjacentes, serviços, serviços subjacentes, serviços intensivos em trabalho, núcleos EX0, EX3, MS, DP e P55,
e a média dos núcleos.

## Fontes e metodologia

- **IBGE/SIDRA:** tabelas 7060 (IPCA) e 7062 (IPCA-15), mais as tabelas 1419 e 1705 como histórico da estrutura anterior.
- **BCB/SGS:** séries oficiais do IPCA (códigos da Nota Técnica BCB nº 57, Anexo II).
- **Cálculos:** [Nota Técnica BCB nº 57 (dez/2025)](https://www.bcb.gov.br/content/publicacoes/notastecnicas/NT_57_202512.pdf),
  com os vetores de agregação oficiais do arquivo de apoio
  [`Vetores_NT_57.xlsx`](https://www.bcb.gov.br/content/publicacoes/notastecnicas_arq/Vetores_NT_57.xlsx), salvos em
  `data/vetores_bcb_jan20.csv` (aba jan/20–presente), mais a coluna de serviços intensivos em trabalho (boxe do RI de dez/2013).
- **Contribuição** = peso mensal × variação mensal ÷ 100 (pontos percentuais).

O BCB só publica essas séries para o IPCA. No IPCA-15, elas são calculadas com a mesma metodologia.

### Validação

Rode `python scripts/validar.py`. O script compara:

1. o **IPCA** calculado com as séries oficiais do SGS. Desde jan/2021, todas as séries (grupos especiais, EX0, EX3,
   MS, DP, P55, MA, difusão, serviços e industriais subjacentes) batem com 2 casas decimais;
2. o **IPCA-15** calculado com uma tabela de referência de mercado (ago–out/26).

## Atualização automática

- O app consulta o último mês disponível no SIDRA a cada 10 minutos. Quando o IBGE divulga um mês novo (às 9h), os
  dados são baixados e recalculados na hora.
- No IPCA, usa o valor oficial do SGS quando já publicado. Antes disso, usa o cálculo próprio, que dá o mesmo resultado.
- O botão **"Atualizar dados agora"** limpa o cache e força uma nova consulta.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar (GitHub + Streamlit Community Cloud)

1. Crie um repositório no GitHub e envie esta pasta:
   ```bash
   git init && git add . && git commit -m "Monitor de inflação"
   git branch -M main
   git remote add origin https://github.com/<usuario>/<repositorio>.git
   git push -u origin main
   ```
2. Em [share.streamlit.io](https://share.streamlit.io), clique em **Create app**, escolha o repositório, a branch `main`
   e o arquivo `app.py`, e faça o deploy.
3. Cada `git push` reimplanta o app. Os dados se atualizam sozinhos, sem nenhum commit.

## Estrutura

```
app.py                     interface Streamlit
inflacao/dados.py          coleta (SIDRA e SGS)
inflacao/calculos.py       agregações, núcleos, acumulados e contribuições
inflacao/graficos.py       gráficos Plotly no padrão Forluz
data/vetores_bcb_jan20.csv vetores de agregação oficiais do BCB
scripts/validar.py         validação contra séries oficiais e referência
assets/logo_forluz.png     símbolo Forluz
```
