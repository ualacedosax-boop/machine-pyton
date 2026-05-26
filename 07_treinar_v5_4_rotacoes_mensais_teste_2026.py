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

PASTA_SAIDA = BASE_DIR / "saida_v5_4_rotacoes_mensais_teste_2026"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD_ROTACOES = PASTA_SAIDA / "01_leaderboard_rotacoes_v5_4.csv"
ARQ_RESUMO_CONFIGS = PASTA_SAIDA / "02_resumo_configs_v5_4.csv"
ARQ_RESULTADO_2026 = PASTA_SAIDA / "03_resultado_teste_2026_v5_4.csv"
ARQ_MENSAL_ROTACOES = PASTA_SAIDA / "04_mensal_rotacoes_v5_4.csv"
ARQ_MENSAL_2026 = PASTA_SAIDA / "05_mensal_teste_2026_v5_4.csv"
ARQ_PRED_2026 = PASTA_SAIDA / "06_predicoes_teste_2026_v5_4.csv.gz"
ARQ_CONFIG = PASTA_SAIDA / "07_config_v5_4.json"
ARQ_MODELO_FINAL = PASTA_SAIDA / "modelo_final_v5_4.joblib"
ARQ_FEATURES_FINAL = PASTA_SAIDA / "features_final_v5_4.joblib"
ARQ_IMPORTANCIA = PASTA_SAIDA / "08_importancia_features_v5_4.csv"

# ============================================================
# CONFIGURAÇÕES
# ============================================================

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

TOP_FEATURES_LIST = [30, 50, 75, 100, 150]
THRESHOLDS = [round(x, 3) for x in np.arange(0.500, 0.651, 0.005)]

MODELOS = ["RandomForest", "ExtraTrees", "LogisticRegression"]
MODOS = ["GLOBAL", "DIRECAO_SEPARADA"]

ROTACOES = {
    "A_MAR_JUN_SET_DEZ": [3, 6, 9, 12],
    "B_FEV_MAI_AGO_NOV": [2, 5, 8, 11],
    "C_JAN_ABR_JUL_OUT": [1, 4, 7, 10],
}

BENCHMARK_V4_2026 = {
    "nome": "V4_OFICIAL_2026",
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

BENCHMARK_V5_3_2026 = {
    "nome": "V5_3_2026",
    "trades": 95,
    "wins": 81,
    "losses": 14,
    "winrate": 85.263158,
    "lucro_pontos": 2452.5,
    "profit_factor": 2.497253,
    "drawdown_trades": -300.5,
}

MIN_TRADES_ROTACAO = 35
MIN_TRADES_2026 = 120


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def carregar_dados():
    if not ARQ_TREINO_2024_2025.exists():
        raise FileNotFoundError(f"Não encontrei: {ARQ_TREINO_2024_2025}")

    if not ARQ_TESTE_2026.exists():
        raise FileNotFoundError(f"Não encontrei: {ARQ_TESTE_2026}")

    treino_2024_2025 = pd.read_csv(ARQ_TREINO_2024_2025, compression="gzip")
    teste_2026 = pd.read_csv(ARQ_TESTE_2026, compression="gzip")

    for df in [treino_2024_2025, teste_2026]:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        df.dropna(subset=["DataHora_SP"], inplace=True)
        df.sort_values("DataHora_SP", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df["Ano"] = df["DataHora_SP"].dt.year
        df["Mes"] = df["DataHora_SP"].dt.month
        df["AnoMes"] = df["DataHora_SP"].dt.strftime("%Y-%m")

    treino_2024_2025 = treino_2024_2025[
        treino_2024_2025["Ano"].isin([2024, 2025])
    ].copy()

    teste_2026 = teste_2026[teste_2026["Ano"] == 2026].copy()

    if treino_2024_2025.empty:
        raise RuntimeError("Treino 2024+2025 vazio.")

    if teste_2026.empty:
        raise RuntimeError("Teste 2026 vazio.")

    total = pd.concat([treino_2024_2025, teste_2026], ignore_index=True)

    return treino_2024_2025, teste_2026, total


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

    tmp = df.copy()
    tmp["DataDia"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m-%d")
    tmp["AnoMes"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")

    mensal = tmp.groupby("AnoMes")[PONTOS_COL].sum()

    total = len(df)
    wins = int((df[TARGET_COL] == 1).sum())
    losses = int((df[TARGET_COL] == 0).sum())

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


def mensal(df, nome, rotacao=None):
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["AnoMes"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m")

    linhas = []

    for mes, g in tmp.groupby("AnoMes", sort=True):
        r = resumo(g, nome)
        r["AnoMes"] = mes
        if rotacao is not None:
            r["rotacao"] = rotacao
        linhas.append(r)

    out = pd.DataFrame(linhas)

    if not out.empty:
        out["lucro_acumulado"] = out["lucro_pontos"].cumsum()

    return out


# ============================================================
# MODELOS
# ============================================================

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


def treinar_global(df_train, df_pred, features, modelo_nome):
    X_train = limpar_X(df_train, features)
    y_train = df_train[TARGET_COL].astype(int)

    X_pred = limpar_X(df_pred, features)

    modelo = criar_modelo(modelo_nome)
    modelo.fit(X_train, y_train)

    pred = df_pred.copy()
    pred["prob_v5_4"] = obter_prob(modelo, X_pred)
    pred["modelo_v5_4"] = modelo_nome
    pred["modo_v5_4"] = "GLOBAL"

    return modelo, pred


def treinar_direcao(df_train, df_pred, features, modelo_nome):
    pred = df_pred.copy()
    pred["prob_v5_4"] = np.nan
    pred["modelo_v5_4"] = modelo_nome
    pred["modo_v5_4"] = "DIRECAO_SEPARADA"

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

        pred.loc[idx, "prob_v5_4"] = obter_prob(modelo, X_pred)
        modelos[direcao] = modelo

    pred["prob_v5_4"] = pred["prob_v5_4"].fillna(0.0)

    return modelos, pred


def treinar_e_predizer(df_train, df_pred, features, modelo_nome, modo):
    if modo == "GLOBAL":
        return treinar_global(df_train, df_pred, features, modelo_nome)

    if modo == "DIRECAO_SEPARADA":
        return treinar_direcao(df_train, df_pred, features, modelo_nome)

    raise ValueError(f"Modo desconhecido: {modo}")


def avaliar_threshold(pred, threshold, nome):
    aceitos = pred[pred["prob_v5_4"] >= threshold].copy()

    r = resumo(aceitos, nome)

    r["threshold"] = threshold
    r["trades_cortados"] = int(len(pred) - len(aceitos))
    r["wins_cortados"] = int(((pred[TARGET_COL] == 1) & (pred["prob_v5_4"] < threshold)).sum())
    r["losses_cortados"] = int(((pred[TARGET_COL] == 0) & (pred["prob_v5_4"] < threshold)).sum())

    return r


def score_rotacao(r):
    score = 0.0

    score += r["lucro_pontos"]
    score += r["profit_factor"] * 250.0
    score += r["winrate"] * 6.0
    score += r["drawdown_trades"] * 0.45
    score += r["pior_mes"] * 0.80

    if r["trades"] < MIN_TRADES_ROTACAO:
        score -= 3000.0
        score -= (MIN_TRADES_ROTACAO - r["trades"]) * 100.0

    if r["lucro_pontos"] <= 0:
        score -= 2000.0

    if r["meses_negativos"] > 0:
        score -= r["meses_negativos"] * 1500.0

    if r["profit_factor"] < 1.40:
        score -= 1000.0

    return float(score)


def score_config_agregado(r):
    score = 0.0

    score += r["lucro_total_validacao"]
    score += r["pf_medio_validacao"] * 400.0
    score += r["winrate_medio_validacao"] * 10.0
    score += r["dd_pior_validacao"] * 0.70
    score += r["pior_mes_geral"] * 1.20

    if r["rotacoes_negativas"] > 0:
        score -= r["rotacoes_negativas"] * 3000.0

    if r["meses_negativos_total"] > 0:
        score -= r["meses_negativos_total"] * 1200.0

    if r["trades_total_validacao"] < 180:
        score -= 4000.0
        score -= (180 - r["trades_total_validacao"]) * 80.0

    if r["pf_medio_validacao"] < 1.50:
        score -= 2000.0

    return float(score)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("V5.4 - ROTAÇÕES MENSAIS 2024/2025 | TESTE FINAL 2026")
    print("=====================================================")

    df_base, df_2026, df_total = carregar_dados()
    features_base = carregar_features_base(df_total)

    print("\nDataset:")
    print("Base 2024+2025:", len(df_base))
    print("Teste 2026    :", len(df_2026))
    print("Features base :", len(features_base))

    imp = selecionar_features_por_importancia(df_base, features_base)
    imp.to_csv(ARQ_IMPORTANCIA, index=False)

    print("\nTop 30 features:")
    print(imp.head(30).to_string(index=False))

    leaderboard_linhas = []
    mensais_linhas = []

    print("\n=====================================================")
    print("FASE 1: ROTAÇÕES 2024/2025")
    print("=====================================================")

    for top_n in TOP_FEATURES_LIST:
        features = imp.head(top_n)["feature"].tolist()

        print(f"\n================ TOP {top_n} FEATURES ================")

        for modelo_nome in MODELOS:
            for modo in MODOS:
                chave_modelo = f"{modelo_nome}_{modo}_top{top_n}"

                for nome_rotacao, meses_validacao in ROTACOES.items():
                    meses_treino = [m for m in range(1, 13) if m not in meses_validacao]

                    df_train = df_base[df_base["Mes"].isin(meses_treino)].copy()
                    df_valid = df_base[df_base["Mes"].isin(meses_validacao)].copy()

                    if df_train.empty or df_valid.empty:
                        continue

                    print(f"Treinando: {chave_modelo} | Rotação: {nome_rotacao}")

                    try:
                        _, pred_valid = treinar_e_predizer(
                            df_train,
                            df_valid,
                            features,
                            modelo_nome,
                            modo,
                        )

                        for thr in THRESHOLDS:
                            nome = f"{chave_modelo}_{nome_rotacao}_thr_{thr:.3f}"
                            r = avaliar_threshold(pred_valid, thr, nome)

                            r["modelo"] = modelo_nome
                            r["modo"] = modo
                            r["top_features"] = top_n
                            r["chave_config"] = f"{modelo_nome}_{modo}_top{top_n}_thr_{thr:.3f}"
                            r["chave_modelo"] = chave_modelo
                            r["rotacao"] = nome_rotacao
                            r["meses_validacao"] = ",".join([str(x) for x in meses_validacao])
                            r["score_rotacao"] = score_rotacao(r)

                            leaderboard_linhas.append(r)

                            aceitos = pred_valid[pred_valid["prob_v5_4"] >= thr].copy()
                            m = mensal(aceitos, nome, rotacao=nome_rotacao)
                            if not m.empty:
                                mensais_linhas.append(m)

                    except Exception as e:
                        print("ERRO:", chave_modelo, nome_rotacao, e)

    leaderboard = pd.DataFrame(leaderboard_linhas)

    if leaderboard.empty:
        raise RuntimeError("Leaderboard vazio.")

    leaderboard.to_csv(ARQ_LEADERBOARD_ROTACOES, index=False)

    mensal_rotacoes = pd.concat(mensais_linhas, ignore_index=True) if mensais_linhas else pd.DataFrame()
    mensal_rotacoes.to_csv(ARQ_MENSAL_ROTACOES, index=False)

    print("\n=====================================================")
    print("AGREGANDO CONFIGURAÇÕES")
    print("=====================================================")

    configs = []

    for chave_config, g in leaderboard.groupby("chave_config", sort=False):
        rotacoes_total = g["rotacao"].nunique()
        lucro_total = float(g["lucro_pontos"].sum())
        trades_total = int(g["trades"].sum())
        wins_total = int(g["wins"].sum())
        losses_total = int(g["losses"].sum())
        pf_medio = float(g["profit_factor"].replace(999.0, np.nan).mean())
        if np.isnan(pf_medio):
            pf_medio = 999.0
        winrate_medio = float(g["winrate"].mean())
        dd_pior = float(g["drawdown_trades"].min())
        pior_mes_geral = float(g["pior_mes"].min())
        meses_neg_total = int(g["meses_negativos"].sum())
        rotacoes_negativas = int((g["lucro_pontos"] <= 0).sum())

        primeira = g.iloc[0].to_dict()

        r = {
            "chave_config": chave_config,
            "modelo": primeira["modelo"],
            "modo": primeira["modo"],
            "top_features": int(primeira["top_features"]),
            "threshold": float(primeira["threshold"]),
            "rotacoes_total": rotacoes_total,
            "trades_total_validacao": trades_total,
            "wins_total_validacao": wins_total,
            "losses_total_validacao": losses_total,
            "winrate_medio_validacao": winrate_medio,
            "lucro_total_validacao": lucro_total,
            "pf_medio_validacao": pf_medio,
            "dd_pior_validacao": dd_pior,
            "pior_mes_geral": pior_mes_geral,
            "meses_negativos_total": meses_neg_total,
            "rotacoes_negativas": rotacoes_negativas,
            "score_config": 0.0,
        }

        r["score_config"] = score_config_agregado(r)
        configs.append(r)

    resumo_configs = pd.DataFrame(configs)
    resumo_configs = resumo_configs.sort_values("score_config", ascending=False).reset_index(drop=True)
    resumo_configs.to_csv(ARQ_RESUMO_CONFIGS, index=False)

    print("\n=====================================================")
    print("RESUMO CONFIGS V5.4 - TOP 40")
    print("=====================================================")

    cols_cfg = [
        "chave_config", "modelo", "modo", "top_features", "threshold",
        "rotacoes_total", "trades_total_validacao", "wins_total_validacao",
        "losses_total_validacao", "winrate_medio_validacao",
        "lucro_total_validacao", "pf_medio_validacao", "dd_pior_validacao",
        "pior_mes_geral", "meses_negativos_total", "rotacoes_negativas",
        "score_config",
    ]

    print(resumo_configs[cols_cfg].head(40).to_string(index=False))

    candidatos = resumo_configs[
        (resumo_configs["rotacoes_total"] == 3)
        & (resumo_configs["rotacoes_negativas"] == 0)
        & (resumo_configs["meses_negativos_total"] <= 2)
        & (resumo_configs["trades_total_validacao"] >= 180)
        & (resumo_configs["pf_medio_validacao"] >= 1.50)
        & (resumo_configs["dd_pior_validacao"] >= -700)
    ].copy()

    if candidatos.empty:
        print("\nATENÇÃO: nenhum candidato passou todos os critérios. Usando melhor score geral.")
        melhor = resumo_configs.iloc[0].to_dict()
    else:
        candidatos = candidatos.sort_values("score_config", ascending=False).reset_index(drop=True)
        melhor = candidatos.iloc[0].to_dict()

    print("\n=====================================================")
    print("MELHOR CONFIG V5.4 ESCOLHIDA NAS ROTAÇÕES")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    modelo_nome = melhor["modelo"]
    modo = melhor["modo"]
    top_features = int(melhor["top_features"])
    threshold = float(melhor["threshold"])
    features_melhor = imp.head(top_features)["feature"].tolist()

    print("\n=====================================================")
    print("FASE 2: TREINA 2024+2025 COMPLETO E TESTA 2026")
    print("=====================================================")

    modelo_final, pred_2026 = treinar_e_predizer(
        df_base,
        df_2026,
        features_melhor,
        modelo_nome,
        modo,
    )

    pred_2026["threshold_usado"] = threshold
    pred_2026["aceito_v5_4"] = pred_2026["prob_v5_4"] >= threshold

    pred_2026.to_csv(ARQ_PRED_2026, index=False, compression="gzip")

    aceitos_2026 = pred_2026[pred_2026["aceito_v5_4"]].copy()
    resultado_2026 = resumo(aceitos_2026, "TESTE_FINAL_2026_V5_4")

    resultado_2026.update({
        "modelo": modelo_nome,
        "modo": modo,
        "top_features": top_features,
        "threshold": threshold,
        "supera_v4_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARK_V4_2026["lucro_pontos"]),
        "supera_v4_pf": bool(resultado_2026["profit_factor"] > BENCHMARK_V4_2026["profit_factor"]),
        "melhora_v4_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARK_V4_2026["drawdown_trades"]),
        "supera_v5_1_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARK_V5_1_2026["lucro_pontos"]),
        "supera_v5_1_pf": bool(resultado_2026["profit_factor"] > BENCHMARK_V5_1_2026["profit_factor"]),
        "melhora_v5_1_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARK_V5_1_2026["drawdown_trades"]),
        "supera_v5_3_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARK_V5_3_2026["lucro_pontos"]),
        "supera_v5_3_pf": bool(resultado_2026["profit_factor"] > BENCHMARK_V5_3_2026["profit_factor"]),
        "melhora_v5_3_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARK_V5_3_2026["drawdown_trades"]),
    })

    resultado_2026_df = pd.DataFrame([resultado_2026])
    resultado_2026_df.to_csv(ARQ_RESULTADO_2026, index=False)

    mensal_2026 = mensal(aceitos_2026, "TESTE_FINAL_2026_V5_4")
    mensal_2026.to_csv(ARQ_MENSAL_2026, index=False)

    print("\n=====================================================")
    print("RESULTADO TESTE FINAL 2026 - V5.4")
    print("=====================================================")
    print(pd.Series(resultado_2026).to_string())

    print("\n=====================================================")
    print("MENSAL TESTE FINAL 2026 - V5.4")
    print("=====================================================")
    print(mensal_2026.to_string(index=False))

    print("\n=====================================================")
    print("COMPARAÇÃO FINAL")
    print("=====================================================")

    comparacao = pd.DataFrame([
        BENCHMARK_V4_2026,
        BENCHMARK_V5_1_2026,
        BENCHMARK_V5_3_2026,
        {
            "nome": "V5_4",
            "trades": resultado_2026["trades"],
            "wins": resultado_2026["wins"],
            "losses": resultado_2026["losses"],
            "winrate": resultado_2026["winrate"],
            "lucro_pontos": resultado_2026["lucro_pontos"],
            "profit_factor": resultado_2026["profit_factor"],
            "drawdown_trades": resultado_2026["drawdown_trades"],
        }
    ])

    print(comparacao.to_string(index=False))

    joblib.dump(modelo_final, ARQ_MODELO_FINAL)
    joblib.dump(features_melhor, ARQ_FEATURES_FINAL)

    config = {
        "nome": "V5_4_ROTACOES_MENSAIS_TESTE_2026",
        "rotacoes": ROTACOES,
        "melhor_config_rotacoes": melhor,
        "resultado_teste_2026": resultado_2026,
        "benchmarks": {
            "v4_2026": BENCHMARK_V4_2026,
            "v5_1_2026": BENCHMARK_V5_1_2026,
            "v5_3_2026": BENCHMARK_V5_3_2026,
        },
        "features": features_melhor,
        "arquivos": {
            "leaderboard_rotacoes": str(ARQ_LEADERBOARD_ROTACOES),
            "resumo_configs": str(ARQ_RESUMO_CONFIGS),
            "resultado_2026": str(ARQ_RESULTADO_2026),
            "mensal_rotacoes": str(ARQ_MENSAL_ROTACOES),
            "mensal_2026": str(ARQ_MENSAL_2026),
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
    print(ARQ_LEADERBOARD_ROTACOES)
    print(ARQ_RESUMO_CONFIGS)
    print(ARQ_RESULTADO_2026)
    print(ARQ_MENSAL_ROTACOES)
    print(ARQ_MENSAL_2026)
    print(ARQ_PRED_2026)
    print(ARQ_CONFIG)
    print(ARQ_MODELO_FINAL)
    print(ARQ_FEATURES_FINAL)
    print(ARQ_IMPORTANCIA)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()