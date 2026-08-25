# Desigualdade Regional no Cuidado ao Diabetes no SUS — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir uma análise reproduzível da desigualdade regional no cuidado ao diabetes no SUS entre 2019 e 2024, entregue como repositório GitHub com notebooks, índice ICVD testado e dashboard Power BI.

**Architecture:** A lógica de cálculo vive num pacote Python (`src/diabetes_sus/`) coberto por `pytest`; os notebooks apenas orquestram. A ingestão pesada (download `.dbc`, conversão, PySpark) roda no Google Colab e devolve uma camada gold de ~33 mil linhas; a análise, o índice e a EDA rodam localmente em pandas + DuckDB. O dashboard consome a gold via Google Sheets e CSV local.

**Tech Stack:** Python 3.13 (local) / 3.11 (Colab) · pandas · numpy · pyarrow · duckdb · pytest · PySpark (só no Colab) · matplotlib + seaborn · Power BI Desktop 2.156.951.0 · Google Sheets

**Spec:** `docs/superpowers/specs/2026-08-23-diabetes-sus-design.md`

## Global Constraints

- **Janela temporal:** 2019–2024. Baseline = 2019. Período atual = 2023–2024.
- **Filtro de seleção:** `DIAG_PRINC` iniciando em `E10`, `E11`, `E12`, `E13` ou `E14`. Filtro simples, nunca composto.
- **Amputação:** procedimentos SIGTAP com prefixo `040805`, identificados **dentro** do conjunto já filtrado por diabetes.
- **AIH de continuação:** registros com `IDENT == 5` são excluídos da contagem de internações.
- **Padronização etária:** método direto, população padrão = Censo 2022 (5.570 municípios, 203.080.756 habitantes).
- **Faixas etárias:** `<30`, `30-39`, `40-49`, `50-59`, `60-69`, `70-79`, `80+`.
- **Componentes do ICVD:** taxa de internação padronizada, % de internações com amputação, letalidade hospitalar, cobertura de APS (invertida). Pesos iguais de 0,25.
- **Normalização:** winsorização em p1/p99, depois min-max com **mínimos e máximos calculados sobre os dois períodos combinados**. Nunca normalizar cada período isoladamente.
- **Corte de 20 internações:** aplicado **exclusivamente** ao ranking municipal do ICVD. Análises regionais e por UF usam os 5.570 municípios.
- **Nunca versionar:** arquivos `.dbc`, `.dbf` e as camadas bronze/silver. Já bloqueados em `.gitignore`.
- **Idioma:** código, nomes de variáveis, commits e documentação em português.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/diabetes_sus/config.py` | Constantes do projeto: CID, faixas, UFs, regiões, corte, caminhos |
| `src/diabetes_sus/idade.py` | Conversão `IDADE`+`COD_IDADE` para anos; atribuição de faixa etária |
| `src/diabetes_sus/municipios.py` | Código IBGE 6↔7 dígitos, UF a partir do código, UF para região |
| `src/diabetes_sus/filtros.py` | Filtro de diabetes, marcação de amputação, remoção de AIH de continuação |
| `src/diabetes_sus/padronizacao.py` | Padronização direta por idade |
| `src/diabetes_sus/indice.py` | Winsorização, min-max em escala comum, ICVD, recuperação, corte, sensibilidade |
| `src/diabetes_sus/validacao.py` | Completude, denominadores órfãos, sanidade das métricas |
| `tests/test_*.py` | Um arquivo de teste por módulo |
| `notebooks/01_ingestao_colab.ipynb` | Download, conversão `.dbc`, filtro, bronze e silver (PySpark) |
| `notebooks/02_eda.ipynb` | Análise exploratória local |
| `notebooks/03_indice_icvd.ipynb` | ICVD, recuperação, gênero, sensibilidade |
| `sql/consultas_duckdb.sql` | Consultas SQL sobre a gold |
| `scripts/baixar_populacao_ibge.py` | População do Censo 2022 por município, sexo e faixa |
| `data/gold/municipio_ano.csv` | Camada final versionada |
| `docs/01-problema.md` … `04-conclusoes.md` | Entregáveis textuais |
| `dashboard/diabetes_sus.pbix` | Dashboard Power BI |

**Distribuição sugerida nos 7 dias:** Dia 1 → Tarefas 1–4 · Dia 2 → 5–6 · Dia 3 → 7–8 · Dia 4 → 9–10 · Dia 5 → 11–12 · Dia 6 → 13–14 · Dia 7 → 15.

---

### Task 1: Esqueleto do projeto e ambiente de testes

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `src/diabetes_sus/__init__.py`, `tests/__init__.py`, `tests/test_ambiente.py`
- Create (vazios com `.gitkeep`): `data/raw/`, `data/gold/`, `notebooks/`, `sql/`, `scripts/`, `dashboard/previews/`, `docs/img/`

**Interfaces:**
- Consumes: nada
- Produces: pacote importável `diabetes_sus`; `pytest` executável a partir da raiz

- [ ] **Step 1: Criar requirements.txt**

```
pandas==2.2.3
numpy==2.4.4
pyarrow>=17.0.0
duckdb==1.5.2
matplotlib==3.10.9
seaborn>=0.13.2
jupyter>=1.1.1
openpyxl>=3.1.5
requests==2.33.1
pytest>=8.3.0
scipy>=1.14.0
```

- [ ] **Step 2: Criar pytest.ini**

```ini
[pytest]
testpaths = tests
pythonpath = src
addopts = -v --tb=short
```

- [ ] **Step 3: Criar o pacote**

`src/diabetes_sus/__init__.py`:
```python
"""Análise da desigualdade regional no cuidado ao diabetes no SUS."""

__version__ = "0.1.0"
```

`tests/__init__.py`: arquivo vazio.

- [ ] **Step 4: Escrever o teste de ambiente**

`tests/test_ambiente.py`:
```python
import diabetes_sus


def test_pacote_importa():
    assert diabetes_sus.__version__ == "0.1.0"
```

- [ ] **Step 5: Instalar dependências e rodar o teste**

Run: `pip install -r requirements.txt && pytest tests/test_ambiente.py`
Expected: PASS, 1 teste.

- [ ] **Step 6: Criar as pastas de dados**

```bash
mkdir -p data/raw data/gold notebooks sql scripts dashboard/previews docs/img
for d in data/raw data/gold notebooks sql scripts dashboard/previews docs/img; do touch "$d/.gitkeep"; done
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini src tests data notebooks sql scripts dashboard docs
git commit -m "chore: esqueleto do projeto e ambiente de testes"
```

---

### Task 2: Constantes e conversão de idade

**Files:**
- Create: `src/diabetes_sus/config.py`, `src/diabetes_sus/idade.py`
- Test: `tests/test_idade.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `config.CID_DIABETES_PREFIXOS: tuple[str, ...]`
  - `config.ROTULOS_FAIXAS: list[str]`
  - `config.ANO_BASELINE: int`, `config.ANOS_ATUAIS: tuple[int, int]`
  - `config.CORTE_MIN_INTERNACOES: int`
  - `config.SIGTAP_AMPUTACAO_MMII_PREFIXO: str`
  - `config.COMPONENTES_ICVD: list[str]`, `config.COMPONENTES_INVERTIDOS: tuple[str, ...]`
  - `idade.idade_em_anos(idade: pd.Series, cod_idade: pd.Series) -> pd.Series[float]`
  - `idade.faixa_etaria(anos: pd.Series) -> pd.Series[pd.Categorical]`

- [ ] **Step 1: Escrever config.py**

```python
"""Constantes do projeto."""

from pathlib import Path

CID_DIABETES_PREFIXOS = ("E10", "E11", "E12", "E13", "E14")
SIGTAP_AMPUTACAO_MMII_PREFIXO = "040805"

ANOS = tuple(range(2019, 2025))
ANO_BASELINE = 2019
ANOS_ATUAIS = (2023, 2024)
PERIODO_BASE = "2019"
PERIODO_ATUAL = "2023-24"

CORTE_MIN_INTERNACOES = 20

ROTULOS_FAIXAS = ["<30", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
LIMITES_FAIXAS = [29, 39, 49, 59, 69, 79]

COMPONENTES_ICVD = [
    "taxa_internacao_padronizada",
    "prop_amputacao",
    "letalidade",
    "cobertura_aps",
]
COMPONENTES_INVERTIDOS = ("cobertura_aps",)
PESOS_IGUAIS = {c: 0.25 for c in COMPONENTES_ICVD}

UFS = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
)

CODIGO_UF_PARA_SIGLA = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

UF_PARA_REGIAO = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(
        ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"
    ),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

RAIZ = Path(__file__).resolve().parents[2]
DIR_DADOS = RAIZ / "data"
DIR_RAW = DIR_DADOS / "raw"
DIR_GOLD = DIR_DADOS / "gold"
```

- [ ] **Step 2: Escrever o teste que falha**

`tests/test_idade.py`:
```python
import numpy as np
import pandas as pd
import pytest

from diabetes_sus.idade import faixa_etaria, idade_em_anos


def test_cod_idade_4_significa_anos():
    resultado = idade_em_anos(pd.Series([45, 3, 80]), pd.Series([4, 4, 4]))
    assert resultado.tolist() == [45.0, 3.0, 80.0]


def test_cod_idade_5_soma_cem_anos():
    resultado = idade_em_anos(pd.Series([2, 7]), pd.Series([5, 5]))
    assert resultado.tolist() == [102.0, 107.0]


def test_dias_e_meses_viram_zero_anos():
    resultado = idade_em_anos(pd.Series([15, 8]), pd.Series([2, 3]))
    assert resultado.tolist() == [0.0, 0.0]


def test_codigo_desconhecido_vira_nan():
    resultado = idade_em_anos(pd.Series([30]), pd.Series([9]))
    assert np.isnan(resultado.iloc[0])


def test_idade_negativa_vira_nan():
    resultado = idade_em_anos(pd.Series([-5]), pd.Series([4]))
    assert np.isnan(resultado.iloc[0])


def test_faixa_etaria_respeita_os_limites():
    anos = pd.Series([0, 29, 30, 39, 40, 59, 60, 79, 80, 105])
    esperado = [
        "<30", "<30", "30-39", "30-39", "40-49",
        "50-59", "60-69", "70-79", "80+", "80+",
    ]
    assert faixa_etaria(anos).astype(str).tolist() == esperado


def test_faixa_etaria_propaga_nan():
    resultado = faixa_etaria(pd.Series([np.nan]))
    assert pd.isna(resultado.iloc[0])
```

- [ ] **Step 3: Rodar e confirmar a falha**

Run: `pytest tests/test_idade.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.idade'`

- [ ] **Step 4: Implementar idade.py**

```python
"""Conversão da idade codificada do SIH para anos e faixas etárias."""

import numpy as np
import pandas as pd

from diabetes_sus.config import LIMITES_FAIXAS, ROTULOS_FAIXAS

_DIAS = 2
_MESES = 3
_ANOS = 4
_ANOS_ACIMA_DE_CEM = 5


def idade_em_anos(idade: pd.Series, cod_idade: pd.Series) -> pd.Series:
    """Converte IDADE + COD_IDADE do SIH para anos completos.

    COD_IDADE: 2 = dias, 3 = meses, 4 = anos, 5 = anos acima de 100
    (a idade registrada precisa ser somada a 100). Qualquer outro código
    é tratado como desconhecido e devolve NaN.
    """
    valor = pd.to_numeric(idade, errors="coerce")
    codigo = pd.to_numeric(cod_idade, errors="coerce")

    anos = pd.Series(np.nan, index=valor.index, dtype="float64")
    anos = anos.mask(codigo.isin([_DIAS, _MESES]), 0.0)
    anos = anos.mask(codigo == _ANOS, valor)
    anos = anos.mask(codigo == _ANOS_ACIMA_DE_CEM, valor + 100)

    return anos.mask(anos < 0, np.nan)


def faixa_etaria(anos: pd.Series) -> pd.Series:
    """Atribui a faixa etária do projeto a uma série de idades em anos."""
    limites = [-np.inf, *LIMITES_FAIXAS, np.inf]
    return pd.cut(
        pd.to_numeric(anos, errors="coerce"),
        bins=limites,
        labels=ROTULOS_FAIXAS,
        right=True,
    )
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `pytest tests/test_idade.py`
Expected: PASS, 7 testes.

- [ ] **Step 6: Commit**

```bash
git add src/diabetes_sus/config.py src/diabetes_sus/idade.py tests/test_idade.py
git commit -m "feat: constantes do projeto e conversao de idade do SIH"
```

---

### Task 3: Municípios, UFs e regiões

**Files:**
- Create: `src/diabetes_sus/municipios.py`
- Test: `tests/test_municipios.py`

**Interfaces:**
- Consumes: `config.CODIGO_UF_PARA_SIGLA`, `config.UF_PARA_REGIAO`
- Produces:
  - `municipios.mapa_6_para_7(codigos7: Iterable[str | int]) -> dict[str, str]`
  - `municipios.completar_codigo(cod6: pd.Series, mapa: dict[str, str]) -> pd.Series[str]`
  - `municipios.uf_do_codigo(codigo: pd.Series) -> pd.Series[str]`
  - `municipios.regiao_da_uf(uf: pd.Series) -> pd.Series[str]`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_municipios.py`:
```python
import pandas as pd

from diabetes_sus.municipios import (
    completar_codigo,
    mapa_6_para_7,
    regiao_da_uf,
    uf_do_codigo,
)


def test_mapa_usa_os_seis_primeiros_digitos():
    assert mapa_6_para_7(["3550308", "2304400"]) == {
        "355030": "3550308",
        "230440": "2304400",
    }


def test_completar_codigo_expande_para_sete_digitos():
    mapa = mapa_6_para_7(["3550308", "2304400"])
    resultado = completar_codigo(pd.Series(["355030", "230440"]), mapa)
    assert resultado.tolist() == ["3550308", "2304400"]


def test_codigo_desconhecido_vira_nulo():
    mapa = mapa_6_para_7(["3550308"])
    resultado = completar_codigo(pd.Series(["999999"]), mapa)
    assert pd.isna(resultado.iloc[0])


def test_uf_vem_dos_dois_primeiros_digitos():
    resultado = uf_do_codigo(pd.Series(["3550308", "2304400", "1200401"]))
    assert resultado.tolist() == ["SP", "CE", "AC"]


def test_uf_aceita_codigo_de_seis_digitos():
    assert uf_do_codigo(pd.Series(["355030"])).tolist() == ["SP"]


def test_regiao_da_uf():
    resultado = regiao_da_uf(pd.Series(["SP", "CE", "AC", "RS", "GO"]))
    assert resultado.tolist() == [
        "Sudeste", "Nordeste", "Norte", "Sul", "Centro-Oeste",
    ]


def test_todas_as_ufs_tem_regiao():
    from diabetes_sus.config import UFS

    resultado = regiao_da_uf(pd.Series(list(UFS)))
    assert resultado.notna().all()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `pytest tests/test_municipios.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.municipios'`

- [ ] **Step 3: Implementar municipios.py**

```python
"""Compatibilização de códigos de município e mapeamento territorial."""

from typing import Iterable

import pandas as pd

from diabetes_sus.config import CODIGO_UF_PARA_SIGLA, UF_PARA_REGIAO


def mapa_6_para_7(codigos7: Iterable) -> dict:
    """Constrói o dicionário de código IBGE de 6 dígitos para 7 dígitos.

    O SIH grava o município sem o dígito verificador; o IBGE publica com ele.
    """
    return {str(c)[:6]: str(c) for c in codigos7}


def completar_codigo(cod6: pd.Series, mapa: dict) -> pd.Series:
    """Expande códigos de 6 dígitos para 7. Códigos ausentes viram NaN."""
    return cod6.astype("string").str.strip().map(mapa).astype("string")


def uf_do_codigo(codigo: pd.Series) -> pd.Series:
    """Extrai a sigla da UF dos dois primeiros dígitos do código IBGE."""
    prefixo = pd.to_numeric(
        codigo.astype("string").str.strip().str[:2], errors="coerce"
    )
    return prefixo.map(CODIGO_UF_PARA_SIGLA).astype("string")


def regiao_da_uf(uf: pd.Series) -> pd.Series:
    """Mapeia a sigla da UF para a macrorregião do IBGE."""
    return uf.astype("string").str.upper().str.strip().map(UF_PARA_REGIAO).astype(
        "string"
    )
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `pytest tests/test_municipios.py`
Expected: PASS, 7 testes.

- [ ] **Step 5: Commit**

```bash
git add src/diabetes_sus/municipios.py tests/test_municipios.py
git commit -m "feat: compatibilizacao de codigos de municipio e mapa territorial"
```

---

### Task 4: Filtros de seleção do SIH

**Files:**
- Create: `src/diabetes_sus/filtros.py`
- Test: `tests/test_filtros.py`

**Interfaces:**
- Consumes: `config.CID_DIABETES_PREFIXOS`, `config.SIGTAP_AMPUTACAO_MMII_PREFIXO`
- Produces:
  - `filtros.eh_diabetes(diag_princ: pd.Series) -> pd.Series[bool]`
  - `filtros.eh_amputacao_mmii(proc_rea: pd.Series) -> pd.Series[bool]`
  - `filtros.remover_aih_continuacao(df: pd.DataFrame, coluna: str = "IDENT") -> pd.DataFrame`
  - `filtros.filtrar_internacoes_diabetes(df: pd.DataFrame) -> pd.DataFrame` — aplica os três acima e devolve o DataFrame com a coluna booleana `amputacao` adicionada

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_filtros.py`:
```python
import pandas as pd

from diabetes_sus.filtros import (
    eh_amputacao_mmii,
    eh_diabetes,
    filtrar_internacoes_diabetes,
    remover_aih_continuacao,
)


def test_reconhece_todos_os_cids_de_diabetes():
    serie = pd.Series(["E100", "E110", "E120", "E130", "E140"])
    assert eh_diabetes(serie).all()


def test_rejeita_cid_vizinho_que_nao_e_diabetes():
    serie = pd.Series(["E150", "E059", "I10", "N180"])
    assert not eh_diabetes(serie).any()


def test_diabetes_ignora_caixa_e_espacos():
    assert eh_diabetes(pd.Series([" e119 "])).iloc[0]


def test_diabetes_trata_nulo_como_falso():
    assert not eh_diabetes(pd.Series([None])).iloc[0]


def test_reconhece_procedimento_de_amputacao():
    assert eh_amputacao_mmii(pd.Series(["0408050020"])).iloc[0]
    assert not eh_amputacao_mmii(pd.Series(["0408010010"])).iloc[0]


def test_amputacao_completa_codigo_com_zeros_a_esquerda():
    assert eh_amputacao_mmii(pd.Series(["408050020"])).iloc[0]


def test_remove_aih_de_continuacao():
    df = pd.DataFrame({"IDENT": [1, 5, 1], "x": ["a", "b", "c"]})
    resultado = remover_aih_continuacao(df)
    assert resultado["x"].tolist() == ["a", "c"]


def test_filtro_completo_mantem_so_diabetes_e_marca_amputacao():
    df = pd.DataFrame(
        {
            "DIAG_PRINC": ["E114", "I10", "E105"],
            "PROC_REA": ["0408050020", "0408050020", "0303040017"],
            "IDENT": [1, 1, 1],
        }
    )
    resultado = filtrar_internacoes_diabetes(df)
    assert len(resultado) == 2
    assert resultado["amputacao"].tolist() == [True, False]


def test_filtro_completo_descarta_continuacao_antes_de_contar():
    df = pd.DataFrame(
        {
            "DIAG_PRINC": ["E114", "E114"],
            "PROC_REA": ["0408050020", "0408050020"],
            "IDENT": [1, 5],
        }
    )
    assert len(filtrar_internacoes_diabetes(df)) == 1
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `pytest tests/test_filtros.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.filtros'`

- [ ] **Step 3: Implementar filtros.py**

```python
"""Regras de seleção das internações do SIH/SUS."""

import pandas as pd

from diabetes_sus.config import (
    CID_DIABETES_PREFIXOS,
    SIGTAP_AMPUTACAO_MMII_PREFIXO,
)

IDENT_CONTINUACAO = 5


def eh_diabetes(diag_princ: pd.Series) -> pd.Series:
    """Marca internações cujo diagnóstico principal é diabetes (E10-E14).

    Compara os três primeiros caracteres em vez de usar startswith com
    tupla, que não é suportado de forma consistente entre os backends de
    string do pandas.
    """
    normalizado = diag_princ.astype("string").str.upper().str.strip()
    return (
        normalizado.str[:3].isin(CID_DIABETES_PREFIXOS).fillna(False).astype(bool)
    )


def eh_amputacao_mmii(proc_rea: pd.Series) -> pd.Series:
    """Marca procedimentos de amputação de membro inferior (SIGTAP 040805)."""
    normalizado = proc_rea.astype("string").str.strip().str.zfill(10)
    prefixo = normalizado.str[: len(SIGTAP_AMPUTACAO_MMII_PREFIXO)]
    return prefixo.eq(SIGTAP_AMPUTACAO_MMII_PREFIXO).fillna(False).astype(bool)


def remover_aih_continuacao(
    df: pd.DataFrame, coluna: str = "IDENT"
) -> pd.DataFrame:
    """Descarta AIHs de continuação, que não são novas internações."""
    ident = pd.to_numeric(df[coluna], errors="coerce")
    return df.loc[ident != IDENT_CONTINUACAO].copy()


def filtrar_internacoes_diabetes(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica o recorte do projeto e marca as internações com amputação."""
    sem_continuacao = remover_aih_continuacao(df)
    diabetes = sem_continuacao.loc[
        eh_diabetes(sem_continuacao["DIAG_PRINC"])
    ].copy()
    diabetes["amputacao"] = eh_amputacao_mmii(diabetes["PROC_REA"])
    return diabetes.reset_index(drop=True)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `pytest tests/test_filtros.py`
Expected: PASS, 9 testes.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `pytest`
Expected: PASS, 24 testes (1 + 7 + 7 + 9).

- [ ] **Step 6: Commit**

```bash
git add src/diabetes_sus/filtros.py tests/test_filtros.py
git commit -m "feat: filtros de selecao das internacoes por diabetes"
```

---

### Task 5: População do Censo 2022 por município, sexo e faixa

**Files:**
- Create: `scripts/baixar_populacao_ibge.py`
- Create (gerado): `data/gold/populacao_municipio_faixa_sexo.parquet`
- Test: `tests/test_populacao.py`

**Interfaces:**
- Consumes: `config.DIR_GOLD`, `municipios.uf_do_codigo`, `municipios.regiao_da_uf`
- Produces: parquet com as colunas `cod_municipio` (str, 7 dígitos), `uf` (str), `regiao` (str), `sexo` (`"M"`/`"F"`), `faixa_etaria` (str), `populacao` (int)

**Nota:** o agregado SIDRA 9514 traz o Censo 2022 por município, sexo e grupo quinquenal de idade. O script agrega os quinquênios nas faixas do projeto. Se a API recusar a requisição nacional inteira, o script itera por UF.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_populacao.py`:
```python
import pandas as pd
import pytest

from diabetes_sus.config import DIR_GOLD, ROTULOS_FAIXAS

ARQUIVO = DIR_GOLD / "populacao_municipio_faixa_sexo.parquet"

pytestmark = pytest.mark.skipif(
    not ARQUIVO.exists(),
    reason="rode scripts/baixar_populacao_ibge.py primeiro",
)


@pytest.fixture(scope="module")
def pop():
    return pd.read_parquet(ARQUIVO)


def test_tem_os_5570_municipios(pop):
    assert pop["cod_municipio"].nunique() == 5570


def test_populacao_total_bate_com_o_censo_2022(pop):
    assert pop["populacao"].sum() == pytest.approx(203_080_756, rel=0.005)


def test_codigo_tem_sete_digitos(pop):
    assert pop["cod_municipio"].str.len().eq(7).all()


def test_usa_apenas_as_faixas_do_projeto(pop):
    assert set(pop["faixa_etaria"]) <= set(ROTULOS_FAIXAS)


def test_sexo_tem_apenas_m_e_f(pop):
    assert set(pop["sexo"]) == {"M", "F"}


def test_nenhuma_populacao_negativa(pop):
    assert (pop["populacao"] >= 0).all()


def test_todas_as_cinco_regioes_presentes(pop):
    assert pop["regiao"].nunique() == 5
```

- [ ] **Step 2: Rodar e confirmar que os testes são pulados**

Run: `pytest tests/test_populacao.py`
Expected: 7 SKIPPED — o parquet ainda não existe.

- [ ] **Step 3: Escrever o script de download**

`scripts/baixar_populacao_ibge.py`:
```python
"""Baixa a população do Censo 2022 por município, sexo e faixa etária."""

import sys
import time

import pandas as pd
import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1] / "src"))

from diabetes_sus.config import DIR_GOLD, ROTULOS_FAIXAS  # noqa: E402
from diabetes_sus.municipios import regiao_da_uf, uf_do_codigo  # noqa: E402

URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/9514"
    "/periodos/2022/variaveis/93"
    "?localidades=N6[N3[{uf}]]&classificacao=2[4,5]|287[{grupos}]"
)

# Códigos da classificação 287 (grupo de idade) que compõem cada faixa do projeto.
GRUPOS_POR_FAIXA = {
    "<30": [93, 94, 95, 96, 97, 98],
    "30-39": [99, 100],
    "40-49": [101, 102],
    "50-59": [103, 104],
    "60-69": [105, 106],
    "70-79": [107, 108],
    "80+": [109, 110, 111, 112],
}
GRUPO_PARA_FAIXA = {
    g: faixa for faixa, grupos in GRUPOS_POR_FAIXA.items() for g in grupos
}
SEXO_POR_CODIGO = {"4": "M", "5": "F"}
CODIGOS_UF = list(range(11, 18)) + list(range(21, 30)) + [31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]


def baixar_uf(cod_uf: int) -> pd.DataFrame:
    grupos = ",".join(str(g) for g in GRUPO_PARA_FAIXA)
    url = URL.format(uf=cod_uf, grupos=grupos)
    resposta = requests.get(url, timeout=180)
    resposta.raise_for_status()
    linhas = []
    for variavel in resposta.json():
        for resultado in variavel["resultados"]:
            cod_sexo = resultado["classificacoes"][0]["categoria"]
            cod_grupo = resultado["classificacoes"][1]["categoria"]
            sexo = SEXO_POR_CODIGO[next(iter(cod_sexo))]
            grupo = int(next(iter(cod_grupo)))
            for serie in resultado["series"]:
                valor = next(iter(serie["serie"].values()))
                linhas.append(
                    {
                        "cod_municipio": serie["localidade"]["id"],
                        "sexo": sexo,
                        "faixa_etaria": GRUPO_PARA_FAIXA[grupo],
                        "populacao": pd.to_numeric(valor, errors="coerce"),
                    }
                )
    return pd.DataFrame(linhas)


def main() -> None:
    partes = []
    for cod_uf in CODIGOS_UF:
        print(f"baixando UF {cod_uf}...", flush=True)
        for tentativa in range(3):
            try:
                partes.append(baixar_uf(cod_uf))
                break
            except requests.RequestException as erro:
                print(f"  tentativa {tentativa + 1} falhou: {erro}")
                time.sleep(5 * (tentativa + 1))
        else:
            raise SystemExit(f"UF {cod_uf} falhou nas 3 tentativas")

    pop = pd.concat(partes, ignore_index=True)
    pop["populacao"] = pop["populacao"].fillna(0).astype("int64")
    pop = (
        pop.groupby(["cod_municipio", "sexo", "faixa_etaria"], as_index=False)[
            "populacao"
        ]
        .sum()
    )
    pop["uf"] = uf_do_codigo(pop["cod_municipio"])
    pop["regiao"] = regiao_da_uf(pop["uf"])
    pop["faixa_etaria"] = pd.Categorical(
        pop["faixa_etaria"], categories=ROTULOS_FAIXAS, ordered=True
    )

    DIR_GOLD.mkdir(parents=True, exist_ok=True)
    destino = DIR_GOLD / "populacao_municipio_faixa_sexo.parquet"
    pop.to_parquet(destino, index=False)
    print(f"gravado: {destino}")
    print(f"municipios: {pop['cod_municipio'].nunique()}")
    print(f"populacao total: {pop['populacao'].sum():,}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Executar o script**

Run: `python scripts/baixar_populacao_ibge.py`
Expected: imprime `municipios: 5570` e uma população total próxima de 203.080.756.

**Se a API recusar a classificação 287:** conferir os códigos de grupo etário em `https://servicodados.ibge.gov.br/api/v3/agregados/9514/metadados` e ajustar `GRUPOS_POR_FAIXA`. O teste `test_populacao_total_bate_com_o_censo_2022` é a rede de segurança — se os grupos estiverem errados, o total não fecha.

- [ ] **Step 5: Rodar os testes**

Run: `pytest tests/test_populacao.py`
Expected: PASS, 7 testes.

- [ ] **Step 6: Commit**

```bash
git add scripts/baixar_populacao_ibge.py tests/test_populacao.py data/gold/populacao_municipio_faixa_sexo.parquet
git commit -m "feat: populacao do Censo 2022 por municipio, sexo e faixa etaria"
```

---

### Task 6: Notebook de ingestão no Colab — camada bronze

**Files:**
- Create: `notebooks/01_ingestao_colab.ipynb`

**Interfaces:**
- Consumes: `filtros.filtrar_internacoes_diabetes`, `idade.idade_em_anos`, `idade.faixa_etaria`
- Produces: no Google Drive, `bronze/uf=<UF>/ano=<AAAA>/RD<UF><AAMM>.parquet` com as colunas `cod_municipio_6`, `sexo`, `idade_anos`, `faixa_etaria`, `ano`, `mes`, `amputacao`, `morte`, `val_tot`, `dias_perm`

**Nota:** este notebook roda **no Google Colab**, não localmente. O `.dbc` não abre no Python 3.13 do Windows — restrição já verificada e documentada na Seção 2.4 do spec.

- [ ] **Step 1: Célula de setup**

```python
!pip install -q datasus-dbc pyarrow
from google.colab import drive
drive.mount('/content/drive')

import os
BASE = '/content/drive/MyDrive/diabetes_sus'
os.makedirs(f'{BASE}/bronze', exist_ok=True)
os.makedirs(f'{BASE}/logs', exist_ok=True)
print(BASE)
```

- [ ] **Step 2: Célula com os módulos do projeto**

Copiar `config.py`, `idade.py`, `municipios.py` e `filtros.py` para o Drive e adicioná-los ao `sys.path`:

```python
import sys
sys.path.insert(0, f'{BASE}/src')
from diabetes_sus.filtros import filtrar_internacoes_diabetes
from diabetes_sus.idade import faixa_etaria, idade_em_anos
print('modulos carregados')
```

- [ ] **Step 3: Célula da lista de arquivos**

```python
UFS = ['AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
       'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO']
ANOS = range(2019, 2025)

alvos = [(uf, ano, mes) for uf in UFS for ano in ANOS for mes in range(1, 13)]
print(f'{len(alvos)} arquivos esperados')   # deve imprimir 1944
```

- [ ] **Step 4: Célula de ingestão com checkpoint**

```python
import datasus_dbc, pandas as pd, urllib.request, os, json, traceback

FTP = ('ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS'
       '/200801_/Dados/RD{uf}{aa:02d}{mm:02d}.dbc')

COLUNAS = ['MUNIC_RES','SEXO','IDADE','COD_IDADE','DIAG_PRINC',
           'PROC_REA','IDENT','MORTE','VAL_TOT','DIAS_PERM']

pendentes = []

def processar(uf, ano, mes):
    destino = f'{BASE}/bronze/uf={uf}/ano={ano}'
    os.makedirs(destino, exist_ok=True)
    saida = f'{destino}/RD{uf}{ano % 100:02d}{mes:02d}.parquet'
    if os.path.exists(saida):
        return 'ja_existe'

    url = FTP.format(uf=uf, aa=ano % 100, mm=mes)
    dbc, dbf = '/tmp/a.dbc', '/tmp/a.dbf'
    urllib.request.urlretrieve(url, dbc)
    datasus_dbc.decompress(dbc, dbf)

    from dbfread import DBF
    df = pd.DataFrame(iter(DBF(dbf, encoding='latin-1')))
    df = df[[c for c in COLUNAS if c in df.columns]]

    df = filtrar_internacoes_diabetes(df)
    df['idade_anos'] = idade_em_anos(df['IDADE'], df['COD_IDADE'])
    df['faixa_etaria'] = faixa_etaria(df['idade_anos']).astype(str)
    df = df.rename(columns={
        'MUNIC_RES': 'cod_municipio_6', 'SEXO': 'sexo',
        'MORTE': 'morte', 'VAL_TOT': 'val_tot', 'DIAS_PERM': 'dias_perm',
    })
    df['ano'], df['mes'] = ano, mes
    df[['cod_municipio_6','sexo','idade_anos','faixa_etaria','ano','mes',
        'amputacao','morte','val_tot','dias_perm']].to_parquet(saida, index=False)

    os.remove(dbc); os.remove(dbf)
    return f'{len(df)} linhas'

for i, (uf, ano, mes) in enumerate(alvos, 1):
    for tentativa in range(3):
        try:
            r = processar(uf, ano, mes)
            if i % 50 == 0:
                print(f'[{i}/{len(alvos)}] {uf} {ano}-{mes:02d}: {r}', flush=True)
            break
        except Exception as e:
            if tentativa == 2:
                pendentes.append({'uf': uf, 'ano': ano, 'mes': mes, 'erro': str(e)})
                print(f'FALHOU {uf} {ano}-{mes:02d}: {e}', flush=True)

with open(f'{BASE}/logs/pendentes.json', 'w') as f:
    json.dump(pendentes, f, indent=2)
print(f'concluido. pendentes: {len(pendentes)}')
```

**A célula é idempotente:** reexecutar após uma queda de sessão pula tudo que já gravou parquet. Rode quantas vezes for preciso.

- [ ] **Step 5: Célula de verificação da completude**

```python
import glob
gerados = glob.glob(f'{BASE}/bronze/uf=*/ano=*/*.parquet')
print(f'gerados: {len(gerados)} de {len(alvos)}')
assert len(gerados) >= len(alvos) * 0.98, 'completude abaixo de 98% — investigar pendentes.json'
```

- [ ] **Step 6: Commit do notebook**

```bash
git add notebooks/01_ingestao_colab.ipynb
git commit -m "feat: notebook de ingestao do SIH no Colab com checkpoint"
```

---

### Task 7: Camada silver com PySpark e camada gold

**Files:**
- Modify: `notebooks/01_ingestao_colab.ipynb` (novas células ao final)
- Create (gerado): `data/gold/municipio_ano.csv`

**Interfaces:**
- Consumes: camada bronze da Task 6; `data/gold/populacao_municipio_faixa_sexo.parquet` da Task 5
- Produces: `municipio_ano.csv` com as colunas `cod_municipio`, `uf`, `regiao`, `ano`, `sexo`, `faixa_etaria`, `internacoes`, `amputacoes`, `obitos`, `val_total`, `dias_perm_total`, `populacao`, `cobertura_aps`

- [ ] **Step 1: Célula de sessão Spark**

```python
!pip install -q pyspark
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder
         .appName('diabetes_sus')
         .config('spark.driver.memory', '8g')
         .config('spark.sql.shuffle.partitions', '64')
         .getOrCreate())
print(spark.version)
```

- [ ] **Step 2: Célula de agregação silver**

```python
bronze = spark.read.parquet(f'{BASE}/bronze')

silver = (bronze
    .withColumn('morte', F.col('morte').cast('int'))
    .withColumn('amputacao', F.col('amputacao').cast('int'))
    .groupBy('cod_municipio_6', 'ano', 'sexo', 'faixa_etaria')
    .agg(
        F.count('*').alias('internacoes'),
        F.sum('amputacao').alias('amputacoes'),
        F.sum('morte').alias('obitos'),
        F.sum('val_tot').alias('val_total'),
        F.sum('dias_perm').alias('dias_perm_total'),
    ))

silver.write.mode('overwrite').parquet(f'{BASE}/silver/municipio_ano_faixa_sexo')
print(silver.count(), 'linhas na silver')
```

- [ ] **Step 3: Célula de join com população e cobertura de APS**

```python
import pandas as pd
from diabetes_sus.municipios import completar_codigo, mapa_6_para_7, regiao_da_uf, uf_do_codigo

pop = pd.read_parquet(f'{BASE}/insumos/populacao_municipio_faixa_sexo.parquet')
aps = pd.read_csv(f'{BASE}/insumos/cobertura_aps.csv', dtype={'cod_municipio': str})

s = spark.read.parquet(f'{BASE}/silver/municipio_ano_faixa_sexo').toPandas()

mapa = mapa_6_para_7(pop['cod_municipio'].unique())
s['cod_municipio'] = completar_codigo(s['cod_municipio_6'], mapa)

orfaos = s['cod_municipio'].isna().sum()
print(f'linhas sem municipio correspondente: {orfaos}')
assert orfaos / len(s) < 0.01, 'mais de 1% de orfaos — investigar antes de seguir'

s['sexo'] = s['sexo'].map({'1': 'M', '3': 'F', 1: 'M', 3: 'F'})
gold = (s.dropna(subset=['cod_municipio'])
          .merge(pop, on=['cod_municipio', 'sexo', 'faixa_etaria'], how='left')
          .merge(aps, on=['cod_municipio', 'ano'], how='left'))
gold['uf'] = uf_do_codigo(gold['cod_municipio'])
gold['regiao'] = regiao_da_uf(gold['uf'])

gold.to_csv(f'{BASE}/gold/municipio_ano.csv', index=False)
print(gold.shape)
```

**Sobre a cobertura de APS:** baixar manualmente do e-Gestor AB o relatório de histórico de cobertura por município, salvar como `cobertura_aps.csv` com as colunas `cod_municipio`, `ano`, `cobertura_aps` (percentual médio anual) e subir para `{BASE}/insumos/`.

**Sobre o código de sexo:** o SIH usa `1` para masculino e `3` para feminino. Conferir na primeira execução — se aparecerem outros valores, tratá-los como desconhecidos e excluí-los da trilha de gênero, registrando quantos foram.

- [ ] **Step 4: Baixar a gold para a máquina local**

Baixar `municipio_ano.csv` do Drive para `data/gold/municipio_ano.csv`.

- [ ] **Step 5: Verificar o arquivo localmente**

Run:
```bash
python -c "import pandas as pd; d=pd.read_csv('data/gold/municipio_ano.csv', dtype={'cod_municipio':str}); print(d.shape); print(d['ano'].value_counts().sort_index()); print(d.isna().sum())"
```
Expected: seis anos de 2019 a 2024, sem nulos em `internacoes`, `populacao` e `cod_municipio`.

- [ ] **Step 6: Commit**

```bash
git add notebooks/01_ingestao_colab.ipynb data/gold/municipio_ano.csv
git commit -m "feat: camada silver com PySpark e camada gold municipio-ano"
```

---

### Task 8: Padronização etária

**Files:**
- Create: `src/diabetes_sus/padronizacao.py`
- Test: `tests/test_padronizacao.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `padronizacao.taxa_padronizada(casos, populacao, pop_padrao, por: int = 100_000) -> float`
  - `padronizacao.padronizar_por_municipio(df: pd.DataFrame, pop_padrao: pd.Series, por: int = 100_000) -> pd.DataFrame` — recebe DataFrame com `cod_municipio`, `faixa_etaria`, `internacoes`, `populacao`; devolve `cod_municipio` e `taxa_internacao_padronizada`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_padronizacao.py`:
```python
import pandas as pd
import pytest

from diabetes_sus.padronizacao import padronizar_por_municipio, taxa_padronizada


def test_estrutura_igual_ao_padrao_devolve_a_taxa_bruta():
    # 10 casos em 1000 pessoas = 1000 por 100 mil, em qualquer faixa.
    resultado = taxa_padronizada(
        casos=[5, 5], populacao=[500, 500], pop_padrao=[500, 500]
    )
    assert resultado == pytest.approx(1000.0)


def test_padronizacao_corrige_estrutura_envelhecida():
    # Município concentrado na faixa idosa, que adoece mais.
    # Taxa bruta seria alta; padronizada pelo padrão jovem, cai.
    bruta = (1 + 19) / (100 + 100) * 100_000
    padronizada = taxa_padronizada(
        casos=[1, 19], populacao=[100, 100], pop_padrao=[900, 100]
    )
    assert padronizada < bruta


def test_pesos_somam_um_independente_da_escala_do_padrao():
    a = taxa_padronizada([3, 7], [100, 200], [50, 150])
    b = taxa_padronizada([3, 7], [100, 200], [5000, 15000])
    assert a == pytest.approx(b)


def test_tamanhos_diferentes_levantam_erro():
    with pytest.raises(ValueError, match="mesmo tamanho"):
        taxa_padronizada([1, 2], [10], [10, 10])


def test_populacao_zero_levanta_erro():
    with pytest.raises(ValueError, match="positiva"):
        taxa_padronizada([1, 2], [0, 10], [10, 10])


def test_padronizar_por_municipio_devolve_uma_linha_por_municipio():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308"] * 2 + ["2304400"] * 2,
            "faixa_etaria": ["<30", "80+"] * 2,
            "internacoes": [1, 9, 2, 8],
            "populacao": [1000, 100, 1000, 100],
        }
    )
    pop_padrao = pd.Series({"<30": 9000, "80+": 1000})
    resultado = padronizar_por_municipio(df, pop_padrao)

    assert len(resultado) == 2
    assert set(resultado.columns) == {
        "cod_municipio",
        "taxa_internacao_padronizada",
    }
    assert (resultado["taxa_internacao_padronizada"] > 0).all()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `pytest tests/test_padronizacao.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.padronizacao'`

- [ ] **Step 3: Implementar padronizacao.py**

```python
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `pytest tests/test_padronizacao.py`
Expected: PASS, 6 testes.

- [ ] **Step 5: Commit**

```bash
git add src/diabetes_sus/padronizacao.py tests/test_padronizacao.py
git commit -m "feat: padronizacao direta de taxas por faixa etaria"
```

---

### Task 9: Índice ICVD, corte e recuperação

**Files:**
- Create: `src/diabetes_sus/indice.py`
- Test: `tests/test_indice.py`

**Interfaces:**
- Consumes: `config.COMPONENTES_ICVD`, `config.COMPONENTES_INVERTIDOS`, `config.CORTE_MIN_INTERNACOES`, `config.PERIODO_BASE`, `config.PERIODO_ATUAL`
- Produces:
  - `indice.winsorizar(s: pd.Series, inferior: float = 0.01, superior: float = 0.99) -> pd.Series`
  - `indice.normalizar_minmax(s: pd.Series) -> pd.Series`
  - `indice.aplicar_corte(df: pd.DataFrame, corte: int = CORTE_MIN_INTERNACOES) -> pd.DataFrame` — adiciona a coluna booleana `no_ranking`
  - `indice.calcular_icvd(df: pd.DataFrame, pesos: dict[str, float] | None = None) -> pd.DataFrame` — adiciona `<componente>_norm` e `icvd`
  - `indice.calcular_recuperacao(df_icvd: pd.DataFrame) -> pd.DataFrame` — colunas `cod_municipio`, `icvd_2019`, `icvd_2023_24`, `recuperacao`

**Decisão de implementação:** `calcular_icvd` recebe o DataFrame **empilhado com os dois períodos** e normaliza sobre o conjunto inteiro. É assim que a escala comum exigida pelo spec fica garantida por construção — não há como esquecer.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_indice.py`:
```python
import numpy as np
import pandas as pd
import pytest

from diabetes_sus.config import PERIODO_ATUAL, PERIODO_BASE
from diabetes_sus.indice import (
    aplicar_corte,
    calcular_icvd,
    calcular_recuperacao,
    normalizar_minmax,
    winsorizar,
)


def quadro(n=6, periodo=PERIODO_BASE, **sobrescreve):
    base = {
        "cod_municipio": [f"350000{i}" for i in range(n)],
        "periodo": [periodo] * n,
        "internacoes": [100] * n,
        "taxa_internacao_padronizada": np.linspace(10, 60, n),
        "prop_amputacao": np.linspace(0.01, 0.06, n),
        "letalidade": np.linspace(0.02, 0.12, n),
        "cobertura_aps": np.linspace(100, 50, n),
    }
    base.update(sobrescreve)
    return pd.DataFrame(base)


def test_winsorizacao_corta_os_extremos():
    s = pd.Series([1, 2, 3, 4, 1000])
    resultado = winsorizar(s, 0.0, 0.75)
    assert resultado.max() == 4.0


def test_normalizar_minmax_mapeia_para_zero_um():
    resultado = normalizar_minmax(pd.Series([10.0, 20.0, 30.0]))
    assert resultado.tolist() == [0.0, 0.5, 1.0]


def test_normalizar_serie_constante_levanta_erro():
    with pytest.raises(ValueError, match="constante"):
        normalizar_minmax(pd.Series([5.0, 5.0]))


def test_corte_marca_municipios_com_poucas_internacoes():
    df = pd.DataFrame({"internacoes": [5, 19, 20, 300]})
    resultado = aplicar_corte(df, corte=20)
    assert resultado["no_ranking"].tolist() == [False, False, True, True]


def test_icvd_fica_entre_zero_e_um():
    resultado = calcular_icvd(quadro())
    assert resultado["icvd"].between(0, 1).all()


def test_cobertura_aps_entra_invertida():
    # O município com MAIOR cobertura precisa ter o MENOR componente normalizado.
    resultado = calcular_icvd(quadro()).sort_values("cobertura_aps")
    assert resultado["cobertura_aps_norm"].iloc[-1] < (
        resultado["cobertura_aps_norm"].iloc[0]
    )


def test_pior_municipio_em_tudo_tem_icvd_um():
    resultado = calcular_icvd(quadro())
    pior = resultado.loc[resultado["taxa_internacao_padronizada"].idxmax()]
    assert pior["icvd"] == pytest.approx(1.0)


def test_escala_e_comum_aos_dois_periodos():
    # Se 2023-24 for uniformemente melhor que 2019, todo ICVD de 2023-24
    # precisa ficar abaixo — o que só acontece com escala compartilhada.
    base = quadro(periodo=PERIODO_BASE)
    atual = quadro(
        periodo=PERIODO_ATUAL,
        taxa_internacao_padronizada=np.linspace(5, 30, 6),
        prop_amputacao=np.linspace(0.005, 0.03, 6),
        letalidade=np.linspace(0.01, 0.06, 6),
        cobertura_aps=np.linspace(100, 80, 6),
    )
    resultado = calcular_icvd(pd.concat([base, atual], ignore_index=True))

    media_base = resultado.loc[resultado["periodo"] == PERIODO_BASE, "icvd"].mean()
    media_atual = resultado.loc[
        resultado["periodo"] == PERIODO_ATUAL, "icvd"
    ].mean()
    assert media_atual < media_base


def test_recuperacao_negativa_significa_melhora():
    base = quadro(periodo=PERIODO_BASE)
    atual = quadro(
        periodo=PERIODO_ATUAL,
        taxa_internacao_padronizada=np.linspace(5, 30, 6),
        prop_amputacao=np.linspace(0.005, 0.03, 6),
        letalidade=np.linspace(0.01, 0.06, 6),
        cobertura_aps=np.linspace(100, 80, 6),
    )
    icvd = calcular_icvd(pd.concat([base, atual], ignore_index=True))
    resultado = calcular_recuperacao(icvd)

    assert set(resultado.columns) == {
        "cod_municipio", "icvd_2019", "icvd_2023_24", "recuperacao",
    }
    assert (resultado["recuperacao"] < 0).all()


def test_pesos_alternativos_mudam_o_icvd():
    # Os componentes precisam ser NAO colineares. Quatro linspaces
    # monotonicos viram vetores identicos depois de normalizados, e a media
    # ponderada de vetores identicos ignora os pesos — o teste passaria a
    # ser impossivel de falhar por motivo errado.
    df = quadro(prop_amputacao=[0.06, 0.01, 0.05, 0.02, 0.04, 0.03])
    igual = calcular_icvd(df)["icvd"]
    pesado = calcular_icvd(
        df,
        pesos={
            "taxa_internacao_padronizada": 0.1,
            "prop_amputacao": 0.7,
            "letalidade": 0.1,
            "cobertura_aps": 0.1,
        },
    )["icvd"]
    assert not np.allclose(igual, pesado)


def test_pesos_que_nao_somam_um_levantam_erro():
    with pytest.raises(ValueError, match="somar 1"):
        calcular_icvd(
            quadro(),
            pesos={
                "taxa_internacao_padronizada": 0.5,
                "prop_amputacao": 0.5,
                "letalidade": 0.5,
                "cobertura_aps": 0.5,
            },
        )
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `pytest tests/test_indice.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.indice'`

- [ ] **Step 3: Implementar indice.py**

```python
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
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `pytest tests/test_indice.py`
Expected: PASS, 11 testes.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `pytest`
Expected: PASS — todos os testes verdes.

- [ ] **Step 6: Commit**

```bash
git add src/diabetes_sus/indice.py tests/test_indice.py
git commit -m "feat: indice ICVD com escala comum entre periodos e corte de ranking"
```

---

### Task 10: Validação do pipeline

**Files:**
- Create: `src/diabetes_sus/validacao.py`
- Test: `tests/test_validacao.py`

**Interfaces:**
- Consumes: nada
- Produces:
  - `validacao.verificar_completude(esperados: int, processados: int, tolerancia: float = 0.02) -> dict`
  - `validacao.verificar_denominadores(df: pd.DataFrame) -> pd.DataFrame` — devolve as linhas com internação e sem população
  - `validacao.verificar_sanidade(df: pd.DataFrame) -> None` — levanta `ValueError` na primeira violação
  - `validacao.comparar_com_tabnet(nosso: pd.DataFrame, tabnet: pd.DataFrame, tolerancia: float = 0.02) -> pd.DataFrame`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_validacao.py`:
```python
import pandas as pd
import pytest

from diabetes_sus.validacao import (
    comparar_com_tabnet,
    verificar_completude,
    verificar_denominadores,
    verificar_sanidade,
)


def test_completude_dentro_da_tolerancia():
    resultado = verificar_completude(1944, 1930)
    assert resultado["aprovado"] is True
    assert resultado["faltando"] == 14


def test_completude_abaixo_da_tolerancia_reprova():
    assert verificar_completude(1944, 1500)["aprovado"] is False


def test_denominadores_encontra_municipio_sem_populacao():
    df = pd.DataFrame(
        {
            "cod_municipio": ["3550308", "9999999"],
            "internacoes": [10, 5],
            "populacao": [1000.0, None],
        }
    )
    orfaos = verificar_denominadores(df)
    assert orfaos["cod_municipio"].tolist() == ["9999999"]


def test_denominador_zero_tambem_e_orfao():
    df = pd.DataFrame(
        {"cod_municipio": ["1"], "internacoes": [3], "populacao": [0.0]}
    )
    assert len(verificar_denominadores(df)) == 1


def test_sanidade_aceita_quadro_valido():
    df = pd.DataFrame(
        {"taxa_internacao_padronizada": [10.0], "icvd": [0.5], "letalidade": [0.1]}
    )
    verificar_sanidade(df)


def test_sanidade_rejeita_taxa_negativa():
    df = pd.DataFrame({"taxa_internacao_padronizada": [-1.0]})
    with pytest.raises(ValueError, match="negativ"):
        verificar_sanidade(df)


def test_sanidade_rejeita_icvd_fora_do_intervalo():
    df = pd.DataFrame({"icvd": [1.4]})
    with pytest.raises(ValueError, match="icvd"):
        verificar_sanidade(df)


def test_sanidade_rejeita_letalidade_acima_de_um():
    df = pd.DataFrame({"letalidade": [1.5]})
    with pytest.raises(ValueError, match="letalidade"):
        verificar_sanidade(df)


def test_comparacao_com_tabnet_sinaliza_divergencia():
    nosso = pd.DataFrame({"uf": ["SP", "CE"], "ano": [2023, 2023], "internacoes": [1000, 500]})
    tabnet = pd.DataFrame({"uf": ["SP", "CE"], "ano": [2023, 2023], "internacoes": [1005, 900]})
    resultado = comparar_com_tabnet(nosso, tabnet)

    assert resultado.loc[resultado["uf"] == "SP", "aprovado"].item() is True
    assert resultado.loc[resultado["uf"] == "CE", "aprovado"].item() is False
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `pytest tests/test_validacao.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'diabetes_sus.validacao'`

- [ ] **Step 3: Implementar validacao.py**

```python
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
    """Reconcilia nossos totais por UF e ano com os do TabNet."""
    juncao = nosso.merge(
        tabnet, on=["uf", "ano"], suffixes=("_nosso", "_tabnet")
    )
    juncao["diferenca"] = (
        juncao["internacoes_nosso"] - juncao["internacoes_tabnet"]
    )
    juncao["erro_relativo"] = (
        juncao["diferenca"].abs() / juncao["internacoes_tabnet"]
    )
    juncao["aprovado"] = juncao["erro_relativo"] <= tolerancia
    return juncao
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `pytest tests/test_validacao.py`
Expected: PASS, 9 testes.

- [ ] **Step 5: Extrair os totais de referência do TabNet**

No TabNet do SIH (`http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def`), gerar internações por UF e ano, filtrando CID-10 nas categorias E10 a E14. Salvar como `data/raw/tabnet_referencia.csv` com as colunas `uf`, `ano`, `internacoes`.

- [ ] **Step 6: Rodar a reconciliação sobre os dados reais**

```bash
python -c "
import pandas as pd, sys; sys.path.insert(0,'src')
from diabetes_sus.validacao import comparar_com_tabnet
g = pd.read_csv('data/gold/municipio_ano.csv', dtype={'cod_municipio':str})
nosso = g.groupby(['uf','ano'], as_index=False)['internacoes'].sum()
tabnet = pd.read_csv('data/raw/tabnet_referencia.csv')
r = comparar_com_tabnet(nosso, tabnet)
print(r[~r['aprovado']])
print('aprovados:', r['aprovado'].sum(), 'de', len(r))
"
```
Expected: todas as combinações UF-ano aprovadas. **Divergência acima de 2% bloqueia o avanço** — investigar filtro, AIH de continuação ou meses faltantes antes de seguir.

- [ ] **Step 7: Commit**

```bash
git add src/diabetes_sus/validacao.py tests/test_validacao.py data/raw/tabnet_referencia.csv
git commit -m "feat: validacao do pipeline e reconciliacao com o TabNet"
```

---

### Task 11: Notebook de EDA e consultas SQL

**Files:**
- Create: `notebooks/02_eda.ipynb`, `sql/consultas_duckdb.sql`
- Create (gerados): `docs/img/*.png`

**Interfaces:**
- Consumes: `data/gold/municipio_ano.csv`
- Produces: gráficos em `docs/img/` e os achados descritivos que alimentam `docs/04-conclusoes.md`

- [ ] **Step 1: Escrever as consultas SQL**

`sql/consultas_duckdb.sql`:
```sql
-- 1. Panorama nacional por ano
SELECT ano,
       SUM(internacoes)                                  AS internacoes,
       SUM(amputacoes)                                   AS amputacoes,
       SUM(obitos)                                       AS obitos,
       ROUND(SUM(val_total), 2)                          AS gasto_total,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2) AS pct_amputacao,
       ROUND(100.0 * SUM(obitos)     / SUM(internacoes), 2) AS letalidade
FROM gold
GROUP BY ano
ORDER BY ano;

-- 2. Taxa bruta por regiao e ano, por 100 mil habitantes
SELECT regiao, ano,
       SUM(internacoes)                                          AS internacoes,
       SUM(populacao)                                            AS populacao,
       ROUND(100000.0 * SUM(internacoes) / SUM(populacao), 1)    AS taxa_bruta
FROM gold
GROUP BY regiao, ano
ORDER BY regiao, ano;

-- 3. Efeito da pandemia: 2019 contra 2020-21 contra 2022-24
SELECT regiao,
       CASE WHEN ano = 2019 THEN '2019'
            WHEN ano IN (2020, 2021) THEN '2020-21'
            ELSE '2022-24' END                                   AS bloco,
       ROUND(100000.0 * SUM(internacoes) / SUM(populacao), 1)    AS taxa_bruta,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2)      AS pct_amputacao
FROM gold
GROUP BY regiao, bloco
ORDER BY regiao, bloco;

-- 4. Recorte de genero por regiao
SELECT regiao, sexo,
       SUM(internacoes)                                          AS internacoes,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2)      AS pct_amputacao,
       ROUND(100.0 * SUM(obitos)     / SUM(internacoes), 2)      AS letalidade
FROM gold
GROUP BY regiao, sexo
ORDER BY regiao, sexo;

-- 5. Municipios com mais amputacoes, respeitando o corte do ranking
SELECT cod_municipio, uf, regiao,
       SUM(internacoes) AS internacoes,
       SUM(amputacoes)  AS amputacoes,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2) AS pct_amputacao
FROM gold
GROUP BY cod_municipio, uf, regiao
HAVING SUM(internacoes) >= 20
ORDER BY pct_amputacao DESC
LIMIT 50;
```

- [ ] **Step 2: Célula de carga do notebook**

```python
import sys; sys.path.insert(0, '../src')
import duckdb, pandas as pd, matplotlib.pyplot as plt, seaborn as sns

sns.set_theme(style='whitegrid')
con = duckdb.connect()
con.execute("""
    CREATE VIEW gold AS
    SELECT * FROM read_csv_auto('../data/gold/municipio_ano.csv',
                                types={'cod_municipio': 'VARCHAR'})
""")
con.execute(open('../sql/consultas_duckdb.sql').read().split(';')[0]).df()
```

- [ ] **Step 3: Célula do panorama e da série temporal**

Executar a consulta 1 e plotar internações por ano com a faixa 2020–21 sombreada:

```python
serie = con.execute("SELECT ano, SUM(internacoes) i FROM gold GROUP BY ano ORDER BY ano").df()
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(serie['ano'], serie['i'], marker='o', linewidth=2)
ax.axvspan(2019.5, 2021.5, alpha=0.15, color='crimson')
ax.annotate('pandemia', xy=(2020.5, serie['i'].max()), ha='center')
ax.set_xlabel('ano'); ax.set_ylabel('internações por diabetes')
ax.set_title('Internações por diabetes no SUS, 2019–2024')
fig.tight_layout(); fig.savefig('../docs/img/serie_nacional.png', dpi=150)
```

- [ ] **Step 4: Células de distribuição, região e correlação**

Gerar e salvar em `docs/img/`: histograma da taxa bruta municipal, boxplot da taxa por região, barras dos três blocos temporais, dispersão cobertura de APS contra taxa de internação, e a matriz de correlação entre os quatro componentes. Cada célula termina com `fig.savefig(...)`.

- [ ] **Step 5: Célula de verificação de sanidade**

```python
from diabetes_sus.validacao import verificar_denominadores, verificar_sanidade
g = con.execute('SELECT * FROM gold').df()
orfaos = verificar_denominadores(g)
print(f'orfaos: {len(orfaos)} linhas')
verificar_sanidade(g)
print('sanidade OK')
```

- [ ] **Step 6: Commit**

```bash
git add notebooks/02_eda.ipynb sql/consultas_duckdb.sql docs/img
git commit -m "feat: EDA em DuckDB e pandas com graficos exportados"
```

---

### Task 12: Notebook do ICVD, gênero e sensibilidade

**Files:**
- Create: `notebooks/03_indice_icvd.ipynb`
- Create (gerados): `data/gold/icvd_municipio.csv`, `data/gold/icvd_regiao.csv`, `data/gold/genero_regiao.csv`

**Interfaces:**
- Consumes: `padronizacao.padronizar_por_municipio`, `indice.*`, `validacao.verificar_sanidade`
- Produces:
  - `icvd_municipio.csv`: `cod_municipio`, `uf`, `regiao`, `icvd_2019`, `icvd_2023_24`, `recuperacao`, `no_ranking`, e os quatro componentes de cada período
  - `icvd_regiao.csv`: `regiao`, `periodo`, quatro componentes agregados e `icvd_regional`
  - `genero_regiao.csv`: `regiao`, `sexo`, `taxa_padronizada`, `pct_amputacao`, `letalidade`, `idade_media`

**Refinamento em relação ao spec:** o ICVD regional é calculado a partir dos numeradores e denominadores **somados de todos os 5.570 municípios**, normalizado na mesma escala municipal. Fazer a média dos ICVDs municipais reintroduziria justamente o viés de composição que a Seção 3.5 do spec quis eliminar, porque o corte remove proporcionalmente mais municípios do Sul.

- [ ] **Step 1: Célula de montagem dos componentes por período**

```python
import sys; sys.path.insert(0, '../src')
import pandas as pd
from diabetes_sus.config import ANOS_ATUAIS, ANO_BASELINE, PERIODO_ATUAL, PERIODO_BASE
from diabetes_sus.padronizacao import padronizar_por_municipio

g = pd.read_csv('../data/gold/municipio_ano.csv', dtype={'cod_municipio': str})
pop = pd.read_parquet('../data/gold/populacao_municipio_faixa_sexo.parquet')
pop_padrao = pop.groupby('faixa_etaria', observed=True)['populacao'].sum()

def componentes(df):
    por_faixa = df.groupby(['cod_municipio', 'faixa_etaria'], as_index=False, observed=True).agg(
        internacoes=('internacoes', 'sum'), populacao=('populacao', 'sum'))
    taxas = padronizar_por_municipio(por_faixa, pop_padrao)
    totais = df.groupby('cod_municipio', as_index=False).agg(
        internacoes=('internacoes', 'sum'), amputacoes=('amputacoes', 'sum'),
        obitos=('obitos', 'sum'), cobertura_aps=('cobertura_aps', 'mean'),
        uf=('uf', 'first'), regiao=('regiao', 'first'))
    out = totais.merge(taxas, on='cod_municipio')
    out['prop_amputacao'] = out['amputacoes'] / out['internacoes']
    out['letalidade'] = out['obitos'] / out['internacoes']
    return out

base = componentes(g[g['ano'] == ANO_BASELINE]).assign(periodo=PERIODO_BASE)
atual = componentes(g[g['ano'].isin(ANOS_ATUAIS)]).assign(periodo=PERIODO_ATUAL)
empilhado = pd.concat([base, atual], ignore_index=True)
print(empilhado['periodo'].value_counts())
```

- [ ] **Step 2: Célula do ICVD e do corte**

```python
from diabetes_sus.indice import aplicar_corte, calcular_icvd, calcular_recuperacao
from diabetes_sus.validacao import verificar_sanidade

comum = aplicar_corte(empilhado)
ranqueaveis = comum[comum['no_ranking']].dropna(subset=['cobertura_aps'])

# Municipios presentes nos DOIS periodos — exigencia do indicador de recuperacao.
nos_dois = ranqueaveis.groupby('cod_municipio')['periodo'].nunique() == 2
ranqueaveis = ranqueaveis[ranqueaveis['cod_municipio'].isin(nos_dois[nos_dois].index)]

icvd = calcular_icvd(ranqueaveis)
verificar_sanidade(icvd)
recup = calcular_recuperacao(icvd)
print(f'municipios no ranking: {len(recup)} de 5570')
print(recup['recuperacao'].describe())
```

- [ ] **Step 3: Célula da análise de sensibilidade**

```python
from scipy.stats import spearmanr

ESQUEMAS = {
    'iguais':      {'taxa_internacao_padronizada':.25,'prop_amputacao':.25,'letalidade':.25,'cobertura_aps':.25},
    'desfecho':    {'taxa_internacao_padronizada':.20,'prop_amputacao':.40,'letalidade':.30,'cobertura_aps':.10},
    'estrutural':  {'taxa_internacao_padronizada':.30,'prop_amputacao':.15,'letalidade':.15,'cobertura_aps':.40},
    'acesso':      {'taxa_internacao_padronizada':.40,'prop_amputacao':.20,'letalidade':.20,'cobertura_aps':.20},
}

atual_only = icvd[icvd['periodo'] == PERIODO_ATUAL]
referencia = calcular_icvd(atual_only, ESQUEMAS['iguais']).set_index('cod_municipio')['icvd']
top_ref = set(referencia.nlargest(100).index)

for nome, pesos in ESQUEMAS.items():
    alt = calcular_icvd(atual_only, pesos).set_index('cod_municipio')['icvd']
    rho = spearmanr(referencia, alt.reindex(referencia.index)).statistic
    sobreposicao = len(top_ref & set(alt.nlargest(100).index))
    print(f'{nome:12} spearman={rho:.3f}  top100 em comum={sobreposicao}%')
```

**Critério:** sobreposição do top-100 acima de 80% e Spearman acima de 0,9 tornam o índice defensável. Abaixo disso, reportar ao autor antes de seguir — o índice precisa ser revisto.

- [ ] **Step 4: Célula do ICVD regional sem viés de composição**

```python
def componentes_regionais(df):
    por_faixa = df.groupby(['regiao','faixa_etaria'], as_index=False, observed=True).agg(
        internacoes=('internacoes','sum'), populacao=('populacao','sum'))
    por_faixa = por_faixa.rename(columns={'regiao':'cod_municipio'})
    taxas = padronizar_por_municipio(por_faixa, pop_padrao).rename(
        columns={'cod_municipio':'regiao'})
    tot = df.groupby('regiao', as_index=False).agg(
        internacoes=('internacoes','sum'), amputacoes=('amputacoes','sum'),
        obitos=('obitos','sum'),
        cobertura_aps=('cobertura_aps','mean'))
    out = tot.merge(taxas, on='regiao')
    out['prop_amputacao'] = out['amputacoes']/out['internacoes']
    out['letalidade'] = out['obitos']/out['internacoes']
    return out

reg = pd.concat([
    componentes_regionais(g[g['ano'] == ANO_BASELINE]).assign(periodo=PERIODO_BASE),
    componentes_regionais(g[g['ano'].isin(ANOS_ATUAIS)]).assign(periodo=PERIODO_ATUAL),
], ignore_index=True)
reg.to_csv('../data/gold/icvd_regiao.csv', index=False)
reg
```

- [ ] **Step 5: Célula da trilha de gênero**

```python
def por_sexo(df):
    por_faixa = df.groupby(['regiao','sexo','faixa_etaria'], as_index=False, observed=True).agg(
        internacoes=('internacoes','sum'), populacao=('populacao','sum'))
    por_faixa['chave'] = por_faixa['regiao'] + '|' + por_faixa['sexo']
    taxas = padronizar_por_municipio(
        por_faixa.rename(columns={'chave':'cod_municipio'}), pop_padrao)
    taxas[['regiao','sexo']] = taxas['cod_municipio'].str.split('|', expand=True)
    tot = df.groupby(['regiao','sexo'], as_index=False).agg(
        internacoes=('internacoes','sum'), amputacoes=('amputacoes','sum'),
        obitos=('obitos','sum'))
    out = tot.merge(taxas.drop(columns='cod_municipio'), on=['regiao','sexo'])
    out['pct_amputacao'] = 100*out['amputacoes']/out['internacoes']
    out['letalidade'] = 100*out['obitos']/out['internacoes']
    return out

genero = por_sexo(g[g['ano'].isin(ANOS_ATUAIS)])
genero.to_csv('../data/gold/genero_regiao.csv', index=False)
genero
```

**Teste da hipótese:** ela se sustenta se, nas cinco regiões, homens apresentarem `pct_amputacao` e `letalidade` maiores que mulheres enquanto a taxa padronizada de internação for semelhante. Confirmada ou refutada, o resultado entra em `docs/04-conclusoes.md` com estes números.

- [ ] **Step 6: Célula de exportação da tabela municipal**

```python
larga = (icvd.pivot_table(index=['cod_municipio','uf','regiao'], columns='periodo',
                          values=['icvd','taxa_internacao_padronizada',
                                  'prop_amputacao','letalidade','cobertura_aps'])
         .reset_index())
larga.columns = ['_'.join(c).strip('_').replace('-','_') for c in larga.columns]
larga = larga.merge(recup[['cod_municipio','recuperacao']], on='cod_municipio')
larga.to_csv('../data/gold/icvd_municipio.csv', index=False)
print(larga.shape)
```

- [ ] **Step 7: Commit**

```bash
git add notebooks/03_indice_icvd.ipynb data/gold/icvd_municipio.csv data/gold/icvd_regiao.csv data/gold/genero_regiao.csv
git commit -m "feat: ICVD municipal e regional, trilha de genero e sensibilidade dos pesos"
```

---

### Task 13: Publicação no Google Sheets

**Files:**
- Create: `docs/02-coleta-de-dados.md` (seção sobre a publicação)

**Interfaces:**
- Consumes: `data/gold/*.csv`
- Produces: planilha Google com as abas `municipio_ano`, `icvd_municipio`, `icvd_regiao`, `genero_regiao`

- [ ] **Step 1: Criar a planilha**

Criar uma planilha no Google Sheets chamada `diabetes_sus_gold` e importar cada CSV como uma aba (Arquivo → Importar → Inserir nova página).

- [ ] **Step 2: Publicar as abas**

Arquivo → Compartilhar → Publicar na web, selecionando cada aba no formato CSV. Guardar as URLs.

- [ ] **Step 3: Conferir o acesso anônimo**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "<URL_PUBLICADA_municipio_ano>"
```
Expected: `200`.

- [ ] **Step 4: Registrar as URLs**

Anotar as URLs publicadas em `docs/02-coleta-de-dados.md`, numa seção "Camada gold publicada".

- [ ] **Step 5: Commit**

```bash
git add docs/02-coleta-de-dados.md
git commit -m "docs: publicacao da camada gold no Google Sheets"
```

---

### Task 14: Dashboard no Power BI

**Files:**
- Create: `dashboard/diabetes_sus.pbix`, `dashboard/dashboard.pdf`, `dashboard/previews/pagina1.png`, `pagina2.png`, `pagina3.png`

**Interfaces:**
- Consumes: as abas publicadas do Google Sheets e, como fonte redundante, os CSVs em `data/gold/`
- Produces: os três arquivos de entrega visual

**Decisão sobre o mapa:** o mapa coroplético usa **UF**, não município. O visual Shape Map do Power BI exige TopoJSON e não sustenta 5.570 polígonos de forma confiável. A granularidade municipal aparece na dispersão e nas tabelas de ranking, que é onde ela realmente informa. Trata-se de um ajuste em relação à Seção 4.2 do spec, motivado por limitação da ferramenta.

- [ ] **Step 1: Conectar as fontes**

Obter Dados → Web, colando cada URL publicada. Renomear as consultas para `municipio_ano`, `icvd_municipio`, `icvd_regiao`, `genero_regiao`.

- [ ] **Step 2: Criar as medidas DAX**

```
Internações = SUM(municipio_ano[internacoes])
Amputações  = SUM(municipio_ano[amputacoes])
Óbitos      = SUM(municipio_ano[obitos])
Gasto SUS   = SUM(municipio_ano[val_total])

% Amputação = DIVIDE([Amputações], [Internações])
Letalidade  = DIVIDE([Óbitos], [Internações])
Taxa Bruta 100k = DIVIDE([Internações], SUM(municipio_ano[populacao])) * 100000

ICVD Atual   = AVERAGE(icvd_municipio[icvd_2023_24])
ICVD Base    = AVERAGE(icvd_municipio[icvd_2019])
Recuperação  = [ICVD Atual] - [ICVD Base]

Municípios no Ranking = DISTINCTCOUNT(icvd_municipio[cod_municipio])
```

- [ ] **Step 3: Montar a Página 1 — Panorama Brasil**

Quatro cartões no topo (`Internações`, `Amputações`, `Óbitos`, `Gasto SUS`); gráfico de linhas de `Internações` por ano com uma linha de referência marcando 2020–21; mapa preenchido de `Taxa Bruta 100k` por UF; segmentações de Região, UF, Ano, Sexo e Faixa Etária.

- [ ] **Step 4: Montar a Página 2 — Desigualdade e recuperação**

Dispersão com `icvd_2019` no eixo X e `icvd_2023_24` no eixo Y, um ponto por município, cor por região, e uma linha de referência na diagonal (acima dela significa piora); barras agrupadas de `icvd_regional` por região comparando os dois períodos, vindas de `icvd_regiao`; dispersão de `cobertura_aps` contra `taxa_internacao_padronizada`; duas tabelas com o top-20 de maior `icvd_2023_24` e o top-20 de `recuperacao` mais negativa.

- [ ] **Step 5: Montar a Página 3 — Recorte de gênero**

Barras agrupadas de taxa padronizada por região e sexo; barras de `pct_amputacao` por região e sexo; barras de `letalidade` por região e sexo; uma caixa de texto com a conclusão do teste da hipótese e os números que a sustentam.

- [ ] **Step 6: Exportar as evidências**

Arquivo → Exportar → PDF, salvando em `dashboard/dashboard.pdf`. Capturar cada página como PNG em `dashboard/previews/`.

- [ ] **Step 7: Commit**

```bash
git add dashboard/
git commit -m "feat: dashboard Power BI com panorama, desigualdade e recorte de genero"
```

---

### Task 15: Documentação e README

**Files:**
- Create: `README.md`, `docs/01-problema.md`, `docs/03-modelagem.md`, `docs/04-conclusoes.md`
- Modify: `docs/02-coleta-de-dados.md`

**Interfaces:**
- Consumes: spec, resultados das Tasks 11–12, imagens das Tasks 11 e 14
- Produces: os entregáveis textuais exigidos pelo briefing

- [ ] **Step 1: Escrever docs/01-problema.md**

Adaptar a Seção 1 do spec: descrição do problema, relevância social, por que a análise de dados ajuda, e o eixo "choque e recuperação desigual". Prosa corrida, sem listas de tópicos soltos.

- [ ] **Step 2: Completar docs/02-coleta-de-dados.md**

Adaptar a Seção 2 do spec: tabela de fontes com URLs, tipo de dado, método de acesso; o filtro de seleção e sua consequência declarada; a restrição do `.dbc` e a decisão pelo Colab; as URLs do Sheets da Task 13.

- [ ] **Step 3: Escrever docs/03-modelagem.md**

Adaptar a Seção 3 do spec: arquitetura em camadas, limpeza, padronização etária com a fórmula, os quatro componentes e a justificativa dos pesos iguais, o problema dos números pequenos com as duas tabelas de impacto do corte, a escala comum entre períodos, e o resultado real da análise de sensibilidade obtido na Task 12.

- [ ] **Step 4: Escrever docs/04-conclusoes.md**

Com os números reais: os cinco a sete achados principais, o resultado do teste da hipótese de gênero, a lista de municípios prioritários, as recomendações de ação decorrentes, e uma seção de limitações que declare a subestimação de amputações pelo filtro simples, a variação de codificação entre regiões e o IDHM defasado.

- [ ] **Step 5: Escrever o README.md**

```markdown
# Desigualdade Regional no Cuidado ao Diabetes no SUS

Análise de 5.570 municípios brasileiros entre 2019 e 2024, medindo se o SUS
entrega o mesmo cuidado ao diabético em todo o território — e quem paga a
conta onde não entrega.

![Panorama](dashboard/previews/pagina1.png)

## Principais achados

<!-- preencher com os 3 achados mais fortes da Task 12 -->

## Documentação

- [Problema e justificativa](docs/01-problema.md)
- [Coleta de dados](docs/02-coleta-de-dados.md)
- [Modelagem](docs/03-modelagem.md)
- [Conclusões](docs/04-conclusoes.md)

## Como reproduzir

1. `pip install -r requirements.txt`
2. `python scripts/baixar_populacao_ibge.py`
3. Abrir `notebooks/01_ingestao_colab.ipynb` no Google Colab e executar
4. Baixar a camada gold para `data/gold/`
5. `pytest` para conferir os módulos de cálculo
6. Executar `notebooks/02_eda.ipynb` e `notebooks/03_indice_icvd.ipynb`
7. Abrir `dashboard/diabetes_sus.pbix` no Power BI Desktop

## Stack

Python · pandas · DuckDB · PySpark (Colab) · pytest · Power BI · Google Sheets
```

Substituir o comentário do bloco "Principais achados" pelos três achados reais antes do commit final — um README com comentário de preenchimento é entrega incompleta.

- [ ] **Step 6: Rodar a suíte completa**

Run: `pytest`
Expected: todos os testes PASS.

- [ ] **Step 7: Commit final e push**

```bash
git add README.md docs/
git commit -m "docs: problema, coleta, modelagem e conclusoes do projeto"
git remote add origin https://github.com/<usuario>/projeto-diabetes-sus.git
git push -u origin main
```

---

## Self-Review

**Cobertura do spec:**

| Seção do spec | Tarefa |
|---|---|
| 1. O problema | 15 |
| 2.1–2.2 Fontes | 5, 6, 7, 15 |
| 2.3 Filtro de seleção | 4 |
| 2.4 Restrição do `.dbc` | 6 |
| 3.1 Arquitetura do pipeline | 6, 7 |
| 3.2 Limpeza | 2, 3, 4, 7 |
| 3.3 Padronização etária | 8 |
| 3.4 Componentes e pesos | 2, 9 |
| 3.5 Números pequenos e corte | 9, 12 |
| 3.6 Escala comum e recuperação | 9 |
| 3.7 Sensibilidade | 12 |
| 3.8 Trilha de gênero | 12 |
| 3.9 Validação | 10 |
| 4.1–4.2 Dashboard | 14 |
| 4.3 Fluxo até o Power BI | 13 |
| 4.4 Estrutura do repositório | 1, 15 |
| 5. Mapa de entregáveis | 15 |

Sem lacunas.

**Consistência de tipos:** `cod_municipio` é string de 7 dígitos em toda a cadeia, a partir da Task 3. `periodo` usa os literais `config.PERIODO_BASE` e `config.PERIODO_ATUAL` nas Tasks 9 e 12. Os nomes dos quatro componentes vêm de `config.COMPONENTES_ICVD` e são idênticos nas Tasks 2, 9, 10, 12 e 14.

**Desvios do spec registrados no plano:** ICVD regional calculado por agregação em vez de média dos municipais (Task 12) e mapa por UF em vez de município (Task 14). Ambos justificados no ponto onde aparecem.
