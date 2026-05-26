import os
import json
import joblib
import warnings

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix


warnings.filterwarnings("ignore")


# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")

ARQUIVO_CANDIDATOS_SCORE = os.path.join(PASTA_V4, "04_v4_score_candidatos.csv.gz")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_V4, "checkpoint_v4_melhor.csv")

ARQUIVO_MODELO = os.path.join(PASTA_V4, "modelo_v4_antiloss.joblib")
ARQUIVO_FEATURES = os.path.join(PASTA_V4, "features_modelo_v4.joblib")
ARQUIVO_CONFIG = os.path.join(PASTA_V4, "config_melhor_v4.json")
ARQUIVO_RELATORIO = os.path.join(PASTA_V4, "relatorio_modelo_v4_salvo.csv")

SPLIT_DATE = pd.Timestamp("2025-07-01")

STOP_BASE = 117.0
STOP_SUFIXO = str(STOP_BASE).replace(".", "_")

TARGET_COL = f"target_win_stop_{STOP_SUFIXO}"
RESULTADO_COL = f"resultado_stop_{STOP_SUFIXO}"


# =====================================================
# FUNÇÕES
# =====================================================

def salvar_csv_seguro(df, caminho):
    temp = caminho + ".tmp"
    df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def detectar_features(df):
    proibidas = {
        "indice_sinal",
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora_SP",
        "Direcao",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "prob_win_v4",
        "take_pontos",
        "stop_pontos",
        "resultado",
        "pontos",
        "dt_entrada",
        "dt_saida",
        "indice_saida",
        "runup",
        "drawdown",
    }

    proibidas_prefixos = [
        "resultado_stop_",
        "pontos_stop_",
        "dt_entrada_stop_",
        "dt_saida_stop_",
        "indice_saida_stop_",
        "runup_stop_",
        "drawdown_stop_",
        "target_win_stop_",
    ]

    features = []

    for col in df.columns:
        if col in proibidas:
            continue

        if any(col.startswith(p) for p in proibidas_prefixos):
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            features.append(col)

    features_extra = [
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "Hora_SP_Decimal",
    ]

    for col in features_extra:
        if col in df.columns and col not in features:
            features.append(col)

    return features


# =====================================================
# CARREGAR DADOS
# =====================================================

print("Carregando candidatos V4 com score...")

if not os.path.exists(ARQUIVO_CANDIDATOS_SCORE):
    raise FileNotFoundError(f"Não encontrei: {ARQUIVO_CANDIDATOS_SCORE}")

cand = pd.read_csv(ARQUIVO_CANDIDATOS_SCORE, compression="gzip")

cand["DataHora_SP"] = pd.to_datetime(cand["DataHora_SP"], errors="coerce")

print("Linhas carregadas:", len(cand))
print("Início:", cand["DataHora_SP"].min())
print("Fim:", cand["DataHora_SP"].max())

if TARGET_COL not in cand.columns:
    raise Exception(f"Coluna alvo não encontrada: {TARGET_COL}")

if RESULTADO_COL not in cand.columns:
    raise Exception(f"Coluna resultado não encontrada: {RESULTADO_COL}")

base = cand[cand[RESULTADO_COL].isin(["WIN", "LOSS"])].copy()

print("Linhas WIN/LOSS:", len(base))
print(base[RESULTADO_COL].value_counts())

feature_cols = detectar_features(base)

print("Features detectadas:", len(feature_cols))

X = base[feature_cols].copy()
y = pd.to_numeric(base[TARGET_COL], errors="coerce").fillna(0).astype(int)

train_mask = base["DataHora_SP"] < SPLIT_DATE

X_train = X[train_mask]
y_train = y[train_mask]

X_test = X[~train_mask]
y_test = y[~train_mask]

print("Treino:", len(X_train))
print("Teste:", len(X_test))


# =====================================================
# TREINAR MODELOS
# =====================================================

modelos = {
    "ExtraTrees_V4": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(
            n_estimators=500,
            max_depth=10,
            min_samples_leaf=4,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ]),

    "RandomForest_V4": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=400,
            max_depth=10,
            min_samples_leaf=4,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ]),

    "HistGradientBoosting_V4": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.035,
            max_leaf_nodes=24,
            l2_regularization=0.25,
            random_state=42
        ))
    ])
}

try:
    from xgboost import XGBClassifier

    modelos["XGBoost_V4"] = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", XGBClassifier(
            n_estimators=450,
            max_depth=4,
            learning_rate=0.035,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1
        ))
    ])

    print("XGBoost encontrado e incluído.")

except Exception:
    print("XGBoost não instalado. Continuando sem ele.")


resultados = []
melhor_modelo = None
melhor_nome = None
melhor_score = -999

for nome, modelo in modelos.items():
    print("\n====================================")
    print("Treinando:", nome)
    print("====================================")

    modelo.fit(X_train, y_train)

    pred = modelo.predict(X_test)

    acc = accuracy_score(y_test, pred)
    bacc = balanced_accuracy_score(y_test, pred)

    print("Accuracy:", acc)
    print("Balanced Accuracy:", bacc)
    print(confusion_matrix(y_test, pred))
    print(classification_report(y_test, pred, zero_division=0))

    resultados.append({
        "modelo": nome,
        "accuracy": acc,
        "balanced_accuracy": bacc,
        "treino_linhas": len(X_train),
        "teste_linhas": len(X_test),
        "features": len(feature_cols),
        "split_date": str(SPLIT_DATE),
        "target_col": TARGET_COL,
        "resultado_col": RESULTADO_COL,
    })

    if bacc > melhor_score:
        melhor_score = bacc
        melhor_modelo = modelo
        melhor_nome = nome


# =====================================================
# SALVAR MODELO, FEATURES E CONFIG
# =====================================================

print("\nMelhor modelo:", melhor_nome)
print("Melhor balanced accuracy:", melhor_score)

joblib.dump(melhor_modelo, ARQUIVO_MODELO)
joblib.dump(feature_cols, ARQUIVO_FEATURES)

print("Modelo salvo:", ARQUIVO_MODELO)
print("Features salvas:", ARQUIVO_FEATURES)

relatorio = pd.DataFrame(resultados)
salvar_csv_seguro(relatorio, ARQUIVO_RELATORIO)

config = {}

if os.path.exists(ARQUIVO_MELHOR_RESUMO):
    melhor = pd.read_csv(ARQUIVO_MELHOR_RESUMO)

    if not melhor.empty:
        config = melhor.iloc[0].to_dict()

config["modelo_salvo"] = ARQUIVO_MODELO
config["features_salvas"] = ARQUIVO_FEATURES
config["modelo_nome"] = melhor_nome
config["balanced_accuracy_modelo"] = float(melhor_score)
config["target_col"] = TARGET_COL
config["resultado_col"] = RESULTADO_COL

with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=4, default=str)

print("Config salva:", ARQUIVO_CONFIG)

print("\n=====================================================")
print("FINALIZADO")
print("=====================================================")
print("Modelo:", ARQUIVO_MODELO)
print("Features:", ARQUIVO_FEATURES)
print("Config:", ARQUIVO_CONFIG)
print("Relatório:", ARQUIVO_RELATORIO)