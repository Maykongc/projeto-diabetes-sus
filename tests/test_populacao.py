import pandas as pd
import pytest

from diabetes_sus.config import DIR_GOLD, ROTULOS_FAIXAS

ARQUIVO = DIR_GOLD / "populacao_municipio_faixa_sexo.parquet"

pytestmark = pytest.mark.skipif(
    not ARQUIVO.exists(),
    reason="rode scripts/baixar_populacao_ibge.py primeiro",
)


@pytest.fixture(scope="module")
def pop():
    return pd.read_parquet(ARQUIVO)


def test_tem_os_5570_municipios(pop):
    assert pop["cod_municipio"].nunique() == 5570


def test_populacao_total_bate_com_o_censo_2022(pop):
    assert pop["populacao"].sum() == pytest.approx(203_080_756, rel=0.005)


def test_codigo_tem_sete_digitos(pop):
    assert pop["cod_municipio"].str.len().eq(7).all()


def test_usa_exatamente_as_faixas_do_projeto(pop):
    # Igualdade, nao inclusao: com `<=` uma faixa inteira ausente passaria
    # despercebida, e a populacao e' o denominador de todas as taxas do
    # projeto — faixa faltando vira taxa padronizada errada.
    assert set(pop["faixa_etaria"]) == set(ROTULOS_FAIXAS)


def test_sexo_tem_apenas_m_e_f(pop):
    assert set(pop["sexo"]) == {"M", "F"}


def test_nenhuma_populacao_negativa(pop):
    assert (pop["populacao"] >= 0).all()


def test_todas_as_cinco_regioes_presentes(pop):
    assert pop["regiao"].nunique() == 5
