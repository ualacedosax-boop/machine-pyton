# -*- coding: utf-8 -*-

from pathlib import Path
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"
ARQ_TREINO = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES = PASTA_DATASET / "08_features_sugeridas_v5.txt"

PASTA_SAIDA = BASE_DIR / "saida_v5_treino_2024_2025_teste_2026"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_PRED_RF = PASTA_SAIDA / "02b_predicoes_v5_RANDOMFOREST_054_2026.csv.gz"
ARQ_MENSAL = PASTA_SAIDA / "04_analise_mensal_v5_randomforest_054_2026.csv"
ARQ_MENSAL_DIR = PASTA_SAIDA / "05_analise_mensal_direcao_v5_randomforest_054_2026.csv"
ARQ_CONFIG = PASTA_SAIDA / "06_config_v5_randomforest_054.json"
ARQ_MODELO_RF = PASTA_SAIDA / "modelo_v5_randomforest_054.joblib"
ARQ_FEATURES_RF = PASTA_SAIDA / "features_v5_randomforest_054.joblib"

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"
THRESHOLD = 0.54


def carregar_features(df_treino, df_teste):
    if not ARQ_FEATURES.exists():
        raise FileNotFoundError(f"Arquivo de features não encontrado: {ARQ_FEATURES}")

    with open(ARQ_FEATURES, "r", encoding="utf-8") as f:
        features = [x.strip() for x in f.readlines() if x.strip()]

    validas = []

    for col in features:
        if col in df_treino.columns and col in df_teste.columns:
            if df_treino[col].dtype.kind in "biufc":
                validas.append(col)

    validas = sorted(set(validas))

    if not validas:
        raise RuntimeError("Nenhuma feature válida encontrada.")

    return validas


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


def resumo(df, grupo, valor):
    if df.empty:
        return {
            "grupo": grupo,
            "valor": valor,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "drawdown_trades": 0.0,
            "buy_total": 0,
            "sell_total": 0,
        }

    total = len(df)
    wins = int((df[TARGET_COL] == 1).sum())
    losses = int((df[TARGET_COL] == 0).sum())
    lucro = float(df[PONTOS_COL].sum())

    return {
        "grupo": grupo,
        "valor": valor,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": calcular_pf(df),
        "drawdown_trades": calcular_dd(df),
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
    }


def main():
    print("=====================================================")
    print("ANALISE MENSAL - V5 RANDOMFOREST 0.54 - 2026")
    print("=====================================================")

    if not ARQ_TREINO.exists():
        raise FileNotFoundError(f"Treino não encontrado: {ARQ_TREINO}")

    if not ARQ_TESTE.exists():
        raise FileNotFoundError(f"Teste não encontrado: {ARQ_TESTE}")

    treino = pd.read_csv(ARQ_TREINO, compression="gzip")
    teste = pd.read_csv(ARQ_TESTE, compression="gzip")

    treino["DataHora_SP"] = pd.to_datetime(treino["DataHora_SP"], errors="coerce")
    teste["DataHora_SP"] = pd.to_datetime(teste["DataHora_SP"], errors="coerce")

    treino = treino.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)
    teste = teste.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

    features = carregar_features(treino, teste)

    print("Treino 2024+2025:", len(treino))
    print("Teste 2026:", len(teste))
    print("Features:", len(features))
    print("Threshold:", THRESHOLD)

    X_train = limpar_X(treino, features)
    y_train = treino[TARGET_COL].astype(int)

    X_test = limpar_X(teste, features)
    y_test = teste[TARGET_COL].astype(int)

    modelo = RandomForestClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print("\nTreinando RandomForest...")
    modelo.fit(X_train, y_train)

    pred_train = modelo.predict(X_train)
    pred_test = modelo.predict(X_test)
    prob = modelo.predict_proba(X_test)[:, 1]

    print("\nMétricas classificação:")
    print("acc_treino:", accuracy_score(y_train, pred_train))
    print("bal_acc_treino:", balanced_accuracy_score(y_train, pred_train))
    print("acc_teste:", accuracy_score(y_test, pred_test))
    print("bal_acc_teste:", balanced_accuracy_score(y_test, pred_test))

    try:
        print("auc_teste:", roc_auc_score(y_test, prob))
    except Exception:
        print("auc_teste:", 0)

    pred = teste.copy()
    pred["modelo_v5"] = "RandomForest"
    pred["prob_v5"] = prob
    pred["aceito_v5"] = pred["prob_v5"] >= THRESHOLD

    pred.to_csv(ARQ_PRED_RF, index=False, compression="gzip")
    joblib.dump(modelo, ARQ_MODELO_RF)
    joblib.dump(features, ARQ_FEATURES_RF)

    aceitos = pred[pred["aceito_v5"]].copy()
    aceitos["AnoMes"] = aceitos["DataHora_SP"].dt.strftime("%Y-%m")

    geral = resumo(aceitos, "GERAL", "2026")

    print("\n=====================================================")
    print("RESUMO GERAL V5 RF 0.54")
    print("=====================================================")
    print(pd.Series(geral).to_string())

    linhas = []

    for mes, g in aceitos.groupby("AnoMes", sort=True):
        linhas.append(resumo(g, "Mes", mes))

    mensal = pd.DataFrame(linhas)

    if not mensal.empty:
        mensal["lucro_acumulado"] = mensal["lucro_pontos"].cumsum()

    print("\n=====================================================")
    print("ANALISE MENSAL")
    print("=====================================================")
    print(mensal.to_string(index=False))

    mensal.to_csv(ARQ_MENSAL, index=False)

    linhas_dir = []

    for (mes, direcao), g in aceitos.groupby(["AnoMes", "Direcao"], sort=True):
        linhas_dir.append(resumo(g, "Mes_Direcao", f"{mes}_{direcao}"))

    mensal_dir = pd.DataFrame(linhas_dir)
    mensal_dir.to_csv(ARQ_MENSAL_DIR, index=False)

    meses_pos = int((mensal["lucro_pontos"] > 0).sum()) if not mensal.empty else 0
    meses_neg = int((mensal["lucro_pontos"] < 0).sum()) if not mensal.empty else 0

    print("\n=====================================================")
    print("DIAGNOSTICO")
    print("=====================================================")
    print("Meses positivos:", meses_pos)
    print("Meses negativos:", meses_neg)
    print("Lucro total:", float(mensal["lucro_pontos"].sum()) if not mensal.empty else 0.0)

    if not mensal.empty:
        melhor_mes = mensal.sort_values("lucro_pontos", ascending=False).head(1)
        pior_mes = mensal.sort_values("lucro_pontos", ascending=True).head(1)

        print("\nMelhor mes:")
        print(melhor_mes.to_string(index=False))

        print("\nPior mes:")
        print(pior_mes.to_string(index=False))

    config = {
        "nome": "V5_RANDOMFOREST_054_CANDIDATA",
        "modelo": "RandomForest",
        "threshold": THRESHOLD,
        "treino": "2024+2025",
        "teste": "2026",
        "resultado_2026": geral,
        "arquivos": {
            "predicoes": str(ARQ_PRED_RF),
            "analise_mensal": str(ARQ_MENSAL),
            "analise_mensal_direcao": str(ARQ_MENSAL_DIR),
            "modelo": str(ARQ_MODELO_RF),
            "features": str(ARQ_FEATURES_RF),
        }
    }

    import json
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\nArquivos gerados:")
    print(ARQ_PRED_RF)
    print(ARQ_MENSAL)
    print(ARQ_MENSAL_DIR)
    print(ARQ_CONFIG)
    print(ARQ_MODELO_RF)
    print(ARQ_FEATURES_RF)


if __name__ == "__main__":
    main()
