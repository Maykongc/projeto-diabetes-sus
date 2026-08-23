"""Índice Composto de Vulnerabilidade no Cuidado ao Diabetes (ICVD)."""

import pandas as pd

from diabetes_sus.config import (
    COMPONENTES_ICVD,
    COMPONENTES_INVERTIDOS,
    CORTE_MIN_INTERNACOES,
    PERIODO_ATUAL,
    PERIODO_BASE,
    PESOS_IGUAIS,
)


def winsorizar(
    s: pd.Series, inferior: float = 0.01, superior: float = 0.99
) -> pd.Series:
    """Comprime a série aos percentis indicados, contendo outliers."""
    return s.clip(s.quantile(inferior), s.quantile(superior))


def normalizar_minmax(s: pd.Series) -> pd.Series:
    """Mapeia a série para o intervalo [0, 1]."""
    minimo, maximo = s.min(), s.max()
    if minimo == maximo:
        raise ValueError("serie constante nao pode ser normalizada por min-max")
    return (s - minimo) / (maximo - minimo)


def aplicar_corte(
    df: pd.DataFrame, corte: int = CORTE_MIN_INTERNACOES
) -> pd.DataFrame:
    """Marca quais municípios têm eventos suficientes para entrar no ranking.

    O corte vale apenas para o ranking municipal. Análises regionais
    devem usar todos os municípios.
    """
    saida = df.copy()
    saida["no_ranking"] = saida["internacoes"] >= corte
    return saida


def parametros_escala(df: pd.DataFrame) -> dict:
    """Calcula, para cada componente do ICVD, os limites de winsorização e
    o mínimo/máximo pós-winsorização observados em `df`.

    Devolve a "régua" de normalização usada por `calcular_icvd`, para que
    ela possa ser reaplicada a um outro quadro (por exemplo, agregados
    regionais) em vez de normalizar esse outro quadro contra si mesmo.

    Reaproveita `normalizar_minmax` apenas para herdar sua validação de
    série constante — um componente sem variação no quadro municipal não
    pode virar régua de normalização para mais nada.
    """
    parametros = {}
    for componente in COMPONENTES_ICVD:
        bruto = df[componente]
        wins_inferior = bruto.quantile(0.01)
        wins_superior = bruto.quantile(0.99)
        comprimido = winsorizar(bruto)
        normalizar_minmax(comprimido)  # valida: nao pode ser constante
        parametros[componente] = {
            "wins_inferior": wins_inferior,
            "wins_superior": wins_superior,
            "minimo": comprimido.min(),
            "maximo": comprimido.max(),
        }
    return parametros


def aplicar_escala(
    df: pd.DataFrame, parametros: dict, pesos: dict | None = None
) -> pd.DataFrame:
    """Aplica a régua de `parametros_escala` a `df` e calcula o ICVD.

    Winsoriza cada componente de `df` aos limites de `parametros` e depois
    normaliza pelo mínimo/máximo também de `parametros` — nunca pelos
    mínimo/máximo do próprio `df`. É assim que um quadro diferente do que
    gerou a régua (ex.: agregados regionais) fica na mesma escala do
    quadro municipal, em vez de ser normalizado contra si mesmo.
    """
    pesos = dict(PESOS_IGUAIS) if pesos is None else dict(pesos)
    if abs(sum(pesos.values()) - 1.0) > 1e-9:
        raise ValueError("os pesos precisam somar 1")

    saida = df.copy()
    saida["icvd"] = 0.0

    for componente in COMPONENTES_ICVD:
        p = parametros[componente]
        comprimido = saida[componente].clip(p["wins_inferior"], p["wins_superior"])
        normalizado = (comprimido - p["minimo"]) / (p["maximo"] - p["minimo"])
        if componente in COMPONENTES_INVERTIDOS:
            normalizado = 1.0 - normalizado
        saida[f"{componente}_norm"] = normalizado
        saida["icvd"] += normalizado * pesos[componente]

    return saida


def calcular_icvd(
    df: pd.DataFrame, pesos: dict | None = None
) -> pd.DataFrame:
    """Calcula o ICVD sobre um quadro que empilha os dois períodos.

    A normalização usa mínimos e máximos do conjunto inteiro (`df` gera a
    própria régua via `parametros_escala`), garantindo que os ICVDs de
    2019 e 2023-24 estejam na mesma escala e portanto sejam comparáveis
    entre si.
    """
    return aplicar_escala(df, parametros_escala(df), pesos)


def calcular_recuperacao(df_icvd: pd.DataFrame) -> pd.DataFrame:
    """Mede a variação do ICVD entre a linha de base e o período atual.

    Valores positivos indicam piora; negativos, recuperação.
    """
    tabela = df_icvd.pivot_table(
        index="cod_municipio", columns="periodo", values="icvd", aggfunc="first"
    )
    faltando = {PERIODO_BASE, PERIODO_ATUAL} - set(tabela.columns)
    if faltando:
        raise ValueError(f"periodos ausentes no quadro: {sorted(faltando)}")

    resultado = pd.DataFrame(
        {
            "cod_municipio": tabela.index,
            "icvd_2019": tabela[PERIODO_BASE].to_numpy(),
            "icvd_2023_24": tabela[PERIODO_ATUAL].to_numpy(),
        }
    )
    resultado["recuperacao"] = (
        resultado["icvd_2023_24"] - resultado["icvd_2019"]
    )
    return resultado
