import numpy as np
import pandas as pd
import pytest

from diabetes_sus.config import (
    COMPONENTES_ICVD,
    COMPONENTES_INVERTIDOS,
    PERIODO_ATUAL,
    PERIODO_BASE,
)
from diabetes_sus.indice import (
    aplicar_corte,
    aplicar_corte_ranking,
    aplicar_escala,
    calcular_icvd,
    calcular_recuperacao,
    normalizar_minmax,
    parametros_escala,
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


def test_nenhum_componente_do_indice_entra_invertido():
    # Os tres componentes atuais apontam todos na mesma direcao: maior valor
    # bruto significa pior cuidado, logo maior componente normalizado.
    assert COMPONENTES_INVERTIDOS == ()
    resultado = calcular_icvd(quadro())
    for componente in COMPONENTES_ICVD:
        ordenado = resultado.sort_values(componente)
        assert (
            ordenado[f"{componente}_norm"].iloc[0]
            < ordenado[f"{componente}_norm"].iloc[-1]
        )


def test_mecanismo_de_inversao_continua_funcionando_quando_declarado(monkeypatch):
    # A inversao nao e usada hoje, mas segue no codigo para o caso de entrar um
    # componente cuja direcao seja invertida. Sem este teste ela viraria codigo
    # morto e nao verificado.
    monkeypatch.setattr(
        "diabetes_sus.indice.COMPONENTES_INVERTIDOS", ("letalidade",)
    )
    resultado = calcular_icvd(quadro()).sort_values("letalidade")
    assert resultado["letalidade_norm"].iloc[-1] < (
        resultado["letalidade_norm"].iloc[0]
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
    # Os componentes precisam ser NAO colineares. Tres linspaces
    # monotonicos viram vetores identicos depois de normalizados, e a media
    # ponderada de vetores identicos ignora os pesos — o teste passaria a
    # ser impossivel de falhar por motivo errado.
    df = quadro(prop_amputacao=[0.06, 0.01, 0.05, 0.02, 0.04, 0.03])
    igual = calcular_icvd(df)["icvd"]
    pesado = calcular_icvd(
        df,
        pesos={
            "taxa_internacao_padronizada": 0.15,
            "prop_amputacao": 0.7,
            "letalidade": 0.15,
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
            },
        )


def test_calcular_icvd_equivale_a_aplicar_a_propria_regua():
    # calcular_icvd(df) precisa ser exatamente aplicar_escala(df,
    # parametros_escala(df)) — é essa equivalência que garante que o
    # refactor não mudou o resultado para o caso municipal.
    df = quadro()
    esperado = calcular_icvd(df)
    obtido = aplicar_escala(df, parametros_escala(df))
    pd.testing.assert_frame_equal(obtido, esperado)


def test_parametros_escala_denuncia_componente_constante():
    df = quadro()
    df["letalidade"] = 0.05
    with pytest.raises(ValueError, match="constante"):
        parametros_escala(df)


def test_aplicar_escala_usa_a_regua_de_outro_quadro_sem_normalizar_contra_si():
    # A régua vem de um quadro "municipal" com 10 pontos. Um quadro
    # "regional" com um único valor exatamente no minimo/maximo observado
    # no municipal (apos winsorizacao) precisa colapsar para icvd == 0 —
    # o oposto do que aconteceria se o regional fosse normalizado contra
    # si mesmo (onde um único valor não pode nem ser normalizado).
    municipal = quadro(n=10)
    parametros = parametros_escala(municipal)

    regional = pd.DataFrame(
        {
            "taxa_internacao_padronizada": [
                municipal["taxa_internacao_padronizada"].min()
            ],
            "prop_amputacao": [municipal["prop_amputacao"].min()],
            "letalidade": [municipal["letalidade"].min()],
        }
    )

    resultado = aplicar_escala(regional, parametros)
    assert resultado["icvd"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_aplicar_escala_recorta_valor_regional_fora_da_faixa_municipal():
    # Um agregado regional pode, em tese, cair fora do intervalo
    # observado no municipal (ex.: media regional acima do maior
    # municipio). O clip aos limites de winsorizacao garante que o icvd
    # continua em [0, 1] mesmo nesse caso.
    municipal = quadro(n=10)
    parametros = parametros_escala(municipal)

    extremo = municipal.iloc[[0]].copy()
    extremo["taxa_internacao_padronizada"] = (
        municipal["taxa_internacao_padronizada"].max() * 10
    )

    resultado = aplicar_escala(extremo, parametros)
    assert resultado["icvd"].between(0, 1).all()


# --- Corte de elegibilidade do ranking (correcao I2 da revisao final) --------
#
# O corte de 20 e' sobre o TOTAL 2019-2024, nao por periodo: 2019 e' um ano e
# 2023-24 sao dois, entao exigir 20 dentro de cada periodo derrubaria o ranking
# para uma fracao dos municipios e tornaria falsa a calibracao de 3.5.


def empilhado_de(por_municipio: dict) -> pd.DataFrame:
    """{cod: (internacoes_2019, internacoes_2023_24)} -> quadro empilhado."""
    linhas = []
    for cod, (base, atual) in por_municipio.items():
        if base is not None:
            linhas.append(
                {"cod_municipio": cod, "periodo": PERIODO_BASE, "internacoes": base}
            )
        if atual is not None:
            linhas.append(
                {"cod_municipio": cod, "periodo": PERIODO_ATUAL, "internacoes": atual}
            )
    return pd.DataFrame(linhas)


def test_corte_do_ranking_usa_o_total_dos_seis_anos():
    # 12 + 10 = 22 nos dois periodos observados, mas o total 2019-2024 e' 40
    # (os anos de 2020-22 tambem contam). Passa nos dois criterios.
    empilhado = empilhado_de({"3550308": (12, 10)})
    totais = pd.Series({"3550308": 40})

    resultado = aplicar_corte_ranking(empilhado, totais)

    assert resultado["passou_corte_total"].all()
    assert resultado["no_ranking"].all()


def test_municipio_abaixo_de_vinte_no_total_fica_fora():
    empilhado = empilhado_de({"3550308": (8, 9)})
    totais = pd.Series({"3550308": 19})

    resultado = aplicar_corte_ranking(empilhado, totais)

    assert not resultado["passou_corte_total"].any()
    assert not resultado["no_ranking"].any()


def test_denominador_degenerado_em_um_periodo_reprova_no_criterio_secundario():
    # 60 internacoes no total, mas so 2 em 2023-24: letalidade e
    # prop_amputacao do periodo atual seriam razoes de dois casos.
    empilhado = empilhado_de({"3550308": (40, 2)})
    totais = pd.Series({"3550308": 60})

    resultado = aplicar_corte_ranking(empilhado, totais)

    assert resultado["passou_corte_total"].all()
    assert not resultado["passou_corte_periodo"].any()
    assert not resultado["no_ranking"].any()


def test_municipio_ausente_de_um_periodo_nao_entra_no_ranking():
    empilhado = empilhado_de({"3550308": (40, None), "2304400": (30, 30)})
    totais = pd.Series({"3550308": 90, "2304400": 80})

    resultado = aplicar_corte_ranking(empilhado, totais)

    so_um = resultado[resultado["cod_municipio"] == "3550308"]
    dois = resultado[resultado["cod_municipio"] == "2304400"]
    assert not so_um["no_ranking"].any()
    assert dois["no_ranking"].all()


def test_corte_do_ranking_exige_total_de_todos_os_municipios():
    empilhado = empilhado_de({"3550308": (40, 40)})
    with pytest.raises(ValueError, match="sem total"):
        aplicar_corte_ranking(empilhado, pd.Series({"2304400": 90}))


def test_corte_do_ranking_exige_os_dois_periodos_no_quadro():
    empilhado = empilhado_de({"3550308": (40, None)})
    with pytest.raises(ValueError, match="periodos ausentes"):
        aplicar_corte_ranking(empilhado, pd.Series({"3550308": 90}))
