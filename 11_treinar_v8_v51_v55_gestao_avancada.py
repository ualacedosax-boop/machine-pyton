# -*- coding: utf-8 -*-

from pathlib import Path
import json
import warnings
import re

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_DATASET = BASE_DIR / "saida_v5_filtro_campeao_2024_2025_2026"

ARQ_TREINO_2024_2025 = PASTA_DATASET / "04_dataset_v5_TREINO_2024_2025.csv.gz"
ARQ_TESTE_2026 = PASTA_DATASET / "05_dataset_v5_TESTE_2026.csv.gz"
ARQ_FEATURES_BASE = PASTA_DATASET / "08_features_sugeridas_v5.txt"

PASTA_V5_1 = BASE_DIR / "OPERACIONAL_V5_1_CAMPEA"
ARQ_FEATURES_V5_1 = PASTA_V5_1 / "features_v5_1_campea.joblib"

PASTA_SAIDA = BASE_DIR / "saida_v8_v51_v55_gestao_avancada"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_LEADERBOARD = PASTA_SAIDA / "01_leaderboard_rotacoes_v8.csv"
ARQ_RESUMO_CONFIGS = PASTA_SAIDA / "02_resumo_configs_v8.csv"
ARQ_RESULTADO_2026 = PASTA_SAIDA / "03_resultado_teste_2026_v8.csv"
ARQ_MENSAL_2026 = PASTA_SAIDA / "04_mensal_teste_2026_v8.csv"
ARQ_DIAS_2026 = PASTA_SAIDA / "05_dias_teste_2026_v8.csv"
ARQ_PRED_2026 = PASTA_SAIDA / "06_predicoes_teste_2026_v8.csv.gz"
ARQ_CONFIG = PASTA_SAIDA / "07_config_v8.json"
ARQ_MODELOS_FINAL = PASTA_SAIDA / "modelos_final_v8.joblib"
ARQ_FEATURES_FINAL = PASTA_SAIDA / "features_final_v8.joblib"
ARQ_IMPORTANCIA_V55 = PASTA_SAIDA / "08_importancia_features_v55_v8.csv"

# ============================================================
# CONFIGURAÇÕES
# ============================================================

TARGET_COL = "target_v5_win"
PONTOS_COL = "pontos_v5"

ROTACOES = {
    "A_MAR_JUN_SET_DEZ": [3, 6, 9, 12],
    "B_FEV_MAI_AGO_NOV": [2, 5, 8, 11],
    "C_JAN_ABR_JUL_OUT": [1, 4, 7, 10],
}

# Busca fina em torno da V7 campeã:
# V7: prob_v51_min=0.590, prob_v55_min=0.425, max3, parar após loss true
PROB_V51_MIN_LIST = [round(x, 3) for x in np.arange(0.560, 0.631, 0.0025)]
PROB_V55_MIN_LIST = [round(x, 3) for x in np.arange(0.350, 0.526, 0.005)]

MAX_TRADES_DIA_LIST = [2, 3]
PARAR_APOS_LOSS_LIST = [False, True]
MAX_LOSSES_DIA_LIST = [1, 2]

# Diferença mínima entre prob_v51 e prob_v55.
# Pode ajudar a tirar cenários de conflito entre V5.1 e V5.5.
MIN_GAP_LIST = [-0.20, -0.15, -0.10, -0.05, 0.00, 0.05]

# Filtros de horário. Se não tiver Hora_SP_Decimal no dataset, usa todos.
HORARIOS = [
    (2.00, 6.00),
    (2.00, 5.75),
    (2.25, 6.00),
    (2.50, 6.00),
    (2.00, 5.50),
]

TOP_FEATURES_V55 = 30

MIN_TRADES_VALIDACAO = 300
MIN_TRADES_2026 = 120

BENCHMARKS = {
    "V4_OFICIAL_2026": {
        "trades": 167,
        "wins": 132,
        "losses": 35,
        "winrate": 79.041916,
        "lucro_pontos": 2571.0,
        "profit_factor": 1.627839,
        "drawdown_trades": -582.5,
    },
    "V5_1_2026": {
        "trades": 154,
        "wins": 125,
        "losses": 29,
        "winrate": 81.168831,
        "lucro_pontos": 2919.5,
        "profit_factor": 1.860448,
        "drawdown_trades": -380.5,
    },
    "V5_5_2026": {
        "trades": 102,
        "wins": 86,
        "losses": 16,
        "winrate": 84.313725,
        "lucro_pontos": 2471.0,
        "profit_factor": 2.319979,
        "drawdown_trades": -316.5,
    },
    "V7_2026": {
        "trades": 134,
        "wins": 111,
        "losses": 23,
        "winrate": 82.835821,
        "lucro_pontos": 2914.5,
        "profit_factor": 2.083055,
        "drawdown_trades": -314.0,
    },
}

# ============================================================
# FILTRO ANTI-VAZAMENTO PARA V5.5
# ============================================================

FEATURES_PROIBIDAS_EXATAS = {
    "Ano", "ano", "Mes", "mes", "Mês", "month", "Month", "year", "Year",
    "conId", "conid", "prev_conId", "prev_conid",
    "mes_sp", "prev_mes_sp",
    "Data", "data", "Date", "date", "AnoMes", "ano_mes",
    "contrato", "Contrato", "localSymbol", "localsymbol",
    "symbol", "Symbol", "vencimento", "Vencimento",
    "prob_win_v4", "folga_prob_v4",
}

PADROES_PROIBIDOS = [
    r"(^|_)ano($|_)",
    r"(^|_)year($|_)",
    r"(^|_)mes($|_)",
    r"(^|_)month($|_)",
    r"conid",
    r"contract",
    r"contrato",
    r"local.?symbol",
    r"venc",
    r"expiry",
    r"expiration",
    r"prob_",
    r"target",
    r"resultado",
    r"lucro",
    r"aceito",
]


def feature_eh_vazamento(nome):
    nome_str = str(nome)
    nome_low = nome_str.lower()

    if nome_str in FEATURES_PROIBIDAS_EXATAS:
        return True

    for padrao in PADROES_PROIBIDOS:
        if re.search(padrao, nome_low):
            return True

    return False


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def carregar_dados():
    df_base = pd.read_csv(ARQ_TREINO_2024_2025, compression="gzip")
    df_2026 = pd.read_csv(ARQ_TESTE_2026, compression="gzip")

    for df in [df_base, df_2026]:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        df.dropna(subset=["DataHora_SP"], inplace=True)
        df.sort_values("DataHora_SP", inplace=True)
        df.reset_index(drop=True, inplace=True)

        df["Ano"] = df["DataHora_SP"].dt.year
        df["Mes"] = df["DataHora_SP"].dt.month
        df["AnoMes"] = df["DataHora_SP"].dt.strftime("%Y-%m")
        df["DataDia"] = df["DataHora_SP"].dt.strftime("%Y-%m-%d")

        if "Hora_SP_Decimal" not in df.columns:
            df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0

    df_base = df_base[df_base["Ano"].isin([2024, 2025])].copy()
    df_2026 = df_2026[df_2026["Ano"] == 2026].copy()

    if df_base.empty:
        raise RuntimeError("Base 2024+2025 vazia.")

    if df_2026.empty:
        raise RuntimeError("Teste 2026 vazio.")

    df_total = pd.concat([df_base, df_2026], ignore_index=True)

    return df_base, df_2026, df_total


def carregar_features_v51(df_total):
    features = joblib.load(ARQ_FEATURES_V5_1)
    validas = []

    for col in features:
        if col in df_total.columns and df_total[col].dtype.kind in "biufc":
            validas.append(col)

    if not validas:
        raise RuntimeError("Nenhuma feature V5.1 válida.")

    return validas


def carregar_features_base_sem_vazamento(df_total):
    with open(ARQ_FEATURES_BASE, "r", encoding="utf-8") as f:
        features_originais = [x.strip() for x in f.readlines() if x.strip()]

    validas = []

    for col in features_originais:
        if col not in df_total.columns:
            continue
        if df_total[col].dtype.kind not in "biufc":
            continue
        if feature_eh_vazamento(col):
            continue
        validas.append(col)

    validas = sorted(set(validas))

    if not validas:
        raise RuntimeError("Nenhuma feature sem vazamento válida.")

    return validas


def limpar_X(df, features):
    X = df[features].copy()
    X = X.replace([np.inf, -np.inf], 0)
    X = X.fillna(0)

    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    return X


def criar_rf():
    return RandomForestClassifier(
        n_estimators=600,
        max_depth=5,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def criar_rf_importancia():
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=6,
        min_samples_leaf=6,
        class_weight="balanced",
        random_state=123,
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


def dias_operados(df):
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()
    tmp["DataDia"] = pd.to_datetime(tmp["DataHora_SP"], errors="coerce").dt.strftime("%Y-%m-%d")

    dias = tmp.groupby("DataDia").agg(
        trades_no_dia=("DataDia", "size"),
        wins=(TARGET_COL, lambda x: int((x == 1).sum())),
        losses=(TARGET_COL, lambda x: int((x == 0).sum())),
        lucro_pontos=(PONTOS_COL, "sum"),
    ).reset_index()

    dias["winrate"] = dias["wins"] / dias["trades_no_dia"] * 100
    dias["lucro_acumulado"] = dias["lucro_pontos"].cumsum()

    return dias


# ============================================================
# TREINO DOS MODELOS
# ============================================================

def treinar_v51_direcao(df_train, df_pred, features_v51):
    pred = df_pred.copy()
    pred["prob_v51"] = np.nan

    modelos = {}

    for direcao in ["BUY", "SELL"]:
        tr = df_train[df_train["Direcao"] == direcao].copy()
        idx = df_pred[df_pred["Direcao"] == direcao].index

        if len(tr) < 30 or len(idx) == 0:
            continue

        X_train = limpar_X(tr, features_v51)
        y_train = tr[TARGET_COL].astype(int)

        X_pred = limpar_X(df_pred.loc[idx], features_v51)

        modelo = criar_rf()
        modelo.fit(X_train, y_train)

        pred.loc[idx, "prob_v51"] = modelo.predict_proba(X_pred)[:, 1]
        modelos[direcao] = modelo

    pred["prob_v51"] = pred["prob_v51"].fillna(0.0)

    return modelos, pred


def selecionar_features_v55(df_train, features_sem_vazamento):
    X = limpar_X(df_train, features_sem_vazamento)
    y = df_train[TARGET_COL].astype(int)

    modelo = criar_rf_importancia()
    modelo.fit(X, y)

    imp = pd.DataFrame({
        "feature": features_sem_vazamento,
        "importance": modelo.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    features_v55 = imp.head(TOP_FEATURES_V55)["feature"].tolist()

    return features_v55, imp


def treinar_v55_global(df_train, df_pred, features_v55):
    X_train = limpar_X(df_train, features_v55)
    y_train = df_train[TARGET_COL].astype(int)

    X_pred = limpar_X(df_pred, features_v55)

    modelo = criar_rf()
    modelo.fit(X_train, y_train)

    pred = df_pred.copy()
    pred["prob_v55"] = modelo.predict_proba(X_pred)[:, 1]

    return modelo, pred


def gerar_predicoes_modelos(df_train, df_pred, features_v51, features_sem_vazamento):
    modelos_v51, pred_v51 = treinar_v51_direcao(df_train, df_pred, features_v51)

    features_v55, imp_v55 = selecionar_features_v55(df_train, features_sem_vazamento)
    modelo_v55, pred_v55 = treinar_v55_global(df_train, df_pred, features_v55)

    pred = df_pred.copy()
    pred["prob_v51"] = pred_v51["prob_v51"].values
    pred["prob_v55"] = pred_v55["prob_v55"].values
    pred["gap_v51_v55"] = pred["prob_v51"] - pred["prob_v55"]

    modelos = {
        "v51": modelos_v51,
        "v55": modelo_v55,
    }

    features = {
        "v51": features_v51,
        "v55": features_v55,
    }

    return modelos, features, imp_v55, pred


# ============================================================
# AVALIAÇÃO V8
# ============================================================

def aplicar_gestao_dia(
    pred,
    prob_v51_min,
    prob_v55_min,
    max_trades_dia,
    parar_apos_loss,
    max_losses_dia,
    min_gap,
    hora_inicio,
    hora_fim,
):
    temp = pred.copy()

    temp["passou_prob_v51"] = temp["prob_v51"] >= prob_v51_min
    temp["passou_prob_v55"] = temp["prob_v55"] >= prob_v55_min
    temp["passou_gap"] = temp["gap_v51_v55"] >= min_gap
    temp["passou_horario"] = (
        (temp["Hora_SP_Decimal"] >= hora_inicio) &
        (temp["Hora_SP_Decimal"] <= hora_fim)
    )

    temp["candidato_v8"] = (
        temp["passou_prob_v51"] &
        temp["passou_prob_v55"] &
        temp["passou_gap"] &
        temp["passou_horario"]
    )

    temp = temp.sort_values("DataHora_SP").reset_index(drop=True)

    aceito = []
    trades_dia = {}
    losses_dia = {}

    for _, row in temp.iterrows():
        data = str(row["DataDia"])

        if data not in trades_dia:
            trades_dia[data] = 0
            losses_dia[data] = 0

        entra = bool(row["candidato_v8"])

        if entra and trades_dia[data] >= max_trades_dia:
            entra = False

        if entra and losses_dia[data] >= max_losses_dia:
            entra = False

        if entra and parar_apos_loss and losses_dia[data] > 0:
            entra = False

        aceito.append(entra)

        if entra:
            trades_dia[data] += 1

            if int(row[TARGET_COL]) == 0:
                losses_dia[data] += 1

    temp["aceito_v8"] = aceito

    return temp


def avaliar_v8(
    pred,
    prob_v51_min,
    prob_v55_min,
    max_trades_dia,
    parar_apos_loss,
    max_losses_dia,
    min_gap,
    hora_inicio,
    hora_fim,
    nome,
):
    temp = aplicar_gestao_dia(
        pred=pred,
        prob_v51_min=prob_v51_min,
        prob_v55_min=prob_v55_min,
        max_trades_dia=max_trades_dia,
        parar_apos_loss=parar_apos_loss,
        max_losses_dia=max_losses_dia,
        min_gap=min_gap,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
    )

    aceitos = temp[temp["aceito_v8"]].copy()

    r = resumo(aceitos, nome)

    r["prob_v51_min"] = prob_v51_min
    r["prob_v55_min"] = prob_v55_min
    r["max_trades_dia"] = max_trades_dia
    r["parar_apos_loss"] = bool(parar_apos_loss)
    r["max_losses_dia"] = max_losses_dia
    r["min_gap"] = min_gap
    r["hora_inicio"] = hora_inicio
    r["hora_fim"] = hora_fim

    r["trades_cortados"] = int(len(temp) - len(aceitos))
    r["wins_cortados"] = int(((temp[TARGET_COL] == 1) & (~temp["aceito_v8"])).sum())
    r["losses_cortados"] = int(((temp[TARGET_COL] == 0) & (~temp["aceito_v8"])).sum())

    return r, temp


def score_config(r):
    score = 0.0

    score += r["lucro_total_validacao"]
    score += r["pf_medio_validacao"] * 400.0
    score += r["winrate_medio_validacao"] * 10.0
    score += r["dd_pior_validacao"] * 0.90
    score += r["pior_mes_geral"] * 1.20

    if r["rotacoes_negativas"] > 0:
        score -= r["rotacoes_negativas"] * 3500.0

    if r["meses_negativos_total"] > 0:
        score -= r["meses_negativos_total"] * 1400.0

    if r["trades_total_validacao"] < MIN_TRADES_VALIDACAO:
        score -= 5000.0
        score -= (MIN_TRADES_VALIDACAO - r["trades_total_validacao"]) * 100.0

    if r["pf_medio_validacao"] < 1.60:
        score -= 2500.0

    if r["dd_pior_validacao"] < -700:
        score -= 2500.0

    # Bônus para configurações equilibradas
    if r["trades_total_validacao"] >= 400:
        score += 500.0

    if r["rotacoes_negativas"] == 0 and r["meses_negativos_total"] <= 2:
        score += 1000.0

    return float(score)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("V8 - V5.1 MOTOR + V5.5 FILTRO + GESTÃO AVANÇADA")
    print("=====================================================")

    df_base, df_2026, df_total = carregar_dados()
    features_v51 = carregar_features_v51(df_total)
    features_sem_vazamento = carregar_features_base_sem_vazamento(df_total)

    print("\nDataset:")
    print("Base 2024+2025:", len(df_base))
    print("Teste 2026    :", len(df_2026))
    print("Features V5.1 :", len(features_v51))
    print("Features sem vazamento para V5.5:", len(features_sem_vazamento))

    linhas = []

    print("\n=====================================================")
    print("FASE 1: ROTAÇÕES")
    print("=====================================================")

    for nome_rotacao, meses_validacao in ROTACOES.items():
        meses_treino = [m for m in range(1, 13) if m not in meses_validacao]

        df_train = df_base[df_base["Mes"].isin(meses_treino)].copy()
        df_valid = df_base[df_base["Mes"].isin(meses_validacao)].copy()

        print("\n-----------------------------------------------------")
        print("Rotação:", nome_rotacao)
        print("Meses validação:", meses_validacao)
        print("Treino:", len(df_train), "| Validação:", len(df_valid))
        print("-----------------------------------------------------")

        _, _, _, pred_valid = gerar_predicoes_modelos(
            df_train,
            df_valid,
            features_v51,
            features_sem_vazamento,
        )

        total_configs_rot = (
            len(PROB_V51_MIN_LIST) *
            len(PROB_V55_MIN_LIST) *
            len(MAX_TRADES_DIA_LIST) *
            len(PARAR_APOS_LOSS_LIST) *
            len(MAX_LOSSES_DIA_LIST) *
            len(MIN_GAP_LIST) *
            len(HORARIOS)
        )

        print("Configurações nesta rotação:", total_configs_rot)

        contador = 0

        for prob_v51_min in PROB_V51_MIN_LIST:
            for prob_v55_min in PROB_V55_MIN_LIST:
                for max_trades_dia in MAX_TRADES_DIA_LIST:
                    for parar_apos_loss in PARAR_APOS_LOSS_LIST:
                        for max_losses_dia in MAX_LOSSES_DIA_LIST:
                            for min_gap in MIN_GAP_LIST:
                                for hora_inicio, hora_fim in HORARIOS:
                                    contador += 1

                                    nome = (
                                        f"V8_{nome_rotacao}"
                                        f"_v51_{prob_v51_min:.3f}"
                                        f"_v55_{prob_v55_min:.3f}"
                                        f"_max{max_trades_dia}"
                                        f"_stoplossdia_{int(parar_apos_loss)}"
                                        f"_maxloss{max_losses_dia}"
                                        f"_gap{min_gap:.2f}"
                                        f"_h{hora_inicio:.2f}_{hora_fim:.2f}"
                                    )

                                    r, _ = avaliar_v8(
                                        pred_valid,
                                        prob_v51_min,
                                        prob_v55_min,
                                        max_trades_dia,
                                        parar_apos_loss,
                                        max_losses_dia,
                                        min_gap,
                                        hora_inicio,
                                        hora_fim,
                                        nome,
                                    )

                                    r["rotacao"] = nome_rotacao
                                    r["meses_validacao"] = ",".join([str(x) for x in meses_validacao])
                                    r["chave_config"] = (
                                        f"v51_{prob_v51_min:.3f}"
                                        f"_v55_{prob_v55_min:.3f}"
                                        f"_max{max_trades_dia}"
                                        f"_stoplossdia_{int(parar_apos_loss)}"
                                        f"_maxloss{max_losses_dia}"
                                        f"_gap{min_gap:.2f}"
                                        f"_h{hora_inicio:.2f}_{hora_fim:.2f}"
                                    )

                                    linhas.append(r)

        print("Configurações processadas:", contador)

    leaderboard = pd.DataFrame(linhas)

    if leaderboard.empty:
        raise RuntimeError("Leaderboard vazio.")

    leaderboard.to_csv(ARQ_LEADERBOARD, index=False)

    print("\nTotal de linhas no leaderboard:", len(leaderboard))

    print("\n=====================================================")
    print("AGREGANDO CONFIGURAÇÕES")
    print("=====================================================")

    configs = []

    for chave, g in leaderboard.groupby("chave_config", sort=False):
        rotacoes_total = g["rotacao"].nunique()
        lucro_total = float(g["lucro_pontos"].sum())
        trades_total = int(g["trades"].sum())
        wins_total = int(g["wins"].sum())
        losses_total = int(g["losses"].sum())

        pf_vals = g["profit_factor"].replace(999.0, np.nan)
        pf_medio = float(pf_vals.mean())
        if np.isnan(pf_medio):
            pf_medio = 999.0

        winrate_medio = float(g["winrate"].mean())
        dd_pior = float(g["drawdown_trades"].min())
        pior_mes_geral = float(g["pior_mes"].min())
        meses_neg_total = int(g["meses_negativos"].sum())
        rotacoes_negativas = int((g["lucro_pontos"] <= 0).sum())

        primeira = g.iloc[0].to_dict()

        r = {
            "chave_config": chave,
            "prob_v51_min": float(primeira["prob_v51_min"]),
            "prob_v55_min": float(primeira["prob_v55_min"]),
            "max_trades_dia": int(primeira["max_trades_dia"]),
            "parar_apos_loss": bool(primeira["parar_apos_loss"]),
            "max_losses_dia": int(primeira["max_losses_dia"]),
            "min_gap": float(primeira["min_gap"]),
            "hora_inicio": float(primeira["hora_inicio"]),
            "hora_fim": float(primeira["hora_fim"]),
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
        }

        r["score_config"] = score_config(r)
        configs.append(r)

    resumo_configs = pd.DataFrame(configs)
    resumo_configs = resumo_configs.sort_values("score_config", ascending=False).reset_index(drop=True)
    resumo_configs.to_csv(ARQ_RESUMO_CONFIGS, index=False)

    print("\n=====================================================")
    print("RESUMO CONFIGS V8 - TOP 40")
    print("=====================================================")

    cols = [
        "chave_config",
        "prob_v51_min",
        "prob_v55_min",
        "max_trades_dia",
        "parar_apos_loss",
        "max_losses_dia",
        "min_gap",
        "hora_inicio",
        "hora_fim",
        "rotacoes_total",
        "trades_total_validacao",
        "wins_total_validacao",
        "losses_total_validacao",
        "winrate_medio_validacao",
        "lucro_total_validacao",
        "pf_medio_validacao",
        "dd_pior_validacao",
        "pior_mes_geral",
        "meses_negativos_total",
        "rotacoes_negativas",
        "score_config",
    ]

    print(resumo_configs[cols].head(40).to_string(index=False))

    candidatos = resumo_configs[
        (resumo_configs["rotacoes_total"] == 3)
        & (resumo_configs["rotacoes_negativas"] == 0)
        & (resumo_configs["meses_negativos_total"] <= 2)
        & (resumo_configs["trades_total_validacao"] >= MIN_TRADES_VALIDACAO)
        & (resumo_configs["pf_medio_validacao"] >= 1.60)
        & (resumo_configs["dd_pior_validacao"] >= -700)
    ].copy()

    if candidatos.empty:
        print("\nATENÇÃO: nenhum candidato passou todos os critérios. Usando melhor score geral.")
        melhor = resumo_configs.iloc[0].to_dict()
    else:
        candidatos = candidatos.sort_values("score_config", ascending=False).reset_index(drop=True)
        melhor = candidatos.iloc[0].to_dict()

    print("\n=====================================================")
    print("MELHOR CONFIG V8 ESCOLHIDA NAS ROTAÇÕES")
    print("=====================================================")
    print(pd.Series(melhor).to_string())

    prob_v51_min = float(melhor["prob_v51_min"])
    prob_v55_min = float(melhor["prob_v55_min"])
    max_trades_dia = int(melhor["max_trades_dia"])
    parar_apos_loss = bool(melhor["parar_apos_loss"])
    max_losses_dia = int(melhor["max_losses_dia"])
    min_gap = float(melhor["min_gap"])
    hora_inicio = float(melhor["hora_inicio"])
    hora_fim = float(melhor["hora_fim"])

    print("\n=====================================================")
    print("FASE 2: TREINA 2024+2025 COMPLETO E TESTA 2026")
    print("=====================================================")

    modelos_final, features_final, imp_v55_final, pred_2026 = gerar_predicoes_modelos(
        df_base,
        df_2026,
        features_v51,
        features_sem_vazamento,
    )

    imp_v55_final.to_csv(ARQ_IMPORTANCIA_V55, index=False)

    pred_2026_final = aplicar_gestao_dia(
        pred=pred_2026,
        prob_v51_min=prob_v51_min,
        prob_v55_min=prob_v55_min,
        max_trades_dia=max_trades_dia,
        parar_apos_loss=parar_apos_loss,
        max_losses_dia=max_losses_dia,
        min_gap=min_gap,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
    )

    pred_2026_final["prob_v51_min"] = prob_v51_min
    pred_2026_final["prob_v55_min"] = prob_v55_min
    pred_2026_final["max_trades_dia"] = max_trades_dia
    pred_2026_final["parar_apos_loss"] = parar_apos_loss
    pred_2026_final["max_losses_dia"] = max_losses_dia
    pred_2026_final["min_gap"] = min_gap
    pred_2026_final["hora_inicio"] = hora_inicio
    pred_2026_final["hora_fim"] = hora_fim

    pred_2026_final.to_csv(ARQ_PRED_2026, index=False, compression="gzip")

    aceitos_2026 = pred_2026_final[pred_2026_final["aceito_v8"]].copy()
    resultado_2026 = resumo(aceitos_2026, "TESTE_FINAL_2026_V8")

    resultado_2026.update({
        "prob_v51_min": prob_v51_min,
        "prob_v55_min": prob_v55_min,
        "max_trades_dia": max_trades_dia,
        "parar_apos_loss": parar_apos_loss,
        "max_losses_dia": max_losses_dia,
        "min_gap": min_gap,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "supera_v4_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARKS["V4_OFICIAL_2026"]["lucro_pontos"]),
        "supera_v4_pf": bool(resultado_2026["profit_factor"] > BENCHMARKS["V4_OFICIAL_2026"]["profit_factor"]),
        "melhora_v4_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARKS["V4_OFICIAL_2026"]["drawdown_trades"]),
        "supera_v5_1_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARKS["V5_1_2026"]["lucro_pontos"]),
        "supera_v5_1_pf": bool(resultado_2026["profit_factor"] > BENCHMARKS["V5_1_2026"]["profit_factor"]),
        "melhora_v5_1_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARKS["V5_1_2026"]["drawdown_trades"]),
        "supera_v5_5_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARKS["V5_5_2026"]["lucro_pontos"]),
        "supera_v5_5_pf": bool(resultado_2026["profit_factor"] > BENCHMARKS["V5_5_2026"]["profit_factor"]),
        "melhora_v5_5_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARKS["V5_5_2026"]["drawdown_trades"]),
        "supera_v7_lucro": bool(resultado_2026["lucro_pontos"] > BENCHMARKS["V7_2026"]["lucro_pontos"]),
        "supera_v7_pf": bool(resultado_2026["profit_factor"] > BENCHMARKS["V7_2026"]["profit_factor"]),
        "melhora_v7_dd": bool(resultado_2026["drawdown_trades"] >= BENCHMARKS["V7_2026"]["drawdown_trades"]),
    })

    pd.DataFrame([resultado_2026]).to_csv(ARQ_RESULTADO_2026, index=False)

    mensal_2026 = mensal(aceitos_2026, "TESTE_FINAL_2026_V8")
    mensal_2026.to_csv(ARQ_MENSAL_2026, index=False)

    dias_2026 = dias_operados(aceitos_2026)
    dias_2026.to_csv(ARQ_DIAS_2026, index=False)

    print("\n=====================================================")
    print("RESULTADO TESTE FINAL 2026 - V8")
    print("=====================================================")
    print(pd.Series(resultado_2026).to_string())

    print("\n=====================================================")
    print("MENSAL TESTE FINAL 2026 - V8")
    print("=====================================================")
    print(mensal_2026.to_string(index=False))

    print("\n=====================================================")
    print("DISTRIBUIÇÃO DIÁRIA V8 - 2026")
    print("=====================================================")
    print(dias_2026.to_string(index=False))

    print("\n=====================================================")
    print("COMPARAÇÃO FINAL")
    print("=====================================================")

    comparacao = []

    for nome, b in BENCHMARKS.items():
        linha = {"nome": nome}
        linha.update(b)
        comparacao.append(linha)

    comparacao.append({
        "nome": "V8",
        "trades": resultado_2026["trades"],
        "wins": resultado_2026["wins"],
        "losses": resultado_2026["losses"],
        "winrate": resultado_2026["winrate"],
        "lucro_pontos": resultado_2026["lucro_pontos"],
        "profit_factor": resultado_2026["profit_factor"],
        "drawdown_trades": resultado_2026["drawdown_trades"],
    })

    comparacao_df = pd.DataFrame(comparacao)
    print(comparacao_df.to_string(index=False))

    joblib.dump(modelos_final, ARQ_MODELOS_FINAL)
    joblib.dump(features_final, ARQ_FEATURES_FINAL)

    config = {
        "nome": "V8_V51_MOTOR_V55_FILTRO_GESTAO_AVANCADA",
        "descricao": "Busca fina com V5.1 como motor, V5.5 como filtro, gap, horário e gestão diária.",
        "melhor_config_rotacoes": melhor,
        "resultado_teste_2026": resultado_2026,
        "benchmarks": BENCHMARKS,
        "features": features_final,
        "arquivos": {
            "leaderboard": str(ARQ_LEADERBOARD),
            "resumo_configs": str(ARQ_RESUMO_CONFIGS),
            "resultado_2026": str(ARQ_RESULTADO_2026),
            "mensal_2026": str(ARQ_MENSAL_2026),
            "dias_2026": str(ARQ_DIAS_2026),
            "predicoes_2026": str(ARQ_PRED_2026),
            "modelos_final": str(ARQ_MODELOS_FINAL),
            "features_final": str(ARQ_FEATURES_FINAL),
            "importancia_v55": str(ARQ_IMPORTANCIA_V55),
        }
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4, default=str)

    print("\n=====================================================")
    print("ARQUIVOS GERADOS")
    print("=====================================================")
    print(ARQ_LEADERBOARD)
    print(ARQ_RESUMO_CONFIGS)
    print(ARQ_RESULTADO_2026)
    print(ARQ_MENSAL_2026)
    print(ARQ_DIAS_2026)
    print(ARQ_PRED_2026)
    print(ARQ_CONFIG)
    print(ARQ_MODELOS_FINAL)
    print(ARQ_FEATURES_FINAL)
    print(ARQ_IMPORTANCIA_V55)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()