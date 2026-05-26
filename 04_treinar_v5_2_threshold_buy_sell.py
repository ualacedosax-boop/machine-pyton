# -*- coding: utf-8 -*-

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"
ARQ_TREINO = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"

PASTA_V5_1 = BASE_DIR / "saida_v5_1_feature_select_threshold_fino"
ARQ_IMPORTANCIA = PASTA_V5_1 / "04_importancia_features_v5_1.csv"

PASTA_SAIDA = BASE_DIR / "saida_v5_2_threshold_buy_sell"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD = PASTA_SAIDA / "01_leaderboard_v5_2_buy_sell.csv"
ARQ_CONFIG = PASTA_SAIDA / "02_melhor_config_v5_2.json"
ARQ_PREDICOES = PASTA_SAIDA / "03_predicoes_melhor_v5_2.csv.gz"
ARQ_MENSAL = PASTA_SAIDA / "04_analise_mensal_melhor_v5_2.csv"
ARQ_MODELOS = PASTA_SAIDA / "modelos_v5_2_buy_sell.joblib"
ARQ_FEATURES = PASTA_SAIDA / "features_v5_2.joblib"

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

TOP_FEATURES = 150

THRESHOLDS_BUY = [round(x, 3) for x in np.arange(0.500, 0.651, 0.005)]
THRESHOLDS_SELL = [round(x, 3) for x in np.arange(0.500, 0.651, 0.005)]

BENCHMARK_V5_1 = {
    "trades": 154,
    "wins": 125,
    "losses": 29,
    "winrate": 81.168831,
    "lucro_pontos": 2919.5,
    "profit_factor": 1.860448,
    "drawdown_trades": -380.5,
}

MIN_TRADES = 145


def carregar_dataset(caminho):
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho}")

    df = pd.read_csv(caminho, compression="gzip")
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"])
    df = df.sort_values("DataHora_SP").reset_index(drop=True)
    return df


def carregar_features():
    if not ARQ_IMPORTANCIA.exists():
        raise FileNotFoundError(f"Arquivo de importancia nao encontrado: {ARQ_IMPORTANCIA}")

    imp = pd.read_csv(ARQ_IMPORTANCIA)

    if "feature" not in imp.columns:
        raise RuntimeError("Arquivo de importancia nao tem coluna feature.")

    return imp.head(TOP_FEATURES)["feature"].tolist()


def limpar_X(df, features):
    X = df[features].copy()
    X = X.replace([np.inf, -np.inf], 0)
    X = X.fillna(0)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    return X


def calcular_pf(df):
    ganhos = df.loc[df[PONTOS_COL] > 0, PONTOS_COL].sum()
    perdas = abs(df.loc[df[PONTOS_COL] < 0, PONTOS_COL].sum())

    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0

    return float(ganhos / perdas)


def calcular_dd(df):
    if df.empty:
        return 0.0

    equity = df[PONTOS_COL].cumsum()
    topo = equity.cummax()
    dd = equity - topo
    return float(dd.min())


def resumo(df, nome):
    if df.empty:
        return {
            "nome": nome,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "drawdown_trades": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "meses": 0,
            "meses_positivos": 0,
            "meses_negativos": 0,
        }

    total = len(df)
    wins = int((df[TARGET_COL] == 1).sum())
    losses = int((df[TARGET_COL] == 0).sum())
    lucro = float(df[PONTOS_COL].sum())

    temp = df.copy()
    temp["AnoMes"] = pd.to_datetime(temp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")
    mensal = temp.groupby("AnoMes")[PONTOS_COL].sum()

    return {
        "nome": nome,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": calcular_pf(df),
        "drawdown_trades": calcular_dd(df),
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
        "meses": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
    }


def criar_modelo():
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def treinar_modelos_por_direcao(df_train, df_test, features):
    pred = df_test.copy()
    pred["prob_v5_2"] = np.nan

    modelos = {}

    for direcao in ["BUY", "SELL"]:
        tr = df_train[df_train["Direcao"] == direcao].copy()
        te_idx = df_test[df_test["Direcao"] == direcao].index

        if len(tr) < 50:
            raise RuntimeError(f"Poucos dados para {direcao}: {len(tr)}")

        X_train = limpar_X(tr, features)
        y_train = tr[TARGET_COL].astype(int)

        X_test = limpar_X(df_test.loc[te_idx], features)

        modelo = criar_modelo()
        modelo.fit(X_train, y_train)

        prob = modelo.predict_proba(X_test)[:, 1]

        pred.loc[te_idx, "prob_v5_2"] = prob
        modelos[direcao] = modelo

    pred["prob_v5_2"] = pred["prob_v5_2"].fillna(0.0)

    return modelos, pred


def avaliar_thresholds(pred, thr_buy, thr_sell):
    cond_buy = (pred["Direcao"] == "BUY") & (pred["prob_v5_2"] >= thr_buy)
    cond_sell = (pred["Direcao"] == "SELL") & (pred["prob_v5_2"] >= thr_sell)

    aceitos = pred[cond_buy | cond_sell].copy()

    nome = f"V5_2_BUY_{thr_buy:.3f}_SELL_{thr_sell:.3f}"

    r = resumo(aceitos, nome)

    r["threshold_buy"] = thr_buy
    r["threshold_sell"] = thr_sell
    r["trades_cortados"] = int(len(pred) - len(aceitos))
    r["wins_cortados"] = int(((pred[TARGET_COL] == 1) & ~(cond_buy | cond_sell)).sum())
    r["losses_cortados"] = int(((pred[TARGET_COL] == 0) & ~(cond_buy | cond_sell)).sum())

    r["passa_min_trades"] = bool(r["trades"] >= MIN_TRADES)

    r["supera_v5_1_lucro"] = bool(r["lucro_pontos"] > BENCHMARK_V5_1["lucro_pontos"])
    r["supera_v5_1_pf"] = bool(r["profit_factor"] > BENCHMARK_V5_1["profit_factor"])
    r["melhora_v5_1_dd"] = bool(r["drawdown_trades"] >= BENCHMARK_V5_1["drawdown_trades"])

    score = 0.0
    score += r["lucro_pontos"]
    score += r["profit_factor"] * 400.0
    score += r["winrate"] * 8.0
    score += r["drawdown_trades"] * 0.70

    if r["trades"] < MIN_TRADES:
        score -= 5000.0
        score -= (MIN_TRADES - r["trades"]) * 150.0

    if r["meses_negativos"] > 0:
        score -= r["meses_negativos"] * 2000.0

    if not r["supera_v5_1_lucro"]:
        score -= 800.0

    if not r["supera_v5_1_pf"]:
        score -= 500.0

    if not r["melhora_v5_1_dd"]:
        score -= 500.0

    r["score_ranking"] = float(score)

    return r


def gerar_mensal(pred, thr_buy, thr_sell):
    cond_buy = (pred["Direcao"] == "BUY") & (pred["prob_v5_2"] >= thr_buy)
    cond_sell = (pred["Direcao"] == "SELL") & (pred["prob_v5_2"] >= thr_sell)

    aceitos = pred[cond_buy | cond_sell].copy()

    if aceitos.empty:
        return pd.DataFrame()

    aceitos["AnoMes"] = pd.to_datetime(aceitos["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")

    linhas = []

    for mes, g in aceitos.groupby("AnoMes", sort=True):
        linhas.append(resumo(g, f"Mes_{mes}"))

    mensal = pd.DataFrame(linhas)

    if not mensal.empty:
        mensal["lucro_acumulado"] = mensal["lucro_pontos"].cumsum()

    return mensal


def main():
    print("=====================================================")
    print("V5.2 - THRESHOLD SEPARADO BUY / SELL")
    print("=====================================================")

    df_train = carregar_dataset(ARQ_TREINO)
    df_test = carregar_dataset(ARQ_TESTE)

    features = carregar_features()

    print("Treino:", len(df_train))
    print("Teste :", len(df_test))
    print("Features:", len(features))

    print("\nTreinando modelos por direcao...")
    modelos, pred = treinar_modelos_por_direcao(df_train, df_test, features)

    leaderboard = []

    print("\nTestando thresholds BUY/SELL...")

    for thr_buy in THRESHOLDS_BUY:
        for thr_sell in THRESHOLDS_SELL:
            linha = avaliar_thresholds(pred, thr_buy, thr_sell)
            leaderboard.append(linha)

    leaderboard_df = pd.DataFrame(leaderboard)
    leaderboard_df = leaderboard_df.sort_values("score_ranking", ascending=False).reset_index(drop=True)
    leaderboard_df.to_csv(ARQ_LEADERBOARD, index=False)

    print("\n=====================================================")
    print("LEADERBOARD V5.2 - TOP 40")
    print("=====================================================")

    cols = [
        "nome",
        "threshold_buy",
        "threshold_sell",
        "trades",
        "wins",
        "losses",
        "winrate",
        "lucro_pontos",
        "profit_factor",
        "drawdown_trades",
        "buy_total",
        "sell_total",
        "meses_positivos",
        "meses_negativos",
        "trades_cortados",
        "wins_cortados",
        "losses_cortados",
        "supera_v5_1_lucro",
        "supera_v5_1_pf",
        "melhora_v5_1_dd",
        "score_ranking",
    ]

    print(leaderboard_df[cols].head(40).to_string(index=False))

    validos = leaderboard_df[
        (leaderboard_df["passa_min_trades"] == True)
        & (leaderboard_df["meses_negativos"] == 0)
        & (leaderboard_df["supera_v5_1_lucro"] == True)
        & (leaderboard_df["supera_v5_1_pf"] == True)
        & (leaderboard_df["melhora_v5_1_dd"] == True)
    ].copy()

    if validos.empty:
        print("\nATENCAO: nenhum resultado superou todos os criterios. Usando melhor ranking geral.")
        melhor = leaderboard_df.iloc[0].to_dict()
    else:
        validos = validos.sort_values("score_ranking", ascending=False).reset_index(drop=True)
        melhor = validos.iloc[0].to_dict()

    print("\n=====================================================")
    print("MELHOR CONFIG V5.2")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    thr_buy = float(melhor["threshold_buy"])
    thr_sell = float(melhor["threshold_sell"])

    pred["threshold_buy"] = thr_buy
    pred["threshold_sell"] = thr_sell
    pred["aceito_v5_2"] = (
        ((pred["Direcao"] == "BUY") & (pred["prob_v5_2"] >= thr_buy))
        | ((pred["Direcao"] == "SELL") & (pred["prob_v5_2"] >= thr_sell))
    )

    pred.to_csv(ARQ_PREDICOES, index=False, compression="gzip")

    mensal = gerar_mensal(pred, thr_buy, thr_sell)
    mensal.to_csv(ARQ_MENSAL, index=False)

    print("\n=====================================================")
    print("ANALISE MENSAL MELHOR V5.2")
    print("=====================================================")
    print(mensal.to_string(index=False))

    joblib.dump(modelos, ARQ_MODELOS)
    joblib.dump(features, ARQ_FEATURES)

    config = {
        "nome": "V5_2_THRESHOLD_BUY_SELL",
        "melhor_config": melhor,
        "features": features,
        "benchmark_v5_1": BENCHMARK_V5_1,
        "arquivos": {
            "leaderboard": str(ARQ_LEADERBOARD),
            "predicoes": str(ARQ_PREDICOES),
            "analise_mensal": str(ARQ_MENSAL),
            "modelos": str(ARQ_MODELOS),
            "features": str(ARQ_FEATURES),
        }
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\nArquivos gerados:")
    print(ARQ_LEADERBOARD)
    print(ARQ_CONFIG)
    print(ARQ_PREDICOES)
    print(ARQ_MENSAL)
    print(ARQ_MODELOS)
    print(ARQ_FEATURES)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()