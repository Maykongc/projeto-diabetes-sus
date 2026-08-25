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


# --- Faixa etaria ausente no grupo (correcao C1 da revisao final) ------------
#
# A camada gold so tem linha para (municipio, ano, sexo, faixa) que registrou
# ao menos uma internacao. A faixa sem nenhum caso simplesmente nao aparece.
# Se o peso dela for redistribuido entre as faixas presentes, a taxa infla —
# e infla mais em municipio pequeno, que tem mais faixas vazias.

POP_PADRAO_TRES_FAIXAS = pd.Series({"<30": 4200, "60-69": 800, "80+": 1000})


def test_faixa_sem_populacao_com_taxa_zero_preserva_o_peso():
    # Faixa <30 sem populacao e sem casos: taxa zero, peso 4200/6000 mantido.
    # (5/100)*800/6000 + (10/100)*1000/6000 = 140/6000 -> 2333.33 por 100 mil.
    resultado = taxa_padronizada(
        casos=[0, 5, 10],
        populacao=[0, 100, 100],
        pop_padrao=[4200, 800, 1000],
        faixa_sem_populacao="taxa_zero",
    )
    assert resultado == pytest.approx(140 / 6000 * 100_000)


def test_faixa_sem_populacao_no_modo_erro_continua_levantando():
    with pytest.raises(ValueError, match="positiva"):
        taxa_padronizada(
            casos=[0, 5],
            populacao=[0, 100],
            pop_padrao=[4200, 800],
        )


def test_todas_as_faixas_sem_populacao_levanta_erro():
    with pytest.raises(ValueError, match="nenhuma faixa"):
        taxa_padronizada(
            casos=[0, 0],
            populacao=[0, 0],
            pop_padrao=[4200, 800],
            faixa_sem_populacao="taxa_zero",
        )


def test_casos_sem_populacao_levanta_erro_mesmo_no_modo_taxa_zero():
    with pytest.raises(ValueError, match="orfao de join"):
        taxa_padronizada(
            casos=[3, 5],
            populacao=[0, 100],
            pop_padrao=[4200, 800],
            faixa_sem_populacao="taxa_zero",
        )


def test_modo_de_faixa_sem_populacao_invalido_levanta_erro():
    with pytest.raises(ValueError, match="faixa_sem_populacao"):
        taxa_padronizada([1], [10], [10], faixa_sem_populacao="ignorar")


def test_faixa_ausente_equivale_a_faixa_presente_com_zero_casos():
    # ESTE TESTE FALHA com a renormalizacao antiga dos pesos.
    # Municipio A nao tem linha para <30 (nenhuma internacao naquela faixa).
    # Municipio B tem a linha, com a mesma populacao e zero casos.
    # Os dois descrevem exatamente a mesma realidade e precisam dar a mesma
    # taxa padronizada.
    sem_a_faixa = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 2,
            "faixa_etaria": ["60-69", "80+"],
            "internacoes": [5, 10],
            "populacao": [100, 100],
        }
    )
    com_a_faixa = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 3,
            "faixa_etaria": ["<30", "60-69", "80+"],
            "internacoes": [0, 5, 10],
            "populacao": [1000, 100, 100],
        }
    )

    taxa_sem = padronizar_por_municipio(sem_a_faixa, POP_PADRAO_TRES_FAIXAS)
    taxa_com = padronizar_por_municipio(com_a_faixa, POP_PADRAO_TRES_FAIXAS)

    assert taxa_sem["taxa_internacao_padronizada"].iloc[0] == pytest.approx(
        taxa_com["taxa_internacao_padronizada"].iloc[0]
    )
    # E o valor e o correto: o peso de <30 (70% do padrao) nao foi
    # redistribuido. Com a renormalizacao antiga daria 7777.78.
    assert taxa_sem["taxa_internacao_padronizada"].iloc[0] == pytest.approx(
        140 / 6000 * 100_000
    )


def test_faixa_ausente_nao_infla_mais_o_municipio_pequeno():
    # Dois municipios com a MESMA taxa especifica por faixa; o pequeno so
    # nao tem caso (nem linha) nas faixas jovens. A taxa padronizada dos
    # dois tem de ser igual — e' para isso que a padronizacao existe.
    grande = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 3,
            "faixa_etaria": ["<30", "60-69", "80+"],
            "internacoes": [0, 5, 10],
            "populacao": [1000, 100, 100],
        }
    )
    pequeno = pd.DataFrame(
        {
            "cod_municipio": ["3500105"] * 2,
            "faixa_etaria": ["60-69", "80+"],
            "internacoes": [5, 10],
            "populacao": [100, 100],
        }
    )
    juntos = pd.concat([grande, pequeno], ignore_index=True)

    resultado = padronizar_por_municipio(juntos, POP_PADRAO_TRES_FAIXAS)

    assert resultado["taxa_internacao_padronizada"].nunique() == 1


def test_grupo_sem_populacao_em_faixa_nenhuma_levanta_erro():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 2,
            "faixa_etaria": ["60-69", "80+"],
            "internacoes": [0, 0],
            "populacao": [0, 0],
        }
    )
    with pytest.raises(ValueError, match="populacao em nenhuma faixa"):
        padronizar_por_municipio(df, POP_PADRAO_TRES_FAIXAS)


def test_faixa_fora_do_padrao_nao_entra_no_calculo():
    # Uma faixa que nao existe em pop_padrao nao tem peso definido; o
    # reindex contra o padrao a deixa de fora, e o resultado e' o mesmo
    # do quadro sem ela.
    com_intrusa = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 3,
            "faixa_etaria": ["60-69", "80+", "90-99"],
            "internacoes": [5, 10, 99],
            "populacao": [100, 100, 100],
        }
    )
    resultado = padronizar_por_municipio(com_intrusa, POP_PADRAO_TRES_FAIXAS)
    assert resultado["taxa_internacao_padronizada"].iloc[0] == pytest.approx(
        140 / 6000 * 100_000
    )
