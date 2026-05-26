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

warnings.filterwarnings("ignore")

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"

ARQ_TREINO_2024_2025 = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE_2026 = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES_BASE = PASTA_DATASET / "08_features_sugeridas_v5.txt"

PASTA_SAIDA = BASE_DIR / "saida_v5_3_validacao_2025_teste_2026"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD_2025 = PASTA_SAIDA / "01_leaderboard_validacao_2025_v5_3.csv"
ARQ_RESULTADO_2026 = PASTA_SAIDA / "02_resultado_teste_2026_v5_3.csv"
ARQ_MENSAL_2025 = PASTA_SAIDA / "03_mensal_validacao_2025_v5_3.csv"
ARQ_MENSAL_2026 = PASTA_SAIDA / "04_mensal_teste_2026_v5_3.csv"
ARQ_PRED_2025 = PASTA_SAIDA / "05_predicoes_validacao_2025_v5_3.csv.gz"
ARQ_PRED_2026 = PASTA_SAIDA / "06_predicoes_teste_2026_v5_3.csv.gz"
ARQ_CONFIG = PASTA_SAIDA / "07_config_v5_3.json"
ARQ_MODELO_FINAL = PASTA_SAIDA / "modelo_final_v5_3.joblib"
ARQ_FEATURES_FINAL = PASTA_SAIDA / "features_final_v5_3.joblib"
ARQ_IMPORTANCIA = PASTA_SAIDA / "08_importancia_features_v5_3.csv"

# ============================================================
# CONFIGURAÇÕES
# ============================================================

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

TOP_FEATURES_LIST = [30, 50, 75, 100, 150]
THRESHOLDS = [round(x, 3) for x in np.arange(0.500, 0.651, 0.005)]

MODELOS = ["RandomForest", "ExtraTrees", "LogisticRegression"]
MODOS = ["GLOBAL", "DIRECAO_SEPARADA"]

MIN_TRADES_2025 = 180
MIN_TRADES_2026 = 120

BENCHMARK_V4_2026 = {
    "nome": "V4_CAMPEAO_2026",
    "trades": 167,
    "wins": 132,
    "losses": 35,
    "winrate": 79.041916,
    "lucro_pontos": 2571.0,
    "profit_factor": 1.627839,
    "drawdown_trades": -582.5,
}

BENCHMARK_V5_1_2026 = {
    "nome": "V5_1_2026",
    "trades": 154,
    "wins": 125,
    "losses": 29,
    "winrate": 81.168831,
    "lucro_pontos": 2919.5,
    "profit_factor": 1.860448,
    "drawdown_trades": -380.5,
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def carregar_dados():
    if not ARQ_TREINO_2024_2025.exists():
        raise FileNotFoundError(f"Não encontrei: {ARQ_TREINO_2024_2025}")

    if not ARQ_TESTE_2026.exists():
        raise FileNotFoundError(f"Não encontrei: {ARQ_TESTE_2026}")

    treino_2024_2025 = pd.read_csv(ARQ_TREINO_2024_2025, compression="gzip")
    teste_2026 = pd.read_csv(ARQ_TESTE_2026, compression="gzip")

    df = pd.concat([treino_2024_2025, teste_2026], ignore_index=True)

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

    df["Ano"] = df["DataHora_SP"].dt.year
    df["AnoMes"] = df["DataHora_SP"].dt.strftime("%Y-%m")

    treino_2024 = df[df["Ano"] == 2024].copy()
    validacao_2025 = df[df["Ano"] == 2025].copy()
    teste_2026 = df[df["Ano"] == 2026].copy()

    if treino_2024.empty:
        raise RuntimeError("Treino 2024 vazio.")

    if validacao_2025.empty:
        raise RuntimeError("Validação 2025 vazia.")

    if teste_2026.empty:
        raise RuntimeError("Teste 2026 vazio.")

    return treino_2024, validacao_2025, teste_2026, df


def carregar_features_base(df):
    if not ARQ_FEATURES_BASE.exists():
        raise FileNotFoundError(f"Não encontrei: {ARQ_FEATURES_BASE}")

    with open(ARQ_FEATURES_BASE, "r", encoding="utf-8") as f:
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
            "dias_operados": 0,
            "meses": 0,
            "meses_positivos": 0,
            "meses_negativos": 0,
            "pior_mes": 0.0,
            "melhor_mes": 0.0,
        }

    total = len(df)
    wins = int((df[TARGET_COL] == 1).sum())
    losses = int((df[TARGET_COL] == 0).sum())

    tmp = df.copy()
    tmp["DataDia"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m-%d")
    tmp["AnoMes"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")

    mensal = tmp.groupby("AnoMes")[PONTOS_COL].sum()

    return {
        "nome": nome,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": float(df[PONTOS_COL].sum()),
        "profit_factor": calcular_pf(df),
        "drawdown_trades": calcular_dd(df),
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
        "dias_operados": int(tmp["DataDia"].nunique()),
        "meses": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "melhor_mes": float(mensal.max()) if len(mensal) else 0.0,
    }


def mensal(df, nome):
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["AnoMes"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")

    linhas = []

    for mes, g in tmp.groupby("AnoMes", sort=True):
        r = resumo(g, nome)
        r["AnoMes"] = mes
        linhas.append(r)

    out = pd.DataFrame(linhas)

    if not out.empty:
        out["lucro_acumulado"] = out["lucro_pontos"].cumsum()

    return out


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


def selecionar_features_por_importancia(df_train, features_base):
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
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    return imp


# ============================================================
# TREINO / PREDIÇÃO
# ============================================================

def treinar_global(df_train, df_pred, features, modelo_nome):
    X_train = limpar_X(df_train, features)
    y_train = df_train[TARGET_COL].astype(int)

    X_pred = limpar_X(df_pred, features)

    modelo = criar_modelo(modelo_nome)
    modelo.fit(X_train, y_train)

    pred = df_pred.copy()
    pred["prob_v5_3"] = obter_prob(modelo, X_pred)
    pred["modelo_v5_3"] = modelo_nome
    pred["modo_v5_3"] = "GLOBAL"

    return modelo, pred


def treinar_direcao(df_train, df_pred, features, modelo_nome):
    pred = df_pred.copy()
    pred["prob_v5_3"] = np.nan
    pred["modelo_v5_3"] = modelo_nome
    pred["modo_v5_3"] = "DIRECAO_SEPARADA"

    modelos = {}

    for direcao in ["BUY", "SELL"]:
        tr = df_train[df_train["Direcao"] == direcao].copy()
        idx = df_pred[df_pred["Direcao"] == direcao].index

        if len(tr) < 30 or len(idx) == 0:
            continue

        X_train = limpar_X(tr, features)
        y_train = tr[TARGET_COL].astype(int)

        X_pred = limpar_X(df_pred.loc[idx], features)

        modelo = criar_modelo(modelo_nome)
        modelo.fit(X_train, y_train)

        pred.loc[idx, "prob_v5_3"] = obter_prob(modelo, X_pred)
        modelos[direcao] = modelo

    pred["prob_v5_3"] = pred["prob_v5_3"].fillna(0.0)

    return modelos, pred


def treinar_e_predizer(df_train, df_pred, features, modelo_nome, modo):
    if modo == "GLOBAL":
        return treinar_global(df_train, df_pred, features, modelo_nome)

    if modo == "DIRECAO_SEPARADA":
        return treinar_direcao(df_train, df_pred, features, modelo_nome)

    raise ValueError(f"Modo desconhecido: {modo}")


def avaliar_threshold(pred, threshold, nome):
    aceitos = pred[pred["prob_v5_3"] >= threshold].copy()

    r = resumo(aceitos, nome)

    r["threshold"] = threshold
    r["trades_cortados"] = int(len(pred) - len(aceitos))
    r["wins_cortados"] = int(((pred[TARGET_COL] == 1) & (pred["prob_v5_3"] < threshold)).sum())
    r["losses_cortados"] = int(((pred[TARGET_COL] == 0) & (pred["prob_v5_3"] < threshold)).sum())

    return r


def score_validacao_2025(r):
    score = 0.0

    score += r["lucro_pontos"]
    score += r["profit_factor"] * 350.0
    score += r["winrate"] * 8.0
    score += r["drawdown_trades"] * 0.50
    score += r["pior_mes"] * 0.75

    if r["trades"] < MIN_TRADES_2025:
        score -= 5000.0
        score -= (MIN_TRADES_2025 - r["trades"]) * 100.0

    if r["meses_negativos"] > 0:
        score -= r["meses_negativos"] * 2000.0

    if r["pior_mes"] < -100:
        score -= abs(r["pior_mes"]) * 5.0

    if r["profit_factor"] < 1.50:
        score -= 1500.0

    if r["drawdown_trades"] < -700:
        score -= 1500.0

    return float(score)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("V5.3 - TREINA 2024 | VALIDA 2025 | TESTA 2026")
    print("=====================================================")

    treino_2024, validacao_2025, teste_2026, df_total = carregar_dados()
    features_base = carregar_features_base(df_total)

    print("\nDataset:")
    print("Treino 2024    :", len(treino_2024))
    print("Validação 2025 :", len(validacao_2025))
    print("Teste 2026     :", len(teste_2026))
    print("Features base  :", len(features_base))

    imp = selecionar_features_por_importancia(treino_2024, features_base)
    imp.to_csv(ARQ_IMPORTANCIA, index=False)

    print("\nTop 30 features 2024:")
    print(imp.head(30).to_string(index=False))

    leaderboard = []
    predicoes_2025 = {}
    modelos_2024 = {}
    features_por_chave = {}

    print("\n=====================================================")
    print("FASE 1: TREINA 2024 E VALIDA 2025")
    print("=====================================================")

    for top_n in TOP_FEATURES_LIST:
        features = imp.head(top_n)["feature"].tolist()

        print(f"\n--- TOP {top_n} FEATURES ---")

        for modelo_nome in MODELOS:
            for modo in MODOS:
                chave = f"{modelo_nome}_{modo}_top{top_n}"

                print("Treinando/validando:", chave)

                try:
                    modelo_obj, pred_2025 = treinar_e_predizer(
                        treino_2024,
                        validacao_2025,
                        features,
                        modelo_nome,
                        modo,
                    )

                    predicoes_2025[chave] = pred_2025
                    modelos_2024[chave] = modelo_obj
                    features_por_chave[chave] = features

                    for thr in THRESHOLDS:
                        nome = f"{chave}_thr_{thr:.3f}"
                        r = avaliar_threshold(pred_2025, thr, nome)
                        r["modelo"] = modelo_nome
                        r["modo"] = modo
                        r["top_features"] = top_n
                        r["chave_modelo"] = chave
                        r["score_validacao_2025"] = score_validacao_2025(r)
                        leaderboard.append(r)

                except Exception as e:
                    print("ERRO:", chave, e)

    leaderboard_df = pd.DataFrame(leaderboard)

    if leaderboard_df.empty:
        raise RuntimeError("Leaderboard 2025 vazio.")

    leaderboard_df = leaderboard_df.sort_values("score_validacao_2025", ascending=False).reset_index(drop=True)
    leaderboard_df.to_csv(ARQ_LEADERBOARD_2025, index=False)

    print("\n=====================================================")
    print("LEADERBOARD VALIDAÇÃO 2025 - TOP 40")
    print("=====================================================")

    cols_show = [
        "nome", "modelo", "modo", "top_features", "threshold",
        "trades", "wins", "losses", "winrate", "lucro_pontos",
        "profit_factor", "drawdown_trades", "meses_positivos",
        "meses_negativos", "pior_mes", "trades_cortados",
        "wins_cortados", "losses_cortados", "score_validacao_2025"
    ]

    cols_show = [c for c in cols_show if c in leaderboard_df.columns]
    print(leaderboard_df[cols_show].head(40).to_string(index=False))

    candidatos = leaderboard_df[
        (leaderboard_df["trades"] >= MIN_TRADES_2025)
        & (leaderboard_df["lucro_pontos"] > 0)
        & (leaderboard_df["profit_factor"] >= 1.50)
        & (leaderboard_df["meses_negativos"] <= 3)
        & (leaderboard_df["drawdown_trades"] >= -700)
    ].copy()

    if candidatos.empty:
        print("\nATENÇÃO: nenhum candidato passou critérios mínimos de 2025. Usando melhor score geral.")
        melhor = leaderboard_df.iloc[0].to_dict()
    else:
        candidatos = candidatos.sort_values("score_validacao_2025", ascending=False).reset_index(drop=True)
        melhor = candidatos.iloc[0].to_dict()

    print("\n=====================================================")
    print("MELHOR CONFIG ESCOLHIDA EM 2025")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    chave_melhor = melhor["chave_modelo"]
    threshold_melhor = float(melhor["threshold"])
    features_melhor = features_por_chave[chave_melhor]
    modelo_nome_melhor = melhor["modelo"]
    modo_melhor = melhor["modo"]
    top_features_melhor = int(melhor["top_features"])

    pred_2025_melhor = predicoes_2025[chave_melhor].copy()
    pred_2025_melhor["threshold_usado"] = threshold_melhor
    pred_2025_melhor["aceito_v5_3"] = pred_2025_melhor["prob_v5_3"] >= threshold_melhor
    pred_2025_melhor.to_csv(ARQ_PRED_2025, index=False, compression="gzip")

    mensal_2025 = mensal(
        pred_2025_melhor[pred_2025_melhor["aceito_v5_3"]].copy(),
        "VALIDACAO_2025"
    )

    mensal_2025.to_csv(ARQ_MENSAL_2025, index=False)

    print("\n=====================================================")
    print("MENSAL VALIDAÇÃO 2025 - CONFIG ESCOLHIDA")
    print("=====================================================")
    print(mensal_2025.to_string(index=False))

    print("\n=====================================================")
    print("FASE 2: TREINA 2024+2025 COM CONFIG ESCOLHIDA E TESTA 2026")
    print("=====================================================")

    treino_2024_2025 = pd.concat([treino_2024, validacao_2025], ignore_index=True)
    treino_2024_2025 = treino_2024_2025.sort_values("DataHora_SP").reset_index(drop=True)

    modelo_final, pred_2026 = treinar_e_predizer(
        treino_2024_2025,
        teste_2026,
        features_melhor,
        modelo_nome_melhor,
        modo_melhor,
    )

    pred_2026["threshold_usado"] = threshold_melhor
    pred_2026["aceito_v5_3"] = pred_2026["prob_v5_3"] >= threshold_melhor

    pred_2026.to_csv(ARQ_PRED_2026, index=False, compression="gzip")

    aceitos_2026 = pred_2026[pred_2026["aceito_v5_3"]].copy()
    resultado_2026 = resumo(aceitos_2026, "TESTE_FINAL_2026")

    resultado_2026.update({
        "modelo": modelo_nome_melhor,
        "modo": modo_melhor,
        "top_features": top_features_melhor,
        "threshold": threshold_melhor,
        "chave_modelo": chave_melhor,
        "supera_v4_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARK_V4_2026["lucro_pontos"]),
        "supera_v4_pf": bool(resultado_2026["profit_factor"] > BENCHMARK_V4_2026["profit_factor"]),
        "melhora_v4_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARK_V4_2026["drawdown_trades"]),
        "supera_v5_1_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARK_V5_1_2026["lucro_pontos"]),
        "supera_v5_1_pf": bool(resultado_2026["profit_factor"] > BENCHMARK_V5_1_2026["profit_factor"]),
        "melhora_v5_1_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARK_V5_1_2026["drawdown_trades"]),
    })

    resultado_2026_df = pd.DataFrame([resultado_2026])
    resultado_2026_df.to_csv(ARQ_RESULTADO_2026, index=False)

    mensal_2026 = mensal(aceitos_2026, "TESTE_FINAL_2026")
    mensal_2026.to_csv(ARQ_MENSAL_2026, index=False)

    print("\n=====================================================")
    print("RESULTADO TESTE FINAL 2026 - V5.3")
    print("=====================================================")
    print(pd.Series(resultado_2026).to_string())

    print("\n=====================================================")
    print("MENSAL TESTE FINAL 2026 - V5.3")
    print("=====================================================")
    print(mensal_2026.to_string(index=False))

    joblib.dump(modelo_final, ARQ_MODELO_FINAL)
    joblib.dump(features_melhor, ARQ_FEATURES_FINAL)

    config = {
        "nome": "V5_3_TREINA_2024_VALIDA_2025_TESTA_2026",
        "melhor_config_escolhida_2025": melhor,
        "resultado_teste_final_2026": resultado_2026,
        "benchmark_v4_2026": BENCHMARK_V4_2026,
        "benchmark_v5_1_2026": BENCHMARK_V5_1_2026,
        "features": features_melhor,
        "arquivos": {
            "leaderboard_2025": str(ARQ_LEADERBOARD_2025),
            "resultado_2026": str(ARQ_RESULTADO_2026),
            "mensal_2025": str(ARQ_MENSAL_2025),
            "mensal_2026": str(ARQ_MENSAL_2026),
            "predicoes_2025": str(ARQ_PRED_2025),
            "predicoes_2026": str(ARQ_PRED_2026),
            "modelo_final": str(ARQ_MODELO_FINAL),
            "features_final": str(ARQ_FEATURES_FINAL),
            "importancia_features": str(ARQ_IMPORTANCIA),
        }
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\n=====================================================")
    print("ARQUIVOS GERADOS")
    print("=====================================================")
    print(ARQ_LEADERBOARD_2025)
    print(ARQ_RESULTADO_2026)
    print(ARQ_MENSAL_2025)
    print(ARQ_MENSAL_2026)
    print(ARQ_PRED_2025)
    print(ARQ_PRED_2026)
    print(ARQ_CONFIG)
    print(ARQ_MODELO_FINAL)
    print(ARQ_FEATURES_FINAL)
    print(ARQ_IMPORTANCIA)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()