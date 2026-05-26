import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier


# =========================================================
# CONFIGURAÇÃO
# =========================================================
BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\saida_operacional_original")

TRADES_CSV = BASE_DIR / "trades_original_reconstruidos.csv"
CANDLES_CSV = BASE_DIR / "candles_com_features.csv"

OUT_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\ml_filtrar_original_reconstruido")
OUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70]


# =========================================================
# LEITURA
# =========================================================
def load_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce")

    df["target_win"] = (df["pnl_usd"] > 0).astype(int)
    df["trade_hour"] = df["entry_time"].dt.hour
    df["trade_minute"] = df["entry_time"].dt.minute
    df["trade_weekday"] = df["entry_time"].dt.weekday
    df["trade_month"] = df["entry_time"].dt.month
    df["direction_num"] = df["direction"].map({"BUY": 1, "SELL": -1})

    return df


def load_candles(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df.sort_values("datetime").reset_index(drop=True)


# =========================================================
# MÉTRICAS
# =========================================================
def profit_factor(pnl: pd.Series) -> float:
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    if gross_loss == 0:
        return np.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def summarize(df: pd.DataFrame, label: str) -> dict:
    if len(df) == 0:
        return {
            "cenario": label,
            "trades": 0,
            "win_rate": 0.0,
            "pnl_total": 0.0,
            "pnl_medio": 0.0,
            "profit_factor": 0.0,
        }

    pnl = df["pnl_usd"]
    return {
        "cenario": label,
        "trades": int(len(df)),
        "win_rate": round(float((pnl > 0).mean()), 4),
        "pnl_total": round(float(pnl.sum()), 2),
        "pnl_medio": round(float(pnl.mean()), 2),
        "profit_factor": round(float(profit_factor(pnl)), 4),
    }


# =========================================================
# MAIN
# =========================================================
def main():
    print("Lendo trades reconstruídos...")
    trades = load_trades(TRADES_CSV)

    print("Lendo candles com features...")
    candles = load_candles(CANDLES_CSV)

    print("Casando cada trade com o candle de entrada...")
    merged = pd.merge_asof(
        trades.sort_values("entry_time"),
        candles.sort_values("datetime"),
        left_on="entry_time",
        right_on="datetime",
        direction="backward",
        tolerance=pd.Timedelta("2min"),
    )

    feature_cols = [
        "direction_num",
        "entry_price",
        "trade_hour",
        "trade_minute",
        "trade_weekday",
        "trade_month",

        "ema17",
        "ema34",
        "bias",
        "volUsada",
        "limiteAlta",
        "limiteBaixa",

        "rsi",
        "stoch",
        "k",
        "d",

        "crossUpRecent",
        "crossDownRecent",
        "stochCaindo",
        "stochSubindo",

        "toqueNaMedia",
        "filtroCompraVol",
        "filtroVendaVol",

        "atr",
        "range",
        "body",
        "body_ratio",
        "bb_width",

        "open",
        "high",
        "low",
        "close",
        "volume",

        "ema17_gt_ema34",
        "dist_ema17",
        "dist_ema34",
        "slope_ema17_3",
        "slope_ema34_3",
        "upper_wick",
        "lower_wick",
    ]

    for col in feature_cols:
        if col not in merged.columns:
            merged[col] = np.nan

    work = merged.dropna(subset=["datetime"]).copy()
    work = work.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)

    bool_cols = [
        "crossUpRecent", "crossDownRecent", "stochCaindo", "stochSubindo",
        "toqueNaMedia", "filtroCompraVol", "filtroVendaVol"
    ]
    for col in bool_cols:
        if col in work.columns:
            work[col] = work[col].astype(float)

    split_idx = int(len(work) * 0.7)
    train = work.iloc[:split_idx].copy()
    test = work.iloc[split_idx:].copy()

    X_train = train[feature_cols]
    y_train = train["target_win"]
    X_test = test[feature_cols]
    y_test = test["target_win"]

    pre_std = ColumnTransformer(
        transformers=[
            ("num", Pipeline([
                ("imp", SimpleImputer(strategy="median")),
                ("sc", StandardScaler()),
            ]), feature_cols)
        ],
        remainder="drop",
    )

    pre_no_std = ColumnTransformer(
        transformers=[
            ("num", Pipeline([
                ("imp", SimpleImputer(strategy="median")),
            ]), feature_cols)
        ],
        remainder="drop",
    )

    models = {
        "logistic_regression": Pipeline([
            ("prep", pre_std),
            ("model", LogisticRegression(max_iter=3000, class_weight="balanced"))
        ]),
        "random_forest": Pipeline([
            ("prep", pre_no_std),
            ("model", RandomForestClassifier(
                n_estimators=500,
                max_depth=8,
                min_samples_leaf=6,
                random_state=42,
                class_weight="balanced_subsample",
                n_jobs=-1
            ))
        ]),
    }

    model_rows = []
    best_name = None
    best_model = None
    best_auc = -np.inf
    best_probs = None

    print("Treinando modelos...")
    for name, model in models.items():
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]
        pred = (probs >= 0.5).astype(int)

        row = {
            "modelo": name,
            "train_trades": len(train),
            "test_trades": len(test),
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
            "auc": round(float(roc_auc_score(y_test, probs)), 4),
        }
        model_rows.append(row)

        if row["auc"] > best_auc:
            best_auc = row["auc"]
            best_name = name
            best_model = model
            best_probs = probs

    print(f"Melhor modelo: {best_name} | AUC: {best_auc:.4f}")

    test = test.copy()
    test["ml_score"] = best_probs

    scenario_rows = [summarize(test, "original_reconstruido_teste")]

    for thr in THRESHOLDS:
        kept = test[test["ml_score"] >= thr].copy()
        s = summarize(kept, f"original_filtrado_ml_{thr:.2f}")
        s["threshold"] = thr
        s["cobertura"] = round(len(kept) / len(test), 4) if len(test) else 0.0
        scenario_rows.append(s)

    # =========================================================
    # IMPORTÂNCIA DAS VARIÁVEIS - BLOCO CORRIGIDO
    # =========================================================
    if best_name == "random_forest":
        importances = best_model.named_steps["model"].feature_importances_
    else:
        importances = np.abs(best_model.named_steps["model"].coef_[0])

    n = min(len(feature_cols), len(importances))

    feat_imp = pd.DataFrame({
        "feature": feature_cols[:n],
        "importance": importances[:n]
    }).sort_values("importance", ascending=False)

    # =========================================================
    # FAIXAS DE SCORE
    # =========================================================
    score_bins = pd.cut(
        test["ml_score"],
        bins=[0.0, 0.4, 0.5, 0.6, 0.7, 1.0],
        include_lowest=True
    )
    score_band_report = (
        test.groupby(score_bins, observed=False)
            .agg(
                trades=("entry_time", "count"),
                win_rate=("target_win", "mean"),
                pnl_total=("pnl_usd", "sum"),
                pnl_medio=("pnl_usd", "mean"),
            )
            .reset_index()
    )
    score_band_report["win_rate"] = score_band_report["win_rate"].round(4)
    score_band_report["pnl_total"] = score_band_report["pnl_total"].round(2)
    score_band_report["pnl_medio"] = score_band_report["pnl_medio"].round(2)

    # =========================================================
    # SUGESTÕES DE REGRAS PRÁTICAS
    # =========================================================
    suggested = []
    rule_cols = [
        "trade_hour", "bias", "volUsada", "rsi", "k", "d",
        "body_ratio", "atr", "dist_ema17", "dist_ema34", "bb_width"
    ]
    for col in rule_cols:
        if col in train.columns:
            winners = train.loc[train["target_win"] == 1, col].dropna()
            losers = train.loc[train["target_win"] == 0, col].dropna()
            if len(winners) and len(losers):
                suggested.append({
                    "feature": col,
                    "media_winners": round(float(winners.mean()), 4),
                    "media_losers": round(float(losers.mean()), 4),
                    "mediana_winners": round(float(winners.median()), 4),
                    "mediana_losers": round(float(losers.median()), 4),
                })
    suggested_df = pd.DataFrame(suggested)

    # =========================================================
    # SALVAR
    # =========================================================
    pd.DataFrame(model_rows).to_csv(OUT_DIR / "01_relatorio_modelos.csv", index=False)
    pd.DataFrame(scenario_rows).to_csv(OUT_DIR / "02_relatorio_cenarios_ml.csv", index=False)
    feat_imp.to_csv(OUT_DIR / "03_importancia_variaveis.csv", index=False)
    score_band_report.to_csv(OUT_DIR / "04_faixas_de_score.csv", index=False)
    suggested_df.to_csv(OUT_DIR / "05_sugestoes_regras_praticas.csv", index=False)
    test.sort_values("entry_time").to_csv(OUT_DIR / "06_trades_teste_com_score_ml.csv", index=False)
    work.sort_values("entry_time").to_csv(OUT_DIR / "07_dataset_completo_com_features.csv", index=False)

    print("\nArquivos gerados:")
    print(OUT_DIR / "01_relatorio_modelos.csv")
    print(OUT_DIR / "02_relatorio_cenarios_ml.csv")
    print(OUT_DIR / "03_importancia_variaveis.csv")
    print(OUT_DIR / "04_faixas_de_score.csv")
    print(OUT_DIR / "05_sugestoes_regras_praticas.csv")
    print(OUT_DIR / "06_trades_teste_com_score_ml.csv")
    print(OUT_DIR / "07_dataset_completo_com_features.csv")

    print("\nModelos:")
    print(pd.DataFrame(model_rows).to_string(index=False))

    print("\nCenários:")
    print(pd.DataFrame(scenario_rows).to_string(index=False))

    print("\nTop 15 variáveis:")
    print(feat_imp.head(15).to_string(index=False))

    print("\nFaixas de score:")
    print(score_band_report.to_string(index=False))


if __name__ == "__main__":
    main()