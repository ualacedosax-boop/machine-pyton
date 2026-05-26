import os
import glob
import pandas as pd
import numpy as np
from itertools import product

# =========================================================
# CONFIG
# =========================================================
ENTRADAS = [
    ("2025-10-28 10:30", "SELL"),
    ("2025-10-28 12:30", "BUY"),
    ("2025-10-28 13:30", "SELL"),
    ("2025-10-28 16:30", "SELL"),
    ("2025-10-28 17:00", "BUY"),
    ("2025-10-28 19:15", "SELL"),
    ("2025-10-28 20:00", "BUY"),
    ("2025-10-28 21:00", "BUY"),
    ("2025-10-28 23:15", "SELL"),
    ("2025-10-29 00:45", "SELL"),
    ("2025-10-29 01:00", "BUY"),
    ("2025-10-29 03:30", "SELL"),
    ("2025-10-29 04:15", "BUY"),
    ("2025-10-29 05:15", "SELL"),
    ("2025-10-29 06:45", "BUY"),
    ("2025-10-29 08:30", "SELL"),
    ("2025-10-29 09:30", "BUY"),
    ("2025-10-29 11:00", "SELL"),
    ("2025-10-29 13:00", "BUY"),
    ("2025-10-29 15:00", "SELL"),
    ("2025-10-29 15:50", "BUY"),
    ("2025-10-29 17:00", "SELL"),
    ("2025-10-29 19:00", "BUY"),
    ("2025-10-29 20:30", "BUY"),
    ("2025-10-29 21:30", "SELL"),
    ("2025-10-29 22:00", "BUY"),
    ("2025-10-30 10:30", "BUY"),
    ("2025-10-30 11:00", "SELL"),
    ("2025-10-30 12:45", "BUY"),
    ("2025-10-30 13:15", "SELL"),
    ("2025-10-30 14:00", "BUY"),
    ("2025-10-30 14:45", "SELL"),
]

MIN_SINAIS_REGRA = 3

# grades focadas na hipótese
CLOSE_POS_BUY_LIST = [0.50, 0.55, 0.60]
CLOSE_POS_SELL_LIST = [0.50, 0.45, 0.40]

K_BUY_LIST = [20, 25, 30, None]
K_SELL_LIST = [70, 75, 80, None]

USAR_KD_BUY_LIST = [0, 1]
USAR_KD_SELL_LIST = [0, 1]

USAR_CLOSE_VS_EMA = [0, 1]
USAR_DIST_EMA = [0, 1]

DIST_EMA_LIMITE_LIST = [0.0000, 0.0005, 0.0010]

# =========================================================
# DESCOBRIR CSV
# =========================================================
def escolher_arquivo_csv():
    print("Pasta atual:", os.getcwd())

    candidatos = []
    projeto_csv = glob.glob("*.csv")
    print("\nCSV na pasta do projeto:")
    for arq in projeto_csv:
        print("-", arq)
    candidatos.extend(projeto_csv)

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    downloads_csv = glob.glob(os.path.join(downloads, "*.csv"))
    print("\nCSV em Downloads:")
    for arq in downloads_csv:
        print("-", arq)
    candidatos.extend(downloads_csv)

    for arq in candidatos:
        nome = os.path.basename(arq).upper()
        if ("MNQ" in nome or "NQ" in nome) and "15" in nome:
            return arq

    for arq in candidatos:
        nome = os.path.basename(arq).upper()
        if "MNQ" in nome or "NQ" in nome:
            return arq

    raise FileNotFoundError("Não encontrei CSV do NQ/MNQ 15 min.")

ARQUIVO = escolher_arquivo_csv()
print("\nArquivo escolhido:", ARQUIVO)

# =========================================================
# INDICADORES
# =========================================================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def stoch_rsi(close, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    rsi_vals = rsi(close, rsi_period)
    min_rsi = rsi_vals.rolling(stoch_period).min()
    max_rsi = rsi_vals.rolling(stoch_period).max()
    stoch = 100 * (rsi_vals - min_rsi) / (max_rsi - min_rsi + 1e-9)
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return k, d

def keltner_channel(df, ema_period=20, atr_period=20, mult=2.0):
    mid = ema(df["close"], ema_period)
    atr_val = atr(df, atr_period)
    upper = mid + atr_val * mult
    lower = mid - atr_val * mult
    return mid, upper, lower

# =========================================================
# LEITURA
# =========================================================
df = pd.read_csv(ARQUIVO)

if "time" in df.columns:
    df = df.rename(columns={"time": "datetime"})
elif "datetime" not in df.columns:
    raise ValueError("O CSV precisa ter coluna 'time' ou 'datetime'.")

df["datetime"] = pd.to_datetime(df["datetime"])

if getattr(df["datetime"].dt, "tz", None) is not None:
    df["datetime"] = df["datetime"].dt.tz_localize(None)

df = df.sort_values("datetime").reset_index(drop=True)
df.columns = [c.lower() if c not in ["K", "D"] else c for c in df.columns]

for col in ["open", "high", "low", "close"]:
    if col not in df.columns:
        raise ValueError(f"Coluna obrigatória ausente: {col}")

df["ema17"] = ema(df["close"], 17)
df["dist_ema17"] = (df["close"] - df["ema17"]) / (df["ema17"] + 1e-9)

df["kc_mid"], df["kc_upper"], df["kc_lower"] = keltner_channel(df, ema_period=20, atr_period=20, mult=2.0)
df["toque_kc_upper"] = (df["high"] >= df["kc_upper"]).astype(int)
df["toque_kc_lower"] = (df["low"] <= df["kc_lower"]).astype(int)
df["kc_pos"] = (df["close"] - df["kc_lower"]) / ((df["kc_upper"] - df["kc_lower"]) + 1e-9)

df["range_candle"] = df["high"] - df["low"]
df["close_pos"] = (df["close"] - df["low"]) / (df["range_candle"] + 1e-9)

if "K" in df.columns and "D" in df.columns:
    df["k"] = df["K"]
    df["d"] = df["D"]
else:
    df["k"], df["d"] = stoch_rsi(df["close"])

df["kd_diff"] = df["k"] - df["d"]

# =========================================================
# ENTRADAS REAIS
# =========================================================
entradas_df = pd.DataFrame(ENTRADAS, columns=["datetime_str", "tipo"])
entradas_df["datetime"] = pd.to_datetime(entradas_df["datetime_str"])
entradas_df = entradas_df.drop(columns=["datetime_str"])

snapshots = entradas_df.merge(df, on="datetime", how="left")

faltantes = snapshots["open"].isna().sum()
print("\nEntradas informadas:", len(entradas_df))
print("Entradas encontradas no CSV:", len(snapshots) - faltantes)
print("Entradas faltantes:", faltantes)

if faltantes > 0:
    print("\nEntradas não encontradas:")
    print(snapshots[snapshots["open"].isna()][["datetime", "tipo"]])

snapshots = snapshots.dropna().copy()

if len(snapshots) == 0:
    raise ValueError("Nenhuma entrada encontrada.")

datas_interesse = snapshots["datetime"].dt.date.unique()
universo = df[df["datetime"].dt.date.isin(datas_interesse)].copy()

reais_buy = set(snapshots.loc[snapshots["tipo"] == "BUY", "datetime"])
reais_sell = set(snapshots.loc[snapshots["tipo"] == "SELL", "datetime"])

# =========================================================
# AVALIAÇÃO
# =========================================================
def avaliar_predicao(pred_set, reais_set):
    tp = len(pred_set & reais_set)
    fp = len(pred_set - reais_set)
    fn = len(reais_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return tp, fp, fn, precision, recall, f1

# =========================================================
# TESTE DE REGRAS BUY
# =========================================================
resultados = []

for close_pos_buy, k_buy, usar_kd_buy, usar_close_vs_ema, usar_dist_ema, dist_limite in product(
    CLOSE_POS_BUY_LIST,
    K_BUY_LIST,
    USAR_KD_BUY_LIST,
    USAR_CLOSE_VS_EMA,
    USAR_DIST_EMA,
    DIST_EMA_LIMITE_LIST
):
    cond_buy = universo["toque_kc_lower"] == 1
    cond_buy = cond_buy & (universo["close_pos"] >= close_pos_buy)

    if usar_close_vs_ema == 1:
        cond_buy = cond_buy & (universo["close"] < universo["ema17"])

    if usar_dist_ema == 1:
        cond_buy = cond_buy & (universo["dist_ema17"] <= -dist_limite)

    if k_buy is not None:
        cond_buy = cond_buy & (universo["k"] <= k_buy)

    if usar_kd_buy == 1:
        cond_buy = cond_buy & (universo["kd_diff"] > 0)

    sinais = set(universo.loc[cond_buy, "datetime"])

    if len(sinais) < MIN_SINAIS_REGRA:
        continue

    tp, fp, fn, precision, recall, f1 = avaliar_predicao(sinais, reais_buy)

    resultados.append({
        "tipo": "BUY",
        "toque_kc": "lower",
        "close_pos_limite": close_pos_buy,
        "k_limite": k_buy,
        "usar_kd": usar_kd_buy,
        "usar_close_vs_ema": usar_close_vs_ema,
        "usar_dist_ema": usar_dist_ema,
        "dist_ema_limite": dist_limite,
        "sinais_preditos": len(sinais),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1
    })

# =========================================================
# TESTE DE REGRAS SELL
# =========================================================
for close_pos_sell, k_sell, usar_kd_sell, usar_close_vs_ema, usar_dist_ema, dist_limite in product(
    CLOSE_POS_SELL_LIST,
    K_SELL_LIST,
    USAR_KD_SELL_LIST,
    USAR_CLOSE_VS_EMA,
    USAR_DIST_EMA,
    DIST_EMA_LIMITE_LIST
):
    cond_sell = universo["toque_kc_upper"] == 1
    cond_sell = cond_sell & (universo["close_pos"] <= close_pos_sell)

    if usar_close_vs_ema == 1:
        cond_sell = cond_sell & (universo["close"] > universo["ema17"])

    if usar_dist_ema == 1:
        cond_sell = cond_sell & (universo["dist_ema17"] >= dist_limite)

    if k_sell is not None:
        cond_sell = cond_sell & (universo["k"] >= k_sell)

    if usar_kd_sell == 1:
        cond_sell = cond_sell & (universo["kd_diff"] < 0)

    sinais = set(universo.loc[cond_sell, "datetime"])

    if len(sinais) < MIN_SINAIS_REGRA:
        continue

    tp, fp, fn, precision, recall, f1 = avaliar_predicao(sinais, reais_sell)

    resultados.append({
        "tipo": "SELL",
        "toque_kc": "upper",
        "close_pos_limite": close_pos_sell,
        "k_limite": k_sell,
        "usar_kd": usar_kd_sell,
        "usar_close_vs_ema": usar_close_vs_ema,
        "usar_dist_ema": usar_dist_ema,
        "dist_ema_limite": dist_limite,
        "sinais_preditos": len(sinais),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1
    })

ranking = pd.DataFrame(resultados)
ranking = ranking.sort_values(
    ["f1", "precision", "recall", "tp"],
    ascending=False
).reset_index(drop=True)

ranking.to_csv("ranking_keltner_v3.csv", index=False)

print("\nTop 30 combinações Keltner V3:")
print(ranking.head(30))

# =========================================================
# RESUMO DAS ENTRADAS
# =========================================================
snapshots_resumo = snapshots[[
    "datetime", "tipo", "close", "ema17", "dist_ema17",
    "k", "d", "kd_diff",
    "toque_kc_upper", "toque_kc_lower",
    "kc_pos", "close_pos"
]].copy()

snapshots_resumo.to_csv("snapshot_keltner_v3.csv", index=False)

print("\nResumo rápido das entradas:")
print(
    snapshots.groupby("tipo")[[
        "dist_ema17", "k", "d", "kd_diff", "kc_pos", "close_pos",
        "toque_kc_upper", "toque_kc_lower"
    ]].mean()
)

print("\nArquivos salvos:")
print("- ranking_keltner_v3.csv")
print("- snapshot_keltner_v3.csv")