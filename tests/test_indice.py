import numpy as np
import pandas as pd
import pytest

from diabetes_sus.config import PERIODO_ATUAL, PERIODO_BASE
from diabetes_sus.indice import (
    aplicar_corte,
    calcular_icvd,
    calcular_recuperacao,
    normalizar_minmax,
    winsorizar,
)


def quadro(n=6, periodo=PERIODO_BASE, **sobrescreve):
    base = {
        "cod_municipio": [f"350000{i}" for i in range(n)],
        "periodo": [periodo] * n,
        "internacoes": [100] * n,
        "taxa_internacao_padronizada": np.linspace(10, 60, n),
        "prop_amputacao": np.linspace(0.01, 0.06, n),
        "letalidade": np.linspace(0.02, 0.12, n),
        "cobertura_aps": np.linspace(100, 50, n),
    }
    base.update(sobrescreve)
    return pd.DataFrame(base)


def test_winsorizacao_corta_os_extremos():
    s = pd.Series([1, 2, 3, 4, 1000])
    resultado = winsorizar(s, 0.0, 0.75)
    assert resultado.max() == 4.0


def test_normalizar_minmax_mapeia_para_zero_um():
    resultado = normalizar_minmax(pd.Series([10.0, 20.0, 30.0]))
    assert resultado.tolist() == [0.0, 0.5, 1.0]


def test_normalizar_serie_constante_levanta_erro():
    with pytest.raises(ValueError, match="constante"):
        normalizar_minmax(pd.Series([5.0, 5.0]))


def test_corte_marca_municipios_com_poucas_internacoes():
    df = pd.DataFrame({"internacoes": [5, 19, 20, 300]})
    resultado = aplicar_corte(df, corte=20)
    assert resultado["no_ranking"].tolist() == [False, False, True, True]


def test_icvd_fica_entre_zero_e_um():
    resultado = calcular_icvd(quadro())
    assert resultado["icvd"].between(0, 1).all()


def test_cobertura_aps_entra_invertida():
    # O município com MAIOR cobertura precisa ter o MENOR componente normalizado.
    resultado = calcular_icvd(quadro()).sort_values("cobertura_aps")
    assert resultado["cobertura_aps_norm"].iloc[-1] < (
        resultado["cobertura_aps_norm"].iloc[0]
    )


def test_pior_municipio_em_tudo_tem_icvd_um():
    resultado = calcular_icvd(quadro())
    pior = resultado.loc[resultado["taxa_internacao_padronizada"].idxmax()]
    assert pior["icvd"] == pytest.approx(1.0)


def test_escala_e_comum_aos_dois_periodos():
    # Se 2023-24 for uniformemente melhor que 2019, todo ICVD de 2023-24
    # precisa ficar abaixo — o que só acontece com escala compartilhada.
    base = quadro(periodo=PERIODO_BASE)
    atual = quadro(
        periodo=PERIODO_ATUAL,
        taxa_internacao_padronizada=np.linspace(5, 30, 6),
        prop_amputacao=np.linspace(0.005, 0.03, 6),
        letalidade=np.linspace(0.01, 0.06, 6),
        cobertura_aps=np.linspace(100, 80, 6),
    )
    resultado = calcular_icvd(pd.concat([base, atual], ignore_index=True))

    media_base = resultado.loc[resultado["periodo"] == PERIODO_BASE, "icvd"].mean()
    media_atual = resultado.loc[
        resultado["periodo"] == PERIODO_ATUAL, "icvd"
    ].mean()
    assert media_atual < media_base


def test_recuperacao_negativa_significa_melhora():
    base = quadro(periodo=PERIODO_BASE)
    atual = quadro(
        periodo=PERIODO_ATUAL,
        taxa_internacao_padronizada=np.linspace(5, 30, 6),
        prop_amputacao=np.linspace(0.005, 0.03, 6),
        letalidade=np.linspace(0.01, 0.06, 6),
        cobertura_aps=np.linspace(100, 80, 6),
    )
    icvd = calcular_icvd(pd.concat([base, atual], ignore_index=True))
    resultado = calcular_recuperacao(icvd)

    assert set(resultado.columns) == {
        "cod_municipio", "icvd_2019", "icvd_2023_24", "recuperacao",
    }
    assert (resultado["recuperacao"] < 0).all()


def test_pesos_alternativos_mudam_o_icvd():
    # Os componentes precisam ser NAO colineares. Quatro linspaces
    # monotonicos viram vetores identicos depois de normalizados, e a media
    # ponderada de vetores identicos ignora os pesos — o teste passaria a
    # ser impossivel de falhar por motivo errado.
    df = quadro(prop_amputacao=[0.06, 0.01, 0.05, 0.02, 0.04, 0.03])
    igual = calcular_icvd(df)["icvd"]
    pesado = calcular_icvd(
        df,
        pesos={
            "taxa_internacao_padronizada": 0.1,
            "prop_amputacao": 0.7,
            "letalidade": 0.1,
            "cobertura_aps": 0.1,
        },
    )["icvd"]
    assert not np.allclose(igual, pesado)


def test_pesos_que_nao_somam_um_levantam_erro():
    with pytest.raises(ValueError, match="somar 1"):
        calcular_icvd(
            quadro(),
            pesos={
                "taxa_internacao_padronizada": 0.5,
                "prop_amputacao": 0.5,
                "letalidade": 0.5,
                "cobertura_aps": 0.5,
            },
        )
