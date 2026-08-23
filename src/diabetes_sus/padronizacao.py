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


def padronizar_por_municipio(
    df: pd.DataFrame, pop_padrao: pd.Series, por: int = 100_000
) -> pd.DataFrame:
    """Calcula a taxa padronizada de internação de cada município.

    `df` precisa das colunas cod_municipio, faixa_etaria, internacoes
    e populacao, com uma linha por município e faixa.
    `pop_padrao` é indexada pela faixa etária.
    """
    faixas = list(pop_padrao.index)
    linhas = []

    for cod, grupo in df.groupby("cod_municipio", sort=False):
        indexado = grupo.set_index("faixa_etaria").reindex(faixas)
        populacao = indexado["populacao"].fillna(0.0)
        casos = indexado["internacoes"].fillna(0.0)

        presentes = populacao > 0
        if not presentes.any():
            continue

        linhas.append(
            {
                "cod_municipio": cod,
                "taxa_internacao_padronizada": taxa_padronizada(
                    casos[presentes],
                    populacao[presentes],
                    pop_padrao[presentes.values],
                    por=por,
                ),
            }
        )

    return pd.DataFrame(linhas)
