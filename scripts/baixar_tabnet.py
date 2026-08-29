"""Baixa do TabNet os totais oficiais de internacao por diabetes, por UF e ano.

Esta e a referencia externa da reconciliacao: se os nossos numeros nao baterem com
os do TabNet dentro da tolerancia, algo esta errado no pipeline e nenhuma conclusao
pode ser escrita antes de descobrir o que.

Cubo: `sih/cnv/nruf.def` — Morbidade Hospitalar por local de RESIDENCIA. E o cubo
certo porque a camada gold agrega por `MUNIC_RES`. O cubo `niuf.def` (por local de
internacao) produziria divergencia sistematica em toda UF com fluxo de pacientes.

Recorte: Lista de Morbidade CID-10, categoria 124 "Diabetes mellitus", que
corresponde a E10-E14 no diagnostico principal — o mesmo filtro do projeto.
"""

import re
import sys
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from diabetes_sus.config import CODIGO_UF_PARA_SIGLA  # noqa: E402

BASE = "http://tabnet.datasus.gov.br"
CGI = f"{BASE}/cgi/tabcgi.exe?sih/cnv/nruf.def"
ANOS = range(2019, 2025)
DESTINO = RAIZ / "data" / "raw" / "tabnet_referencia.csv"

# Os nomes de parametro do TabNet carregam acentos e o corpo vai em latin-1.
PARAMETROS = [
    ("Linha", "Unidade_da_Federa\xe7\xe3o"),
    ("Coluna", "Ano_processamento"),
    ("Incremento", "Interna\xe7\xf5es"),
    ("SLista_Morb__CID-10", "124"),          # Diabetes mellitus (E10-E14)
    ("SRegi\xe3o", "TODAS_AS_CATEGORIAS__"),
    ("SUnidade_da_Federa\xe7\xe3o", "TODAS_AS_CATEGORIAS__"),
    ("SCap\xedtulo_CID-10", "TODAS_AS_CATEGORIAS__"),
    ("SCar\xe1ter_atendimento", "TODAS_AS_CATEGORIAS__"),
    ("SRegime", "TODAS_AS_CATEGORIAS__"),
    ("SSexo", "TODAS_AS_CATEGORIAS__"),
    ("formato", "table"),
    ("mostre", "Mostra"),
]

CABECALHO = {"Content-Type": "application/x-www-form-urlencoded",
             "User-Agent": "Mozilla/5.0"}


def consultar() -> str:
    """Envia o POST ao TabNet e devolve o HTML da resposta."""
    arquivos = [f"nruf{ano % 100:02d}{mes:02d}.dbf"
                for ano in ANOS for mes in range(1, 13)]
    pares = PARAMETROS + [("Arquivos", a) for a in arquivos]
    corpo = "&".join(
        f"{urllib.parse.quote(k, encoding='latin-1')}="
        f"{urllib.parse.quote(v, encoding='latin-1')}"
        for k, v in pares
    )
    resposta = requests.post(CGI, data=corpo.encode("latin-1"),
                             headers=CABECALHO, timeout=300)
    resposta.raise_for_status()
    return resposta.content.decode("latin-1")


def baixar_csv(html: str) -> str:
    achado = re.search(r'HREF=(/csv/[^\s>]+\.csv)', html, re.IGNORECASE)
    if not achado:
        raise SystemExit("TabNet nao devolveu link de CSV — verifique os parametros")
    resposta = requests.get(BASE + achado.group(1), headers=CABECALHO, timeout=300)
    resposta.raise_for_status()
    return resposta.content.decode("latin-1")


def converter(texto: str) -> pd.DataFrame:
    """Converte o CSV do TabNet (UF nas linhas, ano nas colunas) para formato longo."""
    linhas = [l for l in texto.splitlines() if l.startswith('"')]
    cabecalho = [c.strip('"') for c in linhas[0].split(";")]
    anos = [c for c in cabecalho[1:] if c.isdigit()]

    registros = []
    for linha in linhas[1:]:
        campos = [c.strip('"') for c in linha.split(";")]
        rotulo = campos[0]
        # O rotulo vem como '11 Rondonia'; o codigo de 2 digitos identifica a UF.
        codigo = re.match(r"\s*(\d{2})\s", rotulo)
        if not codigo:
            continue                      # linha 'Total' e afins
        sigla = CODIGO_UF_PARA_SIGLA.get(int(codigo.group(1)))
        if not sigla:
            continue
        for posicao, ano in enumerate(anos, start=1):
            bruto = campos[posicao].replace(".", "").replace("-", "0").strip()
            registros.append({"uf": sigla, "ano": int(ano),
                              "internacoes": int(bruto or 0)})
    return pd.DataFrame(registros).sort_values(["uf", "ano"]).reset_index(drop=True)


def main() -> None:
    print("consultando o TabNet (cubo por local de residencia)...", flush=True)
    html = consultar()
    titulo = re.search(r"Morbidade Hospitalar[^<]*", html)
    print("  cubo:", titulo.group(0).strip() if titulo else "?")

    csv = baixar_csv(html)
    tabela = converter(csv)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(DESTINO, index=False)

    print(f"\ngravado: {DESTINO}")
    print(f"  {len(tabela)} linhas | {tabela['uf'].nunique()} UFs | "
          f"anos {sorted(tabela['ano'].unique())}")
    print(f"  total de internacoes por diabetes 2019-2024: "
          f"{tabela['internacoes'].sum():,}")
    print("\npor ano:")
    print(tabela.groupby("ano")["internacoes"].sum().to_string())


if __name__ == "__main__":
    main()
