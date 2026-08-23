"""Padronização direta de taxas por faixa etária."""

import numpy as np
import pandas as pd


def taxa_padronizada(casos, populacao, pop_padrao, por: int = 100_000) -> float:
    """Aplica as taxas específicas por faixa à estrutura etária padrão.

    Responde: qual seria a taxa desta população se ela tivesse a
    composição etária do padrão de referência?
    """
    casos = np.asarray(casos, dtype="float64")
    populacao = np.asarray(populacao, dtype="float64")
    pop_padrao = np.asarray(pop_padrao, dtype="float64")

    if not len(casos) == len(populacao) == len(pop_padrao):
        raise ValueError(
            "casos, populacao e pop_padrao devem ter o mesmo tamanho"
        )
    if (populacao <= 0).any():
        raise ValueError("populacao deve ser positiva em todas as faixas")

    taxas = casos / populacao
    pesos = pop_padrao / pop_padrao.sum()
    return float((taxas * pesos).sum() * por)


def padronizar_por_grupo(
    df: pd.DataFrame,
    coluna_grupo: str | list[str],
    pop_padrao: pd.Series,
    por: int = 100_000,
) -> pd.DataFrame:
    """Calcula a taxa padronizada de internação para cada grupo de `df`.

    `coluna_grupo` aceita o nome de uma única coluna (ex.: "cod_municipio")
    ou uma lista de colunas (ex.: ["regiao", "sexo"]) — nesse caso o
    agrupamento é feito pela combinação das colunas, sem recorrer a uma
    chave composta em string.

    `df` precisa das colunas de agrupamento, mais faixa_etaria, internacoes
    e populacao, com uma linha por grupo e faixa. `pop_padrao` é indexada
    pela faixa etária.
    """
    colunas = [coluna_grupo] if isinstance(coluna_grupo, str) else list(coluna_grupo)
    faixas = list(pop_padrao.index)
    linhas = []

    for chave, grupo in df.groupby(colunas, sort=False):
        chave_tupla = chave if isinstance(chave, tuple) else (chave,)
        indexado = grupo.set_index("faixa_etaria").reindex(faixas)
        populacao = indexado["populacao"].fillna(0.0)
        casos = indexado["internacoes"].fillna(0.0)

        presentes = populacao > 0
        if not presentes.any():
            continue

        linha = dict(zip(colunas, chave_tupla))
        linha["taxa_internacao_padronizada"] = taxa_padronizada(
            casos[presentes],
            populacao[presentes],
            pop_padrao[presentes.values],
            por=por,
        )
        linhas.append(linha)

    return pd.DataFrame(linhas)


def padronizar_por_municipio(
    df: pd.DataFrame, pop_padrao: pd.Series, por: int = 100_000
) -> pd.DataFrame:
    """Calcula a taxa padronizada de internação de cada município.

    `df` precisa das colunas cod_municipio, faixa_etaria, internacoes
    e populacao, com uma linha por município e faixa.
    `pop_padrao` é indexada pela faixa etária.

    Wrapper fino sobre `padronizar_por_grupo` agrupando por cod_municipio.
    """
    return padronizar_por_grupo(df, "cod_municipio", pop_padrao, por=por)
