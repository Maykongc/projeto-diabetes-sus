import pandas as pd

from diabetes_sus.filtros import (
    eh_amputacao_mmii,
    eh_diabetes,
    filtrar_internacoes_diabetes,
    remover_aih_continuacao,
)


def test_reconhece_todos_os_cids_de_diabetes():
    serie = pd.Series(["E100", "E110", "E120", "E130", "E140"])
    assert eh_diabetes(serie).all()


def test_rejeita_cid_vizinho_que_nao_e_diabetes():
    serie = pd.Series(["E150", "E059", "I10", "N180"])
    assert not eh_diabetes(serie).any()


def test_diabetes_ignora_caixa_e_espacos():
    assert eh_diabetes(pd.Series([" e119 "])).iloc[0]


def test_diabetes_trata_nulo_como_falso():
    assert not eh_diabetes(pd.Series([None])).iloc[0]


def test_reconhece_procedimento_de_amputacao():
    assert eh_amputacao_mmii(pd.Series(["0408050020"])).iloc[0]
    assert not eh_amputacao_mmii(pd.Series(["0408010010"])).iloc[0]


def test_amputacao_completa_codigo_com_zeros_a_esquerda():
    assert eh_amputacao_mmii(pd.Series(["408050020"])).iloc[0]


def test_remove_aih_de_continuacao():
    df = pd.DataFrame({"IDENT": [1, 5, 1], "x": ["a", "b", "c"]})
    resultado = remover_aih_continuacao(df)
    assert resultado["x"].tolist() == ["a", "c"]


def test_filtro_completo_mantem_so_diabetes_e_marca_amputacao():
    df = pd.DataFrame(
        {
            "DIAG_PRINC": ["E114", "I10", "E105"],
            "PROC_REA": ["0408050020", "0408050020", "0303040017"],
            "IDENT": [1, 1, 1],
        }
    )
    resultado = filtrar_internacoes_diabetes(df)
    assert len(resultado) == 2
    assert resultado["amputacao"].tolist() == [True, False]


def test_filtro_completo_descarta_continuacao_antes_de_contar():
    df = pd.DataFrame(
        {
            "DIAG_PRINC": ["E114", "E114"],
            "PROC_REA": ["0408050020", "0408050020"],
            "IDENT": [1, 5],
        }
    )
    assert len(filtrar_internacoes_diabetes(df)) == 1
