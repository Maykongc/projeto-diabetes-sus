"""Leitura vetorizada de arquivos DBF.

O `dbfread` percorre o arquivo registro a registro em Python puro, montando um
dicionario por linha. Num arquivo do SIH com 111 mil internacoes isso custa cerca
de 14 segundos — dez vezes mais que baixar o arquivo. Como o DBF e um formato de
largura fixa, da para fatiar os bytes com numpy e ler so as colunas necessarias.

Medido contra `dbfread` no mesmo arquivo: 14,4 s contra 0,6 s, com resultado
identico coluna a coluna (ver `tests/test_dbf.py`).
"""

import struct
from pathlib import Path

import numpy as np
import pandas as pd

REGISTRO_EXCLUIDO = 0x2A   # '*' no primeiro byte marca registro apagado
FIM_DOS_CAMPOS = 0x0D
TIPOS_NUMERICOS = ("N", "F")


def _descritores(fh):
    """Le o cabecalho e devolve (n_registros, tam_cabecalho, tam_registro, campos)."""
    cabecalho = fh.read(32)
    if len(cabecalho) < 32:
        raise ValueError("arquivo DBF truncado: cabecalho incompleto")

    n_registros = struct.unpack("<I", cabecalho[4:8])[0]
    tam_cabecalho = struct.unpack("<H", cabecalho[8:10])[0]
    tam_registro = struct.unpack("<H", cabecalho[10:12])[0]

    campos, deslocamento = [], 1   # o byte 0 de cada registro e a flag de exclusao
    while True:
        bruto = fh.read(32)
        if not bruto or bruto[0] == FIM_DOS_CAMPOS:
            break
        nome = bruto[:11].split(b"\x00")[0].decode("ascii")
        tipo = chr(bruto[11])
        tamanho = bruto[16]
        campos.append((nome, tipo, deslocamento, tamanho))
        deslocamento += tamanho

    return n_registros, tam_cabecalho, tam_registro, campos


def ler_dbf(caminho, colunas=None) -> pd.DataFrame:
    """Le um DBF para DataFrame, opcionalmente so as colunas pedidas.

    Campos declarados como numericos no cabecalho (tipos N e F) sao convertidos
    com `pd.to_numeric`; os demais ficam como texto ja sem espacos nas bordas.
    Registros marcados como excluidos sao descartados, como faz o dbfread.
    """
    caminho = Path(caminho)
    with open(caminho, "rb") as fh:
        n_registros, tam_cabecalho, tam_registro, campos = _descritores(fh)
        fh.seek(tam_cabecalho)
        bruto = np.frombuffer(fh.read(n_registros * tam_registro), dtype=np.uint8)

    # Alguns arquivos do DATASUS declaram mais registros do que realmente tem.
    if len(bruto) < n_registros * tam_registro:
        n_registros = len(bruto) // tam_registro
        bruto = bruto[: n_registros * tam_registro]

    if n_registros == 0:
        nomes = [c[0] for c in campos if colunas is None or c[0] in colunas]
        return pd.DataFrame({nome: pd.Series(dtype="object") for nome in nomes})

    matriz = bruto.reshape(n_registros, tam_registro)
    vivos = matriz[:, 0] != REGISTRO_EXCLUIDO

    saida = {}
    for nome, tipo, inicio, tamanho in campos:
        if colunas is not None and nome not in colunas:
            continue
        fatia = matriz[vivos, inicio : inicio + tamanho]
        texto = pd.Series(
            np.frombuffer(fatia.tobytes(), dtype=f"S{tamanho}").astype(str)
        ).str.strip()
        saida[nome] = (
            pd.to_numeric(texto, errors="coerce") if tipo in TIPOS_NUMERICOS else texto
        )

    return pd.DataFrame(saida)
