import pandas as pd
import pytest

from diabetes_sus.padronizacao import (
    padronizar_por_grupo,
    padronizar_por_municipio,
    taxa_padronizada,
)


def test_estrutura_igual_ao_padrao_devolve_a_taxa_bruta():
    # 10 casos em 1000 pessoas = 1000 por 100 mil, em qualquer faixa.
    resultado = taxa_padronizada(
        casos=[5, 5], populacao=[500, 500], pop_padrao=[500, 500]
    )
    assert resultado == pytest.approx(1000.0)


def test_padronizacao_corrige_estrutura_envelhecida():
    # Município concentrado na faixa idosa, que adoece mais.
    # Taxa bruta seria alta; padronizada pelo padrão jovem, cai.
    bruta = (1 + 19) / (100 + 100) * 100_000
    padronizada = taxa_padronizada(
        casos=[1, 19], populacao=[100, 100], pop_padrao=[900, 100]
    )
    assert padronizada < bruta


def test_pesos_somam_um_independente_da_escala_do_padrao():
    a = taxa_padronizada([3, 7], [100, 200], [50, 150])
    b = taxa_padronizada([3, 7], [100, 200], [5000, 15000])
    assert a == pytest.approx(b)


def test_tamanhos_diferentes_levantam_erro():
    with pytest.raises(ValueError, match="mesmo tamanho"):
        taxa_padronizada([1, 2], [10], [10, 10])


def test_populacao_zero_levanta_erro():
    with pytest.raises(ValueError, match="positiva"):
        taxa_padronizada([1, 2], [0, 10], [10, 10])


def test_padronizar_por_municipio_devolve_uma_linha_por_municipio():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 2 + ["2304400"] * 2,
            "faixa_etaria": ["<30", "80+"] * 2,
            "internacoes": [1, 9, 2, 8],
            "populacao": [1000, 100, 1000, 100],
        }
    )
    pop_padrao = pd.Series({"<30": 9000, "80+": 1000})
    resultado = padronizar_por_municipio(df, pop_padrao)

    assert len(resultado) == 2
    assert set(resultado.columns) == {
        "cod_municipio",
        "taxa_internacao_padronizada",
    }
    assert (resultado["taxa_internacao_padronizada"] > 0).all()


def test_padronizar_por_grupo_com_uma_coluna_equivale_ao_wrapper_municipal():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 2 + ["2304400"] * 2,
            "faixa_etaria": ["<30", "80+"] * 2,
            "internacoes": [1, 9, 2, 8],
            "populacao": [1000, 100, 1000, 100],
        }
    )
    pop_padrao = pd.Series({"<30": 9000, "80+": 1000})

    via_grupo = padronizar_por_grupo(df, "cod_municipio", pop_padrao)
    via_wrapper = padronizar_por_municipio(df, pop_padrao)

    pd.testing.assert_frame_equal(
        via_grupo.sort_values("cod_municipio").reset_index(drop=True),
        via_wrapper.sort_values("cod_municipio").reset_index(drop=True),
    )


def test_padronizar_por_grupo_com_duas_colunas_nao_usa_chave_composta():
    # Regiao e sexo devem virar duas colunas de saida, nunca uma unica
    # coluna do tipo "regiao|sexo".
    df = pd.DataFrame(
        {
            "regiao": ["Sul", "Sul", "Sul", "Sul", "Norte", "Norte", "Norte", "Norte"],
            "sexo": ["M", "M", "F", "F", "M", "M", "F", "F"],
            "faixa_etaria": ["<30", "80+"] * 4,
            "internacoes": [1, 9, 2, 8, 3, 7, 4, 6],
            "populacao": [1000, 100, 1000, 100, 1000, 100, 1000, 100],
        }
    )
    pop_padrao = pd.Series({"<30": 9000, "80+": 1000})

    resultado = padronizar_por_grupo(df, ["regiao", "sexo"], pop_padrao)

    assert len(resultado) == 4
    assert set(resultado.columns) == {
        "regiao",
        "sexo",
        "taxa_internacao_padronizada",
    }
    assert set(zip(resultado["regiao"], resultado["sexo"])) == {
        ("Sul", "M"),
        ("Sul", "F"),
        ("Norte", "M"),
        ("Norte", "F"),
    }
    assert (resultado["taxa_internacao_padronizada"] > 0).all()
