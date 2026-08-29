"""Agrega a camada bronze ate a camada gold, localmente.

Equivalente as Secoes 2.1 e 2.3 de `notebooks/01_ingestao_colab.ipynb`, que fazem o
mesmo com PySpark no Colab. Aqui a agregacao roda em DuckDB sobre a arvore de
parquets da bronze, e a montagem da grade completa em pandas.

A grade completa e o ponto critico: a bronze so tem linha onde houve internacao,
entao sem o produto cartesiano municipio x ano x sexo x faixa a populacao das
combinacoes sem caso nunca entraria no denominador, e a padronizacao etaria
inflaria a taxa dos municipios pequenos. Ver docs/03-modelagem.md, Secao 3.3.
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from diabetes_sus.municipios import (  # noqa: E402
    completar_codigo,
    mapa_6_para_7,
    regiao_da_uf,
    uf_do_codigo,
)

DIR_BRONZE = RAIZ / "data" / "bronze"
DIR_GOLD = RAIZ / "data" / "gold"

COLUNAS_GOLD = ["cod_municipio", "uf", "regiao", "ano", "sexo", "faixa_etaria",
                "internacoes", "amputacoes", "obitos", "val_total",
                "dias_perm_total", "populacao", "cobertura_aps",
                "idade_soma", "idade_validas"]

CONTAGENS = ["internacoes", "amputacoes", "obitos", "val_total",
             "dias_perm_total", "idade_soma", "idade_validas"]

AGREGACAO = """
SELECT
    cod_municipio_6,
    ano,
    sexo,
    faixa_etaria,
    COUNT(*)                                   AS internacoes,
    SUM(CAST(amputacao AS INTEGER))            AS amputacoes,
    SUM(morte)                                 AS obitos,
    SUM(val_tot)                               AS val_total,
    SUM(dias_perm)                             AS dias_perm_total,
    SUM(idade_anos)                            AS idade_soma,
    COUNT(idade_anos)                          AS idade_validas
FROM read_parquet(?, hive_partitioning = false)
WHERE faixa_etaria IS NOT NULL
GROUP BY ALL
"""


def main() -> None:
    padrao = str(DIR_BRONZE / "**" / "*.parquet")

    con = duckdb.connect()
    bruto = con.execute("SELECT COUNT(*) FROM read_parquet(?)", [padrao]).fetchone()[0]
    silver = con.execute(AGREGACAO, [padrao]).df()
    con.close()

    print(f"bronze : {bruto:,} internacoes de diabetes")
    print(f"silver : {len(silver):,} linhas (municipio x ano x sexo x faixa)")

    sem_faixa = bruto - int(silver["internacoes"].sum())
    print(f"         {sem_faixa:,} internacoes sem faixa etaria valida, fora da gold")

    pop = pd.read_parquet(DIR_GOLD / "populacao_municipio_faixa_sexo.parquet")
    aps = pd.read_csv(DIR_GOLD / "cobertura_aps.csv",
                      dtype={"cod_municipio": str},
                      usecols=["cod_municipio", "ano", "cobertura_aps"])

    mapa = mapa_6_para_7(pop["cod_municipio"].unique())
    silver["cod_municipio"] = completar_codigo(silver["cod_municipio_6"], mapa)
    orfaos = int(silver["cod_municipio"].isna().sum())
    print(f"         {orfaos} linhas sem municipio correspondente no IBGE")

    sexo_bruto = silver["sexo"]
    silver["sexo"] = sexo_bruto.map({"1": "M", "3": "F"})
    nao_mapeado = int((sexo_bruto.notna() & silver["sexo"].isna()).sum())
    print(f"         {nao_mapeado} linhas com sexo fora de 1/3")

    chave = ["cod_municipio", "ano", "sexo", "faixa_etaria"]
    agregada = (silver.dropna(subset=["cod_municipio", "sexo", "faixa_etaria"])
                      .groupby(chave, as_index=False, observed=True)[CONTAGENS]
                      .sum())

    anos = pd.DataFrame({"ano": list(range(2019, 2025))})
    grade = (pop.drop(columns=["uf", "regiao"], errors="ignore")
                .merge(anos, how="cross"))
    grade["faixa_etaria"] = grade["faixa_etaria"].astype(str)
    print(f"grade  : {len(grade):,} linhas (esperado 467.880)")

    gold = (grade.merge(agregada, on=chave, how="left")
                 .merge(aps, on=["cod_municipio", "ano"], how="left"))
    gold[CONTAGENS] = gold[CONTAGENS].fillna(0)
    gold["uf"] = uf_do_codigo(gold["cod_municipio"])
    gold["regiao"] = regiao_da_uf(gold["uf"])
    gold = gold[COLUNAS_GOLD]

    DIR_GOLD.mkdir(parents=True, exist_ok=True)
    destino = DIR_GOLD / "municipio_ano.csv"
    gold.to_csv(destino, index=False)

    print(f"\ngold   : {gold.shape} -> {destino}")
    print(f"         internacoes totais: {int(gold['internacoes'].sum()):,}")
    print(f"         municipios: {gold['cod_municipio'].nunique()}")
    print(f"         anos: {sorted(gold['ano'].unique())}")
    nulos = gold[["cod_municipio", "populacao", "internacoes"]].isna().sum()
    print(f"         nulos em colunas criticas:\n{nulos.to_string()}")


if __name__ == "__main__":
    main()
