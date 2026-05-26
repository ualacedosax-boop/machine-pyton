import pandas as pd
import numpy as np
import os
import shutil
from datetime import datetime, date, time

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, balanced_accuracy_score


# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_PRECOS = "MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv"
ARQUIVO_ENTRADAS = "Entrada video-priemira amostra.xlsx"

PASTA_SAIDA = "saida_ml_entradas_video_v2"
os.makedirs(PASTA_SAIDA, exist_ok=True)

PASTA_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoints_v2")
os.makedirs(PASTA_CHECKPOINT, exist_ok=True)

PASTA_BACKUP = os.path.join(PASTA_CHECKPOINT, "backups")
os.makedirs(PASTA_BACKUP, exist_ok=True)

ARQUIVO_ENTRADAS_LIMPAS = os.path.join(PASTA_SAIDA, "01_v2_entradas_video_limpas.csv")
ARQUIVO_FEATURES_ENTRADAS = os.path.join(PASTA_SAIDA, "02_v2_features_nas_entradas.csv")
ARQUIVO_DATASET_ML = os.path.join(PASTA_SAIDA, "03_v2_dataset_ml_treino.csv")
ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "04_v2_resultado_modelos.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "05_v2_importancia_features.csv")
ARQUIVO_SCORE = os.path.join(PASTA_SAIDA, "06_v2_score_todos_candles.csv")
ARQUIVO_FEATURES_BASE = os.path.join(PASTA_SAIDA, "07_v2_base_features_completa.csv")

ARQUIVO_CHECKPOINT_BASE = os.path.join(PASTA_CHECKPOINT, "checkpoint_base_features_v2.csv")
ARQUIVO_CHECKPOINT_DATASET = os.path.join(PASTA_CHECKPOINT, "checkpoint_dataset_ml_v2.csv")
ARQUIVO_CHECKPOINT_SCORE = os.path.join(PASTA_CHECKPOINT, "checkpoint_score_v2.csv")

# Separação temporal para validação fora da amostra
SPLIT_DATE = pd.Timestamp("2025-07-01")

# Quantidade de candles negativos para cada entrada real
MULTIPLICADOR_NEGATIVOS = 10

# Janela de horário usada para montar dataset
HORA_MIN_DATASET = 0.0
HORA_MAX_DATASET = 12.0

# Usar todos os núcleos disponíveis
N_JOBS_MODELOS = -1


# =====================================================
# FUNÇÕES DE BACKUP
# =====================================================

def timestamp_agora():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_arquivo(caminho):
    if os.path.exists(caminho):
        nome = os.path.basename(caminho)
        destino = os.path.join(PASTA_BACKUP, f"{timestamp_agora()}__{nome}")
        shutil.copy2(caminho, destino)
        print("Backup criado:", destino)


def salvar_csv(df, caminho):
    if os.path.exists(caminho):
        backup_arquivo(caminho)

    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print("Arquivo salvo:", caminho)


# =====================================================
# PARSE DE DATA/HORA DAS ENTRADAS
# =====================================================

def parse_data(valor):
    if pd.isna(valor):
        return pd.NaT

    if isinstance(valor, pd.Timestamp):
        return valor.normalize()

    if isinstance(valor, datetime):
        return pd.Timestamp(valor).normalize()

    if isinstance(valor, date):
        return pd.Timestamp(valor).normalize()

    if isinstance(valor, (int, float, np.integer, np.floating)):
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(int(valor), unit="D")

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return pd.NaT

    texto = texto.replace("20225", "2025")

    return pd.to_datetime(texto, errors="coerce", dayfirst=True).normalize()


def parse_hora(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, time):
        return valor

    if isinstance(valor, datetime):
        return valor.time()

    if isinstance(valor, pd.Timestamp):
        return valor.time()

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return None

    convertido = pd.to_datetime(texto, errors="coerce")

    if pd.isna(convertido):
        return None

    return convertido.time()


# =====================================================
# INDICADORES AUXILIARES
# =====================================================

def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    rs = media_ganho / media_perda.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def calcular_adx(df, periodo=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0)

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(
        alpha=1 / periodo,
        adjust=False,
        min_periods=periodo
    ).mean() / atr.replace(0, np.nan)

    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(
        alpha=1 / periodo,
        adjust=False,
        min_periods=periodo
    ).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    return adx, plus_di, minus_di


def calcular_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal

    return macd, macd_signal, macd_hist


def calcular_choppiness(df, periodo=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    tr_sum = tr.rolling(periodo).sum()
    high_max = high.rolling(periodo).max()
    low_min = low.rolling(periodo).min()

    chop = 100 * np.log10(tr_sum / (high_max - low_min).replace(0, np.nan)) / np.log10(periodo)

    return chop


# =====================================================
# FEATURES V2
# =====================================================

def criar_features_v2(df):
    df = df.copy()

    # -------------------------------------------------
    # BASE CANDLE
    # -------------------------------------------------

    df["ret_1"] = df["close"].pct_change()
    df["logret_1"] = np.log(df["close"] / df["close"].shift(1))

    df["range"] = df["high"] - df["low"]
    df["body"] = df["close"] - df["open"]
    df["body_abs"] = df["body"].abs()

    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    df["body_range_pct"] = df["body_abs"] / df["range"].replace(0, np.nan)
    df["close_pos_range"] = (df["close"] - df["low"]) / df["range"].replace(0, np.nan)

    df["candle_alta"] = (df["close"] > df["open"]).astype(int)
    df["candle_baixa"] = (df["close"] < df["open"]).astype(int)

    for n in [2, 3, 4, 5, 8, 10]:
        df[f"seq_alta_{n}"] = df["candle_alta"].rolling(n).sum()
        df[f"seq_baixa_{n}"] = df["candle_baixa"].rolling(n).sum()

    # -------------------------------------------------
    # RETORNOS / MOMENTUM
    # -------------------------------------------------

    for n in [2, 3, 5, 8, 10, 15, 20, 30, 45, 60, 90, 120]:
        df[f"ret_{n}"] = df["close"].pct_change(n)
        df[f"pts_change_{n}"] = df["close"] - df["close"].shift(n)

    for curto, longo in [(3, 10), (5, 20), (10, 30), (15, 60)]:
        df[f"aceleracao_ret_{curto}_{longo}"] = df[f"ret_{curto}"] - df[f"ret_{longo}"]

    # -------------------------------------------------
    # RANGE, VOLUME E FREQUÊNCIA
    # 2MV frequência aproximado:
    # volume/barCount relativo e frequência por horário
    # -------------------------------------------------

    for n in [3, 5, 10, 15, 20, 30, 60, 120]:
        df[f"range_ma_{n}"] = df["range"].rolling(n).mean()
        df[f"range_ratio_{n}"] = df["range"] / df[f"range_ma_{n}"].replace(0, np.nan)

        df[f"volume_ma_{n}"] = df["volume"].rolling(n).mean()
        df[f"volume_ratio_{n}"] = df["volume"] / df[f"volume_ma_{n}"].replace(0, np.nan)

        if "barCount" in df.columns:
            df[f"barcount_ma_{n}"] = df["barCount"].rolling(n).mean()
            df[f"barcount_ratio_{n}"] = df["barCount"] / df[f"barcount_ma_{n}"].replace(0, np.nan)

        df[f"volatilidade_ret_{n}"] = df["logret_1"].rolling(n).std()

    if "barCount" in df.columns:
        df["volume_por_negocio"] = df["volume"] / df["barCount"].replace(0, np.nan)
    else:
        df["volume_por_negocio"] = np.nan

    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
    df["HoraMin_SP"] = df["DataHora_SP"].dt.strftime("%H:%M")

    vol_por_horario = df.groupby("HoraMin_SP")["volume"].transform("median")
    df["volume_relativo_horario"] = df["volume"] / vol_por_horario.replace(0, np.nan)

    if "barCount" in df.columns:
        bc_por_horario = df.groupby("HoraMin_SP")["barCount"].transform("median")
        df["barcount_relativo_horario"] = df["barCount"] / bc_por_horario.replace(0, np.nan)
    else:
        df["barcount_relativo_horario"] = np.nan

    # -------------------------------------------------
    # MÉDIAS / TREND CLOUD APROXIMADO
    # -------------------------------------------------

    emas = [5, 8, 9, 13, 17, 20, 21, 34, 50, 72, 100, 144, 200]

    for n in emas:
        df[f"ema_{n}"] = df["close"].ewm(span=n, adjust=False).mean()
        df[f"dist_ema_{n}"] = df["close"] - df[f"ema_{n}"]
        df[f"dist_ema_{n}_pct"] = df[f"dist_ema_{n}"] / df["close"] * 100
        df[f"ema_{n}_slope_3"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(3)
        df[f"ema_{n}_slope_5"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(5)
        df[f"ema_{n}_slope_10"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(10)

    cloud_pairs = [
        (9, 17),
        (17, 34),
        (20, 50),
        (34, 72),
        (50, 100),
        (100, 200),
    ]

    for a, b in cloud_pairs:
        top = df[[f"ema_{a}", f"ema_{b}"]].max(axis=1)
        bottom = df[[f"ema_{a}", f"ema_{b}"]].min(axis=1)

        df[f"trend_cloud_{a}_{b}_bull"] = (df[f"ema_{a}"] > df[f"ema_{b}"]).astype(int)
        df[f"trend_cloud_{a}_{b}_thickness"] = top - bottom
        df[f"trend_cloud_{a}_{b}_thickness_pct"] = (top - bottom) / df["close"] * 100

        df[f"trend_cloud_{a}_{b}_dist_top"] = df["close"] - top
        df[f"trend_cloud_{a}_{b}_dist_bottom"] = df["close"] - bottom
        df[f"trend_cloud_{a}_{b}_pos"] = (df["close"] - bottom) / (top - bottom).replace(0, np.nan)

    df["ema17_acima_ema34"] = (df["ema_17"] > df["ema_34"]).astype(int)
    df["ema9_acima_ema17"] = (df["ema_9"] > df["ema_17"]).astype(int)
    df["close_acima_ema17"] = (df["close"] > df["ema_17"]).astype(int)
    df["close_acima_ema34"] = (df["close"] > df["ema_34"]).astype(int)
    df["dist_ema17_34"] = df["ema_17"] - df["ema_34"]
    df["dist_ema17_34_pct"] = df["dist_ema17_34"] / df["close"] * 100

    # -------------------------------------------------
    # BIAS
    # -------------------------------------------------

    for n in [6, 9, 12, 17, 20, 23, 24, 34, 50]:
        sma = df["close"].rolling(n).mean()
        df[f"bias_{n}"] = (df["close"] - sma) / sma * 100

    # -------------------------------------------------
    # RSI / STOCH RSI
    # -------------------------------------------------

    for n in [5, 7, 8, 9, 14, 21, 34]:
        df[f"rsi_{n}"] = calcular_rsi(df["close"], n)
        df[f"rsi_{n}_slope_3"] = df[f"rsi_{n}"] - df[f"rsi_{n}"].shift(3)

    for n in [8, 14, 21]:
        rsi_col = df[f"rsi_{n}"]
        minimo = rsi_col.rolling(n).min()
        maximo = rsi_col.rolling(n).max()

        stoch = 100 * (rsi_col - minimo) / (maximo - minimo).replace(0, np.nan)

        df[f"stochrsi_{n}_raw"] = stoch
        df[f"stochrsi_{n}_k"] = stoch.rolling(3).mean()
        df[f"stochrsi_{n}_d"] = df[f"stochrsi_{n}_k"].rolling(3).mean()
        df[f"stochrsi_{n}_k_menos_d"] = df[f"stochrsi_{n}_k"] - df[f"stochrsi_{n}_d"]

    # -------------------------------------------------
    # ATR / TR PONTOS DE DECISÃO APROXIMADO
    # -------------------------------------------------

    prev_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["true_range"] = tr

    for n in [5, 7, 10, 14, 18, 21, 34]:
        df[f"atr_{n}"] = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        df[f"atrp_{n}"] = df[f"atr_{n}"] / df["close"] * 100
        df[f"tr_ratio_atr_{n}"] = tr / df[f"atr_{n}"].replace(0, np.nan)

        df[f"tr_decision_up_{n}"] = df["close"].shift(1) + df[f"atr_{n}"]
        df[f"tr_decision_down_{n}"] = df["close"].shift(1) - df[f"atr_{n}"]

        df[f"dist_tr_decision_up_{n}"] = df["close"] - df[f"tr_decision_up_{n}"]
        df[f"dist_tr_decision_down_{n}"] = df["close"] - df[f"tr_decision_down_{n}"]

        df[f"rompeu_decision_up_{n}"] = (df["high"] >= df[f"tr_decision_up_{n}"]).astype(int)
        df[f"rompeu_decision_down_{n}"] = (df["low"] <= df[f"tr_decision_down_{n}"]).astype(int)

    # -------------------------------------------------
    # BOLLINGER / KELTNER / SQUEEZE
    # -------------------------------------------------

    for n in [20, 34, 50]:
        media = df["close"].rolling(n).mean()
        desvio = df["close"].rolling(n).std()

        upper = media + 2 * desvio
        lower = media - 2 * desvio

        df[f"bb_mid_{n}"] = media
        df[f"bb_upper_{n}"] = upper
        df[f"bb_lower_{n}"] = lower
        df[f"bb_width_{n}"] = (upper - lower) / media * 100
        df[f"bb_pos_{n}"] = (df["close"] - lower) / (upper - lower).replace(0, np.nan)
        df[f"dist_bb_upper_{n}"] = df["close"] - upper
        df[f"dist_bb_lower_{n}"] = df["close"] - lower

    for n in [20, 34]:
        ema_mid = df["close"].ewm(span=n, adjust=False).mean()
        atr_n = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()

        kc_upper = ema_mid + 2 * atr_n
        kc_lower = ema_mid - 2 * atr_n

        df[f"kc_mid_{n}"] = ema_mid
        df[f"kc_upper_{n}"] = kc_upper
        df[f"kc_lower_{n}"] = kc_lower
        df[f"kc_width_{n}"] = (kc_upper - kc_lower) / ema_mid * 100
        df[f"kc_pos_{n}"] = (df["close"] - kc_lower) / (kc_upper - kc_lower).replace(0, np.nan)
        df[f"dist_kc_upper_{n}"] = df["close"] - kc_upper
        df[f"dist_kc_lower_{n}"] = df["close"] - kc_lower

    df["squeeze_bb20_dentro_kc20"] = (
        (df["bb_upper_20"] < df["kc_upper_20"]) &
        (df["bb_lower_20"] > df["kc_lower_20"])
    ).astype(int)

    df["bb20_width_menos_kc20_width"] = df["bb_width_20"] - df["kc_width_20"]

    # -------------------------------------------------
    # VWAP DIÁRIO
    # -------------------------------------------------

    df["Data_SP"] = df["DataHora_SP"].dt.date

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, np.nan)

    df["tpv"] = typical_price * vol

    df["cum_tpv_dia"] = df.groupby("Data_SP")["tpv"].cumsum()
    df["cum_vol_dia"] = df.groupby("Data_SP")["volume"].cumsum()

    df["vwap_dia"] = df["cum_tpv_dia"] / df["cum_vol_dia"].replace(0, np.nan)
    df["dist_vwap_dia"] = df["close"] - df["vwap_dia"]
    df["dist_vwap_dia_pct"] = df["dist_vwap_dia"] / df["close"] * 100
    df["close_acima_vwap"] = (df["close"] > df["vwap_dia"]).astype(int)
    df["vwap_slope_5"] = df["vwap_dia"] - df["vwap_dia"].shift(5)

    # -------------------------------------------------
    # ESTRUTURA DE MERCADO / PIVÔS
    # -------------------------------------------------

    for n in [3, 5, 10, 15, 20, 30, 50, 60, 120]:
        df[f"high_max_{n}"] = df["high"].rolling(n).max()
        df[f"low_min_{n}"] = df["low"].rolling(n).min()

        df[f"dist_high_max_{n}"] = df["close"] - df[f"high_max_{n}"]
        df[f"dist_low_min_{n}"] = df["close"] - df[f"low_min_{n}"]

        df[f"pos_range_{n}"] = (df["close"] - df[f"low_min_{n}"]) / (
            df[f"high_max_{n}"] - df[f"low_min_{n}"]
        ).replace(0, np.nan)

        df[f"rompeu_max_{n}"] = (df["high"] >= df[f"high_max_{n}"].shift(1)).astype(int)
        df[f"rompeu_min_{n}"] = (df["low"] <= df[f"low_min_{n}"].shift(1)).astype(int)

    pivot_left = 2
    pivot_right = 2

    df["pivot_high_aprox"] = (
        df["high"].shift(pivot_right) == df["high"].rolling(pivot_left + pivot_right + 1).max()
    ).astype(int)

    df["pivot_low_aprox"] = (
        df["low"].shift(pivot_right) == df["low"].rolling(pivot_left + pivot_right + 1).min()
    ).astype(int)

    df["bars_desde_pivot_high"] = np.nan
    df["bars_desde_pivot_low"] = np.nan

    bars_high = 9999
    bars_low = 9999

    for i in range(len(df)):
        if df.loc[i, "pivot_high_aprox"] == 1:
            bars_high = 0
        else:
            bars_high += 1

        if df.loc[i, "pivot_low_aprox"] == 1:
            bars_low = 0
        else:
            bars_low += 1

        df.loc[i, "bars_desde_pivot_high"] = bars_high
        df.loc[i, "bars_desde_pivot_low"] = bars_low

    # -------------------------------------------------
    # MACD / ADX / CHOPPINESS
    # -------------------------------------------------

    macd, macd_signal, macd_hist = calcular_macd(df["close"], 12, 26, 9)

    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist
    df["macd_hist_slope_3"] = df["macd_hist"] - df["macd_hist"].shift(3)

    for n in [7, 14, 21]:
        adx, plus_di, minus_di = calcular_adx(df, n)
        df[f"adx_{n}"] = adx
        df[f"plus_di_{n}"] = plus_di
        df[f"minus_di_{n}"] = minus_di
        df[f"di_diff_{n}"] = plus_di - minus_di

    for n in [14, 21, 34]:
        df[f"choppiness_{n}"] = calcular_choppiness(df, n)

    # -------------------------------------------------
    # HORÁRIO / JANELAS ESPECÍFICAS
    # -------------------------------------------------

    df["dia_semana_sp"] = df["DataHora_SP"].dt.dayofweek
    df["minuto_sp"] = df["DataHora_SP"].dt.minute
    df["hora_sp"] = df["DataHora_SP"].dt.hour

    df["sin_hora_sp"] = np.sin(2 * np.pi * df["Hora_SP_Decimal"] / 24)
    df["cos_hora_sp"] = np.cos(2 * np.pi * df["Hora_SP_Decimal"] / 24)

    df["eh_0348"] = (df["HoraMin_SP"] == "03:48").astype(int)
    df["eh_0448"] = (df["HoraMin_SP"] == "04:48").astype(int)

    df["janela_0340_0400"] = (
        (df["HoraMin_SP"] >= "03:40") &
        (df["HoraMin_SP"] <= "04:00")
    ).astype(int)

    df["janela_0430_0500"] = (
        (df["HoraMin_SP"] >= "04:30") &
        (df["HoraMin_SP"] <= "05:00")
    ).astype(int)

    df["janela_0300_0600"] = (
        (df["Hora_SP_Decimal"] >= 3.0) &
        (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    df["janela_0000_0600"] = (
        (df["Hora_SP_Decimal"] >= 0.0) &
        (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    # -------------------------------------------------
    # LIMPEZA
    # -------------------------------------------------

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.copy()

    return df


# =====================================================
# CARREGAR PREÇOS
# =====================================================

print("Carregando preços...")

precos = pd.read_csv(ARQUIVO_PRECOS)

precos["DataHora_SP"] = pd.to_datetime(precos["DataHora_SP"])
precos["DataHora_Chicago"] = pd.to_datetime(precos["DataHora_Chicago"], errors="coerce")

precos = precos.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume"]:
    precos[col] = pd.to_numeric(precos[col], errors="coerce")

if "average" in precos.columns:
    precos["average"] = pd.to_numeric(precos["average"], errors="coerce")
else:
    precos["average"] = np.nan

if "barCount" in precos.columns:
    precos["barCount"] = pd.to_numeric(precos["barCount"], errors="coerce")
else:
    precos["barCount"] = np.nan

print("Preços carregados:", len(precos))
print("Início:", precos["DataHora_SP"].min())
print("Fim:", precos["DataHora_SP"].max())


# =====================================================
# LIMPAR ENTRADAS DO VÍDEO
# =====================================================

print("Limpando entradas do vídeo...")

entradas_raw = pd.read_excel(ARQUIVO_ENTRADAS)

entradas_raw["data_limpa"] = entradas_raw["data"].apply(parse_data)
entradas_raw["data_corrigida"] = entradas_raw["data_limpa"].ffill()
entradas_raw["hora_limpa"] = entradas_raw["hora"].apply(parse_hora)

entradas_raw["Sinal_limpo"] = entradas_raw["Sinal"].astype(str).str.strip().str.lower()

entradas = entradas_raw[entradas_raw["Sinal_limpo"].isin(["comprar", "vender"])].copy()

entradas["DataHora_Video"] = [
    pd.Timestamp.combine(d.date(), h)
    if pd.notna(d) and h is not None
    else pd.NaT
    for d, h in zip(entradas["data_corrigida"], entradas["hora_limpa"])
]

entradas["Direcao"] = entradas["Sinal_limpo"].map({
    "comprar": "BUY",
    "vender": "SELL"
})

entradas = entradas.dropna(subset=["DataHora_Video"]).copy()

colunas_possiveis = [
    "DataHora_Video",
    "Direcao",
    "preço",
    "tamanho",
    "lucro",
    "Ru-up",
    "Drawdown",
    "L&p"
]

colunas_existentes = [c for c in colunas_possiveis if c in entradas.columns]

entradas = entradas[colunas_existentes].copy()

entradas["Data"] = entradas["DataHora_Video"].dt.date.astype(str)
entradas["Hora"] = entradas["DataHora_Video"].dt.time.astype(str)

salvar_csv(entradas, ARQUIVO_ENTRADAS_LIMPAS)

print("Entradas limpas:", len(entradas))
print(entradas["Direcao"].value_counts())


# =====================================================
# CRIAR FEATURES
# =====================================================

print("Criando features V2...")

base = criar_features_v2(precos)

print("Features criadas. Colunas:", len(base.columns))

salvar_csv(base, ARQUIVO_CHECKPOINT_BASE)
salvar_csv(base, ARQUIVO_FEATURES_BASE)


# =====================================================
# LABELS
# =====================================================

base["Label"] = 0
base["Label_Nome"] = "NONE"
base["Preco_Entrada_Video"] = np.nan

mapa_label = {
    "BUY": 1,
    "SELL": 2
}

for _, row in entradas.iterrows():
    dt_entrada = row["DataHora_Video"]
    direcao = row["Direcao"]

    idx = base.index[base["DataHora_SP"] == dt_entrada]

    if len(idx) > 0:
        i = idx[0]
        base.loc[i, "Label"] = mapa_label[direcao]
        base.loc[i, "Label_Nome"] = direcao

        if "preço" in row.index:
            base.loc[i, "Preco_Entrada_Video"] = row["preço"]


# =====================================================
# FEATURES DO CANDLE ANTERIOR
# =====================================================

colunas_nao_features = [
    "DataHora_Chicago",
    "Data_Chicago",
    "Hora_Chicago",
    "DataHora_SP",
    "Data_SP",
    "Hora_SP",
    "DataHora_UTC",
    "DataHora_Video",
    "Data",
    "Hora",
    "HoraMin_SP",
    "contrato",
    "localSymbol",
    "Label",
    "Label_Nome",
    "Preco_Entrada_Video",
]

feature_cols = []

for col in base.columns:
    if col not in colunas_nao_features:
        if pd.api.types.is_numeric_dtype(base[col]):
            feature_cols.append(col)

features_previas = base[feature_cols].shift(1)
features_previas.columns = ["prev_" + c for c in features_previas.columns]

dataset = pd.concat([
    base[[
        "DataHora_SP",
        "DataHora_Chicago",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "Label",
        "Label_Nome",
        "Preco_Entrada_Video"
    ]],
    features_previas
], axis=1)

if "contrato" in base.columns:
    dataset["contrato"] = base["contrato"]
else:
    dataset["contrato"] = ""

if "localSymbol" in base.columns:
    dataset["localSymbol"] = base["localSymbol"]
else:
    dataset["localSymbol"] = ""

dataset["Hora_SP_Decimal"] = dataset["DataHora_SP"].dt.hour + dataset["DataHora_SP"].dt.minute / 60

inicio = entradas["DataHora_Video"].min().normalize()
fim = entradas["DataHora_Video"].max().normalize() + pd.Timedelta(days=1)

dataset_periodo = dataset[
    (dataset["DataHora_SP"] >= inicio) &
    (dataset["DataHora_SP"] < fim)
].copy()

dataset_periodo = dataset_periodo[
    (dataset_periodo["Hora_SP_Decimal"] >= HORA_MIN_DATASET) &
    (dataset_periodo["Hora_SP_Decimal"] <= HORA_MAX_DATASET)
].copy()


# =====================================================
# NEGATIVOS
# =====================================================

print("Montando dataset ML...")

positivos = dataset_periodo[dataset_periodo["Label"] > 0].copy()

dataset_periodo["Perto_Entrada"] = False

for dt_entrada in positivos["DataHora_SP"]:
    mascara = (
        (dataset_periodo["DataHora_SP"] >= dt_entrada - pd.Timedelta(minutes=10)) &
        (dataset_periodo["DataHora_SP"] <= dt_entrada + pd.Timedelta(minutes=10))
    )
    dataset_periodo.loc[mascara, "Perto_Entrada"] = True

negativos_pool = dataset_periodo[
    (dataset_periodo["Label"] == 0) &
    (~dataset_periodo["Perto_Entrada"])
].copy()

quantidade_negativos = min(len(negativos_pool), len(positivos) * MULTIPLICADOR_NEGATIVOS)

negativos = negativos_pool.sample(
    n=quantidade_negativos,
    random_state=42
)

dataset_ml = pd.concat([positivos, negativos], ignore_index=True)
dataset_ml = dataset_ml.sort_values("DataHora_SP").reset_index(drop=True)

feature_ml_cols = [
    c for c in dataset_ml.columns
    if c.startswith("prev_")
]

missing = dataset_ml[feature_ml_cols].isna().mean()
feature_ml_cols = [
    c for c in feature_ml_cols
    if missing[c] < 0.30
]

salvar_csv(dataset_ml, ARQUIVO_DATASET_ML)
salvar_csv(dataset_ml, ARQUIVO_CHECKPOINT_DATASET)

features_nas_entradas = dataset_ml[dataset_ml["Label"] > 0].copy()
salvar_csv(features_nas_entradas, ARQUIVO_FEATURES_ENTRADAS)

print("Dataset ML:")
print(dataset_ml["Label_Nome"].value_counts())
print("Features usadas:", len(feature_ml_cols))


# =====================================================
# TREINAR MODELOS
# =====================================================

print("Treinando modelos V2...")

X = dataset_ml[feature_ml_cols]
y = dataset_ml["Label"]

train_mask = dataset_ml["DataHora_SP"] < SPLIT_DATE

X_train = X[train_mask]
y_train = y[train_mask]

X_test = X[~train_mask]
y_test = y[~train_mask]

modelos = {
    "RandomForest_V2": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=N_JOBS_MODELOS
        ))
    ]),

    "ExtraTrees_V2": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(
            n_estimators=400,
            max_depth=8,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=N_JOBS_MODELOS
        ))
    ]),

    "HistGradientBoosting_V2": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.04,
            max_leaf_nodes=20,
            l2_regularization=0.2,
            random_state=42
        ))
    ])
}

resultados = []
melhor_modelo = None
melhor_nome = None
melhor_score = -999

for nome, modelo in modelos.items():
    print("\n====================================")
    print("Treinando:", nome)
    print("====================================")

    modelo.fit(X_train, y_train)

    pred = modelo.predict(X_test)

    acc = accuracy_score(y_test, pred)
    bacc = balanced_accuracy_score(y_test, pred)

    print("Accuracy:", acc)
    print("Balanced Accuracy:", bacc)
    print(confusion_matrix(y_test, pred))
    print(classification_report(y_test, pred, zero_division=0))

    resultados.append({
        "modelo": nome,
        "accuracy": acc,
        "balanced_accuracy": bacc,
        "treino_linhas": len(X_train),
        "teste_linhas": len(X_test),
        "features": len(feature_ml_cols),
        "split_date": str(SPLIT_DATE)
    })

    if bacc > melhor_score:
        melhor_score = bacc
        melhor_modelo = modelo
        melhor_nome = nome

resultados_df = pd.DataFrame(resultados)
salvar_csv(resultados_df, ARQUIVO_RESULTADOS)

print("\nMelhor modelo V2:", melhor_nome)


# =====================================================
# IMPORTÂNCIA DAS FEATURES
# =====================================================

modelo_interno = melhor_modelo.named_steps["model"]

if hasattr(modelo_interno, "feature_importances_"):
    importancia = pd.DataFrame({
        "feature": feature_ml_cols,
        "importancia": modelo_interno.feature_importances_
    }).sort_values("importancia", ascending=False)
else:
    importancia = pd.DataFrame({
        "feature": feature_ml_cols,
        "importancia": np.nan
    })

salvar_csv(importancia, ARQUIVO_IMPORTANCIA)

print("\nTop 40 features:")
print(importancia.head(40))


# =====================================================
# GERAR SCORE PARA TODOS OS CANDLES
# =====================================================

print("Gerando score V2 para todos os candles...")

dataset_score = dataset.copy()

X_score = dataset_score[feature_ml_cols]

probas = melhor_modelo.predict_proba(X_score)

classes = list(melhor_modelo.named_steps["model"].classes_)

dataset_score["score_NONE"] = 0.0
dataset_score["score_BUY"] = 0.0
dataset_score["score_SELL"] = 0.0

for i, classe in enumerate(classes):
    if classe == 0:
        dataset_score["score_NONE"] = probas[:, i]
    elif classe == 1:
        dataset_score["score_BUY"] = probas[:, i]
    elif classe == 2:
        dataset_score["score_SELL"] = probas[:, i]

dataset_score["Sinal_ML"] = "NONE"

dataset_score.loc[
    (dataset_score["score_BUY"] >= 0.70) &
    (dataset_score["score_BUY"] > dataset_score["score_SELL"]),
    "Sinal_ML"
] = "BUY"

dataset_score.loc[
    (dataset_score["score_SELL"] >= 0.70) &
    (dataset_score["score_SELL"] > dataset_score["score_BUY"]),
    "Sinal_ML"
] = "SELL"

colunas_saida = [
    "DataHora_SP",
    "DataHora_Chicago",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "contrato",
    "localSymbol",
    "Label_Nome",
    "Preco_Entrada_Video",
    "score_BUY",
    "score_SELL",
    "score_NONE",
    "Sinal_ML"
]

for col in colunas_saida:
    if col not in dataset_score.columns:
        dataset_score[col] = ""

score_saida = dataset_score[colunas_saida].copy()

salvar_csv(score_saida, ARQUIVO_SCORE)
salvar_csv(score_saida, ARQUIVO_CHECKPOINT_SCORE)


# =====================================================
# FINAL
# =====================================================

print("\n=====================================================")
print("FINALIZADO V2")
print("=====================================================")
print("Entradas limpas:", ARQUIVO_ENTRADAS_LIMPAS)
print("Features nas entradas:", ARQUIVO_FEATURES_ENTRADAS)
print("Dataset treino:", ARQUIVO_DATASET_ML)
print("Resultados modelos:", ARQUIVO_RESULTADOS)
print("Importância features:", ARQUIVO_IMPORTANCIA)
print("Score todos candles:", ARQUIVO_SCORE)
print("Base features completa:", ARQUIVO_FEATURES_BASE)
print("Pasta checkpoints:", PASTA_CHECKPOINT)