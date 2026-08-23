# Desigualdade regional no cuidado ao diabetes no SUS

**Projeto de Parceria — EBAC / Semantix**
Data: 2026-08-23 · Autor: Maykon (maykongc@gmail.com)
Status: design aprovado, pronto para plano de implementação

---

## 1. O problema

**Pergunta central:** o SUS entrega o mesmo cuidado ao diabético em todo o território brasileiro — e, onde não entrega, quem paga a conta?

O diabetes é uma doença crônica cuja gravidade não está na doença em si, mas nas complicações que surgem quando o acompanhamento falha: pé diabético que evolui para amputação, insuficiência renal, cegueira, internação por descompensação metabólica. Essas complicações são majoritariamente evitáveis com atenção primária adequada. Uma internação por complicação de diabetes é, portanto, um indicador de falha assistencial anterior — não um evento aleatório.

Três características tornam o problema adequado à análise de dados:

1. **A falha é mensurável.** Cada internação evitável deixa um registro administrativo (AIH) com município de residência, diagnóstico, procedimento, custo e desfecho.
2. **A causa provável é observável.** A cobertura de atenção primária de cada município é publicada mensalmente pelo Ministério da Saúde.
3. **A desigualdade é hipótese, não conclusão.** Se o cuidado fosse homogêneo, a taxa de internação evitável ajustada por idade seria semelhante entre municípios. Quantificar o quanto ela não é constitui o núcleo do trabalho.

**Relevância.** O Brasil está entre os países com maior número absoluto de pessoas com diabetes, e o diabetes é a principal causa de amputação não traumática de membro inferior. Cada amputação representa custo hospitalar direto, perda de capacidade produtiva, provável benefício previdenciário e um desfecho irreversível para a pessoa. Um mapa que identifique onde essas amputações se concentram, controlando pelo perfil etário local, é insumo direto para priorização orçamentária em saúde.

**Eixo analítico: choque e recuperação desigual.** A janela 2019–2024 contém um ano de referência pré-pandemia (2019), dois anos de forte distorção assistencial (2020–2021) e três de recuperação (2022–2024). A pandemia interrompeu o acompanhamento do doente crônico em todo o país; a hipótese é que, onde a atenção primária já era frágil, essa interrupção se converteu em desfechos graves — e que a recuperação posterior não foi uniforme.

---

## 2. Coleta de dados

### 2.1 Fontes — núcleo da análise

| Fonte | Conteúdo | Tipo | Acesso | Verificado |
|---|---|---|---|---|
| **SIH/SUS** (`RD*.dbc`) | Internação individual: município de residência, CID-10 principal e secundário, procedimento, valor pago, dias de permanência, óbito, idade, sexo | Estruturado, ~1.944 arquivos | FTP DATASUS `/dissemin/publicos/SIHSUS/200801_/Dados/` | Sim — `RDAC1401.dbc` … `RDSP2412.dbc` (17,8 MB) |
| **SIM** (`DO*.dbc`) | Óbitos com causa básica, município, idade, sexo | Estruturado | FTP DATASUS `/dissemin/publicos/SIM/CID10/DORES/` | Sim — `DOTO2024.dbc` |
| **e-Gestor AB** | Cobertura mensal de Atenção Básica e Estratégia Saúde da Família por município | Estruturado (CSV/XLS) | Download direto | Sim — HTTP 200 |
| **CNES** (`LT*.dbc`) | Leitos por município e tipo | Estruturado | FTP DATASUS `/dissemin/publicos/CNES/200508_/Dados/LT/` | Sim — arquivos mensais |

### 2.2 Fontes — denominadores e contexto

| Fonte | Conteúdo | Acesso | Verificado |
|---|---|---|---|
| **IBGE / SIDRA** agregado 4714 | População do Censo 2022 por município, sexo e faixa etária | API REST | Sim — 5.570 municípios, 203.080.756 hab |
| **IBGE malhas** | GeoJSON dos municípios para mapas | API REST | Sim — HTTP 200 |
| **Atlas Brasil (PNUD)** | IDHM municipal (2010) | Download direto | contexto apenas |
| **VIGITEL** | Prevalência autorreferida de diabetes nas capitais | Download direto | validação apenas |
| **Base dos Dados** (`br_ms_sih`) | SIH já tratado em BigQuery | SQL / BigQuery | Sim — HTTP 200, rota de contingência |

### 2.3 Filtro de seleção

**Regra:** `DIAG_PRINC` pertencente ao intervalo CID-10 **E10–E14** (diabetes mellitus, todos os tipos).

Optou-se pelo filtro simples em vez de um filtro composto que também capturaria amputações codificadas com o diabetes como diagnóstico secundário.

**Consequência declarada:** o indicador de amputação passa a medir "entre as internações cuja causa principal é o diabetes, quantas terminam em amputação de membro inferior". É internamente consistente e mais simples de explicar, mas **subestima o total absoluto de amputações por pé diabético no país**. Como o viés é aproximadamente uniforme entre municípios, o ranking comparativo se sustenta.

**Limitação a declarar no relatório:** práticas de codificação podem variar entre regiões, e essa variação é uma fonte de viés residual num estudo cujo objeto é justamente a comparação regional.

Amputações são identificadas dentro do conjunto filtrado pelos procedimentos do grupo SIGTAP **04.08.05** (amputação/desarticulação de membros inferiores). A lista exata de códigos deve ser confirmada contra a tabela SIGTAP vigente durante a implementação.

### 2.4 Restrição técnica que determina a arquitetura

Os microdados do DATASUS são distribuídos em `.dbc` — formato proprietário (DBF comprimido). A leitura exige `datasus-dbc` ou `PySUS`, que compilam extensões nativas.

**Verificado empiricamente:** `pip install datasus-dbc` **falha** no ambiente local (Windows, Python 3.13.14) por ausência de wheel e falha de build. `dbfread` 2.0.7 instala, mas lê apenas `.dbf`, não `.dbc`.

**Decisão:** toda a ingestão ocorre no **Google Colab** (Linux, Python 3.11), onde a biblioteca funciona e o Spark já está disponível. Para a máquina local desce apenas a camada gold, em CSV/Parquet.

---

## 3. Modelagem

### 3.1 Arquitetura do pipeline

Estratégia: **filtrar cedo**. Processa-se um arquivo por vez, descartando o bruto imediatamente após a extração.

```
baixa RDxx.dbc -> converte -> filtra E10-E14 -> grava Parquet -> apaga o .dbc
```

São aproximadamente 6 GB de `.dbc` bruto. Como o filtro por CID remove a grande maioria das AIHs, o disco nunca retém mais que um arquivo bruto por vez, e cada arquivo processado constitui um checkpoint natural.

**Camadas (medallion):**

- **Bronze** (Colab) — AIHs de diabetes, 2019–2024, no grão original de internação. Particionado por UF e ano.
- **Silver** (Colab, PySpark) — agregação para **município × ano × faixa etária × sexo**, com joins de população (IBGE), cobertura de APS (e-Gestor) e leitos (CNES). É aqui que o PySpark se justifica: joins e agregações sobre milhões de linhas.
- **Gold** — tabela `municipio_ano`: 5.570 municípios × 6 anos, aproximadamente **33 mil linhas**. Poucos MB. É o único artefato que trafega do Colab para a máquina local.
- **Local** — padronização etária, ICVD, correlações e EDA em pandas + DuckDB.
- **Publicação** — CSV para Google Sheets, consumido pelo Power BI.

```
DATASUS FTP -+
IBGE API ----+--> COLAB (bronze->silver) --> gold.csv --> LOCAL (pandas/DuckDB)
e-Gestor ----+         [PySpark]                33k          |
CNES --------+     checkpoint no Drive         linhas        v
                                                    Google Sheets --> Power BI
```

### 3.2 Limpeza obrigatória

- **Idade:** o SIH codifica idade em `IDADE` + `COD_IDADE` (unidade: dias, meses, anos). Converter tudo para anos completos antes de qualquer faixa etária.
- **Município:** códigos IBGE de 6 dígitos no SIH contra 7 dígitos no IBGE — compatibilizar. Tratar municípios criados ou extintos no período.
- **Pandemia:** 2020–2021 é tratado como bloco analítico explícito, nunca interpolado nem lido como tendência natural.
- **Duplicatas:** AIHs de continuação (`IDENT` = 5) não devem ser contadas como novas internações.

### 3.3 Padronização etária

Método **direto**, com a população do **Censo 2022** como padrão nacional.

```
taxa_padronizada(m) = SOMA_i [ casos(m,i) / pop(m,i) ] * w(i)
onde  w(i) = pop_padrao(i) / pop_padrao_total
```

Faixas: `<30, 30–39, 40–49, 50–59, 60–69, 70–79, 80+`.

Responde: "qual seria a taxa deste município se ele tivesse a composição etária do Brasil?" — tornando a comparação entre municípios legítima.

### 3.4 O índice ICVD

Quatro componentes, todos orientados na mesma direção (maior = pior cuidado):

| Componente | Direção | Captura |
|---|---|---|
| Taxa de internação por diabetes padronizada por idade | Maior = pior | Falha da APS em evitar descompensação |
| % de internações com amputação de MMII | Maior = pior | Paciente chegou tarde |
| Letalidade hospitalar | Maior = pior | Gravidade na chegada e capacidade de resposta |
| Cobertura de Atenção Primária **(invertida)** | Menor = pior | Causa estrutural |

**Excluídos deliberadamente:** gasto médio por internação e leitos por habitante. Ambos são ambíguos — gasto alto pode indicar caso grave ou cuidado melhor; poucos leitos reduzem internação sem melhorar desfecho. Permanecem como variáveis de contexto na discussão, fora do índice.

**Pesos: iguais, 25% cada.** Não há base empírica para hierarquizar os componentes, e parcimônia é a posição honesta na ausência de evidência (precedente: o IDH combina suas dimensões com pesos iguais). Argumento técnico adicional: amputação é o evento mais raro e portanto o mais ruidoso; aumentar seu peso elevaria a variância do índice sem elevar a informação.

### 3.5 Números pequenos

Um município de 900 habitantes com uma internação e um óbito registra 100% de letalidade e lidera o ranking de piores do país — ruído puro.

**Duas defesas:**

1. **Corte de eventos mínimos: 20 internações no período.** Abaixo disso, o município fica fora do **ranking**, aparecendo no mapa em cinza com rótulo "dados insuficientes". Nunca excluído em silêncio.
2. **Winsorização em p1/p99** antes da normalização.

**Análise de impacto do corte** (dados reais do Censo 2022, assumindo taxa nacional de aproximadamente 70 internações por 100 mil habitantes por ano — premissa a validar contra os dados observados):

| Corte | Pop. mínima aprox. | Municípios fora | % da população mantida |
|---|---|---|---|
| 10 | ~2.400 | 256 (4,6%) | 99,8% |
| **20** | **~4.800** | **1.230 (22,1%)** | **98,0%** |
| 30 | ~7.100 | 1.958 (35,2%) | 95,9% |
| 50 | ~11.900 | 2.922 (52,5%) | 91,4% |

**Restrição crítica de aplicação.** Municípios muito pequenos concentram-se no Sul e Centro-Oeste, não no Norte/Nordeste:

| Região | % de municípios abaixo de ~4.800 hab |
|---|---|
| Sul | 35,3% |
| Centro-Oeste | 29,3% |
| Sudeste | 22,7% |
| Norte | 19,1% |
| Nordeste | 12,5% |

Aplicar o corte ao estudo inteiro removeria quase três vezes mais municípios do Sul que do Nordeste, comparando regiões sob critérios de inclusão distintos — falha metodológica grave num trabalho cujo objeto é a comparação regional.

**Portanto: o corte de 20 vale exclusivamente para o ranking municipal do ICVD. Todas as análises regionais e por UF utilizam os 5.570 municípios.** Na agregação regional o problema de números pequenos desaparece, pois o denominador se torna grande.

### 3.6 Normalização e comparabilidade entre os dois momentos

Cada componente é normalizado para 0–1 por min-max após winsorização; o ICVD é a média aritmética dos quatro. Zero representa o melhor cuidado observado, um representa o pior.

O ICVD é calculado em **dois momentos**: **2019** (linha de base) e **2023–24** (situação atual).

**Requisito não negociável:** mínimos e máximos da normalização devem ser calculados sobre os **dois períodos combinados**, numa escala única. Normalizar cada período isoladamente faria com que todo município tivesse, por construção, um melhor e um pior em cada recorte, tornando a diferença entre eles sem significado.

Com escala comum:

```
recuperacao = ICVD(2023-24) - ICVD(2019)
```

Valores positivos indicam piora; negativos, recuperação. Este delta sustenta o eixo "choque e recuperação desigual".

### 3.7 Análise de sensibilidade

Recalcular o ICVD sob três esquemas alternativos de pesos e medir a estabilidade do **top 100** por sobreposição percentual e correlação de Spearman. Ranking estável converte a questão dos pesos de vulnerabilidade em nota de rodapé. Instabilidade exige revisão do índice antes da entrega.

### 3.8 Trilha de gênero — hipótese a testar

Fora do índice. Compara homens e mulheres em taxa padronizada de internação, proporção de amputação, letalidade e idade média na internação, nacionalmente e por região.

**Hipótese:** homens apresentam desfechos mais graves apesar de prevalência semelhante, o que apontaria para diferença na procura por cuidado preventivo, não na incidência da doença.

**Teste:** comparação das taxas padronizadas por sexo com intervalos de confiança. A hipótese é sustentada se a diferença em amputação e letalidade for consistente entre regiões enquanto a diferença de prevalência (VIGITEL) não for. Confirmada ou refutada, o resultado é reportado com sua evidência.

### 3.9 Validação

Sem estas checagens, um erro de filtro se converte em "insight":

1. **Completude** — 1.944 arquivos esperados contra processados; pendências listadas com motivo.
2. **Conferência externa** — total de internações por UF e ano comparado ao **TabNet do DATASUS** sob o mesmo filtro. É a validação mais valiosa do projeto e deve constar do relatório.
3. **Integridade dos denominadores** — todo município com internação precisa ter população; órfãos são reportados, nunca descartados silenciosamente.
4. **Sanidade das métricas** — taxa negativa, taxa implausível ou ICVD fora do intervalo [0,1] interrompem a execução.

---

## 4. Visualização e entrega

### 4.1 Ferramenta

**Power BI Desktop** (verificado: versão 2.156.951.0 instalada via Microsoft Store).

**Desvio consciente do briefing:** a etapa 5 do enunciado especifica Looker Studio. A substituição por Power BI foi decidida pelo autor e deve ser confirmada com a tutoria da EBAC. A camada analítica é indiferente à escolha.

**Limitação de publicação:** o Power BI Service não aceita cadastro com e-mail pessoal (`@gmail.com`), apenas contas corporativas ou acadêmicas. Não haverá link público. A entrega consiste em `.pbix` versionado, PDF exportado e PNGs no README — formato que expõe o modelo de dados e as medidas DAX, evidência técnica superior a um link.

### 4.2 Páginas

**Página 1 — Panorama Brasil.** KPIs (internações, amputações, óbitos, gasto SUS); série mensal 2019–2024 com a faixa 2020–21 sombreada; mapa coroplético do ICVD 2023–24, com municípios sob o corte em cinza. Filtros: região, UF, ano, sexo, faixa etária.

**Página 2 — Desigualdade e recuperação.** Núcleo do projeto. Dispersão ICVD 2019 (x) contra ICVD 2023–24 (y) com diagonal de referência e quadrantes rotulados; barras de ICVD médio por região comparando os dois momentos; dispersão cobertura de APS contra taxa de internação padronizada; tabelas do top-20 piores e do top-20 que mais melhoraram.

**Página 3 — Recorte de gênero.** Homens contra mulheres em taxa padronizada, proporção de amputação, letalidade e idade média na internação, quebrado por região, com o resultado do teste da hipótese.

### 4.3 Fluxo de dados até o dashboard

`municipio_ano.csv` é publicado no **Google Sheets** como camada de tabela compartilhável. O Power BI consome do Sheets e mantém o CSV local como fonte redundante — se o Sheets falhar durante a apresentação, o CSV sustenta o dashboard.

### 4.4 Estrutura do repositório

```
projeto-diabetes-sus/
├── README.md                     porta de entrada, com os PNGs
├── requirements.txt
├── docs/
│   ├── 01-problema.md            etapa 1 do briefing
│   ├── 02-coleta-de-dados.md     topico "coleta de dados"
│   ├── 03-modelagem.md           topico "modelagem"
│   ├── 04-conclusoes.md          topico "conclusoes" e insights
│   └── img/
├── notebooks/
│   ├── 01_ingestao_colab.ipynb   PySpark, executa no Colab
│   ├── 02_eda.ipynb              local
│   └── 03_indice_icvd.ipynb      local
├── sql/consultas_duckdb.sql
├── data/gold/municipio_ano.csv   ~33k linhas, versionavel
├── dashboard/
│   ├── diabetes_sus.pbix
│   ├── dashboard.pdf
│   └── previews/*.png
└── .gitignore                    bloqueia bronze/silver
```

Os três tópicos exigidos na entrega — **coleta de dados, modelagem, conclusões** — possuem um arquivo dedicado cada, nomeado de forma correspondente.

---

## 5. Mapa entregáveis contra briefing

| Etapa do briefing | Artefato |
|---|---|
| 1. Dissertar sobre o problema | `docs/01-problema.md` |
| 2. Fontes de dados e método de coleta | `docs/02-coleta-de-dados.md` |
| 3. EDA (Sheets, SQL, Python, PySpark) | `notebooks/01–03`, `sql/consultas_duckdb.sql`, Google Sheets |
| 4. Relatório de insights | `docs/04-conclusoes.md` |
| 5. Visualização | `dashboard/` em Power BI — desvio declarado em 4.1 |
| Entrega via GitHub com documentação em Markdown | Repositório completo e `README.md` |

---

## 6. Ambiente

**Local (verificado):** Windows 10 Pro · Python 3.13.14 · Java 25 · Git 2.46.2 · pandas 2.2.3 · numpy 2.4.4 · matplotlib 3.10.9 · requests 2.33.1 · duckdb 1.5.2 · Power BI Desktop 2.156.951.0

**A instalar localmente:** jupyter, seaborn, plotly, openpyxl, pyarrow, e uma biblioteca de mapas (geobr ou geopandas)

**Ausentes por decisão:** pyspark local (executa no Colab), gh CLI (repositório criado pela interface web)

**Colab:** pyspark, datasus-dbc, pyarrow — instalados por célula no notebook.

---

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Sessão do Colab cai durante a ingestão | Checkpoint por arquivo no Google Drive; ingestão idempotente, reexecução pula o que já existe |
| FTP do DATASUS instável | Retry com backoff; após 3 falhas o arquivo entra em lista de pendências sem derrubar a execução |
| `datasus-dbc` quebra também no Colab | Rota de contingência: Base dos Dados (`br_ms_sih`) via BigQuery |
| Total não bate com o TabNet | Bloqueia a entrega até reconciliação — a validação existe para isso |
| Ranking instável sob pesos alternativos | Revisão do índice antes da entrega, reportada ao autor assim que detectada |
| Prazo de uma semana | Escopo já reduzido (2019–24, quatro componentes, três páginas); o modelo observado-contra-esperado permanece fora |

---

## 8. Fora de escopo

- Modelo de regressão observado-contra-esperado (considerado e descartado por prazo)
- Previsão ou projeção futura — o trabalho é diagnóstico
- Dados individuais identificáveis — apenas microdados públicos anonimizados
- Análise de custo-efetividade com premissas financeiras próprias
- Publicação no Power BI Service (impossibilitada pelo tipo de conta)
