import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd


# =========================================================
# CONFIGURAÇÃO
# =========================================================
BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\ml_filtrar_original_reconstruido")

TRADES_TEST_CSV = BASE_DIR / "06_trades_teste_com_score_ml.csv"
DATASET_CSV = BASE_DIR / "07_dataset_completo_com_features.csv"

OUT_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\regras_praticas_ml")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# FUNÇÕES
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
            "grupo": label,
            "trades": 0,
            "win_rate": 0.0,
            "pnl_total": 0.0,
            "pnl_medio": 0.0,
            "profit_factor": 0.0,
        }

    pnl = df["pnl_usd"]
    return {
        "grupo": label,
        "trades": int(len(df)),
        "win_rate": round(float((pnl > 0).mean()), 4),
        "pnl_total": round(float(pnl.sum()), 2),
        "pnl_medio": round(float(pnl.mean()), 2),
        "profit_factor": round(float(profit_factor(pnl)), 4),
    }


def analyze_numeric_bands(df: pd.DataFrame, col: str, q: int = 5) -> pd.DataFrame:
    temp = df[[col, "pnl_usd"]].dropna().copy()
    if len(temp) < q * 5:
        return pd.DataFrame()

    try:
        temp["faixa"] = pd.qcut(temp[col], q=q, duplicates="drop")
    except Exception:
        return pd.DataFrame()

    rows = []
    for faixa, g in temp.groupby("faixa", observed=False):
        s = summarize(g, str(faixa))
        s["feature"] = col
        rows.append(s)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["profit_factor", "pnl_total"], ascending=[False, False])
    return out


def analyze_category(df: pd.DataFrame, col: str) -> pd.DataFrame:
    temp = df[[col, "pnl_usd"]].dropna().copy()
    rows = []
    for val, g in temp.groupby(col):
        s = summarize(g, str(val))
        s["feature"] = col
        rows.append(s)

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["profit_factor", "pnl_total"], ascending=[False, False])
    return out


# =========================================================
# MAIN
# =========================================================
def main():
    print("Lendo arquivos...")
    trades = pd.read_csv(TRADES_TEST_CSV)
    dataset = pd.read_csv(DATASET_CSV)

    # garantir datas
    for col in ["entry_time", "exit_time", "datetime"]:
        if col in trades.columns:
            trades[col] = pd.to_datetime(trades[col], errors="coerce")
        if col in dataset.columns:
            dataset[col] = pd.to_datetime(dataset[col], errors="coerce")

    # se já vier completo, seguimos com trades
    df = trades.copy()

    # criar hora/minuto se não existirem
    if "trade_hour" not in df.columns and "entry_time" in df.columns:
        df["trade_hour"] = df["entry_time"].dt.hour
    if "trade_minute" not in df.columns and "entry_time" in df.columns:
        df["trade_minute"] = df["entry_time"].dt.minute
    if "trade_weekday" not in df.columns and "entry_time" in df.columns:
        df["trade_weekday"] = df["entry_time"].dt.weekday

    print(f"Trades no teste: {len(df)}")

    # =====================================================
    # BASELINE
    # =====================================================
    baseline = pd.DataFrame([summarize(df, "baseline_teste")])

    # =====================================================
    # ANÁLISES POR FAIXA
    # =====================================================
    numeric_features = [
        "atr", "k", "d", "bias", "volUsada", "bb_width",
        "dist_ema17", "dist_ema34", "body_ratio", "rsi", "stoch", "ml_score"
    ]

    numeric_reports = []
    for col in numeric_features:
        if col in df.columns:
            rep = analyze_numeric_bands(df, col, q=5)
            if not rep.empty:
                numeric_reports.append(rep)

    numeric_report = pd.concat(numeric_reports, ignore_index=True) if numeric_reports else pd.DataFrame()

    # =====================================================
    # ANÁLISES CATEGÓRICAS
    # =====================================================
    cat_reports = []

    for col in ["trade_hour", "trade_minute", "trade_weekday", "direction"]:
        if col in df.columns:
            rep = analyze_category(df, col)
            if not rep.empty:
                cat_reports.append(rep)

    cat_report = pd.concat(cat_reports, ignore_index=True) if cat_reports else pd.DataFrame()

    # =====================================================
    # TOP SUGESTÕES
    # =====================================================
    suggestions = []

    if not numeric_report.empty:
        best_numeric = (
            numeric_report
            .sort_values(["profit_factor", "pnl_total"], ascending=[False, False])
            .groupby("feature", as_index=False)
            .head(1)
            .reset_index(drop=True)
        )
        suggestions.append(best_numeric)

    if not cat_report.empty:
        best_cat = (
            cat_report
            .sort_values(["profit_factor", "pnl_total"], ascending=[False, False])
            .groupby("feature", as_index=False)
            .head(3)
            .reset_index(drop=True)
        )
        suggestions.append(best_cat)

    suggestions_df = pd.concat(suggestions, ignore_index=True) if suggestions else pd.DataFrame()

    # =====================================================
    # REGRAS MAIS SIMPLES BASEADAS NO SCORE
    # =====================================================
    score_rules = []
    if "ml_score" in df.columns:
        for thr in [0.50, 0.55, 0.60, 0.65]:
            g = df[df["ml_score"] >= thr].copy()
            s = summarize(g, f"ml_score >= {thr}")
            s["threshold"] = thr
            s["cobertura"] = round(len(g) / len(df), 4) if len(df) else 0.0
            score_rules.append(s)

    score_rules_df = pd.DataFrame(score_rules)

    # =====================================================
    # SALVAR
    # =====================================================
    baseline.to_csv(OUT_DIR / "01_baseline.csv", index=False)
    numeric_report.to_csv(OUT_DIR / "02_faixas_numericas.csv", index=False)
    cat_report.to_csv(OUT_DIR / "03_faixas_categoricas.csv", index=False)
    suggestions_df.to_csv(OUT_DIR / "04_melhores_regras_encontradas.csv", index=False)
    score_rules_df.to_csv(OUT_DIR / "05_regras_por_score.csv", index=False)

    print("\nArquivos gerados:")
    print(OUT_DIR / "01_baseline.csv")
    print(OUT_DIR / "02_faixas_numericas.csv")
    print(OUT_DIR / "03_faixas_categoricas.csv")
    print(OUT_DIR / "04_melhores_regras_encontradas.csv")
    print(OUT_DIR / "05_regras_por_score.csv")

    print("\nBaseline:")
    print(baseline.to_string(index=False))

    if not suggestions_df.empty:
        print("\nMelhores regras encontradas:")
        print(suggestions_df.to_string(index=False))

    if not score_rules_df.empty:
        print("\nRegras por score:")
        print(score_rules_df.to_string(index=False))


if __name__ == "__main__":
    main()