import os
import time
import warnings
from datetime import datetime, date, time as dtime

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix


warnings.filterwarnings("ignore")


# =====================================================
# CONFIGURAÇÕES WINDOWS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

ARQUIVO_PRECOS = os.path.join(BASE_DIR, "MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv")

ARQUIVO_SCORE_V3 = os.path.join(
    BASE_DIR,
    "saida_ml_entradas_video_v3",
    "05_v3_score_todos_candles.csv.gz"
)

# Planilha nova com mais entradas. O V4 não depende dela para treinar,
# mas lê para comparação e conferência.
ARQUIVO_ENTRADAS_VIDEO = os.path.join(
    BASE_DIR,
    "Entrada video-priemira amostra - Copia.xlsx"
)

PASTA_SAIDA = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")
os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_CANDIDATOS = os.path.join(PASTA_SAIDA, "01_v4_candidatos_rotulados.csv.gz")
ARQUIVO_MODELOS = os.path.join(PASTA_SAIDA, "02_v4_resultado_modelos.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "03_v4_importancia_features.csv")
ARQUIVO_SCORE_CANDIDATOS = os.path.join(PASTA_SAIDA, "04_v4_score_candidatos.csv.gz")
ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "05_v4_otimizacao_resultados.csv.gz")
ARQUIVO_TOP = os.path.join(PASTA_SAIDA, "06_v4_top_resultados.csv")
ARQUIVO_MELHOR = os.path.join(PASTA_SAIDA, "07_v4_melhor_resumo.csv")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "08_v4_melhor_trades.csv.gz")

ARQUIVO_CHECKPOINT_RESULTADOS = os.path.join(PASTA_SAIDA, "checkpoint_v4_resultados.csv.gz")
ARQUIVO_CHECKPOINT_MELHOR = os.path.join(PASTA_SAIDA, "checkpoint_v4_melhor.csv")
ARQUIVO_CHECKPOINT_TRADES = os.path.join(PASTA_SAIDA, "checkpoint_v4_melhor_trades.csv.gz")

# =====================================================
# PARÂMETROS DO OPERACIONAL
# =====================================================

TAKE_PONTOS = 50.5
STOPS_TESTE = [117.0, 120.0]

MAX_CANDLES_FUTURO = 720
MODO_ENTRADA = "close_signal"

# Janelas para gerar candidatos.
HORA_CANDIDATO_INICIO = 0.0
HORA_CANDIDATO_FIM = 12.0

# Filtro mínimo para criar candidato.
# Quanto mais baixo, mais candidatos e mais pesado.
SCORE_MIN_CANDIDATO = 0.50

# Split temporal para treinar o anti-loss.
SPLIT_DATE = pd.Timestamp("2025-07-01")

# Checkpoint da otimização.
SALVAR_A_CADA_RESULTADOS = 500

# =====================================================
# GRID DE OTIMIZAÇÃO FINAL
# =====================================================

PROB_WIN_LISTA = [
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.72, 0.74, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88,
    0.90, 0.92, 0.94, 0.96
]

SCORE_BUY_LISTA = [
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.72, 0.74, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90
]

SCORE_SELL_LISTA = [
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.72, 0.74, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90
]

DIFERENCAS_LISTA = [
    0.00, 0.02, 0.04, 0.06, 0.08,
    0.10, 0.12, 0.15, 0.18, 0.20
]

HORARIOS_LISTA = [
    (0.0, 6.0),
    (3.0, 6.0),
    (3.5, 4.1),
    (3.6, 4.0),
    (3.75, 3.90),
    (4.0, 8.0),
    (6.0, 10.0),
    (8.0, 12.0),
    (0.0, 12.0),
]

MAX_TRADES_DIA_LISTA = [1, 3, 5]
PARAR_APOS_LOSS_LISTA = [True, False]

TRADES_MINIMO_TOP = 100
WINRATE_MINIMO_TOP = 80.0


# =====================================================
# FUNÇÕES DE ARQUIVO
# =====================================================

def salvar_csv_seguro(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(temp, index=False, encoding="utf-8-sig", compression="gzip")
    else:
        df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)


def limpar_temporarios():
    if not os.path.exists(PASTA_SAIDA):
        return

    for nome in os.listdir(PASTA_SAIDA):
        if nome.endswith(".tmp"):
            caminho = os.path.join(PASTA_SAIDA, nome)
            try:
                os.remove(caminho)
                print("Temporário removido:", caminho)
            except Exception:
                pass


# =====================================================
# LEITURA DA PLANILHA DO VÍDEO PARA CONTAGEM
# =====================================================

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

    if isinstance(valor, dtime):
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


def carregar_entradas_video():
    if not os.path.exists(ARQUIVO_ENTRADAS_VIDEO):
        print("Planilha do vídeo não encontrada. Continuando sem ela.")
        return pd.DataFrame()

    try:
        bruto = pd.read_excel(ARQUIVO_ENTRADAS_VIDEO)

        col_data = find_col(bruto, ["data", "date"])
        col_hora = find_col(bruto, ["hora", "time"])
        col_sinal = find_col(bruto, ["sinal", "signal", "direcao", "direção"])

        if col_data is None or col_hora is None or col_sinal is None:
            print("Não consegui identificar colunas da planilha do vídeo.")
            return pd.DataFrame()

        bruto["data_limpa"] = bruto[col_data].apply(parse_data)
        bruto["data_corrigida"] = bruto["data_limpa"].ffill()
        bruto["hora_limpa"] = bruto[col_hora].apply(parse_hora)
        bruto["sinal_limpo"] = bruto[col_sinal].astype(str).str.lower().str.strip()

        ent = bruto[bruto["sinal_limpo"].isin(["comprar", "vender", "buy", "sell"])].copy()

        ent["DataHora_Video"] = [
            pd.Timestamp.combine(d.date(), h)
            if pd.notna(d) and h is not None
            else pd.NaT
            for d, h in zip(ent["data_corrigida"], ent["hora_limpa"])
        ]

        ent["Direcao_Video"] = ent["sinal_limpo"].map({
            "comprar": "BUY",
            "buy": "BUY",
            "vender": "SELL",
            "sell": "SELL"
        })

        ent = ent.dropna(subset=["DataHora_Video"]).copy()
        ent = ent[["DataHora_Video", "Direcao_Video"]].copy()

        print("Entradas do vídeo carregadas:", len(ent))
        print(ent["Direcao_Video"].value_counts())

        return ent

    except Exception as e:
        print("Erro ao ler planilha do vídeo:", e)
        return pd.DataFrame()


# =====================================================
# INDICADORES / FEATURES
# =====================================================

def rsi(series, periodo=14):
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    rs = media_ganho / media_perda.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def adx(df, periodo=14):
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
    adx_val = dx.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    return adx_val, plus_di, minus_di


def choppiness(df, periodo=14):
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

    return 100 * np.log10(tr_sum / (high_max - low_min).replace(0, np.nan)) / np.log10(periodo)


def criar_features(base):
    print("Criando features V4...")

    df = base.copy()
    feats = {}

    feats["range"] = df["high"] - df["low"]
    feats["body"] = df["close"] - df["open"]
    feats["body_abs"] = feats["body"].abs()
    feats["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    feats["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    feats["body_range_pct"] = feats["body_abs"] / feats["range"].replace(0, np.nan)
    feats["close_pos_range"] = (df["close"] - df["low"]) / feats["range"].replace(0, np.nan)

    feats["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
    feats["sin_hora"] = np.sin(2 * np.pi * feats["Hora_SP_Decimal"] / 24)
    feats["cos_hora"] = np.cos(2 * np.pi * feats["Hora_SP_Decimal"] / 24)
    feats["dia_semana"] = df["DataHora_SP"].dt.dayofweek
    feats["mes"] = df["DataHora_SP"].dt.month

    hora_min = df["DataHora_SP"].dt.strftime("%H:%M")
    feats["eh_0348"] = (hora_min == "03:48").astype(int)
    feats["eh_0448"] = (hora_min == "04:48").astype(int)
    feats["janela_0340_0400"] = ((hora_min >= "03:40") & (hora_min <= "04:00")).astype(int)
    feats["janela_0430_0500"] = ((hora_min >= "04:30") & (hora_min <= "05:00")).astype(int)

    feats["logret_1"] = np.log(df["close"] / df["close"].shift(1))

    for n in [1, 2, 3, 5, 8, 10, 15, 20, 30, 60, 120]:
        feats[f"ret_{n}"] = df["close"].pct_change(n)
        feats[f"pts_change_{n}"] = df["close"] - df["close"].shift(n)
        feats[f"volatilidade_ret_{n}"] = feats["logret_1"].rolling(n).std()

    for n in [5, 10, 15, 20, 30, 60, 120]:
        feats[f"range_ma_{n}"] = feats["range"].rolling(n).mean()
        feats[f"range_ratio_{n}"] = feats["range"] / feats[f"range_ma_{n}"].replace(0, np.nan)

        feats[f"volume_ma_{n}"] = df["volume"].rolling(n).mean()
        feats[f"volume_ratio_{n}"] = df["volume"] / feats[f"volume_ma_{n}"].replace(0, np.nan)

        if "barCount" in df.columns:
            feats[f"barcount_ma_{n}"] = df["barCount"].rolling(n).mean()
            feats[f"barcount_ratio_{n}"] = df["barCount"] / feats[f"barcount_ma_{n}"].replace(0, np.nan)

    if "barCount" in df.columns:
        feats["volume_por_negocio"] = df["volume"] / df["barCount"].replace(0, np.nan)

    vol_med_hora = df.groupby(hora_min)["volume"].transform("median")
    feats["volume_relativo_horario"] = df["volume"] / vol_med_hora.replace(0, np.nan)

    emas = [9, 17, 20, 34, 50, 72, 100, 200]

    for n in emas:
        ema = df["close"].ewm(span=n, adjust=False).mean()
        feats[f"ema_{n}"] = ema
        feats[f"dist_ema_{n}"] = df["close"] - ema
        feats[f"dist_ema_{n}_pct"] = (df["close"] - ema) / df["close"] * 100
        feats[f"ema_{n}_slope_3"] = ema - ema.shift(3)
        feats[f"ema_{n}_slope_10"] = ema - ema.shift(10)

    for a, b in [(9, 17), (17, 34), (20, 50), (34, 72), (50, 100), (100, 200)]:
        top = pd.concat([feats[f"ema_{a}"], feats[f"ema_{b}"]], axis=1).max(axis=1)
        bottom = pd.concat([feats[f"ema_{a}"], feats[f"ema_{b}"]], axis=1).min(axis=1)

        feats[f"trend_cloud_{a}_{b}_bull"] = (feats[f"ema_{a}"] > feats[f"ema_{b}"]).astype(int)
        feats[f"trend_cloud_{a}_{b}_thickness"] = top - bottom
        feats[f"trend_cloud_{a}_{b}_thickness_pct"] = (top - bottom) / df["close"] * 100
        feats[f"trend_cloud_{a}_{b}_pos"] = (df["close"] - bottom) / (top - bottom).replace(0, np.nan)
        feats[f"trend_cloud_{a}_{b}_dist_top"] = df["close"] - top
        feats[f"trend_cloud_{a}_{b}_dist_bottom"] = df["close"] - bottom

    feats["ema17_acima_ema34"] = (feats["ema_17"] > feats["ema_34"]).astype(int)
    feats["close_acima_ema17"] = (df["close"] > feats["ema_17"]).astype(int)
    feats["close_acima_ema34"] = (df["close"] > feats["ema_34"]).astype(int)
    feats["dist_ema17_34"] = feats["ema_17"] - feats["ema_34"]

    for n in [6, 9, 12, 17, 20, 23, 24, 34, 50]:
        sma = df["close"].rolling(n).mean()
        feats[f"bias_{n}"] = (df["close"] - sma) / sma * 100

    for n in [7, 9, 14, 21, 34]:
        feats[f"rsi_{n}"] = rsi(df["close"], n)
        feats[f"rsi_{n}_slope_3"] = feats[f"rsi_{n}"] - feats[f"rsi_{n}"].shift(3)

    for n in [8, 14, 21]:
        r = feats[f"rsi_{n}"] if f"rsi_{n}" in feats else rsi(df["close"], n)
        minimo = r.rolling(n).min()
        maximo = r.rolling(n).max()
        stoch = 100 * (r - minimo) / (maximo - minimo).replace(0, np.nan)

        feats[f"stochrsi_{n}_k"] = stoch.rolling(3).mean()
        feats[f"stochrsi_{n}_d"] = feats[f"stochrsi_{n}_k"].rolling(3).mean()
        feats[f"stochrsi_{n}_k_menos_d"] = feats[f"stochrsi_{n}_k"] - feats[f"stochrsi_{n}_d"]

    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    feats["true_range"] = tr

    for n in [7, 10, 14, 18, 21, 34]:
        atr_n = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        feats[f"atr_{n}"] = atr_n
        feats[f"atrp_{n}"] = atr_n / df["close"] * 100
        feats[f"tr_ratio_atr_{n}"] = tr / atr_n.replace(0, np.nan)

        feats[f"tr_decision_up_{n}"] = df["close"].shift(1) + atr_n
        feats[f"tr_decision_down_{n}"] = df["close"].shift(1) - atr_n
        feats[f"dist_tr_decision_up_{n}"] = df["close"] - feats[f"tr_decision_up_{n}"]
        feats[f"dist_tr_decision_down_{n}"] = df["close"] - feats[f"tr_decision_down_{n}"]
        feats[f"rompeu_decision_up_{n}"] = (df["high"] >= feats[f"tr_decision_up_{n}"]).astype(int)
        feats[f"rompeu_decision_down_{n}"] = (df["low"] <= feats[f"tr_decision_down_{n}"]).astype(int)

    for n in [20, 34, 50]:
        media = df["close"].rolling(n).mean()
        desvio = df["close"].rolling(n).std()

        upper = media + 2 * desvio
        lower = media - 2 * desvio

        feats[f"bb_width_{n}"] = (upper - lower) / media * 100
        feats[f"bb_pos_{n}"] = (df["close"] - lower) / (upper - lower).replace(0, np.nan)
        feats[f"dist_bb_upper_{n}"] = df["close"] - upper
        feats[f"dist_bb_lower_{n}"] = df["close"] - lower

    for n in [20, 34]:
        ema_mid = df["close"].ewm(span=n, adjust=False).mean()
        atr_n = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()

        kc_upper = ema_mid + 2 * atr_n
        kc_lower = ema_mid - 2 * atr_n

        feats[f"kc_width_{n}"] = (kc_upper - kc_lower) / ema_mid * 100
        feats[f"kc_pos_{n}"] = (df["close"] - kc_lower) / (kc_upper - kc_lower).replace(0, np.nan)
        feats[f"dist_kc_upper_{n}"] = df["close"] - kc_upper
        feats[f"dist_kc_lower_{n}"] = df["close"] - kc_lower

    data_sp = df["DataHora_SP"].dt.date
    tp = (df["high"] + df["low"] + df["close"]) / 3
    tpv = tp * df["volume"]

    cum_tpv = tpv.groupby(data_sp).cumsum()
    cum_vol = df["volume"].groupby(data_sp).cumsum()

    vwap = cum_tpv / cum_vol.replace(0, np.nan)

    feats["vwap_dia"] = vwap
    feats["dist_vwap_dia"] = df["close"] - vwap
    feats["dist_vwap_dia_pct"] = (df["close"] - vwap) / df["close"] * 100
    feats["close_acima_vwap"] = (df["close"] > vwap).astype(int)
    feats["vwap_slope_5"] = vwap - vwap.shift(5)

    for n in [5, 10, 15, 20, 30, 50, 60, 120]:
        high_max = df["high"].rolling(n).max()
        low_min = df["low"].rolling(n).min()

        feats[f"dist_high_max_{n}"] = df["close"] - high_max
        feats[f"dist_low_min_{n}"] = df["close"] - low_min
        feats[f"pos_range_{n}"] = (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
        feats[f"rompeu_max_{n}"] = (df["high"] >= high_max.shift(1)).astype(int)
        feats[f"rompeu_min_{n}"] = (df["low"] <= low_min.shift(1)).astype(int)

    macd_fast = df["close"].ewm(span=12, adjust=False).mean()
    macd_slow = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = macd_fast - macd_slow
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    feats["macd"] = macd_line
    feats["macd_signal"] = macd_signal
    feats["macd_hist"] = macd_hist
    feats["macd_hist_slope_3"] = macd_hist - macd_hist.shift(3)

    for n in [7, 14, 21]:
        a, plus, minus = adx(df, n)
        feats[f"adx_{n}"] = a
        feats[f"plus_di_{n}"] = plus
        feats[f"minus_di_{n}"] = minus
        feats[f"di_diff_{n}"] = plus - minus

    for n in [14, 21, 34]:
        feats[f"choppiness_{n}"] = choppiness(df, n)

    feats_df = pd.DataFrame(feats, index=df.index)
    feats_df = feats_df.replace([np.inf, -np.inf], np.nan)

    saida = pd.concat([df, feats_df], axis=1)

    print("Features criadas:", len(feats_df.columns))

    return saida, list(feats_df.columns)


# =====================================================
# SIMULAÇÃO
# =====================================================

def simular_trade(df_base, indice_sinal, direcao, take_pontos, stop_pontos):
    if MODO_ENTRADA == "next_open":
        indice_entrada = indice_sinal + 1
        if indice_entrada >= len(df_base):
            return None
        preco_entrada = df_base.loc[indice_entrada, "open"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]
    else:
        indice_entrada = indice_sinal
        preco_entrada = df_base.loc[indice_entrada, "close"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]

    if pd.isna(preco_entrada):
        return None

    if direcao == "BUY":
        preco_take = preco_entrada + take_pontos
        preco_stop = preco_entrada - stop_pontos
    else:
        preco_take = preco_entrada - take_pontos
        preco_stop = preco_entrada + stop_pontos

    fim = min(indice_entrada + MAX_CANDLES_FUTURO, len(df_base) - 1)

    maior_runup = 0.0
    maior_drawdown = 0.0

    for j in range(indice_entrada + 1, fim + 1):
        high = df_base.loc[j, "high"]
        low = df_base.loc[j, "low"]
        dt_saida = df_base.loc[j, "DataHora_SP"]

        if pd.isna(high) or pd.isna(low):
            continue

        if direcao == "BUY":
            maior_runup = max(maior_runup, high - preco_entrada)
            maior_drawdown = max(maior_drawdown, preco_entrada - low)

            bateu_take = high >= preco_take
            bateu_stop = low <= preco_stop

            if bateu_stop and bateu_take:
                return "LOSS", -stop_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

            if bateu_stop:
                return "LOSS", -stop_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

            if bateu_take:
                return "WIN", take_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

        else:
            maior_runup = max(maior_runup, preco_entrada - low)
            maior_drawdown = max(maior_drawdown, high - preco_entrada)

            bateu_take = low <= preco_take
            bateu_stop = high >= preco_stop

            if bateu_stop and bateu_take:
                return "LOSS", -stop_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

            if bateu_stop:
                return "LOSS", -stop_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

            if bateu_take:
                return "WIN", take_pontos, dt_entrada, dt_saida, j, maior_runup, maior_drawdown

    return "ABERTO", 0.0, dt_entrada, pd.NaT, fim, maior_runup, maior_drawdown


# =====================================================
# CANDIDATOS
# =====================================================

def gerar_candidatos_rotulados(base_feat, feature_cols):
    if os.path.exists(ARQUIVO_CANDIDATOS):
        print("Candidatos rotulados já existem. Carregando...")
        cand = pd.read_csv(ARQUIVO_CANDIDATOS, compression="gzip")
        cand["DataHora_SP"] = pd.to_datetime(cand["DataHora_SP"])
        cand["Data"] = pd.to_datetime(cand["Data"]).dt.date
        return cand

    print("Gerando candidatos e simulando take/stop...")

    base = base_feat.copy()
    base["Hora_SP_Decimal"] = base["DataHora_SP"].dt.hour + base["DataHora_SP"].dt.minute / 60
    base["Data"] = base["DataHora_SP"].dt.date

    cond_hora = (
        (base["Hora_SP_Decimal"] >= HORA_CANDIDATO_INICIO) &
        (base["Hora_SP_Decimal"] <= HORA_CANDIDATO_FIM)
    )

    cand_buy = base[
        cond_hora &
        (base["score_BUY"] >= SCORE_MIN_CANDIDATO) &
        (base["score_BUY"] > base["score_SELL"])
    ].copy()

    cand_buy["Direcao"] = "BUY"
    cand_buy["score_direcao"] = cand_buy["score_BUY"]
    cand_buy["score_oposto"] = cand_buy["score_SELL"]

    cand_sell = base[
        cond_hora &
        (base["score_SELL"] >= SCORE_MIN_CANDIDATO) &
        (base["score_SELL"] > base["score_BUY"])
    ].copy()

    cand_sell["Direcao"] = "SELL"
    cand_sell["score_direcao"] = cand_sell["score_SELL"]
    cand_sell["score_oposto"] = cand_sell["score_BUY"]

    cand = pd.concat([cand_buy, cand_sell], ignore_index=False)
    cand = cand.sort_values("DataHora_SP").copy()
    cand["score_diff"] = cand["score_direcao"] - cand["score_oposto"]

    print("Candidatos iniciais:", len(cand))

    registros = []

    for contador, (idx, row) in enumerate(cand.iterrows(), start=1):
        indice_sinal = int(idx)
        direcao = row["Direcao"]

        registro = {
            "indice_sinal": indice_sinal,
            "DataHora_SP": row["DataHora_SP"],
            "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
            "Data": row["Data"],
            "Hora_SP_Decimal": row["Hora_SP_Decimal"],
            "Direcao": direcao,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "score_BUY": row["score_BUY"],
            "score_SELL": row["score_SELL"],
            "score_NONE": row["score_NONE"],
            "score_direcao": row["score_direcao"],
            "score_oposto": row["score_oposto"],
            "score_diff": row["score_diff"],
        }

        for stop_pontos in STOPS_TESTE:
            resultado, pontos, dt_entrada, dt_saida, indice_saida, runup, drawdown = simular_trade(
                base,
                indice_sinal,
                direcao,
                TAKE_PONTOS,
                stop_pontos
            )

            sufixo = str(stop_pontos).replace(".", "_")

            registro[f"resultado_stop_{sufixo}"] = resultado
            registro[f"pontos_stop_{sufixo}"] = pontos
            registro[f"dt_entrada_stop_{sufixo}"] = dt_entrada
            registro[f"dt_saida_stop_{sufixo}"] = dt_saida
            registro[f"indice_saida_stop_{sufixo}"] = indice_saida
            registro[f"runup_stop_{sufixo}"] = runup
            registro[f"drawdown_stop_{sufixo}"] = drawdown
            registro[f"target_win_stop_{sufixo}"] = 1 if resultado == "WIN" else 0

        for col in feature_cols:
            registro[col] = row[col]

        registros.append(registro)

        if contador % 5000 == 0:
            print(f"Candidatos simulados: {contador}/{len(cand)}")

    cand_final = pd.DataFrame(registros)

    salvar_csv_seguro(cand_final, ARQUIVO_CANDIDATOS, compactado=True)

    print("Candidatos salvos:", len(cand_final))

    return cand_final


# =====================================================
# TREINAMENTO ANTI-LOSS
# =====================================================

def treinar_modelo_antiloss(cand, feature_cols):
    print("\nTreinando modelos anti-loss...")

    stop_base = "117_0"
    target_col = f"target_win_stop_{stop_base}"

    treino_df = cand[cand[f"resultado_stop_{stop_base}"].isin(["WIN", "LOSS"])].copy()

    X = treino_df[feature_cols + [
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "Hora_SP_Decimal"
    ]]

    y = treino_df[target_col]

    train_mask = treino_df["DataHora_SP"] < SPLIT_DATE

    X_train = X[train_mask]
    y_train = y[train_mask]

    X_test = X[~train_mask]
    y_test = y[~train_mask]

    modelos = {
        "ExtraTrees_V4": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=500,
                max_depth=10,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            ))
        ]),
        "RandomForest_V4": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=400,
                max_depth=10,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1
            ))
        ]),
        "HistGradientBoosting_V4": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingClassifier(
                max_iter=300,
                learning_rate=0.035,
                max_leaf_nodes=24,
                l2_regularization=0.25,
                random_state=42
            ))
        ])
    }

    try:
        from xgboost import XGBClassifier

        modelos["XGBoost_V4"] = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", XGBClassifier(
                n_estimators=450,
                max_depth=4,
                learning_rate=0.035,
                subsample=0.85,
                colsample_bytree=0.85,
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1
            ))
        ])

        print("XGBoost encontrado e incluído.")

    except Exception:
        print("XGBoost não instalado. Continuando com sklearn.")

    resultados = []
    melhor_modelo = None
    melhor_nome = None
    melhor_score = -999

    for nome, modelo in modelos.items():
        print("\n====================================")
        print("Modelo:", nome)
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
            "features": X.shape[1],
            "split_date": str(SPLIT_DATE)
        })

        if bacc > melhor_score:
            melhor_score = bacc
            melhor_modelo = modelo
            melhor_nome = nome

    res_modelos = pd.DataFrame(resultados)
    salvar_csv_seguro(res_modelos, ARQUIVO_MODELOS, compactado=False)

    print("\nMelhor modelo V4:", melhor_nome)

    modelo_interno = melhor_modelo.named_steps["model"]

    feature_model_cols = list(X.columns)

    if hasattr(modelo_interno, "feature_importances_"):
        importancia = pd.DataFrame({
            "feature": feature_model_cols,
            "importancia": modelo_interno.feature_importances_
        }).sort_values("importancia", ascending=False)
    else:
        importancia = pd.DataFrame({
            "feature": feature_model_cols,
            "importancia": np.nan
        })

    salvar_csv_seguro(importancia, ARQUIVO_IMPORTANCIA, compactado=False)

    print("\nTop 40 features V4:")
    print(importancia.head(40))

    X_all = cand[feature_model_cols]
    probas = melhor_modelo.predict_proba(X_all)
    classes = list(melhor_modelo.named_steps["model"].classes_)

    cand_score = cand.copy()
    cand_score["prob_win_v4"] = 0.0

    for i, classe in enumerate(classes):
        if classe == 1:
            cand_score["prob_win_v4"] = probas[:, i]

    salvar_csv_seguro(cand_score, ARQUIVO_SCORE_CANDIDATOS, compactado=True)

    print("Score de candidatos V4 salvo:", ARQUIVO_SCORE_CANDIDATOS)

    return cand_score


# =====================================================
# OTIMIZAÇÃO FINAL
# =====================================================

def selecionar_trades(cand_score, config):
    stop_sufixo = str(config["stop_pontos"]).replace(".", "_")

    resultado_col = f"resultado_stop_{stop_sufixo}"
    pontos_col = f"pontos_stop_{stop_sufixo}"
    dt_entrada_col = f"dt_entrada_stop_{stop_sufixo}"
    dt_saida_col = f"dt_saida_stop_{stop_sufixo}"
    indice_saida_col = f"indice_saida_stop_{stop_sufixo}"
    runup_col = f"runup_stop_{stop_sufixo}"
    drawdown_col = f"drawdown_stop_{stop_sufixo}"

    base = cand_score.copy()

    cond = (
        (base["prob_win_v4"] >= config["prob_win_min"]) &
        (base["Hora_SP_Decimal"] >= config["hora_inicio"]) &
        (base["Hora_SP_Decimal"] <= config["hora_fim"]) &
        (base["score_diff"] >= config["diferenca_minima"])
    )

    cond_buy = (
        cond &
        (base["Direcao"] == "BUY") &
        (base["score_BUY"] >= config["score_buy_min"])
    )

    cond_sell = (
        cond &
        (base["Direcao"] == "SELL") &
        (base["score_SELL"] >= config["score_sell_min"])
    )

    candidatos = base[cond_buy | cond_sell].copy()

    if candidatos.empty:
        return pd.DataFrame()

    candidatos = candidatos.sort_values(["Data", "DataHora_SP"]).copy()

    trades = []

    for data, grupo in candidatos.groupby("Data"):
        grupo = grupo.sort_values(
            by=["prob_win_v4", "score_direcao", "score_diff", "DataHora_SP"],
            ascending=[False, False, False, True]
        ).copy()

        trades_dia = 0
        ultimo_indice_saida = -1
        teve_loss = False

        for _, row in grupo.iterrows():
            if trades_dia >= config["max_trades_dia"]:
                break

            if config["parar_apos_loss"] and teve_loss:
                break

            indice_sinal = int(row["indice_sinal"])
            indice_saida = int(row[indice_saida_col])

            if indice_sinal <= ultimo_indice_saida:
                continue

            resultado = row[resultado_col]

            if resultado not in ["WIN", "LOSS"]:
                continue

            trades_dia += 1
            ultimo_indice_saida = indice_saida

            if resultado == "LOSS":
                teve_loss = True

            trades.append({
                "DataHora_Sinal_SP": row["DataHora_SP"],
                "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
                "Data": row["Data"],
                "Hora_SP_Decimal": row["Hora_SP_Decimal"],
                "Direcao": row["Direcao"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "score_BUY": row["score_BUY"],
                "score_SELL": row["score_SELL"],
                "score_NONE": row["score_NONE"],
                "score_direcao": row["score_direcao"],
                "score_oposto": row["score_oposto"],
                "score_diff": row["score_diff"],
                "prob_win_v4": row["prob_win_v4"],
                "take_pontos": TAKE_PONTOS,
                "stop_pontos": config["stop_pontos"],
                "resultado": resultado,
                "pontos": row[pontos_col],
                "dt_entrada": row[dt_entrada_col],
                "dt_saida": row[dt_saida_col],
                "indice_saida": indice_saida,
                "runup": row[runup_col],
                "drawdown": row[drawdown_col],
            })

    return pd.DataFrame(trades)


def avaliar_config(cand_score, config):
    trades = selecionar_trades(cand_score, config)

    if trades.empty:
        return None, trades

    total = len(trades)
    wins = (trades["resultado"] == "WIN").sum()
    losses = (trades["resultado"] == "LOSS").sum()

    if total == 0:
        return None, trades

    winrate = wins / total * 100
    lucro = trades["pontos"].sum()

    gross_profit = trades.loc[trades["pontos"] > 0, "pontos"].sum()
    gross_loss = abs(trades.loc[trades["pontos"] < 0, "pontos"].sum())

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    diario = trades.groupby("Data")["pontos"].sum()
    pior_dia = diario.min() if len(diario) else np.nan
    melhor_dia = diario.max() if len(diario) else np.nan

    resumo = {
        **config,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro,
        "profit_factor": profit_factor,
        "buy_total": (trades["Direcao"] == "BUY").sum(),
        "sell_total": (trades["Direcao"] == "SELL").sum(),
        "media_prob_win": trades["prob_win_v4"].mean(),
        "min_prob_win": trades["prob_win_v4"].min(),
        "drawdown_medio_trade": trades["drawdown"].mean(),
        "drawdown_max_trade": trades["drawdown"].max(),
        "runup_medio_trade": trades["runup"].mean(),
        "runup_max_trade": trades["runup"].max(),
        "dias_operados": trades["Data"].nunique(),
        "pior_dia_pontos": pior_dia,
        "melhor_dia_pontos": melhor_dia,
    }

    return resumo, trades


def chave_melhor(resumo):
    pf = resumo["profit_factor"]
    if pf == np.inf:
        pf = 9999

    bonus = 0

    if resumo["winrate"] >= 95:
        bonus += 2_000_000
    elif resumo["winrate"] >= 90:
        bonus += 1_000_000
    elif resumo["winrate"] >= 85:
        bonus += 500_000
    elif resumo["winrate"] >= 80:
        bonus += 100_000

    if resumo["total_trades"] >= 180:
        bonus += 300_000
    elif resumo["total_trades"] >= 150:
        bonus += 150_000
    elif resumo["total_trades"] >= 100:
        bonus += 50_000

    return (
        bonus + resumo["lucro_pontos"],
        resumo["winrate"],
        resumo["total_trades"],
        pf
    )


def salvar_checkpoint(resultados, melhor, melhores_trades):
    if resultados:
        salvar_csv_seguro(pd.DataFrame(resultados), ARQUIVO_CHECKPOINT_RESULTADOS, compactado=True)

    if melhor is not None:
        salvar_csv_seguro(pd.DataFrame([melhor]), ARQUIVO_CHECKPOINT_MELHOR, compactado=False)

    if melhores_trades is not None and not melhores_trades.empty:
        salvar_csv_seguro(melhores_trades, ARQUIVO_CHECKPOINT_TRADES, compactado=True)

    print(f"CHECKPOINT V4 SALVO: {len(resultados)} resultados.")


def otimizar(cand_score):
    if os.path.exists(ARQUIVO_CHECKPOINT_RESULTADOS):
        print("Checkpoint V4 encontrado. Continuando...")
        cp = pd.read_csv(ARQUIVO_CHECKPOINT_RESULTADOS, compression="gzip")
        resultados = cp.to_dict("records")
        testadas = set(cp["config_key"].astype(str).tolist())
        print("Resultados carregados:", len(resultados))
    else:
        resultados = []
        testadas = set()

    melhor = None
    melhores_trades = None

    if os.path.exists(ARQUIVO_CHECKPOINT_MELHOR):
        m = pd.read_csv(ARQUIVO_CHECKPOINT_MELHOR)
        if not m.empty:
            melhor = m.iloc[0].to_dict()
            print("Melhor anterior carregado.")

    if os.path.exists(ARQUIVO_CHECKPOINT_TRADES):
        t = pd.read_csv(ARQUIVO_CHECKPOINT_TRADES, compression="gzip")
        if not t.empty:
            melhores_trades = t
            print("Trades do melhor carregados.")

    configs = []
    cid = 0

    for stop in STOPS_TESTE:
        for prob_min in PROB_WIN_LISTA:
            for max_trades_dia in MAX_TRADES_DIA_LISTA:
                for parar_apos_loss in PARAR_APOS_LOSS_LISTA:
                    for score_buy in SCORE_BUY_LISTA:
                        for score_sell in SCORE_SELL_LISTA:
                            for diff in DIFERENCAS_LISTA:
                                for h_ini, h_fim in HORARIOS_LISTA:
                                    cid += 1

                                    key = (
                                        f"stop={stop}|prob={prob_min}|maxdia={max_trades_dia}|"
                                        f"paraloss={parar_apos_loss}|buy={score_buy}|sell={score_sell}|"
                                        f"diff={diff}|h={h_ini}-{h_fim}"
                                    )

                                    configs.append({
                                        "config_id": cid,
                                        "config_key": key,
                                        "take_pontos": TAKE_PONTOS,
                                        "stop_pontos": stop,
                                        "prob_win_min": prob_min,
                                        "max_trades_dia": max_trades_dia,
                                        "parar_apos_loss": parar_apos_loss,
                                        "score_buy_min": score_buy,
                                        "score_sell_min": score_sell,
                                        "diferenca_minima": diff,
                                        "hora_inicio": h_ini,
                                        "hora_fim": h_fim,
                                    })

    print("Total de configurações V4:", len(configs))
    print("Já testadas:", len(testadas))

    inicio = time.time()
    novos = 0

    try:
        for i, config in enumerate(configs, start=1):
            if config["config_key"] in testadas:
                continue

            resumo, trades = avaliar_config(cand_score, config)

            testadas.add(config["config_key"])

            if resumo is not None:
                resultados.append(resumo)
                novos += 1

                if melhor is None or chave_melhor(resumo) > chave_melhor(melhor):
                    melhor = resumo
                    melhores_trades = trades.copy()

                    print("\nNOVO MELHOR V4:")
                    print(pd.Series(melhor))

            if novos >= SALVAR_A_CADA_RESULTADOS:
                salvar_checkpoint(resultados, melhor, melhores_trades)
                novos = 0

            if i % 1000 == 0:
                print(
                    f"{i}/{len(configs)} | resultados={len(resultados)} | "
                    f"testadas={len(testadas)} | tempo={(time.time() - inicio) / 60:.1f} min"
                )

    except KeyboardInterrupt:
        print("\nInterrompido. Salvando checkpoint V4...")
        salvar_checkpoint(resultados, melhor, melhores_trades)
        raise SystemExit

    except Exception as e:
        print("\nERRO NA OTIMIZAÇÃO V4:")
        print(e)
        print("Salvando checkpoint V4...")
        salvar_checkpoint(resultados, melhor, melhores_trades)
        raise

    salvar_checkpoint(resultados, melhor, melhores_trades)

    res = pd.DataFrame(resultados)

    if res.empty:
        print("Nenhum resultado V4.")
        return

    res["pf_ordem"] = res["profit_factor"].replace(np.inf, 9999)

    res = res.sort_values(
        by=["lucro_pontos", "winrate", "total_trades", "pf_ordem"],
        ascending=[False, False, False, False]
    )

    salvar_csv_seguro(res, ARQUIVO_RESULTADOS, compactado=True)

    top = res[
        (res["total_trades"] >= TRADES_MINIMO_TOP) &
        (res["winrate"] >= WINRATE_MINIMO_TOP)
    ].copy()

    top = top.sort_values(
        by=["winrate", "lucro_pontos", "total_trades", "pf_ordem"],
        ascending=[False, False, False, False]
    )

    salvar_csv_seguro(top.head(500), ARQUIVO_TOP, compactado=False)

    if melhor is not None:
        salvar_csv_seguro(pd.DataFrame([melhor]), ARQUIVO_MELHOR, compactado=False)

    if melhores_trades is not None and not melhores_trades.empty:
        salvar_csv_seguro(melhores_trades, ARQUIVO_MELHOR_TRADES, compactado=True)

    print("\n=====================================================")
    print("MELHOR V4")
    print("=====================================================")
    print(pd.Series(melhor))

    print("\n=====================================================")
    print("TOP 30 V4 COM FILTROS")
    print("=====================================================")

    if top.empty:
        print("Nenhum top com os critérios.")
    else:
        print(top.head(30))

    print("\nArquivos V4:")
    print(ARQUIVO_RESULTADOS)
    print(ARQUIVO_TOP)
    print(ARQUIVO_MELHOR)
    print(ARQUIVO_MELHOR_TRADES)


# =====================================================
# MAIN
# =====================================================

def main():
    limpar_temporarios()

    print("Carregando planilha de entradas do vídeo para conferência...")
    carregar_entradas_video()

    print("\nCarregando preços...")

    if not os.path.exists(ARQUIVO_PRECOS):
        raise FileNotFoundError(f"Não encontrei o arquivo de preços: {ARQUIVO_PRECOS}")

    if not os.path.exists(ARQUIVO_SCORE_V3):
        raise FileNotFoundError(f"Não encontrei o score V3: {ARQUIVO_SCORE_V3}")

    precos = pd.read_csv(ARQUIVO_PRECOS)
    score_v3 = pd.read_csv(ARQUIVO_SCORE_V3, compression="gzip")

    precos["DataHora_SP"] = pd.to_datetime(precos["DataHora_SP"])
    score_v3["DataHora_SP"] = pd.to_datetime(score_v3["DataHora_SP"])

    precos = precos.sort_values("DataHora_SP").reset_index(drop=True)
    score_v3 = score_v3.sort_values("DataHora_SP").reset_index(drop=True)

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

    score_cols = ["DataHora_SP", "score_BUY", "score_SELL", "score_NONE"]

    if "DataHora_Chicago" in score_v3.columns:
        score_cols.append("DataHora_Chicago")

    base = precos.merge(
        score_v3[score_cols],
        on="DataHora_SP",
        how="left",
        suffixes=("", "_score")
    )

    if "DataHora_Chicago_score" in base.columns and "DataHora_Chicago" not in base.columns:
        base["DataHora_Chicago"] = base["DataHora_Chicago_score"]

    for col in ["score_BUY", "score_SELL", "score_NONE"]:
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)

    print("Linhas base:", len(base))
    print("Início:", base["DataHora_SP"].min())
    print("Fim:", base["DataHora_SP"].max())

    base_feat, feature_cols = criar_features(base)

    cand = gerar_candidatos_rotulados(base_feat, feature_cols)

    if os.path.exists(ARQUIVO_SCORE_CANDIDATOS):
        print("Score V4 dos candidatos já existe. Carregando...")
        cand_score = pd.read_csv(ARQUIVO_SCORE_CANDIDATOS, compression="gzip")
        cand_score["DataHora_SP"] = pd.to_datetime(cand_score["DataHora_SP"])
        cand_score["Data"] = pd.to_datetime(cand_score["Data"]).dt.date
    else:
        cand_score = treinar_modelo_antiloss(cand, feature_cols)

    otimizar(cand_score)


if __name__ == "__main__":
    main()