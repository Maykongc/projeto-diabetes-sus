"""Regras de seleção das internações do SIH/SUS."""

import pandas as pd

from diabetes_sus.config import (
    CID_DIABETES_PREFIXOS,
    SIGTAP_AMPUTACAO_MMII_PREFIXO,
)

IDENT_CONTINUACAO = 5


def eh_diabetes(diag_princ: pd.Series) -> pd.Series:
    """Marca internações cujo diagnóstico principal é diabetes (E10-E14).

    Compara os três primeiros caracteres em vez de usar startswith com
    tupla, que não é suportado de forma consistente entre os backends de
    string do pandas.
    """
    normalizado = diag_princ.astype("string").str.upper().str.strip()
    return (
        normalizado.str[:3].isin(CID_DIABETES_PREFIXOS).fillna(False).astype(bool)
    )


def eh_amputacao_mmii(proc_rea: pd.Series) -> pd.Series:
    """Marca procedimentos de amputação de membro inferior (SIGTAP 040805)."""
    normalizado = proc_rea.astype("string").str.strip().str.zfill(10)
    prefixo = normalizado.str[: len(SIGTAP_AMPUTACAO_MMII_PREFIXO)]
    return prefixo.eq(SIGTAP_AMPUTACAO_MMII_PREFIXO).fillna(False).astype(bool)


def remover_aih_continuacao(
    df: pd.DataFrame, coluna: str = "IDENT"
) -> pd.DataFrame:
    """Descarta AIHs de continuação, que não são novas internações."""
    ident = pd.to_numeric(df[coluna], errors="coerce")
    return df.loc[ident != IDENT_CONTINUACAO].copy()


def filtrar_internacoes_diabetes(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o recorte do projeto e marca as internações com amputação."""
    sem_continuacao = remover_aih_continuacao(df)
    diabetes = sem_continuacao.loc[
        eh_diabetes(sem_continuacao["DIAG_PRINC"])
    ].copy()
    diabetes["amputacao"] = eh_amputacao_mmii(diabetes["PROC_REA"])
    return diabetes.reset_index(drop=True)
