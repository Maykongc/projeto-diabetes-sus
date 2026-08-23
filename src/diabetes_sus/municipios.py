"""Compatibilização de códigos de município e mapeamento territorial."""

from typing import Iterable

import pandas as pd

from diabetes_sus.config import CODIGO_UF_PARA_SIGLA, UF_PARA_REGIAO


def mapa_6_para_7(codigos7: Iterable) -> dict:
    """Constrói o dicionário de código IBGE de 6 dígitos para 7 dígitos.

    O SIH grava o município sem o dígito verificador; o IBGE publica com ele.
    """
    return {str(c)[:6]: str(c) for c in codigos7}


def completar_codigo(cod6: pd.Series, mapa: dict) -> pd.Series:
    """Expande códigos de 6 dígitos para 7. Códigos ausentes viram NaN."""
    return cod6.astype("string").str.strip().map(mapa).astype("string")


def uf_do_codigo(codigo: pd.Series) -> pd.Series:
    """Extrai a sigla da UF dos dois primeiros dígitos do código IBGE."""
    prefixo = pd.to_numeric(
        codigo.astype("string").str.strip().str[:2], errors="coerce"
    )
    return prefixo.map(CODIGO_UF_PARA_SIGLA).astype("string")


def regiao_da_uf(uf: pd.Series) -> pd.Series:
    """Mapeia a sigla da UF para a macrorregião do IBGE."""
    return uf.astype("string").str.upper().str.strip().map(UF_PARA_REGIAO).astype(
        "string"
    )
