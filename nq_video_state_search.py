#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from itertools import product
from pathlib import Path
import numpy as np
import pandas as pd

LABELS = [
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
    d = series.diff()
    up = d.clip(lower=0.0)
    dn = -d.clip(upper=0.0)
    au = up.ewm(alpha=1/period, adjust=False).mean()
    ad = dn.ewm(alpha=1/period, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    pc = df["close"].shift(1)
    tr = pd.concat([(df["high"]-df["low"]), (df["high"]-pc).abs(), (df["low"]-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def load_csv(path: Path):
    df = pd.read_csv(path)
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

def labels_df():
    y = pd.DataFrame(LABELS, columns=["date","time","side"])
    y["dt"] = pd.to_datetime(y["date"] + " " + y["time"])
    return y[["dt","side"]]

def add_feat(df):
    x = df.copy()
    x["ema5"] = ema(x["close"], 5)
    x["ema9"] = ema(x["close"], 9)
    x["ema13"] = ema(x["close"], 13)
    x["rsi7"] = rsi(x["close"], 7)
    x["atr14"] = atr(x, 14)
    rng = (x["high"] - x["low"]).replace(0, np.nan)
    x["body_ratio"] = (x["close"] - x["open"]).abs() / rng
    x["upper_wick_ratio"] = (x["high"] - x[["open", "close"]].max(axis=1)) / rng
    x["lower_wick_ratio"] = (x[["open", "close"]].min(axis=1) - x["low"]) / rng
    x["dist_ema9_atr"] = (x["close"] - x["ema9"]).abs() / x["atr14"]
    x["green"] = x["close"] > x["open"]
    x["red"] = x["close"] < x["open"]
    x["state"] = np.where(x["ema5"] > x["ema13"], 1, np.where(x["ema5"] < x["ema13"], -1, 0))
    return x

def pivots(x, left=2, right=1):
    low = x["low"].values
    high = x["high"].values
    pl = np.zeros(len(x), dtype=bool)
    ph = np.zeros(len(x), dtype=bool)
    for i in range(left, len(x)-right):
        pl[i] = (low[i] < low[i-left:i]).all() and (low[i] <= low[i+1:i+1+right]).all()
        ph[i] = (high[i] > high[i-left:i]).all() and (high[i] >= high[i+1:i+1+right]).all()
    return pd.Series(pl, index=x.index), pd.Series(ph, index=x.index)

def score(pred, labels):
    tol = pd.Timedelta(minutes=15)
    sigs = pred[pred["side"] != ""].copy()
    matched = 0
    rows = []
    for _, lab in labels.iterrows():
        same = sigs[sigs["side"] == lab["side"]].copy()
        if same.empty:
            rows.append((lab["dt"], lab["side"], pd.NaT, 0))
            continue
        same["delta"] = (same["time"] - lab["dt"]).abs()
        hit = same[same["delta"] <= tol].sort_values("delta")
        if len(hit):
            matched += 1
            rows.append((lab["dt"], lab["side"], hit.iloc[0]["time"], 1))
        else:
            rows.append((lab["dt"], lab["side"], pd.NaT, 0))
    total = len(labels)
    signals_total = int((pred["side"] != "").sum())
    recall = matched / total if total else 0
    extra = max(signals_total - matched, 0)
    precision_soft = matched / (matched + 0.3 * extra) if matched + extra > 0 else 0
    final = 0.8 * recall + 0.2 * precision_soft
    return final, recall, precision_soft, matched, signals_total, pd.DataFrame(rows, columns=["label_time","label_side","signal_time","matched"])

def generate(x, p):
    pl, ph = pivots(x, p["pivot_left"], p["pivot_right"])
    pl = pl.shift(p["pivot_right"]).fillna(False)
    ph = ph.shift(p["pivot_right"]).fillna(False)
    side = pd.Series("", index=x.index, dtype=object)

    buy_cand = (
        pl &
        (x["rsi7"] <= p["buy_rsi_max"]) &
        (x["lower_wick_ratio"] >= p["buy_lwick_min"]) &
        (x["body_ratio"] >= p["buy_body_min"]) &
        (x["dist_ema9_atr"] >= p["buy_dist_min"])
    )
    sell_cand = (
        ph &
        (x["rsi7"] >= p["sell_rsi_min"]) &
        (x["upper_wick_ratio"] >= p["sell_uwick_min"]) &
        (x["body_ratio"] >= p["sell_body_min"]) &
        (x["dist_ema9_atr"] >= p["sell_dist_min"])
    )

    if p["use_state"]:
        buy_cand &= x["state"] >= 0
        sell_cand &= x["state"] <= 0
    if p["use_color"]:
        buy_cand &= x["green"]
        sell_cand &= x["red"]

    st = 0
    last_bar = -999999
    for i in range(len(x)):
        if i - last_bar <= p["gap"]:
            continue
        if st == 0:
            if bool(buy_cand.iloc[i]) and bool(sell_cand.iloc[i]):
                if x["lower_wick_ratio"].iloc[i] >= x["upper_wick_ratio"].iloc[i]:
                    side.iloc[i] = "BUY"; st = 1
                else:
                    side.iloc[i] = "SELL"; st = -1
                last_bar = i
            elif bool(buy_cand.iloc[i]):
                side.iloc[i] = "BUY"; st = 1; last_bar = i
            elif bool(sell_cand.iloc[i]):
                side.iloc[i] = "SELL"; st = -1; last_bar = i
        elif st == 1:
            if bool(sell_cand.iloc[i]):
                side.iloc[i] = "SELL"; st = -1; last_bar = i
        else:
            if bool(buy_cand.iloc[i]):
                side.iloc[i] = "BUY"; st = 1; last_bar = i

    out = x[["time","open","high","low","close"]].copy()
    out["side"] = side
    return out

def pine(p):
    return f'''//@version=6
indicator("Scalper V10.1 - Ajuste objetivo", overlay=true, max_labels_count=500)
pivotLeft=input.int({p["pivot_left"]},"Pivot Left",minval=1)
pivotRight=input.int({p["pivot_right"]},"Pivot Right",minval=1)
buyRsiMax=input.float({p["buy_rsi_max"]},"RSI max BUY",step=0.5)
sellRsiMin=input.float({p["sell_rsi_min"]},"RSI min SELL",step=0.5)
buyLWick=input.float({p["buy_lwick_min"]},"Min wick inf BUY",step=0.05)
sellUWick=input.float({p["sell_uwick_min"]},"Min wick sup SELL",step=0.05)
buyBody=input.float({p["buy_body_min"]},"Min body BUY",step=0.05)
sellBody=input.float({p["sell_body_min"]},"Min body SELL",step=0.05)
buyDist=input.float({p["buy_dist_min"]},"Min dist EMA9 BUY ATR",step=0.05)
sellDist=input.float({p["sell_dist_min"]},"Min dist EMA9 SELL ATR",step=0.05)
useState=input.bool({str(p["use_state"]).lower()},"Usar estado EMA5/EMA13")
useColor=input.bool({str(p["use_color"]).lower()},"Usar cor candle")
gapMin=input.int({p["gap"]},"Gap mínimo",minval=0)

ema5=ta.ema(close,5)
ema9=ta.ema(close,9)
ema13=ta.ema(close,13)
rsi7=ta.rsi(close,7)
atr14=ta.atr(14)
rangeCandle=high-low
bodyRatio=rangeCandle>0?math.abs(close-open)/rangeCandle:0.0
upperWickRatio=rangeCandle>0?(high-math.max(open,close))/rangeCandle:0.0
lowerWickRatio=rangeCandle>0?(math.min(open,close)-low)/rangeCandle:0.0
distEma9Atr=atr14>0?math.abs(close-ema9)/atr14:0.0
state=ema5>ema13?1:ema5<ema13?-1:0
green=close>open
red=close<open
pLow=ta.pivotlow(low,pivotLeft,pivotRight)
pHigh=ta.pivothigh(high,pivotLeft,pivotRight)
pivotLowConfirmed=not na(pLow)
pivotHighConfirmed=not na(pHigh)
buyCand=pivotLowConfirmed and rsi7<=buyRsiMax and lowerWickRatio>=buyLWick and bodyRatio>=buyBody and distEma9Atr>=buyDist
sellCand=pivotHighConfirmed and rsi7>=sellRsiMin and upperWickRatio>=sellUWick and bodyRatio>=sellBody and distEma9Atr>=sellDist
if useState
    buyCand:=buyCand and state>=0
    sellCand:=sellCand and state<=0
if useColor
    buyCand:=buyCand and green
    sellCand:=sellCand and red
var int sigState=0
var int lastBar=na
buySignal=false
sellSignal=false
gapOk=na(lastBar) or bar_index-lastBar>gapMin
if gapOk
    if sigState==0
        if buyCand and sellCand
            buySignal:=lowerWickRatio>=upperWickRatio
            sellSignal:=upperWickRatio>lowerWickRatio
        else if buyCand
            buySignal:=true
        else if sellCand
            sellSignal:=true
    else if sigState==1 and sellCand
        sellSignal:=true
    else if sigState==-1 and buyCand
        buySignal:=true
if buySignal
    sigState:=1
    lastBar:=bar_index
if sellSignal
    sigState:=-1
    lastBar:=bar_index
plotshape(buySignal,title="BUY",style=shape.labelup,location=location.belowbar,color=color.lime,text="BUY",textcolor=color.black,size=size.small)
plotshape(sellSignal,title="SELL",style=shape.labeldown,location=location.abovebar,color=color.red,text="SELL",textcolor=color.white,size=size.small)
plotshape(pivotLowConfirmed,title="Pivot Low",style=shape.circle,location=location.belowbar,color=color.new(color.lime,0),size=size.tiny,offset=-pivotRight)
plotshape(pivotHighConfirmed,title="Pivot High",style=shape.circle,location=location.abovebar,color=color.new(color.red,0),size=size.tiny,offset=-pivotRight)
'''
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--outdir", default="saida_state_search")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    x = add_feat(load_csv(Path(args.csv)))
    y = labels_df()
    x = x[(x["time"] >= y["dt"].min() - pd.Timedelta(hours=12)) & (x["time"] <= y["dt"].max() + pd.Timedelta(hours=12))].reset_index(drop=True)

    space = {
        "pivot_left": [2,3],
        "pivot_right": [1],
        "buy_rsi_max": [42,45,48],
        "sell_rsi_min": [55,58,62],
        "buy_lwick_min": [0.10,0.18,0.25],
        "sell_uwick_min": [0.10,0.18,0.25,0.35],
        "buy_body_min": [0.10,0.15,0.25],
        "sell_body_min": [0.10,0.15,0.25],
        "buy_dist_min": [0.10,0.15,0.30],
        "sell_dist_min": [0.10,0.15,0.30,0.60],
        "use_state": [False, True],
        "use_color": [False, True],
        "gap": [1,2,3],
    }

    keys = list(space.keys())
    best = None
    best_tuple = None
    best_pred = None
    rows = []
    for combo in product(*[space[k] for k in keys]):
        p = dict(zip(keys, combo))
        pred = generate(x, p)
        sc, rec, prec, matched, signals, mdf = score(pred, y)
        rows.append({**p, "score": sc, "recall": rec, "precision_soft": prec, "matched": matched, "signals_total": signals})
        if best_tuple is None or sc > best_tuple[0]:
            best = p
            best_tuple = (sc, rec, prec, matched, signals, mdf)
            best_pred = pred

    pd.DataFrame(rows).sort_values(["score","matched","precision_soft"], ascending=[False,False,False]).to_csv(outdir / "leaderboard.csv", index=False)
    best_pred.to_csv(outdir / "best_signals.csv", index=False)
    best_tuple[5].to_csv(outdir / "best_matches.csv", index=False)
    (outdir / "best_params.json").write_text(json.dumps(best, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "best_pine.txt").write_text(pine(best), encoding="utf-8")
    report = [
        "=== STATE SEARCH ===",
        f"Score: {best_tuple[0]:.4f}",
        f"Recall: {best_tuple[1]:.4f}",
        f"Precisão soft: {best_tuple[2]:.4f}",
        f"Casamentos: {best_tuple[3]}/{len(y)}",
        f"Sinais gerados: {best_tuple[4]}",
        "",
        "Melhores parâmetros:",
        json.dumps(best, indent=2, ensure_ascii=False),
    ]
    (outdir / "report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()
