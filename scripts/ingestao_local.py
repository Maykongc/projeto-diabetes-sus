"""Ingestao local do SIH/SUS: baixa, decodifica, filtra e grava a camada bronze.

Substitui a etapa que antes so rodava no Google Colab. A restricao original era o
formato `.dbc` do DATASUS, que `datasus-dbc` nao consegue compilar no Windows com
Python 3.13 — mas `pyreaddbc` resolve o mesmo problema com wheel disponivel.

Transporte: `ftp://`. O host `ftp.datasus.gov.br` nao tem servidor web (portas 80 e
443 recusam conexao), apenas a 21 responde.

O script e idempotente: cada arquivo ja processado e pulado, entao pode ser
reexecutado a vontade apos qualquer interrupcao.
"""

import argparse
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ftplib import FTP, all_errors
from pathlib import Path

import pandas as pd
import pyreaddbc

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from diabetes_sus.dbf import ler_dbf  # noqa: E402
from diabetes_sus.filtros import filtrar_internacoes_diabetes  # noqa: E402
from diabetes_sus.idade import faixa_etaria, idade_em_anos  # noqa: E402

HOST = "ftp.datasus.gov.br"
DIR_FTP = "/dissemin/publicos/SIHSUS/200801_/Dados"
ANOS = range(2019, 2025)

DIR_BRONZE = RAIZ / "data" / "bronze"
DIR_LOGS = RAIZ / "data" / "logs"
TMP = tempfile.gettempdir()

MAX_PENDENTES = 60
ERROS_REDE = all_errors + (socket.error, EOFError, OSError)

COLUNAS = ["MUNIC_RES", "SEXO", "IDADE", "COD_IDADE", "DIAG_PRINC",
           "PROC_REA", "IDENT", "MORTE", "VAL_TOT", "DIAS_PERM"]

SAIDA = ["cod_municipio_6", "sexo", "idade_anos", "faixa_etaria", "ano", "mes",
         "amputacao", "morte", "val_tot", "dias_perm"]

# Formato do servidor (estilo IIS): '03-10-20  02:42PM   237472 RDAC1901.dbc'
PADRAO = re.compile(r"\s(\d+)\s+RD(\w{2})(\d{2})(\d{2})\.dbc\s*$", re.IGNORECASE)

trava = threading.Lock()
estado = {"baixados": 0, "pulados": 0, "bytes": 0, "linhas": 0,
          "faixa_indefinida": 0}
pendentes = []
abortar = threading.Event()
inicio = time.time()


def conectar():
    con = FTP(HOST, timeout=300)
    con.login()
    con.cwd(DIR_FTP)
    return con


def catalogar():
    """Lista o diretorio do servidor e devolve {(uf, ano, mes): tamanho}."""
    con = conectar()
    linhas = []
    con.retrlines("LIST RD*.dbc", linhas.append)
    con.quit()

    catalogo = {}
    for linha in linhas:
        achado = PADRAO.search(linha)
        if not achado:
            continue
        ano = 2000 + int(achado.group(3))
        mes = int(achado.group(4))
        if ano in ANOS and 1 <= mes <= 12:
            catalogo[(achado.group(2).upper(), ano, mes)] = int(achado.group(1))
    return catalogo


def gravar_pendentes():
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    (DIR_LOGS / "pendentes.json").write_text(
        json.dumps(pendentes, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def registrar_falha(uf, ano, mes, categoria, erro):
    with trava:
        pendentes.append({"uf": uf, "ano": ano, "mes": mes,
                          "categoria": categoria, "erro": str(erro)})
        print(f"FALHOU {uf} {ano}-{mes:02d} [{categoria}]: {erro}", flush=True)
        if len(pendentes) >= MAX_PENDENTES and not abortar.is_set():
            abortar.set()
            print(f"ABORTANDO: {len(pendentes)} falhas acumuladas.", flush=True)


def processar(con, uf, ano, mes, wid):
    pasta = DIR_BRONZE / f"uf={uf}" / f"ano={ano}"
    nome = f"RD{uf}{ano % 100:02d}{mes:02d}"
    destino = pasta / f"{nome}.parquet"
    if destino.exists():
        return "pulado", 0, 0, 0

    pasta.mkdir(parents=True, exist_ok=True)
    dbc = os.path.join(TMP, f"ing_w{wid}.dbc")
    dbf = os.path.join(TMP, f"ing_w{wid}.dbf")

    with open(dbc, "wb") as arquivo:
        con.retrbinary("RETR " + nome + ".dbc", arquivo.write)
    tamanho = os.path.getsize(dbc)

    pyreaddbc.dbc2dbf(dbc, dbf)
    # Leitor vetorizado: 25x mais rapido que dbfread, com resultado identico
    # (tests/test_dbf.py). Le so as 10 colunas usadas, das 113 do arquivo.
    df = ler_dbf(dbf, colunas=COLUNAS)
    df = filtrar_internacoes_diabetes(df)
    df["idade_anos"] = idade_em_anos(df["IDADE"], df["COD_IDADE"])
    # astype('string') preserva idade desconhecida como nulo real; astype(str)
    # transformaria o ausente na string 'nan', que nunca casaria no join com a
    # tabela de populacao.
    df["faixa_etaria"] = faixa_etaria(df["idade_anos"]).astype("string")
    indefinidas = int(df["faixa_etaria"].isna().sum())
    df = df.rename(columns={"MUNIC_RES": "cod_municipio_6", "SEXO": "sexo",
                            "MORTE": "morte", "VAL_TOT": "val_tot",
                            "DIAS_PERM": "dias_perm"})
    df["ano"], df["mes"] = ano, mes

    # Escrita atomica: provisorio renomeado no fim, para que uma interrupcao
    # durante a gravacao nao deixe um parquet truncado que o checkpoint
    # trataria como pronto.
    provisorio = destino.with_suffix(".parcial")
    df[SAIDA].to_parquet(provisorio, index=False)
    os.replace(provisorio, destino)

    os.remove(dbc)
    os.remove(dbf)
    return "baixado", tamanho, len(df), indefinidas


def relatar(total, alvos):
    decorrido = time.time() - inicio
    mb = estado["bytes"] / 1024 ** 2
    taxa = mb / max(decorrido, 1)
    eta = ((len(alvos) - total) / max(total, 1)) * decorrido / 60
    print(f"[{total}/{len(alvos)}] {mb:.0f} MB | {taxa:.2f} MB/s | "
          f"{estado['linhas']:,} internacoes de diabetes | "
          f"{decorrido / 60:.1f} min | ~{eta:.0f} min restantes", flush=True)


def worker(wid, fatia, alvos):
    con = conectar()
    for uf, ano, mes in fatia:
        if abortar.is_set():
            break
        for tentativa in range(3):
            try:
                status, tamanho, linhas, indefinidas = processar(
                    con, uf, ano, mes, wid)
                with trava:
                    if status == "pulado":
                        estado["pulados"] += 1
                    else:
                        estado["baixados"] += 1
                        estado["bytes"] += tamanho
                        estado["linhas"] += linhas
                        estado["faixa_indefinida"] += indefinidas
                    total = estado["baixados"] + estado["pulados"]
                    if total % 50 == 0:
                        relatar(total, alvos)
                        gravar_pendentes()
                break
            except ERROS_REDE as erro:
                # So erro de rede justifica reabrir a conexao. Reconectar em erro
                # de processamento gera tempestade de reconexoes.
                if tentativa == 2:
                    registrar_falha(uf, ano, mes, "rede", erro)
                else:
                    try:
                        con.quit()
                    except Exception:
                        pass
                    time.sleep(3 * (tentativa + 1))
                    try:
                        con = conectar()
                    except Exception:
                        pass
            except Exception as erro:
                if tentativa == 2:
                    registrar_falha(uf, ano, mes, "processamento", erro)
                else:
                    time.sleep(1)
    try:
        con.quit()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--ufs", default="", help="lista separada por virgula; vazio = todas")
    args = ap.parse_args()

    print("listando o servidor...", flush=True)
    catalogo = catalogar()
    alvos = sorted(catalogo)
    if args.ufs:
        aceitas = {u.strip().upper() for u in args.ufs.split(",")}
        alvos = [a for a in alvos if a[0] in aceitas]

    volume = sum(catalogo[a] for a in alvos)
    print(f"{len(alvos)} arquivos | {volume / 1024 ** 3:.2f} GB | "
          f"{args.workers} conexoes paralelas", flush=True)

    DIR_BRONZE.mkdir(parents=True, exist_ok=True)
    fatias = [alvos[i::args.workers] for i in range(args.workers)]
    with ThreadPoolExecutor(args.workers) as executor:
        list(executor.map(lambda par: worker(par[0], par[1], alvos),
                          list(enumerate(fatias))))

    gravar_pendentes()
    decorrido = (time.time() - inicio) / 60
    print(f"\nCONCLUIDO em {decorrido:.1f} min")
    print(f"  baixados agora        : {estado['baixados']}")
    print(f"  ja existiam (pulados) : {estado['pulados']}")
    print(f"  pendentes (3 falhas)  : {len(pendentes)}")
    print(f"  internacoes diabetes  : {estado['linhas']:,}")
    print(f"  faixa etaria indefinida: {estado['faixa_indefinida']:,}")
    if abortar.is_set():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
