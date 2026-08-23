"""Checagens que impedem um erro de pipeline de virar um insight."""

import pandas as pd

LIMITES = {
    "taxa_internacao_padronizada": (0.0, None),
    "prop_amputacao": (0.0, 1.0),
    "letalidade": (0.0, 1.0),
    "cobertura_aps": (0.0, 100.0),
    "icvd": (0.0, 1.0),
}


def verificar_completude(
    esperados: int, processados: int, tolerancia: float = 0.02
) -> dict:
    """Compara arquivos esperados e efetivamente processados."""
    faltando = esperados - processados
    return {
        "esperados": esperados,
        "processados": processados,
        "faltando": faltando,
        "proporcao_faltando": faltando / esperados if esperados else 0.0,
        "aprovado": faltando <= esperados * tolerancia,
    }


def verificar_denominadores(df: pd.DataFrame) -> pd.DataFrame:
    """Devolve as linhas que têm internação mas não têm população."""
    populacao = pd.to_numeric(df["populacao"], errors="coerce")
    sem_denominador = populacao.isna() | (populacao <= 0)
    return df.loc[sem_denominador & (df["internacoes"] > 0)].copy()


def verificar_sanidade(df: pd.DataFrame) -> None:
    """Levanta ValueError na primeira métrica fora do intervalo aceitável."""
    for coluna, (minimo, maximo) in LIMITES.items():
        if coluna not in df.columns:
            continue
        valores = pd.to_numeric(df[coluna], errors="coerce").dropna()
        if minimo is not None and (valores < minimo).any():
            raise ValueError(
                f"{coluna} tem valor negativo ou abaixo de {minimo}"
            )
        if maximo is not None and (valores > maximo).any():
            raise ValueError(f"{coluna} tem valor acima de {maximo}")


def comparar_com_tabnet(
    nosso: pd.DataFrame, tabnet: pd.DataFrame, tolerancia: float = 0.02
) -> pd.DataFrame:
    """Reconcilia nossos totais por UF e ano com os do TabNet.

    Usa junção externa (how="outer"): uma combinação UF-ano presente em
    apenas um dos lados é justamente o sintoma que a reconciliação existe
    para detectar - mês faltante na nossa camada gold, ou UF-ano que o
    TabNet não cobre. Uma junção interna faria essa linha desaparecer
    silenciosamente do resultado, mascarando o problema. Aqui ela
    permanece, com o lado ausente em NaN e aprovado=False, e a causa fica
    legível ao olhar internacoes_nosso/internacoes_tabnet.
    """
    juncao = nosso.merge(
        tabnet, on=["uf", "ano"], how="outer", suffixes=("_nosso", "_tabnet")
    )
    juncao["diferenca"] = (
        juncao["internacoes_nosso"] - juncao["internacoes_tabnet"]
    )
    juncao["erro_relativo"] = (
        juncao["diferenca"].abs() / juncao["internacoes_tabnet"]
    )
    # Comparações com NaN (chave sem contrapartida em um dos lados) já
    # resultam em False em pandas, então essas linhas ficam reprovadas
    # sem tratamento especial - mas deixamos explícito para documentar a
    # intenção e blindar contra mudanças futuras no comportamento do pandas.
    juncao["aprovado"] = (juncao["erro_relativo"] <= tolerancia).fillna(False)
    return juncao
