# -*- coding: utf-8 -*-

from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"

ARQ_TREINO_2024_2025 = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE_2026 = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES = PASTA_DATASET / "08_features_sugeridas_v5.txt"

PASTA_SAIDA = BASE_DIR / "saida_v5_1_walk_forward"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_RESUMO = PASTA_SAIDA / "01_resumo_walk_forward_v5_1.csv"
ARQ_MENSAL = PASTA_SAIDA / "02_mensal_walk_forward_v5_1.csv"
ARQ_PREDICOES = PASTA_SAIDA / "03_predicoes_walk_forward_v5_1.csv.gz"
ARQ_CONFIG = PASTA_SAIDA / "04_config_walk_forward_v5_1.json"

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

TOP_FEATURES = 150
THRESHOLD = 0.575


def carregar_dados():
    treino = pd.read_csv(ARQ_TREINO_2024_2025, compression="gzip")
    teste = pd.read_csv(ARQ_TESTE_2026, compression="gzip")

    df = pd.concat([treino, teste], ignore_index=True)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)
    df["Ano"] = df["DataHora_SP"].dt.year

    return df


def carregar_features_base(df):
    with open(ARQ_FEATURES, "r", encoding="utf-8") as f:
        features = [x.strip() for x in f.readlines() if x.strip()]

    validas = []
    for col in features:
        if col in df.columns and df[col].dtype.kind in "biufc":
            validas.append(col)

    validas = sorted(set(validas))

    if not validas:
        raise RuntimeError("Nenhuma feature válida encontrada.")

    return validas


def limpar_X(df, features):
    X = df[features].copy()
    X = X.replace([np.inf, -np.inf], 0).fillna(0)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    return X


def selecionar_top_features(df_train, features_base):
    X = limpar_X(df_train, features_base)
    y = df_train[TARGET_COL].astype(int)

    modelo = RandomForestClassifier(
        n_estimators=400,
        max_depth=6,
        min_samples_leaf=6,
        class_weight="balanced",
        random_state=123,
        n_jobs=-1,
    )

    modelo.fit(X, y)

    imp = pd.DataFrame({
        "feature": features_base,
        "importance": modelo.feature_importances_,
    }).sort_values("importance", ascending=False)

    return imp.head(TOP_FEATURES)["feature"].tolist()


def criar_modelo():
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


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


def resumo(df, walk_nome):
    if df.empty:
        return {
            "walk": walk_nome,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "drawdown_trades": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "dias_operados": 0,
            "meses": 0,
            "meses_positivos": 0,
            "meses_negativos": 0,
        }

    temp = df.copy()
    temp["DataDia"] = temp["DataHora_SP"].dt.strftime("%Y-%m-%d")
    temp["AnoMes"] = temp["DataHora_SP"].dt.strftime("%Y-%m")
    mensal = temp.groupby("AnoMes")[PONTOS_COL].sum()

    total = len(df)
    wins = int((df[TARGET_COL] == 1).sum())
    losses = int((df[TARGET_COL] == 0).sum())

    return {
        "walk": walk_nome,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": float(df[PONTOS_COL].sum()),
        "profit_factor": calcular_pf(df),
        "drawdown_trades": calcular_dd(df),
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
        "dias_operados": int(temp["DataDia"].nunique()),
        "meses": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
    }


def gerar_mensal(df, walk_nome):
    if df.empty:
        return pd.DataFrame()

    temp = df.copy()
    temp["AnoMes"] = temp["DataHora_SP"].dt.strftime("%Y-%m")

    linhas = []
    for mes, g in temp.groupby("AnoMes", sort=True):
        r = resumo(g, walk_nome)
        r["AnoMes"] = mes
        linhas.append(r)

    mensal = pd.DataFrame(linhas)

    if not mensal.empty:
        mensal["lucro_acumulado"] = mensal["lucro_pontos"].cumsum()

    return mensal


def treinar_e_testar(df_train, df_test, features_base, walk_nome):
    print("\n=====================================================")
    print("WALK:", walk_nome)
    print("=====================================================")
    print("Treino:", len(df_train), "| anos:", sorted(df_train["Ano"].unique()))
    print("Teste :", len(df_test), "| anos:", sorted(df_test["Ano"].unique()))

    features = selecionar_top_features(df_train, features_base)

    pred = df_test.copy()
    pred["prob_v5_1_walk"] = np.nan
    pred["walk"] = walk_nome

    for direcao in ["BUY", "SELL"]:
        tr = df_train[df_train["Direcao"] == direcao].copy()
        te_idx = df_test[df_test["Direcao"] == direcao].index

        if len(tr) < 30 or len(te_idx) == 0:
            print(f"Aviso: poucos dados para {direcao}. Treino={len(tr)} Teste={len(te_idx)}")
            continue

        X_train = limpar_X(tr, features)
        y_train = tr[TARGET_COL].astype(int)

        X_test = limpar_X(df_test.loc[te_idx], features)

        modelo = criar_modelo()
        modelo.fit(X_train, y_train)

        pred.loc[te_idx, "prob_v5_1_walk"] = modelo.predict_proba(X_test)[:, 1]

    pred["prob_v5_1_walk"] = pred["prob_v5_1_walk"].fillna(0.0)
    pred["aceito_walk"] = pred["prob_v5_1_walk"] >= THRESHOLD

    aceitos = pred[pred["aceito_walk"]].copy()

    r = resumo(aceitos, walk_nome)
    m = gerar_mensal(aceitos, walk_nome)

    print("\nResumo:")
    print(pd.Series(r).to_string())

    print("\nMensal:")
    print(m.to_string(index=False))

    return r, m, pred


def main():
    print("=====================================================")
    print("WALK-FORWARD V5.1")
    print("=====================================================")

    df = carregar_dados()
    features_base = carregar_features_base(df)

    print("Total dados:", len(df))
    print("Anos disponíveis:", sorted(df["Ano"].unique()))
    print("Features base:", len(features_base))
    print("Top features:", TOP_FEATURES)
    print("Threshold:", THRESHOLD)

    walks = [
        {
            "nome": "TREINA_2024_TESTA_2025",
            "anos_treino": [2024],
            "anos_teste": [2025],
        },
        {
            "nome": "TREINA_2025_TESTA_2026",
            "anos_treino": [2025],
            "anos_teste": [2026],
        },
        {
            "nome": "TREINA_2024_2025_TESTA_2026",
            "anos_treino": [2024, 2025],
            "anos_teste": [2026],
        },
    ]

    resumos = []
    mensais = []
    predicoes = []

    for w in walks:
        df_train = df[df["Ano"].isin(w["anos_treino"])].copy()
        df_test = df[df["Ano"].isin(w["anos_teste"])].copy()

        if df_train.empty or df_test.empty:
            print("Pulando walk sem dados:", w["nome"])
            continue

        r, m, p = treinar_e_testar(df_train, df_test, features_base, w["nome"])

        resumos.append(r)

        if not m.empty:
            mensais.append(m)

        predicoes.append(p)

    resumo_df = pd.DataFrame(resumos)
    mensal_df = pd.concat(mensais, ignore_index=True) if mensais else pd.DataFrame()
    pred_df = pd.concat(predicoes, ignore_index=True) if predicoes else pd.DataFrame()

    resumo_df.to_csv(ARQ_RESUMO, index=False)
    mensal_df.to_csv(ARQ_MENSAL, index=False)
    pred_df.to_csv(ARQ_PREDICOES, index=False, compression="gzip")

    config = {
        "nome": "WALK_FORWARD_V5_1",
        "top_features": TOP_FEATURES,
        "threshold": THRESHOLD,
        "arquivos": {
            "resumo": str(ARQ_RESUMO),
            "mensal": str(ARQ_MENSAL),
            "predicoes": str(ARQ_PREDICOES),
        }
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\n=====================================================")
    print("RESUMO FINAL WALK-FORWARD")
    print("=====================================================")
    print(resumo_df.to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_RESUMO)
    print(ARQ_MENSAL)
    print(ARQ_PREDICOES)
    print(ARQ_CONFIG)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()