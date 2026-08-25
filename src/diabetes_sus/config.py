"""Constantes do projeto."""

from pathlib import Path

CID_DIABETES_PREFIXOS = ("E10", "E11", "E12", "E13", "E14")
SIGTAP_AMPUTACAO_MMII_PREFIXO = "040805"

ANOS = tuple(range(2019, 2025))
ANO_BASELINE = 2019
ANOS_ATUAIS = (2023, 2024)
PERIODO_BASE = "2019"
PERIODO_ATUAL = "2023-24"

# Corte principal do ranking municipal: 20 internacoes no TOTAL de 2019-2024.
# E' o corte descrito na tabela de calibracao de docs/03-modelagem.md 3.5
# (mantem 98% da populacao). Aplicar 20 por periodo derrubaria o ranking para
# uma fracao dos municipios, porque 2019 e um ano e 2023-24 sao dois.
CORTE_MIN_INTERNACOES = 20
# Requisito secundario: pelo menos 5 internacoes em CADA periodo, para que
# letalidade e prop_amputacao daquele periodo tenham denominador nao degenerado.
CORTE_MIN_INTERNACOES_PERIODO = 5

ROTULOS_FAIXAS = ["<30", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
LIMITES_FAIXAS = [29, 39, 49, 59, 69, 79]

COMPONENTES_ICVD = [
    "taxa_internacao_padronizada",
    "prop_amputacao",
    "letalidade",
    "cobertura_aps",
]
COMPONENTES_INVERTIDOS = ("cobertura_aps",)
PESOS_IGUAIS = {c: 0.25 for c in COMPONENTES_ICVD}

UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
)

CODIGO_UF_PARA_SIGLA = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

UF_PARA_REGIAO = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(
        ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"
    ),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

RAIZ = Path(__file__).resolve().parents[2]
DIR_DADOS = RAIZ / "data"
DIR_RAW = DIR_DADOS / "raw"
DIR_GOLD = DIR_DADOS / "gold"
