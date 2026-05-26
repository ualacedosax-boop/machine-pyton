#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from typing import Optional, List
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

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
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def stoch(close, high, low, period=14):
    ll = low.rolling(period).min()
    hh = high.rolling(period).max()
    return 100 * (close - ll) / (hh - ll).replace(0, np.nan)

def load_ohlc(csv_path: Path):
    df = pd.read_csv(csv_path)
    cols = {c.lower().strip(): c for c in df.columns}
    t = pd.to_datetime(df[cols["time"]], errors="coerce")
    try:
        if getattr(t.dt, "tz", None) is not None:
            t = t.dt.tz_localize(None)
    except Exception:
        pass
    out = pd.DataFrame({
        "time": t,
        "open": pd.to_numeric(df[cols["open"]], errors="coerce"),
        "high": pd.to_numeric(df[cols["high"]], errors="coerce"),
        "low": pd.to_numeric(df[cols["low"]], errors="coerce"),
        "close": pd.to_numeric(df[cols["close"]], errors="coerce"),
    })
    return out.dropna().sort_values("time").reset_index(drop=True)

def load_labels(path: Optional[Path]):
    if path is None:
        y = pd.DataFrame(DEFAULT_LABELS, columns=["date","time","side"])
    else:
        y = pd.read_csv(path)
        y.columns = [c.lower().strip() for c in y.columns]
    y["dt"] = pd.to_datetime(y["date"].astype(str) + " " + y["time"].astype(str), errors="coerce")
    try:
        if getattr(y["dt"].dt, "tz", None) is not None:
            y["dt"] = y["dt"].dt.tz_localize(None)
    except Exception:
        pass
    y["side"] = y["side"].str.upper().str.strip()
    return y.dropna(subset=["dt"]).sort_values("dt").reset_index(drop=True)[["dt","side"]]

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    for n in [5,7,9,13,21,34]:
        x[f"ema{n}"] = ema(x["close"], n)
    for n in [5,7,10,14]:
        x[f"rsi{n}"] = rsi(x["close"], n)
    x["atr14"] = atr(x, 14)
    x["stoch14"] = stoch(x["close"], x["high"], x["low"], 14)
    x["k"] = x["stoch14"].rolling(3).mean()
    x["d"] = x["k"].rolling(3).mean()

    rng = (x["high"] - x["low"]).replace(0, np.nan)
    body = (x["close"] - x["open"]).abs()
    upper = x["high"] - x[["open","close"]].max(axis=1)
    lower = x[["open","close"]].min(axis=1) - x["low"]

    x["body_ratio"] = body / rng
    x["upper_wick_ratio"] = upper / rng
    x["lower_wick_ratio"] = lower / rng
    x["dist_ema5_atr"] = (x["close"] - x["ema5"]).abs() / x["atr14"]
    x["dist_ema9_atr"] = (x["close"] - x["ema9"]).abs() / x["atr14"]
    x["dist_ema13_atr"] = (x["close"] - x["ema13"]).abs() / x["atr14"]
    x["green"] = (x["close"] > x["open"]).astype(int)
    x["red"] = (x["close"] < x["open"]).astype(int)
    x["close_up"] = (x["close"] > x["close"].shift(1)).astype(int)
    x["close_down"] = (x["close"] < x["close"].shift(1)).astype(int)
    x["ema5_gt_13"] = (x["ema5"] > x["ema13"]).astype(int)
    x["ema9_gt_21"] = (x["ema9"] > x["ema21"]).astype(int)
    x["ema13_gt_34"] = (x["ema13"] > x["ema34"]).astype(int)
    x["ret1"] = x["close"].pct_change()
    x["ret2"] = x["close"].pct_change(2)
    x["ret3"] = x["close"].pct_change(3)
    x["hour"] = x["time"].dt.hour
    x["minute"] = x["time"].dt.minute
    return x

FEATURES = [
    "rsi5","rsi7","rsi10","rsi14","k","d",
    "body_ratio","upper_wick_ratio","lower_wick_ratio",
    "dist_ema5_atr","dist_ema9_atr","dist_ema13_atr",
    "green","red","close_up","close_down",
    "ema5_gt_13","ema9_gt_21","ema13_gt_34",
    "ret1","ret2","ret3","hour","minute"
]

FEATURE_GROUPS = {
    "core": ["rsi7","body_ratio","upper_wick_ratio","lower_wick_ratio","dist_ema9_atr"],
    "rsi_pack": ["rsi5","rsi7","rsi10","rsi14"],
    "stoch_pack": ["k","d"],
    "ema_pack": ["dist_ema5_atr","dist_ema9_atr","dist_ema13_atr","ema5_gt_13","ema9_gt_21","ema13_gt_34"],
    "candle_pack": ["body_ratio","upper_wick_ratio","lower_wick_ratio","green","red","close_up","close_down"],
    "returns_pack": ["ret1","ret2","ret3"],
    "time_pack": ["hour","minute"],
}

def build_dataset(df: pd.DataFrame, labels: pd.DataFrame, neg_mult: int = 4) -> pd.DataFrame:
    x = df.copy()
    x["side"] = ""
    buy_times = set(labels.loc[labels["side"]=="BUY","dt"].tolist())
    sell_times = set(labels.loc[labels["side"]=="SELL","dt"].tolist())
    x.loc[x["time"].isin(buy_times), "side"] = "BUY"
    x.loc[x["time"].isin(sell_times), "side"] = "SELL"
    x["is_entry"] = (x["side"] != "").astype(int)

    label_times = set(labels["dt"].tolist())
    neg_idx = []
    for i, row in x.iterrows():
        if row["time"] in label_times:
            continue
        near = any(abs((row["time"] - t).total_seconds()) <= 30*60 for t in label_times)
        if not near:
            neg_idx.append(i)

    pos = x[x["is_entry"] == 1].copy()
    neg = x.loc[neg_idx].copy()
    max_neg = min(len(neg), max(len(pos) * neg_mult, len(pos)))
    if len(neg) > max_neg:
        neg = neg.sample(n=max_neg, random_state=42)
    ds = pd.concat([pos, neg], axis=0).sort_values("time").reset_index(drop=True)
    return ds

def make_feature_subsets() -> List[List[str]]:
    subsets = []
    subsets.append(sorted(set(FEATURE_GROUPS["core"])))
    subsets.append(sorted(set(FEATURE_GROUPS["core"] + FEATURE_GROUPS["candle_pack"])))
    subsets.append(sorted(set(FEATURE_GROUPS["core"] + FEATURE_GROUPS["ema_pack"])))
    subsets.append(sorted(set(FEATURE_GROUPS["core"] + FEATURE_GROUPS["rsi_pack"] + FEATURE_GROUPS["candle_pack"])))
    subsets.append(sorted(set(FEATURE_GROUPS["core"] + FEATURE_GROUPS["rsi_pack"] + FEATURE_GROUPS["ema_pack"] + FEATURE_GROUPS["candle_pack"])))
    subsets.append(sorted(set(FEATURES)))
    return subsets

def build_model(name: str, seed: int):
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=300, max_depth=4, min_samples_leaf=2,
            random_state=seed, n_jobs=-1, class_weight="balanced_subsample"
        )
    if name == "rf_deep":
        return RandomForestClassifier(
            n_estimators=500, max_depth=6, min_samples_leaf=2,
            random_state=seed, n_jobs=-1, class_weight="balanced_subsample"
        )
    if name == "gb":
        return GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=2, random_state=seed
        )
    raise ValueError(name)

def eval_one(ds: pd.DataFrame, feat_cols: List[str], model_name: str, threshold: float, seed: int):
    data = ds.dropna(subset=feat_cols).copy()
    X = data[feat_cols].values
    y = data["is_entry"].astype(int).values

    if len(np.unique(y)) < 2 or len(data) < 20:
        return None

    tscv = TimeSeriesSplit(n_splits=4)
    oof = np.full(len(data), np.nan)

    for tr, te in tscv.split(X):
        Xtr, Xte = X[tr], X[te]
        ytr = y[tr]
        scaler = StandardScaler()
        Xtr = scaler.fit_transform(Xtr)
        Xte = scaler.transform(Xte)

        model = build_model(model_name, seed)
        model.fit(Xtr, ytr)

        if hasattr(model, "predict_proba"):
            p = model.predict_proba(Xte)[:, 1]
        else:
            raw = model.decision_function(Xte)
            p = 1 / (1 + np.exp(-raw))
        oof[te] = p

    valid = ~np.isnan(oof)
    yv = y[valid]
    pv = (oof[valid] >= threshold).astype(int)

    precision = precision_score(yv, pv, zero_division=0)
    recall = recall_score(yv, pv, zero_division=0)
    f1 = f1_score(yv, pv, zero_division=0)
    pred_count = int(pv.sum())
    score = 0.60 * precision + 0.25 * recall + 0.15 * f1

    return {
        "model": model_name,
        "threshold": threshold,
        "seed": seed,
        "features": feat_cols,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "pred_count": pred_count,
        "score": float(score),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--outdir", default="saida_iterative_ml")
    ap.add_argument("--target-precision", type=float, default=0.90)
    ap.add_argument("--max-rounds", type=int, default=60)
    ap.add_argument("--neg-mult", type=int, default=4)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = add_features(load_ohlc(Path(args.csv)))
    labels = load_labels(Path(args.labels) if args.labels else None)
    t0 = labels["dt"].min() - pd.Timedelta(hours=12)
    t1 = labels["dt"].max() + pd.Timedelta(hours=12)
    df = df[(df["time"] >= t0) & (df["time"] <= t1)].copy().reset_index(drop=True)

    ds = build_dataset(df, labels, neg_mult=args.neg_mult)
    subsets = make_feature_subsets()
    thresholds = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    models = ["rf", "rf_deep", "gb"]

    random.seed(42)
    candidates = []
    for _ in range(args.max_rounds):
        candidates.append((
            random.choice(subsets),
            random.choice(models),
            random.choice(thresholds),
            random.randint(1, 99999),
        ))

    best = None
    rows = []
    for i, (feat_cols, model_name, threshold, seed) in enumerate(candidates, start=1):
        res = eval_one(ds, feat_cols, model_name, threshold, seed)
        if res is None:
            continue
        res["round"] = i
        rows.append(res)
        if best is None or res["score"] > best["score"]:
            best = res
        print(f"[{i}/{args.max_rounds}] model={model_name} thr={threshold:.2f} precision={res['precision']:.3f} recall={res['recall']:.3f} f1={res['f1']:.3f} score={res['score']:.3f}")
        if res["precision"] >= args.target_precision and res["recall"] >= 0.35:
            best = res
            break

    leaderboard = pd.DataFrame(rows).sort_values(["score","precision","recall"], ascending=[False,False,False])
    leaderboard.to_csv(outdir / "leaderboard.csv", index=False)

    summary = {
        "target_precision": args.target_precision,
        "max_rounds": args.max_rounds,
        "dataset_rows": int(len(ds)),
        "entry_rows": int(ds["is_entry"].sum()),
        "best_result": best,
        "hit_target": bool(best is not None and best["precision"] >= args.target_precision and best["recall"] >= 0.35)
    }
    (outdir / "best_result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report = []
    report.append("=== ITERATIVE ML SEARCH ===")
    report.append(f"Linhas do dataset: {len(ds)}")
    report.append(f"Entradas reais: {int(ds['is_entry'].sum())}")
    report.append(f"Alvo de precisão: {args.target_precision:.2f}")
    report.append(f"Rodadas máximas: {args.max_rounds}")
    report.append("")
    if best is None:
        report.append("Nenhum resultado válido encontrado.")
    else:
        report.append("Melhor resultado:")
        report.append(f"- model: {best['model']}")
        report.append(f"- threshold: {best['threshold']}")
        report.append(f"- precision: {best['precision']:.4f}")
        report.append(f"- recall: {best['recall']:.4f}")
        report.append(f"- f1: {best['f1']:.4f}")
        report.append(f"- score: {best['score']:.4f}")
        report.append(f"- predições positivas: {best['pred_count']}")
        report.append(f"- features: {', '.join(best['features'])}")
        report.append("")
        if summary["hit_target"]:
            report.append("Meta de precisão atingida.")
        else:
            report.append("Meta de precisão NÃO atingida.")
            report.append("Isso pode acontecer porque há poucas entradas rotuladas e o padrão pode não ser estável o suficiente.")
    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
