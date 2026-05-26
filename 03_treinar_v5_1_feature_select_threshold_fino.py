# -*- coding: utf-8 -*-

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score

warnings.filterwarnings("ignore")

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"
ARQ_TREINO = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES = PASTA_DATASET / "08_features_sugeridas_v5.txt"

PASTA_SAIDA = BASE_DIR / "saida_v5_1_feature_select_threshold_fino"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD = PASTA_SAIDA / "01_leaderboard_v5_1_2026.csv"
ARQ_CONFIG = PASTA_SAIDA / "02_melhor_config_v5_1.json"
ARQ_PREDICOES = PASTA_SAIDA / "03_predicoes_melhor_v5_1_2026.csv.gz"
ARQ_IMPORTANCIA = PASTA_SAIDA / "04_importancia_features_v5_1.csv"
ARQ_MENSAL = PASTA_SAIDA / "05_analise_mensal_melhor_v5_1.csv"
ARQ_MODELO = PASTA_SAIDA / "modelo_melhor_v5_1.joblib"
ARQ_FEATURES_MODELO = PASTA_SAIDA / "features_melhor_v5_1.joblib"

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

BENCHMARK_V4 = {
    "trades": 167,
    "wins": 132,
    "losses": 35,
    "winrate": 79.041916,
    "lucro_pontos": 2571.0,
    "profit_factor": 1.627839,
    "drawdown_trades": -582.5,
}

BENCHMARK_V5_ATUAL = {
    "trades": 148,
    "wins": 119,
    "losses": 29,
    "winrate": 80.405405,
    "lucro_pontos": 2616.5,
    "profit_factor": 1.771146,
    "drawdown_trades": -548.0,
}

MIN_TRADES = 145

TOP_FEATURES_LIST = [30, 50, 75, 100, 150]
THRESHOLDS = [round(x, 3) for x in np.arange(0.500, 0.601, 0.005)]


def carregar_dataset(caminho):
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho}")

    df = pd.read_csv(caminho, compression="gzip")

    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        df = df.dropna(subset=["DataHora_SP"])
        df = df.sort_values("DataHora_SP").reset_index(drop=True)

    return df


def carregar_features(df_train, df_test):
    if not ARQ_FEATURES.exists():
        raise FileNotFoundError(f"Arquivo de features nao encontrado: {ARQ_FEATURES}")

    with open(ARQ_FEATURES, "r", encoding="utf-8") as f:
        features = [x.strip() for x in f.readlines() if x.strip()]

    validas = []

    for col in features:
        if col in df_train.columns and col in df_test.columns:
            if df_train[col].dtype.kind in "biufc":
                validas.append(col)

    validas = sorted(set(validas))

    if not validas:
        raise RuntimeError("Nenhuma feature valida encontrada.")

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

    meses = 0
    meses_pos = 0
    meses_neg = 0

    if "DataHora_SP" in df.columns:
        tmp = df.copy()
        tmp["AnoMes"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")
        mensal = tmp.groupby("AnoMes")[PONTOS_COL].sum()
        meses = int(len(mensal))
        meses_pos = int((mensal > 0).sum())
        meses_neg = int((mensal < 0).sum())

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
        "meses": meses,
        "meses_positivos": meses_pos,
        "meses_negativos": meses_neg,
    }


def criar_modelo(nome):
    if nome == "RandomForest":
        return RandomForestClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    if nome == "ExtraTrees":
        return ExtraTreesClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    if nome == "LogisticRegression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=2500,
                class_weight="balanced",
                random_state=42,
            ))
        ])

    raise ValueError(f"Modelo desconhecido: {nome}")


def obter_prob(modelo, X):
    if hasattr(modelo, "predict_proba"):
        p = modelo.predict_proba(X)
        return p[:, 1] if p.shape[1] > 1 else p[:, 0]

    return modelo.predict(X).astype(float)


def metricas(modelo, X_train, y_train, X_test, y_test):
    pred_train = modelo.predict(X_train)
    pred_test = modelo.predict(X_test)

    out = {
        "acc_treino": float(accuracy_score(y_train, pred_train)),
        "bal_acc_treino": float(balanced_accuracy_score(y_train, pred_train)),
        "acc_teste": float(accuracy_score(y_test, pred_test)),
        "bal_acc_teste": float(balanced_accuracy_score(y_test, pred_test)),
    }

    try:
        out["auc_teste"] = float(roc_auc_score(y_test, obter_prob(modelo, X_test)))
    except Exception:
        out["auc_teste"] = 0.0

    return out


def selecionar_features(df_train, df_test, features_base):
    print("\nCalculando importancia das features...")

    X_train = limpar_X(df_train, features_base)
    y_train = df_train[TARGET_COL].astype(int)

    modelo = RandomForestClassifier(
        n_estimators=400,
        max_depth=6,
        min_samples_leaf=6,
        class_weight="balanced",
        random_state=123,
        n_jobs=-1,
    )

    modelo.fit(X_train, y_train)

    imp = pd.DataFrame({
        "feature": features_base,
        "importance": modelo.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    imp.to_csv(ARQ_IMPORTANCIA, index=False)

    print("\nTop 30 features:")
    print(imp.head(30).to_string(index=False))

    return imp


def avaliar(df_pred, threshold, nome):
    aceitos = df_pred[df_pred["prob_v5"] >= threshold].copy()

    r = resumo(aceitos, nome)

    r["threshold"] = threshold
    r["trades_cortados"] = int(len(df_pred) - len(aceitos))
    r["wins_cortados"] = int(((df_pred[TARGET_COL] == 1) & (df_pred["prob_v5"] < threshold)).sum())
    r["losses_cortados"] = int(((df_pred[TARGET_COL] == 0) & (df_pred["prob_v5"] < threshold)).sum())

    r["passa_min_trades"] = bool(r["trades"] >= MIN_TRADES)

    r["supera_v4_lucro"] = bool(r["lucro_pontos"] > BENCHMARK_V4["lucro_pontos"])
    r["supera_v4_pf"] = bool(r["profit_factor"] > BENCHMARK_V4["profit_factor"])
    r["melhora_v4_dd"] = bool(r["drawdown_trades"] >= BENCHMARK_V4["drawdown_trades"])

    r["supera_v5_lucro"] = bool(r["lucro_pontos"] > BENCHMARK_V5_ATUAL["lucro_pontos"])
    r["supera_v5_pf"] = bool(r["profit_factor"] > BENCHMARK_V5_ATUAL["profit_factor"])
    r["melhora_v5_dd"] = bool(r["drawdown_trades"] >= BENCHMARK_V5_ATUAL["drawdown_trades"])

    score = 0.0
    score += r["lucro_pontos"]
    score += r["profit_factor"] * 350.0
    score += r["winrate"] * 8.0
    score += r["drawdown_trades"] * 0.60

    if r["trades"] < MIN_TRADES:
        score -= 5000.0
        score -= (MIN_TRADES - r["trades"]) * 100.0

    if r["meses_negativos"] > 0:
        score -= r["meses_negativos"] * 1500.0

    if not r["supera_v4_lucro"]:
        score -= 800.0

    if not r["supera_v4_pf"]:
        score -= 500.0

    if not r["supera_v5_lucro"]:
        score -= 400.0

    r["score_ranking"] = float(score)

    return r


def treinar_global(df_train, df_test, features, modelo_nome):
    X_train = limpar_X(df_train, features)
    y_train = df_train[TARGET_COL].astype(int)

    X_test = limpar_X(df_test, features)
    y_test = df_test[TARGET_COL].astype(int)

    modelo = criar_modelo(modelo_nome)
    modelo.fit(X_train, y_train)

    pred = df_test.copy()
    pred["prob_v5"] = obter_prob(modelo, X_test)
    pred["modo_v5"] = "GLOBAL"
    pred["modelo_v5"] = modelo_nome

    m = metricas(modelo, X_train, y_train, X_test, y_test)

    return modelo, pred, m


def treinar_direcao(df_train, df_test, features, modelo_nome):
    pred_final = df_test.copy()
    pred_final["prob_v5"] = np.nan
    pred_final["modo_v5"] = "DIRECAO_SEPARADA"
    pred_final["modelo_v5"] = modelo_nome

    modelos = {}
    metricas_lista = []

    for direcao in ["BUY", "SELL"]:
        tr = df_train[df_train["Direcao"] == direcao].copy()
        te_idx = df_test[df_test["Direcao"] == direcao].index

        if len(tr) < 50 or len(te_idx) == 0:
            continue

        X_train = limpar_X(tr, features)
        y_train = tr[TARGET_COL].astype(int)

        X_test = limpar_X(df_test.loc[te_idx], features)
        y_test = df_test.loc[te_idx, TARGET_COL].astype(int)

        modelo = criar_modelo(modelo_nome)
        modelo.fit(X_train, y_train)

        pred_final.loc[te_idx, "prob_v5"] = obter_prob(modelo, X_test)

        try:
            metricas_lista.append(metricas(modelo, X_train, y_train, X_test, y_test))
        except Exception:
            pass

        modelos[direcao] = modelo

    pred_final["prob_v5"] = pred_final["prob_v5"].fillna(0.0)

    m = {
        "acc_treino": 0.0,
        "bal_acc_treino": 0.0,
        "acc_teste": 0.0,
        "bal_acc_teste": 0.0,
        "auc_teste": 0.0,
    }

    if metricas_lista:
        for k in m:
            m[k] = float(np.mean([x.get(k, 0.0) for x in metricas_lista]))

    return modelos, pred_final, m


def gerar_mensal(pred, threshold):
    aceitos = pred[pred["prob_v5"] >= threshold].copy()

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
    print("V5.1 - FEATURE SELECTION + THRESHOLD FINO")
    print("=====================================================")

    df_train = carregar_dataset(ARQ_TREINO)
    df_test = carregar_dataset(ARQ_TESTE)

    print("\nDataset:")
    print("Treino:", len(df_train))
    print("Teste :", len(df_test))

    features_base = carregar_features(df_train, df_test)

    print("\nFeatures base:", len(features_base))

    imp = selecionar_features(df_train, df_test, features_base)

    modelos_nome = ["RandomForest", "ExtraTrees", "LogisticRegression"]
    modos = ["GLOBAL", "DIRECAO_SEPARADA"]

    leaderboard = []
    predicoes = {}
    modelos_salvos = {}
    features_por_chave = {}

    for top_n in TOP_FEATURES_LIST:
        features = imp.head(top_n)["feature"].tolist()

        print("\n=====================================================")
        print(f"TESTANDO TOP {top_n} FEATURES")
        print("=====================================================")

        for modelo_nome in modelos_nome:
            for modo in modos:
                chave = f"{modelo_nome}_{modo}_top{top_n}"

                print(f"Treinando: {chave}")

                try:
                    if modo == "GLOBAL":
                        modelo, pred, m = treinar_global(df_train, df_test, features, modelo_nome)
                    else:
                        modelo, pred, m = treinar_direcao(df_train, df_test, features, modelo_nome)

                    predicoes[chave] = pred
                    modelos_salvos[chave] = modelo
                    features_por_chave[chave] = features

                    for thr in THRESHOLDS:
                        nome = f"{chave}_thr_{thr:.3f}"
                        linha = avaliar(pred, thr, nome)
                        linha["modelo"] = modelo_nome
                        linha["modo"] = modo
                        linha["top_features"] = top_n
                        linha["chave_modelo"] = chave
                        linha.update(m)
                        leaderboard.append(linha)

                except Exception as e:
                    print("ERRO:", chave, e)

    leaderboard_df = pd.DataFrame(leaderboard)

    if leaderboard_df.empty:
        raise RuntimeError("Nenhum resultado gerado.")

    leaderboard_df = leaderboard_df.sort_values("score_ranking", ascending=False).reset_index(drop=True)
    leaderboard_df.to_csv(ARQ_LEADERBOARD, index=False)

    print("\n=====================================================")
    print("LEADERBOARD V5.1 - TOP 40")
    print("=====================================================")

    cols = [
        "nome", "modelo", "modo", "top_features", "threshold",
        "trades", "wins", "losses", "winrate", "lucro_pontos",
        "profit_factor", "drawdown_trades", "meses_positivos", "meses_negativos",
        "trades_cortados", "wins_cortados", "losses_cortados",
        "supera_v4_lucro", "supera_v4_pf", "melhora_v4_dd",
        "supera_v5_lucro", "supera_v5_pf", "melhora_v5_dd",
        "score_ranking", "auc_teste", "bal_acc_teste"
    ]

    cols = [c for c in cols if c in leaderboard_df.columns]
    print(leaderboard_df[cols].head(40).to_string(index=False))

    validos = leaderboard_df[
        (leaderboard_df["passa_min_trades"] == True)
        & (leaderboard_df["supera_v4_lucro"] == True)
        & (leaderboard_df["supera_v4_pf"] == True)
        & (leaderboard_df["melhora_v4_dd"] == True)
        & (leaderboard_df["meses_negativos"] == 0)
    ].copy()

    if validos.empty:
        print("\nATENCAO: nenhum modelo passou todos os criterios. Usando melhor ranking geral.")
        melhor = leaderboard_df.iloc[0].to_dict()
    else:
        validos = validos.sort_values("score_ranking", ascending=False).reset_index(drop=True)
        melhor = validos.iloc[0].to_dict()

    print("\n=====================================================")
    print("MELHOR CONFIG V5.1")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    chave_melhor = melhor["chave_modelo"]
    threshold_melhor = float(melhor["threshold"])

    pred_melhor = predicoes[chave_melhor].copy()
    pred_melhor["threshold_usado"] = threshold_melhor
    pred_melhor["aceito_v5_1"] = pred_melhor["prob_v5"] >= threshold_melhor

    pred_melhor.to_csv(ARQ_PREDICOES, index=False, compression="gzip")

    features_melhor = features_por_chave[chave_melhor]

    joblib.dump(modelos_salvos[chave_melhor], ARQ_MODELO)
    joblib.dump(features_melhor, ARQ_FEATURES_MODELO)

    mensal = gerar_mensal(pred_melhor, threshold_melhor)
    mensal.to_csv(ARQ_MENSAL, index=False)

    print("\n=====================================================")
    print("ANALISE MENSAL MELHOR V5.1")
    print("=====================================================")
    print(mensal.to_string(index=False))

    config = {
        "nome": "V5_1_FEATURE_SELECT_THRESHOLD_FINO",
        "melhor_config": melhor,
        "features": features_melhor,
        "benchmark_v4": BENCHMARK_V4,
        "benchmark_v5_atual": BENCHMARK_V5_ATUAL,
        "arquivos": {
            "leaderboard": str(ARQ_LEADERBOARD),
            "predicoes": str(ARQ_PREDICOES),
            "analise_mensal": str(ARQ_MENSAL),
            "modelo": str(ARQ_MODELO),
            "features_modelo": str(ARQ_FEATURES_MODELO),
            "importancia_features": str(ARQ_IMPORTANCIA),
        }
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\nArquivos gerados:")
    print(ARQ_LEADERBOARD)
    print(ARQ_CONFIG)
    print(ARQ_PREDICOES)
    print(ARQ_IMPORTANCIA)
    print(ARQ_MENSAL)
    print(ARQ_MODELO)
    print(ARQ_FEATURES_MODELO)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()
