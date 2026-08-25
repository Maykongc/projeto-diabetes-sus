"""Padronização direta de taxas por faixa etária."""

import numpy as np
import pandas as pd


def taxa_padronizada(
    casos,
    populacao,
    pop_padrao,
    por: int = 100_000,
    faixa_sem_populacao: str = "erro",
) -> float:
    """Aplica as taxas específicas por faixa à estrutura etária padrão.

    Responde: qual seria a taxa desta população se ela tivesse a
    composição etária do padrão de referência?

    `faixa_sem_populacao` controla o que fazer com uma faixa cujo
    denominador é zero ou ausente:

    - `"erro"` (padrão): levanta `ValueError`. É o contrato original da
      função — quem chama garante o denominador de todas as faixas.
    - `"taxa_zero"`: a faixa entra com **taxa zero e peso preservado**.
      Os pesos continuam somando 1 sobre todas as faixas do padrão, em
      vez de serem renormalizados só sobre as faixas presentes.

    Por que `"taxa_zero"` existe: a camada gold só tem linha para as
    combinações que registraram internação. Uma faixa sem nenhum caso
    simplesmente não aparece — e renormalizar os pesos sobre as faixas
    presentes redistribui o peso da faixa ausente entre as demais, o que
    infla a taxa. Como a faixa `<30` sozinha vale cerca de 42% da
    população padrão e é justamente a que menos interna por diabetes, o
    efeito é grande e, pior, correlacionado com o porte do município
    (município pequeno tem mais faixas vazias, logo mais inflação) —
    exatamente o viés que a padronização existe para eliminar.

    Uma faixa com casos mas sem população é outra coisa: é um órfão de
    join, taxa infinita, e levanta erro nos dois modos.
    """
    casos = np.asarray(casos, dtype="float64")
    populacao = np.asarray(populacao, dtype="float64")
    pop_padrao = np.asarray(pop_padrao, dtype="float64")

    if not len(casos) == len(populacao) == len(pop_padrao):
        raise ValueError(
            "casos, populacao e pop_padrao devem ter o mesmo tamanho"
        )
    if faixa_sem_populacao not in ("erro", "taxa_zero"):
        raise ValueError(
            "faixa_sem_populacao deve ser 'erro' ou 'taxa_zero'"
        )

    sem_populacao = ~(populacao > 0)  # cobre zero, negativo e NaN

    if faixa_sem_populacao == "erro":
        if sem_populacao.any():
            raise ValueError("populacao deve ser positiva em todas as faixas")
    else:
        if sem_populacao.all():
            raise ValueError(
                "nenhuma faixa tem populacao — sem denominador nao existe taxa"
            )
        if (casos[sem_populacao] > 0).any():
            raise ValueError(
                "faixa com casos e sem populacao — orfao de join, taxa "
                "infinita; investigue com validacao.verificar_denominadores"
            )

    taxas = np.zeros_like(casos)
    com_populacao = ~sem_populacao
    taxas[com_populacao] = casos[com_populacao] / populacao[com_populacao]

    # Pesos sobre TODAS as faixas do padrão, inclusive as de taxa zero.
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

    **Faixa ausente no grupo entra com taxa zero e peso preservado.** O
    grupo é reindexado contra todas as faixas de `pop_padrao`; a faixa que
    não aparece vira zero caso e zero população, contribui taxa zero e
    mantém seu peso na soma — os pesos somam 1 sobre as sete faixas,
    sempre. Descartar a faixa ausente (renormalizando os pesos entre as
    presentes) inflaria a taxa de todo grupo com faixa vazia, e o viés
    seria maior quanto menor o município. Ver `taxa_padronizada`.

    Levanta `ValueError` se um grupo não tiver população em faixa
    nenhuma — aí não há denominador possível, e omitir o grupo em
    silêncio esconderia um problema de join.
    """
    colunas = [coluna_grupo] if isinstance(coluna_grupo, str) else list(coluna_grupo)
    faixas = list(pop_padrao.index)
    linhas = []

    for chave, grupo in df.groupby(colunas, sort=False):
        chave_tupla = chave if isinstance(chave, tuple) else (chave,)
        indexado = grupo.set_index("faixa_etaria").reindex(faixas)
        populacao = indexado["populacao"].fillna(0.0)
        casos = indexado["internacoes"].fillna(0.0)

        if not (populacao > 0).any():
            raise ValueError(
                f"grupo {chave_tupla} nao tem populacao em nenhuma faixa "
                "etaria — sem denominador nao existe taxa padronizada"
            )

        linha = dict(zip(colunas, chave_tupla))
        linha["taxa_internacao_padronizada"] = taxa_padronizada(
            casos,
            populacao,
            pop_padrao,
            por=por,
            faixa_sem_populacao="taxa_zero",
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
