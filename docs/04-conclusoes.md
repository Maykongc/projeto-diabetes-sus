# Conclusões

> **PENDENTE DE PREENCHIMENTO.** Este documento é um esqueleto. Nenhum número, achado ou nome de município abaixo foi calculado ainda — a camada gold (`data/gold/municipio_ano.csv`) só existe depois da ingestão manual no Google Colab, que ainda não foi executada. Preencher esta página é o último passo do checklist em `00-execucao-manual.md`, depois de rodar os notebooks `02_eda.ipynb` e `03_indice_icvd.ipynb` com dados reais. Cada seção abaixo indica a pergunta que ela precisa responder e onde buscar o número exato — notebook, célula e arquivo de saída.

---

## 1. Panorama nacional

**Pergunta:** qual o volume total de internações, amputações, óbitos e gasto SUS por diabetes no período 2019–2024? Como esses números se comportam ano a ano, e qual o efeito visível do bloco 2020–2021?

**Onde buscar:** `notebooks/02_eda.ipynb`, Seção 2 ("Panorama nacional e efeito da pandemia"), célula que executa a consulta 1 de `sql/consultas_duckdb.sql`. Gráfico de série temporal na mesma seção.

## 2. Os cinco a sete achados principais

**Pergunta:** quais são os padrões mais fortes e mais defensáveis encontrados na análise — os que sustentariam uma recomendação de política pública sem precisar de qualificação extensa? Cada achado deve vir com o número que o sustenta e a fonte desse número.

**Onde buscar:** cruzar `notebooks/02_eda.ipynb` (Seções 3 a 8: distribuição da taxa bruta, taxa por região, blocos pré/durante/pós-pandemia, cobertura de APS contra taxa de internação, correlação entre indicadores, top municípios por amputação) com `notebooks/03_indice_icvd.ipynb` (Seções 2 e 4: ICVD municipal e regional). Candidatos a achado forte: a região com maior ICVD atual; a região com pior recuperação (delta mais positivo) entre 2019 e 2023–24; a correlação entre cobertura de APS e taxa padronizada de internação.

## 3. Desigualdade regional — resultado central

**Pergunta:** o ICVD varia entre regiões de forma que sustente a hipótese de desigualdade no cuidado? Qual região tem o pior ICVD atual (`icvd_2023_24`)? Qual teve a pior recuperação (`recuperacao` mais positiva, indicando piora, ou mais negativa, indicando melhora)?

**Onde buscar:** `data/gold/icvd_regiao.csv` (gerado por `notebooks/03_indice_icvd.ipynb`, Seção 4) para a comparação por região; `data/gold/icvd_municipio.csv` (Seção 6 do mesmo notebook) para o detalhe municipal, já com o corte de 20 internações aplicado (`no_ranking`) e a coluna `recuperacao`.

## 4. Resultado do teste da hipótese de gênero

**Pergunta:** homens apresentam proporção de amputação e letalidade consistentemente maiores que mulheres nas cinco regiões, enquanto a taxa padronizada de internação permanece semelhante entre os sexos? A hipótese descrita em `03-modelagem.md`, Seção 3.8, foi sustentada ou refutada — e com que margem?

**Onde buscar:** `notebooks/03_indice_icvd.ipynb`, Seção 5 ("Trilha de gênero") e a célula markdown logo abaixo que define o critério do teste; arquivo de saída `data/gold/genero_regiao.csv`.

## 5. Resultado da análise de sensibilidade dos pesos

**Pergunta:** o ranking do ICVD é estável sob os três esquemas alternativos de pesos (desfecho, estrutural, acesso)? A sobreposição do top-100 ficou acima de 80% e a correlação de Spearman acima de 0,9 (critério definido em `03-modelagem.md`, Seção 3.7)? Se não, que revisão do índice isso exige?

**Onde buscar:** `notebooks/03_indice_icvd.ipynb`, Seção 3 ("Análise de sensibilidade dos pesos") — a saída impressa da célula de código lista `spearman` e `top100 em comum` para cada esquema.

## 6. Lista de municípios prioritários

**Pergunta:** quais municípios, entre os elegíveis para o ranking (`no_ranking = True`, ao menos 20 internações no período), têm o ICVD atual mais alto — os candidatos mais diretos a priorização orçamentária de atenção primária? Quais tiveram a pior recuperação, isto é, pioraram mais entre 2019 e 2023–24?

**Onde buscar:** `data/gold/icvd_municipio.csv`, ordenado por `icvd_2023_24` (top-20 piores) e por `recuperacao` (top-20 de maior piora). As mesmas duas tabelas alimentam a Página 2 do dashboard Power BI (ver `05-dashboard-powerbi.md`).

## 7. Recomendações de ação

**Pergunta:** dado o resultado das seções 3 a 6, que ação concreta de política pública ou de gestão em saúde decorre da análise? A quem ela se dirige (gestão municipal, estadual, federal)? Que dado adicional, se houver, fortaleceria a recomendação antes de virar decisão orçamentária real?

**Onde buscar:** não é extraído de um notebook — é a síntese interpretativa das seções 2, 3 e 6, escrita depois que os números estiverem confirmados. Deve evitar prescrever valor de investimento ou impacto financeiro específico, o que está fora de escopo do projeto (ver `03-modelagem.md` e a Seção 8 do desenho do projeto).

## 8. Limitações

Estas limitações não dependem do resultado da análise e podem ser afirmadas desde já:

**Subestimação de amputações pelo filtro simples.** O filtro de seleção usa apenas `DIAG_PRINC` em E10–E14 (diabetes como causa principal da internação), não um filtro composto que também capturaria amputações registradas com diabetes como diagnóstico secundário. O indicador de amputação deste projeto mede "entre as internações cuja causa principal é o diabetes, quantas terminam em amputação" — não o total absoluto de amputações por pé diabético no país, que é maior. O ranking comparativo entre municípios se sustenta sob a suposição de que esse viés é aproximadamente uniforme entre eles; essa suposição não foi verificada de forma independente (ver `02-coleta-de-dados.md`, Seção 2.3).

**Variação de codificação entre regiões.** Práticas de registro hospitalar — como um procedimento é codificado, com que diagnóstico principal — podem variar entre estados e entre tipos de hospital. Essa variação é uma fonte potencial de viés residual justamente no tipo de comparação regional que é o objeto central deste estudo, e não há, dentro do escopo deste projeto, uma forma de quantificar ou corrigir esse viés.

**IDHM defasado.** O IDHM municipal usado como variável de contexto (Atlas Brasil/PNUD) tem como base o Censo 2010 — a fonte mais recente disponível nesse formato —, enquanto o restante da análise usa a população do Censo 2022. Qualquer cruzamento com o IDHM carrega essa defasagem de mais de uma década e deve ser lido como indicativo de contexto socioeconômico estrutural, não como retrato atual.

**Corte de 20 internações remove proporcionalmente mais municípios do Sul.** O corte usado para estabilizar o ranking municipal (`03-modelagem.md`, Seção 3.5) exclui 35,3% dos municípios do Sul contra 12,5% do Nordeste, porque municípios pequenos se concentram no Sul e no Centro-Oeste. Por isso o corte é aplicado exclusivamente ao ranking municipal, nunca às análises regionais — mas mesmo dentro do ranking, um leitor comparando "quantos municípios do Sul aparecem na lista" contra "quantos do Nordeste aparecem" precisa lembrar que a base de elegibilidade já não é a mesma proporção de municípios de cada região.

**Premissa de taxa nacional de referência não validada.** A tabela de impacto do corte em `03-modelagem.md`, Seção 3.5, assume uma taxa nacional de aproximadamente 70 internações por 100 mil habitantes/ano para estimar a população mínima de cada limiar de corte. Essa premissa precisa ser confrontada com a taxa observada nos dados reais assim que a camada gold existir; se divergir de forma relevante, os números de "municípios fora" e "% da população mantida" nessa tabela devem ser recalculados.
