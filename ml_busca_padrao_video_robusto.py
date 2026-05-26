import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from joblib import Parallel, delayed
import os
import math
import time

ARQUIVO = "mercado_real.csv"

# =========================================================
# CONFIGURAÇÃO ROBUSTA
# =========================================================
N_JOBS = -1
LOTE_COMBINACOES = 100

# grade principal
EMA_PERIODOS = [9, 13, 17, 21, 34]
BIAS_PERIODOS = [20, 25, 30, 40]

K_LIMITE_COMPRA_LIST = [15, 20, 25, 30, 35]
K_LIMITE_VENDA_LIST = [65, 70, 75, 80, 85]

BIAS_LIMITE_COMPRA_LIST = [-0.30, -0.25, -0.20, -0.15, -0.12, -0.10]
BIAS_LIMITE_VENDA_LIST = [0.10, 0.12, 0.15, 0.20, 0.25, 0.30]

TAKE_LIST = [40.0, 50.0, 60.0, 70.0]
STOP_LIST = [70.0, 80.0, 90.0, 100.0, 117.0]

HORA_INICIO_LIST = [0, 4, 8, 10]
HORA_FIM_LIST = [12, 16, 20, 23]

USAR_CRUZAMENTO_OBRIGATORIO_LIST = [0, 1]
USAR_RETORNO_MEDIA_LIST = [0, 1]

# ranking final
MIN_SINAIS_RANKING = 20

# modelo
RF_N_ESTIMATORS = 400
RF_MAX_DEPTH = 10
RF_MIN_SAMPLES_LEAF = 4
RF_RANDOM_STATE = 42

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
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
    stoch = 100 * (rsi_vals - min_rsi) / (max_rsi - min_rsi + 1e-9)
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return rsi_vals, stoch, k, d

def crossover(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))

def crossunder(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))

def filtrar_horario(df, h_ini, h_fim):
    if h_ini <= h_fim:
        return (df["hora"] >= h_ini) & (df["hora"] <= h_fim)
    return (df["hora"] >= h_ini) | (df["hora"] <= h_fim)

def preparar_base():
    base = pd.read_csv(ARQUIVO)
    base = base.rename(columns={"time": "datetime"})
    base["datetime"] = pd.to_datetime(base["datetime"])
    base = base.sort_values("datetime").reset_index(drop=True)

    base["hora"] = base["datetime"].dt.hour
    base["minuto"] = base["datetime"].dt.minute
    base["dia_semana"] = base["datetime"].dt.dayofweek

    base["rsi14"] = rsi(base["close"], 14)
    base["atr14"] = atr(base, 14)
    base["range_candle"] = base["high"] - base["low"]
    base["body"] = (base["close"] - base["open"]).abs()
    base["close_pos"] = (base["close"] - base["low"]) / (base["high"] - base["low"] + 1e-9)

    base["dist_high_low"] = (base["high"] - base["low"]) / (base["close"] + 1e-9)
    base["ret_1"] = base["close"].pct_change(1)
    base["ret_2"] = base["close"].pct_change(2)
    base["ret_3"] = base["close"].pct_change(3)

    if "K" in base.columns and "D" in base.columns:
        base["k_base"] = base["K"]
        base["d_base"] = base["D"]
    else:
        _, _, base["k_base"], base["d_base"] = stoch_rsi(base["close"])

    return base

def processar_combinacao(combo, base):
    (
        ema_p,
        bias_p,
        k_compra,
        k_venda,
        bias_compra,
        bias_venda,
        take_pontos,
        stop_pontos,
        hora_ini,
        hora_fim,
        usar_cruzamento_obrigatorio,
        usar_retorno_media
    ) = combo

    df = base.copy()

    df["emaX"] = ema(df["close"], ema_p)
    df["emaSlope"] = df["emaX"].diff(3)

    df["smaBias"] = df["close"].rolling(bias_p).mean()
    df["biasX"] = (df["close"] - df["smaBias"]) / (df["smaBias"] + 1e-9) * 100

    df["k"] = df["k_base"]
    df["d"] = df["d_base"]
    df["kd_diff"] = df["k"] - df["d"]

    df["cross_up"] = crossover(df["k"], df["d"])
    df["cross_down"] = crossunder(df["k"], df["d"])

    df["acima_media"] = df["close"] > df["emaX"]
    df["abaixo_media"] = df["close"] < df["emaX"]

    df["tocou_media"] = (df["low"] <= df["emaX"]) & (df["high"] >= df["emaX"])
    df["dist_ema"] = (df["close"] - df["emaX"]) / (df["emaX"] + 1e-9)

    df["candle_reacao_alta"] = df["close"] > df["open"]
    df["candle_reacao_baixa"] = df["close"] < df["open"]

    horario_ok = filtrar_horario(df, hora_ini, hora_fim)

    cond_compra = (
        (df["biasX"] <= bias_compra) &
        (df["k"] <= k_compra) &
        df["abaixo_media"] &
        df["candle_reacao_alta"] &
        horario_ok
    )

    cond_venda = (
        (df["biasX"] >= bias_venda) &
        (df["k"] >= k_venda) &
        df["acima_media"] &
        df["candle_reacao_baixa"] &
        horario_ok
    )

    if usar_cruzamento_obrigatorio == 1:
        cond_compra = cond_compra & df["cross_up"]
        cond_venda = cond_venda & df["cross_down"]
    else:
        cond_compra = cond_compra & (df["cross_up"] | (df["k"] > df["d"]))
        cond_venda = cond_venda & (df["cross_down"] | (df["k"] < df["d"]))

    if usar_retorno_media == 1:
        cond_compra = cond_compra & df["tocou_media"]
        cond_venda = cond_venda & df["tocou_media"]

    df["compra"] = cond_compra
    df["venda"] = cond_venda

    registros = []

    n = len(df)
    for i in range(n - 1):
        row = df.iloc[i]

        direcao = 0
        if row["compra"]:
            direcao = 1
        elif row["venda"]:
            direcao = -1

        if direcao == 0:
            continue

        entrada = row["close"]

        if direcao == 1:
            take_price = entrada + take_pontos
            stop_price = entrada - stop_pontos
        else:
            take_price = entrada - take_pontos
            stop_price = entrada + stop_pontos

        resultado = None
        preco_saida = None
        motivo_saida = None

        for j in range(i + 1, n):
            prox = df.iloc[j]

            if direcao == 1:
                bate_take = prox["high"] >= take_price
                bate_stop = prox["low"] <= stop_price

                if bate_take and bate_stop:
                    preco_saida = stop_price
                    resultado = 0
                    motivo_saida = "stop_e_take_mesmo_candle"
                    break
                elif bate_stop:
                    preco_saida = stop_price
                    resultado = 0
                    motivo_saida = "stop"
                    break
                elif bate_take:
                    preco_saida = take_price
                    resultado = 1
                    motivo_saida = "take"
                    break
            else:
                bate_take = prox["low"] <= take_price
                bate_stop = prox["high"] >= stop_price

                if bate_take and bate_stop:
                    preco_saida = stop_price
                    resultado = 0
                    motivo_saida = "stop_e_take_mesmo_candle"
                    break
                elif bate_stop:
                    preco_saida = stop_price
                    resultado = 0
                    motivo_saida = "stop"
                    break
                elif bate_take:
                    preco_saida = take_price
                    resultado = 1
                    motivo_saida = "take"
                    break

        if resultado is None:
            continue

        pnl = (preco_saida - entrada) if direcao == 1 else (entrada - preco_saida)

        registros.append({
            "datetime_entrada": row["datetime"],
            "tipo": "BUY" if direcao == 1 else "SELL",
            "resultado": int(resultado),
            "pnl_pontos": float(pnl),
            "motivo_saida": motivo_saida,

            # parâmetros
            "ema_p": ema_p,
            "bias_p": bias_p,
            "k_compra": k_compra,
            "k_venda": k_venda,
            "bias_compra": bias_compra,
            "bias_venda": bias_venda,
            "take_pontos": take_pontos,
            "stop_pontos": stop_pontos,
            "hora_ini": hora_ini,
            "hora_fim": hora_fim,
            "usar_cruzamento_obrigatorio": usar_cruzamento_obrigatorio,
            "usar_retorno_media": usar_retorno_media,

            # contexto
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "emaX": row["emaX"],
            "emaSlope": row["emaSlope"],
            "biasX": row["biasX"],
            "k": row["k"],
            "d": row["d"],
            "kd_diff": row["kd_diff"],
            "rsi14": row["rsi14"],
            "atr14": row["atr14"],
            "range_candle": row["range_candle"],
            "body": row["body"],
            "close_pos": row["close_pos"],
            "dist_high_low": row["dist_high_low"],
            "ret_1": row["ret_1"],
            "ret_2": row["ret_2"],
            "ret_3": row["ret_3"],
            "dist_ema": row["dist_ema"],
            "hora": row["hora"],
            "minuto": row["minuto"],
            "dia_semana": row["dia_semana"]
        })

    return registros

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    inicio = time.time()

    base = preparar_base()

    combinacoes = list(product(
        EMA_PERIODOS,
        BIAS_PERIODOS,
        K_LIMITE_COMPRA_LIST,
        K_LIMITE_VENDA_LIST,
        BIAS_LIMITE_COMPRA_LIST,
        BIAS_LIMITE_VENDA_LIST,
        TAKE_LIST,
        STOP_LIST,
        HORA_INICIO_LIST,
        HORA_FIM_LIST,
        USAR_CRUZAMENTO_OBRIGATORIO_LIST,
        USAR_RETORNO_MEDIA_LIST
    ))

    print("Total de combinações:", len(combinacoes))

    todos_registros = []

    total_lotes = math.ceil(len(combinacoes) / LOTE_COMBINACOES)

    for idx_lote in range(total_lotes):
        ini = idx_lote * LOTE_COMBINACOES
        fim = min((idx_lote + 1) * LOTE_COMBINACOES, len(combinacoes))
        lote = combinacoes[ini:fim]

        print(f"\nProcessando lote {idx_lote + 1}/{total_lotes} | combinações {ini} até {fim - 1}")

        resultados_lote = Parallel(n_jobs=N_JOBS, backend="loky")(
            delayed(processar_combinacao)(combo, base) for combo in lote
        )

        for item in resultados_lote:
            if item:
                todos_registros.extend(item)

        print("Sinais acumulados:", len(todos_registros))

    dataset = pd.DataFrame(todos_registros)

    print("\nQuantidade total de sinais gerados:", len(dataset))

    if len(dataset) == 0:
        print("Nenhum sinal gerado.")
        raise SystemExit

    dataset = dataset.sort_values("datetime_entrada").reset_index(drop=True)
    dataset.to_csv("dataset_ml_padrao_video_robusto.csv", index=False)
    print("Arquivo salvo: dataset_ml_padrao_video_robusto.csv")

    dataset["tipo_num"] = dataset["tipo"].map({"BUY": 1, "SELL": -1})

    features = [
        "tipo_num",
        "ema_p", "bias_p",
        "k_compra", "k_venda",
        "bias_compra", "bias_venda",
        "take_pontos", "stop_pontos",
        "hora_ini", "hora_fim",
        "usar_cruzamento_obrigatorio",
        "usar_retorno_media",
        "open", "high", "low", "close",
        "emaX", "emaSlope", "biasX",
        "k", "d", "kd_diff",
        "rsi14", "atr14",
        "range_candle", "body", "close_pos",
        "dist_high_low",
        "ret_1", "ret_2", "ret_3",
        "dist_ema",
        "hora", "minuto", "dia_semana"
    ]

    X = dataset[features].copy()
    y = dataset["resultado"].copy()

    divisao = int(len(dataset) * 0.7)

    X_treino = X.iloc[:divisao]
    X_teste = X.iloc[divisao:]

    y_treino = y.iloc[:divisao]
    y_teste = y.iloc[divisao:]

    print("\nTreinando modelo...")
    modelo = RandomForestClassifier(
        n_estimators=RF_N_ESTIMATORS,
        max_depth=RF_MAX_DEPTH,
        min_samples_leaf=RF_MIN_SAMPLES_LEAF,
        random_state=RF_RANDOM_STATE,
        n_jobs=N_JOBS
    )

    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    probs = modelo.predict_proba(X_teste)[:, 1]

    acc = accuracy_score(y_teste, previsoes)

    print("\nAcurácia do modelo:", acc)
    print("\nMatriz de confusão:")
    print(confusion_matrix(y_teste, previsoes))
    print("\nRelatório:")
    print(classification_report(y_teste, previsoes, zero_division=0))

    teste = dataset.iloc[divisao:].copy()
    teste["previsto"] = previsoes
    teste["prob_gain"] = probs

    ranking = (
        teste.groupby([
            "tipo", "ema_p", "bias_p", "k_compra", "k_venda",
            "bias_compra", "bias_venda",
            "take_pontos", "stop_pontos",
            "hora_ini", "hora_fim",
            "usar_cruzamento_obrigatorio",
            "usar_retorno_media"
        ])
        .agg(
            sinais=("resultado", "count"),
            wins=("resultado", "sum"),
            lucro_total=("pnl_pontos", "sum"),
            lucro_medio=("pnl_pontos", "mean"),
            prob_media=("prob_gain", "mean")
        )
        .reset_index()
    )

    ranking["losses"] = ranking["sinais"] - ranking["wins"]
    ranking["taxa_acerto"] = ranking["wins"] / ranking["sinais"]

    ranking = ranking[ranking["sinais"] >= MIN_SINAIS_RANKING].copy()

    ranking = ranking.sort_values(
        ["lucro_total", "taxa_acerto", "prob_media", "lucro_medio"],
        ascending=False
    ).reset_index(drop=True)

    ranking.to_csv("ranking_padroes_video_ml_robusto.csv", index=False)

    print("\nTop 30 padrões mais próximos / melhores:")
    print(ranking.head(30))

    importancias = pd.DataFrame({
        "feature": features,
        "importancia": modelo.feature_importances_
    }).sort_values("importancia", ascending=False)

    importancias.to_csv("importancia_features_video_ml_robusto.csv", index=False)

    print("\nImportância das features:")
    print(importancias)

    fim = time.time()
    print(f"\nTempo total (segundos): {round(fim - inicio, 2)}")

    print("\nArquivos salvos:")
    print("- dataset_ml_padrao_video_robusto.csv")
    print("- ranking_padroes_video_ml_robusto.csv")
    print("- importancia_features_video_ml_robusto.csv")