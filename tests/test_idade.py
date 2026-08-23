import numpy as np
import pandas as pd
import pytest

from diabetes_sus.idade import faixa_etaria, idade_em_anos


def test_cod_idade_4_significa_anos():
    resultado = idade_em_anos(pd.Series([45, 3, 80]), pd.Series([4, 4, 4]))
    assert resultado.tolist() == [45.0, 3.0, 80.0]


def test_cod_idade_5_soma_cem_anos():
    resultado = idade_em_anos(pd.Series([2, 7]), pd.Series([5, 5]))
    assert resultado.tolist() == [102.0, 107.0]


def test_dias_e_meses_viram_zero_anos():
    resultado = idade_em_anos(pd.Series([15, 8]), pd.Series([2, 3]))
    assert resultado.tolist() == [0.0, 0.0]


def test_codigo_desconhecido_vira_nan():
    resultado = idade_em_anos(pd.Series([30]), pd.Series([9]))
    assert np.isnan(resultado.iloc[0])


def test_idade_negativa_vira_nan():
    resultado = idade_em_anos(pd.Series([-5]), pd.Series([4]))
    assert np.isnan(resultado.iloc[0])


def test_faixa_etaria_respeita_os_limites():
    anos = pd.Series([0, 29, 30, 39, 40, 59, 60, 79, 80, 105])
    esperado = [
        "<30", "<30", "30-39", "30-39", "40-49",
        "50-59", "60-69", "70-79", "80+", "80+",
    ]
    assert faixa_etaria(anos).astype(str).tolist() == esperado


def test_faixa_etaria_propaga_nan():
    resultado = faixa_etaria(pd.Series([np.nan]))
    assert pd.isna(resultado.iloc[0])
