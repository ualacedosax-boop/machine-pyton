#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

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
    x["dist_ema5_atr"] = (x["close"] - x["ema5"]).abs() / x["atr14"]
    x["dist_ema9_atr"] = (x["close"] - x["ema9"]).abs() / x["atr14"]
    x["dist_ema13_atr"] = (x["close"] - x["ema13"]).abs() / x["atr14"]
    x["ema5_gt_ema13"] = (x["ema5"] > x["ema13"]).astype(int)
    x["ema9_gt_ema21"] = (x["ema9"] > x["ema21"]).astype(int)
    x["ema13_gt_ema34"] = (x["ema13"] > x["ema34"]).astype(int)
    x["green"] = (x["close"] > x["open"]).astype(int)
    x["red"] = (x["close"] < x["open"]).astype(int)
    x["close_gt_prev"] = (x["close"] > x["close"].shift(1)).astype(int)
    x["close_lt_prev"] = (x["close"] < x["close"].shift(1)).astype(int)
    x["ret1"] = x["close"].pct_change()
    x["ret2"] = x["close"].pct_change(2)
    x["ret3"] = x["close"].pct_change(3)
    x["hour"] = x["time"].dt.hour
    x["minute"] = x["time"].dt.minute
    return x

def build_entry_dataset(df, labels):
    x = df.copy()
    x["side"] = ""
    buy_times = set(labels.loc[labels["side"]=="BUY", "dt"].tolist())
    sell_times = set(labels.loc[labels["side"]=="SELL", "dt"].tolist())
    x.loc[x["time"].isin(buy_times), "side"] = "BUY"
    x.loc[x["time"].isin(sell_times), "side"] = "SELL"
    return x[x["side"] != ""].copy()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--outdir", default="saida_unsupervised_patterns")
    ap.add_argument("--clusters", type=int, default=3)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = add_features(load_ohlc(Path(args.csv)))
    labels = load_labels(Path(args.labels) if args.labels else None)

    t0 = labels["dt"].min() - pd.Timedelta(hours=12)
    t1 = labels["dt"].max() + pd.Timedelta(hours=12)
    df = df[(df["time"] >= t0) & (df["time"] <= t1)].copy().reset_index(drop=True)

    entries = build_entry_dataset(df, labels)

    feature_cols = [
        "rsi7","rsi10","rsi14","k","d",
        "body_ratio","upper_wick_ratio","lower_wick_ratio",
        "dist_ema5_atr","dist_ema9_atr","dist_ema13_atr",
        "ema5_gt_ema13","ema9_gt_ema21","ema13_gt_ema34",
        "green","red","close_gt_prev","close_lt_prev",
        "ret1","ret2","ret3","hour","minute"
    ]
    entries = entries.dropna(subset=feature_cols).copy()

    X = entries[feature_cols].copy()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=args.clusters, random_state=42, n_init=20)
    entries["cluster"] = kmeans.fit_predict(Xs)

    pca = PCA(n_components=2, random_state=42)
    p2 = pca.fit_transform(Xs)
    entries["pc1"] = p2[:, 0]
    entries["pc2"] = p2[:, 1]

    cluster_rows = []
    for c in sorted(entries["cluster"].unique()):
        d = entries[entries["cluster"] == c].copy()
        cluster_rows.append({
            "cluster": int(c),
            "count": int(len(d)),
            "buy_count": int((d["side"] == "BUY").sum()),
            "sell_count": int((d["side"] == "SELL").sum()),
            "buy_ratio": float((d["side"] == "BUY").mean()),
            "rsi7_mean": float(d["rsi7"].mean()),
            "rsi10_mean": float(d["rsi10"].mean()),
            "body_ratio_mean": float(d["body_ratio"].mean()),
            "upper_wick_ratio_mean": float(d["upper_wick_ratio"].mean()),
            "lower_wick_ratio_mean": float(d["lower_wick_ratio"].mean()),
            "dist_ema5_atr_mean": float(d["dist_ema5_atr"].mean()),
            "dist_ema9_atr_mean": float(d["dist_ema9_atr"].mean()),
            "hour_mean": float(d["hour"].mean()),
        })
    cluster_summary = pd.DataFrame(cluster_rows)

    entries["sell_exhaustion_score"] = (
        0.35 * entries["upper_wick_ratio"].fillna(0) +
        0.20 * entries["body_ratio"].fillna(0) +
        0.20 * (entries["rsi7"].fillna(50) / 100.0) +
        0.25 * np.clip(entries["dist_ema9_atr"].fillna(0) / 2.0, 0, 1)
    )
    entries["buy_exhaustion_score"] = (
        0.35 * entries["lower_wick_ratio"].fillna(0) +
        0.20 * entries["body_ratio"].fillna(0) +
        0.20 * ((100.0 - entries["rsi7"].fillna(50)) / 100.0) +
        0.25 * np.clip(entries["dist_ema9_atr"].fillna(0) / 2.0, 0, 1)
    )
    score_summary = entries.groupby("side")[["buy_exhaustion_score","sell_exhaustion_score"]].mean().reset_index()

    entries.to_csv(outdir / "clustered_entries.csv", index=False)
    cluster_summary.to_csv(outdir / "cluster_summary.csv", index=False)
    score_summary.to_csv(outdir / "exhaustion_score_summary.csv", index=False)

    report = []
    report.append("=== UNSUPERVISED ENTRY PATTERNS ===")
    report.append(f"Entradas usadas: {len(entries)}")
    report.append(f"Clusters: {args.clusters}")
    report.append("")
    report.append("Resumo por cluster:")
    for _, r in cluster_summary.iterrows():
        report.append(
            f"- Cluster {int(r['cluster'])}: count={int(r['count'])}, BUY={int(r['buy_count'])}, SELL={int(r['sell_count'])}, "
            f"buy_ratio={r['buy_ratio']:.2f}, rsi7_mean={r['rsi7_mean']:.2f}, body_mean={r['body_ratio_mean']:.2f}, "
            f"uwick_mean={r['upper_wick_ratio_mean']:.2f}, lwick_mean={r['lower_wick_ratio_mean']:.2f}, dist_ema9_atr_mean={r['dist_ema9_atr_mean']:.2f}"
        )
    report.append("")
    report.append("Novo indicador observacional sugerido:")
    report.append("- buy_exhaustion_score")
    report.append("- sell_exhaustion_score")
    report.append("Eles combinam wick + body + RSI7 + distância da EMA9.")
    report.append("")
    report.append("Arquivos gerados:")
    report.append("- clustered_entries.csv")
    report.append("- cluster_summary.csv")
    report.append("- exhaustion_score_summary.csv")
    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
