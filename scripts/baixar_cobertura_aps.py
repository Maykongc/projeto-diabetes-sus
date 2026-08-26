"""Baixa a cobertura de Atencao Primaria por municipio do portal Relatorios Publicos da APS.

O antigo e-Gestor AB foi substituido por https://relatorioaps.saude.gov.br, cuja API
publica expoe duas series com metodologias e periodos DISJUNTOS:

  /cobertura/ab   Cobertura de Atencao Basica  -- competencias 2019-01 a 2020-12
  /cobertura/aps  Cobertura Potencial da APS   -- competencias 2021-01 a 2024-12

Nao ha sobreposicao entre elas, portanto nao ha como calibrar uma contra a outra.
A coluna `fonte` registra de qual serie veio cada linha; a decisao de como usa-las
esta documentada em docs/03-modelagem.md.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from diabetes_sus.config import DIR_GOLD  # noqa: E402
from diabetes_sus.municipios import (  # noqa: E402
    completar_codigo,
    mapa_6_para_7,
    regiao_da_uf,
    uf_do_codigo,
)

API = "https://relatorioaps-prd.saude.gov.br"

SERIES = [
    {"rota": "/cobertura/ab", "inicio": "201901", "fim": "202012",
     "campo": "pcCoberturaAb", "fonte": "cobertura_ab"},
    {"rota": "/cobertura/aps", "inicio": "202101", "fim": "202412",
     "campo": "qtCobertura", "fonte": "cobertura_aps"},
]

CODIGOS_UF = (
    list(range(11, 18)) + list(range(21, 30))
    + [31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]
)


def ano_da_competencia(nu_comp: str) -> int:
    """A serie /ab devolve 'AAAAMM'; a /aps devolve 'MM/AAAA'."""
    texto = str(nu_comp).strip()
    return int(texto[-4:]) if "/" in texto else int(texto[:4])


def baixar(rota: str, cod_uf: int, inicio: str, fim: str) -> list:
    url = (
        f"{API}{rota}?unidadeGeografica=MUNICIPIO"
        f"&nuCompInicio={inicio}&nuCompFim={fim}&coUf={cod_uf}"
    )
    for tentativa in range(3):
        try:
            resposta = requests.get(url, timeout=240)
            resposta.raise_for_status()
            return resposta.json()
        except (requests.RequestException, ValueError) as erro:
            print(f"    tentativa {tentativa + 1} falhou: {erro}", flush=True)
            time.sleep(5 * (tentativa + 1))
    raise SystemExit(f"{rota} UF {cod_uf} falhou nas 3 tentativas")


def main() -> None:
    linhas = []
    for serie in SERIES:
        print(f"== {serie['rota']} ({serie['inicio']}-{serie['fim']}) ==", flush=True)
        for cod_uf in CODIGOS_UF:
            registros = baixar(serie["rota"], cod_uf, serie["inicio"], serie["fim"])
            for r in registros:
                bruto = r.get(serie["campo"])
                if bruto is None:
                    continue
                valor = pd.to_numeric(
                    str(bruto).replace(".", "").replace(",", ".")
                    if isinstance(bruto, str) and "," in str(bruto)
                    else bruto,
                    errors="coerce",
                )
                linhas.append({
                    "cod_municipio_6": str(r["coMunicipioIbge"]),
                    "ano": ano_da_competencia(r["nuComp"]),
                    "cobertura": valor,
                    "fonte": serie["fonte"],
                })
            print(f"  UF {cod_uf}: {len(registros)} registros", flush=True)

    bruto = pd.DataFrame(linhas).dropna(subset=["cobertura"])

    # Media anual das competencias mensais de cada municipio.
    anual = (
        bruto.groupby(["cod_municipio_6", "ano", "fonte"], as_index=False)["cobertura"]
        .mean()
        .rename(columns={"cobertura": "cobertura_aps"})
    )

    pop = pd.read_parquet(DIR_GOLD / "populacao_municipio_faixa_sexo.parquet")
    mapa = mapa_6_para_7(pop["cod_municipio"].unique())
    anual["cod_municipio"] = completar_codigo(anual["cod_municipio_6"], mapa)

    orfaos = anual["cod_municipio"].isna().sum()
    if orfaos:
        print(f"AVISO: {orfaos} linhas sem municipio correspondente no IBGE")

    anual = anual.dropna(subset=["cod_municipio"]).copy()
    anual["uf"] = uf_do_codigo(anual["cod_municipio"])
    anual["regiao"] = regiao_da_uf(anual["uf"])
    anual["cobertura_aps"] = anual["cobertura_aps"].round(2)

    saida = anual[
        ["cod_municipio", "uf", "regiao", "ano", "cobertura_aps", "fonte"]
    ].sort_values(["cod_municipio", "ano"])

    DIR_GOLD.mkdir(parents=True, exist_ok=True)
    destino = DIR_GOLD / "cobertura_aps.csv"
    saida.to_csv(destino, index=False)

    print(f"\ngravado: {destino}")
    print(f"linhas: {len(saida)} | municipios: {saida['cod_municipio'].nunique()}")
    print(saida.groupby(["fonte", "ano"]).size().to_string())
    print(f"\ncobertura min/max: {saida['cobertura_aps'].min()} / {saida['cobertura_aps'].max()}")


if __name__ == "__main__":
    main()
