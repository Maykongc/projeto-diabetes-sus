"""Conversão da idade codificada do SIH para anos e faixas etárias."""

import numpy as np
import pandas as pd

from diabetes_sus.config import LIMITES_FAIXAS, ROTULOS_FAIXAS

_DIAS = 2
_MESES = 3
_ANOS = 4
_ANOS_ACIMA_DE_CEM = 5


def idade_em_anos(idade: pd.Series, cod_idade: pd.Series) -> pd.Series:
    """Converte IDADE + COD_IDADE do SIH para anos completos.

    COD_IDADE: 2 = dias, 3 = meses, 4 = anos, 5 = anos acima de 100
    (a idade registrada precisa ser somada a 100). Qualquer outro código
    é tratado como desconhecido e devolve NaN.
    """
    valor = pd.to_numeric(idade, errors="coerce")
    codigo = pd.to_numeric(cod_idade, errors="coerce")

    anos = pd.Series(np.nan, index=valor.index, dtype="float64")
    anos = anos.mask(codigo.isin([_DIAS, _MESES]), 0.0)
    anos = anos.mask(codigo == _ANOS, valor)
    anos = anos.mask(codigo == _ANOS_ACIMA_DE_CEM, valor + 100)

    return anos.mask(anos < 0, np.nan)


def faixa_etaria(anos: pd.Series) -> pd.Series:
    """Atribui a faixa etária do projeto a uma série de idades em anos."""
    limites = [-np.inf, *LIMITES_FAIXAS, np.inf]
    return pd.cut(
        pd.to_numeric(anos, errors="coerce"),
        bins=limites,
        labels=ROTULOS_FAIXAS,
        right=True,
    )
