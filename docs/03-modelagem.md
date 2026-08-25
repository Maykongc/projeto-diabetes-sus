# Modelagem

## 3.1 Arquitetura do pipeline

A estratégia central é **filtrar cedo**: cada arquivo mensal de AIH é baixado, convertido, filtrado pelo CID-10 do diabetes e gravado em Parquet antes de o próximo arquivo ser baixado; o `.dbc` bruto é apagado logo em seguida. Como o volume bruto de AIH de todas as causas é grande (cerca de 6 GB comprimidos ao longo de 2019–2024) e o filtro remove a grande maioria das internações — a maior parte não tem diabetes como causa principal — manter tudo em disco simultaneamente seria desnecessário. Cada arquivo processado é também um checkpoint natural: a próxima execução verifica se o Parquet de destino já existe e pula o que já foi feito, o que torna a ingestão idempotente e tolerante a quedas de sessão no Colab.

O pipeline segue o padrão de camadas (medallion):

- **Bronze** (Colab): AIHs de diabetes, 2019–2024, no grão original de uma linha por internação, particionado por UF e ano.
- **Silver** (Colab, PySpark): agregação para o grão **município × ano × faixa etária × sexo**, com joins contra a população do IBGE e a cobertura de APS do e-Gestor. É neste ponto que o PySpark se justifica: agregar dezenas de milhões de internações ao longo de seis anos em pandas puro excederia a memória disponível no Colab.
- **Gold**: a tabela `municipio_ano`, na **grade completa** de 5.570 municípios × 6 anos × 2 sexos × 7 faixas etárias = 467.880 linhas e 15 colunas, poucos megabytes. A grade é completa por decisão metodológica, não por conveniência: a combinação sem nenhuma internação precisa existir com zero, senão a população dela some do denominador da padronização etária (Seção 3.3). É o único artefato que atravessa a fronteira entre Colab e máquina local.
- **Local**: padronização etária, cálculo do ICVD, correlações e EDA, em pandas e DuckDB.
- **Publicação**: CSV exportado para Google Sheets, consumido pelo Power BI.

```
DATASUS FTP -+
IBGE API ----+--> COLAB (bronze -> silver) --> gold.csv --> LOCAL (pandas/DuckDB)
e-Gestor ----+         [PySpark]                 ~35k          |
CNES --------+     checkpoint no Drive          linhas         v
                                                     Google Sheets --> Power BI
```

A implementação está em `notebooks/01_ingestao_colab.ipynb` (bronze e silver, roda no Colab), `notebooks/02_eda.ipynb` e `notebooks/03_indice_icvd.ipynb` (camada local).

## 3.2 Limpeza obrigatória

Quatro problemas de qualidade de dado são tratados antes de qualquer análise, porque cada um deles, se ignorado, produziria um número errado sem gerar um erro visível:

**Idade.** O SIH codifica idade em duas colunas, `IDADE` e `COD_IDADE`, onde `COD_IDADE` indica a unidade de medida (dias, meses ou anos, a depender do código). Sem converter tudo para anos completos antes de aplicar qualquer faixa etária, um recém-nascido com `IDADE=15` (15 dias) seria contado como uma pessoa de 15 anos. A conversão está em `src/diabetes_sus/idade.py`, testada em `tests/test_idade.py`.

**Código de município.** O SIH registra o município de residência em 6 dígitos (sem dígito verificador); o IBGE usa 7 dígitos. É preciso completar o código antes de qualquer join com população — caso contrário, o join silenciosamente não encontra correspondência e a linha vira órfã. `src/diabetes_sus/municipios.py` implementa essa compatibilização e também trata municípios criados ou extintos no período. A ingestão reporta o volume de linhas órfãs (que não encontraram correspondência de 7 dígitos) e interrompe a execução se ultrapassarem 1% do total, para não deixar um problema estrutural de mapeamento passar despercebido como ruído normal.

**Pandemia.** 2020 e 2021 são tratados como um bloco analítico explícito — nunca interpolados como se fossem dado ausente, nem lidos como parte de uma tendência natural do restante da série. É esse bloco que sustenta o eixo "choque e recuperação" descrito em `01-problema.md`.

**Duplicatas.** AIHs de continuação (`IDENT = 5`, usadas quando uma internação longa precisa ser refaturada em partes) não são novas internações e são excluídas antes da contagem, dentro de `filtrar_internacoes_diabetes` (`src/diabetes_sus/filtros.py`, testado em `tests/test_filtros.py`).

## 3.3 Padronização etária

Comparar a taxa bruta de internação entre um município jovem e um envelhecido é enganoso: mesmo com cuidado idêntico, o município mais velho internará mais por diabetes só pela composição etária da sua população. A padronização direta resolve isso ao responder: "qual seria a taxa deste município se ele tivesse a composição etária do Brasil?"

Usa-se o método direto, com a população do **Censo 2022** como padrão nacional:

```
taxa_padronizada(m) = SOMA_i [ casos(m,i) / pop(m,i) ] * w(i)
onde  w(i) = pop_padrao(i) / pop_padrao_total
```

`i` percorre as faixas etárias `<30, 30–39, 40–49, 50–59, 60–69, 70–79, 80+`; `casos(m,i)` e `pop(m,i)` são internações e população do município `m` na faixa `i`; `w(i)` é o peso dessa faixa na população nacional total. Implementado em `src/diabetes_sus/padronizacao.py` (`padronizar_por_municipio`, generalizada depois para `padronizar_por_grupo`, que aceita qualquer coluna ou combinação de colunas de agrupamento — usada tanto para município quanto para região e para o recorte por sexo), testado em `tests/test_padronizacao.py`.

**Faixa etária sem internação entra com taxa zero e peso preservado.** A soma acima percorre **sempre as sete faixas**, inclusive as que não registraram nenhuma internação no município: elas contribuem `casos(m,i) = 0`, portanto taxa específica zero, e **mantêm seu peso `w(i)`**. Os pesos somam 1 sobre as sete faixas, sempre.

Isso precisa ser dito explicitamente porque a alternativa é um erro fácil de cometer e difícil de enxergar. A camada bronze só contém internações por diabetes, então uma agregação ingênua produz linha apenas para as combinações `(município, ano, sexo, faixa)` que tiveram ao menos um caso — a faixa sem internação simplesmente não aparece. Se, diante da faixa ausente, os pesos forem renormalizados sobre as faixas presentes (`w(i) = pop_padrao(i) / soma das faixas presentes`), o peso da faixa vazia é **redistribuído** entre as demais em vez de contribuir com zero, e a taxa padronizada infla.

O efeito não é marginal: a faixa `<30` sozinha vale cerca de **42% da população padrão** brasileira e é justamente a que menos interna por diabetes, ou seja, a que mais frequentemente falta. Pior, o viés é **correlacionado com o porte do município** — quanto menor o município, mais faixas vazias, mais inflação —, exatamente o viés de composição que a padronização existe para eliminar.

Duas defesas independentes, ambas implementadas:

1. **Na origem.** A camada gold é construída a partir da **grade completa** — o produto de todas as combinações município × ano × sexo × faixa da tabela de população, 5.570 × 6 × 2 × 7 = **467.880 linhas** — com `left join` da silver e contagens preenchidas com zero onde não houve internação (`notebooks/01_ingestao_colab.ipynb`, Seção 2.3). Zero internações passa a ser um fato registrado, não uma linha ausente.
2. **Na defesa.** `padronizar_por_grupo` reindexa cada grupo contra as sete faixas do padrão antes de calcular: a faixa que não aparece entra com taxa zero e peso preservado, nunca é descartada. Só levanta erro se o grupo não tiver população em faixa nenhuma (aí não existe denominador possível) ou se uma faixa tiver casos sem população (órfão de join, taxa infinita). O comportamento está fixado em `tests/test_padronizacao.py`, incluindo um teste que compara o resultado com a faixa ausente contra o resultado com a mesma faixa presente e zero casos — os dois descrevem a mesma realidade e têm de dar o mesmo número.

## 3.4 O índice ICVD

O Índice Composto de Vulnerabilidade no Cuidado ao Diabetes (ICVD) combina quatro componentes, todos orientados na mesma direção — quanto maior, pior o cuidado:

| Componente | Direção | O que captura |
|---|---|---|
| Taxa de internação por diabetes, padronizada por idade | Maior = pior | Falha da atenção primária em evitar a descompensação |
| Proporção de internações com amputação de membro inferior | Maior = pior | Paciente chegou tarde ao sistema |
| Letalidade hospitalar | Maior = pior | Gravidade na chegada e capacidade de resposta do hospital |
| Cobertura de Atenção Primária (**invertida**) | Menor cobertura = pior | Causa estrutural, não desfecho |

**Excluídos deliberadamente do índice:** gasto médio por internação e leitos por habitante. Ambos são ambíguos como indicador de qualidade — gasto alto pode significar caso mais grave ou pode significar cuidado melhor; poucos leitos reduzem a taxa de internação sem necessariamente melhorar o desfecho do paciente. Os dois permanecem como variáveis de contexto na discussão dos resultados, fora da soma do índice.

**Pesos: iguais, 25% cada.** Não há base empírica disponível neste projeto para justificar hierarquizar um componente sobre os outros, e pesos iguais é a posição honesta na ausência dessa evidência — o mesmo princípio usado pelo IDH ao combinar renda, educação e longevidade. Há também um argumento técnico a favor: amputação é o evento mais raro dos quatro componentes e, por isso, o mais sujeito a ruído estatístico em municípios pequenos; dar a ele um peso maior aumentaria a variância do índice sem aumentar a informação que ele carrega. A Seção 3.7 avalia se essa escolha de pesos é robusta.

Implementado em `src/diabetes_sus/indice.py` (`calcular_icvd`), testado em `tests/test_indice.py`.

## 3.5 O problema dos números pequenos

Um município de 900 habitantes com uma internação e um óbito no período registra 100% de letalidade e lideraria o ranking de piores do país — não porque o cuidado ali seja de fato o pior, mas porque um único caso decide o indicador inteiro. Ignorar esse efeito produziria um ranking dominado por ruído estatístico, não por desigualdade real.

Duas defesas são aplicadas:

1. **Corte de eventos mínimos: 20 internações no período.** Abaixo desse volume, o município fica de fora do **ranking municipal**, aparecendo no mapa do dashboard em cinza com o rótulo "dados insuficientes" — nunca excluído em silêncio, sempre com o motivo visível.
2. **Winsorização em p1/p99** de cada componente, antes da normalização, para conter o efeito de valores extremos isolados que sobrevivem ao corte.

A escolha do valor 20 não é arbitrária; ela foi avaliada contra o impacto que produz na cobertura populacional do ranking, usando os dados reais do Censo 2022 e assumindo uma taxa nacional de referência de aproximadamente 70 internações por 100 mil habitantes/ano (premissa a validar contra os dados observados assim que a camada gold existir):

| Corte | Pop. mínima aprox. | Municípios fora | % da população mantida |
|---|---|---|---|
| 10 | ~2.400 hab. | 256 (4,6%) | 99,8% |
| **20** | **~4.800 hab.** | **1.230 (22,1%)** | **98,0%** |
| 30 | ~7.100 hab. | 1.958 (35,2%) | 95,9% |
| 50 | ~11.900 hab. | 2.922 (52,5%) | 91,4% |

O corte de 20 remove 22,1% dos municípios do ranking, mas apenas 2,0% da população — porque os municípios abaixo do corte são, por definição, os menores do país. É um compromisso deliberado: cortes menores (10) deixam mais ruído estatístico no ranking; cortes maiores (30, 50) descartam uma fração crescente e desnecessária dos municípios sem ganho proporcional de estabilidade.

**Por que esse corte não pode ser aplicado ao estudo inteiro.** Municípios pequenos não se distribuem uniformemente pelo país — eles se concentram no Sul e no Centro-Oeste, não no Norte e no Nordeste:

| Região | % de municípios abaixo de ~4.800 hab. |
|---|---|
| Sul | 35,3% |
| Centro-Oeste | 29,3% |
| Sudeste | 22,7% |
| Norte | 19,1% |
| Nordeste | 12,5% |

Se o corte de 20 internações fosse aplicado ao estudo inteiro, ele removeria proporcionalmente quase três vezes mais municípios do Sul (35,3%) do que do Nordeste (12,5%). Isso significaria comparar regiões sob critérios de inclusão diferentes: o Sul entraria na comparação regional representado só pelos seus municípios maiores — sistematicamente diferentes dos pequenos excluídos —, enquanto o Nordeste manteria uma amostra bem mais completa da própria variabilidade. Isso é uma falha metodológica grave num trabalho cujo objeto central é justamente a comparação entre regiões: o corte, criado para remover ruído do ranking, reintroduziria viés de composição pela porta lateral da agregação regional.

**Portanto: o corte de 20 vale exclusivamente para o ranking municipal do ICVD. Todas as análises regionais e por UF usam os 5.570 municípios, sem corte.** Na agregação regional o problema de números pequenos desaparece por construção — o denominador de cada região soma dezenas ou centenas de municípios, o que dilui o ruído de qualquer caso isolado. Essa é a distinção mais importante do desenho metodológico do projeto, e está implementada como duas rotinas separadas em `src/diabetes_sus/indice.py`: `aplicar_corte`, usada só para o ranking municipal, e a agregação regional em `notebooks/03_indice_icvd.ipynb` (Seção 4), que soma numeradores e denominadores dos 5.570 municípios sem filtrar por volume de internações — o mesmo padrão das consultas 2, 3 e 4 de `sql/consultas_duckdb.sql`.

## 3.6 Normalização e comparabilidade entre os dois momentos

Cada um dos quatro componentes é normalizado para o intervalo 0–1 por min-max após a winsorização; o ICVD é a média aritmética dos quatro componentes normalizados. Zero representa o melhor cuidado observado na amostra; um representa o pior.

O índice é calculado em **dois momentos**: **2019**, como linha de base pré-pandemia, e **2023–2024**, como situação mais recente disponível.

**Requisito não negociável de desenho:** os mínimos e máximos usados na normalização min-max precisam ser calculados sobre os **dois períodos combinados**, numa única régua — não um min-max por período. Normalizar cada período isoladamente forçaria, por construção, que todo período tivesse seu próprio pior e melhor município, ainda que a distância real entre os dois momentos tivesse mudado. Nesse cenário errado, a diferença entre os dois ICVDs deixaria de significar "o cuidado piorou ou melhorou de fato" e passaria a significar apenas "a posição relativa mudou dentro da amostra daquele ano" — uma comparação sem conteúdo substantivo.

Com a régua comum, a recuperação é definida como:

```
recuperacao = ICVD(2023-24) - ICVD(2019)
```

Valores positivos indicam piora (o município ficou mais vulnerável); negativos indicam recuperação. Este delta é o indicador central do eixo "choque e recuperação desigual" descrito em `01-problema.md`.

A mesma régua comum é reaplicada ao nível regional: o ICVD de cada uma das cinco regiões não é normalizado entre si (o que, com apenas cinco pontos, forçaria a pior região a valer exatamente 1,0 e a melhor exatamente 0,0 por construção, não porque a distância real entre elas seja grande). Em vez disso, os parâmetros de escala calculados sobre os municípios elegíveis para o ranking (`parametros_escala`) são reaplicados aos valores regionais (`aplicar_escala`), de modo que um `icvd_regional` de 0,8 signifique a mesma coisa que um `icvd` municipal de 0,8: pior que 80% da régua observada nos municípios, não "pior que quatro das outras regiões". Implementado em `src/diabetes_sus/indice.py` (`normalizar_minmax`, `winsorizar`, `parametros_escala`, `aplicar_escala`, `calcular_icvd`, `calcular_recuperacao`), testado em `tests/test_indice.py`.

## 3.7 Análise de sensibilidade

Uma escolha de pesos iguais é defensável, mas não é a única defensável. Para verificar se o ranking do ICVD depende demais dessa escolha específica, o índice do período atual (2023–24) é recalculado sob três esquemas alternativos de pesos — mais peso em desfecho (amputação e letalidade), mais peso em estrutura (cobertura de APS), mais peso em acesso (taxa de internação) — e comparado ao esquema de pesos iguais por dois critérios: correlação de Spearman entre os valores do índice (o índice muda de posição relativa entre municípios?) e sobreposição percentual do top-100 de piores municípios (os piores continuam sendo, majoritariamente, os mesmos, mesmo que o valor numérico mude?).

O critério de aceitação, definido antes de rodar a análise (`notebooks/03_indice_icvd.ipynb`, Seção 3): sobreposição do top-100 acima de 80% e correlação de Spearman acima de 0,9 tornam o ranking defensável — a escolha de pesos vira nota de rodapé, não um ponto vulnerável da metodologia. Abaixo desse critério, o índice exigiria revisão antes de qualquer entrega.

**Este resultado ainda não existe.** A análise depende da camada gold, que só é gerada após a execução manual da ingestão no Colab (ver `00-execucao-manual.md`). O notebook está implementado e pronto para rodar; os números de Spearman e de sobreposição do top-100, e a conclusão sobre se o critério foi atingido, serão preenchidos em `04-conclusoes.md` assim que a execução acontecer — não são reportados aqui para não antecipar um resultado que ainda não foi calculado.

## 3.8 Trilha de gênero — hipótese a testar

Fora do índice ICVD, deliberadamente: o recorte de gênero é tratado como uma hipótese a testar, não como um componente que agregaria homens e mulheres num único número. Compara-se homens e mulheres em taxa padronizada de internação, proporção de amputação, letalidade e idade média na internação, nacionalmente e por região.

**Hipótese:** homens apresentam desfechos mais graves (maior proporção de amputação, maior letalidade) apesar de prevalência da doença semelhante entre os sexos, o que apontaria para uma diferença na procura por cuidado preventivo, não na incidência da doença em si.

**Teste:** comparação das taxas padronizadas por sexo, em cada uma das cinco regiões. A hipótese é considerada sustentada se a diferença em proporção de amputação e em letalidade for consistente (na mesma direção) entre as cinco regiões, enquanto a diferença de prevalência autorreferida (VIGITEL, usado só como fonte de validação externa) não acompanhar essa mesma consistência. Implementado em `notebooks/03_indice_icvd.ipynb`, Seção 5, com exportação para `data/gold/genero_regiao.csv`. O resultado do teste — confirmado ou refutado — depende da mesma execução pendente da Seção 3.7 e será reportado em `04-conclusoes.md` com os números observados.

## 3.9 Validação

Sem estas checagens, um erro no filtro ou na ingestão se converteria em "achado" sem que ninguém percebesse a diferença. Quatro camadas de verificação, implementadas em `src/diabetes_sus/validacao.py` (testado em `tests/test_validacao.py`):

1. **Completude.** Dos 1.944 arquivos mensais esperados (27 UFs × 12 meses × 6 anos), quantos foram de fato baixados e processados. Tolerância de até 2% de arquivos faltando; acima disso, a execução do notebook de ingestão é interrompida por `assert` antes de seguir para a camada silver, e as pendências ficam listadas com o motivo em `logs/pendentes.json` (no Drive).
2. **Conferência externa contra o TabNet.** O total de internações por UF e ano, sob o mesmo filtro de diabetes, é comparado ao total oficial do TabNet do DATASUS (`comparar_com_tabnet`). É a validação mais valiosa do projeto, porque é a única que confronta o pipeline inteiro — download, filtro, agregação — contra uma fonte externa independente. Usa junção externa (`how="outer"`) deliberadamente: uma combinação UF/ano presente só de um dos lados é exatamente o sintoma que a reconciliação existe para capturar (mês faltante na ingestão, ou UF/ano que o TabNet não cobre), e uma junção interna faria essa linha desaparecer silenciosamente do resultado. Tolerância de 2% de erro relativo por UF/ano; acima disso, a linha reprova (`aprovado=False`).
3. **Integridade dos denominadores.** Todo município com internação registrada precisa ter população correspondente na tabela do IBGE; municípios órfãos (`verificar_denominadores`) são reportados explicitamente, nunca descartados silenciosamente.
4. **Sanidade das métricas.** Taxa negativa, taxa implausível, ou ICVD fora do intervalo [0,1] interrompem a execução (`verificar_sanidade`) em vez de seguir adiante com um número que não faz sentido.

A etapa de reconciliação contra o TabNet é manual (extrair o total de referência e rodar `comparar_com_tabnet`) e está descrita passo a passo em `00-execucao-manual.md`, com o aviso de que uma divergência acima de 2% bloqueia a entrega — não é uma checagem opcional.
