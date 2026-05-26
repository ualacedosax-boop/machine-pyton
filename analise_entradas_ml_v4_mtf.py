#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V4 multi-timeframe
- timeframe base de entrada: 15m
- contexto: 5m, 30m opcional, 1h
- features estruturais + indicadores + sessão
- casamento das entradas no 15m
- merge do contexto dos outros timeframes por merge_asof
- ranking BUY x SELL
- ML simples e robusto

Exemplo:
python analise_entradas_ml_v4_mtf.py ^
  --base "nq_15m.csv" ^
  --tf5 "nq_5m.csv" ^
  --tf1h "nq_1h.csv" ^
  --entradas "entradas_ampliadas.csv" ^
  --saida "./saida_v4"

Opcional:
  --tf30 "nq_30m.csv"
"""

from __future__ import annotations

import argparse
import json
import math
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score


# =========================================================
# util
# =========================================================
def norm_text(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "_").replace("-", "_").replace("/", "_")
    return s


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [norm_text(c) for c in df.columns]
    return df


def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    try:
        df = pd.read_csv(path)
        if len(df.columns) == 1:
            df = pd.read_csv(path, sep=None, engine="python")
        return df
    except Exception:
        return pd.read_csv(path, sep=None, engine="python")


def ensure_naive_datetime(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s, errors="coerce")
    try:
        if getattr(s.dtype, "tz", None) is not None:
            s = s.dt.tz_convert(None)
    except Exception:
        pass
    return s


# =========================================================
# leitura
# =========================================================
def load_ohlc(path: Path) -> pd.DataFrame:
    df = read_any(path)
    df = norm_cols(df)

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

    if "datetime" in df.columns:
        df["datetime"] = ensure_naive_datetime(df["datetime"])
    elif "time" in df.columns and "date" not in df.columns:
        df["datetime"] = ensure_naive_datetime(df["time"])
    elif "date" in df.columns and "time" in df.columns:
        df["datetime"] = ensure_naive_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    elif "date" in df.columns:
        df["datetime"] = ensure_naive_datetime(df["date"])
    else:
        raise ValueError(f"Arquivo {path.name}: nao encontrei datetime nem date+time.")

    for c in ["open", "high", "low", "close"]:
        if c not in df.columns:
            raise ValueError(f"Arquivo {path.name}: falta coluna {c}.")
        df[c] = pd.to_numeric(df[c], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = np.nan
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df = df.dropna(subset=["datetime", "open", "high", "low", "close"]).copy()
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    return df[["datetime", "open", "high", "low", "close", "volume"]]


def load_entries(path: Path) -> pd.DataFrame:
    df = read_any(path)
    df = norm_cols(df)

    rename_map = {}
    for c in df.columns:
        if c in ["date", "data"]:
            rename_map[c] = "date"
        elif c in ["time", "hora"]:
            rename_map[c] = "time"
        elif c in ["datetime", "timestamp", "datahora", "data_hora"]:
            rename_map[c] = "datetime"
        elif c in ["side", "tipo", "acao", "action", "direcao", "lado"]:
            rename_map[c] = "side"
    df = df.rename(columns=rename_map)

    if "datetime" not in df.columns:
        if "date" in df.columns and "time" in df.columns:
            df["datetime"] = ensure_naive_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
        else:
            raise ValueError("Arquivo de entradas precisa ter datetime ou date+time.")

    if "side" not in df.columns:
        raise ValueError("Arquivo de entradas precisa ter side.")

    df["datetime"] = ensure_naive_datetime(df["datetime"])
    df["side"] = df["side"].astype(str).str.upper().str.strip()
    df = df[df["side"].isin(["BUY", "SELL"])].copy()
    df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    return df[["datetime", "side"]]


# =========================================================
# indicadores
# =========================================================
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    pc = c.shift(1)
    tr = pd.concat([(h-l), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()


def cci(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 20) -> pd.Series:
    tp = (h+l+c)/3
    ma = tp.rolling(n).mean()
    mad = (tp-ma).abs().rolling(n).mean()
    return (tp-ma) / (0.015 * mad.replace(0, np.nan))


def add_session_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hour"] = out["datetime"].dt.hour
    out["minute"] = out["datetime"].dt.minute
    out["dow"] = out["datetime"].dt.dayofweek

    out["sess_asia"] = ((out["hour"] >= 19) | (out["hour"] < 2)).astype(int)
    out["sess_europa"] = ((out["hour"] >= 2) & (out["hour"] < 8)).astype(int)
    out["sess_ny_open"] = ((out["hour"] >= 8) & (out["hour"] < 11)).astype(int)
    out["sess_ny_mid"] = ((out["hour"] >= 11) & (out["hour"] < 15)).astype(int)
    out["sess_ny_close"] = ((out["hour"] >= 15) & (out["hour"] < 18)).astype(int)

    out["hour_sin"] = np.sin(2*np.pi*out["hour"]/24.0)
    out["hour_cos"] = np.cos(2*np.pi*out["hour"]/24.0)
    return out


def add_price_structure(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = df.copy()
    o, h, l, c = out["open"], out["high"], out["low"], out["close"]

    out[f"{prefix}ret_1"] = c.pct_change(1) * 100
    out[f"{prefix}ret_3"] = c.pct_change(3) * 100
    out[f"{prefix}ret_5"] = c.pct_change(5) * 100

    for n in [5, 8, 9, 21, 50]:
        sm = c.rolling(n).mean()
        em = ema(c, n)
        out[f"{prefix}sma_{n}"] = sm
        out[f"{prefix}ema_{n}"] = em
        out[f"{prefix}dist_sma_{n}"] = c - sm
        out[f"{prefix}dist_ema_{n}"] = c - em

    out[f"{prefix}slope_ema_5_5"] = out[f"{prefix}ema_5"] - out[f"{prefix}ema_5"].shift(5)
    out[f"{prefix}slope_ema_21_5"] = out[f"{prefix}ema_21"] - out[f"{prefix}ema_21"].shift(5)

    for n in [7, 9, 14]:
        out[f"{prefix}rsi_{n}"] = rsi(c, n)

    out[f"{prefix}atr_14"] = atr(h, l, c, 14)
    out[f"{prefix}atr_pct"] = (out[f"{prefix}atr_14"] / c.replace(0, np.nan)) * 100
    out[f"{prefix}cci_20"] = cci(h, l, c, 20)

    out[f"{prefix}body"] = c - o
    out[f"{prefix}range"] = h - l
    out[f"{prefix}body_pct"] = (out[f"{prefix}body"].abs() / out[f"{prefix}range"].replace(0, np.nan))
    out[f"{prefix}upper_wick"] = h - np.maximum(c, o)
    out[f"{prefix}lower_wick"] = np.minimum(c, o) - l
    out[f"{prefix}close_pos_bar"] = (c - l) / (h - l).replace(0, np.nan)

    # estrutura local
    for n in [5, 10, 20]:
        rh = h.rolling(n).max()
        rl = l.rolling(n).min()
        out[f"{prefix}dist_top_{n}"] = rh - c
        out[f"{prefix}dist_bottom_{n}"] = c - rl
        out[f"{prefix}pos_range_{n}"] = (c - rl) / (rh - rl).replace(0, np.nan)

    # sequencia de candles
    chg = np.sign(c.diff()).fillna(0)
    out[f"{prefix}run_up_3"] = chg.rolling(3).apply(lambda x: np.sum(x > 0), raw=True)
    out[f"{prefix}run_dn_3"] = chg.rolling(3).apply(lambda x: np.sum(x < 0), raw=True)
    out[f"{prefix}run_up_5"] = chg.rolling(5).apply(lambda x: np.sum(x > 0), raw=True)
    out[f"{prefix}run_dn_5"] = chg.rolling(5).apply(lambda x: np.sum(x < 0), raw=True)

    # pivôs simples
    out[f"{prefix}pivot_low"] = ((l.shift(2) > l.shift(1)) & (l > l.shift(1))).astype(int)
    out[f"{prefix}pivot_high"] = ((h.shift(2) < h.shift(1)) & (h < h.shift(1))).astype(int)

    # rejeição
    out[f"{prefix}bull_reject"] = (
        (out[f"{prefix}lower_wick"] > out[f"{prefix}body"].abs() * 1.2) &
        (out[f"{prefix}close_pos_bar"] > 0.55)
    ).astype(int)

    out[f"{prefix}bear_reject"] = (
        (out[f"{prefix}upper_wick"] > out[f"{prefix}body"].abs() * 1.2) &
        (out[f"{prefix}close_pos_bar"] < 0.45)
    ).astype(int)

    return out


def build_tf_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out = add_session_features(out)
    out = add_price_structure(out, prefix)
    keep = ["datetime"] + [c for c in out.columns if c != "datetime" and c not in ["open", "high", "low", "close", "volume", "hour", "minute", "dow"]]
    # também manter OHLC do timeframe com prefixo
    out = out.rename(columns={
        "open": f"{prefix}open",
        "high": f"{prefix}high",
        "low": f"{prefix}low",
        "close": f"{prefix}close",
        "volume": f"{prefix}volume",
        "hour_sin": f"{prefix}hour_sin",
        "hour_cos": f"{prefix}hour_cos",
        "sess_asia": f"{prefix}sess_asia",
        "sess_europa": f"{prefix}sess_europa",
        "sess_ny_open": f"{prefix}sess_ny_open",
        "sess_ny_mid": f"{prefix}sess_ny_mid",
        "sess_ny_close": f"{prefix}sess_ny_close",
    })
    cols = ["datetime", f"{prefix}open", f"{prefix}high", f"{prefix}low", f"{prefix}close", f"{prefix}volume"] + \
           [c for c in out.columns if c.startswith(prefix) and c not in [f"{prefix}open", f"{prefix}high", f"{prefix}low", f"{prefix}close", f"{prefix}volume"]]
    cols = [c for c in cols if c in out.columns]
    return out[cols].copy()


# =========================================================
# merge multi-timeframe
# =========================================================
def infer_tf_minutes(df: pd.DataFrame) -> int:
    diffs = df["datetime"].diff().dropna().dt.total_seconds() / 60.0
    if diffs.empty:
        return 1
    return int(round(float(diffs.mode().iloc[0])))


def merge_context(base_entries: pd.DataFrame, ctx: pd.DataFrame, tolerance_min: int) -> pd.DataFrame:
    return pd.merge_asof(
        base_entries.sort_values("datetime"),
        ctx.sort_values("datetime"),
        on="datetime",
        direction="backward",
        tolerance=pd.Timedelta(minutes=tolerance_min),
    )


def match_entries_to_base(base_tf: pd.DataFrame, entries: pd.DataFrame, tolerance_min: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    matched = pd.merge_asof(
        entries.sort_values("datetime"),
        base_tf.sort_values("datetime"),
        on="datetime",
        direction="backward",
        tolerance=pd.Timedelta(minutes=tolerance_min),
    )
    ok = matched.dropna(subset=["b_open"]).copy()
    miss = matched[matched["b_open"].isna()][["datetime", "side"]].copy()
    return ok.reset_index(drop=True), miss.reset_index(drop=True)


# =========================================================
# ranking e ml
# =========================================================
def robust_effect(buy: pd.Series, sell: pd.Series) -> float:
    med_b = float(np.nanmedian(buy))
    med_s = float(np.nanmedian(sell))
    allv = pd.concat([buy, sell], ignore_index=True)
    iqr = float(np.nanpercentile(allv, 75) - np.nanpercentile(allv, 25))
    if iqr == 0 or math.isnan(iqr):
        iqr = float(np.nanstd(allv))
    if iqr == 0 or math.isnan(iqr):
        return 0.0
    return (med_b - med_s) / iqr


def make_ranking(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for col in features:
        if col not in df.columns:
            continue
        b = pd.to_numeric(df.loc[df["side"] == "BUY", col], errors="coerce")
        s = pd.to_numeric(df.loc[df["side"] == "SELL", col], errors="coerce")
        if b.notna().sum() < 8 or s.notna().sum() < 8:
            continue
        eff = robust_effect(b, s)
        rows.append({
            "variavel": col,
            "median_buy": float(np.nanmedian(b)),
            "median_sell": float(np.nanmedian(s)),
            "effect": eff,
            "abs_effect": abs(eff),
        })
    if not rows:
        return pd.DataFrame(columns=["variavel", "median_buy", "median_sell", "effect", "abs_effect"])
    return pd.DataFrame(rows).sort_values("abs_effect", ascending=False).reset_index(drop=True)


def run_ml(df: pd.DataFrame, features: list[str]) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    feats = [c for c in features if c in df.columns]
    X = df[feats].apply(pd.to_numeric, errors="coerce")
    y = df["side"].map({"SELL": 0, "BUY": 1}).astype(int)

    keep = [c for c in X.columns if X[c].nunique(dropna=True) > 1]
    X = X[keep]

    n = len(df)
    n_train = max(30, int(round(n * 0.65)))
    n_train = min(n_train, n - 5)

    X_train, X_test = X.iloc[:n_train].copy(), X.iloc[n_train:].copy()
    y_train, y_test = y.iloc[:n_train].copy(), y.iloc[n_train:].copy()

    imp = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(imp.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_imp = pd.DataFrame(imp.transform(X_test), columns=X_test.columns, index=X_test.index)

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=4,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced_subsample",
    )
    clf.fit(X_train_imp, y_train)

    pred = clf.predict(X_test_imp)
    proba = clf.predict_proba(X_test_imp)[:, 1]

    acc = float(accuracy_score(y_test, pred))
    try:
        auc = float(roc_auc_score(y_test, proba)) if len(np.unique(y_test)) > 1 else float("nan")
    except Exception:
        auc = float("nan")

    rep = classification_report(
        y_test, pred,
        labels=[0, 1],
        target_names=["SELL", "BUY"],
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, pred, labels=[0, 1])

    importances = pd.DataFrame({
        "feature": X_train_imp.columns,
        "importance": clf.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    preds = pd.DataFrame({
        "datetime": df.iloc[n_train:]["datetime"].values,
        "side_real": df.iloc[n_train:]["side"].values,
        "y_real": y_test.values,
        "y_pred": pred,
        "side_pred": np.where(pred == 1, "BUY", "SELL"),
        "proba_buy": proba,
    })
    preds["acertou"] = (preds["side_real"] == preds["side_pred"]).astype(int)

    metrics = {
        "accuracy": acc,
        "roc_auc": auc,
        "n_total": int(n),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_features": int(X.shape[1]),
        "features_usadas": list(X.columns),
        "class_map": {"SELL": 0, "BUY": 1},
        "confusion_matrix": cm.tolist(),
        "classification_report": rep,
    }
    return metrics, importances, preds


# =========================================================
# main
# =========================================================
DEFAULT_FEATURES = [
    # base 15m
    "b_ret_3", "b_ret_5", "b_rsi_7", "b_rsi_9", "b_rsi_14",
    "b_atr_14", "b_atr_pct", "b_cci_20",
    "b_dist_top_5", "b_dist_bottom_5", "b_pos_range_5",
    "b_dist_top_10", "b_dist_bottom_10", "b_pos_range_10",
    "b_dist_sma_8", "b_dist_sma_9",
    "b_slope_ema_5_5", "b_slope_ema_21_5",
    "b_bull_reject", "b_bear_reject", "b_pivot_low", "b_pivot_high",
    "b_run_up_3", "b_run_dn_3", "b_run_up_5", "b_run_dn_5",
    # 5m gatilho
    "m5_rsi_7", "m5_rsi_9", "m5_dist_top_5", "m5_dist_bottom_5",
    "m5_pos_range_5", "m5_bull_reject", "m5_bear_reject",
    "m5_pivot_low", "m5_pivot_high", "m5_close_pos_bar",
    "m5_run_up_3", "m5_run_dn_3",
    # 1h contexto
    "h1_rsi_14", "h1_dist_sma_21", "h1_dist_ema_21",
    "h1_dist_sma_50", "h1_dist_ema_50",
    "h1_pos_range_10", "h1_pos_range_20",
    "h1_slope_ema_21_5", "h1_slope_ema_5_5",
    "h1_bull_reject", "h1_bear_reject",
    # sessão
    "b_sess_asia", "b_sess_europa", "b_sess_ny_open", "b_sess_ny_mid", "b_sess_ny_close",
    "b_hour_sin", "b_hour_cos",
]

OPTIONAL_TF30 = [
    "m30_rsi_14", "m30_pos_range_10", "m30_dist_sma_21",
    "m30_slope_ema_21_5", "m30_bull_reject", "m30_bear_reject"
]


def write_summary(path: Path, df: pd.DataFrame, ranking: pd.DataFrame, metrics: dict, not_matched: int) -> None:
    lines = []
    lines.append("RESUMO DA ANALISE V4 MULTI-TIMEFRAME")
    lines.append("")
    lines.append(f"Total de entradas casadas: {len(df)}")
    lines.append(f"BUY: {(df['side'] == 'BUY').sum()}")
    lines.append(f"SELL: {(df['side'] == 'SELL').sum()}")
    lines.append(f"Entradas nao casadas: {not_matched}")
    lines.append("")
    lines.append("Top variaveis por diferenca BUY x SELL:")
    for _, r in ranking.head(20).iterrows():
        lines.append(
            f"- {r['variavel']}: median_buy={r['median_buy']:.4f} | "
            f"median_sell={r['median_sell']:.4f} | effect={r['effect']:.4f}"
        )
    lines.append("")
    lines.append("Metricas do ML:")
    lines.append(f"- accuracy: {metrics.get('accuracy', float('nan')):.4f}")
    auc = metrics.get("roc_auc", float("nan"))
    lines.append("- roc_auc: nan" if pd.isna(auc) else f"- roc_auc: {auc:.4f}")
    lines.append(f"- treino: {metrics.get('n_train')}")
    lines.append(f"- teste: {metrics.get('n_test')}")
    lines.append(f"- n_features: {metrics.get('n_features')}")
    lines.append(f"- matriz confusao: {metrics.get('confusion_matrix')}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="CSV base de entrada, ex.: 15m")
    ap.add_argument("--tf5", required=True, help="CSV do 5m")
    ap.add_argument("--tf1h", required=True, help="CSV do 1h")
    ap.add_argument("--tf30", required=False, default=None, help="CSV do 30m opcional")
    ap.add_argument("--entradas", required=True, help="CSV/XLSX com entradas")
    ap.add_argument("--saida", required=True, help="Pasta de saída")
    args = ap.parse_args()

    outdir = Path(args.saida)
    outdir.mkdir(parents=True, exist_ok=True)

    base_raw = load_ohlc(Path(args.base))
    tf5_raw = load_ohlc(Path(args.tf5))
    tf1h_raw = load_ohlc(Path(args.tf1h))
    tf30_raw = load_ohlc(Path(args.tf30)) if args.tf30 else None
    entries = load_entries(Path(args.entradas))

    base = build_tf_features(base_raw, "b_")
    tf5 = build_tf_features(tf5_raw, "m5_")
    tf1h = build_tf_features(tf1h_raw, "h1_")
    tf30 = build_tf_features(tf30_raw, "m30_") if tf30_raw is not None else None

    base_tf = infer_tf_minutes(base_raw)
    match_tol = max(1, base_tf // 2)

    matched, unmatched = match_entries_to_base(base, entries, match_tol)
    if matched.empty:
        raise ValueError("Nenhuma entrada casou com o timeframe base.")

    # merge contexto 5m / 1h / 30m
    df = matched.copy()
    df = merge_context(df, tf5, tolerance_min=max(1, infer_tf_minutes(tf5_raw)))
    df = merge_context(df, tf1h, tolerance_min=max(1, infer_tf_minutes(tf1h_raw)))
    if tf30 is not None:
        df = merge_context(df, tf30, tolerance_min=max(1, infer_tf_minutes(tf30_raw)))

    # remover colunas datetime duplicadas de contextos já resolvidos pelo asof
    df = df.sort_values("datetime").reset_index(drop=True)

    features = DEFAULT_FEATURES.copy()
    if tf30 is not None:
        features.extend(OPTIONAL_TF30)
    features = [c for c in features if c in df.columns]

    ranking = make_ranking(df, features)
    metrics, importances, preds = run_ml(df, features)

    df.to_csv(outdir / "01_entradas_casadas_mtf.csv", index=False, encoding="utf-8-sig")
    ranking.to_csv(outdir / "02_ranking_indicadores_mtf.csv", index=False, encoding="utf-8-sig")
    importances.to_csv(outdir / "04_importancias_ml_mtf.csv", index=False, encoding="utf-8-sig")
    preds.to_csv(outdir / "05_predicoes_ml_mtf.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metrics["confusion_matrix"], index=["real_sell", "real_buy"], columns=["pred_sell", "pred_buy"]).to_csv(
        outdir / "05_matriz_confusao_mtf.csv", encoding="utf-8-sig"
    )
    with open(outdir / "06_metricas_ml_mtf.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    write_summary(outdir / "07_resumo_mtf.txt", df, ranking, metrics, len(unmatched))

    if not unmatched.empty:
        unmatched.to_csv(outdir / "08_entradas_nao_casadas.csv", index=False, encoding="utf-8-sig")

    print("Analise V4 multi-timeframe concluida.")
    print(f"Entradas totais: {len(entries)}")
    print(f"Entradas casadas: {len(df)}")
    print(f"Entradas nao casadas: {len(unmatched)}")
    print(f"Timeframe base inferido: {base_tf} min")
    print(f"Tolerancia base: {match_tol} min")
    print(f"Features usadas: {len(features)}")
    print(f"Saida em: {outdir.resolve()}")


if __name__ == "__main__":
    main()
