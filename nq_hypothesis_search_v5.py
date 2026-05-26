#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

DEFAULT_LABELS = [
    ("2025-10-28","10:30","SELL"),("2025-10-28","12:30","BUY"),("2025-10-28","13:30","SELL"),
    ("2025-10-28","16:30","SELL"),("2025-10-28","17:00","BUY"),("2025-10-28","19:15","SELL"),
    ("2025-10-28","20:00","BUY"),("2025-10-28","21:00","BUY"),("2025-10-28","23:15","SELL"),
    ("2025-10-29","00:45","SELL"),("2025-10-29","01:00","BUY"),("2025-10-29","03:30","SELL"),
    ("2025-10-29","04:15","BUY"),("2025-10-29","05:15","SELL"),("2025-10-29","06:45","BUY"),
    ("2025-10-29","08:30","SELL"),("2025-10-29","09:30","BUY"),("2025-10-29","11:00","SELL"),
    ("2025-10-29","13:00","BUY"),("2025-10-29","15:00","SELL"),("2025-10-29","15:50","BUY"),
    ("2025-10-29","17:00","SELL"),("2025-10-29","19:00","BUY"),("2025-10-29","20:30","BUY"),
    ("2025-10-29","21:30","SELL"),("2025-10-29","22:00","BUY"),("2025-10-30","10:30","BUY"),
    ("2025-10-30","11:00","SELL"),("2025-10-30","12:45","BUY"),("2025-10-30","13:15","SELL"),
    ("2025-10-30","14:00","BUY"),("2025-10-30","14:45","SELL"),
]

def ema(s, span): return s.ewm(span=span, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    avg_up = up.ewm(alpha=1/period, adjust=False).mean()
    avg_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    prev_close = df["close"].shift(1)
    tr = pd.concat([(df["high"]-df["low"]), (df["high"]-prev_close).abs(), (df["low"]-prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def stoch(close, high, low, period=14):
    ll = low.rolling(period).min()
    hh = high.rolling(period).max()
    return 100 * (close-ll) / (hh-ll).replace(0, np.nan)

def pivot_low(series, left, right):
    arr = series.values
    out = np.zeros(len(arr), dtype=bool)
    for i in range(left, len(arr)-right):
        c = arr[i]
        if np.all(c < arr[i-left:i]) and np.all(c <= arr[i+1:i+1+right]):
            out[i] = True
    return pd.Series(out, index=series.index)

def pivot_high(series, left, right):
    arr = series.values
    out = np.zeros(len(arr), dtype=bool)
    for i in range(left, len(arr)-right):
        c = arr[i]
        if np.all(c > arr[i-left:i]) and np.all(c >= arr[i+1:i+1+right]):
            out[i] = True
    return pd.Series(out, index=series.index)

def load_ohlc(csv_path: Path):
    df = pd.read_csv(csv_path)
    cols = {c.lower().strip(): c for c in df.columns}
    parsed_time = pd.to_datetime(df[cols["time"]], errors="coerce")
    try:
        if getattr(parsed_time.dt, "tz", None) is not None:
            parsed_time = parsed_time.dt.tz_localize(None)
    except Exception:
        pass
    out = pd.DataFrame({
        "time": parsed_time,
        "open": pd.to_numeric(df[cols["open"]], errors="coerce"),
        "high": pd.to_numeric(df[cols["high"]], errors="coerce"),
        "low": pd.to_numeric(df[cols["low"]], errors="coerce"),
        "close": pd.to_numeric(df[cols["close"]], errors="coerce"),
    })
    return out.dropna().sort_values("time").reset_index(drop=True)

def load_labels(path: Optional[Path]):
    if path is None:
        labels = pd.DataFrame(DEFAULT_LABELS, columns=["date","time","side"])
    else:
        labels = pd.read_csv(path)
        labels.columns = [c.lower().strip() for c in labels.columns]
    labels["dt"] = pd.to_datetime(labels["date"].astype(str) + " " + labels["time"].astype(str), errors="coerce")
    try:
        if getattr(labels["dt"].dt, "tz", None) is not None:
            labels["dt"] = labels["dt"].dt.tz_localize(None)
    except Exception:
        pass
    labels["side"] = labels["side"].str.upper().str.strip()
    return labels.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)[["dt","side"]]

def add_features(df):
    x = df.copy()
    for n in [5,7,9,13,21]:
        x[f"ema{n}"] = ema(x["close"], n)
    for n in [7,10,14]:
        x[f"rsi{n}"] = rsi(x["close"], n)
    x["atr14"] = atr(x, 14)
    x["stoch14"] = stoch(x["close"], x["high"], x["low"], 14)
    x["k"] = x["stoch14"].rolling(3).mean()
    x["d"] = x["k"].rolling(3).mean()
    x["range"] = (x["high"] - x["low"]).replace(0, np.nan)
    x["body"] = (x["close"] - x["open"]).abs()
    x["body_ratio"] = x["body"] / x["range"]
    x["upper_wick"] = x["high"] - x[["open","close"]].max(axis=1)
    x["lower_wick"] = x[["open","close"]].min(axis=1) - x["low"]
    x["upper_wick_ratio"] = x["upper_wick"] / x["range"]
    x["lower_wick_ratio"] = x["lower_wick"] / x["range"]
    x["close_gt_prev"] = x["close"] > x["close"].shift(1)
    x["close_lt_prev"] = x["close"] < x["close"].shift(1)
    return x

@dataclass
class ScoreResult:
    score: float
    recall: float
    precision_soft: float
    matched: int
    labels_total: int
    signals_total: int
    matched_rows: pd.DataFrame

def score_signals_vs_labels(signals, labels, tolerance_bars=1):
    tol = pd.Timedelta(minutes=15*tolerance_bars)
    sigs = signals.loc[signals["is_signal"], ["time","side"]].copy().reset_index(drop=True)
    rows = []
    for _, lab in labels.iterrows():
        same = sigs[sigs["side"] == lab["side"]].copy()
        if same.empty:
            rows.append({"label_time": lab["dt"], "label_side": lab["side"], "signal_time": pd.NaT, "signal_side": "", "delta_minutes": np.nan, "matched": 0})
            continue
        same["delta"] = (same["time"] - lab["dt"]).abs()
        cand = same[same["delta"] <= tol].sort_values("delta")
        if cand.empty:
            rows.append({"label_time": lab["dt"], "label_side": lab["side"], "signal_time": pd.NaT, "signal_side": "", "delta_minutes": np.nan, "matched": 0})
        else:
            row = cand.iloc[0]
            rows.append({"label_time": lab["dt"], "label_side": lab["side"], "signal_time": row["time"], "signal_side": row["side"], "delta_minutes": row["delta"].total_seconds()/60.0, "matched": 1})
    m = pd.DataFrame(rows)
    matched = int(m["matched"].sum()) if not m.empty else 0
    labels_total = len(labels)
    signals_total = int(len(sigs))
    recall = matched / labels_total if labels_total else 0.0
    extra = max(signals_total - matched, 0)
    precision_soft = matched / (matched + 0.35 * extra) if (matched + extra) > 0 else 0.0
    score = 0.78 * recall + 0.22 * precision_soft
    return ScoreResult(score, recall, precision_soft, matched, labels_total, signals_total, m)

def choose_ema(x, n):
    return x[f"ema{n}"]

def build_signals(df, p):
    x = df.copy()
    pl = pivot_low(x["low"], p["pivot_left"], p["pivot_right"])
    ph = pivot_high(x["high"], p["pivot_left"], p["pivot_right"])
    pivot_low_conf = pl.shift(p["pivot_right"]).fillna(False)
    pivot_high_conf = ph.shift(p["pivot_right"]).fillna(False)
    pivot_low_price = x["low"].shift(p["pivot_right"])
    pivot_high_price = x["high"].shift(p["pivot_right"])

    buy = pivot_low_conf & (x["body_ratio"] >= p["min_body"])
    sell = pivot_high_conf & (x["body_ratio"] >= p["min_body"])

    if p["need_close_up_buy"]:
        buy &= x["close_gt_prev"]
    if p["need_close_down_sell"]:
        sell &= x["close_lt_prev"]
    if p["need_green_buy"]:
        buy &= x["close"] > x["open"]
    if p["need_red_sell"]:
        sell &= x["close"] < x["open"]
    if p["need_wick_buy"]:
        buy &= x["lower_wick_ratio"] >= p["min_wick_buy"]
    if p["need_wick_sell"]:
        sell &= x["upper_wick_ratio"] >= p["min_wick_sell"]

    buy_rsi = x[f"rsi{p['rsi_len_buy']}"].shift(p["pivot_right"]) <= p["rsi_buy_max"]
    sell_rsi = x[f"rsi{p['rsi_len_sell']}"].shift(p["pivot_right"]) >= p["rsi_sell_min"]
    if p["use_rsi_turn_buy"]:
        buy_rsi = buy_rsi | (x[f"rsi{p['rsi_len_buy']}"] > x[f"rsi{p['rsi_len_buy']}"].shift(1))
    if p["use_rsi_turn_sell"]:
        sell_rsi = sell_rsi | (x[f"rsi{p['rsi_len_sell']}"] < x[f"rsi{p['rsi_len_sell']}"].shift(1))
    buy &= buy_rsi
    sell &= sell_rsi

    if p["use_stoch_buy"]:
        buy &= (x["k"] > x["d"]) & (x["k"].shift(1) <= x["d"].shift(1))
    if p["use_stoch_sell"]:
        sell &= (x["k"] < x["d"]) & (x["k"].shift(1) >= x["d"].shift(1))

    if p["use_atr_pivot_buy"]:
        buy &= (x["close"] - pivot_low_price).abs() >= x["atr14"] * p["min_atr_pivot_buy"]
    if p["use_atr_pivot_sell"]:
        sell &= (pivot_high_price - x["close"]).abs() >= x["atr14"] * p["min_atr_pivot_sell"]

    if p["use_ema_filter_buy"]:
        buy &= choose_ema(x, p["ema_fast_buy"]) > choose_ema(x, p["ema_slow_buy"])
    if p["use_ema_filter_sell"]:
        sell &= choose_ema(x, p["ema_fast_sell"]) < choose_ema(x, p["ema_slow_sell"])

    if p["use_ema_distance_buy"]:
        buy &= (x["close"] - choose_ema(x, p["ema_dist_buy"])).abs() >= x["atr14"] * p["min_atr_ema_buy"]
    if p["use_ema_distance_sell"]:
        sell &= (x["close"] - choose_ema(x, p["ema_dist_sell"])).abs() >= x["atr14"] * p["min_atr_ema_sell"]

    if p["use_extreme_buy"]:
        buy &= pivot_low_price <= x["low"].rolling(p["extreme_lb_buy"]).min().shift(p["pivot_right"])
    if p["use_extreme_sell"]:
        sell &= pivot_high_price >= x["high"].rolling(p["extreme_lb_sell"]).max().shift(p["pivot_right"])

    sig = pd.Series("", index=x.index, dtype=object)
    last_buy = -999999
    last_sell = -999999
    for i in range(len(x)):
        if bool(buy.iloc[i]) and i - last_buy > p["gap_buy"]:
            sig.iloc[i] = "BUY"
            last_buy = i
        if bool(sell.iloc[i]) and i - last_sell > p["gap_sell"]:
            if sig.iloc[i] == "BUY":
                buy_strength = float(x["lower_wick_ratio"].fillna(0).iloc[i] + x["body_ratio"].fillna(0).iloc[i])
                sell_strength = float(x["upper_wick_ratio"].fillna(0).iloc[i] + x["body_ratio"].fillna(0).iloc[i])
                if sell_strength >= buy_strength:
                    sig.iloc[i] = "SELL"
                    last_sell = i
            else:
                sig.iloc[i] = "SELL"
                last_sell = i

    out = x[["time","open","high","low","close"]].copy()
    out["side"] = sig
    out["is_signal"] = out["side"] != ""
    return out

def candidate_space():
    return {
        "pivot_left": [2,3,4],
        "pivot_right": [1,2],
        "min_body": [0.20,0.25,0.30],
        "need_close_up_buy": [False,True],
        "need_close_down_sell": [False,True],
        "need_green_buy": [False,True],
        "need_red_sell": [False,True],
        "need_wick_buy": [False,True],
        "need_wick_sell": [False,True],
        "min_wick_buy": [0.0,0.15],
        "min_wick_sell": [0.0,0.15],
        "rsi_len_buy": [7,10,14],
        "rsi_len_sell": [7,10,14],
        "rsi_buy_max": [35,40,45],
        "rsi_sell_min": [50,52,55,58],
        "use_rsi_turn_buy": [False,True],
        "use_rsi_turn_sell": [False,True],
        "use_stoch_buy": [False,True],
        "use_stoch_sell": [False,True],
        "use_atr_pivot_buy": [False,True],
        "use_atr_pivot_sell": [False,True],
        "min_atr_pivot_buy": [0.15,0.30,0.45],
        "min_atr_pivot_sell": [0.15,0.30,0.45],
        "use_ema_filter_buy": [False,True],
        "use_ema_filter_sell": [False,True],
        "ema_fast_buy": [5,7,9],
        "ema_slow_buy": [13,21],
        "ema_fast_sell": [5,7,9],
        "ema_slow_sell": [13,21],
        "use_ema_distance_buy": [False,True],
        "use_ema_distance_sell": [False,True],
        "ema_dist_buy": [5,9,21],
        "ema_dist_sell": [5,9,21],
        "min_atr_ema_buy": [0.0,0.15],
        "min_atr_ema_sell": [0.0,0.15],
        "use_extreme_buy": [False,True],
        "use_extreme_sell": [False,True],
        "extreme_lb_buy": [4,6,8],
        "extreme_lb_sell": [4,6,8],
        "gap_buy": [1,2,3],
        "gap_sell": [1,2,3],
    }

def search(df, labels, tolerance_bars=1, max_tests=15000):
    space = candidate_space()
    keys = list(space.keys())
    vals = [space[k] for k in keys]
    rows, best_params, best_signals, best_score = [], None, None, None
    tested = 0
    for combo in product(*vals):
        p = dict(zip(keys, combo))
        if p["ema_fast_buy"] >= p["ema_slow_buy"] or p["ema_fast_sell"] >= p["ema_slow_sell"]:
            continue
        if (not p["need_wick_buy"]) and p["min_wick_buy"] != 0.0:
            continue
        if (not p["need_wick_sell"]) and p["min_wick_sell"] != 0.0:
            continue
        if (not p["use_atr_pivot_buy"]) and p["min_atr_pivot_buy"] != 0.15:
            continue
        if (not p["use_atr_pivot_sell"]) and p["min_atr_pivot_sell"] != 0.15:
            continue
        if (not p["use_ema_distance_buy"]) and p["min_atr_ema_buy"] != 0.0:
            continue
        if (not p["use_ema_distance_sell"]) and p["min_atr_ema_sell"] != 0.0:
            continue
        if (not p["use_extreme_buy"]) and p["extreme_lb_buy"] != 4:
            continue
        if (not p["use_extreme_sell"]) and p["extreme_lb_sell"] != 4:
            continue

        sigs = build_signals(df, p)
        sc = score_signals_vs_labels(sigs, labels, tolerance_bars=tolerance_bars)
        rows.append({**p, "score": sc.score, "recall": sc.recall, "precision_soft": sc.precision_soft, "matched": sc.matched, "signals_total": sc.signals_total})
        tested += 1
        if best_score is None or sc.score > best_score.score:
            best_params, best_signals, best_score = p, sigs, sc
        if tested >= max_tests:
            break
    lb = pd.DataFrame(rows).sort_values(["score","matched","precision_soft"], ascending=[False,False,False]).reset_index(drop=True)
    return best_params, best_signals, best_score, lb

def pine_from_params(p):
    return "// Veja best_params.json para os parametros vencedores. Este arquivo resume a busca V5."

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--outdir", default="saida_hypothesis_v5")
    ap.add_argument("--tolerance-bars", type=int, default=1)
    ap.add_argument("--max-tests", type=int, default=15000)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = add_features(load_ohlc(Path(args.csv)))
    labels = load_labels(Path(args.labels) if args.labels else None)

    t0 = labels["dt"].min() - pd.Timedelta(hours=12)
    t1 = labels["dt"].max() + pd.Timedelta(hours=12)
    df = df[(df["time"] >= t0) & (df["time"] <= t1)].copy().reset_index(drop=True)

    best, sigs, score, lb = search(df, labels, args.tolerance_bars, args.max_tests)

    lb.to_csv(outdir / "leaderboard.csv", index=False)
    sigs.to_csv(outdir / "best_signals.csv", index=False)
    score.matched_rows.to_csv(outdir / "best_matches.csv", index=False)
    (outdir / "best_params.json").write_text(json.dumps(best, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "best_pine_params.txt").write_text(pine_from_params(best), encoding="utf-8")

    report = []
    report.append("=== HYPOTHESIS SEARCH V5 ===")
    report.append(f"Labels: {len(labels)}")
    report.append(f"Tolerancia: {args.tolerance_bars} candle(s)")
    report.append(f"Max tests: {args.max_tests}")
    report.append("")
    report.append("Melhores parametros:")
    report.append(json.dumps(best, indent=2, ensure_ascii=False))
    report.append("")
    report.append(f"Score final: {score.score:.4f}")
    report.append(f"Recall: {score.recall:.4f}")
    report.append(f"Precisao soft: {score.precision_soft:.4f}")
    report.append(f"Casamentos: {score.matched}/{score.labels_total}")
    report.append(f"Sinais gerados: {score.signals_total}")
    report.append("")
    report.append("Arquivos gerados:")
    report.append("- leaderboard.csv")
    report.append("- best_signals.csv")
    report.append("- best_matches.csv")
    report.append("- best_params.json")
    report.append("- best_pine_params.txt")
    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
