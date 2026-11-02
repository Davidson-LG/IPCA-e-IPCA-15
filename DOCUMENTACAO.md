# Monitor de Inflação — IPCA e IPCA-15

**Documentação técnica e funcional**
Forluz · Diretoria de Investimentos e Controle (DIC)

---

## 1. Objetivo

O Monitor de Inflação é um relatório web interativo que acompanha o **IPCA** e o **IPCA-15**. Ele:

- baixa os dados direto das APIs públicas do IBGE e do Banco Central;
- recalcula grupos especiais, núcleos, difusão e contribuições com a metodologia oficial do BCB;
- se atualiza sozinho quando o IBGE divulga um mês novo, sem trabalho manual.

O app foi feito em Python com Streamlit e fica publicado no Streamlit Community Cloud. O código está no GitHub, e cada alteração enviada ao repositório é publicada automaticamente.

---

## 2. O que o relatório mostra

A barra lateral tem:
- o seletor **IPCA / IPCA-15**;
- a janela dos gráficos (12 a 60 meses, padrão 24);
- a opção de exibir os valores nas barras;
- o botão **"Atualizar dados agora"**.

| Aba | Conteúdo |
|---|---|
| **Visão geral** | Indicadores do último mês e gráficos de barras da variação mensal, do acumulado no ano e do acumulado em 12 meses |
| **Tabela resumo** | Grupos e classificações especiais nos últimos 3 meses, no ano e em 12 meses, com peso e contribuição de cada um para o índice cheio |
| **Grupos especiais e núcleos** | Para a série escolhida: variação mensal, no ano, em 12 meses e média móvel de 3 meses (simples ou anualizada) |
| **Difusão** | Percentual de subitens com alta no mês, com média móvel de 3 meses |
| **Contribuições** | Tabelas por grupo, subgrupo, item e subitem (peso, variação e contribuição) no mês, no ano, em 12 meses ou na janela escolhida, com filtro por nome; gráfico das maiores contribuições positivas e negativas; e a evolução mês a mês de qualquer componente |
| **Metodologia** | Resumo das fontes e regras de cálculo |

Os gráficos de barras mostram o valor exato ao passar o mouse. Valores positivos aparecem em laranja e negativos em azul, nas cores da Forluz.

**Séries disponíveis:**
- **Administrados:** total, energia elétrica e gasolina;
- **Preços livres:** total e alimentação no domicílio;
- **Bens industriais:** total e industriais subjacentes;
- **Serviços:** total, serviços subjacentes e serviços intensivos em mão de obra;
- **Bens:** duráveis, semiduráveis e não duráveis;
- **Núcleos:** EX0, EX3, MS, DP, P55 e a média dos núcleos.

---

## 3. De onde vêm os dados

| Fonte | O que fornece | Uso |
|---|---|---|
| **IBGE / SIDRA** — tabelas 7060 (IPCA) e 7062 (IPCA-15) | Variação mensal e peso de todos os componentes (geral, grupos, subgrupos, itens e subitens) desde 2020 | Base de todos os cálculos |
| **IBGE / SIDRA** — tabelas 1419 (IPCA) e 1705 (IPCA-15) | Mesmos dados na estrutura de pesos anterior (2016–2019) | Só histórico dos núcleos DP e MS, que precisam de 48 e 12 meses passados |
| **IBGE / SIDRA** (consulta leve do último mês) | Último mês divulgado | Saber se saiu um mês novo. A API de metadados do IBGE (servicodados.ibge.gov.br) fica só como reserva, porque o Streamlit Cloud não consegue acessá-la |
| **Banco Central / SGS** | Séries oficiais do IPCA (núcleos, grupos especiais, difusão) | Quando disponíveis, substituem o cálculo próprio no IPCA. O BCB não publica essas séries para o IPCA-15 |

---

## 4. Como os números são calculados

A base é a **Nota Técnica BCB nº 57 (dez/2025)**. As regras de classificação vêm do arquivo oficial de vetores do BCB
(`Vetores_NT_57.xlsx`), que indica a qual grupo especial e núcleo pertence cada subitem do IPCA. Ele está salvo em
`data/vetores_bcb_jan20.csv`.

### 4.1 Grupos especiais e núcleos por exclusão

A variação de um agregado é a média das variações dos seus componentes, ponderada pelos pesos do mês:

> variação do agregado = Σ (peso × variação) ÷ Σ peso

Isso vale para os administrados, preços livres, serviços, industriais, bens duráveis/semiduráveis/não duráveis e
para os núcleos **EX0** e **EX3**. Os serviços e industriais subjacentes são as partes de serviços e de industriais do
EX3.

Os **serviços intensivos em mão de obra** seguem o boxe do Relatório de Inflação do BCB (dez/2013), que lista 9 subitens:
- mão de obra (reparos);
- médico;
- dentista;
- fisioterapeuta;
- psicólogo;
- costureira;
- manicure;
- empregado doméstico;
- cabeleireiro e barbeiro.

### 4.2 Núcleos estatísticos

| Núcleo | Regra |
|---|---|
| **MA** (médias aparadas) | Ordena os itens pela variação e descarta 20% do peso em cada ponta. É a média ponderada do que sobra |
| **MS** (médias aparadas com suavização) | Igual ao MA, mas 9 itens com reajustes concentrados em poucos meses (ex.: energia, gasolina, educação) entram suavizados pela média geométrica dos últimos 12 meses |
| **DP** (dupla ponderação) | Cada item tem o peso dividido pela sua volatilidade: o desvio-padrão da diferença entre o item e o IPCA nos 48 meses anteriores. Itens voláteis pesam menos |
| **P55** | Percentil 55 da distribuição das variações dos subitens, ponderada pelos pesos |
| **Média dos núcleos** | Média simples de EX0, EX3, MS, DP e P55. No ano e em 12 meses, é a média dos acumulados de cada núcleo |

### 4.3 Difusão

Percentual de subitens pesquisados no mês que tiveram variação positiva. Não usa pesos.

### 4.4 Contribuição

> contribuição (p.p.) = peso do mês × variação do mês ÷ 100

Mostra quantos pontos percentuais cada componente acrescentou ao índice no mês. A soma das contribuições dos grupos é igual ao índice cheio.

Na aba Contribuições, também dá para escolher um período (no ano, 12 meses ou a janela da barra lateral) terminando no mês de referência:

- **Variação:** acumulada no período, por capitalização composta das variações mensais.
- **Peso:** o do mês de referência.
- **Contribuição:** soma das contribuições mensais, cada uma corrigida pela inflação acumulada do índice até o mês anterior:

  > contribuição no período = Σₜ (pesoₜ × variaçãoₜ ÷ 100) × Πₛ<ₜ (1 + IPCAₛ ÷ 100)

  Assim, a soma das contribuições dos grupos é igual à variação acumulada do índice no período, a menos de centésimos de arredondamento dos dados do IBGE.

Abaixo das tabelas, o gráfico **Evolução de um componente** mostra, para qualquer grupo, subgrupo, item ou subitem (ex.: picanha), a variação mês a mês e o acumulado em 12 meses na janela escolhida.

### 4.5 Acumulados e média móvel

- **No ano:** produto de (1 + variação/100) desde janeiro, menos 1.
- **12 meses:** o mesmo produto, nos últimos 12 meses.
- **Média móvel de 3 meses:** média simples dos últimos 3 meses. A versão anualizada compõe os 3 meses e eleva a 4 (equivalente a 12 meses): [(1 + v₁/100)(1 + v₂/100)(1 + v₃/100)]⁴ − 1.

---

## 5. Validação

O script `scripts/validar.py` confere os cálculos com duas referências.

**1. IPCA contra as séries oficiais do BCB.** Desde jan/2021 (69 meses), todas as séries batem com o SGS em 2 casas decimais:
- grupos especiais;
- EX0, EX3, MS, DP, P55 e MA;
- difusão;
- serviços e industriais subjacentes.

**2. IPCA-15 contra uma tabela de mercado (ago–out/2026).**
- **Batem:** índice cheio, grupos, energia, gasolina, administrados, livres, duráveis, EX3, DP, P55, difusão e média dos núcleos.
- **Pequenas diferenças (até 0,04 p.p.):** serviços, industriais, não duráveis, EX0 e MS. Elas vêm da classificação proprietária usada na tabela de referência, não de erro de cálculo. O cálculo deste relatório segue a classificação oficial do BCB, a mesma que reproduz o IPCA exatamente.
- **Erro na referência:** em setembro, a tabela de mercado traz alimentação no domicílio e fora do domicílio com os valores trocados. O correto é 0,38 e 0,44.

Para rodar a validação:

```bash
python scripts/validar.py
```

---

## 6. Atualização dos dados

1. A cada 10 minutos, o app consulta o último mês disponível no IBGE (uma chamada leve).
2. Quando o IBGE divulga um mês novo (normalmente às 9h), os dados são baixados e recalculados no próximo acesso.
3. No IPCA, os valores oficiais do SGS substituem o cálculo próprio assim que o BCB os publica. Antes disso, vale o cálculo próprio, que dá o mesmo resultado.
4. O botão **"Atualizar dados agora"** limpa o cache e força uma nova consulta.

Os dados ficam em cache: o primeiro acesso após uma divulgação demora mais, e os seguintes abrem na hora.

**Tempo de carregamento:** o primeiro acesso costuma levar de 5 a 20 segundos, mas pode chegar a cerca de 1 minuto quando as APIs do IBGE ou do BCB estão lentas. Para não travar a página:
- as chamadas têm tempo máximo de espera;
- as séries do BCB são baixadas em paralelo;
- se o BCB não responder, o app usa o cálculo próprio.

O tempo de cada etapa aparece nos logs do Streamlit Cloud (**Manage app → logs**), em linhas que começam com `[inflacao]`.

---

## 7. Estrutura dos arquivos

```
inflacao-forluz/
├── app.py                      interface (abas, tabelas, botões)
├── inflacao/
│   ├── dados.py                coleta nas APIs do IBGE (SIDRA) e do BCB (SGS)
│   ├── calculos.py             agregações, núcleos, difusão, acumulados e contribuições
│   └── graficos.py             gráficos no padrão visual Forluz
├── data/vetores_bcb_jan20.csv  classificação oficial dos subitens (BCB NT 57)
├── scripts/validar.py          validação contra o BCB e a tabela de referência
├── assets/logo_forluz.png      logotipo
├── .streamlit/config.toml      cores e tema do app
├── requirements.txt            bibliotecas Python necessárias
├── README.md                   instruções resumidas de uso e publicação
└── DOCUMENTACAO.md             este documento
```

---

## 8. Como usar e manter

**Rodar no computador:**

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Publicar alterações:** envie os arquivos alterados ao repositório no GitHub. O Streamlit Cloud reimplanta o app em alguns minutos. A pasta `__pycache__` não deve ir para o repositório; o `.gitignore` já a exclui.

**Quando pode ser preciso mexer no código:**
- **Nova estrutura de pesos do IPCA** (nova POF): o IBGE cria tabelas novas no SIDRA, e o BCB publica novos vetores de classificação. Será preciso atualizar os números das tabelas em `inflacao/dados.py` e o arquivo `data/vetores_bcb_jan20.csv`.
- **Mudança de metodologia do BCB:** revisar `inflacao/calculos.py` e rodar `scripts/validar.py` para confirmar que tudo continua batendo.
- **Mudança nas APIs:** os endereços estão no início de `inflacao/dados.py`.

---

*Produzido pela Diretoria de Investimentos e Controle — DIC*
