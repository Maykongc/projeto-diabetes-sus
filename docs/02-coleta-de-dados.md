# Coleta de dados

## 2.1 Fontes — núcleo da análise

| Fonte | Conteúdo | Tipo | Acesso | Verificado |
|---|---|---|---|---|
| **SIH/SUS** (`RD*.dbc`) | Internação individual: município de residência, CID-10 principal, procedimento (SIGTAP), valor pago, dias de permanência, óbito, idade, sexo | Estruturado, ~1.944 arquivos mensais | FTP DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados/RD{UF}{AA}{MM}.dbc` | Sim — arquivo de exemplo baixado por FTP e lido com sucesso durante o desenho do projeto |
| **SIM** (`DO*.dbc`) | Óbitos com causa básica, município, idade, sexo | Estruturado | FTP DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/` | Sim — 812 arquivos listados e um baixado (237 KB) por FTP durante o desenho do projeto |
| **Relatórios Públicos da APS** (sucessor do e-Gestor AB) | Cobertura mensal de Atenção Primária por município, em duas séries disjuntas: `/cobertura/ab` (2019–2020, truncada em 100%) e `/cobertura/aps` (2021–2024, sem teto) | Estruturado (JSON via API pública) | `https://relatorioaps-prd.saude.gov.br/cobertura/ab` e `.../cobertura/aps`, parâmetros `unidadeGeografica=MUNICIPIO`, `coUf`, `nuCompInicio`, `nuCompFim`. Automatizado em `scripts/baixar_cobertura_aps.py` | Sim — 33.418 linhas, 5.570 municípios, 2019–2024 |
| **CNES** (`LT*.dbc`) | Leitos por município e tipo, usado como variável de contexto | Estruturado | FTP DATASUS, `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/LT/` | Sim |

As três URLs de FTP acima usam o esquema `ftp://`, confirmado por esta sessão (download de um arquivo de exemplo do SIM e listagem de 812 arquivos no diretório do SIM). O notebook `notebooks/01_ingestao_colab.ipynb` acessa o mesmo host usando `https://` — isso não é um erro do notebook: o Google Colab consegue resolver esse host por HTTPS, o que nem toda rede local consegue (nesta sessão, `https://ftp.datasus.gov.br/...` expirou por timeout). É diferença de ambiente, não inconsistência a corrigir; o notebook permanece como está.

## 2.2 Fontes — denominadores e contexto

| Fonte | Conteúdo | Acesso | Verificado |
|---|---|---|---|
| **IBGE / SIDRA**, agregado 9514 | População do Censo 2022 por município, sexo e grupo etário quinquenal | API REST, `https://servicodados.ibge.gov.br/api/v3/agregados/9514/periodos/2022/variaveis/93?localidades=N6[N3[{uf}]]&classificacao=2[4,5]|287[{grupos}]` (o endpoint exige os parâmetros `localidades` e `classificacao` — chamado sem eles, como só a base da URL, devolve HTTP 500) | Sim — HTTP 200 com os parâmetros preenchidos (testado com UF=35, grupo 93089/93090); 5.570 municípios, 203.080.756 habitantes; script `scripts/baixar_populacao_ibge.py`, testado em `tests/test_populacao.py` |
| **IBGE malhas municipais** | Geometria dos municípios para o mapa coroplético | API REST, `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&intrarregiao=municipio` | Sim — HTTP 200 |
| **Atlas Brasil (PNUD)** | IDHM municipal, base Censo 2010 — contexto apenas; ver limitação da defasagem em `03-modelagem.md` e `04-conclusoes.md` | Download direto, `https://www.atlasbrasil.org.br/consulta/planilha` | Endereço público, não testado nesta sessão — responde 308 (redirecionamento) sobre HTTP; HTTPS não confirmado nesta rede |
| **VIGITEL** | Prevalência autorreferida de diabetes, capitais — validação apenas, usado no teste da hipótese de gênero (Seção 3.8 da modelagem) | Download direto, `https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/svsa/vigitel` | Sim — HTTP 200 |
| **Base dos Dados** (`br_ms_sih`) | SIH já tratado, disponível via SQL/BigQuery — rota de contingência caso a ingestão direta via `.dbc` falhe (Seção 2.4) | `https://basedosdados.org/dataset/br-ms-sih` | Sim — HTTP 200 |
| **TabNet DATASUS** | Totais oficiais de internação por UF e ano **por local de residência** (cubo `nruf.def`), usados só para reconciliação, nunca como fonte primária — Seção 3.9 da modelagem. Tem de ser o cubo de residência, e não o de local de internação (`niuf.def`), porque a camada gold agrega por `MUNIC_RES`: confrontar residência com internação geraria divergência sistemática em toda UF com fluxo de pacientes | `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nruf.def` | Sim — HTTP 200 |

O agregado SIDRA usado é o **9514** ("População residente, por sexo, idade e forma de declaração da idade" — Censo Demográfico 2022), variável 93, não o 4714 mencionado em versões preliminares do desenho do projeto: o número correto foi confirmado contra os metadados da API (`.../9514/metadados`) e é o que está de fato implementado em `scripts/baixar_populacao_ibge.py`.

## 2.3 Filtro de seleção

**Regra aplicada:** `DIAG_PRINC` pertencente ao intervalo CID-10 **E10 a E14** (diabetes mellitus, todos os tipos, como causa principal da internação).

A alternativa considerada era um filtro composto, que também capturaria internações em que o diabetes aparece como diagnóstico secundário — por exemplo, uma amputação registrada sob um diagnóstico principal diferente, com o diabetes listado como comorbidade. Optou-se pelo filtro simples.

**Consequência declarada desta escolha:** o indicador de amputação construído a partir deste filtro passa a medir "entre as internações cuja causa principal registrada é o diabetes, quantas terminam em amputação de membro inferior" — não "todas as amputações de membro inferior atribuíveis ao diabetes no país". Isso é internamente consistente, mais simples de explicar e de auditar, mas **subestima o total absoluto de amputações por pé diabético**, porque uma parcela real dessas amputações é registrada sob diagnóstico principal diferente do E10–E14. Essa subestimação é aceita conscientemente: como o viés de codificação é assumido aproximadamente uniforme entre municípios, o ranking comparativo entre eles se sustenta mesmo que o número absoluto de amputações não represente o universo completo do fenômeno. O ponto de comparação é relativo (quem está pior que quem), não uma contagem epidemiológica definitiva.

**Limitação a declarar no relatório final:** a suposição de uniformidade do viés de codificação entre regiões é uma suposição, não um fato verificado. Práticas de codificação hospitalar podem variar entre estados e entre tipos de hospital (público, filantrópico, universitário), e essa variação é uma fonte de viés residual justamente no tipo de comparação regional que é o objeto deste estudo. Ela é registrada como limitação em `04-conclusoes.md`.

Amputações são identificadas, dentro do conjunto já filtrado por CID-10, pelos procedimentos SIGTAP com prefixo **04.08.05** (amputação/desarticulação de membros inferiores). A lista exata de códigos dentro desse grupo foi confirmada contra a tabela SIGTAP vigente e está implementada em `src/diabetes_sus/config.py` (`SIGTAP_AMPUTACAO_MMII_PREFIXO`) e `src/diabetes_sus/filtros.py`.

## 2.4 Restrição técnica que determina a arquitetura

Os microdados do DATASUS são distribuídos em formato `.dbc` — um DBF comprimido, proprietário. Lê-lo exige a biblioteca `datasus-dbc` (ou a alternativa `PySUS`, que a usa internamente), que compila extensões nativas a partir do código-fonte.

**Verificado empiricamente durante o desenho do projeto:** `pip install datasus-dbc` falha no ambiente local (Windows, Python 3.13.14) por ausência de wheel pré-compilado para essa combinação de sistema operacional e versão do Python, e o build a partir do código-fonte também falha. A alternativa `dbfread` 2.0.7 instala sem problema, mas lê apenas `.dbf` puro — não descomprime `.dbc`.

**Decisão:** toda a etapa de ingestão (download, descompressão, filtro linha a linha) e a agregação com PySpark ocorrem no **Google Colab** (Linux, Python 3.11), ambiente em que `datasus-dbc` instala e funciona, e onde o Spark já está disponível sem configuração adicional. Da máquina local, o pipeline consome apenas o resultado final da agregação — a camada gold, em CSV — e todo o processamento subsequente (padronização etária, cálculo do índice, EDA) roda em pandas e DuckDB localmente. Essa divisão de responsabilidade entre Colab e máquina local é o que molda a arquitetura em camadas descrita em `03-modelagem.md`, Seção 3.1.

O passo a passo operacional de como rodar essa etapa manual está em `00-execucao-manual.md`.

## 2.5 Camada gold publicada

A tabela `municipio_ano.csv`, gerada pela ingestão no Colab, e as tabelas derivadas do índice ICVD (`icvd_municipio.csv`, `icvd_regiao.csv`, `genero_regiao.csv`), geradas pelo notebook `03_indice_icvd.ipynb`, são publicadas no Google Sheets como camada intermediária consumida pelo Power BI (ver `05-dashboard-powerbi.md`, Seção 4.3 do desenho do projeto). Publicar via Sheets, em vez de apontar o Power BI direto para os CSVs locais, permite que o dashboard seja atualizado sem reabrir o Power BI Desktop e serve de camada de dados compartilhável independente do repositório Git.

**Pendente de preenchimento após a execução da Tarefa 13** (publicar a planilha `diabetes_sus_gold` no Google Sheets — ver checklist em `00-execucao-manual.md`):

| Aba | URL publicada (CSV) |
|---|---|
| `municipio_ano` | _a preencher_ |
| `icvd_municipio` | _a preencher_ |
| `icvd_regiao` | _a preencher_ |
| `genero_regiao` | _a preencher_ |

O CSV local em `data/gold/` permanece como fonte redundante: se a publicação no Sheets ficar indisponível durante uma apresentação, o dashboard continua funcional a partir dele.
