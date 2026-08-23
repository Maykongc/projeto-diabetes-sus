"""Baixa a população do Censo 2022 por município, sexo e faixa etária.

Fonte: agregado SIDRA 9514 ("População residente, por sexo, idade e forma
de declaração da idade" - Censo Demográfico 2022), variável 93 (população
residente), nível territorial N6 (município).

Os códigos de classificação foram confirmados em
https://servicodados.ibge.gov.br/api/v3/agregados/9514/metadados antes de
serem usados aqui:

- Classificação 2 (Sexo): 4 = Homens, 5 = Mulheres.
- Classificação 287 (Idade): usamos apenas as categorias de nível 1, que
  já são os grupos quinquenais completos (ex.: "30 a 34 anos"), evitando
  contar em dobro os níveis mais finos (idade em anos e em meses) que a
  mesma classificação também expõe.
"""

import sys
import time

import pandas as pd
import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1] / "src"))

from diabetes_sus.config import DIR_GOLD, ROTULOS_FAIXAS  # noqa: E402
from diabetes_sus.municipios import regiao_da_uf, uf_do_codigo  # noqa: E402

URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/9514"
    "/periodos/2022/variaveis/93"
    "?localidades=N6[N3[{uf}]]&classificacao=2[4,5]|287[{grupos}]"
)

# Códigos reais da classificação 287 (grupo quinquenal de idade, nível 1)
# que compõem cada faixa do projeto, conforme os metadados do agregado 9514.
GRUPOS_POR_FAIXA = {
    "<30": [93070, 93084, 93085, 93086, 93087, 93088],
    # 0 a 4, 5 a 9, 10 a 14, 15 a 19, 20 a 24, 25 a 29 anos
    "30-39": [93089, 93090],  # 30 a 34, 35 a 39 anos
    "40-49": [93091, 93092],  # 40 a 44, 45 a 49 anos
    "50-59": [93093, 93094],  # 50 a 54, 55 a 59 anos
    "60-69": [93095, 93096],  # 60 a 64, 65 a 69 anos
    "70-79": [93097, 93098],  # 70 a 74, 75 a 79 anos
    "80+": [49108, 49109, 60040, 60041, 6653],
    # 80 a 84, 85 a 89, 90 a 94, 95 a 99, 100 anos ou mais
}
GRUPO_PARA_FAIXA = {
    g: faixa for faixa, grupos in GRUPOS_POR_FAIXA.items() for g in grupos
}
SEXO_POR_CODIGO = {"4": "M", "5": "F"}
CODIGOS_UF = list(range(11, 18)) + list(range(21, 30)) + [31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]


def baixar_uf(cod_uf: int) -> pd.DataFrame:
    grupos = ",".join(str(g) for g in GRUPO_PARA_FAIXA)
    url = URL.format(uf=cod_uf, grupos=grupos)
    resposta = requests.get(url, timeout=180)
    resposta.raise_for_status()
    linhas = []
    for variavel in resposta.json():
        for resultado in variavel["resultados"]:
            cod_sexo = resultado["classificacoes"][0]["categoria"]
            cod_grupo = resultado["classificacoes"][1]["categoria"]
            sexo = SEXO_POR_CODIGO[next(iter(cod_sexo))]
            grupo = int(next(iter(cod_grupo)))
            for serie in resultado["series"]:
                valor = next(iter(serie["serie"].values()))
                linhas.append(
                    {
                        "cod_municipio": serie["localidade"]["id"],
                        "sexo": sexo,
                        "faixa_etaria": GRUPO_PARA_FAIXA[grupo],
                        "populacao": pd.to_numeric(valor, errors="coerce"),
                    }
                )
    return pd.DataFrame(linhas)


def main() -> None:
    partes = []
    for cod_uf in CODIGOS_UF:
        print(f"baixando UF {cod_uf}...", flush=True)
        for tentativa in range(3):
            try:
                partes.append(baixar_uf(cod_uf))
                break
            except requests.RequestException as erro:
                print(f"  tentativa {tentativa + 1} falhou: {erro}")
                time.sleep(5 * (tentativa + 1))
        else:
            raise SystemExit(f"UF {cod_uf} falhou nas 3 tentativas")

    pop = pd.concat(partes, ignore_index=True)
    pop["populacao"] = pop["populacao"].fillna(0).astype("int64")
    pop = (
        pop.groupby(["cod_municipio", "sexo", "faixa_etaria"], as_index=False)[
            "populacao"
        ]
        .sum()
    )
    pop["uf"] = uf_do_codigo(pop["cod_municipio"])
    pop["regiao"] = regiao_da_uf(pop["uf"])
    pop["faixa_etaria"] = pd.Categorical(
        pop["faixa_etaria"], categories=ROTULOS_FAIXAS, ordered=True
    )

    DIR_GOLD.mkdir(parents=True, exist_ok=True)
    destino = DIR_GOLD / "populacao_municipio_faixa_sexo.parquet"
    pop.to_parquet(destino, index=False)
    print(f"gravado: {destino}")
    print(f"municipios: {pop['cod_municipio'].nunique()}")
    print(f"populacao total: {pop['populacao'].sum():,}")


if __name__ == "__main__":
    main()
