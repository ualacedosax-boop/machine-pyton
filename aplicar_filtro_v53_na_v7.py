import os
import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

# Pasta correta da V5.3 oficial
PASTA_V53 = BASE_DIR / "saida_v5_3_validacao_2025_teste_2026"
ARQUIVO_V53_2025 = PASTA_V53 / "05_predicoes_validacao_2025_v5_3.csv.gz"
ARQUIVO_V53_2026 = PASTA_V53 / "06_predicoes_teste_2026_v5_3.csv.gz"

# Pasta da V7
PASTA_V7 = BASE_DIR / "saida_v7_v51_filtro_v55_gestao_dia"

# Se você souber o arquivo exato de trades da V7, coloque aqui.
# Se deixar None, o script tenta localizar dentro da pasta da V7.
ARQUIVO_V7_TRADES = None

# MODO:
# "2025"  = usa somente V5.3 2025
# "2026"  = usa somente V5.3 2026
# "AMBOS" = usa V5.3 2025 + 2026
MODO_V53 = "AMBOS"

# Tolerância para casar sinal V7 com sinal aceito pela V5.3.
# 0 = precisa ser exatamente mesmo horário.
# 2 = permite até 2 minutos de diferença.
TOLERANCIA_MINUTOS = 2

VALOR_POR_PONTO_NQ = 20.0

DATA_EXECUCAO = datetime.now().strftime("%Y%m%d_%H%M%S")

PASTA_SAIDA = BASE_DIR / "saida_v7_1_com_filtro_v53" / f"rodada_{DATA_EXECUCAO}"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_CONFIG = PASTA_SAIDA / "00_config_execucao.json"
ARQ_V53_OFICIAL = PASTA_SAIDA / "01_v53_oficial_aceitos.csv.gz"
ARQ_V7_ORIGINAL_NORMALIZADO = PASTA_SAIDA / "02_v7_original_normalizado.csv.gz"
ARQ_V71_FILTRADO = PASTA_SAIDA / "03_v7_1_filtrado_v53.csv.gz"

ARQ_RESUMO_V7 = PASTA_SAIDA / "04_resumo_v7_original.csv"
ARQ_RESUMO_V71 = PASTA_SAIDA / "05_resumo_v7_1_filtrado_v53.csv"
ARQ_COMPARATIVO = PASTA_SAIDA / "06_comparativo_v7_vs_v7_1.csv"

ARQ_MENSAL_V7 = PASTA_SAIDA / "07_mensal_v7_original.csv"
ARQ_MENSAL_V71 = PASTA_SAIDA / "08_mensal_v7_1_filtrado_v53.csv"

ARQ_ROTACAO_V7 = PASTA_SAIDA / "09_rotacao_v7_original.csv"
ARQ_ROTACAO_V71 = PASTA_SAIDA / "10_rotacao_v7_1_filtrado_v53.csv"

ARQ_HORARIO_V7 = PASTA_SAIDA / "11_horario_v7_original.csv"
ARQ_HORARIO_V71 = PASTA_SAIDA / "12_horario_v7_1_filtrado_v53.csv"

ARQ_RELATORIO = PASTA_SAIDA / "13_relatorio_v7_1_filtro_v53.txt"


# ============================================================
# ROTAÇÕES
# ============================================================

ROTACOES = {
    "ROTACAO_A": [3, 6, 9, 12],
    "ROTACAO_B": [2, 5, 8, 11],
    "ROTACAO_C": [1, 4, 7, 10],
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def barra(iteravel, desc="Processando"):
    if tqdm is not None:
        return tqdm(iteravel, desc=desc, unit="item")
    return iteravel


def ler_csv(caminho: Path) -> pd.DataFrame:
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if str(caminho).lower().endswith(".gz"):
        return pd.read_csv(caminho, compression="gzip")

    return pd.read_csv(caminho)


def salvar_config():
    config = {
        "base_dir": str(BASE_DIR),
        "pasta_v53": str(PASTA_V53),
        "arquivo_v53_2025": str(ARQUIVO_V53_2025),
        "arquivo_v53_2026": str(ARQUIVO_V53_2026),
        "pasta_v7": str(PASTA_V7),
        "arquivo_v7_trades": str(ARQUIVO_V7_TRADES) if ARQUIVO_V7_TRADES else None,
        "modo_v53": MODO_V53,
        "tolerancia_minutos": TOLERANCIA_MINUTOS,
        "valor_por_ponto_nq": VALOR_POR_PONTO_NQ,
        "pasta_saida": str(PASTA_SAIDA),
        "data_execucao": DATA_EXECUCAO,
        "observacao": (
            "V7.1 = V7 filtrada pela V5.3 oficial. "
            "Mantém trade da V7 somente se a V5.3 também aceitou sinal "
            "com mesma direção e horário próximo."
        ),
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def achar_coluna(df, nomes_exatos=None, contem=None):
    nomes_exatos = nomes_exatos or []
    contem = contem or []

    mapa = {str(c).lower(): c for c in df.columns}

    for nome in nomes_exatos:
        if nome.lower() in mapa:
            return mapa[nome.lower()]

    for c in df.columns:
        cl = str(c).lower()
        if any(x.lower() in cl for x in contem):
            return c

    return None


def transformar_bool(serie: pd.Series) -> pd.Series:
    s = serie.astype(str).str.strip().str.upper()

    return s.isin([
        "TRUE",
        "1",
        "SIM",
        "YES",
        "S",
        "VERDADEIRO",
        "V",
    ])


def definir_rotacao(mes: int) -> str:
    for nome, meses in ROTACOES.items():
        if int(mes) in meses:
            return nome
    return "SEM_ROTACAO"


# ============================================================
# V5.3 OFICIAL
# ============================================================

def carregar_v53_oficial() -> pd.DataFrame:
    arquivos = []

    modo = MODO_V53.upper().strip()

    if modo == "2025":
        arquivos.append(("V53_2025", ARQUIVO_V53_2025))
    elif modo == "2026":
        arquivos.append(("V53_2026", ARQUIVO_V53_2026))
    elif modo == "AMBOS":
        arquivos.append(("V53_2025", ARQUIVO_V53_2025))
        arquivos.append(("V53_2026", ARQUIVO_V53_2026))
    else:
        raise ValueError("MODO_V53 inválido. Use 2025, 2026 ou AMBOS.")

    dfs = []

    for fonte, caminho in arquivos:
        print(f"\nLendo V5.3 {fonte}:")
        print(caminho)

        df = ler_csv(caminho)
        df["Fonte_V53"] = fonte

        if "aceito_v5_3" not in df.columns:
            raise ValueError(f"Arquivo V5.3 sem coluna aceito_v5_3: {caminho}")

        if "pontos_v5" not in df.columns:
            raise ValueError(f"Arquivo V5.3 sem coluna pontos_v5: {caminho}")

        if "DataHora_SP" not in df.columns:
            raise ValueError(f"Arquivo V5.3 sem coluna DataHora_SP: {caminho}")

        if "Direcao" not in df.columns:
            raise ValueError(f"Arquivo V5.3 sem coluna Direcao: {caminho}")

        print("Linhas:", len(df))
        print("Distribuição aceito_v5_3:")
        print(df["aceito_v5_3"].value_counts(dropna=False))

        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)

    df["aceito_v5_3_bool"] = transformar_bool(df["aceito_v5_3"])

    df = df[df["aceito_v5_3_bool"]].copy()

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()

    df["Direcao"] = df["Direcao"].astype(str).str.upper()
    df["pontos_v5"] = pd.to_numeric(df["pontos_v5"], errors="coerce")
    df["prob_v5_3"] = pd.to_numeric(df.get("prob_v5_3", np.nan), errors="coerce")

    df = df.dropna(subset=["pontos_v5"]).copy()
    df = df[df["pontos_v5"] != 0].copy()

    df["Data"] = df["DataHora_SP"].dt.date
    df["Ano"] = df["DataHora_SP"].dt.year
    df["Mes"] = df["DataHora_SP"].dt.month
    df["AnoMes"] = df["DataHora_SP"].dt.strftime("%Y-%m")
    df["Hora"] = df["DataHora_SP"].dt.hour
    df["Minuto"] = df["DataHora_SP"].dt.minute
    df["Rotacao"] = df["Mes"].apply(definir_rotacao)

    out = df[
        [
            "Fonte_V53",
            "DataHora_SP",
            "Direcao",
            "pontos_v5",
            "prob_v5_3",
            "Data",
            "Ano",
            "Mes",
            "AnoMes",
            "Hora",
            "Minuto",
            "Rotacao",
        ]
    ].copy()

    out = out.sort_values("DataHora_SP").reset_index(drop=True)

    print("\nV5.3 oficial carregada:")
    print("Trades aceitos:", len(out))
    print("Período:", out["DataHora_SP"].min(), "até", out["DataHora_SP"].max())

    return out


# ============================================================
# LOCALIZAR E NORMALIZAR V7
# ============================================================

def listar_arquivos_v7():
    if not PASTA_V7.exists():
        raise FileNotFoundError(f"Pasta V7 não encontrada: {PASTA_V7}")

    arquivos = []

    for root, dirs, files in os.walk(PASTA_V7):
        root_path = Path(root)

        for f in files:
            p = root_path / f
            nome = p.name.lower()

            if nome.endswith(".csv") or nome.endswith(".csv.gz"):
                try:
                    tamanho = p.stat().st_size
                    modificado = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    tamanho = 0
                    modificado = ""

                arquivos.append({
                    "arquivo": p,
                    "nome": p.name,
                    "tamanho": tamanho,
                    "modificado": modificado,
                })

    arquivos = sorted(arquivos, key=lambda x: x["modificado"], reverse=True)

    return arquivos


def escolher_arquivo_v7():
    if ARQUIVO_V7_TRADES is not None:
        return Path(ARQUIVO_V7_TRADES)

    print("\nProcurando arquivo de trades da V7 dentro da pasta:")
    print(PASTA_V7)

    arquivos = listar_arquivos_v7()

    if not arquivos:
        raise FileNotFoundError("Nenhum CSV encontrado na pasta da V7.")

    print("\nArquivos encontrados na pasta V7:")
    for i, item in enumerate(arquivos, start=1):
        print(f"{i:02d}. {item['arquivo']} | tamanho={item['tamanho']} | modificado={item['modificado']}")

    candidatos = []

    for item in barra(arquivos, desc="Testando arquivos V7"):
        p = item["arquivo"]

        try:
            df = ler_csv(p)
        except Exception:
            continue

        cols_lower = [str(c).lower() for c in df.columns]

        tem_data = any(
            x in cols_lower
            for x in [
                "datahora_sp",
                "datahora_sinal_sp",
                "dt_entrada",
                "datahora",
                "datetime",
            ]
        ) or any("datahora" in x for x in cols_lower)

        tem_direcao = any(
            x in cols_lower
            for x in ["direcao", "direction", "sinal", "side"]
        ) or any("direcao" in x for x in cols_lower)

        tem_pontos = any(
            x in cols_lower
            for x in [
                "pontos",
                "pontos_v7",
                "pontos_stop_117_0",
                "lucro_pontos",
                "profit",
                "pnl",
            ]
        ) or any("pontos" in x or "profit" in x or "lucro" in x or "pnl" in x for x in cols_lower)

        tem_resultado = any(
            x in cols_lower
            for x in [
                "resultado",
                "resultado_stop_117_0",
                "target_win",
                "target",
                "win",
            ]
        ) or any("resultado" in x or "target" in x for x in cols_lower)

        score = 0
        if tem_data:
            score += 2
        if tem_direcao:
            score += 2
        if tem_pontos:
            score += 2
        if tem_resultado:
            score += 1
        if len(df) > 20:
            score += 1

        if score >= 5:
            candidatos.append((score, len(df), p, list(df.columns)))

    if not candidatos:
        print("\nNão consegui identificar automaticamente o arquivo de trades da V7.")
        print("Coloque o caminho manualmente na variável ARQUIVO_V7_TRADES.")
        raise FileNotFoundError("Arquivo de trades da V7 não identificado.")

    candidatos = sorted(candidatos, key=lambda x: (x[0], x[1]), reverse=True)

    score, linhas, arquivo, colunas = candidatos[0]

    print("\nArquivo V7 escolhido automaticamente:")
    print(arquivo)
    print("Score:", score)
    print("Linhas:", linhas)
    print("Colunas:")
    print(colunas)

    return arquivo


def normalizar_v7(df: pd.DataFrame, arquivo_origem: Path) -> pd.DataFrame:
    df = df.copy()

    col_data = achar_coluna(
        df,
        nomes_exatos=[
            "DataHora_SP",
            "DataHora_Sinal_SP",
            "dt_entrada",
            "DataHora",
            "datetime",
        ],
        contem=[
            "datahora_sp",
            "datahora_sinal",
            "dt_entrada",
            "datahora",
            "datetime",
        ],
    )

    col_direcao = achar_coluna(
        df,
        nomes_exatos=[
            "Direcao",
            "direcao",
            "direction",
            "sinal",
            "side",
        ],
        contem=[
            "direcao",
            "direction",
            "sinal",
            "side",
        ],
    )

    col_pontos = achar_coluna(
        df,
        nomes_exatos=[
            "pontos_v7",
            "pontos",
            "pontos_stop_117_0",
            "lucro_pontos",
            "profit_points",
            "pnl_pontos",
            "pnl",
            "profit",
            "lucro",
        ],
        contem=[
            "pontos",
            "profit",
            "lucro",
            "pnl",
        ],
    )

    col_resultado = achar_coluna(
        df,
        nomes_exatos=[
            "resultado",
            "resultado_stop_117_0",
            "target_win",
            "target",
            "win_loss",
        ],
        contem=[
            "resultado",
            "target",
            "win_loss",
        ],
    )

    if col_data is None:
        raise ValueError("Não encontrei coluna de data na V7.")

    if col_direcao is None:
        raise ValueError("Não encontrei coluna de direção na V7.")

    if col_pontos is None and col_resultado is None:
        raise ValueError("Não encontrei coluna de pontos nem resultado na V7.")

    out = pd.DataFrame()
    out["Arquivo_Origem_V7"] = str(arquivo_origem)
    out["DataHora_SP"] = pd.to_datetime(df[col_data], errors="coerce")
    out["Direcao"] = df[col_direcao].astype(str).str.upper()

    if col_pontos is not None:
        out["Pontos"] = pd.to_numeric(df[col_pontos], errors="coerce")
    else:
        out["Pontos"] = np.nan

    if col_resultado is not None:
        resultado_raw = df[col_resultado].astype(str).str.upper()
    else:
        resultado_raw = pd.Series([""] * len(df), index=df.index)

    resultado = []

    for txt, pts in zip(resultado_raw, out["Pontos"]):
        txt = str(txt).upper()

        if "WIN" in txt or "GAIN" in txt or "TAKE" in txt or "TP" in txt:
            resultado.append("WIN")
        elif "LOSS" in txt or "STOP" in txt or "SL" in txt:
            resultado.append("LOSS")
        elif pd.notna(pts) and pts > 0:
            resultado.append("WIN")
        elif pd.notna(pts) and pts < 0:
            resultado.append("LOSS")
        else:
            resultado.append("NEUTRO")

    out["Resultado"] = resultado

    # Copia colunas úteis se existirem
    colunas_uteis = [
        "prob_v7",
        "prob_win_v7",
        "prob_win",
        "prob_v5_1",
        "prob_v5_5",
        "prob_v51",
        "prob_v55",
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_diff",
        "config_key",
        "threshold",
        "threshold_usado",
    ]

    for col in colunas_uteis:
        if col in df.columns:
            out[col] = df[col].values

    out = out.dropna(subset=["DataHora_SP"]).copy()
    out = out[out["Resultado"].isin(["WIN", "LOSS"])].copy()

    if out["Pontos"].isna().all():
        raise ValueError("Coluna de pontos da V7 ficou toda vazia. Precisa ajustar o nome da coluna.")

    out = out.dropna(subset=["Pontos"]).copy()
    out = out[out["Pontos"] != 0].copy()

    out["Data"] = out["DataHora_SP"].dt.date
    out["Ano"] = out["DataHora_SP"].dt.year
    out["Mes"] = out["DataHora_SP"].dt.month
    out["AnoMes"] = out["DataHora_SP"].dt.strftime("%Y-%m")
    out["Hora"] = out["DataHora_SP"].dt.hour
    out["Minuto"] = out["DataHora_SP"].dt.minute
    out["Bloco_15m"] = (
        out["Hora"].astype(str).str.zfill(2)
        + ":"
        + ((out["Minuto"] // 15) * 15).astype(str).str.zfill(2)
    )
    out["Rotacao"] = out["Mes"].apply(definir_rotacao)

    out = out.sort_values("DataHora_SP").reset_index(drop=True)

    return out


def carregar_v7() -> pd.DataFrame:
    arquivo = escolher_arquivo_v7()

    print("\nLendo V7:")
    print(arquivo)

    df = ler_csv(arquivo)

    print("Linhas V7 lidas:", len(df))
    print("Colunas V7:")
    print(list(df.columns))

    v7 = normalizar_v7(df, arquivo)

    print("\nV7 normalizada:")
    print("Trades:", len(v7))
    print("Período:", v7["DataHora_SP"].min(), "até", v7["DataHora_SP"].max())
    print("WIN/LOSS:")
    print(v7["Resultado"].value_counts())

    return v7


# ============================================================
# APLICAR FILTRO V5.3 NA V7
# ============================================================

def aplicar_filtro_v53_na_v7(v7: pd.DataFrame, v53: pd.DataFrame) -> pd.DataFrame:
    print("\nAplicando filtro da V5.3 oficial na V7...")

    v7 = v7.copy()
    v53 = v53.copy()

    v7["mantido_v53"] = False
    v7["DataHora_V53_match"] = pd.NaT
    v7["prob_v5_3_match"] = np.nan
    v7["pontos_v5_match"] = np.nan
    v7["Fonte_V53_match"] = ""

    # Agrupa V5.3 por data e direção para acelerar
    grupos = {}

    for _, row in v53.iterrows():
        chave = (row["Data"], row["Direcao"])
        grupos.setdefault(chave, []).append(row)

    mantidos = []

    for idx, row in barra(v7.iterrows(), desc="Filtrando V7 com V5.3"):
        data = row["Data"]
        direcao = row["Direcao"]
        dt_v7 = row["DataHora_SP"]

        chave = (data, direcao)

        candidatos = grupos.get(chave, [])

        melhor = None
        melhor_diff = None

        for cand in candidatos:
            dt_v53 = cand["DataHora_SP"]
            diff_min = abs((dt_v7 - dt_v53).total_seconds()) / 60.0

            if diff_min <= TOLERANCIA_MINUTOS:
                if melhor is None or diff_min < melhor_diff:
                    melhor = cand
                    melhor_diff = diff_min

        if melhor is not None:
            v7.at[idx, "mantido_v53"] = True
            v7.at[idx, "DataHora_V53_match"] = melhor["DataHora_SP"]
            v7.at[idx, "prob_v5_3_match"] = melhor.get("prob_v5_3", np.nan)
            v7.at[idx, "pontos_v5_match"] = melhor.get("pontos_v5", np.nan)
            v7.at[idx, "Fonte_V53_match"] = melhor.get("Fonte_V53", "")
            mantidos.append(idx)

    filtrado = v7[v7["mantido_v53"]].copy()
    filtrado = filtrado.sort_values("DataHora_SP").reset_index(drop=True)

    print("\nFiltro aplicado:")
    print("Trades V7 original:", len(v7))
    print("Trades V7.1 mantidos pelo filtro V5.3:", len(filtrado))
    print("Trades cortados:", len(v7) - len(filtrado))

    if len(v7) > 0:
        print("Percentual mantido:", len(filtrado) / len(v7) * 100)

    return filtrado


# ============================================================
# MÉTRICAS
# ============================================================

def calcular_drawdown(pontos):
    pontos = pd.Series(pontos).fillna(0.0)
    equity = pontos.cumsum()
    topo = equity.cummax()
    dd = equity - topo

    if len(dd) == 0:
        return 0.0

    return float(dd.min())


def resumir(df: pd.DataFrame, nome: str) -> dict:
    if df.empty:
        return {
            "estrategia": nome,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "lucro_dolar_nq": 0.0,
            "profit_factor": 0.0,
            "drawdown_pontos": 0.0,
            "drawdown_dolar_nq": 0.0,
            "dias_operados": 0,
            "media_trades_dia": 0.0,
            "pior_dia": 0.0,
            "melhor_dia": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "media_pontos_trade": 0.0,
            "media_pontos_10_trades": 0.0,
            "media_dolar_trade_nq": 0.0,
            "media_dolar_10_trades_nq": 0.0,
        }

    trades = len(df)
    wins = int((df["Resultado"] == "WIN").sum())
    losses = int((df["Resultado"] == "LOSS").sum())

    lucro = float(df["Pontos"].sum())

    ganhos = float(df.loc[df["Pontos"] > 0, "Pontos"].sum())
    perdas = abs(float(df.loc[df["Pontos"] < 0, "Pontos"].sum()))

    pf = ganhos / perdas if perdas > 0 else 999.0
    dd = calcular_drawdown(df["Pontos"])

    dias = int(df["Data"].nunique())
    media_dia = trades / dias if dias else 0.0

    por_dia = df.groupby("Data")["Pontos"].sum()

    buy_total = int((df["Direcao"].astype(str).str.upper() == "BUY").sum())
    sell_total = int((df["Direcao"].astype(str).str.upper() == "SELL").sum())

    media_trade = lucro / trades if trades else 0.0

    return {
        "estrategia": nome,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate": wins / trades * 100 if trades else 0.0,
        "lucro_pontos": lucro,
        "lucro_dolar_nq": lucro * VALOR_POR_PONTO_NQ,
        "profit_factor": pf,
        "drawdown_pontos": dd,
        "drawdown_dolar_nq": dd * VALOR_POR_PONTO_NQ,
        "dias_operados": dias,
        "media_trades_dia": media_dia,
        "pior_dia": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia": float(por_dia.max()) if len(por_dia) else 0.0,
        "buy_total": buy_total,
        "sell_total": sell_total,
        "media_pontos_trade": media_trade,
        "media_pontos_10_trades": media_trade * 10,
        "media_dolar_trade_nq": media_trade * VALOR_POR_PONTO_NQ,
        "media_dolar_10_trades_nq": media_trade * 10 * VALOR_POR_PONTO_NQ,
    }


def resumo_mensal(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    linhas = []

    for anomes, g in df.groupby("AnoMes"):
        r = resumir(g, nome)
        r["AnoMes"] = anomes
        r["Ano"] = int(g["Ano"].iloc[0])
        r["Mes"] = int(g["Mes"].iloc[0])
        linhas.append(r)

    return pd.DataFrame(linhas)


def resumo_rotacao(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    linhas = []

    for rotacao, g in df.groupby("Rotacao"):
        r = resumir(g, nome)
        r["Rotacao"] = rotacao
        r["Meses_Rotacao"] = ",".join(str(x) for x in ROTACOES.get(rotacao, []))
        linhas.append(r)

    return pd.DataFrame(linhas)


def resumo_horario(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    linhas = []

    for hora, g in df.groupby("Hora"):
        r = resumir(g, nome)
        r["Hora"] = hora
        linhas.append(r)

    return pd.DataFrame(linhas)


# ============================================================
# RELATÓRIO
# ============================================================

def salvar_relatorio(
    v7,
    v71,
    resumo_v7,
    resumo_v71,
    comparativo,
    mensal_v7,
    mensal_v71,
    rot_v7,
    rot_v71,
    hor_v7,
    hor_v71,
):
    linhas = []

    def add(x=""):
        linhas.append(str(x))

    add("=" * 100)
    add("RELATÓRIO V7.1 - V7 FILTRADA PELA V5.3 OFICIAL")
    add("=" * 100)
    add("")
    add("Regra:")
    add("Mantém trade da V7 somente se houver trade aceito pela V5.3 oficial")
    add("com mesma direção e horário próximo.")
    add("")
    add(f"Tolerância em minutos: {TOLERANCIA_MINUTOS}")
    add(f"Valor por ponto NQ: US$ {VALOR_POR_PONTO_NQ}")
    add(f"Pasta saída: {PASTA_SAIDA}")
    add("")

    add("=" * 100)
    add("RESUMO V7 ORIGINAL")
    add("=" * 100)
    add(resumo_v7.T.to_string())

    add("")
    add("=" * 100)
    add("RESUMO V7.1 FILTRADA V5.3")
    add("=" * 100)
    add(resumo_v71.T.to_string())

    add("")
    add("=" * 100)
    add("COMPARATIVO")
    add("=" * 100)
    add(comparativo.to_string(index=False))

    add("")
    add("=" * 100)
    add("MENSAL V7 ORIGINAL")
    add("=" * 100)
    add(mensal_v7.to_string(index=False))

    add("")
    add("=" * 100)
    add("MENSAL V7.1 FILTRADA")
    add("=" * 100)
    add(mensal_v71.to_string(index=False))

    add("")
    add("=" * 100)
    add("ROTAÇÃO V7 ORIGINAL")
    add("=" * 100)
    add(rot_v7.to_string(index=False))

    add("")
    add("=" * 100)
    add("ROTAÇÃO V7.1 FILTRADA")
    add("=" * 100)
    add(rot_v71.to_string(index=False))

    add("")
    add("=" * 100)
    add("HORÁRIO V7 ORIGINAL")
    add("=" * 100)
    add(hor_v7.to_string(index=False))

    add("")
    add("=" * 100)
    add("HORÁRIO V7.1 FILTRADA")
    add("=" * 100)
    add(hor_v71.to_string(index=False))

    with open(ARQ_RELATORIO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 100)
    print("V7.1 - APLICAR FILTRO OFICIAL DA V5.3 NA V7")
    print("=" * 100)

    print("\nPasta de saída:")
    print(PASTA_SAIDA)

    salvar_config()

    v53 = carregar_v53_oficial()
    v53.to_csv(ARQ_V53_OFICIAL, index=False, compression="gzip")

    v7 = carregar_v7()
    v7.to_csv(ARQ_V7_ORIGINAL_NORMALIZADO, index=False, compression="gzip")

    v71 = aplicar_filtro_v53_na_v7(v7, v53)
    v71.to_csv(ARQ_V71_FILTRADO, index=False, compression="gzip")

    resumo_v7 = pd.DataFrame([resumir(v7, "V7_ORIGINAL")])
    resumo_v71 = pd.DataFrame([resumir(v71, "V7_1_FILTRADA_V53")])

    resumo_v7.to_csv(ARQ_RESUMO_V7, index=False)
    resumo_v71.to_csv(ARQ_RESUMO_V71, index=False)

    comparativo = pd.concat([resumo_v7, resumo_v71], ignore_index=True)
    comparativo.to_csv(ARQ_COMPARATIVO, index=False)

    mensal_v7 = resumo_mensal(v7, "V7_ORIGINAL")
    mensal_v71 = resumo_mensal(v71, "V7_1_FILTRADA_V53")

    mensal_v7.to_csv(ARQ_MENSAL_V7, index=False)
    mensal_v71.to_csv(ARQ_MENSAL_V71, index=False)

    rot_v7 = resumo_rotacao(v7, "V7_ORIGINAL")
    rot_v71 = resumo_rotacao(v71, "V7_1_FILTRADA_V53")

    rot_v7.to_csv(ARQ_ROTACAO_V7, index=False)
    rot_v71.to_csv(ARQ_ROTACAO_V71, index=False)

    hor_v7 = resumo_horario(v7, "V7_ORIGINAL")
    hor_v71 = resumo_horario(v71, "V7_1_FILTRADA_V53")

    hor_v7.to_csv(ARQ_HORARIO_V7, index=False)
    hor_v71.to_csv(ARQ_HORARIO_V71, index=False)

    salvar_relatorio(
        v7,
        v71,
        resumo_v7,
        resumo_v71,
        comparativo,
        mensal_v7,
        mensal_v71,
        rot_v7,
        rot_v71,
        hor_v7,
        hor_v71,
    )

    print("\n")
    print("=" * 100)
    print("COMPARATIVO FINAL - V7 x V7.1 FILTRADA V5.3")
    print("=" * 100)
    print(comparativo.to_string(index=False))

    print("\nArquivos salvos:")
    print(ARQ_V53_OFICIAL)
    print(ARQ_V7_ORIGINAL_NORMALIZADO)
    print(ARQ_V71_FILTRADO)
    print(ARQ_RESUMO_V7)
    print(ARQ_RESUMO_V71)
    print(ARQ_COMPARATIVO)
    print(ARQ_MENSAL_V7)
    print(ARQ_MENSAL_V71)
    print(ARQ_ROTACAO_V7)
    print(ARQ_ROTACAO_V71)
    print(ARQ_HORARIO_V7)
    print(ARQ_HORARIO_V71)
    print(ARQ_RELATORIO)

    print("\nFinalizado com sucesso.")


if __name__ == "__main__":
    main()