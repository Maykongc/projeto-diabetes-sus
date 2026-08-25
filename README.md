# Desigualdade Regional no Cuidado ao Diabetes no SUS

Projeto de Parceria do curso de Analista de Dados (EBAC/Semantix). Análise de 5.570 municípios brasileiros entre 2019 e 2024, medindo se o SUS entrega o mesmo cuidado ao diabético em todo o território — e quem paga a conta onde não entrega. O eixo central é o choque assistencial da pandemia (2020–2021) e a recuperação desigual que veio depois dele. O raciocínio completo do problema está em [`docs/01-problema.md`](docs/01-problema.md).

## Principais achados

**Pendente.** Esta seção só pode ser preenchida depois que o pipeline completo rodar contra dados reais — a camada gold (`data/gold/municipio_ano.csv`) ainda não existe, porque a ingestão no Google Colab é uma etapa manual que ainda não foi executada. O checklist para chegar até aqui está em [`docs/00-execucao-manual.md`](docs/00-execucao-manual.md); a estrutura de onde cada achado vai ser extraído já está pronta em [`docs/04-conclusoes.md`](docs/04-conclusoes.md).

## Documentação

- [Execução manual — checklist](docs/00-execucao-manual.md) — o que precisa ser feito à mão, e por quê
- [Problema e justificativa](docs/01-problema.md)
- [Coleta de dados](docs/02-coleta-de-dados.md)
- [Modelagem](docs/03-modelagem.md)
- [Conclusões](docs/04-conclusoes.md) — pendente de preenchimento
- [Guia do dashboard Power BI](docs/05-dashboard-powerbi.md)

## Como reproduzir

O passo a passo detalhado, com o motivo de cada etapa manual, está em [`docs/00-execucao-manual.md`](docs/00-execucao-manual.md). Resumo:

1. `pip install -r requirements.txt`
2. `python scripts/baixar_populacao_ibge.py` — baixa a população do Censo 2022 por município, sexo e faixa etária (já versionada em `data/gold/populacao_municipio_faixa_sexo.parquet`, não precisa rodar de novo a menos que o dado mude)
3. Subir `src/diabetes_sus/` e os insumos (população, cobertura de APS) para o Google Drive
4. Abrir `notebooks/01_ingestao_colab.ipynb` no Google Colab e executar — é a etapa longa (1.944 arquivos de AIH), idempotente, pode ser reexecutada após queda de sessão
5. Baixar `municipio_ano.csv` do Drive para `data/gold/`
6. Reconciliar contra o TabNet do DATASUS (divergência acima de 2% bloqueia a entrega)
7. `python -m pytest` — confere os módulos de cálculo (idade, padronização, índice, validação)
8. Executar `notebooks/02_eda.ipynb` e `notebooks/03_indice_icvd.ipynb`
9. Publicar a camada gold no Google Sheets
10. Abrir `dashboard/diabetes_sus.pbix` no Power BI Desktop e construir o dashboard conforme `docs/05-dashboard-powerbi.md`
11. Preencher `docs/04-conclusoes.md` e a seção "Principais achados" acima

## Estrutura de pastas

```
├── README.md
├── requirements.txt
├── docs/
│   ├── 00-execucao-manual.md     checklist de etapas manuais
│   ├── 01-problema.md
│   ├── 02-coleta-de-dados.md
│   ├── 03-modelagem.md
│   ├── 04-conclusoes.md          pendente de preenchimento
│   └── 05-dashboard-powerbi.md
├── notebooks/
│   ├── 01_ingestao_colab.ipynb   roda no Google Colab (bronze -> silver -> gold)
│   ├── 02_eda.ipynb              local, DuckDB + pandas
│   └── 03_indice_icvd.ipynb      local, calcula o ICVD e a trilha de gênero
├── sql/consultas_duckdb.sql
├── scripts/baixar_populacao_ibge.py
├── src/diabetes_sus/             pacote testado, usado localmente e no Colab
├── tests/                        65 testes, `python -m pytest`
├── data/gold/                    camada gold (CSV/Parquet, versionável)
├── dashboard/                    diabetes_sus.pbix, dashboard.pdf, previews/*.png
└── .gitignore                    bloqueia data/bronze/, data/silver/, .dbc, .dbf
```

## Stack

Python · pandas · DuckDB · PySpark (Colab) · pytest · Power BI Desktop · Google Sheets

## Fontes de dados

SIH/SUS e SIM (FTP DATASUS), e-Gestor Atenção Básica, CNES, população do Censo 2022 (IBGE/SIDRA), IDHM (Atlas Brasil/PNUD) e VIGITEL. Detalhamento completo, com URLs e método de acesso, em [`docs/02-coleta-de-dados.md`](docs/02-coleta-de-dados.md).

## Desvios declarados em relação ao briefing original

- **Visualização em Power BI, não Looker Studio** (pedido no briefing original) — decisão do autor, camada analítica é indiferente à ferramenta. Detalhes em `docs/05-dashboard-powerbi.md`.
- **Mapa por UF, não por município** — o Shape Map do Power BI não sustenta 5.570 polígonos de forma confiável. A granularidade municipal aparece na dispersão e nos rankings do dashboard.
- **Sem link público do dashboard** — o Power BI Service não aceita conta de e-mail pessoal (`@gmail.com`). Entrega via `.pbix` versionado, PDF e PNGs.
