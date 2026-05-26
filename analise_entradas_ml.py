
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analisa entradas BUY/SELL sobre uma série OHLCV, testa vários indicadores
técnicos e roda ML exploratório.

Uso:
    python analise_entradas_ml.py --ohlc "NQ_15min.csv" --entradas "entradas.csv" --saida "./saida"

Formato esperado do arquivo OHLC:
    datetime,open,high,low,close,volume
    2025-10-28 10:15:00,....
    2025-10-28 10:30:00,....

Formato esperado do arquivo de entradas:
    date,time,side
    2025-10-28,10:30,SELL
    2025-10-28,12:30,BUY

Observações:
- O script casa cada entrada com o candle de mesmo timestamp.
- Se não existir candle exato, ele procura o candle mais próximo dentro da tolerância.
- Ele cria:
    1) dataset completo com indicadores
    2) amostra das entradas
    3) ranking por efeito estatístico
    4) importâncias do RandomForest
    5) matriz de confusão e relatório
"""

from __future__ import annotations
import argparse
from pathlib import Path
import json
import math
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# =========================
# INDICADORES
# =========================

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def stochastic_k(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    lowest = low.rolling(n).min()
    highest = high.rolling(n).max()
    return 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)

def stochastic_d(k: pd.Series, n: int = 3) -> pd.Series:
    return k.rolling(n).mean()

def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    lowest = low.rolling(n).min()
    highest = high.rolling(n).max()
    return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)

def cci(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    ma = tp.rolling(n).mean()
    md = (tp - ma).abs().rolling(n).mean()
    return (tp - ma) / (0.015 * md.replace(0, np.nan))

def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def roc(close: pd.Series, n: int = 5) -> pd.Series:
    return (close / close.shift(n) - 1.0) * 100

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close: pd.Series, n: int = 20, mult: float = 2.0):
    basis = sma(close, n)
    std = close.rolling(n).std()
    upper = basis + mult * std
    lower = basis - mult * std
    z = (close - basis) / std.replace(0, np.nan)
    width = (upper - lower) / basis.replace(0, np.nan)
    return basis, upper, lower, z, width

def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = true_range(high, low, close)
    atr_n = tr.ewm(alpha=1/n, adjust=False).mean()

    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(alpha=1/n, adjust=False).mean() / atr_n.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(alpha=1/n, adjust=False).mean() / atr_n.replace(0, np.nan)

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_line = dx.ewm(alpha=1/n, adjust=False).mean()

    return plus_di, minus_di, adx_line

def slope(series: pd.Series, n: int = 5) -> pd.Series:
    def _slope(x):
        y = np.array(x, dtype=float)
        idx = np.arange(len(y), dtype=float)
        if np.isnan(y).any():
            return np.nan
        x_mean = idx.mean()
        y_mean = y.mean()
        denom = ((idx - x_mean) ** 2).sum()
        if denom == 0:
            return np.nan
        beta = ((idx - x_mean) * (y - y_mean)).sum() / denom
        return beta
    return series.rolling(n).apply(_slope, raw=False)

def run_direction(close: pd.Series, n: int = 3) -> pd.Series:
    ret = np.sign(close.diff())
    return ret.rolling(n).sum()

def distance_to_extremes(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 10):
    recent_high = high.rolling(n).max()
    recent_low = low.rolling(n).min()
    dist_top = recent_high - close
    dist_bottom = close - recent_low
    pos_in_range = (close - recent_low) / (recent_high - recent_low).replace(0, np.nan)
    return dist_top, dist_bottom, pos_in_range

# =========================
# PREPARAÇÃO
# =========================

def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def carregar_ohlc(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    df = normalizar_colunas(df)

    rename_map = {}
    for c in df.columns:
        if c in ["date", "data"]:
            rename_map[c] = "date"
        elif c in ["time", "hora"]:
            rename_map[c] = "time"
        elif c in ["datetime", "timestamp", "date_time", "datahora", "data_hora"]:
            rename_map[c] = "datetime"
        elif c in ["open", "abertura"]:
            rename_map[c] = "open"
        elif c in ["high", "max", "alta"]:
            rename_map[c] = "high"
        elif c in ["low", "min", "baixa"]:
            rename_map[c] = "low"
        elif c in ["close", "fechamento", "last"]:
            rename_map[c] = "close"
        elif c in ["volume", "vol"]:
            rename_map[c] = "volume"
    df = df.rename(columns=rename_map)

    if "datetime" not in df.columns:
        if "date" in df.columns and "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
        elif "date" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"])
        else:
            raise ValueError("Não encontrei coluna datetime nem combinação date + time no arquivo OHLC.")

    required = ["datetime", "open", "high", "low", "close"]
    faltando = [c for c in required if c not in df.columns]
    if faltando:
        raise ValueError(f"Faltam colunas no OHLC: {faltando}")

    if "volume" not in df.columns:
        df["volume"] = np.nan

    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    return df[["datetime", "open", "high", "low", "close", "volume"]]

def carregar_entradas(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    df = normalizar_colunas(df)
    rename_map = {}
    for c in df.columns:
        if c in ["date", "data"]:
            rename_map[c] = "date"
        elif c in ["time", "hora"]:
            rename_map[c] = "time"
        elif c in ["side", "tipo", "acao", "action", "direcao", "lado"]:
            rename_map[c] = "side"
        elif c in ["datetime", "timestamp", "datahora", "data_hora"]:
            rename_map[c] = "datetime"
    df = df.rename(columns=rename_map)

    if "datetime" not in df.columns:
        if "date" in df.columns and "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
        else:
            raise ValueError("Arquivo de entradas precisa ter datetime ou date + time.")

    if "side" not in df.columns:
        raise ValueError("Arquivo de entradas precisa ter coluna side com BUY/SELL.")

    df["datetime"] = pd.to_datetime(df["datetime"])
    df["side"] = df["side"].astype(str).str.upper().str.strip()
    df = df[df["side"].isin(["BUY", "SELL"])].copy()
    df = df.sort_values("datetime").reset_index(drop=True)
    return df[["datetime", "side"]]

def inferir_timeframe_minutos(ohlc: pd.DataFrame) -> int:
    diffs = ohlc["datetime"].diff().dropna().dt.total_seconds() / 60
    if len(diffs) == 0:
        return 1
    return int(round(diffs.mode().iloc[0]))

def casar_entradas_com_candles(ohlc: pd.DataFrame, entradas: pd.DataFrame, tolerancia_min: int | None = None):
    tf = inferir_timeframe_minutos(ohlc)
    if tolerancia_min is None:
        tolerancia_min = tf // 2 if tf > 1 else 1
        tolerancia_min = max(tolerancia_min, 1)

    base = ohlc.copy().sort_values("datetime")
    ent = entradas.copy().sort_values("datetime")

    merged = pd.merge_asof(
        ent,
        base,
        on="datetime",
        direction="nearest",
        tolerance=pd.Timedelta(minutes=tolerancia_min)
    )

    merged["matched"] = ~merged["close"].isna()
    return merged, tf, tolerancia_min

def criar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # retornos básicos
    out["ret_1"] = out["close"].pct_change() * 100
    out["ret_2"] = out["close"].pct_change(2) * 100
    out["ret_3"] = out["close"].pct_change(3) * 100
    out["ret_5"] = out["close"].pct_change(5) * 100

    # médias
    for n in [5, 8, 9, 13, 17, 21, 34, 50, 100, 200]:
        out[f"sma_{n}"] = sma(out["close"], n)
        out[f"ema_{n}"] = ema(out["close"], n)
        out[f"dist_sma_{n}"] = out["close"] - out[f"sma_{n}"]
        out[f"dist_ema_{n}"] = out["close"] - out[f"ema_{n}"]
        out[f"slope_ema_{n}_5"] = slope(out[f"ema_{n}"], 5)

    # osciladores
    for n in [7, 9, 14, 21]:
        out[f"rsi_{n}"] = rsi(out["close"], n)
        out[f"roc_{n}"] = roc(out["close"], n)

    k14 = stochastic_k(out["high"], out["low"], out["close"], 14)
    out["stoch_k_14"] = k14
    out["stoch_d_3"] = stochastic_d(k14, 3)
    out["stoch_cross"] = np.sign(out["stoch_k_14"] - out["stoch_d_3"])

    out["wpr_14"] = williams_r(out["high"], out["low"], out["close"], 14)
    out["cci_20"] = cci(out["high"], out["low"], out["close"], 20)

    out["atr_14"] = atr(out["high"], out["low"], out["close"], 14)
    out["atr_pct"] = out["atr_14"] / out["close"] * 100

    macd_line, signal_line, hist = macd(out["close"])
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = hist

    bb_basis, bb_up, bb_low, bb_z, bb_width = bollinger(out["close"], 20, 2.0)
    out["bb_basis"] = bb_basis
    out["bb_upper"] = bb_up
    out["bb_lower"] = bb_low
    out["bb_z"] = bb_z
    out["bb_width"] = bb_width
    out["bb_pos"] = (out["close"] - out["bb_lower"]) / (out["bb_upper"] - out["bb_lower"]).replace(0, np.nan)

    plus_di, minus_di, adx_line = adx(out["high"], out["low"], out["close"], 14)
    out["plus_di"] = plus_di
    out["minus_di"] = minus_di
    out["adx_14"] = adx_line
    out["di_spread"] = plus_di - minus_di

    # contexto de candle
    out["body"] = (out["close"] - out["open"]).abs()
    out["range"] = out["high"] - out["low"]
    out["body_range"] = out["body"] / out["range"].replace(0, np.nan)
    out["upper_wick"] = out["high"] - out[["open", "close"]].max(axis=1)
    out["lower_wick"] = out[["open", "close"]].min(axis=1) - out["low"]
    out["close_pos_bar"] = (out["close"] - out["low"]) / (out["high"] - out["low"]).replace(0, np.nan)

    # extremos recentes
    for n in [5, 10, 20]:
        dist_top, dist_bottom, pos_range = distance_to_extremes(out["close"], out["high"], out["low"], n)
        out[f"dist_top_{n}"] = dist_top
        out[f"dist_bottom_{n}"] = dist_bottom
        out[f"pos_range_{n}"] = pos_range

    # runs
    for n in [3, 5, 8]:
        out[f"run_{n}"] = run_direction(out["close"], n)

    # calendário
    out["hour"] = out["datetime"].dt.hour
    out["minute"] = out["datetime"].dt.minute
    out["dow"] = out["datetime"].dt.dayofweek
    out["dom"] = out["datetime"].dt.day

    # cíclicos
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["minute_sin"] = np.sin(2 * np.pi * out["minute"] / 60)
    out["minute_cos"] = np.cos(2 * np.pi * out["minute"] / 60)

    return out

def relatorio_estatistico(amostra: pd.DataFrame, side_col: str = "side"):
    features = [c for c in amostra.columns if c not in ["datetime", side_col] and pd.api.types.is_numeric_dtype(amostra[c])]
    linhas = []
    buy = amostra[amostra[side_col] == "BUY"]
    sell = amostra[amostra[side_col] == "SELL"]

    for c in features:
        b = buy[c].dropna()
        s = sell[c].dropna()
        if len(b) < 3 or len(s) < 3:
            continue
        mean_buy = b.mean()
        mean_sell = s.mean()
        std_all = amostra[c].dropna().std()
        effect = np.nan if pd.isna(std_all) or std_all == 0 else (mean_buy - mean_sell) / std_all
        med_buy = b.median()
        med_sell = s.median()
        linhas.append({
            "feature": c,
            "mean_buy": mean_buy,
            "mean_sell": mean_sell,
            "median_buy": med_buy,
            "median_sell": med_sell,
            "effect_size_std": effect,
            "abs_effect": abs(effect) if pd.notna(effect) else np.nan,
            "n_buy": len(b),
            "n_sell": len(s),
        })
    out = pd.DataFrame(linhas).sort_values("abs_effect", ascending=False)
    return out

def rodar_ml(amostra: pd.DataFrame, pasta_saida: Path):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline

    df = amostra.copy()
    y = df["side"].map({"BUY": 1, "SELL": 0})

    feature_cols = [
        c for c in df.columns
        if c not in ["datetime", "side"] and pd.api.types.is_numeric_dtype(df[c])
    ]

    X = df[feature_cols].copy()

    if len(df) < 12 or y.nunique() < 2:
        raise ValueError("Amostra insuficiente para ML. Tente usar mais entradas.")

    test_size = 0.35 if len(df) >= 20 else 0.25
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight="balanced"
        ))
    ])

    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, pred)
    cm = confusion_matrix(y_test, pred)
    report = classification_report(y_test, pred, output_dict=True)

    rf = model.named_steps["rf"]
    importancias = pd.DataFrame({
        "feature": feature_cols,
        "importance": rf.feature_importances_
    }).sort_values("importance", ascending=False)

    metricas = {
        "accuracy": float(acc),
        "n_total": int(len(df)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "class_map": {"SELL": 0, "BUY": 1},
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }

    importancias.to_csv(pasta_saida / "04_importancias_ml.csv", index=False)
    pd.DataFrame(cm, index=["real_sell", "real_buy"], columns=["pred_sell", "pred_buy"]).to_csv(
        pasta_saida / "05_matriz_confusao.csv"
    )
    with open(pasta_saida / "06_metricas_ml.json", "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)

    return metricas, importancias

def salvar_resumo_txt(pasta_saida: Path, metricas: dict | None, ranking: pd.DataFrame, amostra: pd.DataFrame):
    buy = amostra[amostra["side"] == "BUY"]
    sell = amostra[amostra["side"] == "SELL"]

    top = ranking.head(20)

    linhas = []
    linhas.append("RESUMO DA ANÁLISE\n")
    linhas.append(f"Total de entradas: {len(amostra)}")
    linhas.append(f"BUY: {len(buy)}")
    linhas.append(f"SELL: {len(sell)}\n")

    linhas.append("Top variáveis por diferença BUY x SELL:")
    for _, r in top.iterrows():
        linhas.append(
            f"- {r['feature']}: median_buy={r['median_buy']:.4f} | "
            f"median_sell={r['median_sell']:.4f} | effect={r['effect_size_std']:.4f}"
        )

    if metricas:
        linhas.append("\nMétricas do ML:")
        linhas.append(f"- accuracy: {metricas['accuracy']:.4f}")
        linhas.append(f"- treino: {metricas['n_train']}")
        linhas.append(f"- teste: {metricas['n_test']}")
        linhas.append(f"- matriz confusão: {metricas['confusion_matrix']}")

    with open(pasta_saida / "07_resumo.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ohlc", required=True, help="Arquivo OHLC CSV/XLSX")
    parser.add_argument("--entradas", required=True, help="Arquivo de entradas CSV/XLSX")
    parser.add_argument("--saida", default="saida_analise_ml", help="Pasta de saída")
    parser.add_argument("--tolerancia-min", type=int, default=None, help="Tolerância em minutos para casar entrada e candle")
    args = parser.parse_args()

    ohlc_path = Path(args.ohlc)
    entradas_path = Path(args.entradas)
    pasta_saida = Path(args.saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    ohlc = carregar_ohlc(ohlc_path)
    entradas = carregar_entradas(entradas_path)

    feats = criar_features(ohlc)
    merged, tf, tolerancia = casar_entradas_com_candles(feats, entradas, args.tolerancia_min)
    merged["source_timeframe_min"] = tf
    merged["match_tolerance_min"] = tolerancia

    merged.to_csv(pasta_saida / "01_entradas_casadas.csv", index=False)

    amostra = merged[merged["matched"]].copy()
    if len(amostra) == 0:
        raise ValueError("Nenhuma entrada foi casada com candles. Revise timezone, horários e timeframe.")

    ranking = relatorio_estatistico(amostra)
    ranking.to_csv(pasta_saida / "02_ranking_indicadores.csv", index=False)

    dataset = feats.copy()
    dataset.to_csv(pasta_saida / "03_dataset_completo_indicadores.csv", index=False)

    metricas = None
    try:
        metricas, _ = rodar_ml(amostra, pasta_saida)
    except Exception as e:
        with open(pasta_saida / "06_metricas_ml.json", "w", encoding="utf-8") as f:
            json.dump({"erro_ml": str(e)}, f, ensure_ascii=False, indent=2)

    salvar_resumo_txt(pasta_saida, metricas, ranking, amostra)

    print("Análise concluída.")
    print(f"Entradas totais: {len(entradas)}")
    print(f"Entradas casadas: {len(amostra)}")
    print(f"Timeframe inferido: {tf} min")
    print(f"Tolerância usada: {tolerancia} min")
    print(f"Saída em: {pasta_saida.resolve()}")

if __name__ == "__main__":
    main()
