from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor, simular_trade


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARQ_RANKING = SAIDA_DIR / f"ml_seletor_diario_230_250_ranking_{STAMP}.csv"
ARQ_TRADES = SAIDA_DIR / f"ml_seletor_diario_230_250_trades_{STAMP}.csv"

HORARIOS = ["03:46", "03:48", "03:50", "10:26", "10:28", "10:30", "20:52", "20:54", "20:56", "20:58"]
FEATURES_NUM = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "ema17",
    "ema34",
    "ema200",
    "sma17",
    "sma34",
    "macd",
    "macd_signal",
    "roc5",
    "roc10",
    "prev_roc5",
    "body",
    "ema_gap",
    "vwap",
    "rsi14",
    "di_plus",
    "di_minus",
    "adx14",
    "dmi_gap",
    "dist_ema17",
    "dist_ema34",
    "dist_ema200",
    "dist_vwap",
    "macd_gap",
]
FEATURES_CAT = ["hhmm", "dow", "direcao"]


def metricas(trades, dias=365):
    if trades.empty:
        return 0, 0.0, 0.0, 0.0, 0.0, 0
    fim = trades["datahora_entrada"].max()
    base = trades[trades["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return 0, 0.0, 0.0, 0.0, 0.0, 0
    p = base["pontos"].astype(float)
    return (
        int(len(base)),
        float((p > 0).mean() * 100),
        float(p.sum()),
        max_drawdown(p),
        profit_factor(p),
        int(base["datahora_entrada"].dt.date.nunique()),
    )


def preparar_amostras():
    candles = indicadores(carregar_candles()).reset_index(drop=True)
    candles["hhmm"] = candles["DataHora_SP"].dt.strftime("%H:%M")
    candles["dow"] = candles["DataHora_SP"].dt.day_name()
    candles["data"] = candles["DataHora_SP"].dt.date
    candles["dist_ema17"] = candles["close"] - candles["ema17"]
    candles["dist_ema34"] = candles["close"] - candles["ema34"]
    candles["dist_ema200"] = candles["close"] - candles["ema200"]
    candles["dist_vwap"] = candles["close"] - candles["vwap"]
    candles["macd_gap"] = candles["macd"] - candles["macd_signal"]

    linhas = []
    idxs = candles.index[candles["hhmm"].isin(HORARIOS)].tolist()
    print("Candles candidatos:", len(idxs), flush=True)
    for n, idx in enumerate(idxs, 1):
        if n % 500 == 0:
            print("  simulados:", n, "/", len(idxs), flush=True)
        row = candles.loc[idx]
        for direcao in ["BUY", "SELL"]:
            sim = simular_trade(candles, idx, direcao, 50.5, 117.0)
            if sim is None:
                continue
            entrada, saida, pontos, resultado = sim
            item = {
                "idx": idx,
                "data": row["data"],
                "datahora_sinal": row["DataHora_SP"],
                "datahora_entrada": entrada,
                "datahora_saida": saida,
                "hhmm": row["hhmm"],
                "dow": row["dow"],
                "direcao": direcao,
                "pontos": float(pontos),
                "resultado": resultado,
                "y": int(pontos > 0),
            }
            for col in FEATURES_NUM:
                item[col] = float(row[col]) if pd.notna(row[col]) else np.nan
            linhas.append(item)

    samples = pd.DataFrame(linhas).dropna(subset=FEATURES_NUM).reset_index(drop=True)
    samples["mes"] = pd.to_datetime(samples["datahora_sinal"]).dt.to_period("M").dt.to_timestamp()
    return samples


def matriz_features(samples):
    x_num = samples[FEATURES_NUM].copy()
    x_cat = pd.get_dummies(samples[FEATURES_CAT], prefix=FEATURES_CAT, dtype=float)
    return pd.concat([x_num, x_cat], axis=1)


def modelos():
    return {
        "logistica": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1200, class_weight="balanced")),
        "rf_4": RandomForestClassifier(n_estimators=120, max_depth=4, min_samples_leaf=18, random_state=72, class_weight="balanced_subsample", n_jobs=-1),
    }


def walk_forward(samples, nome_modelo, modelo, meses_treino=12):
    x_all = matriz_features(samples)
    y_all = samples["y"].astype(int)
    meses = sorted(samples["mes"].unique())
    preds = []
    for mes in meses:
        inicio_treino = mes - pd.DateOffset(months=meses_treino)
        mask_train = (samples["mes"] < mes) & (samples["mes"] >= inicio_treino)
        mask_test = samples["mes"].eq(mes)
        if mask_train.sum() < 500 or mask_test.sum() == 0:
            continue
        x_train = x_all.loc[mask_train]
        y_train = y_all.loc[mask_train]
        x_test = x_all.loc[mask_test]
        modelo.fit(x_train, y_train)
        proba = modelo.predict_proba(x_test)[:, 1]
        bloco = samples.loc[mask_test].copy()
        bloco["prob_take"] = proba
        bloco["modelo"] = nome_modelo
        bloco["meses_treino"] = meses_treino
        try:
            bloco["auc_mes"] = roc_auc_score(bloco["y"], proba)
        except ValueError:
            bloco["auc_mes"] = np.nan
        preds.append(bloco)
    return pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()


def selecionar_por_dia(preds, threshold, top_rank=1):
    escolhidos = []
    proxima_liberada = pd.Timestamp.min
    for data, grupo in preds.sort_values("datahora_sinal").groupby("data", sort=True):
        grupo = grupo[grupo["prob_take"] >= threshold].sort_values("prob_take", ascending=False)
        if grupo.empty or top_rank > len(grupo):
            continue
        trade = grupo.iloc[top_rank - 1]
        if trade["datahora_sinal"] < proxima_liberada:
            continue
        proxima_liberada = trade["datahora_saida"]
        escolhidos.append(trade)
    return pd.DataFrame(escolhidos)


def avaliar(preds):
    linhas = []
    trades_top = []
    for threshold in np.arange(0.00, 0.86, 0.02):
        for top_rank in [1, 2, 3]:
            trades = selecionar_por_dia(preds, float(threshold), top_rank)
            if trades.empty:
                continue
            m365 = metricas(trades, 365)
            m90 = metricas(trades, 90)
            m30 = metricas(trades, 30)
            row = {
                "modelo": preds["modelo"].iloc[0],
                "meses_treino": int(preds["meses_treino"].iloc[0]),
                "threshold": float(threshold),
                "top_rank": top_rank,
                "trades_365": m365[0],
                "winrate_365": m365[1],
                "pontos_365": m365[2],
                "dd_365": m365[3],
                "pf_365": m365[4],
                "dias_365": m365[5],
                "trades_90": m90[0],
                "winrate_90": m90[1],
                "pontos_90": m90[2],
                "trades_30": m30[0],
                "winrate_30": m30[1],
                "pontos_30": m30[2],
                "auc_media": float(preds["auc_mes"].dropna().mean()) if preds["auc_mes"].notna().any() else np.nan,
            }
            distancia = 0 if 230 <= row["trades_365"] <= 250 else min(abs(row["trades_365"] - 230), abs(row["trades_365"] - 250))
            pf_cap = min(row["pf_365"], 5.0)
            row["distancia_alvo"] = distancia
            row["score"] = (
                row["pontos_365"]
                + 220 * pf_cap
                + 25 * row["winrate_365"]
                - 0.8 * abs(row["dd_365"])
                - 180 * distancia
                - 650 * max(0, 80 - row["winrate_365"])
            )
            linhas.append(row)
            if row["trades_365"] >= 200 and row["pontos_365"] > 0:
                trades_top.append(trades.assign(threshold=threshold, top_rank=top_rank))
    return pd.DataFrame(linhas), pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()


def main():
    samples = preparar_amostras()
    print("Amostras:", len(samples), samples["datahora_sinal"].min(), samples["datahora_sinal"].max(), flush=True)
    rankings = []
    trades_all = []
    for meses_treino in [9, 12]:
        for nome, modelo in modelos().items():
            print("Walk-forward:", nome, "treino", meses_treino, "meses", flush=True)
            preds = walk_forward(samples, nome, modelo, meses_treino)
            if preds.empty:
                continue
            ranking, trades = avaliar(preds)
            rankings.append(ranking)
            if not trades.empty:
                trades_all.append(trades)

    ranking = pd.concat(rankings, ignore_index=True).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    trades_top = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()

    cols = [
        "modelo", "meses_treino", "threshold", "top_rank", "score",
        "trades_365", "distancia_alvo", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "auc_media",
    ]
    print("\nTop geral:")
    print(ranking[cols].head(30).to_string(index=False), flush=True)
    alvo = ranking[(ranking["trades_365"].between(230, 250)) & (ranking["winrate_365"] >= 80) & (ranking["pontos_365"] > 0)]
    print("\nDentro do alvo 230-250, winrate >=80:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False), flush=True)
    perto = ranking[(ranking["trades_365"].between(200, 280)) & (ranking["pontos_365"] > 0)].sort_values(
        ["winrate_365", "pontos_365", "pf_365"], ascending=False
    )
    print("\nPerto do alvo 200-280 trades, positivo:")
    if not perto.empty:
        print(perto[cols].head(30).to_string(index=False), flush=True)

    try:
        ranking.to_csv(ARQ_RANKING, index=False)
        trades_top.to_csv(ARQ_TRADES, index=False)
        print("Arquivos:", flush=True)
        print(ARQ_RANKING, flush=True)
        print(ARQ_TRADES, flush=True)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV:", exc, flush=True)


if __name__ == "__main__":
    main()
