import pandas as pd
import numpy as np

ARQUIVO = "mercado_real.csv"
TICK = 0.25

TAKE_PONTOS = 50.0
STOP_PONTOS = 100.0

BIAS_PERIODO = 25
EMA_PERIODO = 17

K_LIMITE_COMPRA = 30
K_LIMITE_VENDA = 70

BIAS_LIMITE_COMPRA = -0.12
BIAS_LIMITE_VENDA = 0.12


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def stoch_rsi(close, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    rsi_vals = rsi(close, rsi_period)
    min_rsi = rsi_vals.rolling(stoch_period).min()
    max_rsi = rsi_vals.rolling(stoch_period).max()

    stoch = 100 * (rsi_vals - min_rsi) / (max_rsi - min_rsi)
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return rsi_vals, stoch, k, d


def crossover(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


# =========================
# LEITURA
# =========================
df = pd.read_csv(ARQUIVO)
df = df.rename(columns={"time": "datetime"})
df["datetime"] = pd.to_datetime(df["datetime"])
df = df.sort_values("datetime").reset_index(drop=True)

# =========================
# INDICADORES
# =========================
df["ema17"] = ema(df["close"], EMA_PERIODO)
df["sma_bias"] = df["close"].rolling(BIAS_PERIODO).mean()
df["bias"] = (df["close"] - df["sma_bias"]) / df["sma_bias"] * 100

if "K" in df.columns and "D" in df.columns:
    df["k"] = df["K"]
    df["d"] = df["D"]
else:
    _, _, df["k"], df["d"] = stoch_rsi(df["close"])

df["cross_up"] = crossover(df["k"], df["d"])
df["cross_down"] = crossunder(df["k"], df["d"])

df["acima_media"] = df["close"] > df["ema17"]
df["abaixo_media"] = df["close"] < df["ema17"]

df["candle_reacao_alta"] = df["close"] > df["open"]
df["candle_reacao_baixa"] = df["close"] < df["open"]

# =========================
# ENTRADAS
# =========================
df["compra"] = (
    (df["bias"] <= BIAS_LIMITE_COMPRA) &
    (df["k"] <= K_LIMITE_COMPRA) &
    (df["cross_up"] | (df["k"] > df["d"])) &
    df["abaixo_media"] &
    df["candle_reacao_alta"]
)

df["venda"] = (
    (df["bias"] >= BIAS_LIMITE_VENDA) &
    (df["k"] >= K_LIMITE_VENDA) &
    (df["cross_down"] | (df["k"] < df["d"])) &
    df["acima_media"] &
    df["candle_reacao_baixa"]
)

# =========================
# SIMULAÇÃO
# =========================
registros = []

for i in range(len(df) - 1):
    row = df.iloc[i]

    direcao = None
    if row["compra"]:
        direcao = 1
    elif row["venda"]:
        direcao = -1

    if direcao is None:
        continue

    entrada = row["close"]

    if direcao == 1:
        take_price = entrada + TAKE_PONTOS
        stop_price = entrada - STOP_PONTOS
    else:
        take_price = entrada - TAKE_PONTOS
        stop_price = entrada + STOP_PONTOS

    resultado = None
    preco_saida = None
    motivo = None

    for j in range(i + 1, len(df)):
        prox = df.iloc[j]

        if direcao == 1:
            bate_take = prox["high"] >= take_price
            bate_stop = prox["low"] <= stop_price

            if bate_take and bate_stop:
                preco_saida = stop_price
                resultado = 0
                motivo = "stop_e_take_mesmo_candle"
                break
            elif bate_stop:
                preco_saida = stop_price
                resultado = 0
                motivo = "stop"
                break
            elif bate_take:
                preco_saida = take_price
                resultado = 1
                motivo = "take"
                break
        else:
            bate_take = prox["low"] <= take_price
            bate_stop = prox["high"] >= stop_price

            if bate_take and bate_stop:
                preco_saida = stop_price
                resultado = 0
                motivo = "stop_e_take_mesmo_candle"
                break
            elif bate_stop:
                preco_saida = stop_price
                resultado = 0
                motivo = "stop"
                break
            elif bate_take:
                preco_saida = take_price
                resultado = 1
                motivo = "take"
                break

    if resultado is None:
        continue

    pnl = (preco_saida - entrada) if direcao == 1 else (entrada - preco_saida)

    registros.append({
        "datetime_entrada": row["datetime"],
        "tipo": "BUY" if direcao == 1 else "SELL",
        "entrada": entrada,
        "saida": preco_saida,
        "resultado": resultado,
        "motivo_saida": motivo,
        "pnl_pontos": pnl,
        "bias": row["bias"],
        "k": row["k"],
        "d": row["d"],
        "ema17": row["ema17"]
    })

trades = pd.DataFrame(registros)

print("Quantidade de trades:", len(trades))

if len(trades) > 0:
    print("\nResultado geral:")
    print(trades["resultado"].value_counts())

    print("\nPor tipo:")
    print(pd.crosstab(trades["tipo"], trades["resultado"]))

    print("\nMotivos de saída:")
    print(trades["motivo_saida"].value_counts())

    print("\nPnL total:", trades["pnl_pontos"].sum())
    print("PnL médio:", trades["pnl_pontos"].mean())

    trades.to_csv("trades_video_estrategia_a.csv", index=False)
    print("\nArquivo salvo: trades_video_estrategia_a.csv")
else:
    print("Nenhum trade encontrado.")