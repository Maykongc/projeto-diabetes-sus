# Importação no Power BI

Os seis arquivos desta pasta foram gerados por `scripts/exportar_powerbi.py` já no padrão brasileiro: **separador `;`, decimal `,`, codificação UTF-8 com BOM**. Importe sem mudar nada nas opções.

## Por que estes arquivos e não os de `data/gold/`

Os CSVs de `data/gold/` são a base analítica dos notebooks e usam ponto decimal, à moda do Python. Num Windows configurado em português, o Power BI leria `92.01` como **9.201** — silenciosamente, sem erro, e todo indicador decimal do dashboard ficaria errado. Os arquivos daqui já vêm com vírgula decimal e resolvem isso na origem.

Outras diferenças: contagens voltaram a ser inteiras (vinham como `0.0`), os decimais foram arredondados para o que faz sentido ler (o ICVD tinha 16 casas), e o ranking ganhou o **nome** de cada município — `3544202` não comunica nada num visual.

## Os arquivos

| Arquivo | Linhas | Papel no modelo |
|---|---|---|
| `fato_municipio_ano.csv` | 467.880 | **Fato.** Uma linha por município × ano × sexo × faixa etária |
| `dim_municipio.csv` | 5.570 | **Dimensão.** Código, nome, UF, região, população e a marca `no_ranking` |
| `dim_tempo.csv` | 6 | **Dimensão.** Ano, bloco temporal e o período do ICVD |
| `ranking_municipal.csv` | 3.365 | Tabela do ranking: ICVD nos dois períodos, recuperação e componentes |
| `resumo_regiao.csv` | 10 | Cinco regiões × dois períodos, com o ICVD regional |
| `genero_regiao.csv` | 10 | Cinco regiões × dois sexos |

## Como importar

**Obter dados → Texto/CSV**, um arquivo por vez. Na janela de visualização, confira que os números aparecem alinhados à direita (se vierem à esquerda, o Power BI os tratou como texto). Clique em **Carregar**.

Uma checagem que vale trinta segundos: depois de carregar, olhe `resumo_regiao` e confirme que `taxa_internacao_padronizada` do Centro-Oeste em 2019 está em **62,69** e não em 6.269. Se estiver errado, a localidade da importação não é pt-BR — refaça com **Transformar dados → Usar Localidade → Português (Brasil)**.

## Relacionamentos a criar

Em **Modelagem → Gerenciar relações**, crie três:

| De (lado 1) | Para (lado muitos) | Cardinalidade | Direção |
|---|---|---|---|
| `dim_municipio[cod_municipio]` | `fato_municipio_ano[cod_municipio]` | Um para muitos | Simples |
| `dim_tempo[ano]` | `fato_municipio_ano[ano]` | Um para muitos | Simples |
| `dim_municipio[cod_municipio]` | `ranking_municipal[cod_municipio]` | Um para muitos | Simples |

`resumo_regiao` e `genero_regiao` ficam **sem relacionamento**. São tabelas de resumo já calculadas, usadas em visuais próprios. Ligá-las por `regiao` criaria relação muitos-para-muitos e produziria totais errados.

Em `dim_tempo`, ordene a coluna `bloco` pela coluna `ordem_bloco` (selecione `bloco` → **Classificar por coluna** → `ordem_bloco`), senão os blocos aparecem em ordem alfabética nos gráficos.

## Medidas DAX

Crie numa tabela de medidas ou dentro de `fato_municipio_ano`.

### Base

```dax
Internações = SUM(fato_municipio_ano[internacoes])
Amputações = SUM(fato_municipio_ano[amputacoes])
Óbitos = SUM(fato_municipio_ano[obitos])
Gasto SUS = SUM(fato_municipio_ano[val_total])
Dias de internação = SUM(fato_municipio_ano[dias_perm_total])
```

### População e taxas

A população é a mesma em todos os anos (Censo 2022 aplicado à grade). Somá-la com seis anos no contexto multiplicaria por seis, então a medida divide pelo número de anos filtrados:

```dax
Anos no contexto = DISTINCTCOUNT(fato_municipio_ano[ano])

População = DIVIDE(SUM(fato_municipio_ano[populacao]), [Anos no contexto])

Internações por ano = DIVIDE([Internações], [Anos no contexto])

Taxa anual por 100 mil = DIVIDE([Internações por ano], [População]) * 100000
```

Use **Taxa anual por 100 mil** em qualquer visual que compare períodos de tamanhos diferentes — 2019 é um ano e 2023–24 são dois. Comparar contagens brutas entre eles daria o dobro por construção.

### Indicadores de gravidade

```dax
% Amputação = DIVIDE([Amputações], [Internações])
Letalidade = DIVIDE([Óbitos], [Internações])
Custo por internação = DIVIDE([Gasto SUS], [Internações])
Idade média = DIVIDE(SUM(fato_municipio_ano[idade_soma]), SUM(fato_municipio_ano[idade_validas]))
```

Formate `% Amputação` e `Letalidade` como percentual com duas casas.

### Cobertura de APS

```dax
Cobertura APS média = AVERAGE(fato_municipio_ano[cobertura_aps])
```

**Use `AVERAGE`, nunca `SUM`.** A cobertura é um percentual do município no ano, repetido nas 28 linhas de sexo × faixa etária; somá-la não tem significado.

E **nunca compare cobertura entre 2019–2020 e 2021–2024**: são séries com metodologias diferentes, e a média salta 42 pontos na virada por troca de régua, não por mudança real. A justificativa completa está na Seção 3.4 de `docs/03-modelagem.md`.

### Índice ICVD

```dax
ICVD atual = AVERAGE(ranking_municipal[icvd_2023_24])
ICVD base = AVERAGE(ranking_municipal[icvd_2019])
Recuperação = AVERAGE(ranking_municipal[recuperacao])
Municípios no ranking = DISTINCTCOUNT(ranking_municipal[cod_municipio])
```

`Recuperação` positiva significa **piora** (o índice subiu). Deixe isso explícito no título do visual, senão a leitura se inverte.

## Cuidados

**O mapa deve ser por UF, não por município.** O visual Shape Map não sustenta 5.570 polígonos de forma confiável. Use o mapa preenchido com `dim_municipio[uf]` e leve a granularidade municipal para a dispersão e as tabelas de ranking.

**`ranking_municipal` tem 3.365 municípios, não 5.570.** Os outros 2.205 não passaram nos critérios de elegibilidade (menos de 20 internações no total, ou menos de 5 em algum dos dois períodos). Em visuais que usam `dim_municipio`, filtre por `no_ranking = Verdadeiro` quando estiver mostrando ICVD — do contrário aparecem municípios com o índice em branco.

**Percentuais no ranking já vêm multiplicados por 100.** Em `ranking_municipal`, `prop_amputacao_*` e `letalidade_*` estão em pontos percentuais (8,53 significa 8,53%). Formate como número, não como percentual, ou o Power BI mostrará 853%.

## Estrutura das páginas

O desenho das três páginas, com os visuais de cada uma, está em [`docs/05-dashboard-powerbi.md`](../../docs/05-dashboard-powerbi.md). Os achados que elas precisam contar estão em [`docs/04-conclusoes.md`](../../docs/04-conclusoes.md).
