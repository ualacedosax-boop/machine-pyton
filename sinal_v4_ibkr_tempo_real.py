import os
import json
import time
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from ib_insync import IB, Future, util


# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V3 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")
PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")
PASTA_OPERACIONAL = os.path.join(BASE_DIR, "operacional_v4")
os.makedirs(PASTA_OPERACIONAL, exist_ok=True)

# Modelo V3: score BUY / SELL / NONE
ARQUIVO_MODELO_V3 = os.path.join(PASTA_V3, "modelo_v3_score.joblib")
ARQUIVO_FEATURES_V3 = os.path.join(PASTA_V3, "features_v3_score.joblib")
ARQUIVO_CONFIG_V3 = os.path.join(PASTA_V3, "config_modelo_v3_score.json")

# Modelo V4: anti-loss / probabilidade
ARQUIVO_CONFIG_V4 = os.path.join(PASTA_V4, "config_melhor_v4.json")
ARQUIVO_MODELO_V4 = os.path.join(PASTA_V4, "modelo_v4_antiloss.joblib")
ARQUIVO_FEATURES_V4 = os.path.join(PASTA_V4, "features_modelo_v4.joblib")

# Saídas operacionais
ARQUIVO_CANDLES_IBKR = os.path.join(PASTA_OPERACIONAL, "candles_ibkr_mnq_2min.csv")
ARQUIVO_FEATURES_TEMPO_REAL = os.path.join(PASTA_OPERACIONAL, "features_tempo_real_v4.csv")
ARQUIVO_SINAL_TXT = os.path.join(PASTA_OPERACIONAL, "sinal.txt")
ARQUIVO_ULTIMO_SINAL_JSON = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v4_ibkr.json")
ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_ibkr.csv")

# IBKR / TWS
HOST = "127.0.0.1"
PORT = 7497          # 7497 = Paper/Simulated | 7496 = Live
CLIENT_ID = 22

SIMBOLO = "MNQ"
EXCHANGE = "CME"
CURRENCY = "USD"

# Histórico solicitado a cada execução
DURATION_STR = "10 D"
BAR_SIZE = "2 mins"
WHAT_TO_SHOW = "TRADES"
USE_RTH = False

# Loop
RODAR_EM_LOOP = False
INTERVALO_SEGUNDOS = 30

# Segurança
MODO_SEGURO_SEM_ORDEM = True

VALOR_PONTO_MNQ = 2.0


# =====================================================
# FUNÇÕES DE ARQUIVO
# =====================================================

def salvar_txt_seguro(texto, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        f.write(str(texto).strip().lower())

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)


def salvar_json_seguro(obj, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4, default=str)

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)


def salvar_csv_seguro(df, caminho):
    temp = caminho + ".tmp"

    df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)


def append_log(linha):
    df_linha = pd.DataFrame([linha])

    if os.path.exists(ARQUIVO_LOG):
        antigo = pd.read_csv(ARQUIVO_LOG)
        novo = pd.concat([antigo, df_linha], ignore_index=True)
    else:
        novo = df_linha

    salvar_csv_seguro(novo, ARQUIVO_LOG)


# =====================================================
# CARREGAR MODELOS
# =====================================================

def carregar_json(caminho):
    if not os.path.exists(caminho):
        return {}

    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_config_v4():
    if not os.path.exists(ARQUIVO_CONFIG_V4):
        raise FileNotFoundError(f"Não encontrei: {ARQUIVO_CONFIG_V4}")

    config = carregar_json(ARQUIVO_CONFIG_V4)

    config["take_pontos"] = float(config["take_pontos"])
    config["stop_pontos"] = float(config["stop_pontos"])
    config["prob_win_min"] = float(config["prob_win_min"])
    config["max_trades_dia"] = int(config["max_trades_dia"])
    config["parar_apos_loss"] = str(config["parar_apos_loss"]).lower() in ["true", "1", "sim", "yes"]
    config["score_buy_min"] = float(config["score_buy_min"])
    config["score_sell_min"] = float(config["score_sell_min"])
    config["diferenca_minima"] = float(config["diferenca_minima"])
    config["hora_inicio"] = float(config["hora_inicio"])
    config["hora_fim"] = float(config["hora_fim"])

    return config


def carregar_modelo_v3():
    if not os.path.exists(ARQUIVO_MODELO_V3):
        raise FileNotFoundError(f"Não encontrei modelo V3: {ARQUIVO_MODELO_V3}")

    if not os.path.exists(ARQUIVO_FEATURES_V3):
        raise FileNotFoundError(f"Não encontrei features V3: {ARQUIVO_FEATURES_V3}")

    modelo = joblib.load(ARQUIVO_MODELO_V3)
    features = joblib.load(ARQUIVO_FEATURES_V3)
    config = carregar_json(ARQUIVO_CONFIG_V3)

    print("Modelo V3 carregado:", ARQUIVO_MODELO_V3)
    print("Features V3:", len(features))

    return modelo, features, config


def carregar_modelo_v4():
    if not os.path.exists(ARQUIVO_MODELO_V4):
        raise FileNotFoundError(f"Não encontrei modelo V4: {ARQUIVO_MODELO_V4}")

    if not os.path.exists(ARQUIVO_FEATURES_V4):
        raise FileNotFoundError(f"Não encontrei features V4: {ARQUIVO_FEATURES_V4}")

    modelo = joblib.load(ARQUIVO_MODELO_V4)
    features = joblib.load(ARQUIVO_FEATURES_V4)

    print("Modelo V4 carregado:", ARQUIVO_MODELO_V4)
    print("Features V4:", len(features))

    return modelo, features


# =====================================================
# IBKR
# =====================================================

def conectar_ibkr():
    ib = IB()

    print("Conectando ao IBKR/TWS...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=15)
    print("Conectado:", ib.isConnected())

    return ib


def obter_contrato_mnq(ib):
    print("Buscando contrato MNQ...")

    contrato_base = Future(
        symbol=SIMBOLO,
        exchange=EXCHANGE,
        currency=CURRENCY
    )

    detalhes = ib.reqContractDetails(contrato_base)

    if not detalhes:
        raise Exception("Nenhum contrato MNQ encontrado. Verifique permissões ou contrato.")

    print(f"Contratos encontrados: {len(detalhes)}")

    for i, cd in enumerate(detalhes[:5]):
        c = cd.contract
        print(
            i,
            "localSymbol:", c.localSymbol,
            "lastTradeDate:", c.lastTradeDateOrContractMonth,
            "conId:", c.conId
        )

    contrato = detalhes[0].contract

    print("Contrato escolhido:", contrato.localSymbol, contrato.conId)

    return contrato


def baixar_candles_2min(ib, contrato):
    print("Baixando candles MNQ 2 minutos...")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime="",
        durationStr=DURATION_STR,
        barSizeSetting=BAR_SIZE,
        whatToShow=WHAT_TO_SHOW,
        useRTH=USE_RTH,
        formatDate=1,
        keepUpToDate=False
    )

    if not bars:
        raise Exception("Nenhum candle retornado pela IBKR.")

    df = util.df(bars)

    df = df.rename(columns={
        "date": "DataHora_IBKR",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    })

    df["DataHora_IBKR"] = pd.to_datetime(df["DataHora_IBKR"], errors="coerce")

    try:
        if df["DataHora_IBKR"].dt.tz is not None:
            df["DataHora_SP"] = df["DataHora_IBKR"].dt.tz_convert("America/Sao_Paulo")
        else:
            df["DataHora_SP"] = df["DataHora_IBKR"].dt.tz_localize("America/Chicago").dt.tz_convert("America/Sao_Paulo")
    except Exception:
        df["DataHora_SP"] = df["DataHora_IBKR"]

    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0
    df["Data"] = df["DataHora_SP"].dt.date

    if "average" not in df.columns:
        df["average"] = np.nan

    if "barCount" not in df.columns:
        df["barCount"] = np.nan

    df["contrato"] = getattr(contrato, "symbol", SIMBOLO)
    df["localSymbol"] = getattr(contrato, "localSymbol", "")

    salvar_csv_seguro(df, ARQUIVO_CANDLES_IBKR)

    print("Candles salvos:", ARQUIVO_CANDLES_IBKR)
    print("Linhas:", len(df))
    print("Último candle:")
    print(df.tail(1).T)

    return df


# =====================================================
# INDICADORES / FEATURES
# =====================================================

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def rma(series, n):
    return series.ewm(alpha=1 / n, adjust=False).mean()


def sma(series, n):
    return series.rolling(n).mean()


def calcular_rsi(close, n):
    delta = close.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    avg_gain = rma(ganho, n)
    avg_loss = rma(perda, n)

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def calcular_stoch_rsi(close, rsi_len=14, stoch_len=14, smooth_k=3, smooth_d=3):
    rsi_base = calcular_rsi(close, rsi_len)

    rsi_min = rsi_base.rolling(stoch_len).min()
    rsi_max = rsi_base.rolling(stoch_len).max()

    stoch_raw = (rsi_base - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100

    k = sma(stoch_raw, smooth_k)
    d = sma(k, smooth_d)

    return k, d


def calcular_macd(close, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    macd_signal = ema(macd_line, signal)
    macd_hist = macd_line - macd_signal

    return macd_line, macd_signal, macd_hist


def calcular_adx(df, n=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    tr_rma = rma(tr, n)

    plus_di = 100 * rma(pd.Series(plus_dm, index=df.index), n) / tr_rma.replace(0, np.nan)
    minus_di = 100 * rma(pd.Series(minus_dm, index=df.index), n) / tr_rma.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = rma(dx, n)

    return adx, plus_di, minus_di, tr


def preparar_features_tempo_real(df):
    base = df.copy()

    base = base.sort_values("DataHora_SP").reset_index(drop=True)

    base["range"] = base["high"] - base["low"]
    base["body"] = base["close"] - base["open"]
    base["body_abs"] = base["body"].abs()

    base["upper_wick"] = base["high"] - base[["open", "close"]].max(axis=1)
    base["lower_wick"] = base[["open", "close"]].min(axis=1) - base["low"]

    base["body_range_pct"] = base["body_abs"] / base["range"].replace(0, np.nan)
    base["close_pos_range"] = (base["close"] - base["low"]) / base["range"].replace(0, np.nan)

    base["logret_1"] = np.log(base["close"] / base["close"].shift(1))
    base["ret_1"] = base["close"].pct_change(1)
    base["pts_change_1"] = base["close"] - base["close"].shift(1)
    base["volatilidade_ret_1"] = base["logret_1"].rolling(1).std()

    for n in [2, 3, 5, 8, 10, 15, 20, 30, 60, 120]:
        base[f"ret_{n}"] = base["close"].pct_change(n)
        base[f"pts_change_{n}"] = base["close"] - base["close"].shift(n)
        base[f"volatilidade_ret_{n}"] = base["logret_1"].rolling(n).std()

    for n in [3, 5, 8, 9, 10, 12, 17, 20, 21, 26, 34, 50, 55, 72, 89, 100, 144, 200]:
        base[f"sma_{n}"] = sma(base["close"], n)
        base[f"ema_{n}"] = ema(base["close"], n)

    base["ema_17_slope_3"] = base["ema_17"] - base["ema_17"].shift(3)
    base["ema_34_slope_3"] = base["ema_34"] - base["ema_34"].shift(3)
    base["ema_50_slope_3"] = base["ema_50"] - base["ema_50"].shift(3)
    base["ema_200_slope_3"] = base["ema_200"] - base["ema_200"].shift(3)

    base["dist_ema_9"] = base["close"] - base["ema_9"]
    base["dist_ema_17"] = base["close"] - base["ema_17"]
    base["dist_ema_34"] = base["close"] - base["ema_34"]
    base["dist_ema_50"] = base["close"] - base["ema_50"]
    base["dist_ema_72"] = base["close"] - base["ema_72"]
    base["dist_ema_100"] = base["close"] - base["ema_100"]
    base["dist_ema_200"] = base["close"] - base["ema_200"]

    base["ema_9_acima_17"] = (base["ema_9"] > base["ema_17"]).astype(int)
    base["ema_17_acima_34"] = (base["ema_17"] > base["ema_34"]).astype(int)
    base["ema_34_acima_50"] = (base["ema_34"] > base["ema_50"]).astype(int)
    base["ema_50_acima_200"] = (base["ema_50"] > base["ema_200"]).astype(int)

    # VWAP diário
    base["pv"] = base["close"] * base["volume"]
    volume_acum = base.groupby("Data")["volume"].cumsum().replace(0, np.nan)
    pv_acum = base.groupby("Data")["pv"].cumsum()

    base["vwap_dia"] = pv_acum / volume_acum
    base["dist_vwap_dia"] = base["close"] - base["vwap_dia"]
    base["close_acima_vwap"] = (base["close"] > base["vwap_dia"]).astype(int)

    # TR / ATR / Keltner
    adx14, plus_di14, minus_di14, tr = calcular_adx(base, 14)

    base["tr"] = tr
    base["adx_14"] = adx14
    base["plus_di_14"] = plus_di14
    base["minus_di_14"] = minus_di14
    base["di_diff_14"] = plus_di14 - minus_di14

    for n in [7, 10, 14, 18, 20, 21, 34, 50]:
        base[f"atr_{n}"] = rma(base["tr"], n)
        base[f"atrp_{n}"] = base[f"atr_{n}"] / base["close"] * 100

        kc_mid = ema(base["close"], n)
        kc_upper = kc_mid + 2.0 * base[f"atr_{n}"]
        kc_lower = kc_mid - 2.0 * base[f"atr_{n}"]

        base[f"kc_mid_{n}"] = kc_mid
        base[f"kc_upper_{n}"] = kc_upper
        base[f"kc_lower_{n}"] = kc_lower
        base[f"kc_width_{n}"] = (kc_upper - kc_lower) / kc_mid.replace(0, np.nan) * 100
        base[f"kc_pos_{n}"] = (base["close"] - kc_lower) / (kc_upper - kc_lower).replace(0, np.nan)

    # Bollinger
    for n in [20, 34]:
        bb_mid = sma(base["close"], n)
        bb_std = base["close"].rolling(n).std()

        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        base[f"bb_mid_{n}"] = bb_mid
        base[f"bb_upper_{n}"] = bb_upper
        base[f"bb_lower_{n}"] = bb_lower
        base[f"bb_width_{n}"] = (bb_upper - bb_lower) / bb_mid.replace(0, np.nan) * 100
        base[f"bb_pos_{n}"] = (base["close"] - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

    # RSI
    for n in [7, 9, 14, 21, 34]:
        base[f"rsi_{n}"] = calcular_rsi(base["close"], n)
        base[f"rsi_{n}_slope_3"] = base[f"rsi_{n}"] - base[f"rsi_{n}"].shift(3)

    # Stoch RSI
    stoch_k, stoch_d = calcular_stoch_rsi(base["close"], 14, 14, 3, 3)
    base["stochrsi_k"] = stoch_k
    base["stochrsi_d"] = stoch_d
    base["stochrsi_diff"] = stoch_k - stoch_d

    # MACD
    macd_line, macd_signal, macd_hist = calcular_macd(base["close"], 12, 26, 9)

    base["macd_line"] = macd_line
    base["macd_signal"] = macd_signal
    base["macd_hist"] = macd_hist
    base["macd_hist_slope_3"] = macd_hist - macd_hist.shift(3)

    # Bias
    for n in [6, 12, 23, 24]:
        media = sma(base["close"], n)
        base[f"bias_{n}"] = (base["close"] - media) / media.replace(0, np.nan) * 100

    # Ranges / rompimentos
    for n in [5, 10, 20, 30, 50, 60, 120]:
        high_n = base["high"].rolling(n).max()
        low_n = base["low"].rolling(n).min()

        base[f"high_{n}"] = high_n
        base[f"low_{n}"] = low_n
        base[f"pos_range_{n}"] = (base["close"] - low_n) / (high_n - low_n).replace(0, np.nan)
        base[f"rompeu_min_{n}"] = (base["low"] <= low_n.shift(1)).astype(int)
        base[f"rompeu_max_{n}"] = (base["high"] >= high_n.shift(1)).astype(int)
        base[f"dist_low_min_{n}"] = base["close"] - low_n
        base[f"dist_high_max_{n}"] = high_n - base["close"]

    # Volume
    for n in [10, 20, 50]:
        vol_med = sma(base["volume"], n)
        base[f"volume_media_{n}"] = vol_med
        base[f"volume_ratio_{n}"] = base["volume"] / vol_med.replace(0, np.nan)

    # Horário / calendário
    base["Hora_SP_Decimal"] = base["DataHora_SP"].dt.hour + base["DataHora_SP"].dt.minute / 60.0
    base["sin_hora"] = np.sin(2 * np.pi * base["Hora_SP_Decimal"] / 24.0)
    base["cos_hora"] = np.cos(2 * np.pi * base["Hora_SP_Decimal"] / 24.0)
    base["dia_semana"] = pd.to_datetime(base["DataHora_SP"]).dt.dayofweek
    base["mes"] = pd.to_datetime(base["DataHora_SP"]).dt.month

    base["eh_0348"] = ((base["DataHora_SP"].dt.hour == 3) & (base["DataHora_SP"].dt.minute == 48)).astype(int)
    base["eh_0448"] = ((base["DataHora_SP"].dt.hour == 4) & (base["DataHora_SP"].dt.minute == 48)).astype(int)

    base["janela_0340_0400"] = (
        (base["Hora_SP_Decimal"] >= 3 + 40 / 60) &
        (base["Hora_SP_Decimal"] <= 4.0)
    ).astype(int)

    base["janela_0430_0500"] = (
        (base["Hora_SP_Decimal"] >= 4.5) &
        (base["Hora_SP_Decimal"] <= 5.0)
    ).astype(int)

    # Compatibilidade com nomes possíveis
    base["DataHora_Chicago"] = base["DataHora_IBKR"]
    base["Label_Nome"] = ""
    base["Label"] = 0

    return base


# =====================================================
# SCORE V3 / PROB V4
# =====================================================

def preparar_X(df_features, feature_cols):
    ultima = df_features.iloc[-1].copy()

    linha = {}

    for col in feature_cols:
        if col in df_features.columns:
            linha[col] = ultima[col]
        else:
            linha[col] = np.nan

    X = pd.DataFrame([linha])

    return X, ultima


def calcular_score_v3(modelo_v3, X_v3):
    probas = modelo_v3.predict_proba(X_v3)
    classes = list(modelo_v3.named_steps["model"].classes_)

    score_none = 0.0
    score_buy = 0.0
    score_sell = 0.0

    for i, classe in enumerate(classes):
        if classe == 0:
            score_none = float(probas[0, i])
        elif classe == 1:
            score_buy = float(probas[0, i])
        elif classe == 2:
            score_sell = float(probas[0, i])

    if score_buy > score_sell:
        direcao = "BUY"
        score_direcao = score_buy
        score_oposto = score_sell
    elif score_sell > score_buy:
        direcao = "SELL"
        score_direcao = score_sell
        score_oposto = score_buy
    else:
        direcao = "NONE"
        score_direcao = score_none
        score_oposto = max(score_buy, score_sell)

    score_diff = score_direcao - score_oposto

    return {
        "score_NONE": score_none,
        "score_BUY": score_buy,
        "score_SELL": score_sell,
        "Direcao": direcao,
        "score_direcao": score_direcao,
        "score_oposto": score_oposto,
        "score_diff": score_diff,
    }


def calcular_prob_v4(modelo_v4, X_v4):
    if hasattr(modelo_v4, "predict_proba"):
        prob = modelo_v4.predict_proba(X_v4)[0][1]
        return float(prob)

    pred = modelo_v4.predict(X_v4)[0]
    return float(pred)


def montar_X_v4(df_features, ultima, score_v3, feature_cols_v4):
    linha = {}

    for col in feature_cols_v4:
        if col in score_v3:
            linha[col] = score_v3[col]
        elif col in df_features.columns:
            linha[col] = ultima[col]
        else:
            linha[col] = np.nan

    X = pd.DataFrame([linha])

    return X


# =====================================================
# CONTROLE OPERACIONAL DO DIA
# =====================================================

def carregar_estado_operacional():
    estado_path = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v4.json")

    if not os.path.exists(estado_path):
        return {
            "data": "",
            "trades_hoje": 0,
            "loss_no_dia": False,
            "ultimo_sinal_datahora": "",
        }

    with open(estado_path, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_estado_operacional(estado):
    estado_path = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v4.json")
    salvar_json_seguro(estado, estado_path)


def atualizar_estado_para_data(estado, data_atual):
    data_str = str(data_atual)

    if estado.get("data") != data_str:
        estado = {
            "data": data_str,
            "trades_hoje": 0,
            "loss_no_dia": False,
            "ultimo_sinal_datahora": "",
        }

    return estado


# =====================================================
# GERAÇÃO DE SINAL
# =====================================================

def gerar_sinal_tempo_real(df_candles, config_v4, modelo_v3, features_v3, modelo_v4, features_v4):
    df_feat = preparar_features_tempo_real(df_candles)

    salvar_csv_seguro(df_feat.tail(300), ARQUIVO_FEATURES_TEMPO_REAL)

    X_v3, ultima = preparar_X(df_feat, features_v3)

    score_v3 = calcular_score_v3(modelo_v3, X_v3)

    X_v4 = montar_X_v4(df_feat, ultima, score_v3, features_v4)

    prob_win_v4 = calcular_prob_v4(modelo_v4, X_v4)

    hora_decimal = float(ultima["Hora_SP_Decimal"])
    dentro_horario = config_v4["hora_inicio"] <= hora_decimal <= config_v4["hora_fim"]

    data_atual = ultima["Data"]

    estado = carregar_estado_operacional()
    estado = atualizar_estado_para_data(estado, data_atual)

    datahora_ultimo_candle = str(ultima["DataHora_SP"])

    ja_enviou_nesse_candle = estado.get("ultimo_sinal_datahora") == datahora_ultimo_candle

    pode_operar_dia = (
        estado.get("trades_hoje", 0) < config_v4["max_trades_dia"] and
        (not config_v4["parar_apos_loss"] or not estado.get("loss_no_dia", False))
    )

    direcao = score_v3["Direcao"]

    cond_base = (
        dentro_horario and
        pode_operar_dia and
        not ja_enviou_nesse_candle and
        prob_win_v4 >= config_v4["prob_win_min"] and
        score_v3["score_diff"] >= config_v4["diferenca_minima"]
    )

    cond_buy = (
        cond_base and
        direcao == "BUY" and
        score_v3["score_BUY"] >= config_v4["score_buy_min"] and
        score_v3["score_BUY"] > score_v3["score_SELL"]
    )

    cond_sell = (
        cond_base and
        direcao == "SELL" and
        score_v3["score_SELL"] >= config_v4["score_sell_min"] and
        score_v3["score_SELL"] > score_v3["score_BUY"]
    )

    sinal = "none"

    if cond_buy:
        sinal = "buy"
    elif cond_sell:
        sinal = "sell"

    preco_entrada_ref = float(ultima["close"])

    if sinal == "buy":
        preco_take = preco_entrada_ref + config_v4["take_pontos"]
        preco_stop = preco_entrada_ref - config_v4["stop_pontos"]
    elif sinal == "sell":
        preco_take = preco_entrada_ref - config_v4["take_pontos"]
        preco_stop = preco_entrada_ref + config_v4["stop_pontos"]
    else:
        preco_take = np.nan
        preco_stop = np.nan

    motivo = "sem_sinal"

    if not dentro_horario:
        motivo = "fora_do_horario_v4"
    elif ja_enviou_nesse_candle:
        motivo = "sinal_ja_enviado_neste_candle"
    elif not pode_operar_dia:
        motivo = "limite_diario_ou_loss_no_dia"
    elif prob_win_v4 < config_v4["prob_win_min"]:
        motivo = "prob_win_v4_abaixo_minimo"
    elif score_v3["score_diff"] < config_v4["diferenca_minima"]:
        motivo = "score_diff_abaixo_minimo"
    elif sinal == "none":
        motivo = "score_buy_sell_nao_passou"
    else:
        motivo = "sinal_valido"

    payload = {
        "sinal": sinal,
        "motivo": motivo,
        "modo_seguro_sem_ordem": MODO_SEGURO_SEM_ORDEM,
        "datahora_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "datahora_ultimo_candle_sp": datahora_ultimo_candle,
        "data": str(data_atual),
        "preco_close": preco_entrada_ref,
        "preco_take": None if pd.isna(preco_take) else float(preco_take),
        "preco_stop": None if pd.isna(preco_stop) else float(preco_stop),
        "take_pontos": config_v4["take_pontos"],
        "stop_pontos": config_v4["stop_pontos"],
        "hora_decimal_sp": hora_decimal,
        "dentro_horario_v4": bool(dentro_horario),
        "prob_win_v4": float(prob_win_v4),
        "prob_win_min": config_v4["prob_win_min"],
        "Direcao": direcao,
        "score_NONE": float(score_v3["score_NONE"]),
        "score_BUY": float(score_v3["score_BUY"]),
        "score_SELL": float(score_v3["score_SELL"]),
        "score_direcao": float(score_v3["score_direcao"]),
        "score_oposto": float(score_v3["score_oposto"]),
        "score_diff": float(score_v3["score_diff"]),
        "score_buy_min": config_v4["score_buy_min"],
        "score_sell_min": config_v4["score_sell_min"],
        "diferenca_minima": config_v4["diferenca_minima"],
        "trades_hoje": estado.get("trades_hoje", 0),
        "max_trades_dia": config_v4["max_trades_dia"],
        "loss_no_dia": estado.get("loss_no_dia", False),
        "parar_apos_loss": config_v4["parar_apos_loss"],
    }

    if sinal in ["buy", "sell"]:
        estado["trades_hoje"] = int(estado.get("trades_hoje", 0)) + 1
        estado["ultimo_sinal_datahora"] = datahora_ultimo_candle
        salvar_estado_operacional(estado)

    return payload


def salvar_payload_sinal(payload):
    sinal = payload.get("sinal", "none")

    salvar_txt_seguro(sinal, ARQUIVO_SINAL_TXT)
    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL_JSON)

    append_log(payload)

    print("\n=====================================================")
    print("SINAL ATUAL")
    print("=====================================================")
    print(json.dumps(payload, ensure_ascii=False, indent=4, default=str))

    print("\nArquivos atualizados:")
    print(ARQUIVO_SINAL_TXT)
    print(ARQUIVO_ULTIMO_SINAL_JSON)
    print(ARQUIVO_LOG)


# =====================================================
# EXECUÇÃO
# =====================================================

def executar_uma_vez():
    config_v4 = carregar_config_v4()

    modelo_v3, features_v3, config_v3 = carregar_modelo_v3()
    modelo_v4, features_v4 = carregar_modelo_v4()

    print("\nConfig V4:")
    print(json.dumps({
        "take": config_v4["take_pontos"],
        "stop": config_v4["stop_pontos"],
        "prob_win_min": config_v4["prob_win_min"],
        "score_buy_min": config_v4["score_buy_min"],
        "score_sell_min": config_v4["score_sell_min"],
        "hora_inicio": config_v4["hora_inicio"],
        "hora_fim": config_v4["hora_fim"],
        "max_trades_dia": config_v4["max_trades_dia"],
        "parar_apos_loss": config_v4["parar_apos_loss"],
    }, indent=4, ensure_ascii=False))

    ib = None

    try:
        ib = conectar_ibkr()
        contrato = obter_contrato_mnq(ib)
        candles = baixar_candles_2min(ib, contrato)

        payload = gerar_sinal_tempo_real(
            candles,
            config_v4,
            modelo_v3,
            features_v3,
            modelo_v4,
            features_v4
        )

        salvar_payload_sinal(payload)

    except Exception as e:
        payload = {
            "sinal": "none",
            "motivo": "erro",
            "erro": str(e),
            "datahora_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        salvar_payload_sinal(payload)

        print("ERRO:", e)

    finally:
        if ib is not None and ib.isConnected():
            ib.disconnect()
            print("IBKR desconectado.")


def main():
    print("=====================================================")
    print("SINAL V4 IBKR TEMPO REAL - V2 COM SCORE V3")
    print("=====================================================")

    if MODO_SEGURO_SEM_ORDEM:
        print("MODO SEGURO ATIVO: este script NÃO envia ordens.")
        print("Ele apenas gera sinal.txt e ultimo_sinal_v4_ibkr.json.")

    if RODAR_EM_LOOP:
        while True:
            executar_uma_vez()
            print(f"\nAguardando {INTERVALO_SEGUNDOS} segundos...\n")
            time.sleep(INTERVALO_SEGUNDOS)
    else:
        executar_uma_vez()

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()