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

TRADES_XLSX = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\Entradas realizada.xlsx")
CANDLES_CSV = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\US100M2-.csv")
OUT_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\ml_original_filtrar_entradas")
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70]

def load_trades(xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx_path, sheet_name="Lista de negociações").copy()
    df["Data e hora"] = pd.to_datetime(df["Data e hora"], errors="coerce")
    entradas = df[df["Tipo"].astype(str).str.contains("Entrada", case=False, na=False)].copy()
    saidas = df[df["Tipo"].astype(str).str.contains("Saída|Saida", case=False, na=False)].copy()
    entradas = entradas.rename(columns={"Trade #":"trade_id","Data e hora":"entry_time","Sinal":"entry_signal","Preço USD":"entry_price","Tamanho (qtd)":"qty"})
    saidas = saidas.rename(columns={"Trade #":"trade_id","Data e hora":"exit_time","Sinal":"exit_reason","Preço USD":"exit_price","Lucro e Prejuízo Líquido USD":"pnl_usd","Excursão favorável USD":"mfe_usd","Excursão adversa USD":"mae_usd"})
    trades = entradas[["trade_id","entry_time","entry_signal","entry_price","qty"]].merge(
        saidas[["trade_id","exit_time","exit_reason","exit_price","pnl_usd","mfe_usd","mae_usd"]], on="trade_id", how="inner")
    trades = trades.sort_values("entry_time").reset_index(drop=True)
    trades["direction"] = trades["entry_signal"].map({"BUY":1,"SELL":-1})
    trades["target_win"] = (trades["pnl_usd"] > 0).astype(int)
    trades["hour"] = trades["entry_time"].dt.hour
    trades["minute"] = trades["entry_time"].dt.minute
    trades["weekday"] = trades["entry_time"].dt.weekday
    trades["month"] = trades["entry_time"].dt.month
    return trades

def load_candles(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-16", header=None, names=["datetime","open","high","low","close","volume","spread"]).copy()
    df["datetime"] = pd.to_datetime(df["datetime"], format="%Y.%m.%d %H:%M", errors="coerce")
    for col in ["open","high","low","close","volume","spread"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["datetime","open","high","low","close"]).sort_values("datetime").reset_index(drop=True)

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

def compute_features(c: pd.DataFrame) -> pd.DataFrame:
    c = c.copy()
    c["ema17"] = c["close"].ewm(span=17, adjust=False).mean()
    c["ema34"] = c["close"].ewm(span=34, adjust=False).mean()
    c["ema17_gt_ema34"] = (c["ema17"] > c["ema34"]).astype(int)
    c["dist_ema17"] = c["close"] - c["ema17"]
    c["dist_ema34"] = c["close"] - c["ema34"]
    c["slope_ema17_3"] = c["ema17"] - c["ema17"].shift(3)
    c["slope_ema34_3"] = c["ema34"] - c["ema34"].shift(3)
    sma_bias = c["close"].rolling(25).mean()
    c["bias"] = (c["close"] - sma_bias) / sma_bias * 100
    c["retorno_log"] = np.log(c["close"] / c["close"].shift(1))
    c["vol_atual"] = c["retorno_log"].rolling(30).std()
    c["vol_usada"] = c["vol_atual"].ewm(span=10, adjust=False).mean()
    c["limite_alta"] = c["vol_usada"] * 0.6 * 100
    c["limite_baixa"] = -c["vol_usada"] * 0.6 * 100
    c["filtro_compra_vol"] = (c["bias"] <= c["limite_baixa"]).astype(int)
    c["filtro_venda_vol"] = (c["bias"] >= c["limite_alta"]).astype(int)
    c["rsi14"] = rsi(c["close"], 14)
    rsi_min = c["rsi14"].rolling(14).min()
    rsi_max = c["rsi14"].rolling(14).max()
    c["stoch_rsi"] = 100 * (c["rsi14"] - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
    c["k"] = c["stoch_rsi"].rolling(3).mean()
    c["d"] = c["k"].rolling(3).mean()
    c["k_minus_d"] = c["k"] - c["d"]
    c["stoch_caindo"] = (c["k"].shift(1) > c["k"].shift(2)).astype(int)
    c["stoch_subindo"] = (c["k"].shift(1) < c["k"].shift(2)).astype(int)
    cross_up = ((c["k"] > c["d"]) & (c["k"].shift(1) <= c["d"].shift(1)))
    cross_dn = ((c["k"] < c["d"]) & (c["k"].shift(1) >= c["d"].shift(1)))
    c["cross_up_recent"] = cross_up.astype(int).rolling(4, min_periods=1).max().fillna(0).astype(int)
    c["cross_dn_recent"] = cross_dn.astype(int).rolling(4, min_periods=1).max().fillna(0).astype(int)
    c["atr14"] = atr(c, 14)
    c["range"] = c["high"] - c["low"]
    c["body"] = (c["close"] - c["open"]).abs()
    c["body_ratio"] = c["body"] / c["range"].replace(0, np.nan)
    c["upper_wick"] = c["high"] - c[["open","close"]].max(axis=1)
    c["lower_wick"] = c[["open","close"]].min(axis=1) - c["low"]
    basis = c["close"].rolling(20).mean()
    dev = c["close"].rolling(20).std()
    c["bb_width"] = ((basis + 2*dev) - (basis - 2*dev)) / basis.replace(0, np.nan)
    toque = (c["low"] <= c["ema17"]) & (c["high"] >= c["ema17"])
    c["compra_original"] = (toque & (c["cross_up_recent"] == 1) & (c["stoch_caindo"] == 1) & (c["ema17"] > c["ema34"]) & (c["filtro_compra_vol"] == 1)).astype(int)
    c["venda_original"] = (toque & (c["cross_dn_recent"] == 1) & (c["stoch_subindo"] == 1) & (c["ema17"] < c["ema34"]) & (c["filtro_venda_vol"] == 1)).astype(int)
    return c

def profit_factor(pnl: pd.Series) -> float:
    gp = pnl[pnl > 0].sum()
    gl = -pnl[pnl < 0].sum()
    if gl == 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl

def summarize(df: pd.DataFrame, label: str) -> dict:
    if len(df) == 0:
        return {"cenario":label,"trades":0,"win_rate":0.0,"pnl_total":0.0,"pnl_medio":0.0,"profit_factor":0.0}
    pnl = df["pnl_usd"]
    return {"cenario":label,"trades":int(len(df)),"win_rate":round(float((pnl > 0).mean()),4),"pnl_total":round(float(pnl.sum()),2),"pnl_medio":round(float(pnl.mean()),2),"profit_factor":round(float(profit_factor(pnl)),4)}

def main():
    trades = load_trades(TRADES_XLSX)
    candles = compute_features(load_candles(CANDLES_CSV))
    merged = pd.merge_asof(
        trades.sort_values("entry_time"), candles.sort_values("datetime"),
        left_on="entry_time", right_on="datetime", direction="backward", tolerance=pd.Timedelta("2min")
    )
    merged["covered_by_candles"] = merged["datetime"].notna().astype(int)
    work = merged.dropna(subset=["datetime"]).copy()
    work = work.rename(columns={"hour_x":"trade_hour","minute_x":"trade_minute","weekday_x":"trade_weekday","month_x":"trade_month"})
    feature_cols = [
        "direction","entry_price","trade_hour","trade_minute","trade_weekday","trade_month",
        "ema17","ema34","ema17_gt_ema34","bias","vol_usada","limite_alta","limite_baixa","filtro_compra_vol","filtro_venda_vol",
        "rsi14","stoch_rsi","k","d","k_minus_d","cross_up_recent","cross_dn_recent","stoch_caindo","stoch_subindo",
        "compra_original","venda_original","dist_ema17","dist_ema34","slope_ema17_3","slope_ema34_3",
        "atr14","range","body","body_ratio","upper_wick","lower_wick","bb_width","open","high","low","close","volume"
    ]
    work = work.dropna(subset=feature_cols).sort_values("entry_time").reset_index(drop=True)
    split_idx = int(len(work) * 0.7)
    train = work.iloc[:split_idx].copy()
    test = work.iloc[split_idx:].copy()
    X_train = train[feature_cols]
    y_train = train["target_win"]
    X_test = test[feature_cols]
    y_test = test["target_win"]
    pre_std = ColumnTransformer([("num", Pipeline([("imp", SimpleImputer(strategy="median")),("sc", StandardScaler())]), feature_cols)], remainder="drop")
    pre_no_std = ColumnTransformer([("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), feature_cols)], remainder="drop")
    models = {
        "logistic_regression": Pipeline([("prep", pre_std),("model", LogisticRegression(max_iter=3000, class_weight="balanced"))]),
        "random_forest": Pipeline([("prep", pre_no_std),("model", RandomForestClassifier(n_estimators=500, max_depth=8, min_samples_leaf=6, random_state=42, class_weight="balanced_subsample", n_jobs=-1))]),
    }
    rows = []
    best_name, best_model, best_auc, best_probs = None, None, -1.0, None
    for name, model in models.items():
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_test)[:, 1]
        pred = (probs >= 0.5).astype(int)
        auc = float(roc_auc_score(y_test, probs))
        rows.append({"modelo":name,"train_trades":len(train),"test_trades":len(test),"accuracy":round(float(accuracy_score(y_test, pred)),4),"precision":round(float(precision_score(y_test, pred, zero_division=0)),4),"recall":round(float(recall_score(y_test, pred, zero_division=0)),4),"auc":round(auc,4)})
        if auc > best_auc:
            best_name, best_model, best_auc, best_probs = name, model, auc, probs
    test = test.copy()
    test["ml_score"] = best_probs
    cenarios = [summarize(test, "original_teste")]
    for thr in THRESHOLDS:
        kept = test[test["ml_score"] >= thr].copy()
        s = summarize(kept, f"original_filtrado_ml_{thr:.2f}")
        s["threshold"] = thr
        s["cobertura"] = round(len(kept) / len(test), 4) if len(test) else 0.0
        cenarios.append(s)
    feat_imp = pd.DataFrame({"feature": feature_cols})
    if best_name == "random_forest":
        feat_imp["importance"] = best_model.named_steps["model"].feature_importances_
    else:
        feat_imp["importance"] = np.abs(best_model.named_steps["model"].coef_[0])
    feat_imp = feat_imp.sort_values("importance", ascending=False)
    score_bins = pd.cut(test["ml_score"], bins=[0.0,0.4,0.5,0.6,0.7,1.0], include_lowest=True)
    faixas = test.groupby(score_bins, observed=False).agg(trades=("trade_id","count"), win_rate=("target_win","mean"), pnl_total=("pnl_usd","sum"), pnl_medio=("pnl_usd","mean")).reset_index()
    faixas["win_rate"] = faixas["win_rate"].round(4)
    faixas["pnl_total"] = faixas["pnl_total"].round(2)
    faixas["pnl_medio"] = faixas["pnl_medio"].round(2)
    sugestoes = []
    for col in ["trade_hour","bias","vol_usada","rsi14","k","d","body_ratio","atr14","dist_ema17","bb_width"]:
        winners = train.loc[train["target_win"] == 1, col].dropna()
        losers = train.loc[train["target_win"] == 0, col].dropna()
        if len(winners) and len(losers):
            sugestoes.append({"feature":col,"media_winners":round(float(winners.mean()),4),"media_losers":round(float(losers.mean()),4),"mediana_winners":round(float(winners.median()),4),"mediana_losers":round(float(losers.median()),4)})
    sugestoes = pd.DataFrame(sugestoes)
    cobertura = pd.DataFrame([{
        "trades_total_planilha": len(trades),
        "trades_com_contexto_candles": int(merged["covered_by_candles"].sum()),
        "percentual_coberto": round(float(merged["covered_by_candles"].mean()), 4),
        "inicio_trades": trades["entry_time"].min(),
        "fim_trades": trades["entry_time"].max(),
        "inicio_candles": candles["datetime"].min(),
        "fim_candles": candles["datetime"].max(),
        "melhor_modelo": best_name,
        "melhor_auc": round(float(best_auc), 4),
    }])
    pd.DataFrame(rows).to_csv(OUT_DIR / "01_relatorio_modelos.csv", index=False)
    pd.DataFrame(cenarios).to_csv(OUT_DIR / "02_relatorio_cenarios_ml.csv", index=False)
    feat_imp.to_csv(OUT_DIR / "03_importancia_variaveis.csv", index=False)
    faixas.to_csv(OUT_DIR / "04_faixas_de_score.csv", index=False)
    sugestoes.to_csv(OUT_DIR / "05_sugestoes_regras_praticas.csv", index=False)
    cobertura.to_csv(OUT_DIR / "06_cobertura_dados.csv", index=False)
    test.sort_values("entry_time").to_csv(OUT_DIR / "07_trades_teste_com_score_ml.csv", index=False)
    work.sort_values("entry_time").to_csv(OUT_DIR / "08_dataset_completo_com_features.csv", index=False)
    print("Saída em:", OUT_DIR)
    print("\nCobertura:")
    print(cobertura.to_string(index=False))
    print("\nModelos:")
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nCenários no conjunto de teste:")
    print(pd.DataFrame(cenarios).to_string(index=False))
    print("\nTop 12 variáveis:")
    print(feat_imp.head(12).to_string(index=False))
    print("\nFaixas de score:")
    print(faixas.to_string(index=False))

if __name__ == "__main__":
    main()