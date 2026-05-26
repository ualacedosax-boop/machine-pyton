
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Versão v3:
- usa apenas as melhores variáveis
- reduz overfitting
- gera score final BUY/SELL mais limpo
- ML com poucas features e tratamento robusto
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


# =========================
# UTIL
# =========================
def normalizar_texto(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace(" ", "_").replace("-", "_").replace("/", "_")
    return s


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalizar_texto(c) for c in df.columns]
    return df


# =========================
# LEITURA
# =========================
def carregar_ohlc(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        try:
            df = pd.read_csv(path)
            if len(df.columns) == 1:
                df = pd.read_csv(path, sep=None, engine="python")
        except Exception:
            df = pd.read_csv(path, sep=None, engine="python")

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

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    elif "time" in df.columns and "date" not in df.columns:
        df["datetime"] = pd.to_datetime(df["time"], errors="coerce")
    elif "date" in df.columns and "time" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["date"].astype(str).str.strip() + " " + df["time"].astype(str).str.strip(),
            errors="coerce"
        )
    elif "date" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        raise ValueError("Nao encontrei coluna datetime nem combinacao date + time no arquivo OHLC.")

    required = ["datetime", "open", "high", "low", "close"]
    faltando = [c for c in required if c not in df.columns]
    if faltando:
        raise ValueError(f"Faltam colunas no OHLC: {faltando}")

    if "volume" not in df.columns:
        df["volume"] = np.nan

    try:
        if getattr(df["datetime"].dtype, "tz", None) is not None:
            df["datetime"] = df["datetime"].dt.tz_convert(None)
    except Exception:
        pass

    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["datetime", "open", "high", "low", "close"]).copy()
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)
    return df[["datetime", "open", "high", "low", "close", "volume"]]


def carregar_entradas(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        try:
            df = pd.read_csv(path)
            if len(df.columns) == 1:
                df = pd.read_csv(path, sep=None, engine="python")
        except Exception:
            df = pd.read_csv(path, sep=None, engine="python")

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
            df["datetime"] = pd.to_datetime(
                df["date"].astype(str).str.strip() + " " + df["time"].astype(str).str.strip(),
                errors="coerce"
            )
        else:
            raise ValueError("Arquivo de entradas precisa ter datetime ou date + time.")

    if "side" not in df.columns:
        raise ValueError("Arquivo de entradas precisa ter coluna side com BUY/SELL.")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    try:
        if getattr(df["datetime"].dtype, "tz", None) is not None:
            df["datetime"] = df["datetime"].dt.tz_convert(None)
    except Exception:
        pass

    df["side"] = df["side"].astype(str).str.upper().str.strip()
    df = df[df["side"].isin(["BUY", "SELL"])].copy()
    df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    return df[["datetime", "side"]]


# =========================
# INDICADORES
# =========================
def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(period).mean()
    mad = (tp - sma_tp).abs().rolling(period).mean()
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()


def adicionar_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h = df["high"]
    l = df["low"]
    o = df["open"]

    df["ret_1"] = c.pct_change(1) * 100
    df["ret_2"] = c.pct_change(2) * 100
    df["ret_3"] = c.pct_change(3) * 100
    df["ret_5"] = c.pct_change(5) * 100

    for p in [5, 8, 9]:
        sma = c.rolling(p).mean()
        em = ema(c, p)
        df[f"sma_{p}"] = sma
        df[f"ema_{p}"] = em
        df[f"dist_sma_{p}"] = c - sma
        df[f"dist_ema_{p}"] = c - em

    df["slope_ema_5_5"] = df["ema_5"] - df["ema_5"].shift(5)

    for p in [7, 9, 14, 21]:
        df[f"rsi_{p}"] = rsi(c, p)

    atr14 = atr(h, l, c, 14)
    df["atr_14"] = atr14
    df["atr_pct"] = (atr14 / c.replace(0, np.nan)) * 100

    roll_high_5 = h.rolling(5).max()
    roll_low_5 = l.rolling(5).min()
    roll_high_10 = h.rolling(10).max()
    roll_low_10 = l.rolling(10).min()

    df["dist_top_5"] = roll_high_5 - c
    df["dist_bottom_5"] = c - roll_low_5
    df["pos_range_5"] = (c - roll_low_5) / (roll_high_5 - roll_low_5).replace(0, np.nan)

    df["dist_top_10"] = roll_high_10 - c
    df["dist_bottom_10"] = c - roll_low_10
    df["pos_range_10"] = (c - roll_low_10) / (roll_high_10 - roll_low_10).replace(0, np.nan)

    df["body"] = c - o
    df["range"] = h - l
    df["upper_wick"] = h - np.maximum(c, o)
    df["lower_wick"] = np.minimum(c, o) - l
    df["cci_20"] = cci(h, l, c, 20)

    return df


# =========================
# MATCH ENTRADAS
# =========================
def inferir_timeframe_minutos(ohlc: pd.DataFrame) -> int:
    diffs = ohlc["datetime"].diff().dropna().dt.total_seconds() / 60.0
    if diffs.empty:
        return 1
    return int(round(float(diffs.mode().iloc[0])))


def casar_entradas(ohlc: pd.DataFrame, entradas: pd.DataFrame, tolerancia_min: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = ohlc.sort_values("datetime").copy()
    ent = entradas.sort_values("datetime").copy()

    matched_rows = []
    unmatched_rows = []

    times = base["datetime"].tolist()
    # merge_asof usa candle anterior mais próximo
    m = pd.merge_asof(
        ent,
        base,
        on="datetime",
        direction="backward",
        tolerance=pd.Timedelta(minutes=tolerancia_min),
    )

    for _, row in m.iterrows():
        if pd.isna(row["open"]):
            unmatched_rows.append({"datetime": row["datetime"], "side": row["side"]})
        else:
            matched_rows.append(row.to_dict())

    return pd.DataFrame(matched_rows), pd.DataFrame(unmatched_rows)


# =========================
# RANKING + SCORE
# =========================
TOP_FEATURES = [
    "ret_3",
    "dist_top_10",
    "ret_5",
    "dist_top_5",
    "rsi_7",
    "pos_range_5",
    "rsi_9",
    "pos_range_10",
    "rsi_14",
    "atr_14",
    "atr_pct",
    "cci_20",
    "slope_ema_5_5",
    "dist_sma_8",
    "dist_sma_9",
]


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


def gerar_ranking(amostra: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in TOP_FEATURES:
        if col not in amostra.columns:
            continue
        b = pd.to_numeric(amostra.loc[amostra["side"] == "BUY", col], errors="coerce")
        s = pd.to_numeric(amostra.loc[amostra["side"] == "SELL", col], errors="coerce")
        if b.notna().sum() < 3 or s.notna().sum() < 3:
            continue
        rows.append(
            {
                "variavel": col,
                "median_buy": float(np.nanmedian(b)),
                "median_sell": float(np.nanmedian(s)),
                "effect": robust_effect(b, s),
                "abs_effect": abs(robust_effect(b, s)),
            }
        )
    out = pd.DataFrame(rows).sort_values("abs_effect", ascending=False).reset_index(drop=True)
    return out


def _norm_by_side_direction(series: pd.Series, side_positive_for_buy: bool = True) -> pd.Series:
    med = np.nanmedian(series)
    iqr = np.nanpercentile(series, 75) - np.nanpercentile(series, 25)
    if iqr == 0 or np.isnan(iqr):
        iqr = np.nanstd(series)
    if iqr == 0 or np.isnan(iqr):
        iqr = 1.0
    z = (series - med) / iqr
    return z if side_positive_for_buy else -z


def adicionar_score(amostra: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = amostra.copy()

    componentes = {
        "ret_3": _norm_by_side_direction(pd.to_numeric(df["ret_3"], errors="coerce"), True),
        "ret_5": _norm_by_side_direction(pd.to_numeric(df["ret_5"], errors="coerce"), True),
        "dist_top_10": _norm_by_side_direction(pd.to_numeric(df["dist_top_10"], errors="coerce"), True),
        "dist_top_5": _norm_by_side_direction(pd.to_numeric(df["dist_top_5"], errors="coerce"), True),
        "rsi_7": _norm_by_side_direction(pd.to_numeric(df["rsi_7"], errors="coerce"), False),
        "rsi_9": _norm_by_side_direction(pd.to_numeric(df["rsi_9"], errors="coerce"), False),
        "pos_range_5": _norm_by_side_direction(pd.to_numeric(df["pos_range_5"], errors="coerce"), False),
        "pos_range_10": _norm_by_side_direction(pd.to_numeric(df["pos_range_10"], errors="coerce"), False),
        "slope_ema_5_5": _norm_by_side_direction(pd.to_numeric(df["slope_ema_5_5"], errors="coerce"), True),
        "dist_sma_8": _norm_by_side_direction(pd.to_numeric(df["dist_sma_8"], errors="coerce"), True),
    }

    comp_df = pd.DataFrame(componentes)
    score_buy = comp_df.mean(axis=1)
    score_sell = -score_buy

    df["score_buy"] = score_buy
    df["score_sell"] = score_sell
    df["score_operacional"] = np.where(df["side"] == "BUY", score_buy, score_sell)
    df["score_predito_side"] = np.where(score_buy >= score_sell, "BUY", "SELL")
    df["score_acertou"] = (df["score_predito_side"] == df["side"]).astype(int)

    comp_df.insert(0, "side_real", df["side"].values)
    comp_df.insert(0, "datetime", df["datetime"].values)
    comp_df["score_buy"] = score_buy
    comp_df["score_sell"] = score_sell
    comp_df["score_predito_side"] = df["score_predito_side"].values
    comp_df["score_acertou"] = df["score_acertou"].values

    return df, comp_df


# =========================
# ML V3
# =========================
ML_FEATURES = [
    "ret_3",
    "ret_5",
    "dist_top_10",
    "dist_top_5",
    "rsi_7",
    "pos_range_5",
    "rsi_9",
    "pos_range_10",
    "rsi_14",
    "atr_14",
    "atr_pct",
    "cci_20",
    "slope_ema_5_5",
    "dist_sma_8",
    "dist_sma_9",
    "score_buy",
    "score_sell",
]


def rodar_ml(amostra: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    df = amostra.copy()

    features = [c for c in ML_FEATURES if c in df.columns]
    X = df[features].copy()
    y = df["side"].map({"SELL": 0, "BUY": 1}).astype(int)

    # remove features constantes
    keep = []
    for c in X.columns:
        vals = pd.to_numeric(X[c], errors="coerce")
        if vals.nunique(dropna=True) > 1:
            keep.append(c)
    X = X[keep]

    # split temporal 65/35
    n = len(df)
    n_train = max(10, int(round(n * 0.65)))
    n_train = min(n_train, n - 2)

    X_train = X.iloc[:n_train].copy()
    X_test = X.iloc[n_train:].copy()
    y_train = y.iloc[:n_train].copy()
    y_test = y.iloc[n_train:].copy()

    imp = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(imp.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_test_imp = pd.DataFrame(imp.transform(X_test), columns=X_test.columns, index=X_test.index)

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=3,
        min_samples_leaf=2,
        random_state=42,
        class_weight="balanced_subsample",
    )
    clf.fit(X_train_imp, y_train)

    pred = clf.predict(X_test_imp)
    if hasattr(clf, "predict_proba"):
        proba_buy = clf.predict_proba(X_test_imp)[:, 1]
    else:
        proba_buy = np.full(len(X_test_imp), np.nan)

    acc = float(accuracy_score(y_test, pred))
    try:
        auc = float(roc_auc_score(y_test, proba_buy)) if len(np.unique(y_test)) > 1 else float("nan")
    except Exception:
        auc = float("nan")

    rep = classification_report(
        y_test,
        pred,
        labels=[0, 1],
        target_names=["SELL", "BUY"],
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, pred, labels=[0, 1])

    importancias = pd.DataFrame(
        {
            "feature": X_train_imp.columns,
            "importance": clf.feature_importances_,
        }
    ).sort_values("importance", ascending=False).reset_index(drop=True)

    preds = pd.DataFrame(
        {
            "datetime": df.iloc[n_train:]["datetime"].values,
            "side_real": df.iloc[n_train:]["side"].values,
            "y_real": y_test.values,
            "y_pred": pred,
            "side_pred": np.where(pred == 1, "BUY", "SELL"),
            "proba_buy": proba_buy,
        }
    )
    preds["acertou"] = (preds["side_real"] == preds["side_pred"]).astype(int)

    metricas = {
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
    return metricas, importancias, preds


# =========================
# RESUMO
# =========================
def escrever_resumo(path: Path, amostra: pd.DataFrame, ranking: pd.DataFrame, metricas: dict) -> None:
    lines = []
    lines.append("RESUMO DA ANALISE V3")
    lines.append("")
    lines.append(f"Total de entradas: {len(amostra)}")
    lines.append(f"BUY: {(amostra['side'] == 'BUY').sum()}")
    lines.append(f"SELL: {(amostra['side'] == 'SELL').sum()}")
    lines.append("")
    lines.append("Top variaveis por diferenca BUY x SELL:")
    for _, r in ranking.head(15).iterrows():
        lines.append(
            f"- {r['variavel']}: median_buy={r['median_buy']:.4f} | "
            f"median_sell={r['median_sell']:.4f} | effect={r['effect']:.4f}"
        )
    lines.append("")
    lines.append("Metricas do ML:")
    lines.append(f"- accuracy: {metricas.get('accuracy', float('nan')):.4f}")
    auc = metricas.get("roc_auc", float("nan"))
    if pd.isna(auc):
        lines.append("- roc_auc: nan")
    else:
        lines.append(f"- roc_auc: {auc:.4f}")
    lines.append(f"- treino: {metricas.get('n_train')}")
    lines.append(f"- teste: {metricas.get('n_test')}")
    lines.append(f"- n_features: {metricas.get('n_features')}")
    lines.append(f"- matriz confusao: {metricas.get('confusion_matrix')}")

    path.write_text("\n".join(lines), encoding="utf-8")


# =========================
# MAIN
# =========================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ohlc", required=True, help="Arquivo OHLC CSV/XLSX")
    parser.add_argument("--entradas", required=True, help="Arquivo de entradas CSV/XLSX")
    parser.add_argument("--saida", required=True, help="Pasta de saída")
    args = parser.parse_args()

    ohlc_path = Path(args.ohlc)
    entradas_path = Path(args.entradas)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    ohlc = carregar_ohlc(ohlc_path)
    entradas = carregar_entradas(entradas_path)
    ohlc = adicionar_indicadores(ohlc)

    tf = inferir_timeframe_minutos(ohlc)
    tolerancia = max(1, tf // 2)

    amostra, nao_casadas = casar_entradas(ohlc, entradas, tolerancia)
    if amostra.empty:
        raise ValueError("Nenhuma entrada foi casada com o OHLC. Verifique datas e timezone.")

    ranking = gerar_ranking(amostra)
    amostra_score, comp_score = adicionar_score(amostra)
    metricas, importancias, preds = rodar_ml(amostra_score)

    # Salva
    amostra.to_csv(saida / "01_entradas_casadas.csv", index=False, encoding="utf-8-sig")
    amostra_score.to_csv(saida / "01b_entradas_com_score.csv", index=False, encoding="utf-8-sig")
    ranking.to_csv(saida / "02_ranking_indicadores.csv", index=False, encoding="utf-8-sig")
    comp_score.to_csv(saida / "02b_componentes_score.csv", index=False, encoding="utf-8-sig")
    ohlc.to_csv(saida / "03_dataset_completo_indicadores.csv", index=False, encoding="utf-8-sig")
    importancias.to_csv(saida / "04_importancias_ml.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(metricas["confusion_matrix"], index=["real_sell", "real_buy"], columns=["pred_sell", "pred_buy"]).to_csv(
        saida / "05_matriz_confusao.csv", encoding="utf-8-sig"
    )
    preds.to_csv(saida / "05b_predicoes_ml.csv", index=False, encoding="utf-8-sig")
    with open(saida / "06_metricas_ml.json", "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    escrever_resumo(saida / "07_resumo.txt", amostra_score, ranking, metricas)

    if not nao_casadas.empty:
        nao_casadas.to_csv(saida / "08_entradas_nao_casadas.csv", index=False, encoding="utf-8-sig")

    print("Análise V3 concluída.")
    print(f"Entradas totais: {len(entradas)}")
    print(f"Entradas casadas: {len(amostra)}")
    print(f"Entradas não casadas: {len(entradas) - len(amostra)}")
    print(f"Timeframe inferido: {tf} min")
    print(f"Tolerância usada: {tolerancia} min")
    print(f"Saída em: {saida.resolve()}")


if __name__ == "__main__":
    main()
