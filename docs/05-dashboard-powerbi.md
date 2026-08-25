# Dashboard Power BI — guia de construção

Power BI Desktop é uma ferramenta gráfica: não há como gerar o `.pbix` por código. Este documento é o roteiro para construí-lo manualmente — as medidas DAX prontas para copiar, a estrutura das três páginas e os visuais de cada uma. É a Tarefa 14 do plano de implementação, e o passo 9 do checklist em `00-execucao-manual.md`.

## Pré-requisito

As quatro abas publicadas no Google Sheets (`municipio_ano`, `icvd_municipio`, `icvd_regiao`, `genero_regiao` — Tarefa 13, ver `02-coleta-de-dados.md`, Seção 2.5). Os CSVs locais em `data/gold/` servem de fonte redundante, para o caso de o Sheets ficar indisponível durante uma apresentação.

## Dois desvios em relação ao desenho original do projeto

**O mapa é por UF, não por município.** O visual Shape Map do Power BI exige um arquivo TopoJSON e não sustenta 5.570 polígonos municipais de forma confiável — em volumes desse tamanho o visual trava ou renderiza mal. A granularidade municipal não desaparece do dashboard: ela aparece na dispersão da Página 2 e nas tabelas de ranking (top-20), que é onde ela realmente informa uma decisão. O mapa coroplético usa `Taxa Bruta 100k` agregada por UF.

**Não haverá link público do dashboard.** O Power BI Service não aceita cadastro com conta de e-mail pessoal (`@gmail.com`) — só contas corporativas ou acadêmicas (Microsoft 365 Business/Education). A entrega é o arquivo `.pbix` versionado no repositório, um PDF exportado (`dashboard/dashboard.pdf`) e capturas de tela de cada página (`dashboard/previews/*.png`). Essa combinação expõe o modelo de dados e as medidas DAX de forma mais verificável, para fins de avaliação, do que um link.

## Passo 1 — Conectar as fontes

Página inicial do Power BI Desktop → **Obter Dados → Web**, colando cada uma das quatro URLs publicadas (registradas em `02-coleta-de-dados.md`, Seção 2.5). Renomear cada consulta, no Editor poder Query, para: `municipio_ano`, `icvd_municipio`, `icvd_regiao`, `genero_regiao`.

Conferir os tipos de coluna após a carga — em particular `cod_municipio` precisa ficar como texto (não número), para não perder o zero à esquerda do código IBGE de 7 dígitos.

## Passo 2 — Criar as medidas DAX

Criar como medidas novas (não colunas calculadas) na tabela `municipio_ano`, exceto onde indicado:

```dax
Internações = SUM(municipio_ano[internacoes])
Amputações  = SUM(municipio_ano[amputacoes])
Óbitos      = SUM(municipio_ano[obitos])
Gasto SUS   = SUM(municipio_ano[val_total])

% Amputação      = DIVIDE([Amputações], [Internações])
Letalidade       = DIVIDE([Óbitos], [Internações])
Taxa Bruta 100k  = DIVIDE([Internações], SUM(municipio_ano[populacao])) * 100000
```

As três medidas seguintes referenciam colunas de `icvd_municipio` — criá-las nessa tabela:

```dax
ICVD Atual   = AVERAGE(icvd_municipio[icvd_2023_24])
ICVD Base    = AVERAGE(icvd_municipio[icvd_2019])
Recuperação  = [ICVD Atual] - [ICVD Base]

Municípios no Ranking = DISTINCTCOUNT(icvd_municipio[cod_municipio])
```

Usar `DIVIDE` em vez do operador `/` em todas as razões: `DIVIDE` devolve `BLANK()` em vez de erro quando o denominador é zero (município sem internação no filtro ativo), o que evita que um cartão ou visual quebre a página inteira por causa de uma combinação de filtros vazia.

## Passo 3 — Página 1: Panorama Brasil

- Quatro cartões (visual **Cartão**) no topo, um por medida: `Internações`, `Amputações`, `Óbitos`, `Gasto SUS`.
- Gráfico de linhas de `Internações` por `ano` (eixo X = `municipio_ano[ano]`, valor = `[Internações]`), com uma linha de referência (zona sombreada ou linha constante) marcando o intervalo 2020–2021 — Formatar visual → Linhas de referência, ou uma segunda série sombreada, para tornar visível o bloco de distorção pandêmica descrito em `01-problema.md`.
- Mapa preenchido (visual **Mapa**, não Shape Map — ver desvio acima), campo de localização `municipio_ano[uf]`, tamanho/cor por `[Taxa Bruta 100k]`.
- Segmentações de dados (**Slicer**): Região (`municipio_ano[regiao]`), UF (`municipio_ano[uf]`), Ano (`municipio_ano[ano]`), Sexo (`municipio_ano[sexo]`) e Faixa Etária (`municipio_ano[faixa_etaria]`).

## Passo 4 — Página 2: Desigualdade e recuperação

Núcleo do projeto — é aqui que o eixo "choque e recuperação desigual" fica visível.

- **Dispersão** (visual **Gráfico de Dispersão**): eixo X = `icvd_municipio[icvd_2019]`, eixo Y = `icvd_municipio[icvd_2023_24]`, um ponto por `cod_municipio`, cor por `regiao`. Adicionar uma linha de referência na diagonal (X = Y) via Formatar visual → Linhas de referência → Linha Y=X, ou uma coluna calculada auxiliar — pontos acima da diagonal representam municípios que pioraram (ICVD atual maior que o de 2019); abaixo, municípios que recuperaram.
- **Barras agrupadas** de `icvd_regional` por `regiao`, comparando os dois períodos — usar `icvd_regiao[periodo]` como legenda e `icvd_regiao[icvd_regional]` como valor.
- **Dispersão** de `municipio_ano[cobertura_aps]` (eixo X) contra `[Taxa Bruta 100k]` ou a taxa padronizada equivalente vinda de `icvd_municipio[taxa_internacao_padronizada_2023_24]` (eixo Y), um ponto por município.
- Duas **tabelas**: top-20 de maior `icvd_municipio[icvd_2023_24]` (piores municípios no período atual) e top-20 de `icvd_municipio[recuperacao]` mais negativa (municípios que mais melhoraram). Ordenar cada tabela pela coluna relevante, limitar a 20 linhas via filtro de visual (Top N).

## Passo 5 — Página 3: Recorte de gênero

- Barras agrupadas de taxa padronizada por `genero_regiao[regiao]` e `genero_regiao[sexo]`.
- Barras de `genero_regiao[pct_amputacao]` por região e sexo.
- Barras de `genero_regiao[letalidade]` por região e sexo.
- Uma caixa de texto (visual **Texto**) com a conclusão do teste da hipótese de gênero (`03-modelagem.md`, Seção 3.8) e os números que a sustentam — preenchida só depois que `04-conclusoes.md`, Seção 4, estiver escrita com o resultado real.

## Passo 6 — Exportar as evidências

Arquivo → Exportar → **Exportar para PDF**, salvando em `dashboard/dashboard.pdf`. Em seguida, capturar cada página individualmente como PNG (recorte de tela ou a própria exportação do Power BI) e salvar em `dashboard/previews/pagina1.png`, `pagina2.png`, `pagina3.png`.

## Passo 7 — Salvar e versionar

Salvar o arquivo como `dashboard/diabetes_sus.pbix` e commitar `dashboard/` inteiro (o `.pbix`, o PDF e os PNGs) — nenhum desses arquivos está no `.gitignore` do projeto.
