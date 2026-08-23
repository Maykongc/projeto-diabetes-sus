import pandas as pd
import pytest

from diabetes_sus.validacao import (
    comparar_com_tabnet,
    verificar_completude,
    verificar_denominadores,
    verificar_sanidade,
)


def test_completude_dentro_da_tolerancia():
    resultado = verificar_completude(1944, 1930)
    assert resultado["aprovado"] is True
    assert resultado["faltando"] == 14


def test_completude_abaixo_da_tolerancia_reprova():
    assert verificar_completude(1944, 1500)["aprovado"] is False


def test_denominadores_encontra_municipio_sem_populacao():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308", "9999999"],
            "internacoes": [10, 5],
            "populacao": [1000.0, None],
        }
    )
    orfaos = verificar_denominadores(df)
    assert orfaos["cod_municipio"].tolist() == ["9999999"]


def test_denominador_zero_tambem_e_orfao():
    df = pd.DataFrame(
        {"cod_municipio": ["1"], "internacoes": [3], "populacao": [0.0]}
    )
    assert len(verificar_denominadores(df)) == 1


def test_sanidade_aceita_quadro_valido():
    df = pd.DataFrame(
        {"taxa_internacao_padronizada": [10.0], "icvd": [0.5], "letalidade": [0.1]}
    )
    verificar_sanidade(df)


def test_sanidade_rejeita_taxa_negativa():
    df = pd.DataFrame({"taxa_internacao_padronizada": [-1.0]})
    with pytest.raises(ValueError, match="negativ"):
        verificar_sanidade(df)


def test_sanidade_rejeita_icvd_fora_do_intervalo():
    df = pd.DataFrame({"icvd": [1.4]})
    with pytest.raises(ValueError, match="icvd"):
        verificar_sanidade(df)


def test_sanidade_rejeita_letalidade_acima_de_um():
    df = pd.DataFrame({"letalidade": [1.5]})
    with pytest.raises(ValueError, match="letalidade"):
        verificar_sanidade(df)


def test_comparacao_com_tabnet_sinaliza_divergencia():
    nosso = pd.DataFrame({"uf": ["SP", "CE"], "ano": [2023, 2023], "internacoes": [1000, 500]})
    tabnet = pd.DataFrame({"uf": ["SP", "CE"], "ano": [2023, 2023], "internacoes": [1005, 900]})
    resultado = comparar_com_tabnet(nosso, tabnet)

    assert resultado.loc[resultado["uf"] == "SP", "aprovado"].item() is True
    assert resultado.loc[resultado["uf"] == "CE", "aprovado"].item() is False


def test_comparacao_com_tabnet_nao_descarta_uf_ano_so_no_nosso():
    # AC existe na nossa camada gold mas nao no recorte do TabNet (ex.:
    # mes ainda nao publicado la). A linha precisa sobreviver reprovada,
    # nunca desaparecer da reconciliacao.
    nosso = pd.DataFrame(
        {"uf": ["SP", "AC"], "ano": [2023, 2023], "internacoes": [1000, 200]}
    )
    tabnet = pd.DataFrame({"uf": ["SP"], "ano": [2023], "internacoes": [1005]})
    resultado = comparar_com_tabnet(nosso, tabnet)

    assert len(resultado) == 2
    linha_ac = resultado.loc[resultado["uf"] == "AC"]
    assert linha_ac["aprovado"].item() is False
    assert pd.isna(linha_ac["internacoes_tabnet"].item())


def test_comparacao_com_tabnet_nao_descarta_uf_ano_so_no_tabnet():
    # CE existe no TabNet mas sumiu da nossa camada gold - sintoma de mes
    # faltante no nosso pipeline. Tambem precisa sobreviver reprovada.
    nosso = pd.DataFrame({"uf": ["SP"], "ano": [2023], "internacoes": [1000]})
    tabnet = pd.DataFrame(
        {"uf": ["SP", "CE"], "ano": [2023, 2023], "internacoes": [1005, 500]}
    )
    resultado = comparar_com_tabnet(nosso, tabnet)

    assert len(resultado) == 2
    linha_ce = resultado.loc[resultado["uf"] == "CE"]
    assert linha_ce["aprovado"].item() is False
    assert pd.isna(linha_ce["internacoes_nosso"].item())
