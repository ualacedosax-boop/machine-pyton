import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


warnings.filterwarnings("ignore")


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQUIVO_CANDLES_2026 = (
    BASE_DIR
    / "dados_mnq_2026_ibkr"
    / "MNQ_2026_2MIN_IBKR_CONTINUO.csv"
)

PASTA_V3 = BASE_DIR / "saida_ml_entradas_video_v3"
MODELO_V3 = PASTA_V3 / "modelo_v3_score.joblib"
FEATURES_V3 = PASTA_V3 / "features_v3_score.joblib"

PASTA_V4 = BASE_DIR / "saida_ml_entradas_video_v4_antiloss"
MODELO_V4 = PASTA_V4 / "modelo_v4_antiloss.joblib"
FEATURES_V4 = PASTA_V4 / "features_modelo_v4.joblib"

PASTA_SAIDA = BASE_DIR / "validacao_v4_2026_fora_amostra"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_FEATURES_2026 = PASTA_SAIDA / "01_2026_features_corrigidas_prev.csv.gz"
ARQ_SCORE_2026 = PASTA_SAIDA / "02_2026_score_candidatos_corrigido.csv.gz"
ARQ_TRADES_2026 = PASTA_SAIDA / "03_2026_trades_config_travada_corrigido.csv.gz"
ARQ_RESUMO_2026 = PASTA_SAIDA / "04_2026_resumo_config_travada_corrigido.csv"
ARQ_ANALISE_2026 = PASTA_SAIDA / "05_2026_analise_por_horario_corrigido.csv"


# ============================================================
# CONFIGURAÇÃO TRAVADA FORA DA AMOSTRA
# ============================================================

TAKE_PONTOS = 50.5
STOP_PONTOS = 117.0

PROB_WIN_MIN = 0.60
SCORE_BUY_MIN = 0.70
SCORE_SELL_MIN = 0.50
DIFERENCA_MINIMA = 0.00

HORA_INICIO = 2.0
HORA_FIM = 6.0

MAX_TRADES_DIA = 3
PARAR_APOS_LOSS = True

MAX_CANDLES_FUTURO = 720
SCORE_MIN_CANDIDATO = 0.50


# ============================================================
# UTILITÁRIOS
# ============================================================

def safe_div(a, b):
    return np.where(np.abs(b) > 1e-12, a / b, 0.0)


def carregar_csv(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if str(caminho).lower().endswith(".gz"):
        return pd.read_csv(caminho, compression="gzip")

    return pd.read_csv(caminho)


def remover_timezone(serie):
    s = pd.to_datetime(serie, errors="coerce")

    try:
        if s.dt.tz is not None:
            s = s.dt.tz_localize(None)
    except Exception:
        s = s.apply(
            lambda x: x.replace(tzinfo=None)
            if pd.notna(x) and getattr(x, "tzinfo", None) is not None
            else x
        )

    return s


def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def true_range(df):
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(df, period):
    return df["true_range"].ewm(alpha=1 / period, adjust=False).mean()


def calcular_adx(df, period):
    high = df["high"]
    low = df["low"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = df["true_range"]
    atr_val = tr.ewm(alpha=1 / period, adjust=False).mean()

    plus_di = (
        100
        * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean()
        / atr_val.replace(0, np.nan)
    )

    minus_di = (
        100
        * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean()
        / atr_val.replace(0, np.nan)
    )

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_val = dx.ewm(alpha=1 / period, adjust=False).mean()

    return adx_val.fillna(0.0), plus_di.fillna(0.0), minus_di.fillna(0.0)


def choppiness(df, period):
    tr_sum = df["true_range"].rolling(period).sum()
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    denom = (high_max - low_min).replace(0, np.nan)

    out = 100 * np.log10(tr_sum / denom) / np.log10(period)
    return out.replace([np.inf, -np.inf], np.nan).fillna(50.0)


# ============================================================
# FEATURES
# ============================================================

def preparar_candles(df):
    df = df.copy()

    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = remover_timezone(df["DataHora_SP"])
    elif "DataHora" in df.columns:
        df["DataHora_SP"] = remover_timezone(df["DataHora"])
    elif "date" in df.columns:
        df["DataHora_SP"] = remover_timezone(df["date"])
    else:
        raise ValueError("Não encontrei coluna de data/hora no arquivo 2026.")

    df = df.dropna(subset=["DataHora_SP"]).copy()
    df = df.sort_values("DataHora_SP").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "barCount" not in df.columns:
        df["barCount"] = 0.0

    if "average" not in df.columns:
        df["average"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0

    if "conId" not in df.columns:
        df["conId"] = 0.0

    df["barCount"] = pd.to_numeric(df["barCount"], errors="coerce").fillna(0.0)
    df["average"] = pd.to_numeric(df["average"], errors="coerce").fillna(0.0)
    df["conId"] = pd.to_numeric(df["conId"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["open", "high", "low", "close"]).copy()
    df = df.reset_index(drop=True)

    if "DataHora_Chicago" not in df.columns:
        df["DataHora_Chicago"] = df["DataHora_SP"] - pd.Timedelta(hours=3)

    df["Data"] = df["DataHora_SP"].dt.date

    df["Hora_SP_Decimal"] = (
        df["DataHora_SP"].dt.hour
        + df["DataHora_SP"].dt.minute / 60.0
        + df["DataHora_SP"].dt.second / 3600.0
    )

    return df


def calcular_features_base(df):
    df = preparar_candles(df)

    # Candle
    df["range"] = df["high"] - df["low"]
    df["body"] = df["close"] - df["open"]
    df["body_abs"] = df["body"].abs()
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    df["body_range_pct"] = safe_div(df["body_abs"], df["range"]) * 100.0
    df["close_pos_range"] = safe_div(df["close"] - df["low"], df["range"]) * 100.0

    df["candle_alta"] = (df["close"] > df["open"]).astype(int)
    df["candle_baixa"] = (df["close"] < df["open"]).astype(int)

    for n in [2, 3, 4, 5, 8, 10]:
        df[f"seq_alta_{n}"] = (
            df["candle_alta"].rolling(n).sum() == n
        ).astype(int)

        df[f"seq_baixa_{n}"] = (
            df["candle_baixa"].rolling(n).sum() == n
        ).astype(int)

    # Tempo
    df["hora_sp"] = df["DataHora_SP"].dt.hour
    df["minuto_sp"] = df["DataHora_SP"].dt.minute
    df["dia_semana_sp"] = df["DataHora_SP"].dt.dayofweek
    df["mes_sp"] = df["DataHora_SP"].dt.month

    # Compatibilidade com features V4
    df["dia_semana"] = df["dia_semana_sp"]
    df["mes"] = df["mes_sp"]

    hora_rad = 2 * np.pi * df["Hora_SP_Decimal"] / 24.0
    df["sin_hora"] = np.sin(hora_rad)
    df["cos_hora"] = np.cos(hora_rad)
    df["sin_hora_sp"] = df["sin_hora"]
    df["cos_hora_sp"] = df["cos_hora"]

    hhmm = df["DataHora_SP"].dt.strftime("%H:%M")
    df["eh_0348"] = (hhmm == "03:48").astype(int)
    df["eh_0448"] = (hhmm == "04:48").astype(int)

    df["janela_0340_0400"] = (
        (df["Hora_SP_Decimal"] >= 3.6667)
        & (df["Hora_SP_Decimal"] <= 4.0)
    ).astype(int)

    df["janela_0430_0500"] = (
        (df["Hora_SP_Decimal"] >= 4.5)
        & (df["Hora_SP_Decimal"] <= 5.0)
    ).astype(int)

    df["janela_0000_0600"] = (
        (df["Hora_SP_Decimal"] >= 0.0)
        & (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    df["janela_0300_0600"] = (
        (df["Hora_SP_Decimal"] >= 3.0)
        & (df["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    # Retornos
    df["logret_1"] = np.log(df["close"] / df["close"].shift(1)).replace([np.inf, -np.inf], np.nan)

    for n in [1, 2, 3, 5, 8, 10, 15, 20, 30, 45, 60, 90, 120]:
        df[f"ret_{n}"] = df["close"].pct_change(n)
        df[f"pts_change_{n}"] = df["close"] - df["close"].shift(n)

    df["aceleracao_ret_3_10"] = df["ret_3"] - df["ret_10"]
    df["aceleracao_ret_5_20"] = df["ret_5"] - df["ret_20"]
    df["aceleracao_ret_10_30"] = df["ret_10"] - df["ret_30"]
    df["aceleracao_ret_15_60"] = df["ret_15"] - df["ret_60"]

    for n in [3, 5, 10, 15, 20, 30, 60, 120]:
        df[f"range_ma_{n}"] = df["range"].rolling(n).mean()
        df[f"range_ratio_{n}"] = safe_div(df["range"], df[f"range_ma_{n}"])

        df[f"volume_ma_{n}"] = df["volume"].rolling(n).mean()
        df[f"volume_ratio_{n}"] = safe_div(df["volume"], df[f"volume_ma_{n}"])

        df[f"barcount_ma_{n}"] = df["barCount"].rolling(n).mean()
        df[f"barcount_ratio_{n}"] = safe_div(df["barCount"], df[f"barcount_ma_{n}"])

        df[f"volatilidade_ret_{n}"] = df["ret_1"].rolling(n).std()

    df["volume_por_negocio"] = safe_div(df["volume"], df["barCount"].replace(0, np.nan))

    hora_minuto = df["DataHora_SP"].dt.strftime("%H:%M")
    media_volume_horario = df.groupby(hora_minuto)["volume"].transform("mean")
    df["volume_relativo_horario"] = safe_div(df["volume"], media_volume_horario)

    # EMAs
    for n in [9, 17, 20, 34, 50, 72, 100, 200]:
        df[f"ema_{n}"] = df["close"].ewm(span=n, adjust=False).mean()
        df[f"dist_ema_{n}"] = df["close"] - df[f"ema_{n}"]
        df[f"dist_ema_{n}_pct"] = safe_div(df[f"dist_ema_{n}"], df[f"ema_{n}"]) * 100.0
        df[f"ema_{n}_slope_3"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(3)
        df[f"ema_{n}_slope_10"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(10)

    # Trend clouds
    pares = [(9, 17), (17, 34), (20, 50), (34, 72), (50, 100), (100, 200)]

    for a, b in pares:
        top = df[[f"ema_{a}", f"ema_{b}"]].max(axis=1)
        bottom = df[[f"ema_{a}", f"ema_{b}"]].min(axis=1)

        df[f"trend_cloud_{a}_{b}_bull"] = (df[f"ema_{a}"] > df[f"ema_{b}"]).astype(int)
        df[f"trend_cloud_{a}_{b}_thickness"] = (df[f"ema_{a}"] - df[f"ema_{b}"]).abs()
        df[f"trend_cloud_{a}_{b}_thickness_pct"] = safe_div(
            df[f"trend_cloud_{a}_{b}_thickness"],
            df["close"]
        ) * 100.0

        df[f"trend_cloud_{a}_{b}_pos"] = np.select(
            [
                df["close"] > top,
                df["close"] < bottom,
            ],
            [1, -1],
            default=0,
        )

        df[f"trend_cloud_{a}_{b}_dist_top"] = df["close"] - top
        df[f"trend_cloud_{a}_{b}_dist_bottom"] = df["close"] - bottom

    df["ema17_acima_ema34"] = (df["ema_17"] > df["ema_34"]).astype(int)
    df["close_acima_ema17"] = (df["close"] > df["ema_17"]).astype(int)
    df["close_acima_ema34"] = (df["close"] > df["ema_34"]).astype(int)
    df["dist_ema17_34"] = df["ema_17"] - df["ema_34"]

    # Bias
    for n in [6, 9, 12, 17, 20, 23, 24, 34, 50]:
        sma = df["close"].rolling(n).mean()
        df[f"bias_{n}"] = safe_div(df["close"] - sma, sma) * 100.0

    # RSI
    for n in [7, 9, 14, 21, 34]:
        df[f"rsi_{n}"] = rsi(df["close"], n)
        df[f"rsi_{n}_slope_3"] = df[f"rsi_{n}"] - df[f"rsi_{n}"].shift(3)

    # StochRSI
    for n in [8, 14, 21]:
        r = rsi(df["close"], n)
        r_min = r.rolling(n).min()
        r_max = r.rolling(n).max()
        stoch = safe_div(r - r_min, r_max - r_min) * 100.0
        k = pd.Series(stoch, index=df.index).rolling(3).mean()
        d = k.rolling(3).mean()

        df[f"stochrsi_{n}_k"] = k
        df[f"stochrsi_{n}_d"] = d
        df[f"stochrsi_{n}_k_menos_d"] = k - d

    # ATR e TR decisions
    df["true_range"] = true_range(df)

    for n in [7, 10, 14, 18, 21, 34]:
        df[f"atr_{n}"] = atr(df, n)
        df[f"atrp_{n}"] = safe_div(df[f"atr_{n}"], df["close"]) * 100.0
        df[f"tr_ratio_atr_{n}"] = safe_div(df["true_range"], df[f"atr_{n}"])

        df[f"tr_decision_up_{n}"] = df["close"].shift(1) + df[f"atr_{n}"]
        df[f"tr_decision_down_{n}"] = df["close"].shift(1) - df[f"atr_{n}"]

        df[f"dist_tr_decision_up_{n}"] = df["close"] - df[f"tr_decision_up_{n}"]
        df[f"dist_tr_decision_down_{n}"] = df["close"] - df[f"tr_decision_down_{n}"]

        df[f"rompeu_decision_up_{n}"] = (df["high"] >= df[f"tr_decision_up_{n}"]).astype(int)
        df[f"rompeu_decision_down_{n}"] = (df["low"] <= df[f"tr_decision_down_{n}"]).astype(int)

    # Bollinger
    for n in [20, 34, 50]:
        mid = df["close"].rolling(n).mean()
        std = df["close"].rolling(n).std()
        upper = mid + 2 * std
        lower = mid - 2 * std

        df[f"bb_width_{n}"] = upper - lower
        df[f"bb_pos_{n}"] = safe_div(df["close"] - lower, upper - lower)
        df[f"dist_bb_upper_{n}"] = df["close"] - upper
        df[f"dist_bb_lower_{n}"] = df["close"] - lower

    # Keltner
    for n in [20, 34]:
        mid = df["close"].ewm(span=n, adjust=False).mean()
        atr_n = atr(df, n)
        upper = mid + 1.5 * atr_n
        lower = mid - 1.5 * atr_n

        df[f"kc_width_{n}"] = upper - lower
        df[f"kc_pos_{n}"] = safe_div(df["close"] - lower, upper - lower)
        df[f"dist_kc_upper_{n}"] = df["close"] - upper
        df[f"dist_kc_lower_{n}"] = df["close"] - lower

    # VWAP diário
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    df["pv"] = typical * df["volume"]
    soma_pv = df.groupby("Data")["pv"].cumsum()
    soma_vol = df.groupby("Data")["volume"].cumsum().replace(0, np.nan)

    df["vwap_dia"] = soma_pv / soma_vol
    df["dist_vwap_dia"] = df["close"] - df["vwap_dia"]
    df["dist_vwap_dia_pct"] = safe_div(df["dist_vwap_dia"], df["vwap_dia"]) * 100.0
    df["close_acima_vwap"] = (df["close"] > df["vwap_dia"]).astype(int)
    df["vwap_slope_5"] = df["vwap_dia"] - df["vwap_dia"].shift(5)
    df = df.drop(columns=["pv"], errors="ignore")

    # Rompimentos
    for n in [3, 5, 10, 15, 20, 30, 50, 60, 120]:
        high_max = df["high"].rolling(n).max()
        low_min = df["low"].rolling(n).min()

        df[f"high_max_{n}"] = high_max
        df[f"low_min_{n}"] = low_min
        df[f"dist_high_max_{n}"] = df["close"] - high_max
        df[f"dist_low_min_{n}"] = df["close"] - low_min
        df[f"pos_range_{n}"] = safe_div(df["close"] - low_min, high_max - low_min)

        df[f"rompeu_max_{n}"] = (df["high"] >= high_max.shift(1)).astype(int)
        df[f"rompeu_min_{n}"] = (df["low"] <= low_min.shift(1)).astype(int)

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["macd_hist_slope_3"] = df["macd_hist"] - df["macd_hist"].shift(3)

    # ADX
    for n in [7, 14, 21]:
        adx_val, plus_di, minus_di = calcular_adx(df, n)
        df[f"adx_{n}"] = adx_val
        df[f"plus_di_{n}"] = plus_di
        df[f"minus_di_{n}"] = minus_di
        df[f"di_diff_{n}"] = plus_di - minus_di

    # Choppiness
    for n in [14, 21, 34]:
        df[f"choppiness_{n}"] = choppiness(df, n)

    df = df.replace([np.inf, -np.inf], np.nan)

    return df


def criar_features_prev(df):
    """
    O modelo V3 foi treinado com features prev_.
    Aqui criamos prev_col = col.shift(1) para todas as features base.
    """
    df = df.copy()

    features_v3 = joblib.load(FEATURES_V3)

    prev_features = [f for f in features_v3 if f.startswith("prev_")]

    faltantes_base = []

    for feat_prev in prev_features:
        base_col = feat_prev.replace("prev_", "", 1)

        if base_col in df.columns:
            df[feat_prev] = df[base_col].shift(1)
        else:
            df[feat_prev] = 0.0
            faltantes_base.append(base_col)

    if faltantes_base:
        faltantes_unicos = sorted(set(faltantes_base))
        print("\nATENÇÃO: algumas bases de prev_ não existiam e foram preenchidas com 0.")
        print("Quantidade:", len(faltantes_unicos))
        print("Primeiras 80 faltantes:")
        print(faltantes_unicos[:80])

    return df


def calcular_features(df):
    df = calcular_features_base(df)
    df = criar_features_prev(df)
    df = df.replace([np.inf, -np.inf], np.nan)

    return df


# ============================================================
# MODELOS
# ============================================================

def preparar_X(df, features, nome_modelo=""):
    base = df.copy()
    faltantes = []

    for col in features:
        if col not in base.columns:
            base[col] = 0.0
            faltantes.append(col)

    if faltantes:
        print(f"\nATENÇÃO: {nome_modelo} teve features ausentes preenchidas com 0.")
        print("Quantidade:", len(faltantes))
        print("Primeiras 80:")
        print(faltantes[:80])

    X = base[features].copy()
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0.0)

    return X


def aplicar_modelo_v3(df_features):
    print("\nCarregando modelo V3...")
    modelo_v3 = joblib.load(MODELO_V3)
    features_v3 = joblib.load(FEATURES_V3)

    X3 = preparar_X(df_features, features_v3, nome_modelo="V3")

    print("Gerando scores V3...")
    probas = modelo_v3.predict_proba(X3)

    print("Classes do modelo V3:")
    print(modelo_v3.classes_)

    df = df_features.copy()

    # Mapeamento confirmado:
    # 0 = NONE
    # 1 = BUY
    # 2 = SELL
    classes = list(modelo_v3.classes_)

    df["score_NONE"] = 0.0
    df["score_BUY"] = 0.0
    df["score_SELL"] = 0.0

    for i, classe in enumerate(classes):
        if int(classe) == 0:
            df["score_NONE"] = probas[:, i]
        elif int(classe) == 1:
            df["score_BUY"] = probas[:, i]
        elif int(classe) == 2:
            df["score_SELL"] = probas[:, i]

    df["score_direcao"] = df[["score_BUY", "score_SELL"]].max(axis=1)
    df["Direcao"] = np.where(df["score_BUY"] >= df["score_SELL"], "BUY", "SELL")
    df["score_oposto"] = np.where(
        df["Direcao"] == "BUY",
        df["score_SELL"],
        df["score_BUY"]
    )
    df["score_diff"] = df["score_direcao"] - df["score_oposto"]

    print("\nResumo dos scores V3 antes do filtro:")
    print(df[["score_BUY", "score_SELL", "score_NONE", "score_direcao", "score_diff"]].describe())

    print("\nTop 10 BUY 2026:")
    print(
        df[["DataHora_SP", "score_BUY", "score_SELL", "score_NONE"]]
        .sort_values("score_BUY", ascending=False)
        .head(10)
        .to_string(index=False)
    )

    print("\nTop 10 SELL 2026:")
    print(
        df[["DataHora_SP", "score_BUY", "score_SELL", "score_NONE"]]
        .sort_values("score_SELL", ascending=False)
        .head(10)
        .to_string(index=False)
    )

    df_cand = df[
        (df["Hora_SP_Decimal"] >= 0.0)
        & (df["Hora_SP_Decimal"] <= 12.0)
        & (
            (df["score_BUY"] >= SCORE_MIN_CANDIDATO)
            | (df["score_SELL"] >= SCORE_MIN_CANDIDATO)
        )
    ].copy()

    df_cand = df_cand.sort_values("DataHora_SP").reset_index(drop=True)

    print("\nCandidatos V3/V4 gerados:", len(df_cand))

    if not df_cand.empty:
        print("\nDireções dos candidatos:")
        print(df_cand["Direcao"].value_counts())

    return df_cand


def aplicar_modelo_v4(df_candidatos):
    print("\nCarregando modelo V4 anti-loss...")

    if df_candidatos.empty:
        print("ATENÇÃO: nenhum candidato chegou ao modelo V4.")
        return df_candidatos.copy()

    modelo_v4 = joblib.load(MODELO_V4)
    features_v4 = joblib.load(FEATURES_V4)

    X4 = preparar_X(df_candidatos, features_v4, nome_modelo="V4")

    print("Gerando prob_win_v4...")
    probas = modelo_v4.predict_proba(X4)

    print("Classes do modelo V4:")
    print(modelo_v4.classes_)

    classes = list(modelo_v4.classes_)

    df = df_candidatos.copy()
    df["prob_win_v4"] = 0.0

    if len(classes) == 2:
        if 1 in classes:
            idx = classes.index(1)
        elif True in classes:
            idx = classes.index(True)
        else:
            idx = 1

        df["prob_win_v4"] = probas[:, idx]

    else:
        for i, classe in enumerate(classes):
            if str(classe).upper() in ["1", "TRUE", "WIN", "GAIN", "TAKE", "TP"]:
                df["prob_win_v4"] = probas[:, i]

    print("\nResumo prob_win_v4:")
    print(df["prob_win_v4"].describe())

    return df


# ============================================================
# SIMULAÇÃO TAKE/STOP
# ============================================================

def simular_trade(df, idx, direcao, take_pontos, stop_pontos, max_candles):
    entrada = float(df.at[idx, "close"])
    fim = min(idx + max_candles, len(df) - 1)

    if fim <= idx:
        return "NEUTRO", 0.0, np.nan, np.nan, pd.NaT, np.nan

    runup_max = 0.0
    drawdown_max = 0.0

    for j in range(idx + 1, fim + 1):
        high = float(df.at[j, "high"])
        low = float(df.at[j, "low"])

        if direcao == "BUY":
            runup = high - entrada
            drawdown = entrada - low

            bateu_stop = low <= entrada - stop_pontos
            bateu_take = high >= entrada + take_pontos

        else:
            runup = entrada - low
            drawdown = high - entrada

            bateu_stop = high >= entrada + stop_pontos
            bateu_take = low <= entrada - take_pontos

        runup_max = max(runup_max, runup)
        drawdown_max = max(drawdown_max, drawdown)

        # Conservador: se bater stop e take no mesmo candle, considera loss
        if bateu_stop and bateu_take:
            return "LOSS", -stop_pontos, runup_max, drawdown_max, df.at[j, "DataHora_SP"], j

        if bateu_stop:
            return "LOSS", -stop_pontos, runup_max, drawdown_max, df.at[j, "DataHora_SP"], j

        if bateu_take:
            return "WIN", take_pontos, runup_max, drawdown_max, df.at[j, "DataHora_SP"], j

    return "NEUTRO", 0.0, runup_max, drawdown_max, pd.NaT, np.nan


def adicionar_resultados_take_stop(df_score, df_candles):
    print("\nSimulando resultados com Take/Stop em 2026...")

    if df_score.empty:
        print("Sem candidatos para simular.")
        return df_score.copy()

    df_base = df_candles.reset_index(drop=True).copy()
    df_base["DataHora_SP"] = remover_timezone(df_base["DataHora_SP"])

    mapa_idx = pd.Series(df_base.index.values, index=df_base["DataHora_SP"]).to_dict()

    linhas = []

    for _, row in df_score.iterrows():
        dt = row["DataHora_SP"]

        if dt not in mapa_idx:
            continue

        idx = int(mapa_idx[dt])
        direcao = row["Direcao"]

        resultado, pontos, runup, drawdown, dt_saida, idx_saida = simular_trade(
            df_base,
            idx,
            direcao,
            TAKE_PONTOS,
            STOP_PONTOS,
            MAX_CANDLES_FUTURO,
        )

        if resultado == "NEUTRO":
            continue

        r = row.copy()
        r["resultado_stop_117_0"] = resultado
        r["pontos_stop_117_0"] = pontos
        r["runup_stop_117_0"] = runup
        r["drawdown_stop_117_0"] = drawdown
        r["dt_saida_stop_117_0"] = dt_saida
        r["indice_saida_stop_117_0"] = idx_saida
        r["target_win_stop_117_0"] = 1 if resultado == "WIN" else 0

        linhas.append(r)

    out = pd.DataFrame(linhas)
    print("Candidatos com resultado:", len(out))

    return out


# ============================================================
# CONFIGURAÇÃO TRAVADA
# ============================================================

def aplicar_config_travada(df):
    if df.empty:
        return pd.DataFrame()

    base = df.copy()

    filtro = (
        (base["prob_win_v4"] >= PROB_WIN_MIN)
        & (base["Hora_SP_Decimal"] >= HORA_INICIO)
        & (base["Hora_SP_Decimal"] < HORA_FIM)
        & (base["score_diff"] >= DIFERENCA_MINIMA)
        & (
            ((base["Direcao"] == "BUY") & (base["score_BUY"] >= SCORE_BUY_MIN))
            | ((base["Direcao"] == "SELL") & (base["score_SELL"] >= SCORE_SELL_MIN))
        )
    )

    base = base[filtro].copy()
    base = base.sort_values("DataHora_SP").reset_index(drop=True)

    trades = []

    for data, grupo in base.groupby("Data", sort=True):
        qtd = 0
        teve_loss = False

        grupo = grupo.sort_values("DataHora_SP")

        for _, row in grupo.iterrows():
            if qtd >= MAX_TRADES_DIA:
                break

            if PARAR_APOS_LOSS and teve_loss:
                break

            resultado = row["resultado_stop_117_0"]

            if resultado not in ["WIN", "LOSS"]:
                continue

            trades.append(row)

            qtd += 1

            if resultado == "LOSS":
                teve_loss = True

    if not trades:
        return pd.DataFrame()

    return pd.DataFrame(trades).reset_index(drop=True)


def resumir_trades(trades):
    if trades.empty:
        return pd.DataFrame([{
            "take_pontos": TAKE_PONTOS,
            "stop_pontos": STOP_PONTOS,
            "prob_win_min": PROB_WIN_MIN,
            "score_buy_min": SCORE_BUY_MIN,
            "score_sell_min": SCORE_SELL_MIN,
            "hora_inicio": HORA_INICIO,
            "hora_fim": HORA_FIM,
            "max_trades_dia": MAX_TRADES_DIA,
            "parar_apos_loss": PARAR_APOS_LOSS,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "dias_operados": 0,
            "pior_dia": 0.0,
            "melhor_dia": 0.0,
        }])

    total = len(trades)
    wins = int((trades["resultado_stop_117_0"] == "WIN").sum())
    losses = int((trades["resultado_stop_117_0"] == "LOSS").sum())
    lucro = float(trades["pontos_stop_117_0"].sum())

    ganhos = trades.loc[trades["pontos_stop_117_0"] > 0, "pontos_stop_117_0"].sum()
    perdas = abs(trades.loc[trades["pontos_stop_117_0"] < 0, "pontos_stop_117_0"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    por_dia = trades.groupby("Data")["pontos_stop_117_0"].sum()

    return pd.DataFrame([{
        "take_pontos": TAKE_PONTOS,
        "stop_pontos": STOP_PONTOS,
        "prob_win_min": PROB_WIN_MIN,
        "score_buy_min": SCORE_BUY_MIN,
        "score_sell_min": SCORE_SELL_MIN,
        "diferenca_minima": DIFERENCA_MINIMA,
        "hora_inicio": HORA_INICIO,
        "hora_fim": HORA_FIM,
        "max_trades_dia": MAX_TRADES_DIA,
        "parar_apos_loss": PARAR_APOS_LOSS,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "buy_total": int((trades["Direcao"] == "BUY").sum()),
        "sell_total": int((trades["Direcao"] == "SELL").sum()),
        "dias_operados": int(trades["Data"].nunique()),
        "pior_dia": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia": float(por_dia.max()) if len(por_dia) else 0.0,
        "media_prob_win": float(trades["prob_win_v4"].mean()),
        "min_prob_win": float(trades["prob_win_v4"].min()),
        "drawdown_medio_trade": float(trades["drawdown_stop_117_0"].mean()),
        "drawdown_max_trade": float(trades["drawdown_stop_117_0"].max()),
        "runup_medio_trade": float(trades["runup_stop_117_0"].mean()),
        "runup_max_trade": float(trades["runup_stop_117_0"].max()),
    }])


def analise_por_horario(trades):
    if trades.empty:
        return pd.DataFrame()

    df = trades.copy()
    dt = pd.to_datetime(df["DataHora_SP"])

    df["Hora"] = dt.dt.hour
    df["Bloco_15m"] = (
        dt.dt.hour.astype(str).str.zfill(2)
        + ":"
        + ((dt.dt.minute // 15) * 15).astype(str).str.zfill(2)
    )

    linhas = []

    for nome_grupo, col in [("Hora", "Hora"), ("Bloco_15m", "Bloco_15m"), ("Direcao", "Direcao")]:
        for valor, g in df.groupby(col):
            total = len(g)
            wins = int((g["resultado_stop_117_0"] == "WIN").sum())
            losses = int((g["resultado_stop_117_0"] == "LOSS").sum())
            lucro = float(g["pontos_stop_117_0"].sum())

            ganhos = g.loc[g["pontos_stop_117_0"] > 0, "pontos_stop_117_0"].sum()
            perdas = abs(g.loc[g["pontos_stop_117_0"] < 0, "pontos_stop_117_0"].sum())
            pf = ganhos / perdas if perdas > 0 else 999.0

            linhas.append({
                "grupo": nome_grupo,
                "valor": valor,
                "trades": total,
                "wins": wins,
                "losses": losses,
                "winrate": wins / total * 100 if total else 0.0,
                "lucro_pontos": lucro,
                "profit_factor": pf,
            })

    return pd.DataFrame(linhas)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("VALIDAÇÃO V4 2026 FORA DA AMOSTRA - CORRIGIDO PREV")
    print("=====================================================")

    print("\nArquivos:")
    print("Candles 2026:", ARQUIVO_CANDLES_2026)
    print("Modelo V3:", MODELO_V3)
    print("Features V3:", FEATURES_V3)
    print("Modelo V4:", MODELO_V4)
    print("Features V4:", FEATURES_V4)

    print("\nLendo candles 2026...")
    candles = carregar_csv(ARQUIVO_CANDLES_2026)
    print("Candles carregados:", len(candles))

    print("\nCalculando features base + prev_...")
    features = calcular_features(candles)
    features.to_csv(ARQ_FEATURES_2026, index=False, compression="gzip")

    print("Features salvas:")
    print(ARQ_FEATURES_2026)

    score_v3 = aplicar_modelo_v3(features)

    if score_v3.empty:
        print("\nERRO: nenhum candidato foi gerado pelo modelo V3.")
        print("Mesmo com prev_, o V3 não encontrou sinais acima do filtro.")
        return

    score_v4 = aplicar_modelo_v4(score_v3)

    if score_v4.empty:
        print("\nERRO: nenhum candidato chegou ao modelo V4.")
        return

    score_resultado = adicionar_resultados_take_stop(score_v4, features)

    if score_resultado.empty:
        print("\nERRO: nenhum candidato teve resultado WIN/LOSS dentro do horizonte.")
        return

    score_resultado.to_csv(ARQ_SCORE_2026, index=False, compression="gzip")

    print("\nScore candidatos 2026 salvo:")
    print(ARQ_SCORE_2026)

    trades = aplicar_config_travada(score_resultado)
    resumo = resumir_trades(trades)
    analise = analise_por_horario(trades)

    trades.to_csv(ARQ_TRADES_2026, index=False, compression="gzip")
    resumo.to_csv(ARQ_RESUMO_2026, index=False)
    analise.to_csv(ARQ_ANALISE_2026, index=False)

    print("\n=====================================================")
    print("RESULTADO FORA DA AMOSTRA 2026")
    print("=====================================================")
    print(resumo.T.to_string())

    print("\nArquivos gerados:")
    print(ARQ_TRADES_2026)
    print(ARQ_RESUMO_2026)
    print(ARQ_ANALISE_2026)

    print("\nAnálise por horário/direção:")
    if not analise.empty:
        print(analise.to_string(index=False))
    else:
        print("Sem análise, pois não houve trades finais.")


if __name__ == "__main__":
    main()