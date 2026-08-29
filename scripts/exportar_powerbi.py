"""Exporta a camada gold no formato que o Power BI brasileiro importa sem ajuste.

Tres problemas separam os CSVs analiticos de `data/gold/` do que o Power BI espera
numa maquina configurada em portugues:

1. **Separador decimal.** O Windows em pt-BR usa virgula para decimal e ponto para
   milhar. Um arquivo com `92.01` e lido como `9.201` — silenciosamente, sem erro.
   Aqui os arquivos saem com separador de campo `;` e decimal `,`, que e a
   convencao brasileira e o padrao que o Power BI assume.

2. **Contagens gravadas como decimal.** `internacoes` vale `0.0` porque veio de um
   preenchimento de nulos. Aqui volta a ser inteiro.

3. **Precisao inutil.** O ICVD tinha 16 casas decimais. Aqui cada medida e
   arredondada para o que faz sentido ler.

Alem disso, monta um modelo estrela: um fato e duas dimensoes, em vez de repetir
UF, regiao e nome do municipio em 467.880 linhas.

A camada `data/gold/` NAO e alterada: ela e a base analitica dos notebooks.
"""

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

DIR_GOLD = RAIZ / "data" / "gold"
DIR_SAIDA = RAIZ / "dashboard" / "dados"

# Convencao brasileira: campo separado por ponto-e-virgula, decimal com virgula.
# utf-8-sig grava o BOM, que faz o Power BI e o Excel detectarem UTF-8 sozinhos.
CSV = {"sep": ";", "decimal": ",", "encoding": "utf-8-sig", "index": False}

CONTAGENS = ["internacoes", "amputacoes", "obitos", "dias_perm_total",
             "idade_soma", "idade_validas"]

BLOCOS = {
    2019: ("2019 (pre-pandemia)", 1),
    2020: ("2020-21 (choque)", 2),
    2021: ("2020-21 (choque)", 2),
    2022: ("2022-24 (pos)", 3),
    2023: ("2022-24 (pos)", 3),
    2024: ("2022-24 (pos)", 3),
}


def gravar(df: pd.DataFrame, nome: str) -> None:
    destino = DIR_SAIDA / nome
    df.to_csv(destino, **CSV)
    tamanho = destino.stat().st_size
    print(f"  {nome:32} {len(df):>8,} linhas  {tamanho / 1024:>8,.0f} KB")


def main() -> None:
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    gold = pd.read_csv(DIR_GOLD / "municipio_ano.csv", dtype={"cod_municipio": str})
    nomes = pd.read_csv(DIR_GOLD / "nomes_municipios.csv",
                        dtype={"cod_municipio": str}).set_index("cod_municipio")["nome"]
    ranking = pd.read_csv(DIR_GOLD / "icvd_municipio.csv",
                          dtype={"cod_municipio": str})
    regiao = pd.read_csv(DIR_GOLD / "icvd_regiao.csv")
    genero = pd.read_csv(DIR_GOLD / "genero_regiao.csv")

    total_original = int(gold["internacoes"].sum())
    print(f"origem: {len(gold):,} linhas, {total_original:,} internacoes\n")
    print("gerando em dashboard/dados/:")

    # ---------------- dimensao municipio ----------------
    # A populacao e a mesma em todos os anos (Censo 2022 aplicado a grade), entao
    # basta somar um ano para nao multiplicar por seis.
    um_ano = gold[gold["ano"] == 2019]
    dim_mun = (um_ano.groupby(["cod_municipio", "uf", "regiao"], as_index=False)
                     ["populacao"].sum()
                     .rename(columns={"populacao": "populacao_2022"}))
    dim_mun["nome"] = dim_mun["cod_municipio"].map(nomes)
    dim_mun["no_ranking"] = dim_mun["cod_municipio"].isin(ranking["cod_municipio"])
    dim_mun["municipio_uf"] = dim_mun["nome"] + " (" + dim_mun["uf"] + ")"
    dim_mun = dim_mun[["cod_municipio", "nome", "municipio_uf", "uf", "regiao",
                       "populacao_2022", "no_ranking"]]
    gravar(dim_mun, "dim_municipio.csv")

    # ---------------- dimensao tempo ----------------
    dim_tempo = pd.DataFrame({"ano": sorted(gold["ano"].unique())})
    dim_tempo["bloco"] = dim_tempo["ano"].map(lambda a: BLOCOS[a][0])
    dim_tempo["ordem_bloco"] = dim_tempo["ano"].map(lambda a: BLOCOS[a][1])
    dim_tempo["periodo_icvd"] = dim_tempo["ano"].map(
        lambda a: "2019" if a == 2019 else ("2023-24" if a >= 2023 else ""))
    gravar(dim_tempo, "dim_tempo.csv")

    # ---------------- fato ----------------
    # uf e regiao saem: vivem na dimensao. populacao fica, porque varia por sexo
    # e faixa etaria e e o denominador das taxas.
    fato = gold.drop(columns=["uf", "regiao"]).copy()
    fato[CONTAGENS] = fato[CONTAGENS].round(0).astype("int64")
    fato["val_total"] = fato["val_total"].round(2)
    fato["cobertura_aps"] = fato["cobertura_aps"].round(2)
    gravar(fato, "fato_municipio_ano.csv")

    # ---------------- ranking municipal ----------------
    rank = ranking.copy()
    rank["nome"] = rank["cod_municipio"].map(nomes)
    rank["municipio_uf"] = rank["nome"] + " (" + rank["uf"] + ")"
    for coluna in rank.columns:
        if coluna.startswith(("icvd_", "recuperacao")):
            rank[coluna] = rank[coluna].round(4)
        elif coluna.startswith(("prop_amputacao", "letalidade")):
            rank[coluna] = (100 * rank[coluna]).round(2)   # vira percentual legivel
        elif coluna.startswith(("taxa_", "cobertura_")):
            rank[coluna] = rank[coluna].round(2)
    rank["quadrante"] = rank["recuperacao"].map(
        lambda d: "Piorou" if d > 0 else ("Melhorou" if d < 0 else "Estavel"))
    ordem = (["cod_municipio", "nome", "municipio_uf", "uf", "regiao"]
             + [c for c in rank.columns
                if c not in ("cod_municipio", "nome", "municipio_uf", "uf",
                             "regiao", "no_ranking")])
    gravar(rank[ordem], "ranking_municipal.csv")

    # ---------------- resumo regional ----------------
    reg = regiao.copy()
    for coluna in ("prop_amputacao", "letalidade"):
        reg[coluna] = (100 * reg[coluna]).round(2)
    for coluna in ("icvd_regional", "taxa_internacao_padronizada_norm",
                   "prop_amputacao_norm", "letalidade_norm"):
        if coluna in reg:
            reg[coluna] = reg[coluna].round(4)
    reg["taxa_internacao_padronizada"] = reg["taxa_internacao_padronizada"].round(2)
    reg["cobertura_aps"] = reg["cobertura_aps"].round(2)
    for coluna in ("internacoes", "amputacoes", "obitos"):
        reg[coluna] = reg[coluna].round(0).astype("int64")
    gravar(reg, "resumo_regiao.csv")

    # ---------------- genero ----------------
    gen = genero.copy()
    gen["idade_media"] = (gen["idade_soma"] / gen["idade_validas"]).round(1)
    for coluna in ("taxa_internacao_padronizada", "pct_amputacao", "letalidade"):
        gen[coluna] = gen[coluna].round(2)
    for coluna in ("internacoes", "amputacoes", "obitos"):
        gen[coluna] = gen[coluna].round(0).astype("int64")
    gen = gen.drop(columns=["idade_soma", "idade_validas"])
    gravar(gen, "genero_regiao.csv")

    # ---------------- validacao ----------------
    print("\nvalidacao:")
    conferido = pd.read_csv(DIR_SAIDA / "fato_municipio_ano.csv",
                            sep=";", decimal=",", encoding="utf-8-sig",
                            dtype={"cod_municipio": str})
    total_exportado = int(conferido["internacoes"].sum())
    print(f"  internacoes na origem   : {total_original:,}")
    print(f"  internacoes no exportado: {total_exportado:,}")
    if total_exportado != total_original:
        raise SystemExit("DIVERGENCIA: o total exportado nao bate com a origem")
    print("  totais conferem")

    print(f"  municipios na dimensao  : {dim_mun['cod_municipio'].nunique():,}")
    sem_nome = int(dim_mun["nome"].isna().sum())
    print(f"  municipios sem nome     : {sem_nome}")
    if sem_nome:
        raise SystemExit("DIVERGENCIA: ha municipio sem nome na dimensao")
    print(f"  no ranking              : {int(dim_mun['no_ranking'].sum()):,}")

    amostra = (DIR_SAIDA / "resumo_regiao.csv").read_text(encoding="utf-8-sig")
    print("\n  amostra do formato brasileiro (resumo_regiao.csv):")
    for linha in amostra.splitlines()[:3]:
        print("   ", linha[:110])


if __name__ == "__main__":
    main()
