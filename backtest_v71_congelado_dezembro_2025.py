from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json
import os
import sys
import traceback

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA = BASE / "backtest_v71_congelado_dezembro_2025"
SAIDA.mkdir(exist_ok=True)

print("=" * 100)
print("BACKTEST V7.1 CONGELADO - DEZEMBRO 2025")
print("=" * 100)

PARAMS = {
    "versao": "V7.1_CONGELADO",
    "data_congelamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "periodo_teste_inicio": "2025-12-01",
    "periodo_teste_fim": "2025-12-31",
    "take": 50.5,
    "stop": 117.0,
    "prob_v51_min": 0.59,
    "prob_v55_min": 0.425,
    "score_buy_min": 0.74,
    "score_sell_min": 0.50,
    "prob_v53_min": 0.50,
    "hora_inicio": 2.0,
    "hora_fim": 6.0,
    "bloquear_0430_0444": True,
    "hora_bloqueio_inicio": 4.5,
    "hora_bloqueio_fim": 4.75,
    "max_trades_dia": 3,
    "parar_apos_loss": True,
}

with open(SAIDA / "params_v71_congelado_dezembro_2025.json", "w", encoding="utf-8") as f:
    json.dump(PARAMS, f, indent=4, ensure_ascii=False)

print("Parâmetros congelados salvos em:")
print(SAIDA / "params_v71_congelado_dezembro_2025.json")

# ============================================================
# LOCALIZAR ARQUIVOS DE TRADES/PREDIÇÕES JÁ EXISTENTES
# ============================================================

candidatos = []

padroes = [
    "*2025*.csv",
    "*2025*.csv.gz",
    "*trades*.csv",
    "*trades*.csv.gz",
    "*sinais*.csv",
    "*sinais*.csv.gz",
    "*resultado*.csv",
    "*resultado*.csv.gz",
    "*v71*.csv",
    "*v71*.csv.gz",
    "*v7*.csv",
    "*v7*.csv.gz",
]

for padrao in padroes:
    candidatos.extend(BASE.rglob(padrao))

# remove duplicados
vistos = set()
arquivos = []
for p in candidatos:
    if p.is_file() and p not in vistos:
        vistos.add(p)
        arquivos.append(p)

print()
print("Arquivos candidatos encontrados:", len(arquivos))

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def ler_csv_possivel(path):
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            pass
    return pd.read_csv(path, low_memory=False)


def achar_col_data(df):
    candidatos = [
        "DataHora_SP",
        "datahora_entrada",
        "DataHora",
        "datetime",
        "date",
        "Data",
        "data",
        "entrada",
        "entry_time",
        "time",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def achar_col_resultado(df):
    candidatos = [
        "resultado",
        "Result",
        "result",
        "saida",
        "tipo_saida",
        "status",
        "win_loss",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def achar_col_direcao(df):
    candidatos = [
        "sinal",
        "Direcao",
        "direcao",
        "direction",
        "side",
        "ordem",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def achar_col_preco_entrada(df):
    candidatos = [
        "preco_entrada",
        "entry_price",
        "entrada_preco",
        "preco_close",
        "close",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def achar_col_pnl(df):
    candidatos = [
        "pontos",
        "pnl_pontos",
        "resultado_pontos",
        "lucro_pontos",
        "profit_points",
        "Profit",
        "profit",
        "PnL",
        "pnl",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def normalizar_resultado_para_pontos(row, col_resultado=None, col_pnl=None):
    take = PARAMS["take"]
    stop = PARAMS["stop"]

    if col_pnl and col_pnl in row.index:
        val = pd.to_numeric(row[col_pnl], errors="coerce")
        if pd.notna(val):
            return float(val)

    if col_resultado and col_resultado in row.index:
        r = str(row[col_resultado]).lower()
        if "take" in r or "win" in r or r in ["1", "true", "gain", "lucro"]:
            return take
        if "stop" in r or "loss" in r or r in ["-1", "false", "prejuizo", "prejuízo"]:
            return -stop

    return np.nan


# ============================================================
# PROCURAR UM ARQUIVO COM DEZEMBRO 2025
# ============================================================

melhores = []

for arq in arquivos:
    try:
        df = ler_csv_possivel(arq)

        if df.empty:
            continue

        col_data = achar_col_data(df)
        if not col_data:
            continue

        datas = pd.to_datetime(df[col_data], errors="coerce", dayfirst=False)
        if datas.isna().mean() > 0.8:
            datas = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

        qtd_dez = ((datas >= "2025-12-01") & (datas < "2026-01-01")).sum()

        if qtd_dez > 0:
            melhores.append((qtd_dez, arq, col_data, list(df.columns)))

    except Exception:
        continue

melhores = sorted(melhores, reverse=True, key=lambda x: x[0])

print()
print("Arquivos com dados de dezembro/2025 encontrados:", len(melhores))

if not melhores:
    print()
    print("NÃO ENCONTREI um arquivo de trades/sinais com dezembro de 2025.")
    print("Vou salvar a lista de candidatos para você conferir.")
    pd.DataFrame({"arquivo": [str(a) for a in arquivos]}).to_csv(SAIDA / "arquivos_candidatos.csv", index=False)
    print("Lista salva em:", SAIDA / "arquivos_candidatos.csv")
    raise SystemExit(1)

print()
print("Melhores candidatos:")
for qtd, arq, col_data, cols in melhores[:10]:
    print(f"{qtd:6d} linhas em dez/2025 | {arq} | coluna data: {col_data}")

# usa o arquivo com mais linhas de dezembro
_, ARQ_ESCOLHIDO, COL_DATA, COLS = melhores[0]

print()
print("=" * 100)
print("ARQUIVO ESCOLHIDO")
print("=" * 100)
print(ARQ_ESCOLHIDO)
print("Coluna de data:", COL_DATA)

df = ler_csv_possivel(ARQ_ESCOLHIDO)
datas = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=False)
if datas.isna().mean() > 0.8:
    datas = pd.to_datetime(df[COL_DATA], errors="coerce", dayfirst=True)

df["_DataHoraTeste"] = datas
df = df[(df["_DataHoraTeste"] >= "2025-12-01") & (df["_DataHoraTeste"] < "2026-01-01")].copy()
df = df.sort_values("_DataHoraTeste").reset_index(drop=True)

# ============================================================
# APLICAR FILTROS CONGELADOS SE AS COLUNAS EXISTIREM
# ============================================================

df["_hora_decimal"] = df["_DataHoraTeste"].dt.hour + df["_DataHoraTeste"].dt.minute / 60.0

mask_hora = (df["_hora_decimal"] >= PARAMS["hora_inicio"]) & (df["_hora_decimal"] < PARAMS["hora_fim"])

if PARAMS["bloquear_0430_0444"]:
    mask_bloqueio = (df["_hora_decimal"] >= PARAMS["hora_bloqueio_inicio"]) & (df["_hora_decimal"] < PARAMS["hora_bloqueio_fim"])
else:
    mask_bloqueio = False

df = df[mask_hora & (~mask_bloqueio)].copy()

# tenta aplicar thresholds se colunas existirem
filtros_aplicados = []

if "prob_v51" in df.columns:
    df = df[pd.to_numeric(df["prob_v51"], errors="coerce") >= PARAMS["prob_v51_min"]].copy()
    filtros_aplicados.append("prob_v51")

if "prob_v55" in df.columns:
    df = df[pd.to_numeric(df["prob_v55"], errors="coerce") >= PARAMS["prob_v55_min"]].copy()
    filtros_aplicados.append("prob_v55")

if "prob_v5_3" in df.columns:
    df = df[pd.to_numeric(df["prob_v5_3"], errors="coerce") >= PARAMS["prob_v53_min"]].copy()
    filtros_aplicados.append("prob_v5_3")

# score buy/sell
col_dir = achar_col_direcao(df)

if "score_BUY" in df.columns and "score_SELL" in df.columns:
    score_buy = pd.to_numeric(df["score_BUY"], errors="coerce")
    score_sell = pd.to_numeric(df["score_SELL"], errors="coerce")

    if col_dir:
        direcao = df[col_dir].astype(str).str.upper()
        mask_score = (
            ((direcao.str.contains("BUY") | direcao.str.contains("COMPRA")) & (score_buy >= PARAMS["score_buy_min"])) |
            ((direcao.str.contains("SELL") | direcao.str.contains("VENDA")) & (score_sell >= PARAMS["score_sell_min"]))
        )
    else:
        mask_score = (score_buy >= PARAMS["score_buy_min"]) | (score_sell >= PARAMS["score_sell_min"])

    df = df[mask_score].copy()
    filtros_aplicados.append("score_BUY/score_SELL")

# máximo de trades por dia e parar após loss
df["_Data"] = df["_DataHoraTeste"].dt.date

col_resultado = achar_col_resultado(df)
col_pnl = achar_col_pnl(df)

if col_resultado or col_pnl:
    df["_pontos"] = df.apply(lambda row: normalizar_resultado_para_pontos(row, col_resultado, col_pnl), axis=1)
else:
    df["_pontos"] = np.nan

selecionadas = []
for data, g in df.groupby("_Data"):
    trades_dia = 0
    teve_loss = False

    for _, row in g.sort_values("_DataHoraTeste").iterrows():
        if trades_dia >= PARAMS["max_trades_dia"]:
            continue

        if PARAMS["parar_apos_loss"] and teve_loss:
            continue

        selecionadas.append(row)
        trades_dia += 1

        if pd.notna(row["_pontos"]) and row["_pontos"] < 0:
            teve_loss = True

df_sel = pd.DataFrame(selecionadas)

# ============================================================
# RESUMO
# ============================================================

if df_sel.empty:
    resumo = {
        "arquivo_usado": str(ARQ_ESCOLHIDO),
        "periodo": "2025-12-01 a 2025-12-31",
        "trades": 0,
        "observacao": "Nenhum trade passou pelos filtros congelados.",
        "filtros_aplicados": filtros_aplicados,
    }
else:
    pontos = pd.to_numeric(df_sel["_pontos"], errors="coerce")

    trades = len(df_sel)
    wins = int((pontos > 0).sum()) if pontos.notna().any() else None
    losses = int((pontos < 0).sum()) if pontos.notna().any() else None
    lucro_pontos = float(pontos.sum()) if pontos.notna().any() else None

    if pontos.notna().any():
        curva = pontos.fillna(0).cumsum()
        dd = curva - curva.cummax()
        max_dd = float(dd.min())

        bruto_win = float(pontos[pontos > 0].sum())
        bruto_loss = abs(float(pontos[pontos < 0].sum()))
        pf = bruto_win / bruto_loss if bruto_loss > 0 else None
        winrate = wins / trades * 100 if trades else 0
    else:
        max_dd = None
        pf = None
        winrate = None

    resumo = {
        "arquivo_usado": str(ARQ_ESCOLHIDO),
        "periodo": "2025-12-01 a 2025-12-31",
        "filtros_aplicados": filtros_aplicados,
        "coluna_data": COL_DATA,
        "coluna_resultado": col_resultado,
        "coluna_pnl": col_pnl,
        "coluna_direcao": col_dir,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate_pct": winrate,
        "lucro_pontos": lucro_pontos,
        "lucro_estimado_nq_dolar_20_por_ponto": lucro_pontos * 20 if lucro_pontos is not None else None,
        "drawdown_pontos": max_dd,
        "drawdown_estimado_nq_dolar_20_por_ponto": max_dd * 20 if max_dd is not None else None,
        "profit_factor": pf,
        "dias_operados": int(df_sel["_Data"].nunique()),
        "media_trades_por_dia_operado": trades / df_sel["_Data"].nunique() if df_sel["_Data"].nunique() else None,
    }

# salvar
df_sel.to_csv(SAIDA / "trades_dezembro_2025_v71_congelado.csv", index=False, encoding="utf-8-sig")

with open(SAIDA / "resumo_dezembro_2025_v71_congelado.json", "w", encoding="utf-8") as f:
    json.dump(resumo, f, indent=4, ensure_ascii=False)

pd.DataFrame([resumo]).to_csv(SAIDA / "resumo_dezembro_2025_v71_congelado.csv", index=False, encoding="utf-8-sig")

print()
print("=" * 100)
print("RESULTADO BACKTEST V7.1 CONGELADO - DEZEMBRO 2025")
print("=" * 100)

for k, v in resumo.items():
    print(f"{k}: {v}")

print()
print("Arquivos gerados:")
print(SAIDA / "trades_dezembro_2025_v71_congelado.csv")
print(SAIDA / "resumo_dezembro_2025_v71_congelado.json")
print(SAIDA / "resumo_dezembro_2025_v71_congelado.csv")
