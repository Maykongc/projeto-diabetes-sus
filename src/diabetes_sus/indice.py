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


def calcular_icvd(
    df: pd.DataFrame, pesos: dict | None = None
) -> pd.DataFrame:
    """Calcula o ICVD sobre um quadro que empilha os dois períodos.

    A normalização usa mínimos e máximos do conjunto inteiro, garantindo
    que os ICVDs de 2019 e 2023-24 estejam na mesma escala e portanto
    sejam comparáveis entre si.
    """
    pesos = dict(PESOS_IGUAIS) if pesos is None else dict(pesos)
    if abs(sum(pesos.values()) - 1.0) > 1e-9:
        raise ValueError("os pesos precisam somar 1")

    saida = df.copy()
    saida["icvd"] = 0.0

    for componente in COMPONENTES_ICVD:
        normalizado = normalizar_minmax(winsorizar(saida[componente]))
        if componente in COMPONENTES_INVERTIDOS:
            normalizado = 1.0 - normalizado
        saida[f"{componente}_norm"] = normalizado
        saida["icvd"] += normalizado * pesos[componente]

    return saida


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
