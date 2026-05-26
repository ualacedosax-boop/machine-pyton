#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
nq_video_strategy_ml.py

Objetivo
--------
1) Carregar um CSV de OHLC do NQ/MNQ em 15 minutos.
2) Construir várias estratégias candidatas inspiradas no vídeo.
3) Rodar backtest vetorizado e comparar resultados.
4) Treinar modelos de ML para filtrar entradas.
5) Cruzar frames/imagens do vídeo com os dados de preço via matching visual
   aproximado de janelas do gráfico.

Observações
-----------
- O script aceita CSV com colunas: time, open, high, low, close.
- volume é opcional.
- O matching das imagens é aproximado. Sem timestamp no vídeo, ele encontra
  trechos do preço que mais se parecem com os frames fornecidos.
- O ML não "adivinha" a estratégia; ele atua como filtro probabilístico sobre
  sinais das estratégias candidatas.

Exemplo de uso
--------------
python nq_video_strategy_ml.py --csv "CME_MINI_MNQ1!, 15.csv"

Com imagens:
python nq_video_strategy_ml.py \
  --csv "CME_MINI_MNQ1!, 15.csv" \
  --frames "/caminho/frame1.jpg" "/caminho/frame2.jpg"

Com saída customizada:
python nq_video_strategy_ml.py \
  --csv "CME_MINI_MNQ1!, 15.csv" \
  --outdir "./saida_ml"

Dependências
------------
pip install pandas numpy scikit-learn matplotlib pillow
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# =========================
# Utilidades numéricas
# =========================

def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    avg_up = up.ewm(alpha=1 / period, adjust=False).mean()
    avg_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def stoch_rsi(close: pd.Series, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Tuple[pd.Series, pd.Series]:
    r = rsi(close, period=period)
    min_r = r.rolling(period).min()
    max_r = r.rolling(period).max()
    stoch = 100 * (r - min_r) / (max_r - min_r).replace(0, np.nan)
    k = stoch.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    return k, d


def bollinger(close: pd.Series, period: int = 20, mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    basis = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = basis + mult * std
    lower = basis - mult * std
    return basis, upper, lower


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    line = fast_ema - slow_ema
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    _atr = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upperband = hl2 + multiplier * _atr
    lowerband = hl2 - multiplier * _atr

    final_upper = upperband.copy()
    final_lower = lowerband.copy()
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=float)

    for i in range(1, len(df)):
        if upperband.iloc[i] < final_upper.iloc[i - 1] or df["close"].iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = upperband.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if lowerband.iloc[i] > final_lower.iloc[i - 1] or df["close"].iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = lowerband.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if pd.isna(st.iloc[i - 1]):
            if df["close"].iloc[i] <= final_upper.iloc[i]:
                st.iloc[i] = final_upper.iloc[i]
                direction.iloc[i] = -1
            else:
                st.iloc[i] = final_lower.iloc[i]
                direction.iloc[i] = 1
        else:
            if st.iloc[i - 1] == final_upper.iloc[i - 1]:
                if df["close"].iloc[i] <= final_upper.iloc[i]:
                    st.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    st.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
            else:
                if df["close"].iloc[i] >= final_lower.iloc[i]:
                    st.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    st.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1

    direction.iloc[0] = np.nan
    return direction.ffill()


def pivot_low(series: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    values = series.values
    out = np.zeros(len(series), dtype=bool)
    for i in range(left, len(series) - right):
        center = values[i]
        if np.all(center < values[i - left:i]) and np.all(center <= values[i + 1:i + right + 1]):
            out[i] = True
    return pd.Series(out, index=series.index)


def pivot_high(series: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    values = series.values
    out = np.zeros(len(series), dtype=bool)
    for i in range(left, len(series) - right):
        center = values[i]
        if np.all(center > values[i - left:i]) and np.all(center >= values[i + 1:i + right + 1]):
            out[i] = True
    return pd.Series(out, index=series.index)


# =========================
# Preparação dos dados
# =========================

def load_ohlc(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cols = {c.lower().strip(): c for c in df.columns}
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"CSV sem colunas obrigatórias: {missing}. Colunas encontradas: {list(df.columns)}")

    out = pd.DataFrame({
        "time": pd.to_datetime(df[cols["time"]], errors="coerce"),
        "open": pd.to_numeric(df[cols["open"]], errors="coerce"),
        "high": pd.to_numeric(df[cols["high"]], errors="coerce"),
        "low": pd.to_numeric(df[cols["low"]], errors="coerce"),
        "close": pd.to_numeric(df[cols["close"]], errors="coerce"),
    })

    if "volume" in cols:
        out["volume"] = pd.to_numeric(df[cols["volume"]], errors="coerce")
    else:
        out["volume"] = np.nan

    out = out.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)
    return out


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret1"] = out["close"].pct_change()
    out["ret3"] = out["close"].pct_change(3)
    out["ret6"] = out["close"].pct_change(6)
    out["ret12"] = out["close"].pct_change(12)

    out["ema9"] = ema(out["close"], 9)
    out["ema21"] = ema(out["close"], 21)
    out["ema50"] = ema(out["close"], 50)

    out["rsi14"] = rsi(out["close"], 14)
    out["atr14"] = atr(out, 14)
    out["atr_norm"] = out["atr14"] / out["close"]

    out["k"], out["d"] = stoch_rsi(out["close"], 14, 3, 3)
    out["bb_basis"], out["bb_upper"], out["bb_lower"] = bollinger(out["close"], 20, 2.0)
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_basis"]
    out["bb_pos"] = (out["close"] - out["bb_lower"]) / (out["bb_upper"] - out["bb_lower"]).replace(0, np.nan)

    out["macd"], out["macd_signal"], out["macd_hist"] = macd(out["close"])
    out["supertrend_dir"] = supertrend(out, 10, 3.0)

    out["body"] = (out["close"] - out["open"]).abs()
    out["range"] = out["high"] - out["low"]
    out["body_ratio"] = out["body"] / out["range"].replace(0, np.nan)

    out["upper_wick"] = out["high"] - out[["open", "close"]].max(axis=1)
    out["lower_wick"] = out[["open", "close"]].min(axis=1) - out["low"]
    out["upper_wick_ratio"] = out["upper_wick"] / out["range"].replace(0, np.nan)
    out["lower_wick_ratio"] = out["lower_wick"] / out["range"].replace(0, np.nan)

    out["pivot_low"] = pivot_low(out["low"], 2, 2).astype(int)
    out["pivot_high"] = pivot_high(out["high"], 2, 2).astype(int)

    out["hour"] = out["time"].dt.hour
    out["minute"] = out["time"].dt.minute
    out["dow"] = out["time"].dt.dayofweek

    return out


# =========================
# Estratégias candidatas
# =========================

def build_signals(df: pd.DataFrame) -> Dict[str, pd.Series]:
    s = {}

    trend_up = (df["ema9"] > df["ema21"]) & (df["close"] > df["ema9"])
    trend_down = (df["ema9"] < df["ema21"]) & (df["close"] < df["ema9"])

    momentum_up = (df["rsi14"] > 50) & (df["k"] > df["d"])
    momentum_down = (df["rsi14"] < 50) & (df["k"] < df["d"])

    # A) EMA + RSI + pivô
    buy_a = trend_up & momentum_up & (df["pivot_low"].shift(1) == 1) & (df["close"] > df["open"])
    sell_a = trend_down & momentum_down & (df["pivot_high"].shift(1) == 1) & (df["close"] < df["open"])
    s["A_ema_rsi_pivot"] = encode_signal(buy_a, sell_a)

    # B) EMA + StochRSI + ATR + candle forte
    buy_b = trend_up & (df["k"] > df["d"]) & (df["k"].shift(1) <= df["d"].shift(1)) & (df["body_ratio"] > 0.55) & (df["atr_norm"] > df["atr_norm"].rolling(50).median())
    sell_b = trend_down & (df["k"] < df["d"]) & (df["k"].shift(1) >= df["d"].shift(1)) & (df["body_ratio"] > 0.55) & (df["atr_norm"] > df["atr_norm"].rolling(50).median())
    s["B_ema_stoch_atr"] = encode_signal(buy_b, sell_b)

    # C) Supertrend + EMA + pivô
    buy_c = (df["supertrend_dir"] > 0) & (df["ema9"] > df["ema21"]) & (df["pivot_low"].shift(1) == 1) & (df["close"] > df["ema9"])
    sell_c = (df["supertrend_dir"] < 0) & (df["ema9"] < df["ema21"]) & (df["pivot_high"].shift(1) == 1) & (df["close"] < df["ema9"])
    s["C_supertrend_ema_pivot"] = encode_signal(buy_c, sell_c)

    # D) Bollinger reversão curta + momentum
    buy_d = (df["low"] <= df["bb_lower"]) & (df["close"] > df["open"]) & (df["rsi14"] > df["rsi14"].shift(1)) & (df["k"] > df["d"])
    sell_d = (df["high"] >= df["bb_upper"]) & (df["close"] < df["open"]) & (df["rsi14"] < df["rsi14"].shift(1)) & (df["k"] < df["d"])
    s["D_bb_reversal_momentum"] = encode_signal(buy_d, sell_d)

    # E) MACD + RSI + pullback à EMA9
    buy_e = (df["ema9"] > df["ema21"]) & (df["low"] <= df["ema9"]) & (df["close"] > df["ema9"]) & (df["macd_hist"] > 0) & (df["rsi14"] > 52)
    sell_e = (df["ema9"] < df["ema21"]) & (df["high"] >= df["ema9"]) & (df["close"] < df["ema9"]) & (df["macd_hist"] < 0) & (df["rsi14"] < 48)
    s["E_macd_rsi_pullback"] = encode_signal(buy_e, sell_e)

    return s


def encode_signal(buy: pd.Series, sell: pd.Series) -> pd.Series:
    signal = pd.Series(0, index=buy.index, dtype=int)
    signal[buy.fillna(False)] = 1
    signal[sell.fillna(False)] = -1
    return signal


# =========================
# Backtest
# =========================

@dataclass
class BacktestResult:
    name: str
    trades: pd.DataFrame
    summary: Dict[str, float]


def simulate_trades(
    df: pd.DataFrame,
    signal: pd.Series,
    strategy_name: str,
    hold_bars: int = 8,
    stop_atr: float = 1.0,
    take_atr: float = 1.5,
    one_position: bool = True,
) -> BacktestResult:
    rows = []
    position = 0
    entry_idx = None
    entry_price = None
    stop_price = None
    take_price = None

    for i in range(1, len(df) - 1):
        if np.isnan(df["atr14"].iloc[i]):
            continue

        if position == 0:
            sig = int(signal.iloc[i])
            if sig == 1:
                position = 1
                entry_idx = i + 1
                if entry_idx >= len(df):
                    break
                entry_price = df["open"].iloc[entry_idx]
                a = df["atr14"].iloc[i]
                stop_price = entry_price - stop_atr * a
                take_price = entry_price + take_atr * a
                entry_time = df["time"].iloc[entry_idx]
            elif sig == -1:
                position = -1
                entry_idx = i + 1
                if entry_idx >= len(df):
                    break
                entry_price = df["open"].iloc[entry_idx]
                a = df["atr14"].iloc[i]
                stop_price = entry_price + stop_atr * a
                take_price = entry_price - take_atr * a
                entry_time = df["time"].iloc[entry_idx]
        else:
            bars_held = i - entry_idx + 1
            high_i = df["high"].iloc[i]
            low_i = df["low"].iloc[i]
            close_i = df["close"].iloc[i]
            exit_reason = None
            exit_price = None

            if position == 1:
                stop_hit = low_i <= stop_price
                take_hit = high_i >= take_price
                if stop_hit and take_hit:
                    exit_reason = "stop_and_take_same_bar"
                    exit_price = stop_price
                elif stop_hit:
                    exit_reason = "stop"
                    exit_price = stop_price
                elif take_hit:
                    exit_reason = "take"
                    exit_price = take_price
                elif bars_held >= hold_bars or signal.iloc[i] == -1:
                    exit_reason = "time_or_flip"
                    exit_price = close_i
            else:
                stop_hit = high_i >= stop_price
                take_hit = low_i <= take_price
                if stop_hit and take_hit:
                    exit_reason = "stop_and_take_same_bar"
                    exit_price = stop_price
                elif stop_hit:
                    exit_reason = "stop"
                    exit_price = stop_price
                elif take_hit:
                    exit_reason = "take"
                    exit_price = take_price
                elif bars_held >= hold_bars or signal.iloc[i] == 1:
                    exit_reason = "time_or_flip"
                    exit_price = close_i

            if exit_reason is not None:
                pnl = (exit_price - entry_price) * position
                rows.append({
                    "strategy": strategy_name,
                    "side": "BUY" if position == 1 else "SELL",
                    "entry_idx": int(entry_idx),
                    "exit_idx": int(i),
                    "entry_time": entry_time,
                    "exit_time": df["time"].iloc[i],
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "stop_price": float(stop_price),
                    "take_price": float(take_price),
                    "bars_held": int(bars_held),
                    "reason": exit_reason,
                    "pnl_points": float(pnl),
                    "win": int(pnl > 0),
                })
                position = 0
                entry_idx = None
                entry_price = None
                stop_price = None
                take_price = None

    trades = pd.DataFrame(rows)
    summary = summarize_trades(trades)
    return BacktestResult(strategy_name, trades, summary)


def summarize_trades(trades: pd.DataFrame) -> Dict[str, float]:
    if trades.empty:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "net_points": 0.0,
            "avg_points": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_like": 0.0,
        }

    pnl = trades["pnl_points"].astype(float)
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    cum = pnl.cumsum()
    peak = cum.cummax()
    dd = cum - peak
    sharpe_like = pnl.mean() / (pnl.std(ddof=0) + 1e-9) * math.sqrt(max(len(pnl), 1))
    return {
        "trades": int(len(trades)),
        "win_rate": float((pnl > 0).mean()),
        "net_points": float(pnl.sum()),
        "avg_points": float(pnl.mean()),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "max_drawdown": float(dd.min()),
        "sharpe_like": float(sharpe_like),
    }


# =========================
# ML para filtrar sinais
# =========================

FEATURE_COLS = [
    "ret1", "ret3", "ret6", "ret12",
    "ema9", "ema21", "ema50",
    "rsi14", "atr14", "atr_norm",
    "k", "d",
    "bb_width", "bb_pos",
    "macd", "macd_signal", "macd_hist",
    "supertrend_dir",
    "body_ratio", "upper_wick_ratio", "lower_wick_ratio",
    "pivot_low", "pivot_high",
    "hour", "minute", "dow",
]


def build_ml_dataset(df: pd.DataFrame, base_signal: pd.Series, horizon: int = 4, target_atr: float = 1.0) -> pd.DataFrame:
    out = df.copy()
    out["base_signal"] = base_signal

    future_max = out["high"].rolling(horizon).max().shift(-horizon + 1)
    future_min = out["low"].rolling(horizon).min().shift(-horizon + 1)
    move_up = future_max - out["close"]
    move_down = out["close"] - future_min

    # Só avalia barras com sinal.
    mask_buy = out["base_signal"] == 1
    mask_sell = out["base_signal"] == -1

    out["target"] = np.nan
    out.loc[mask_buy, "target"] = (move_up.loc[mask_buy] > target_atr * out.loc[mask_buy, "atr14"]).astype(int)
    out.loc[mask_sell, "target"] = (move_down.loc[mask_sell] > target_atr * out.loc[mask_sell, "atr14"]).astype(int)

    ds = out.loc[out["base_signal"] != 0, FEATURE_COLS + ["base_signal", "target", "time", "close"]].copy()
    ds = ds.dropna()
    return ds


def train_time_series_models(ds: pd.DataFrame) -> Tuple[Dict[str, dict], Optional[pd.Series]]:
    if ds.empty or ds["target"].nunique() < 2:
        return {}, None

    X = ds[FEATURE_COLS + ["base_signal"]]
    y = ds["target"].astype(int)

    models = {
        "logreg": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000))
        ]),
        "rf": RandomForestClassifier(
            n_estimators=250,
            max_depth=8,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        ),
        "gb": GradientBoostingClassifier(
            random_state=42
        ),
    }

    tscv = TimeSeriesSplit(n_splits=5)
    results = {}
    oof_pred = pd.Series(index=ds.index, dtype=float)

    for name, model in models.items():
        fold_metrics = []
        preds = pd.Series(index=ds.index, dtype=float)

        for train_idx, test_idx in tscv.split(X):
            x_train, x_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model.fit(x_train, y_train)
            if hasattr(model, "predict_proba"):
                p = model.predict_proba(x_test)[:, 1]
            else:
                p = model.decision_function(x_test)
                p = (p - p.min()) / (p.max() - p.min() + 1e-9)

            preds.iloc[test_idx] = p
            y_hat = (p >= 0.5).astype(int)

            fold_metrics.append({
                "auc": float(roc_auc_score(y_test, p)) if y_test.nunique() > 1 else np.nan,
                "accuracy": float(accuracy_score(y_test, y_hat)),
                "precision": float(precision_score(y_test, y_hat, zero_division=0)),
                "recall": float(recall_score(y_test, y_hat, zero_division=0)),
            })

        valid = preds.notna()
        if valid.any():
            yv = y.loc[valid]
            pv = preds.loc[valid]
            auc = float(roc_auc_score(yv, pv)) if yv.nunique() > 1 else np.nan
            acc = float(accuracy_score(yv, (pv >= 0.5).astype(int)))
        else:
            auc = np.nan
            acc = np.nan

        results[name] = {
            "folds": fold_metrics,
            "oof_auc": auc,
            "oof_accuracy": acc,
        }

        # guarda o melhor oof por auc
        if oof_pred.isna().all():
            oof_pred = preds
        else:
            prev_auc = roc_auc_score(y.loc[oof_pred.notna()], oof_pred.loc[oof_pred.notna()]) if oof_pred.notna().sum() > 10 and y.loc[oof_pred.notna()].nunique() > 1 else -1
            curr_auc = roc_auc_score(y.loc[preds.notna()], preds.loc[preds.notna()]) if preds.notna().sum() > 10 and y.loc[preds.notna()].nunique() > 1 else -1
            if curr_auc > prev_auc:
                oof_pred = preds

    return results, oof_pred


def apply_ml_filter_to_signal(df: pd.DataFrame, base_signal: pd.Series, ds: pd.DataFrame, proba: pd.Series, threshold: float = 0.55) -> pd.Series:
    filtered = pd.Series(0, index=df.index, dtype=int)
    if proba is None or ds.empty:
        return filtered

    keep_idx = ds.index[proba >= threshold]
    filtered.loc[keep_idx] = ds.loc[keep_idx, "base_signal"].astype(int)
    return filtered


# =========================
# Matching visual dos frames
# =========================

def normalize_window(window: pd.DataFrame, size: int = 96) -> np.ndarray:
    prices = window[["open", "high", "low", "close"]].copy().reset_index(drop=True)
    low = prices["low"].min()
    high = prices["high"].max()
    rng = max(high - low, 1e-9)

    arr = np.zeros((size, size), dtype=np.float32)
    x_positions = np.linspace(2, size - 3, len(prices)).astype(int)

    for x, (_, row) in zip(x_positions, prices.iterrows()):
        o = int((1 - (row["open"] - low) / rng) * (size - 1))
        h = int((1 - (row["high"] - low) / rng) * (size - 1))
        l = int((1 - (row["low"] - low) / rng) * (size - 1))
        c = int((1 - (row["close"] - low) / rng) * (size - 1))

        y1, y2 = sorted([h, l])
        arr[y1:y2 + 1, x] = 0.6

        top, bot = sorted([o, c])
        arr[top:bot + 1, max(0, x - 1):min(size, x + 2)] = 1.0

    return arr


def preprocess_frame_image(image_path: Path, size: int = 96) -> np.ndarray:
    img = Image.open(image_path).convert("L")
    w, h = img.size

    # crop heurístico: região central da tela onde normalmente fica o gráfico
    left = int(w * 0.08)
    right = int(w * 0.92)
    top = int(h * 0.12)
    bottom = int(h * 0.82)
    img = img.crop((left, top, right, bottom)).resize((size, size))
    arr = np.asarray(img).astype(np.float32) / 255.0

    # inverter para deixar candles/linhas mais claras
    arr = 1.0 - arr
    # normalizar
    arr = (arr - arr.mean()) / (arr.std() + 1e-9)
    return arr


def similarity_score(chart_arr: np.ndarray, frame_arr: np.ndarray) -> float:
    ca = (chart_arr - chart_arr.mean()) / (chart_arr.std() + 1e-9)
    fa = (frame_arr - frame_arr.mean()) / (frame_arr.std() + 1e-9)
    return float((ca * fa).mean())


def find_similar_windows(
    df: pd.DataFrame,
    frame_paths: List[Path],
    window_bars: int = 60,
    top_k: int = 5,
) -> Dict[str, List[dict]]:
    result = {}
    prepared_frames = {str(p): preprocess_frame_image(p) for p in frame_paths}

    for p_str, frame_arr in prepared_frames.items():
        matches = []
        for end in range(window_bars, len(df)):
            window = df.iloc[end - window_bars:end]
            chart_arr = normalize_window(window, size=96)
            score = similarity_score(chart_arr, frame_arr)
            matches.append({
                "frame": p_str,
                "start_idx": int(end - window_bars),
                "end_idx": int(end - 1),
                "start_time": str(window["time"].iloc[0]),
                "end_time": str(window["time"].iloc[-1]),
                "score": score,
            })
        best = sorted(matches, key=lambda x: x["score"], reverse=True)[:top_k]
        result[p_str] = best

    return result


# =========================
# Execução principal
# =========================

def run_pipeline(args: argparse.Namespace) -> None:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_ohlc(Path(args.csv))
    df = add_features(df)

    signals = build_signals(df)

    all_summaries = []
    trade_book = []
    ml_reports = {}
    frame_matches = {}

    for name, sig in signals.items():
        bt = simulate_trades(
            df=df,
            signal=sig,
            strategy_name=name,
            hold_bars=args.hold_bars,
            stop_atr=args.stop_atr,
            take_atr=args.take_atr,
        )

        summary = dict(bt.summary)
        summary["strategy"] = name
        summary["mode"] = "raw"
        all_summaries.append(summary)

        if not bt.trades.empty:
            trade_book.append(bt.trades)

        ds = build_ml_dataset(df, sig, horizon=args.ml_horizon, target_atr=args.ml_target_atr)
        ml_stats, oof_pred = train_time_series_models(ds)
        ml_reports[name] = ml_stats

        if oof_pred is not None and not ds.empty:
            filt_sig = apply_ml_filter_to_signal(df, sig, ds, oof_pred, threshold=args.ml_threshold)
            bt_ml = simulate_trades(
                df=df,
                signal=filt_sig,
                strategy_name=name + "_ML",
                hold_bars=args.hold_bars,
                stop_atr=args.stop_atr,
                take_atr=args.take_atr,
            )
            summary_ml = dict(bt_ml.summary)
            summary_ml["strategy"] = name
            summary_ml["mode"] = "ml_filtered"
            all_summaries.append(summary_ml)
            if not bt_ml.trades.empty:
                trade_book.append(bt_ml.trades)

    if args.frames:
        frame_paths = [Path(p) for p in args.frames if Path(p).exists()]
        if frame_paths:
            frame_matches = find_similar_windows(df, frame_paths, window_bars=args.window_bars, top_k=args.top_k)

    summary_df = pd.DataFrame(all_summaries)
    if not summary_df.empty:
        # score composto simples
        summary_df["score"] = (
            summary_df["net_points"].fillna(0) * 1.0
            + summary_df["win_rate"].fillna(0) * 100.0
            + summary_df["profit_factor"].replace(np.inf, 5).fillna(0) * 50.0
            + summary_df["max_drawdown"].fillna(0) * 0.3
        )
        summary_df = summary_df.sort_values(["score", "net_points", "win_rate"], ascending=[False, False, False]).reset_index(drop=True)

    if trade_book:
        trades_df = pd.concat(trade_book, ignore_index=True)
    else:
        trades_df = pd.DataFrame()

    # Salvar saídas
    summary_path = outdir / "strategy_summary.csv"
    trades_path = outdir / "all_trades.csv"
    ml_path = outdir / "ml_report.json"
    frames_path = outdir / "frame_matches.json"

    summary_df.to_csv(summary_path, index=False)
    trades_df.to_csv(trades_path, index=False)
    with open(ml_path, "w", encoding="utf-8") as f:
        json.dump(ml_reports, f, ensure_ascii=False, indent=2, default=str)
    with open(frames_path, "w", encoding="utf-8") as f:
        json.dump(frame_matches, f, ensure_ascii=False, indent=2, default=str)

    # Relatório textual
    report_txt = []
    report_txt.append("=== RESUMO DAS ESTRATÉGIAS ===")
    if summary_df.empty:
        report_txt.append("Nenhum resultado gerado.")
    else:
        report_txt.append(summary_df.head(10).to_string(index=False))

    if frame_matches:
        report_txt.append("\n=== MELHORES MATCHES DOS FRAMES ===")
        for frame, matches in frame_matches.items():
            report_txt.append(f"\nFrame: {frame}")
            for m in matches:
                report_txt.append(
                    f"  score={m['score']:.4f} | {m['start_time']} -> {m['end_time']} | idx {m['start_idx']}:{m['end_idx']}"
                )

    report_path = outdir / "report.txt"
    report_path.write_text("\n".join(report_txt), encoding="utf-8")

    print("Arquivos gerados:")
    print(f"- {summary_path}")
    print(f"- {trades_path}")
    print(f"- {ml_path}")
    print(f"- {frames_path}")
    print(f"- {report_path}")

    if not summary_df.empty:
        print("\nTop 10:")
        print(summary_df.head(10).to_string(index=False))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ML + backtest para estratégias candidatas do NQ/MNQ 15m.")
    p.add_argument("--csv", required=True, help="Caminho do CSV com colunas time/open/high/low/close.")
    p.add_argument("--frames", nargs="*", default=[], help="Lista de frames/imagens do vídeo para cruzamento visual.")
    p.add_argument("--outdir", default="saida_ml_nq", help="Pasta de saída.")
    p.add_argument("--hold-bars", type=int, default=8, help="Máximo de candles em posição.")
    p.add_argument("--stop-atr", type=float, default=1.0, help="Stop em múltiplos do ATR.")
    p.add_argument("--take-atr", type=float, default=1.5, help="Take em múltiplos do ATR.")
    p.add_argument("--ml-horizon", type=int, default=4, help="Horizonte em candles para target do ML.")
    p.add_argument("--ml-target-atr", type=float, default=1.0, help="Movimento alvo em ATR para rotular acerto do ML.")
    p.add_argument("--ml-threshold", type=float, default=0.55, help="Limiar de probabilidade para aceitar sinal.")
    p.add_argument("--window-bars", type=int, default=60, help="Quantidade de candles na janela de match visual.")
    p.add_argument("--top-k", type=int, default=5, help="Top matches por frame.")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)
