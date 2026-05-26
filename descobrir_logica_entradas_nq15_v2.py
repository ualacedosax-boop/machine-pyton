import os
import glob
import pandas as pd
import numpy as np
from itertools import combinations

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

# =========================================================
# DESCOBRIR ARQUIVO CSV AUTOMATICAMENTE
# =========================================================
def escolher_arquivo_csv():
    print("Pasta atual:", os.getcwd())

    candidatos = []

    # pasta do projeto
    projeto_csv = glob.glob("*.csv")
    print("\nCSV na pasta do projeto:")
    for arq in projeto_csv:
        print("-", arq)
    candidatos.extend(projeto_csv)

    # downloads
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    downloads_csv = glob.glob(os.path.join(downloads, "*.csv"))
    print("\nCSV em Downloads:")
    for arq in downloads_csv:
        print("-", arq)
    candidatos.extend(downloads_csv)

    # 1) preferência por arquivos com NQ/MNQ e 15 no nome
    for arq in candidatos:
        nome = os.path.basename(arq).upper()
        if ("MNQ" in nome or "NQ" in nome) and "15" in nome:
            return arq

    # 2) fallback: qualquer arquivo com NQ/MNQ
    for arq in candidatos:
        nome = os.path.basename(arq).upper()
        if "MNQ" in nome or "NQ" in nome:
            return arq

    raise FileNotFoundError(
        "Não encontrei CSV do NQ/MNQ nem na pasta do projeto nem em Downloads. "
        "Coloque o arquivo lá ou renomeie para algo contendo NQ/MNQ e 15."
    )

ARQUIVO = escolher_arquivo_csv()
print("\nArquivo escolhido:", ARQUIVO)

# =========================================================
# FUNÇÕES DE INDICADORES
# =========================================================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    return series.rolling(period).mean()

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

def macd(close, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close, period=20, mult=2):
    basis = close.rolling(period).mean()
    dev = close.rolling(period).std()
    upper = basis + mult * dev
    lower = basis - mult * dev
    return basis, upper, lower

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

# adapta nome da coluna de tempo
if "time" in df.columns:
    df = df.rename(columns={"time": "datetime"})
elif "datetime" not in df.columns:
    raise ValueError("O CSV precisa ter coluna 'time' ou 'datetime'.")

df["datetime"] = pd.to_datetime(df["datetime"])

# remove timezone para bater com as entradas
if getattr(df["datetime"].dt, "tz", None) is not None:
    df["datetime"] = df["datetime"].dt.tz_localize(None)

df = df.sort_values("datetime").reset_index(drop=True)

# normaliza colunas
df.columns = [c.lower() if c not in ["K", "D"] else c for c in df.columns]

for col in ["open", "high", "low", "close"]:
    if col not in df.columns:
        raise ValueError(f"Coluna obrigatória ausente: {col}")

# =========================================================
# INDICADORES
# =========================================================
df["ema9"] = ema(df["close"], 9)
df["ema17"] = ema(df["close"], 17)
df["ema21"] = ema(df["close"], 21)
df["ema34"] = ema(df["close"], 34)
df["ema50"] = ema(df["close"], 50)

df["sma20"] = sma(df["close"], 20)
df["sma50"] = sma(df["close"], 50)

df["ema17_slope"] = df["ema17"].diff(3)
df["ema34_slope"] = df["ema34"].diff(3)
df["ema50_slope"] = df["ema50"].diff(3)

df["rsi14"] = rsi(df["close"], 14)
df["atr14"] = atr(df, 14)

for p in [20, 25, 30]:
    sma_bias = sma(df["close"], p)
    df[f"bias{p}"] = (df["close"] - sma_bias) / (sma_bias + 1e-9) * 100

# K e D
if "K" in df.columns and "D" in df.columns:
    df["k"] = df["K"]
    df["d"] = df["D"]
else:
    df["k"], df["d"] = stoch_rsi(df["close"])

df["kd_diff"] = df["k"] - df["d"]

# MACD
df["macd_line"], df["macd_signal"], df["macd_hist"] = macd(df["close"])

# Bollinger
df["bb_basis"], df["bb_upper"], df["bb_lower"] = bollinger(df["close"], 20, 2)
df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_basis"] + 1e-9)
df["bb_pos"] = (df["close"] - df["bb_lower"]) / ((df["bb_upper"] - df["bb_lower"]) + 1e-9)

# Keltner
df["kc_mid"], df["kc_upper"], df["kc_lower"] = keltner_channel(df, ema_period=20, atr_period=20, mult=2.0)
df["kc_width"] = (df["kc_upper"] - df["kc_lower"]) / (df["kc_mid"] + 1e-9)
df["kc_pos"] = (df["close"] - df["kc_lower"]) / ((df["kc_upper"] - df["kc_lower"]) + 1e-9)
df["close_acima_kc_upper"] = (df["close"] > df["kc_upper"]).astype(int)
df["close_abaixo_kc_lower"] = (df["close"] < df["kc_lower"]).astype(int)
df["toque_kc_upper"] = (df["high"] >= df["kc_upper"]).astype(int)
df["toque_kc_lower"] = (df["low"] <= df["kc_lower"]).astype(int)
df["dist_kc_mid"] = (df["close"] - df["kc_mid"]) / (df["kc_mid"] + 1e-9)

# candle / preço
df["range_candle"] = df["high"] - df["low"]
df["body"] = (df["close"] - df["open"]).abs()
df["body_ratio"] = df["body"] / (df["range_candle"] + 1e-9)
df["close_pos"] = (df["close"] - df["low"]) / (df["range_candle"] + 1e-9)

df["dist_ema9"] = (df["close"] - df["ema9"]) / (df["ema9"] + 1e-9)
df["dist_ema17"] = (df["close"] - df["ema17"]) / (df["ema17"] + 1e-9)
df["dist_ema34"] = (df["close"] - df["ema34"]) / (df["ema34"] + 1e-9)
df["dist_ema50"] = (df["close"] - df["ema50"]) / (df["ema50"] + 1e-9)

df["ret_1"] = df["close"].pct_change(1)
df["ret_2"] = df["close"].pct_change(2)
df["ret_3"] = df["close"].pct_change(3)

df["hora"] = df["datetime"].dt.hour
df["minuto"] = df["datetime"].dt.minute

# =========================================================
# ENTRADAS REAIS
# =========================================================
entradas_df = pd.DataFrame(ENTRADAS, columns=["datetime_str", "tipo"])
entradas_df["datetime"] = pd.to_datetime(entradas_df["datetime_str"])

if getattr(entradas_df["datetime"].dt, "tz", None) is not None:
    entradas_df["datetime"] = entradas_df["datetime"].dt.tz_localize(None)

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
    raise ValueError("Nenhuma entrada foi encontrada no CSV. Verifique datas, horário e timeframe.")

# =========================================================
# SALVAR SNAPSHOT DAS ENTRADAS
# =========================================================
colunas_snapshot = [
    "datetime", "tipo", "open", "high", "low", "close",
    "ema9", "ema17", "ema21", "ema34", "ema50",
    "sma20", "sma50",
    "ema17_slope", "ema34_slope", "ema50_slope",
    "rsi14", "atr14",
    "bias20", "bias25", "bias30",
    "k", "d", "kd_diff",
    "macd_line", "macd_signal", "macd_hist",
    "bb_width", "bb_pos",
    "kc_mid", "kc_upper", "kc_lower",
    "kc_width", "kc_pos",
    "close_acima_kc_upper", "close_abaixo_kc_lower",
    "toque_kc_upper", "toque_kc_lower", "dist_kc_mid",
    "range_candle", "body", "body_ratio", "close_pos",
    "dist_ema9", "dist_ema17", "dist_ema34", "dist_ema50",
    "ret_1", "ret_2", "ret_3",
    "hora", "minuto"
]

snapshots[colunas_snapshot].to_csv("snapshot_entradas_video_v2.csv", index=False)
print("\nArquivo salvo: snapshot_entradas_video_v2.csv")

# =========================================================
# RESUMO BUY / SELL
# =========================================================
colunas_resumo = [
    "rsi14", "atr14",
    "bias20", "bias25", "bias30",
    "k", "d", "kd_diff",
    "macd_hist",
    "bb_pos", "bb_width",
    "kc_pos", "kc_width", "dist_kc_mid",
    "close_acima_kc_upper", "close_abaixo_kc_lower",
    "toque_kc_upper", "toque_kc_lower",
    "body_ratio", "close_pos",
    "dist_ema9", "dist_ema17", "dist_ema34", "dist_ema50",
    "ema17_slope", "ema34_slope", "ema50_slope"
]

resumo = snapshots.groupby("tipo")[colunas_resumo].agg(["mean", "median", "min", "max"])
resumo.to_csv("resumo_indicadores_buy_sell_v2.csv")
print("Arquivo salvo: resumo_indicadores_buy_sell_v2.csv")

print("\nResumo BUY/SELL:")
print(resumo)

# =========================================================
# REGRAS CANDIDATAS
# =========================================================
regras_buy = {
    "k<=25": df["k"] <= 25,
    "k<=30": df["k"] <= 30,
    "kd_diff>0": df["kd_diff"] > 0,
    "close<ema17": df["close"] < df["ema17"],
    "close<ema34": df["close"] < df["ema34"],
    "ema17_slope>0": df["ema17_slope"] > 0,
    "rsi14<=45": df["rsi14"] <= 45,
    "rsi14<=40": df["rsi14"] <= 40,
    "macd_hist>0": df["macd_hist"] > 0,
    "bb_pos<=0.35": df["bb_pos"] <= 0.35,
    "kc_pos<=0.35": df["kc_pos"] <= 0.35,
    "toque_kc_lower=1": df["toque_kc_lower"] == 1,
    "close_abaixo_kc_lower=1": df["close_abaixo_kc_lower"] == 1,
    "close_pos>=0.50": df["close_pos"] >= 0.50,
    "dist_ema17<0": df["dist_ema17"] < 0,
}

regras_sell = {
    "k>=70": df["k"] >= 70,
    "k>=75": df["k"] >= 75,
    "kd_diff<0": df["kd_diff"] < 0,
    "close>ema17": df["close"] > df["ema17"],
    "close>ema34": df["close"] > df["ema34"],
    "ema17_slope<0": df["ema17_slope"] < 0,
    "rsi14>=55": df["rsi14"] >= 55,
    "rsi14>=60": df["rsi14"] >= 60,
    "macd_hist<0": df["macd_hist"] < 0,
    "bb_pos>=0.65": df["bb_pos"] >= 0.65,
    "kc_pos>=0.65": df["kc_pos"] >= 0.65,
    "toque_kc_upper=1": df["toque_kc_upper"] == 1,
    "close_acima_kc_upper=1": df["close_acima_kc_upper"] == 1,
    "close_pos<=0.50": df["close_pos"] <= 0.50,
    "dist_ema17>0": df["dist_ema17"] > 0,
}

datas_interesse = snapshots["datetime"].dt.date.unique()
universo = df[df["datetime"].dt.date.isin(datas_interesse)].copy()

reais_buy = set(snapshots.loc[snapshots["tipo"] == "BUY", "datetime"])
reais_sell = set(snapshots.loc[snapshots["tipo"] == "SELL", "datetime"])

def avaliar_regras(regras_dict, tipo_nome, reais_set):
    resultados = []
    nomes = list(regras_dict.keys())

    for tamanho in [2, 3]:
        for combo in combinations(nomes, tamanho):
            cond = pd.Series(True, index=universo.index)

            for nome in combo:
                cond = cond & regras_dict[nome].reindex(universo.index, fill_value=False)

            sinais = universo.loc[cond, "datetime"]
            pred_set = set(sinais)

            tp = len(pred_set & reais_set)
            fp = len(pred_set - reais_set)
            fn = len(reais_set - pred_set)

            if len(pred_set) < MIN_SINAIS_REGRA:
                continue

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            resultados.append({
                "tipo": tipo_nome,
                "regras": " AND ".join(combo),
                "sinais_preditos": len(pred_set),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1
            })

    return pd.DataFrame(resultados)

resultado_buy = avaliar_regras(regras_buy, "BUY", reais_buy)
resultado_sell = avaliar_regras(regras_sell, "SELL", reais_sell)

ranking_regras = pd.concat([resultado_buy, resultado_sell], ignore_index=True)
ranking_regras = ranking_regras.sort_values(
    ["f1", "precision", "recall", "tp"],
    ascending=False
).reset_index(drop=True)

ranking_regras.to_csv("ranking_regras_entradas_video_v2.csv", index=False)
print("\nArquivo salvo: ranking_regras_entradas_video_v2.csv")

print("\nTop 30 regras candidatas:")
print(ranking_regras.head(30))

# =========================================================
# PADRÕES MAIS COMUNS
# =========================================================
def resumir_condicoes(df_side, side):
    return {
        "tipo": side,
        "qtd": len(df_side),
        "pct_close_abaixo_ema17": (df_side["close"] < df_side["ema17"]).mean(),
        "pct_close_acima_ema17": (df_side["close"] > df_side["ema17"]).mean(),
        "pct_k_le_30": (df_side["k"] <= 30).mean(),
        "pct_k_ge_70": (df_side["k"] >= 70).mean(),
        "pct_kd_diff_pos": (df_side["kd_diff"] > 0).mean(),
        "pct_kd_diff_neg": (df_side["kd_diff"] < 0).mean(),
        "pct_rsi_le_45": (df_side["rsi14"] <= 45).mean(),
        "pct_rsi_ge_55": (df_side["rsi14"] >= 55).mean(),
        "pct_bb_pos_le_035": (df_side["bb_pos"] <= 0.35).mean(),
        "pct_bb_pos_ge_065": (df_side["bb_pos"] >= 0.65).mean(),
        "pct_kc_pos_le_035": (df_side["kc_pos"] <= 0.35).mean(),
        "pct_kc_pos_ge_065": (df_side["kc_pos"] >= 0.65).mean(),
        "pct_toque_kc_lower": (df_side["toque_kc_lower"] == 1).mean(),
        "pct_toque_kc_upper": (df_side["toque_kc_upper"] == 1).mean(),
    }

padroes = pd.DataFrame([
    resumir_condicoes(snapshots[snapshots["tipo"] == "BUY"], "BUY"),
    resumir_condicoes(snapshots[snapshots["tipo"] == "SELL"], "SELL")
])

padroes.to_csv("padroes_comuns_entradas_video_v2.csv", index=False)
print("\nArquivo salvo: padroes_comuns_entradas_video_v2.csv")

print("\nPadrões comuns:")
print(padroes)