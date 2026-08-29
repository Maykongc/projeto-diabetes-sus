"""Compara o leitor vetorizado com o dbfread sobre um DBF construido a mao.

O teste nao depende de rede: monta um DBF minimo em bytes, com um registro
excluido e campos de tipo texto e numerico, e exige que os dois leitores
produzam exatamente o mesmo resultado.
"""

import struct

import pandas as pd
import pytest

from diabetes_sus.dbf import ler_dbf

dbfread = pytest.importorskip("dbfread")


def _campo(nome, tipo, tamanho):
    bruto = bytearray(32)
    bruto[0 : len(nome)] = nome.encode("ascii")
    bruto[11] = ord(tipo)
    bruto[16] = tamanho
    return bytes(bruto)


def _montar_dbf(caminho, campos, registros):
    """campos: [(nome, tipo, tamanho)]; registros: [(flag, [valores formatados])]."""
    tam_registro = 1 + sum(t for _, _, t in campos)
    tam_cabecalho = 32 + 32 * len(campos) + 1

    cabecalho = bytearray(32)
    cabecalho[0] = 0x03
    cabecalho[1:4] = bytes([125, 1, 1])
    cabecalho[4:8] = struct.pack("<I", len(registros))
    cabecalho[8:10] = struct.pack("<H", tam_cabecalho)
    cabecalho[10:12] = struct.pack("<H", tam_registro)

    corpo = b"".join(
        flag + b"".join(v.encode("latin-1").ljust(t) for v, (_, _, t) in zip(vals, campos))
        for flag, vals in registros
    )

    with open(caminho, "wb") as fh:
        fh.write(bytes(cabecalho))
        for nome, tipo, tamanho in campos:
            fh.write(_campo(nome, tipo, tamanho))
        fh.write(b"\x0d")
        fh.write(corpo)
        fh.write(b"\x1a")


@pytest.fixture
def arquivo(tmp_path):
    caminho = tmp_path / "amostra.dbf"
    campos = [("MUNIC_RES", "C", 6), ("DIAG_PRINC", "C", 4),
              ("IDADE", "N", 3), ("VAL_TOT", "N", 10)]
    registros = [
        (b" ", ["355030", "E119", " 59", "    321.68"]),
        (b" ", ["230440", "E105", " 42", "    360.80"]),
        (b"*", ["999999", "XXXX", "  1", "      0.00"]),   # excluido
        (b" ", ["120050", "I10 ", "  7", "      0.00"]),
    ]
    _montar_dbf(caminho, campos, registros)
    return caminho


def test_descarta_registro_excluido(arquivo):
    assert len(ler_dbf(arquivo)) == 3


def test_campo_numerico_vira_numero(arquivo):
    df = ler_dbf(arquivo)
    assert df["VAL_TOT"].tolist() == [321.68, 360.80, 0.0]
    assert df["IDADE"].tolist() == [59, 42, 7]


def test_campo_texto_perde_espacos_das_bordas(arquivo):
    assert ler_dbf(arquivo)["DIAG_PRINC"].tolist() == ["E119", "E105", "I10"]


def test_le_apenas_as_colunas_pedidas(arquivo):
    df = ler_dbf(arquivo, colunas=["MUNIC_RES", "IDADE"])
    assert list(df.columns) == ["MUNIC_RES", "IDADE"]


def test_resultado_identico_ao_dbfread(arquivo):
    rapido = ler_dbf(arquivo)
    lento = pd.DataFrame(iter(dbfread.DBF(str(arquivo), encoding="latin-1")))

    assert list(rapido.columns) == list(lento.columns)
    assert len(rapido) == len(lento)
    for coluna in rapido.columns:
        a, b = rapido[coluna], lento[coluna]
        if pd.api.types.is_numeric_dtype(a):
            assert a.tolist() == pytest.approx(pd.to_numeric(b).tolist())
        else:
            assert a.tolist() == [str(v).strip() for v in b]
