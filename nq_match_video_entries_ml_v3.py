#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit


DEFAULT_LABELS = [
    ("2025-10-28", "10:30", "SELL"),
    ("2025-10-28", "12:30", "BUY"),
    ("2025-10-28", "13:30", "SELL"),
    ("2025-10-28", "16:30", "SELL"),
    ("2025-10-28", "17:00", "BUY"),
    ("2025-10-28", "19:15", "SELL"),
    ("2025-10-28", "20:00", "BUY"),
    ("2025-10-28", "21:00", "BUY"),
    ("2025-10-28", "23:15", "SELL"),
    ("2025-10-29", "00:45", "SELL"),
    ("2025-10-29", "01:00", "BUY"),
    ("2025-10-29", "03:30", "SELL"),
    ("2025-10-29", "04:15", "BUY"),
    ("2025-10-29", "05:15", "SELL"),
    ("2025-10-29", "06:45", "BUY"),
    ("2025-10-29", "08:30", "SELL"),
    ("2025-10-29", "09:30", "BUY"),
    ("2025-10-29", "11:00", "SELL"),
    ("2025-10-29", "13:00", "BUY"),
    ("2025-10-29", "15:00", "SELL"),
    ("2025-10-29", "15:50", "BUY"),
    ("2025-10-29", "17:00", "SELL"),
    ("2025-10-29", "19:00", "BUY"),
    ("2025-10-29", "20:30", "BUY"),
    ("2025-10-29", "21:30", "SELL"),
    ("2025-10-29", "22:00", "BUY"),
    ("2025-10-30", "10:30", "BUY"),
    ("2025-10-30", "11:00", "SELL"),
    ("2025-10-30", "12:45", "BUY"),
    ("2025-10-30", "13:15", "SELL"),
    ("2025-10-30", "14:00", "BUY"),
    ("2025-10-30", "14:45", "SELL"),
]


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
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def stoch(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
    ll = low.rolling(period).min()
    hh = high.rolling(period).max()
    return 100 * (close - ll) / (hh - ll).replace(0, np.nan)


def pivot_low(series: pd.Series, left: int, right: int) -> pd.Series:
    arr = series.values
    out = np.zeros(len(arr), dtype=bool)
    for i in range(left, len(arr) - right):
        c = arr[i]
        if np.all(c < arr[i - left : i]) and np.all(c <= arr[i + 1 : i + 1 + right]):
            out[i] = True
    return pd.Series(out, index=series.index)


def pivot_high(series: pd.Series, left: int, right: int) -> pd.Series:
    arr = series.values
    out = np.zeros(len(arr), dtype=bool)
    for i in range(left, len(arr) - right):
        c = arr[i]
        if np.all(c > arr[i - left : i]) and np.all(c >= arr[i + 1 : i + 1 + right]):
            out[i] = True
    return pd.Series(out, index=series.index)


def load_ohlc(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cols = {c.lower().strip(): c for c in df.columns}
    req = ["time", "open", "high", "low", "close"]
    missing = [c for c in req if c not in cols]
    if missing:
        raise ValueError(f"CSV sem colunas obrigatórias: {missing}. Colunas encontradas: {list(df.columns)}")

    parsed_time = pd.to_datetime(df[cols["time"]], errors="coerce")
    try:
        if getattr(parsed_time.dt, "tz", None) is not None:
            parsed_time = parsed_time.dt.tz_localize(None)
    except Exception:
        pass
    out = pd.DataFrame(
        {
            "time": parsed_time,
            "open": pd.to_numeric(df[cols["open"]], errors="coerce"),
            "high": pd.to_numeric(df[cols["high"]], errors="coerce"),
            "low": pd.to_numeric(df[cols["low"]], errors="coerce"),
            "close": pd.to_numeric(df[cols["close"]], errors="coerce"),
        }
    )
    out = out.dropna().sort_values("time").reset_index(drop=True)
    return out


def load_labels(labels_path: Optional[Path]) -> pd.DataFrame:
    if labels_path is None:
        labels = pd.DataFrame(DEFAULT_LABELS, columns=["date", "time", "side"])
    else:
        labels = pd.read_csv(labels_path)
        labels.columns = [c.lower().strip() for c in labels.columns]
        required = {"date", "time", "side"}
        if not required.issubset(labels.columns):
            raise ValueError(f"Arquivo de labels precisa ter colunas {required}")
    labels["dt"] = pd.to_datetime(labels["date"].astype(str) + " " + labels["time"].astype(str), errors="coerce")
    try:
        if getattr(labels["dt"].dt, "tz", None) is not None:
            labels["dt"] = labels["dt"].dt.tz_localize(None)
    except Exception:
        pass
    labels["side"] = labels["side"].str.upper().str.strip()
    labels = labels.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)
    return labels[["dt", "side"]]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["ema9"] = ema(x["close"], 9)
    x["ema21"] = ema(x["close"], 21)
    x["rsi14"] = rsi(x["close"], 14)
    x["atr14"] = atr(x, 14)
    x["stoch14"] = stoch(x["close"], x["high"], x["low"], 14)
    x["k"] = x["stoch14"].rolling(3).mean()
    x["d"] = x["k"].rolling(3).mean()
    x["range"] = (x["high"] - x["low"]).replace(0, np.nan)
    x["body"] = (x["close"] - x["open"]).abs()
    x["body_ratio"] = x["body"] / x["range"]
    x["upper_wick"] = x["high"] - x[["open", "close"]].max(axis=1)
    x["lower_wick"] = x[["open", "close"]].min(axis=1) - x["low"]
    x["upper_wick_ratio"] = x["upper_wick"] / x["range"]
    x["lower_wick_ratio"] = x["lower_wick"] / x["range"]
    x["ret1"] = x["close"].pct_change()
    x["ret3"] = x["close"].pct_change(3)
    x["hour"] = x["time"].dt.hour
    x["minute"] = x["time"].dt.minute
    return x


def generate_candidate_signals(
    df: pd.DataFrame,
    pivot_left: int,
    pivot_right: int,
    rsi_buy_max: float,
    rsi_sell_min: float,
    min_body: float,
    use_stoch: bool,
    min_wick: float,
    min_atr_distance: float,
    min_gap_bars: int,
) -> pd.DataFrame:
    x = df.copy()

    pl = pivot_low(x["low"], pivot_left, pivot_right)
    ph = pivot_high(x["high"], pivot_left, pivot_right)

    pivot_low_conf = pl.shift(pivot_right).fillna(False)
    pivot_high_conf = ph.shift(pivot_right).fillna(False)

    pivot_low_price = x["low"].shift(pivot_right)
    pivot_high_price = x["high"].shift(pivot_right)

    bull_reaction = (
        (x["close"] > x["open"])
        & (x["close"] > x["close"].shift(1))
        & (x["body_ratio"] >= min_body)
    )

    bear_reaction = (
        (x["close"] < x["open"])
        & (x["close"] < x["close"].shift(1))
        & (x["body_ratio"] >= min_body)
    )

    buy_rsi = (x["rsi14"].shift(pivot_right) < rsi_buy_max) | (x["rsi14"] > x["rsi14"].shift(1))
    sell_rsi = (x["rsi14"].shift(pivot_right) > rsi_sell_min) | (x["rsi14"] < x["rsi14"].shift(1))

    if use_stoch:
        buy_stoch = (x["k"] > x["d"]) & (x["k"].shift(1) <= x["d"].shift(1))
        sell_stoch = (x["k"] < x["d"]) & (x["k"].shift(1) >= x["d"].shift(1))
    else:
        buy_stoch = pd.Series(True, index=x.index)
        sell_stoch = pd.Series(True, index=x.index)

    buy_wick = x["lower_wick_ratio"].fillna(0) >= min_wick
    sell_wick = x["upper_wick_ratio"].fillna(0) >= min_wick

    buy_dist = ((x["close"] - pivot_low_price).abs() >= x["atr14"] * min_atr_distance)
    sell_dist = ((pivot_high_price - x["close"]).abs() >= x["atr14"] * min_atr_distance)

    buy_signal = pivot_low_conf & bull_reaction & buy_rsi & buy_stoch & buy_wick & buy_dist
    sell_signal = pivot_high_conf & bear_reaction & sell_rsi & sell_stoch & sell_wick & sell_dist

    sig = pd.Series("", index=x.index, dtype=object)
    last_buy = -999999
    last_sell = -999999
    for i in range(len(x)):
        if bool(buy_signal.iloc[i]) and i - last_buy > min_gap_bars:
            sig.iloc[i] = "BUY"
            last_buy = i
        if bool(sell_signal.iloc[i]) and i - last_sell > min_gap_bars:
            if sig.iloc[i] == "BUY":
                if x["upper_wick_ratio"].fillna(0).iloc[i] > x["lower_wick_ratio"].fillna(0).iloc[i]:
                    sig.iloc[i] = "SELL"
                    last_sell = i
            else:
                sig.iloc[i] = "SELL"
                last_sell = i

    out = x[
        [
            "time",
            "open",
            "high",
            "low",
            "close",
            "rsi14",
            "atr14",
            "body_ratio",
            "upper_wick_ratio",
            "lower_wick_ratio",
        ]
    ].copy()
    out["pivot_low_confirmed"] = pivot_low_conf.astype(int)
    out["pivot_high_confirmed"] = pivot_high_conf.astype(int)
    out["side"] = sig
    out["is_signal"] = out["side"] != ""
    return out


@dataclass
class ScoreResult:
    score: float
    recall: float
    precision_soft: float
    matched: int
    labels_total: int
    signals_total: int
    duplicate_penalty: float
    matched_rows: pd.DataFrame


def score_signals_vs_labels(signals: pd.DataFrame, labels: pd.DataFrame, tolerance_bars: int = 1, timeframe_minutes: int = 15) -> ScoreResult:
    tol = pd.Timedelta(minutes=tolerance_bars * timeframe_minutes)
    sigs = signals.loc[signals["is_signal"], ["time", "side"]].copy().reset_index(drop=True)
    labs = labels.copy().reset_index(drop=True)

    matched_signal_idx = set()
    rows = []

    for _, lab in labs.iterrows():
        same_side = sigs[sigs["side"] == lab["side"]].copy()
        if same_side.empty:
            rows.append(
                {
                    "label_time": lab["dt"],
                    "label_side": lab["side"],
                    "signal_time": pd.NaT,
                    "signal_side": "",
                    "delta_minutes": np.nan,
                    "matched": 0,
                }
            )
            continue
        same_side["delta"] = (same_side["time"] - lab["dt"]).abs()
        cand = same_side[same_side["delta"] <= tol].sort_values("delta")
        if not cand.empty:
            row = cand.iloc[0]
            matched_signal_idx.add(row.name)
            rows.append(
                {
                    "label_time": lab["dt"],
                    "label_side": lab["side"],
                    "signal_time": row["time"],
                    "signal_side": row["side"],
                    "delta_minutes": row["delta"].total_seconds() / 60.0,
                    "matched": 1,
                }
            )
        else:
            rows.append(
                {
                    "label_time": lab["dt"],
                    "label_side": lab["side"],
                    "signal_time": pd.NaT,
                    "signal_side": "",
                    "delta_minutes": np.nan,
                    "matched": 0,
                }
            )

    matched_df = pd.DataFrame(rows)
    matched = int(matched_df["matched"].sum()) if not matched_df.empty else 0
    labels_total = len(labs)
    signals_total = int(len(sigs))

    recall = matched / labels_total if labels_total else 0.0
    extra_signals = max(signals_total - matched, 0)
    precision_soft = matched / (matched + 0.35 * extra_signals) if (matched + extra_signals) > 0 else 0.0

    duplicate_penalty = 0.0
    if signals_total > 1:
        sigs2 = sigs.sort_values("time").reset_index(drop=True)
        same_side_close = 0
        for i in range(1, len(sigs2)):
            if sigs2.loc[i, "side"] == sigs2.loc[i - 1, "side"]:
                if (sigs2.loc[i, "time"] - sigs2.loc[i - 1, "time"]) <= pd.Timedelta(minutes=30):
                    same_side_close += 1
        duplicate_penalty = same_side_close / max(signals_total, 1)

    score = (0.72 * recall) + (0.28 * precision_soft) - (0.10 * duplicate_penalty)

    return ScoreResult(
        score=float(score),
        recall=float(recall),
        precision_soft=float(precision_soft),
        matched=matched,
        labels_total=labels_total,
        signals_total=signals_total,
        duplicate_penalty=float(duplicate_penalty),
        matched_rows=matched_df,
    )


def grid_search(df: pd.DataFrame, labels: pd.DataFrame, tolerance_bars: int):
    grid = {
        "pivot_left": [1, 2, 3],
        "pivot_right": [1, 2],
        "rsi_buy_max": [40, 42, 45, 48],
        "rsi_sell_min": [52, 55, 58, 60],
        "min_body": [0.15, 0.20, 0.25, 0.30],
        "use_stoch": [False, True],
        "min_wick": [0.00, 0.10, 0.20, 0.30],
        "min_atr_distance": [0.00, 0.15, 0.30, 0.45],
        "min_gap_bars": [0, 1, 2, 3],
    }

    rows = []
    best_params = None
    best_signals = None
    best_score = None

    for pivot_left in grid["pivot_left"]:
        for pivot_right in grid["pivot_right"]:
            for rsi_buy_max in grid["rsi_buy_max"]:
                for rsi_sell_min in grid["rsi_sell_min"]:
                    for min_body in grid["min_body"]:
                        for use_stoch in grid["use_stoch"]:
                            for min_wick in grid["min_wick"]:
                                for min_atr_distance in grid["min_atr_distance"]:
                                    for min_gap_bars in grid["min_gap_bars"]:
                                        sigs = generate_candidate_signals(
                                            df=df,
                                            pivot_left=pivot_left,
                                            pivot_right=pivot_right,
                                            rsi_buy_max=rsi_buy_max,
                                            rsi_sell_min=rsi_sell_min,
                                            min_body=min_body,
                                            use_stoch=use_stoch,
                                            min_wick=min_wick,
                                            min_atr_distance=min_atr_distance,
                                            min_gap_bars=min_gap_bars,
                                        )
                                        sc = score_signals_vs_labels(sigs, labels, tolerance_bars=tolerance_bars)
                                        params = {
                                            "pivot_left": pivot_left,
                                            "pivot_right": pivot_right,
                                            "rsi_buy_max": rsi_buy_max,
                                            "rsi_sell_min": rsi_sell_min,
                                            "min_body": min_body,
                                            "use_stoch": use_stoch,
                                            "min_wick": min_wick,
                                            "min_atr_distance": min_atr_distance,
                                            "min_gap_bars": min_gap_bars,
                                        }
                                        rows.append(
                                            {
                                                **params,
                                                "score": sc.score,
                                                "recall": sc.recall,
                                                "precision_soft": sc.precision_soft,
                                                "matched": sc.matched,
                                                "labels_total": sc.labels_total,
                                                "signals_total": sc.signals_total,
                                                "duplicate_penalty": sc.duplicate_penalty,
                                            }
                                        )
                                        if (best_score is None) or (sc.score > best_score.score):
                                            best_score = sc
                                            best_params = params
                                            best_signals = sigs

    leaderboard = (
        pd.DataFrame(rows)
        .sort_values(["score", "matched", "precision_soft"], ascending=[False, False, False])
        .reset_index(drop=True)
    )
    return best_params, best_signals, best_score, leaderboard


def build_pivot_dataset(df: pd.DataFrame, labels: pd.DataFrame, best_params: Dict, timeframe_minutes: int = 15, tolerance_bars: int = 1):
    x = df.copy()

    pl = pivot_low(x["low"], best_params["pivot_left"], best_params["pivot_right"])
    ph = pivot_high(x["high"], best_params["pivot_left"], best_params["pivot_right"])

    pivot_low_conf = pl.shift(best_params["pivot_right"]).fillna(False)
    pivot_high_conf = ph.shift(best_params["pivot_right"]).fillna(False)

    x["candidate_side"] = ""
    x.loc[pivot_low_conf, "candidate_side"] = "BUY"
    x.loc[pivot_high_conf, "candidate_side"] = "SELL"
    x = x.loc[x["candidate_side"] != ""].copy()

    x["dist_from_ema9_atr"] = ((x["close"] - x["ema9"]).abs() / x["atr14"]).replace([np.inf, -np.inf], np.nan)
    x["dist_from_ema21_atr"] = ((x["close"] - x["ema21"]).abs() / x["atr14"]).replace([np.inf, -np.inf], np.nan)
    x["k_minus_d"] = x["k"] - x["d"]
    x["is_buy_candle"] = (x["close"] > x["open"]).astype(int)
    x["is_sell_candle"] = (x["close"] < x["open"]).astype(int)

    tol = pd.Timedelta(minutes=tolerance_bars * timeframe_minutes)
    x["target"] = 0
    for i, row in x.iterrows():
        same_side = labels[labels["side"] == row["candidate_side"]]
        if same_side.empty:
            continue
        d = (same_side["dt"] - row["time"]).abs()
        if (d <= tol).any():
            x.at[i, "target"] = 1

    feature_cols = [
        "rsi14",
        "atr14",
        "k",
        "d",
        "k_minus_d",
        "body_ratio",
        "upper_wick_ratio",
        "lower_wick_ratio",
        "ret1",
        "ret3",
        "dist_from_ema9_atr",
        "dist_from_ema21_atr",
        "hour",
        "minute",
        "is_buy_candle",
        "is_sell_candle",
    ]
    x = x.dropna(subset=feature_cols)
    return x, feature_cols


def train_ml_filter(pivot_ds: pd.DataFrame, feature_cols: List[str]):
    if pivot_ds.empty or pivot_ds["target"].nunique() < 2:
        return None, pd.DataFrame()

    X = pivot_ds[feature_cols]
    y = pivot_ds["target"].astype(int)
    tscv = TimeSeriesSplit(n_splits=4)
    oof = pd.Series(np.nan, index=pivot_ds.index, dtype=float)

    for tr, te in tscv.split(X):
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X.iloc[tr], y.iloc[tr])
        p = model.predict_proba(X.iloc[te])[:, 1]
        # te já são posições inteiras de X/pivot_ds; usar index labels aqui causava estouro
        oof.iloc[te] = p

    pivot_ds = pivot_ds.copy()
    pivot_ds["ml_prob"] = oof
    pivot_ds = pivot_ds.dropna(subset=["ml_prob"]).copy()

    final_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
    )
    final_model.fit(X, y)
    return final_model, pivot_ds


def ml_filtered_signals(df: pd.DataFrame, pivot_scored: pd.DataFrame, threshold: float = 0.55) -> pd.DataFrame:
    sigs = df[["time", "open", "high", "low", "close"]].copy()
    sigs["side"] = ""
    ok = pivot_scored[pivot_scored["ml_prob"] >= threshold].copy()
    sigs.loc[ok.index, "side"] = ok["candidate_side"]
    sigs["is_signal"] = sigs["side"] != ""
    return sigs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="CSV OHLC do NQ/MNQ 15m")
    ap.add_argument("--labels", default=None, help="CSV opcional com labels date,time,side")
    ap.add_argument("--outdir", default="saida_match_video_ml", help="Pasta de saída")
    ap.add_argument("--tolerance-bars", type=int, default=1, help="Tolerância em candles")
    ap.add_argument("--ml-threshold", type=float, default=0.55, help="Threshold do ML")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_ohlc(Path(args.csv))
    df = add_features(df)
    labels = load_labels(Path(args.labels) if args.labels else None)

    t0 = labels["dt"].min() - pd.Timedelta(hours=12)
    t1 = labels["dt"].max() + pd.Timedelta(hours=12)
    dfp = df[(df["time"] >= t0) & (df["time"] <= t1)].copy().reset_index(drop=True)

    best_params, best_signals, best_score, leaderboard = grid_search(dfp, labels, tolerance_bars=args.tolerance_bars)

    pivot_ds, feature_cols = build_pivot_dataset(dfp, labels, best_params, tolerance_bars=args.tolerance_bars)
    model, pivot_scored = train_ml_filter(pivot_ds, feature_cols)

    ml_signals = pd.DataFrame()
    ml_score = None
    if model is not None and not pivot_scored.empty:
        ml_signals = ml_filtered_signals(dfp, pivot_scored, threshold=args.ml_threshold)
        ml_score = score_signals_vs_labels(ml_signals, labels, tolerance_bars=args.tolerance_bars)

    (outdir / "best_params.json").write_text(json.dumps(best_params, indent=2, ensure_ascii=False), encoding="utf-8")
    leaderboard.to_csv(outdir / "leaderboard.csv", index=False)
    best_score.matched_rows.to_csv(outdir / "best_matches.csv", index=False)
    best_signals.to_csv(outdir / "candidate_signals.csv", index=False)

    if not pivot_scored.empty:
        pivot_scored.to_csv(outdir / "pivot_ml_dataset_scored.csv", index=False)
    if not ml_signals.empty:
        ml_signals.to_csv(outdir / "ml_filtered_signals.csv", index=False)
        ml_score.matched_rows.to_csv(outdir / "ml_matches.csv", index=False)

    pine = f'''//@version=6
indicator("Scalper V8 - Parametros Ajustados ML", overlay=true)

pivotLeft   = input.int({best_params["pivot_left"]}, "Pivot Left", minval=1)
pivotRight  = input.int({best_params["pivot_right"]}, "Pivot Right", minval=1)
rsiLen      = input.int(14, "RSI")
usarRSI     = input.bool(true, "Usar filtro RSI")
usarStoch   = input.bool({str(best_params["use_stoch"]).lower()}, "Usar filtro Stoch")
stochLen    = input.int(14, "Stoch Len")
smoothK     = input.int(3, "Smooth K")
smoothD     = input.int(3, "Smooth D")
minBody     = input.float({best_params["min_body"]}, "Min body/range", step=0.05)
minWick     = input.float({best_params["min_wick"]}, "Min wick/range", step=0.05)
minAtrDist  = input.float({best_params["min_atr_distance"]}, "Min distancia ATR", step=0.05)

rsiVal = ta.rsi(close, rsiLen)
stochBase = ta.stoch(close, high, low, stochLen)
k = ta.sma(stochBase, smoothK)
d = ta.sma(k, smoothD)
atrVal = ta.atr(14)

rangeCandle = high - low
body = math.abs(close - open)
bodyRatio = rangeCandle > 0 ? body / rangeCandle : 0.0
upperWick = high - math.max(open, close)
lowerWick = math.min(open, close) - low
upperWickRatio = rangeCandle > 0 ? upperWick / rangeCandle : 0.0
lowerWickRatio = rangeCandle > 0 ? lowerWick / rangeCandle : 0.0

bullReaction = close > open and close > close[1] and bodyRatio >= minBody and lowerWickRatio >= minWick
bearReaction = close < open and close < close[1] and bodyRatio >= minBody and upperWickRatio >= minWick

pLow  = ta.pivotlow(low, pivotLeft, pivotRight)
pHigh = ta.pivothigh(high, pivotLeft, pivotRight)

pivotLowConfirmed  = not na(pLow)
pivotHighConfirmed = not na(pHigh)

pivotLowPrice  = low[pivotRight]
pivotHighPrice = high[pivotRight]

buyRSI  = not usarRSI or (rsiVal[pivotRight] < {best_params["rsi_buy_max"]} or rsiVal > rsiVal[1])
sellRSI = not usarRSI or (rsiVal[pivotRight] > {best_params["rsi_sell_min"]} or rsiVal < rsiVal[1])

buyStoch  = not usarStoch or (k > d and k[1] <= d[1])
sellStoch = not usarStoch or (k < d and k[1] >= d[1])

buyDist  = math.abs(close - pivotLowPrice)  >= atrVal * minAtrDist
sellDist = math.abs(pivotHighPrice - close) >= atrVal * minAtrDist

buySignal  = pivotLowConfirmed and buyRSI and buyStoch and bullReaction and buyDist
sellSignal = pivotHighConfirmed and sellRSI and sellStoch and bearReaction and sellDist

barcolor(close > open ? color.lime : color.red)
plotshape(buySignal,  title="BUY",  style=shape.labelup,   location=location.belowbar, color=color.lime, text="BUY", textcolor=color.black, size=size.small)
plotshape(sellSignal, title="SELL", style=shape.labeldown, location=location.abovebar, color=color.red,  text="SELL", textcolor=color.white, size=size.small)
plotshape(pivotLowConfirmed,  title="Pivot Low",  style=shape.circle, location=location.belowbar, color=color.new(color.lime, 0), size=size.tiny, offset=-pivotRight)
plotshape(pivotHighConfirmed, title="Pivot High", style=shape.circle, location=location.abovebar, color=color.new(color.red, 0),  size=size.tiny, offset=-pivotRight)
'''
    (outdir / "best_pine_params.txt").write_text(pine, encoding="utf-8")

    report = []
    report.append("=== AJUSTE POR HORARIOS DO VIDEO ===")
    report.append(f"Labels fornecidos: {len(labels)}")
    report.append(f"Tolerancia: {args.tolerance_bars} candle(s)")
    report.append("")
    report.append("Melhores parametros:")
    report.append(json.dumps(best_params, indent=2, ensure_ascii=False))
    report.append("")
    report.append(f"Score melhor conjunto: {best_score.score:.4f}")
    report.append(f"Recall labels: {best_score.recall:.4f}")
    report.append(f"Precisao soft: {best_score.precision_soft:.4f}")
    report.append(f"Casamentos: {best_score.matched}/{best_score.labels_total}")
    report.append(f"Sinais gerados: {best_score.signals_total}")
    if ml_score is not None:
        report.append("")
        report.append("=== FILTRO ML ===")
        report.append(f"Threshold ML: {args.ml_threshold}")
        report.append(f"Score ML: {ml_score.score:.4f}")
        report.append(f"Recall ML: {ml_score.recall:.4f}")
        report.append(f"Precisao soft ML: {ml_score.precision_soft:.4f}")
        report.append(f"Casamentos ML: {ml_score.matched}/{ml_score.labels_total}")
        report.append(f"Sinais ML: {ml_score.signals_total}")
    report.append("")
    report.append("Arquivos gerados:")
    report.append("- best_params.json")
    report.append("- leaderboard.csv")
    report.append("- best_matches.csv")
    report.append("- candidate_signals.csv")
    report.append("- pivot_ml_dataset_scored.csv")
    report.append("- ml_filtered_signals.csv")
    report.append("- ml_matches.csv")
    report.append("- best_pine_params.txt")

    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")

    print(f"Criado: {outdir}")
    print("\n".join(report))


if __name__ == "__main__":
    main()
