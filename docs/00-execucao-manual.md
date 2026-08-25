# Execução manual — checklist

Este documento existe porque uma parte relevante do pipeline não pode ser automatizada: exige subir arquivos numa interface web, baixar um relatório de um portal sem API, ou operar um programa gráfico (Power BI). Nenhum agente de código consegue fazer essas etapas — precisam ser feitas à mão, nesta ordem. Cada item explica o que fazer e por que não dá para automatizar.

Marque cada item ao concluir. Os itens 1 a 7 são pré-requisito direto de `docs/04-conclusoes.md` e da seção "Principais achados" do `README.md` — sem eles, os dois documentos permanecem com os placeholders pendentes que foram deixados propositalmente.

## 1. Subir `src/diabetes_sus/` para o Google Drive

**Por quê:** o notebook `notebooks/01_ingestao_colab.ipynb` roda no Google Colab, que não tem acesso ao seu clone local do repositório. Ele importa `filtrar_internacoes_diabetes`, `idade_em_anos`, `faixa_etaria`, `completar_codigo` e outras funções já testadas localmente (`tests/`) — reimplementá-las direto no notebook criaria duas versões do mesmo código que poderiam divergir.

**Como:** no Google Drive, dentro de `MyDrive/diabetes_sus/`, crie a pasta `src/` e envie a pasta `diabetes_sus/` inteira (com `__init__.py`, `config.py`, `idade.py`, `municipios.py`, `filtros.py`, `padronizacao.py`, `indice.py`, `validacao.py`), preservando a estrutura, de forma que o caminho final seja `MyDrive/diabetes_sus/src/diabetes_sus/__init__.py` e assim por diante. O `__init__.py` é obrigatório — sem ele o Python não reconhece a pasta como pacote e o `import diabetes_sus...` falha na célula 1.2 do notebook.

- [ ] Feito

## 2. Baixar a cobertura de APS do e-Gestor Atenção Básica

**Por quê:** não existe um endpoint de API pública para esse dado — é um relatório exportável manualmente pela interface web do e-Gestor. Automatizar exigiria simular login e navegação numa sessão autenticada, fora do escopo de um pipeline de dados.

**Como:** acessar `https://egestorab.saude.gov.br/paginas/acessoPublico/relatorios/relHistoricoCoberturaAB.xhtml` (URL confirmada por HTTP 200), extrair a cobertura mensal (ou anual, conforme o relatório disponível) de Atenção Básica/Estratégia Saúde da Família por município, para os anos 2019 a 2024, e formatar como um único CSV chamado `cobertura_aps.csv` com exatamente as colunas:

```
cod_municipio,ano,cobertura_aps
```

`cod_municipio` no código IBGE de 7 dígitos (como string, para não perder zero à esquerda), `ano` como inteiro, `cobertura_aps` como percentual médio anual (0–100).

- [ ] Feito

## 3. Subir os insumos para `{BASE}/insumos/` no Drive

**Por quê:** a célula 2.2 do notebook (`notebooks/01_ingestao_colab.ipynb`) faz o join da camada silver com população e cobertura de APS, e ambos os arquivos precisam existir no Drive antes dela rodar — a célula seguinte (2.2, verificação) interrompe a execução com `FileNotFoundError` se algum estiver faltando.

**Como:** copiar dois arquivos para `MyDrive/diabetes_sus/insumos/` no Drive:

1. `data/gold/populacao_municipio_faixa_sexo.parquet` — já existe no repositório local (gerado pela Tarefa 5 a partir do Censo 2022). Só copiar.
2. `cobertura_aps.csv` — o arquivo produzido no item 2 acima.

- [ ] Feito

## 4. Rodar a ingestão no Colab

**Por quê:** é a etapa que só funciona no Colab — `datasus-dbc` não instala no Windows local com Python 3.13 (`02-coleta-de-dados.md`, Seção 2.4). É a etapa mais demorada de todo o projeto: 1.944 arquivos mensais, um download de FTP por vez.

**Como:** abrir `notebooks/01_ingestao_colab.ipynb` no Google Colab e executar todas as células, de cima para baixo. Pode levar horas, dependendo da velocidade do FTP do DATASUS.

**Importante — a ingestão é idempotente.** Se a sessão do Colab cair no meio (acontece, é comum em sessões longas), não é preciso recomeçar do zero: basta reconectar e rodar as células de novo. Cada arquivo já baixado é pulado automaticamente (a célula verifica se o parquet de destino já existe antes de baixar). Falhas persistentes de download (3 tentativas sem sucesso) são registradas em `logs/pendentes.json` no Drive, sem derrubar o restante da execução.

- [ ] Feito — completude ≥ 98% confirmada pela célula 1.5 (senão, investigar `logs/pendentes.json` antes de seguir)

## 5. Baixar `municipio_ano.csv` para `data/gold/`

**Por quê:** é o único artefato que atravessa a fronteira entre o Colab e a máquina local — todo o resto do pipeline (padronização, ICVD, EDA) roda localmente a partir dele.

**Como:** copiar `{BASE}/gold/municipio_ano.csv` do Google Drive para `data/gold/municipio_ano.csv` no repositório local. Conferir com:

```bash
python -c "import pandas as pd; d=pd.read_csv('data/gold/municipio_ano.csv', dtype={'cod_municipio':str}); print(d.shape); print(d['ano'].value_counts().sort_index()); print(d.isna().sum())"
```

Esperado: os seis anos de 2019 a 2024 presentes, sem nulos em `internacoes`, `populacao` e `cod_municipio` (nulos em `cobertura_aps` são aceitáveis se o e-Gestor não cobrir algum município/ano).

- [ ] Feito

## 6. Reconciliar contra o TabNet — bloqueia a entrega se divergir

**Por quê:** é a única validação que confronta o pipeline inteiro (download, filtro, agregação) contra uma fonte externa independente. Sem ela, um erro no filtro do CID-10 ou na agregação poderia virar um "achado" sem que ninguém percebesse.

**Como:**

1. Acessar o TabNet do DATASUS em `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nruf.def` — **Morbidade Hospitalar do SUS por local de residência** (verificado: HTTP 200) —, gerar internações por UF e ano com o mesmo filtro (CID-10 E10–E14).

   **É `nruf.def`, não `niuf.def`.** O cubo `niuf.def` é por local de *internação*; a camada gold agrega por `MUNIC_RES`, ou seja, por local de *residência*. Comparar residência contra internação produz divergência sistemática em toda UF com fluxo de pacientes (quem mora no interior e interna na capital de outro estado), e como divergência acima de 2% bloqueia a entrega, a reconciliação reprovaria por um falso positivo — depois de toda a ingestão já ter sido feita.
2. Salvar como `data/raw/tabnet_referencia.csv`, com as colunas `uf`, `ano`, `internacoes`.
3. Rodar a reconciliação:

```python
import pandas as pd
from diabetes_sus.validacao import comparar_com_tabnet

nosso = pd.read_csv('data/gold/municipio_ano.csv', dtype={'cod_municipio': str})
nosso = nosso.groupby(['uf', 'ano'], as_index=False)['internacoes'].sum()
tabnet = pd.read_csv('data/raw/tabnet_referencia.csv')

resultado = comparar_com_tabnet(nosso, tabnet)
print(resultado[~resultado['aprovado']])
```

**Critério de bloqueio: divergência acima de 2% em qualquer UF/ano reprova a linha (`aprovado=False`) e bloqueia a entrega.** Investigar a causa (mês faltante na ingestão, UF/ano fora da cobertura do TabNet, erro de filtro) antes de seguir para os notebooks de análise — não descartar a linha reprovada e seguir em frente.

- [ ] Feito — todas as linhas aprovadas (ou divergências investigadas e explicadas)

## 7. Rodar os notebooks 02 e 03 localmente

**Por quê:** é aqui que a padronização etária, o ICVD, a análise de sensibilidade e a trilha de gênero são efetivamente calculados — tudo depende de `data/gold/municipio_ano.csv` existir com dados reais.

**Como:** com o ambiente local configurado (`pip install -r requirements.txt`), abrir e executar de ponta a ponta:

1. `notebooks/02_eda.ipynb` — panorama nacional, distribuição da taxa bruta, taxa por região, blocos pré/durante/pós-pandemia, cobertura de APS × taxa de internação, correlações, top municípios por amputação.
2. `notebooks/03_indice_icvd.ipynb` — ICVD municipal e regional, análise de sensibilidade dos pesos, trilha de gênero. Gera `data/gold/icvd_municipio.csv`, `data/gold/icvd_regiao.csv` e `data/gold/genero_regiao.csv`.

Conferir a análise de sensibilidade (Seção 3 do notebook 03) contra o critério de aceitação (sobreposição do top-100 acima de 80%, Spearman acima de 0,9) antes de seguir — se o critério não for atingido, o índice precisa de revisão antes do dashboard.

- [ ] Feito

## 8. Publicar no Google Sheets

**Por quê:** o Power BI consome as tabelas via Google Sheets, não direto dos CSVs locais — isso permite atualizar o dashboard sem reabrir o Power BI Desktop, e serve de camada de dados compartilhável fora do Git.

**Como:** seguir o passo a passo de `02-coleta-de-dados.md`, Seção 2.5, e o roteiro completo da Tarefa 13 (`.superpowers/sdd/2026-08-23-diabetes-sus/task-13-brief.md`) — criar a planilha `diabetes_sus_gold`, importar `municipio_ano.csv`, `icvd_municipio.csv`, `icvd_regiao.csv` e `genero_regiao.csv` como abas, publicar cada uma na web em formato CSV, e registrar as URLs publicadas em `02-coleta-de-dados.md`.

- [ ] Feito

## 9. Construir o dashboard no Power BI

**Por quê:** Power BI Desktop é uma ferramenta gráfica — não há como gerar um `.pbix` por código. O guia de construção completo (medidas DAX prontas para copiar, estrutura das três páginas, quais visuais usar) está em `docs/05-dashboard-powerbi.md`.

**Como:** seguir `docs/05-dashboard-powerbi.md` do início ao fim: conectar as fontes publicadas no Sheets, criar as medidas DAX, montar as três páginas, exportar `dashboard/dashboard.pdf` e os PNGs de `dashboard/previews/`.

- [ ] Feito

## 10. Preencher `docs/04-conclusoes.md` e a seção de achados do `README.md`

**Por quê:** são os dois documentos que dependem diretamente dos números reais — só podem ser escritos depois que os itens 1 a 9 estiverem concluídos. Estão deixados como esqueleto propositalmente (ver o aviso no topo de `docs/04-conclusoes.md`), para não haver risco de número inventado no documento entregue à tutoria.

**Como:** seguir a estrutura de seções já escrita em `docs/04-conclusoes.md` — cada seção já indica onde buscar o número. Depois, substituir o aviso "Pendente" da seção "Principais achados" do `README.md` pelos três achados mais fortes, e adicionar a imagem `dashboard/previews/pagina1.png` (gerada no passo 9) logo no início do README.

- [ ] Feito
