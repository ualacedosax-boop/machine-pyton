# -*- coding: utf-8 -*-

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_ENTRADA = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"

ARQ_TREINO = PASTA_ENTRADA / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE = PASTA_ENTRADA / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES_SUGERIDAS = PASTA_ENTRADA / "08_features_sugeridas_v5.txt"

PASTA_SAIDA = BASE_DIR / "saida_v5_treino_2024_2025_teste_2026"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD = PASTA_SAIDA / "01_leaderboard_v5_2026.csv"
ARQ_PREDICOES_2026 = PASTA_SAIDA / "02_predicoes_v5_2026.csv.gz"
ARQ_MELHOR_CONFIG = PASTA_SAIDA / "03_melhor_config_v5.json"
ARQ_MODELO = PASTA_SAIDA / "modelo_v5_filtro_antiloss.joblib"
ARQ_FEATURES_MODELO = PASTA_SAIDA / "features_v5_filtro_antiloss.joblib"


# ============================================================
# BENCHMARK V4 CAMPEAO 2026
# ============================================================

BENCHMARK = {
    "nome": "V4_CAMPEAO_2026",
    "trades": 167,
    "wins": 132,
    "losses": 35,
    "winrate": 79.041916,
    "lucro_pontos": 2571.0,
    "profit_factor": 1.627839,
    "drawdown_trades": -582.5,
}


# ============================================================
# CONFIGURACOES
# ============================================================

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

MIN_TRADES_2026 = 130

THRESHOLDS = [
    0.50,
    0.52,
    0.54,
    0.56,
    0.58,
    0.60,
    0.62,
    0.64,
    0.66,
    0.68,
    0.70,
    0.72,
    0.74,
    0.76,
    0.78,
    0.80,
]


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def carregar_dataset(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho}")

    df = pd.read_csv(caminho, compression="gzip")

    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        df = df.sort_values("DataHora_SP").reset_index(drop=True)

    return df


def carregar_features_sugeridas(df_treino: pd.DataFrame, df_teste: pd.DataFrame) -> list:
    if ARQ_FEATURES_SUGERIDAS.exists():
        with open(ARQ_FEATURES_SUGERIDAS, "r", encoding="utf-8") as f:
            features = [linha.strip() for linha in f.readlines() if linha.strip()]
    else:
        features = []

    if not features:
        excluir_prefixos = [
            "resultado_",
            "pontos_",
            "target_",
            "dt_saida",
            "indice_saida",
            "runup_stop",
            "drawdown_stop",
            "DataHora",
            "Data",
            "AnoMes",
            "base_ano",
        ]

        excluir_exatos = {
            TARGET_COL,
            PONTOS_COL,
            "resultado_stop_117_0",
            "pontos_stop_117_0",
            "target_win_stop_117_0",
            "dt_saida_stop_117_0",
            "indice_saida_stop_117_0",
        }

        for col in df_treino.columns:
            if col in excluir_exatos:
                continue

            if any(str(col).startswith(pref) for pref in excluir_prefixos):
                continue

            if df_treino[col].dtype.kind in "biufc":
                features.append(col)

    features_validas = []

    for col in features:
        if col in df_treino.columns and col in df_teste.columns:
            if df_treino[col].dtype.kind in "biufc":
                features_validas.append(col)

    features_validas = sorted(set(features_validas))

    if not features_validas:
        raise RuntimeError("Nenhuma feature valida encontrada para treinar a V5.")

    return features_validas


def limpar_X(df: pd.DataFrame, features: list) -> pd.DataFrame:
    X = df[features].copy()
    X = X.replace([np.inf, -np.inf], 0)
    X = X.fillna(0)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    return X


def calcular_profit_factor(df: pd.DataFrame) -> float:
    ganhos = df.loc[df[PONTOS_COL] > 0, PONTOS_COL].sum()
    perdas = abs(df.loc[df[PONTOS_COL] < 0, PONTOS_COL].sum())

    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0

    return float(ganhos / perdas)


def calcular_drawdown_trades(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0

    equity = df[PONTOS_COL].cumsum()
    topo = equity.cummax()
    dd = equity - topo

    return float(dd.min())


def resumir_trades(df: pd.DataFrame, nome: str) -> dict:
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
    pf = calcular_profit_factor(df)
    dd = calcular_drawdown_trades(df)

    meses = 0
    meses_positivos = 0
    meses_negativos = 0

    if "DataHora_SP" in df.columns:
        temp = df.copy()
        temp["AnoMes"] = pd.to_datetime(temp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")
        mensal = temp.groupby("AnoMes")[PONTOS_COL].sum()
        meses = int(mensal.shape[0])
        meses_positivos = int((mensal > 0).sum())
        meses_negativos = int((mensal < 0).sum())

    return {
        "nome": nome,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "drawdown_trades": dd,
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
        "meses": meses,
        "meses_positivos": meses_positivos,
        "meses_negativos": meses_negativos,
    }


def avaliar_threshold(df_pred: pd.DataFrame, threshold: float, modelo_nome: str) -> dict:
    aceitos = df_pred[df_pred["prob_v5"] >= threshold].copy()
    resumo = resumir_trades(aceitos, f"{modelo_nome}_thr_{threshold:.2f}")

    resumo.update({
        "modelo": modelo_nome,
        "threshold": threshold,
        "trades_cortados": int(len(df_pred) - len(aceitos)),
        "wins_cortados": int(((df_pred[TARGET_COL] == 1) & (df_pred["prob_v5"] < threshold)).sum()),
        "losses_cortados": int(((df_pred[TARGET_COL] == 0) & (df_pred["prob_v5"] < threshold)).sum()),
        "passa_min_trades": bool(resumo["trades"] >= MIN_TRADES_2026),
        "supera_lucro": bool(resumo["lucro_pontos"] > BENCHMARK["lucro_pontos"]),
        "supera_pf": bool(resumo["profit_factor"] > BENCHMARK["profit_factor"]),
        "melhora_dd": bool(resumo["drawdown_trades"] >= BENCHMARK["drawdown_trades"]),
    })

    # Score de ranking conservador
    score = 0.0
    score += resumo["lucro_pontos"]
    score += resumo["profit_factor"] * 300.0
    score += resumo["winrate"] * 10.0
    score += resumo["drawdown_trades"] * 0.50  # drawdown negativo penaliza
    score -= max(0, MIN_TRADES_2026 - resumo["trades"]) * 30.0

    if resumo["trades"] < MIN_TRADES_2026:
        score -= 5000.0

    if resumo["lucro_pontos"] <= BENCHMARK["lucro_pontos"]:
        score -= 1000.0

    if resumo["profit_factor"] <= BENCHMARK["profit_factor"]:
        score -= 500.0

    resumo["score_ranking"] = float(score)

    return resumo


def criar_modelos():
    modelos = {}

    modelos["HistGradientBoosting"] = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.04,
        max_leaf_nodes=15,
        l2_regularization=0.10,
        random_state=42,
    )

    modelos["HistGradientBoosting_mais_forte"] = HistGradientBoostingClassifier(
        max_iter=400,
        learning_rate=0.03,
        max_leaf_nodes=21,
        l2_regularization=0.20,
        random_state=42,
    )

    modelos["RandomForest"] = RandomForestClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    modelos["ExtraTrees"] = ExtraTreesClassifier(
        n_estimators=500,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    modelos["LogisticRegression"] = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
        ))
    ])

    return modelos


def obter_probabilidade(modelo, X):
    if hasattr(modelo, "predict_proba"):
        proba = modelo.predict_proba(X)

        if proba.shape[1] == 2:
            return proba[:, 1]

        return proba[:, -1]

    pred = modelo.predict(X)
    return pred.astype(float)


def metricas_classificacao(modelo, X_treino, y_treino, X_teste, y_teste):
    pred_train = modelo.predict(X_treino)
    pred_test = modelo.predict(X_teste)

    out = {
        "acc_treino": float(accuracy_score(y_treino, pred_train)),
        "bal_acc_treino": float(balanced_accuracy_score(y_treino, pred_train)),
        "acc_teste": float(accuracy_score(y_teste, pred_test)),
        "bal_acc_teste": float(balanced_accuracy_score(y_teste, pred_test)),
    }

    try:
        proba_test = obter_probabilidade(modelo, X_teste)
        out["auc_teste"] = float(roc_auc_score(y_teste, proba_test))
    except Exception:
        out["auc_teste"] = 0.0

    return out


def salvar_json(obj, caminho: Path):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("02 - TREINAR V5 FILTRO ANTI-LOSS")
    print("=====================================================")

    print("\nArquivos:")
    print("Treino:", ARQ_TREINO)
    print("Teste :", ARQ_TESTE)

    print("\nBenchmark V4 campeao 2026:")
    for k, v in BENCHMARK.items():
        print(f"{k}: {v}")

    treino = carregar_dataset(ARQ_TREINO)
    teste = carregar_dataset(ARQ_TESTE)

    print("\nDataset carregado:")
    print("Treino 2024+2025:", len(treino))
    print("Teste 2026:", len(teste))

    resumo_treino = resumir_trades(treino, "TREINO_2024_2025_BASE_V4")
    resumo_teste = resumir_trades(teste, "TESTE_2026_BASE_V4")

    print("\nResumo base V4:")
    print(pd.DataFrame([resumo_treino, resumo_teste]).to_string(index=False))

    features = carregar_features_sugeridas(treino, teste)

    print("\nFeatures usadas na V5:")
    print("Total:", len(features))
    print(features)

    X_treino = limpar_X(treino, features)
    y_treino = treino[TARGET_COL].astype(int)

    X_teste = limpar_X(teste, features)
    y_teste = teste[TARGET_COL].astype(int)

    modelos = criar_modelos()

    leaderboard = []
    predicoes_por_modelo = {}
    modelos_treinados = {}

    for nome, modelo in modelos.items():
        print("\n=====================================================")
        print("Treinando modelo:", nome)
        print("=====================================================")

        modelo.fit(X_treino, y_treino)

        metricas = metricas_classificacao(modelo, X_treino, y_treino, X_teste, y_teste)

        print("Metricas classificacao:")
        print(pd.Series(metricas).to_string())

        prob_v5 = obter_probabilidade(modelo, X_teste)

        df_pred = teste.copy()
        df_pred["modelo_v5"] = nome
        df_pred["prob_v5"] = prob_v5

        predicoes_por_modelo[nome] = df_pred
        modelos_treinados[nome] = modelo

        for thr in THRESHOLDS:
            linha = avaliar_threshold(df_pred, thr, nome)
            linha.update(metricas)
            leaderboard.append(linha)

    leaderboard_df = pd.DataFrame(leaderboard)
    leaderboard_df = leaderboard_df.sort_values("score_ranking", ascending=False).reset_index(drop=True)

    leaderboard_df.to_csv(ARQ_LEADERBOARD, index=False)

    print("\n=====================================================")
    print("LEADERBOARD V5 - TESTE FINAL 2026")
    print("=====================================================")
    print(leaderboard_df.head(30).to_string(index=False))

    melhor = leaderboard_df.iloc[0].to_dict()
    melhor_modelo_nome = melhor["modelo"]
    melhor_threshold = float(melhor["threshold"])

    print("\n=====================================================")
    print("MELHOR CONFIG V5")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    df_melhor_pred = predicoes_por_modelo[melhor_modelo_nome].copy()
    df_melhor_pred["aceito_v5"] = df_melhor_pred["prob_v5"] >= melhor_threshold
    df_melhor_pred.to_csv(ARQ_PREDICOES_2026, index=False, compression="gzip")

    joblib.dump(modelos_treinados[melhor_modelo_nome], ARQ_MODELO)
    joblib.dump(features, ARQ_FEATURES_MODELO)

    config = {
        "nome": "V5_FILTRO_ANTILOSS_2024_2025_TESTE_2026",
        "modelo_v5": melhor_modelo_nome,
        "threshold_v5": melhor_threshold,
        "features": features,
        "benchmark_v4_campeao_2026": BENCHMARK,
        "melhor_resultado_2026": melhor,
        "arquivos": {
            "modelo_v5": str(ARQ_MODELO),
            "features_v5": str(ARQ_FEATURES_MODELO),
            "leaderboard": str(ARQ_LEADERBOARD),
            "predicoes_2026": str(ARQ_PREDICOES_2026),
        },
        "criterios_aceite": {
            "min_trades_2026": MIN_TRADES_2026,
            "lucro_maior_que": BENCHMARK["lucro_pontos"],
            "profit_factor_maior_que": BENCHMARK["profit_factor"],
            "drawdown_maior_ou_igual_que": BENCHMARK["drawdown_trades"],
        }
    }

    salvar_json(config, ARQ_MELHOR_CONFIG)

    print("\nArquivos gerados:")
    print(ARQ_LEADERBOARD)
    print(ARQ_PREDICOES_2026)
    print(ARQ_MELHOR_CONFIG)
    print(ARQ_MODELO)
    print(ARQ_FEATURES_MODELO)

    print("\nComparacao contra V4 campeao:")
    print("V4 campeao 2026:")
    print(pd.Series(BENCHMARK).to_string())
    print("\nMelhor V5 2026:")
    print(pd.Series(melhor).to_string())

    print("\nATENCAO:")
    print("A V5 so deve ser aceita se superar lucro, PF e nao cortar trades demais.")


if __name__ == "__main__":
    main()