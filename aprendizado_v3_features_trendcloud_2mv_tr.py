import pandas as pd
import numpy as np
import os
from datetime import datetime, date, time

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, balanced_accuracy_score


# =====================================================
# CONFIGURAÇÕES WINDOWS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

ARQUIVO_PRECOS = os.path.join(BASE_DIR, "MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv")
ARQUIVO_ENTRADAS = os.path.join(BASE_DIR, "Entrada video-priemira amostra.xlsx")

PASTA_SAIDA = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")
os.makedirs(PASTA_SAIDA, exist_ok=True)

PASTA_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoints_v3")
os.makedirs(PASTA_CHECKPOINT, exist_ok=True)

ARQUIVO_ENTRADAS_LIMPAS = os.path.join(PASTA_SAIDA, "01_v3_entradas_video_limpas.csv")
ARQUIVO_DATASET_ML = os.path.join(PASTA_SAIDA, "02_v3_dataset_ml_treino.csv.gz")
ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "03_v3_resultado_modelos.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "04_v3_importancia_features.csv")
ARQUIVO_SCORE = os.path.join(PASTA_SAIDA, "05_v3_score_todos_candles.csv.gz")

SPLIT_DATE = pd.Timestamp("2025-07-01")
MULTIPLICADOR_NEGATIVOS = 10
HORA_MIN_DATASET = 0.0
HORA_MAX_DATASET = 12.0

# Usa todos os núcleos disponíveis
N_JOBS_MODELOS = -1


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def salvar_csv(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(
            temp,
            index=False,
            encoding="utf-8-sig",
            compression="gzip"
        )
    else:
        df.to_csv(
            temp,
            index=False,
            encoding="utf-8-sig"
        )

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def find_col(df, nomes_possiveis):
    cols = {c.lower().strip(): c for c in df.columns}

    for n in nomes_possiveis:
        n2 = n.lower().strip()

        if n2 in cols:
            return cols[n2]

    return None


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


def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    rs = media_ganho / media_perda.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def calcular_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line

    return macd, signal_line, hist


def calcular_adx(df, periodo=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

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

    chop = 100 * np.log10(
        tr_sum / (high_max - low_min).replace(0, np.nan)
    ) / np.log10(periodo)

    return chop


# =====================================================
# FEATURES V3
# =====================================================

def criar_features_v3(df):
    df = df.copy()

    # =================================================
    # CANDLE
    # =================================================

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

    # =================================================
    # HORÁRIO
    # =================================================

    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
    df["HoraMin_SP"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["hora_sp"] = df["DataHora_SP"].dt.hour
    df["minuto_sp"] = df["DataHora_SP"].dt.minute
    df["dia_semana_sp"] = df["DataHora_SP"].dt.dayofweek
    df["mes_sp"] = df["DataHora_SP"].dt.month

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

    df["janela_0000_0600"] = (
        (df["Hora_SP_Decimal"] >= 0.0) &
        (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    df["janela_0300_0600"] = (
        (df["Hora_SP_Decimal"] >= 3.0) &
        (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    # =================================================
    # RETORNO / MOMENTUM
    # =================================================

    df["logret_1"] = np.log(df["close"] / df["close"].shift(1))

    for n in [1, 2, 3, 5, 8, 10, 15, 20, 30, 45, 60, 90, 120]:
        df[f"ret_{n}"] = df["close"].pct_change(n)
        df[f"pts_change_{n}"] = df["close"] - df["close"].shift(n)

    for curto, longo in [(3, 10), (5, 20), (10, 30), (15, 60)]:
        df[f"aceleracao_ret_{curto}_{longo}"] = df[f"ret_{curto}"] - df[f"ret_{longo}"]

    # =================================================
    # VOLUME / 2MV FREQUÊNCIA APROXIMADO
    # =================================================

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

    vol_med_hora = df.groupby("HoraMin_SP")["volume"].transform("median")
    df["volume_relativo_horario"] = df["volume"] / vol_med_hora.replace(0, np.nan)

    if "barCount" in df.columns:
        bc_med_hora = df.groupby("HoraMin_SP")["barCount"].transform("median")
        df["barcount_relativo_horario"] = df["barCount"] / bc_med_hora.replace(0, np.nan)
    else:
        df["barcount_relativo_horario"] = np.nan

    # =================================================
    # EMAS / TREND CLOUD
    # =================================================

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

    # =================================================
    # BIAS
    # =================================================

    for n in [6, 9, 12, 17, 20, 23, 24, 34, 50]:
        sma = df["close"].rolling(n).mean()
        df[f"bias_{n}"] = (df["close"] - sma) / sma * 100

    # =================================================
    # RSI / STOCH RSI
    # =================================================

    for n in [5, 7, 8, 9, 14, 21, 34]:
        df[f"rsi_{n}"] = calcular_rsi(df["close"], n)
        df[f"rsi_{n}_slope_3"] = df[f"rsi_{n}"] - df[f"rsi_{n}"].shift(3)

    for n in [8, 14, 21]:
        rsi = df[f"rsi_{n}"]
        minimo = rsi.rolling(n).min()
        maximo = rsi.rolling(n).max()

        stoch = 100 * (rsi - minimo) / (maximo - minimo).replace(0, np.nan)

        df[f"stochrsi_{n}_raw"] = stoch
        df[f"stochrsi_{n}_k"] = stoch.rolling(3).mean()
        df[f"stochrsi_{n}_d"] = df[f"stochrsi_{n}_k"].rolling(3).mean()
        df[f"stochrsi_{n}_k_menos_d"] = df[f"stochrsi_{n}_k"] - df[f"stochrsi_{n}_d"]

    # =================================================
    # TRUE RANGE / TR PONTOS DE DECISÃO
    # =================================================

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

    # =================================================
    # BOLLINGER / KELTNER / SQUEEZE
    # =================================================

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

    # =================================================
    # VWAP DIÁRIO
    # =================================================

    df["Data_SP"] = df["DataHora_SP"].dt.date

    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0, np.nan)

    df["tpv"] = tp * vol
    df["cum_tpv_dia"] = df.groupby("Data_SP")["tpv"].cumsum()
    df["cum_vol_dia"] = df.groupby("Data_SP")["volume"].cumsum()

    df["vwap_dia"] = df["cum_tpv_dia"] / df["cum_vol_dia"].replace(0, np.nan)
    df["dist_vwap_dia"] = df["close"] - df["vwap_dia"]
    df["dist_vwap_dia_pct"] = df["dist_vwap_dia"] / df["close"] * 100
    df["close_acima_vwap"] = (df["close"] > df["vwap_dia"]).astype(int)
    df["vwap_slope_5"] = df["vwap_dia"] - df["vwap_dia"].shift(5)

    # =================================================
    # ESTRUTURA DE MERCADO
    # =================================================

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

    # =================================================
    # MACD / ADX / CHOPPINESS
    # =================================================

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

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.copy()

    return df


# =====================================================
# CARREGAR PREÇOS
# =====================================================

print("Carregando preços...")

if not os.path.exists(ARQUIVO_PRECOS):
    raise FileNotFoundError(f"Arquivo de preços não encontrado: {ARQUIVO_PRECOS}")

if not os.path.exists(ARQUIVO_ENTRADAS):
    raise FileNotFoundError(f"Arquivo de entradas não encontrado: {ARQUIVO_ENTRADAS}")

precos = pd.read_csv(ARQUIVO_PRECOS)

precos["DataHora_SP"] = pd.to_datetime(precos["DataHora_SP"])
precos["DataHora_Chicago"] = pd.to_datetime(precos["DataHora_Chicago"], errors="coerce")

precos = precos.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume"]:
    precos[col] = pd.to_numeric(precos[col], errors="coerce")

if "barCount" in precos.columns:
    precos["barCount"] = pd.to_numeric(precos["barCount"], errors="coerce")
else:
    precos["barCount"] = np.nan

if "average" in precos.columns:
    precos["average"] = pd.to_numeric(precos["average"], errors="coerce")
else:
    precos["average"] = np.nan

print("Preços:", len(precos))
print("Início:", precos["DataHora_SP"].min())
print("Fim:", precos["DataHora_SP"].max())


# =====================================================
# CARREGAR ENTRADAS
# =====================================================

print("Carregando entradas do vídeo...")

entradas_raw = pd.read_excel(ARQUIVO_ENTRADAS)

col_data = find_col(entradas_raw, ["data", "date"])
col_hora = find_col(entradas_raw, ["hora", "time"])
col_sinal = find_col(entradas_raw, ["sinal", "signal", "direcao", "direção"])

if col_data is None or col_hora is None or col_sinal is None:
    raise Exception("Não encontrei colunas de data/hora/sinal na planilha de entradas.")

entradas_raw["data_limpa"] = entradas_raw[col_data].apply(parse_data)
entradas_raw["data_corrigida"] = entradas_raw["data_limpa"].ffill()
entradas_raw["hora_limpa"] = entradas_raw[col_hora].apply(parse_hora)

entradas_raw["Sinal_limpo"] = entradas_raw[col_sinal].astype(str).str.strip().str.lower()

entradas = entradas_raw[
    entradas_raw["Sinal_limpo"].isin(["comprar", "vender", "buy", "sell"])
].copy()

entradas["DataHora_Video"] = [
    pd.Timestamp.combine(d.date(), h)
    if pd.notna(d) and h is not None
    else pd.NaT
    for d, h in zip(entradas["data_corrigida"], entradas["hora_limpa"])
]

entradas["Direcao"] = entradas["Sinal_limpo"].map({
    "comprar": "BUY",
    "buy": "BUY",
    "vender": "SELL",
    "sell": "SELL"
})

entradas = entradas.dropna(subset=["DataHora_Video"]).copy()
entradas = entradas[["DataHora_Video", "Direcao"]].copy()

salvar_csv(entradas, ARQUIVO_ENTRADAS_LIMPAS, compactado=False)

print("Entradas:", len(entradas))
print(entradas["Direcao"].value_counts())


# =====================================================
# CRIAR FEATURES
# =====================================================

print("Criando features V3...")

base = criar_features_v3(precos)

print("Colunas com features:", len(base.columns))


# =====================================================
# LABELS
# =====================================================

base["Label"] = 0
base["Label_Nome"] = "NONE"

mapa_label = {
    "BUY": 1,
    "SELL": 2
}

base_dt_index = pd.Index(base["DataHora_SP"])

for _, row in entradas.iterrows():
    dt_entrada = row["DataHora_Video"]
    direcao = row["Direcao"]

    idx = base.index[base["DataHora_SP"] == dt_entrada]

    if len(idx) == 0:
        pos = base_dt_index.get_indexer(
            [dt_entrada],
            method="nearest",
            tolerance=pd.Timedelta(minutes=1)
        )

        if pos[0] != -1:
            idx = [pos[0]]

    if len(idx) > 0:
        i = int(idx[0])
        base.loc[i, "Label"] = mapa_label[direcao]
        base.loc[i, "Label_Nome"] = direcao


# =====================================================
# DATASET COM FEATURES DO CANDLE ANTERIOR
# =====================================================

nao_features = [
    "DataHora_SP",
    "DataHora_Chicago",
    "Data_SP",
    "HoraMin_SP",
    "contrato",
    "localSymbol",
    "Label",
    "Label_Nome",
]

feature_cols = []

for col in base.columns:
    if col not in nao_features:
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
        "Label_Nome"
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

qtd_negativos = min(len(negativos_pool), len(positivos) * MULTIPLICADOR_NEGATIVOS)

negativos = negativos_pool.sample(
    n=qtd_negativos,
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

salvar_csv(dataset_ml, ARQUIVO_DATASET_ML, compactado=True)

print("Dataset ML:")
print(dataset_ml["Label_Nome"].value_counts())
print("Features usadas:", len(feature_ml_cols))


# =====================================================
# TREINAR MODELOS
# =====================================================

X = dataset_ml[feature_ml_cols]
y = dataset_ml["Label"]

train_mask = dataset_ml["DataHora_SP"] < SPLIT_DATE

X_train = X[train_mask]
y_train = y[train_mask]

X_test = X[~train_mask]
y_test = y[~train_mask]

modelos = {
    "RandomForest_V3": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400,
            max_depth=9,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=N_JOBS_MODELOS
        ))
    ]),

    "ExtraTrees_V3": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(
            n_estimators=500,
            max_depth=9,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=N_JOBS_MODELOS
        ))
    ]),

    "HistGradientBoosting_V3": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.035,
            max_leaf_nodes=20,
            l2_regularization=0.25,
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
salvar_csv(resultados_df, ARQUIVO_RESULTADOS, compactado=False)

print("\nMelhor modelo:", melhor_nome)


# =====================================================
# IMPORTÂNCIA
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

salvar_csv(importancia, ARQUIVO_IMPORTANCIA, compactado=False)

print("\nTop 50 features:")
print(importancia.head(50))


# =====================================================
# SCORE PARA TODOS OS CANDLES
# =====================================================

print("Gerando score V3...")

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

colunas_score = [
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
    "score_BUY",
    "score_SELL",
    "score_NONE",
    "Sinal_ML"
]

for col in colunas_score:
    if col not in dataset_score.columns:
        dataset_score[col] = ""

score_saida = dataset_score[colunas_score].copy()

salvar_csv(score_saida, ARQUIVO_SCORE, compactado=True)

print("\n=====================================================")
print("FINALIZADO SCORE V3")
print("=====================================================")
print("Score V3:", ARQUIVO_SCORE)
print("Resultados:", ARQUIVO_RESULTADOS)
print("Importância:", ARQUIVO_IMPORTANCIA)