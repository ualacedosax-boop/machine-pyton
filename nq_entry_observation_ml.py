#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

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
    for n in [5,7,9,13,21,34]:
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
    x["close_gt_prev"] = (x["close"] > x["close"].shift(1)).astype(int)
    x["close_lt_prev"] = (x["close"] < x["close"].shift(1)).astype(int)
    x["green"] = (x["close"] > x["open"]).astype(int)
    x["red"] = (x["close"] < x["open"]).astype(int)
    x["dist_ema5_atr"] = (x["close"] - x["ema5"]).abs() / x["atr14"]
    x["dist_ema9_atr"] = (x["close"] - x["ema9"]).abs() / x["atr14"]
    x["dist_ema13_atr"] = (x["close"] - x["ema13"]).abs() / x["atr14"]
    x["ema5_gt_ema13"] = (x["ema5"] > x["ema13"]).astype(int)
    x["ema9_gt_ema21"] = (x["ema9"] > x["ema21"]).astype(int)
    x["ema13_gt_ema34"] = (x["ema13"] > x["ema34"]).astype(int)
    x["hour"] = x["time"].dt.hour
    x["minute"] = x["time"].dt.minute
    return x

def build_observation_dataset(df, labels):
    x = df.copy()
    x["label_side"] = ""
    buy_times = set(labels.loc[labels["side"]=="BUY", "dt"].tolist())
    sell_times = set(labels.loc[labels["side"]=="SELL", "dt"].tolist())
    x.loc[x["time"].isin(buy_times), "label_side"] = "BUY"
    x.loc[x["time"].isin(sell_times), "label_side"] = "SELL"
    x["is_entry"] = (x["label_side"] != "").astype(int)
    return x

def summarize_side(df_obs, side):
    d = df_obs[df_obs["label_side"] == side].copy()
    cols = [
        "rsi7","rsi10","rsi14","k","d","body_ratio","upper_wick_ratio","lower_wick_ratio",
        "dist_ema5_atr","dist_ema9_atr","dist_ema13_atr","ema5_gt_ema13","ema9_gt_ema21","ema13_gt_ema34",
        "green","red","close_gt_prev","close_lt_prev"
    ]
    out = {}
    for c in cols:
        if c not in d.columns or d.empty:
            continue
        out[c] = {
            "mean": float(d[c].mean()) if pd.api.types.is_numeric_dtype(d[c]) else None,
            "median": float(d[c].median()) if pd.api.types.is_numeric_dtype(d[c]) else None,
            "min": float(d[c].min()) if pd.api.types.is_numeric_dtype(d[c]) else None,
            "max": float(d[c].max()) if pd.api.types.is_numeric_dtype(d[c]) else None,
        }
    return out

def train_observation_model(df_obs):
    feature_cols = [
        "rsi7","rsi10","rsi14","k","d","body_ratio","upper_wick_ratio","lower_wick_ratio",
        "dist_ema5_atr","dist_ema9_atr","dist_ema13_atr","ema5_gt_ema13","ema9_gt_ema21","ema13_gt_ema34",
        "green","red","close_gt_prev","close_lt_prev","hour","minute"
    ]
    train = df_obs.dropna(subset=feature_cols).copy()
    X = train[feature_cols]
    y = train["is_entry"].astype(int)
    model = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=4, random_state=42, n_jobs=-1)
    model.fit(X, y)
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)

    side_importances = None
    entries = train[train["is_entry"] == 1].copy()
    if len(entries["label_side"].unique()) >= 2:
        y2 = (entries["label_side"] == "BUY").astype(int)
        side_model = RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=2, random_state=42, n_jobs=-1)
        side_model.fit(entries[feature_cols], y2)
        side_importances = pd.Series(side_model.feature_importances_, index=feature_cols).sort_values(ascending=False)

    return importances, side_importances

def build_entry_table(df_obs):
    cols = [
        "time","label_side","open","high","low","close","rsi7","rsi10","rsi14","k","d",
        "body_ratio","upper_wick_ratio","lower_wick_ratio","dist_ema5_atr","dist_ema9_atr",
        "dist_ema13_atr","ema5_gt_ema13","ema9_gt_ema21","ema13_gt_ema34","green","red","close_gt_prev","close_lt_prev"
    ]
    return df_obs[df_obs["is_entry"] == 1][cols].copy()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--outdir", default="saida_entry_observation")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = add_features(load_ohlc(Path(args.csv)))
    labels = load_labels(Path(args.labels) if args.labels else None)

    t0 = labels["dt"].min() - pd.Timedelta(hours=12)
    t1 = labels["dt"].max() + pd.Timedelta(hours=12)
    df = df[(df["time"] >= t0) & (df["time"] <= t1)].copy().reset_index(drop=True)

    obs = build_observation_dataset(df, labels)
    entry_table = build_entry_table(obs)
    summary_buy = summarize_side(obs, "BUY")
    summary_sell = summarize_side(obs, "SELL")
    importances, side_importances = train_observation_model(obs)

    entry_table.to_csv(outdir / "entry_indicator_snapshot.csv", index=False)

    imp_df = importances.reset_index()
    imp_df.columns = ["feature", "importance_entry"]
    imp_df.to_csv(outdir / "feature_importance_entry.csv", index=False)

    if side_importances is not None:
        side_df = side_importances.reset_index()
        side_df.columns = ["feature", "importance_buy_vs_sell"]
        side_df.to_csv(outdir / "feature_importance_buy_vs_sell.csv", index=False)

    (outdir / "summary_buy.json").write_text(json.dumps(summary_buy, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "summary_sell.json").write_text(json.dumps(summary_sell, indent=2, ensure_ascii=False), encoding="utf-8")

    report = []
    report.append("=== ENTRY OBSERVATION ML ===")
    report.append(f"Entradas analisadas: {len(entry_table)}")
    report.append("")
    report.append("Top 10 variáveis que mais ajudam a separar candle de entrada vs não entrada:")
    for feat, val in importances.head(10).items():
        report.append(f"- {feat}: {val:.4f}")
    if side_importances is not None:
        report.append("")
        report.append("Top 10 variáveis que mais ajudam a separar BUY vs SELL:")
        for feat, val in side_importances.head(10).items():
            report.append(f"- {feat}: {val:.4f}")

    report.append("")
    report.append("Médias observadas nas entradas BUY:")
    for k in ["rsi7","rsi10","rsi14","body_ratio","lower_wick_ratio","dist_ema5_atr","dist_ema9_atr","ema5_gt_ema13","ema9_gt_ema21"]:
        if k in summary_buy and summary_buy[k]["mean"] is not None:
            report.append(f"- {k}: mean={summary_buy[k]['mean']:.4f}")

    report.append("")
    report.append("Médias observadas nas entradas SELL:")
    for k in ["rsi7","rsi10","rsi14","body_ratio","upper_wick_ratio","dist_ema5_atr","dist_ema9_atr","ema5_gt_ema13","ema9_gt_ema21"]:
        if k in summary_sell and summary_sell[k]["mean"] is not None:
            report.append(f"- {k}: mean={summary_sell[k]['mean']:.4f}")

    report.append("")
    report.append("Arquivos gerados:")
    report.append("- entry_indicator_snapshot.csv")
    report.append("- feature_importance_entry.csv")
    report.append("- feature_importance_buy_vs_sell.csv")
    report.append("- summary_buy.json")
    report.append("- summary_sell.json")

    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
