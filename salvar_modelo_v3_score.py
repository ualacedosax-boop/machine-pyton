import os
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix


warnings.filterwarnings("ignore")


# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V3 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")

ARQUIVO_DATASET_ML = os.path.join(PASTA_V3, "02_v3_dataset_ml_treino.csv.gz")
ARQUIVO_SCORE_TODOS_CANDLES = os.path.join(PASTA_V3, "05_v3_score_todos_candles.csv.gz")

ARQUIVO_MODELO_V3 = os.path.join(PASTA_V3, "modelo_v3_score.joblib")
ARQUIVO_FEATURES_V3 = os.path.join(PASTA_V3, "features_v3_score.joblib")
ARQUIVO_CONFIG_V3 = os.path.join(PASTA_V3, "config_modelo_v3_score.json")
ARQUIVO_RELATORIO_V3 = os.path.join(PASTA_V3, "06_v3_relatorio_modelo_salvo.csv")
ARQUIVO_SCORE_REGERADO = os.path.join(PASTA_V3, "07_v3_score_regerado_todos_candles.csv.gz")
ARQUIVO_COMPARACAO_SCORE = os.path.join(PASTA_V3, "08_v3_comparacao_score_original_regerado.csv")

SPLIT_DATE = pd.Timestamp("2025-07-01")
RANDOM_STATE = 42


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def salvar_csv_seguro(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(temp, index=False, encoding="utf-8-sig", compression="gzip")
    else:
        df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def salvar_json_seguro(obj, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4, default=str)

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def detectar_coluna_alvo(df):
    candidatas = [
        "Label_Num",
        "label_num",
        "target",
        "Target",
        "classe",
        "Classe",
        "y",
        "Y",
        "Label",
        "label",
        "Sinal",
        "Sinal_ML",
        "Direcao",
        "direcao",
    ]

    for col in candidatas:
        if col in df.columns:
            valores = set(df[col].dropna().unique())

            # Caso já seja 0, 1, 2
            if valores.issubset({0, 1, 2, 0.0, 1.0, 2.0}):
                return col

            # Caso seja texto
            valores_txt = {str(v).upper().strip() for v in valores}
            if valores_txt.issubset({"NONE", "BUY", "SELL", "COMPRA", "VENDA"}):
                return col

    # Tenta achar por padrão
    for col in df.columns:
        c = col.lower()
        if "label" in c or "target" in c or "classe" in c or "sinal" in c:
            return col

    raise Exception("Não consegui detectar a coluna alvo do dataset V3.")


def converter_alvo_para_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").fillna(0).astype(int)

    mapa = {
        "NONE": 0,
        "0": 0,
        "BUY": 1,
        "COMPRA": 1,
        "1": 1,
        "SELL": 2,
        "VENDA": 2,
        "2": 2,
    }

    return serie.astype(str).str.upper().str.strip().map(mapa).fillna(0).astype(int)


def detectar_features(df, target_col):
    proibidas = {
        target_col,
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora",
        "Hora_SP",
        "time",
        "Time",
        "date",
        "Date",
        "datetime",
        "DateTime",
        "Label",
        "label",
        "Label_Num",
        "label_num",
        "Label_Nome",
        "Sinal",
        "Sinal_ML",
        "Direcao",
        "direcao",
        "resultado",
        "Resultado",
        "contrato",
        "localSymbol",
    }

    # OHLCV pode ou não entrar no modelo original.
    # Aqui vamos deixar OHLCV fora por segurança, porque no score salvo do V3 eles aparecem só como referência.
    proibidas.update({
        "open",
        "high",
        "low",
        "close",
        "volume",
    })

    proibidas_prefixos = [
        "score_",
        "prob_",
        "resultado_stop_",
        "pontos_stop_",
        "target_win_stop_",
        "dt_entrada_stop_",
        "dt_saida_stop_",
        "indice_saida_stop_",
        "runup_stop_",
        "drawdown_stop_",
    ]

    features = []

    for col in df.columns:
        if col in proibidas:
            continue

        if any(col.startswith(p) for p in proibidas_prefixos):
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            nunique = df[col].nunique(dropna=True)
            if nunique > 1:
                features.append(col)

    if not features:
        raise Exception("Nenhuma feature numérica detectada para treinar o V3.")

    return features


def preparar_datas(df):
    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    elif "time" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["time"], errors="coerce")
    elif "date" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["DataHora_SP"] = pd.NaT

    return df


def criar_modelos():
    modelos = {
        "ExtraTrees_V3": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=500,
                max_depth=14,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1
            ))
        ]),

        "RandomForest_V3": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=500,
                max_depth=14,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1
            ))
        ]),

        "HistGradientBoosting_V3": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingClassifier(
                max_iter=350,
                learning_rate=0.035,
                max_leaf_nodes=31,
                l2_regularization=0.20,
                random_state=RANDOM_STATE
            ))
        ]),
    }

    return modelos


def gerar_scores(modelo, df, feature_cols):
    dataset_score = df.copy()

    for col in feature_cols:
        if col not in dataset_score.columns:
            dataset_score[col] = np.nan

    X_score = dataset_score[feature_cols]

    probas = modelo.predict_proba(X_score)
    classes = list(modelo.named_steps["model"].classes_)

    dataset_score["score_NONE"] = 0.0
    dataset_score["score_BUY"] = 0.0
    dataset_score["score_SELL"] = 0.0

    for i, classe in enumerate(classes):
        if classe == 0:
            dataset_score["score_NONE"] = probas[:, i]
        elif classe == 1:
            dataset_score["score_BUY"] = probas[:, i]
        elif classe == 2:
            dataset_score["score_SELL"] = probas[:, i]

    dataset_score["Sinal_ML"] = "NONE"

    dataset_score.loc[
        (dataset_score["score_BUY"] >= 0.70) &
        (dataset_score["score_BUY"] > dataset_score["score_SELL"]),
        "Sinal_ML"
    ] = "BUY"

    dataset_score.loc[
        (dataset_score["score_SELL"] >= 0.70) &
        (dataset_score["score_SELL"] > dataset_score["score_BUY"]),
        "Sinal_ML"
    ] = "SELL"

    return dataset_score


def comparar_score_original(score_regerado):
    if not os.path.exists(ARQUIVO_SCORE_TODOS_CANDLES):
        print("Arquivo original de score V3 não encontrado para comparação.")
        return pd.DataFrame()

    print("\nComparando com score original V3...")

    original = pd.read_csv(ARQUIVO_SCORE_TODOS_CANDLES, compression="gzip")
    original = preparar_datas(original)

    cols_comp = ["DataHora_SP", "score_BUY", "score_SELL", "score_NONE", "Sinal_ML"]

    for col in cols_comp:
        if col not in original.columns:
            original[col] = np.nan
        if col not in score_regerado.columns:
            score_regerado[col] = np.nan

    orig = original[cols_comp].copy()
    reg = score_regerado[cols_comp].copy()

    orig["DataHora_SP"] = pd.to_datetime(orig["DataHora_SP"], errors="coerce")
    reg["DataHora_SP"] = pd.to_datetime(reg["DataHora_SP"], errors="coerce")

    comp = orig.merge(
        reg,
        on="DataHora_SP",
        how="inner",
        suffixes=("_original", "_regerado")
    )

    if comp.empty:
        print("Não houve interseção de datas para comparar.")
        return pd.DataFrame()

    comp["diff_score_BUY_abs"] = (comp["score_BUY_original"] - comp["score_BUY_regerado"]).abs()
    comp["diff_score_SELL_abs"] = (comp["score_SELL_original"] - comp["score_SELL_regerado"]).abs()
    comp["diff_score_NONE_abs"] = (comp["score_NONE_original"] - comp["score_NONE_regerado"]).abs()
    comp["sinal_igual"] = comp["Sinal_ML_original"].astype(str) == comp["Sinal_ML_regerado"].astype(str)

    resumo = pd.DataFrame([{
        "linhas_original": len(original),
        "linhas_regerado": len(score_regerado),
        "linhas_comparadas": len(comp),
        "media_diff_score_BUY_abs": comp["diff_score_BUY_abs"].mean(),
        "media_diff_score_SELL_abs": comp["diff_score_SELL_abs"].mean(),
        "media_diff_score_NONE_abs": comp["diff_score_NONE_abs"].mean(),
        "pct_sinal_igual": comp["sinal_igual"].mean() * 100,
        "sinais_buy_original": int((original["Sinal_ML"] == "BUY").sum()) if "Sinal_ML" in original.columns else np.nan,
        "sinais_sell_original": int((original["Sinal_ML"] == "SELL").sum()) if "Sinal_ML" in original.columns else np.nan,
        "sinais_buy_regerado": int((score_regerado["Sinal_ML"] == "BUY").sum()),
        "sinais_sell_regerado": int((score_regerado["Sinal_ML"] == "SELL").sum()),
    }])

    salvar_csv_seguro(resumo, ARQUIVO_COMPARACAO_SCORE, compactado=False)

    print("\nResumo comparação score:")
    print(resumo.T)

    return resumo


# =====================================================
# MAIN
# =====================================================

def main():
    print("=====================================================")
    print("SALVAR MODELO V3 SCORE")
    print("=====================================================")

    if not os.path.exists(ARQUIVO_DATASET_ML):
        raise FileNotFoundError(f"Não encontrei: {ARQUIVO_DATASET_ML}")

    print("Carregando dataset V3...")
    dataset = pd.read_csv(ARQUIVO_DATASET_ML, compression="gzip")
    dataset = preparar_datas(dataset)

    print("Linhas dataset:", len(dataset))
    print("Colunas:", len(dataset.columns))
    print("Início:", dataset["DataHora_SP"].min())
    print("Fim:", dataset["DataHora_SP"].max())

    target_col = detectar_coluna_alvo(dataset)
    print("Coluna alvo detectada:", target_col)

    y = converter_alvo_para_numero(dataset[target_col])

    print("\nDistribuição alvo:")
    print(y.value_counts().sort_index())

    feature_cols = detectar_features(dataset, target_col)
    print("Features detectadas:", len(feature_cols))

    X = dataset[feature_cols].copy()

    if dataset["DataHora_SP"].notna().sum() > 0:
        train_mask = dataset["DataHora_SP"] < SPLIT_DATE
    else:
        print("DataHora_SP não encontrada. Usando split 70/30 por ordem.")
        corte = int(len(dataset) * 0.70)
        train_mask = pd.Series(False, index=dataset.index)
        train_mask.iloc[:corte] = True

    X_train = X[train_mask]
    y_train = y[train_mask]

    X_test = X[~train_mask]
    y_test = y[~train_mask]

    print("Treino:", len(X_train))
    print("Teste:", len(X_test))

    modelos = criar_modelos()

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
        print("Matriz:")
        print(confusion_matrix(y_test, pred))
        print(classification_report(y_test, pred, zero_division=0))

        resultados.append({
            "modelo": nome,
            "accuracy": acc,
            "balanced_accuracy": bacc,
            "linhas_treino": len(X_train),
            "linhas_teste": len(X_test),
            "features": len(feature_cols),
            "target_col": target_col,
        })

        if bacc > melhor_score:
            melhor_score = bacc
            melhor_modelo = modelo
            melhor_nome = nome

    print("\n=====================================================")
    print("MELHOR MODELO V3")
    print("=====================================================")
    print("Modelo:", melhor_nome)
    print("Balanced Accuracy:", melhor_score)

    joblib.dump(melhor_modelo, ARQUIVO_MODELO_V3)
    joblib.dump(feature_cols, ARQUIVO_FEATURES_V3)

    print("Modelo salvo:", ARQUIVO_MODELO_V3)
    print("Features salvas:", ARQUIVO_FEATURES_V3)

    relatorio = pd.DataFrame(resultados).sort_values("balanced_accuracy", ascending=False)
    salvar_csv_seguro(relatorio, ARQUIVO_RELATORIO_V3, compactado=False)

    config = {
        "modelo_v3": melhor_nome,
        "balanced_accuracy": float(melhor_score),
        "target_col": target_col,
        "features": len(feature_cols),
        "arquivo_modelo": ARQUIVO_MODELO_V3,
        "arquivo_features": ARQUIVO_FEATURES_V3,
        "split_date": str(SPLIT_DATE),
        "classes_modelo": list(map(int, melhor_modelo.named_steps["model"].classes_)),
        "mapa_classes": {
            "0": "NONE",
            "1": "BUY",
            "2": "SELL"
        }
    }

    salvar_json_seguro(config, ARQUIVO_CONFIG_V3)

    print("\nGerando score regenerado para conferência...")
    score_regerado = gerar_scores(melhor_modelo, dataset, feature_cols)

    salvar_csv_seguro(score_regerado, ARQUIVO_SCORE_REGERADO, compactado=True)

    comparar_score_original(score_regerado)

    print("\n=====================================================")
    print("FINALIZADO")
    print("=====================================================")
    print("Modelo V3:", ARQUIVO_MODELO_V3)
    print("Features V3:", ARQUIVO_FEATURES_V3)
    print("Config V3:", ARQUIVO_CONFIG_V3)
    print("Score regerado:", ARQUIVO_SCORE_REGERADO)
    print("Comparação:", ARQUIVO_COMPARACAO_SCORE)


if __name__ == "__main__":
    main()