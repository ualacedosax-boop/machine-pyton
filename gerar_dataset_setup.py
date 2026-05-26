import pandas as pd
import numpy as np

# =========================
# CONFIG
# =========================
ARQUIVO = "mercado_real.csv"
TIMEZONE = "America/Sao_Paulo"

TAKE_PONTOS = 50.5
ATR_MULT = 6
MIN_STOP = 80.0
MAX_STOP = 117.0

# tick do ativo
# ajuste se precisar
TICK = 0.25

# =========================
# FUNÇÕES AUXILIARES
# =========================
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

    stoch = 100 * (rsi_vals - min_rsi) / (max_rsi - min_rsi)
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return rsi_vals, stoch, k, d

def crossover(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))

def crossunder(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))

def barssince(cond):
    result = []
    last_true = None
    for i, val in enumerate(cond):
        if bool(val):
            last_true = i
            result.append(0)
        elif last_true is None:
            result.append(np.nan)
        else:
            result.append(i - last_true)
    return pd.Series(result, index=cond.index)

# =========================
# LER DADOS
# =========================
df = pd.read_csv(ARQUIVO)

df = df.rename(columns={"time": "datetime"})
df["datetime"] = pd.to_datetime(df["datetime"])
df = df.sort_values("datetime").reset_index(drop=True)

# se quiser retirar timezone, descomente:
# df["datetime"] = df["datetime"].dt.tz_convert(TIMEZONE)

# =========================
# HORÁRIO
# =========================
df["hora"] = df["datetime"].dt.hour
df["minuto"] = df["datetime"].dt.minute

df["horarioBloqueado"] = (
    ((df["hora"] == 17) & (df["minuto"] >= 40)) |
    (df["hora"] == 18) |
    ((df["hora"] == 19) & (df["minuto"] < 2))
)

df["fecharTudoAgora"] = (df["hora"] == 17) & (df["minuto"] == 40)

# =========================
# INDICADORES
# =========================
df["ema17"] = ema(df["close"], 17)
df["ema34"] = ema(df["close"], 34)

periodBias = 25
df["smaBias"] = df["close"].rolling(periodBias).mean()
df["bias"] = (df["close"] - df["smaBias"]) / df["smaBias"] * 100

df["retorno_log"] = np.log(df["close"] / df["close"].shift(1))
df["volAtual"] = df["retorno_log"].rolling(30).std()
df["volUsada"] = ema(df["volAtual"], 10)

fator = 0.6
df["limiteAlta"] = df["volUsada"] * fator * 100
df["limiteBaixa"] = -df["volUsada"] * fator * 100

df["rsi"], df["stoch"], df["k"], df["d"] = stoch_rsi(df["close"], 14, 14, 3, 3)

cross_up = crossover(df["k"], df["d"])
cross_down = crossunder(df["k"], df["d"])

df["bars_since_cross_up"] = barssince(cross_up)
df["bars_since_cross_down"] = barssince(cross_down)

df["crossUpRecent"] = df["bars_since_cross_up"] <= 3
df["crossDownRecent"] = df["bars_since_cross_down"] <= 3

df["stochCaindo"] = df["k"].shift(1) > df["k"].shift(2)
df["stochSubindo"] = df["k"].shift(1) < df["k"].shift(2)

df["toqueNaMedia"] = (df["low"] <= df["ema17"]) & (df["high"] >= df["ema17"])

df["filtroCompraVol"] = df["bias"] <= df["limiteBaixa"]
df["filtroVendaVol"] = df["bias"] >= df["limiteAlta"]

# =========================
# ENTRADAS
# =========================
df["compra"] = (
    df["toqueNaMedia"] &
    df["crossUpRecent"] &
    df["stochCaindo"] &
    (df["ema17"] > df["ema34"]) &
    df["filtroCompraVol"] &
    (~df["horarioBloqueado"])
)

df["venda"] = (
    df["toqueNaMedia"] &
    df["crossDownRecent"] &
    df["stochSubindo"] &
    (df["ema17"] < df["ema34"]) &
    df["filtroVendaVol"] &
    (~df["horarioBloqueado"])
)

# =========================
# ATR / STOP
# =========================
df["atr"] = atr(df, 14)
df["atrStop"] = df["atr"] * ATR_MULT
df["stopFinal"] = df["atrStop"].clip(lower=MIN_STOP, upper=MAX_STOP)

# =========================
# SIMULAÇÃO DOS SINAIS
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
    stop_pontos = row["stopFinal"]
    take_pontos = TAKE_PONTOS

    if direcao == 1:
        stop_price = entrada - stop_pontos
        take_price = entrada + take_pontos
    else:
        stop_price = entrada + stop_pontos
        take_price = entrada - take_pontos

    resultado = None
    preco_saida = None
    motivo_saida = None
    saida_idx = None

    for j in range(i + 1, len(df)):
        prox = df.iloc[j]

        # fechamento obrigatório
        if prox["fecharTudoAgora"]:
            preco_saida = prox["close"]
            motivo_saida = "fechamento_horario"
            saida_idx = j
            if direcao == 1:
                resultado = 1 if preco_saida > entrada else 0
            else:
                resultado = 1 if preco_saida < entrada else 0
            break

        if direcao == 1:
            bate_take = prox["high"] >= take_price
            bate_stop = prox["low"] <= stop_price

            if bate_take and bate_stop:
                # conservador: assume stop primeiro
                preco_saida = stop_price
                motivo_saida = "stop_e_take_mesmo_candle"
                resultado = 0
                saida_idx = j
                break
            elif bate_stop:
                preco_saida = stop_price
                motivo_saida = "stop"
                resultado = 0
                saida_idx = j
                break
            elif bate_take:
                preco_saida = take_price
                motivo_saida = "take"
                resultado = 1
                saida_idx = j
                break

        else:
            bate_take = prox["low"] <= take_price
            bate_stop = prox["high"] >= stop_price

            if bate_take and bate_stop:
                preco_saida = stop_price
                motivo_saida = "stop_e_take_mesmo_candle"
                resultado = 0
                saida_idx = j
                break
            elif bate_stop:
                preco_saida = stop_price
                motivo_saida = "stop"
                resultado = 0
                saida_idx = j
                break
            elif bate_take:
                preco_saida = take_price
                motivo_saida = "take"
                resultado = 1
                saida_idx = j
                break

    if resultado is None:
        continue

    registros.append({
        "datetime_entrada": row["datetime"],
        "tipo": "BUY" if direcao == 1 else "SELL",
        "entrada": entrada,
        "stop_pontos": stop_pontos,
        "take_pontos": take_pontos,
        "datetime_saida": df.iloc[saida_idx]["datetime"],
        "preco_saida": preco_saida,
        "motivo_saida": motivo_saida,
        "resultado": resultado,

        # features do candle de entrada
        "open": row["open"],
        "high": row["high"],
        "low": row["low"],
        "close": row["close"],
        "ema17": row["ema17"],
        "ema34": row["ema34"],
        "bias": row["bias"],
        "limiteAlta": row["limiteAlta"],
        "limiteBaixa": row["limiteBaixa"],
        "k": row["k"],
        "d": row["d"],
        "atr": row["atr"],
        "stopFinal": row["stopFinal"],
        "hora": row["hora"],
        "minuto": row["minuto"],
        "crossUpRecent": row["crossUpRecent"],
        "crossDownRecent": row["crossDownRecent"],
        "stochCaindo": row["stochCaindo"],
        "stochSubindo": row["stochSubindo"],
        "toqueNaMedia": row["toqueNaMedia"],
        "filtroCompraVol": row["filtroCompraVol"],
        "filtroVendaVol": row["filtroVendaVol"]
    })

# =========================
# DATASET FINAL
# =========================
dataset = pd.DataFrame(registros)

print("Quantidade de sinais encontrados:", len(dataset))

if len(dataset) > 0:
    print("\nResultados gerais:")
    print(dataset["resultado"].value_counts())

    print("\nResultado por tipo:")
    print(pd.crosstab(dataset["tipo"], dataset["resultado"]))

    print("\nMotivos de saída:")
    print(dataset["motivo_saida"].value_counts())

    print("\nPrimeiros 20 sinais:")
    print(dataset.head(20))

    dataset.to_csv("dataset_setup_ml.csv", index=False)
    print("\nArquivo salvo: dataset_setup_ml.csv")
else:
    print("Nenhum sinal encontrado.")