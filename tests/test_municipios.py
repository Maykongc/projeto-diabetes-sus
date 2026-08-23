import pandas as pd

from diabetes_sus.municipios import (
    completar_codigo,
    mapa_6_para_7,
    regiao_da_uf,
    uf_do_codigo,
)


def test_mapa_usa_os_seis_primeiros_digitos():
    assert mapa_6_para_7(["3550308", "2304400"]) == {
        "355030": "3550308",
        "230440": "2304400",
    }


def test_completar_codigo_expande_para_sete_digitos():
    mapa = mapa_6_para_7(["3550308", "2304400"])
    resultado = completar_codigo(pd.Series(["355030", "230440"]), mapa)
    assert resultado.tolist() == ["3550308", "2304400"]


def test_codigo_desconhecido_vira_nulo():
    mapa = mapa_6_para_7(["3550308"])
    resultado = completar_codigo(pd.Series(["999999"]), mapa)
    assert pd.isna(resultado.iloc[0])


def test_uf_vem_dos_dois_primeiros_digitos():
    resultado = uf_do_codigo(pd.Series(["3550308", "2304400", "1200401"]))
    assert resultado.tolist() == ["SP", "CE", "AC"]


def test_uf_aceita_codigo_de_seis_digitos():
    assert uf_do_codigo(pd.Series(["355030"])).tolist() == ["SP"]


def test_regiao_da_uf():
    resultado = regiao_da_uf(pd.Series(["SP", "CE", "AC", "RS", "GO"]))
    assert resultado.tolist() == [
        "Sudeste", "Nordeste", "Norte", "Sul", "Centro-Oeste",
    ]


def test_todas_as_ufs_tem_regiao():
    from diabetes_sus.config import UFS

    resultado = regiao_da_uf(pd.Series(list(UFS)))
    assert resultado.notna().all()
