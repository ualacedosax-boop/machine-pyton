import pandas as pd
import numpy as np
import os
import time
import shutil
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict


# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_SCORE = r"saida_ml_entradas_video\06_score_todos_candles.csv"

PASTA_SAIDA = "saida_ml_entradas_video"
os.makedirs(PASTA_SAIDA, exist_ok=True)

# =====================================================
# CHECKPOINTS EM PASTA SEPARADA
# =====================================================

PASTA_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoints_anti_loss")
os.makedirs(PASTA_CHECKPOINT, exist_ok=True)

PASTA_BACKUP = os.path.join(PASTA_CHECKPOINT, "backups")
os.makedirs(PASTA_BACKUP, exist_ok=True)

ARQUIVO_CHECKPOINT = os.path.join(PASTA_CHECKPOINT, "checkpoint_anti_loss.csv")
ARQUIVO_CHECKPOINT_TRADES_BASE = os.path.join(PASTA_CHECKPOINT, "checkpoint_trades_base_anti_loss.csv")
ARQUIVO_CHECKPOINT_DATASET = os.path.join(PASTA_CHECKPOINT, "checkpoint_dataset_anti_loss.csv")
ARQUIVO_CHECKPOINT_THRESHOLDS = os.path.join(PASTA_CHECKPOINT, "checkpoint_thresholds_anti_loss.csv")
ARQUIVO_CHECKPOINT_RESUMO = os.path.join(PASTA_CHECKPOINT, "checkpoint_resumo_anti_loss.csv")

# =====================================================
# ARQUIVOS FINAIS
# =====================================================

ARQUIVO_TRADES_BASE = os.path.join(PASTA_SAIDA, "23_anti_loss_trades_base_241.csv")
ARQUIVO_DATASET = os.path.join(PASTA_SAIDA, "24_anti_loss_dataset_features.csv")
ARQUIVO_RESULTADOS_MODELOS = os.path.join(PASTA_SAIDA, "25_anti_loss_resultados_modelos.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "26_anti_loss_importancia_features.csv")
ARQUIVO_THRESHOLDS = os.path.join(PASTA_SAIDA, "27_anti_loss_thresholds.csv")
ARQUIVO_TRADES_FILTRADOS = os.path.join(PASTA_SAIDA, "28_anti_loss_melhor_trades_filtrados.csv")
ARQUIVO_RESUMO_FINAL = os.path.join(PASTA_SAIDA, "29_anti_loss_resumo_final.csv")

# Take e Stop do operacional
TAKE_PONTOS = 25.5
STOP_PONTOS = 225.0

# Base de 2 minutos:
# 720 candles = 24 horas
MAX_CANDLES_FUTURO = 720

# Entrada no fechamento do candle do sinal
MODO_ENTRADA = "close_signal"  # "close_signal" ou "next_open"

# Configuração base com 241 trades / 13 losses
CONFIG_BASE = {
    "score_buy_min": 0.75,
    "score_sell_min": 0.50,
    "hora_inicio": 0.00,
    "hora_fim": 6.00,
    "diferenca_minima": 0.00,
}

# Apenas 1 operação por dia
APENAS_1_TRADE_POR_DIA = True
MODO_ESCOLHA_DIA = "maior_score"

# Validação cruzada
N_SPLITS_CV = 5

# Mínimo desejado para análise
MIN_TRADES_DESEJADO = 180


# =====================================================
# FUNÇÕES DE BACKUP E CHECKPOINT
# =====================================================

def timestamp_agora():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_arquivo(caminho):
    if os.path.exists(caminho):
        nome = os.path.basename(caminho)
        destino = os.path.join(PASTA_BACKUP, f"{timestamp_agora()}__{nome}")
        shutil.copy2(caminho, destino)
        print("Backup criado:", destino)


def salvar_csv_com_backup(df, caminho):
    if os.path.exists(caminho):
        backup_arquivo(caminho)

    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print("Arquivo salvo:", caminho)


def salvar_checkpoint(nome_etapa, df_checkpoint):
    """
    Salva checkpoint separado por etapa.
    """
    caminho = os.path.join(PASTA_CHECKPOINT, f"checkpoint_{nome_etapa}.csv")

    if os.path.exists(caminho):
        backup_arquivo(caminho)

    df_checkpoint.to_csv(caminho, index=False, encoding="utf-8-sig")
    print("Checkpoint salvo:", caminho)


# =====================================================
# CARREGAR SCORE
# =====================================================

print("Carregando score...")

df = pd.read_csv(ARQUIVO_SCORE)

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"])
df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

df = df.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume", "score_BUY", "score_SELL", "score_NONE"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
df["Hora_SP_Texto"] = df["DataHora_SP"].dt.strftime("%H:%M")
df["Data"] = df["DataHora_SP"].dt.date
df["DiaSemana"] = df["DataHora_SP"].dt.dayofweek
df["Mes"] = df["DataHora_SP"].dt.month
df["DiaMes"] = df["DataHora_SP"].dt.day

print("Linhas carregadas:", len(df))
print("Início:", df["DataHora_SP"].min())
print("Fim:", df["DataHora_SP"].max())


# =====================================================
# CRIAR FEATURES DE MERCADO
# =====================================================

def adicionar_features_mercado(base):
    base = base.copy()

    base["range"] = base["high"] - base["low"]
    base["body"] = base["close"] - base["open"]
    base["body_abs"] = base["body"].abs()
    base["upper_wick"] = base["high"] - base[["open", "close"]].max(axis=1)
    base["lower_wick"] = base[["open", "close"]].min(axis=1) - base["low"]
    base["body_range_pct"] = base["body_abs"] / base["range"].replace(0, np.nan)
    base["close_pos_range"] = (base["close"] - base["low"]) / base["range"].replace(0, np.nan)

    base["score_diff_buy_sell"] = base["score_BUY"] - base["score_SELL"]
    base["score_max"] = base[["score_BUY", "score_SELL", "score_NONE"]].max(axis=1)
    base["score_gap_direcional"] = base[["score_BUY", "score_SELL"]].max(axis=1) - base["score_NONE"]

    for n in [1, 2, 3, 5, 10, 15, 30, 60]:
        base[f"ret_{n}"] = base["close"].pct_change(n)
        base[f"pts_change_{n}"] = base["close"] - base["close"].shift(n)

    for n in [3, 5, 10, 15, 30, 60]:
        base[f"range_ma_{n}"] = base["range"].rolling(n).mean()
        base[f"range_ratio_{n}"] = base["range"] / base[f"range_ma_{n}"].replace(0, np.nan)

        base[f"volume_ma_{n}"] = base["volume"].rolling(n).mean()
        base[f"volume_ratio_{n}"] = base["volume"] / base[f"volume_ma_{n}"].replace(0, np.nan)

        base[f"high_max_{n}"] = base["high"].rolling(n).max()
        base[f"low_min_{n}"] = base["low"].rolling(n).min()

        base[f"dist_high_max_{n}"] = base["close"] - base[f"high_max_{n}"]
        base[f"dist_low_min_{n}"] = base["close"] - base[f"low_min_{n}"]

        base[f"pos_range_{n}"] = (base["close"] - base[f"low_min_{n}"]) / (
            base[f"high_max_{n}"] - base[f"low_min_{n}"]
        ).replace(0, np.nan)

    for n in [9, 17, 20, 34, 50, 100, 200]:
        base[f"ema_{n}"] = base["close"].ewm(span=n, adjust=False).mean()
        base[f"dist_ema_{n}"] = base["close"] - base[f"ema_{n}"]
        base[f"ema_{n}_slope_3"] = base[f"ema_{n}"] - base[f"ema_{n}"].shift(3)
        base[f"ema_{n}_slope_5"] = base[f"ema_{n}"] - base[f"ema_{n}"].shift(5)

    for n in [6, 12, 20, 23, 24, 34]:
        sma = base["close"].rolling(n).mean()
        base[f"bias_{n}"] = (base["close"] - sma) / sma * 100

    for n in [7, 8, 14, 21]:
        delta = base["close"].diff()
        ganho = delta.clip(lower=0)
        perda = -delta.clip(upper=0)

        media_ganho = ganho.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        media_perda = perda.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()

        rs = media_ganho / media_perda.replace(0, np.nan)
        base[f"rsi_{n}"] = 100 - (100 / (1 + rs))

    for n in [8, 14]:
        rsi = base[f"rsi_{n}"]
        minimo = rsi.rolling(n).min()
        maximo = rsi.rolling(n).max()

        stoch = 100 * (rsi - minimo) / (maximo - minimo).replace(0, np.nan)

        base[f"stochrsi_{n}_k"] = stoch.rolling(3).mean()
        base[f"stochrsi_{n}_d"] = base[f"stochrsi_{n}_k"].rolling(3).mean()

    prev_close = base["close"].shift(1)

    tr1 = base["high"] - base["low"]
    tr2 = (base["high"] - prev_close).abs()
    tr3 = (base["low"] - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    for n in [7, 14, 18, 21]:
        base[f"atr_{n}"] = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        base[f"atrp_{n}"] = base[f"atr_{n}"] / base["close"] * 100

    for n in [20, 34]:
        media = base["close"].rolling(n).mean()
        desvio = base["close"].rolling(n).std()

        upper = media + 2 * desvio
        lower = media - 2 * desvio

        base[f"bb_mid_{n}"] = media
        base[f"bb_upper_{n}"] = upper
        base[f"bb_lower_{n}"] = lower
        base[f"bb_width_{n}"] = (upper - lower) / media * 100
        base[f"bb_pos_{n}"] = (base["close"] - lower) / (upper - lower).replace(0, np.nan)

    ema20 = base["close"].ewm(span=20, adjust=False).mean()
    atr20 = tr.ewm(alpha=1 / 20, adjust=False, min_periods=20).mean()

    base["kc_mid_20"] = ema20
    base["kc_upper_20"] = ema20 + 2 * atr20
    base["kc_lower_20"] = ema20 - 2 * atr20
    base["kc_pos_20"] = (base["close"] - base["kc_lower_20"]) / (
        base["kc_upper_20"] - base["kc_lower_20"]
    ).replace(0, np.nan)

    base["ema17_acima_ema34"] = (base["ema_17"] > base["ema_34"]).astype(int)
    base["ema9_acima_ema17"] = (base["ema_9"] > base["ema_17"]).astype(int)
    base["close_acima_ema17"] = (base["close"] > base["ema_17"]).astype(int)
    base["close_acima_ema34"] = (base["close"] > base["ema_34"]).astype(int)
    base["dist_ema17_34"] = base["ema_17"] - base["ema_34"]

    base["sin_hora"] = np.sin(2 * np.pi * base["Hora_SP_Decimal"] / 24)
    base["cos_hora"] = np.cos(2 * np.pi * base["Hora_SP_Decimal"] / 24)

    base = base.copy()

    return base


print("Criando features de mercado...")
df_feat = adicionar_features_mercado(df)

# Checkpoint da base com features, opcionalmente pequeno resumo
pd.DataFrame([{
    "linhas": len(df_feat),
    "inicio": df_feat["DataHora_SP"].min(),
    "fim": df_feat["DataHora_SP"].max(),
    "colunas": len(df_feat.columns)
}]).to_csv(ARQUIVO_CHECKPOINT, index=False, encoding="utf-8-sig")


# =====================================================
# SIMULAR TAKE/STOP
# =====================================================

def simular_trade(df_base, indice_sinal, direcao):
    if MODO_ENTRADA == "next_open":
        indice_entrada = indice_sinal + 1

        if indice_entrada >= len(df_base):
            return None

        preco_entrada = df_base.loc[indice_entrada, "open"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]
    else:
        indice_entrada = indice_sinal
        preco_entrada = df_base.loc[indice_entrada, "close"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]

    if pd.isna(preco_entrada):
        return None

    if direcao == "BUY":
        preco_take = preco_entrada + TAKE_PONTOS
        preco_stop = preco_entrada - STOP_PONTOS
    else:
        preco_take = preco_entrada - TAKE_PONTOS
        preco_stop = preco_entrada + STOP_PONTOS

    fim = min(indice_entrada + MAX_CANDLES_FUTURO, len(df_base) - 1)

    maior_runup = 0.0
    maior_drawdown = 0.0

    for j in range(indice_entrada + 1, fim + 1):
        high = df_base.loc[j, "high"]
        low = df_base.loc[j, "low"]
        dt_saida = df_base.loc[j, "DataHora_SP"]

        if pd.isna(high) or pd.isna(low):
            continue

        if direcao == "BUY":
            runup_atual = high - preco_entrada
            drawdown_atual = preco_entrada - low

            maior_runup = max(maior_runup, runup_atual)
            maior_drawdown = max(maior_drawdown, drawdown_atual)

            bateu_take = high >= preco_take
            bateu_stop = low <= preco_stop

            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

        else:
            runup_atual = preco_entrada - low
            drawdown_atual = high - preco_entrada

            maior_runup = max(maior_runup, runup_atual)
            maior_drawdown = max(maior_drawdown, drawdown_atual)

            bateu_take = low <= preco_take
            bateu_stop = high >= preco_stop

            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

    return {
        "resultado": "ABERTO",
        "pontos": 0.0,
        "preco_entrada": preco_entrada,
        "preco_saida": np.nan,
        "dt_entrada": dt_entrada,
        "dt_saida": pd.NaT,
        "candles_ate_saida": np.nan,
        "minutos_ate_saida": np.nan,
        "runup": maior_runup,
        "drawdown": maior_drawdown
    }


# =====================================================
# GERAR TRADES DA CONFIGURAÇÃO BASE
# =====================================================

def gerar_trades_config_base(df_base):
    print("Gerando trades da configuração base...")

    cond_horario = (
        (df_base["Hora_SP_Decimal"] >= CONFIG_BASE["hora_inicio"]) &
        (df_base["Hora_SP_Decimal"] <= CONFIG_BASE["hora_fim"])
    )

    cond_buy = (
        cond_horario &
        (df_base["score_BUY"] >= CONFIG_BASE["score_buy_min"]) &
        (df_base["score_BUY"] > df_base["score_SELL"]) &
        ((df_base["score_BUY"] - df_base["score_SELL"]) >= CONFIG_BASE["diferenca_minima"])
    )

    cond_sell = (
        cond_horario &
        (df_base["score_SELL"] >= CONFIG_BASE["score_sell_min"]) &
        (df_base["score_SELL"] > df_base["score_BUY"]) &
        ((df_base["score_SELL"] - df_base["score_BUY"]) >= CONFIG_BASE["diferenca_minima"])
    )

    base = df_base.copy()
    base["Direcao_Candidata"] = "NONE"
    base.loc[cond_buy, "Direcao_Candidata"] = "BUY"
    base.loc[cond_sell, "Direcao_Candidata"] = "SELL"

    candidatos = base[base["Direcao_Candidata"] != "NONE"].copy()

    candidatos["score_direcao"] = np.where(
        candidatos["Direcao_Candidata"] == "BUY",
        candidatos["score_BUY"],
        candidatos["score_SELL"]
    )

    candidatos["score_oposto"] = np.where(
        candidatos["Direcao_Candidata"] == "BUY",
        candidatos["score_SELL"],
        candidatos["score_BUY"]
    )

    candidatos["score_diff"] = candidatos["score_direcao"] - candidatos["score_oposto"]

    if APENAS_1_TRADE_POR_DIA:
        escolhidos = []

        for data, grupo in candidatos.groupby("Data"):
            grupo = grupo.copy()

            if MODO_ESCOLHA_DIA == "primeiro":
                escolhido = grupo.sort_values("DataHora_SP").iloc[0]
            else:
                escolhido = grupo.sort_values(
                    by=["score_direcao", "score_diff", "DataHora_SP"],
                    ascending=[False, False, True]
                ).iloc[0]

            escolhidos.append(escolhido)

        candidatos = pd.DataFrame(escolhidos).sort_values("DataHora_SP").reset_index(drop=True)

    trades = []

    for _, row in candidatos.iterrows():
        idx_base = df_base.index[df_base["DataHora_SP"] == row["DataHora_SP"]]

        if len(idx_base) == 0:
            continue

        indice_sinal = int(idx_base[0])
        direcao = row["Direcao_Candidata"]

        trade = simular_trade(df_base, indice_sinal, direcao)

        if trade is None:
            continue

        linha = {
            "indice_sinal": indice_sinal,
            "DataHora_Sinal_SP": row["DataHora_SP"],
            "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
            "Data": row["Data"],
            "Hora_SP": row["Hora_SP_Texto"],
            "Direcao": direcao,
            "resultado": trade["resultado"],
            "pontos": trade["pontos"],
            "preco_entrada": trade["preco_entrada"],
            "preco_saida": trade["preco_saida"],
            "dt_entrada": trade["dt_entrada"],
            "dt_saida": trade["dt_saida"],
            "candles_ate_saida": trade["candles_ate_saida"],
            "minutos_ate_saida": trade["minutos_ate_saida"],
            "runup": trade["runup"],
            "drawdown": trade["drawdown"],
        }

        for col in df_base.columns:
            if pd.api.types.is_numeric_dtype(df_base[col]):
                linha[f"feat_{col}"] = row[col]

        trades.append(linha)

    trades_df = pd.DataFrame(trades)

    return trades_df


trades_base = gerar_trades_config_base(df_feat)

salvar_csv_com_backup(trades_base, ARQUIVO_TRADES_BASE)
salvar_csv_com_backup(trades_base, ARQUIVO_CHECKPOINT_TRADES_BASE)

print("\nResumo da configuração base:")
print(trades_base["resultado"].value_counts())

fechados_base = trades_base[trades_base["resultado"].isin(["WIN", "LOSS"])].copy()

wins_base = (fechados_base["resultado"] == "WIN").sum()
losses_base = (fechados_base["resultado"] == "LOSS").sum()
total_base = len(fechados_base)
winrate_base = wins_base / total_base * 100 if total_base > 0 else 0

print("Total:", total_base)
print("Wins:", wins_base)
print("Losses:", losses_base)
print("Winrate:", winrate_base)


# =====================================================
# DATASET ANTI-LOSS
# =====================================================

dataset = fechados_base.copy()

dataset["y_keep"] = (dataset["resultado"] == "WIN").astype(int)

dataset["dir_buy"] = (dataset["Direcao"] == "BUY").astype(int)
dataset["dir_sell"] = (dataset["Direcao"] == "SELL").astype(int)

dataset["Hora_int"] = pd.to_datetime(dataset["DataHora_Sinal_SP"]).dt.hour
dataset["Minuto_int"] = pd.to_datetime(dataset["DataHora_Sinal_SP"]).dt.minute
dataset["DiaSemana"] = pd.to_datetime(dataset["DataHora_Sinal_SP"]).dt.dayofweek
dataset["Mes"] = pd.to_datetime(dataset["DataHora_Sinal_SP"]).dt.month

dataset["hora_decimal_trade"] = dataset["Hora_int"] + dataset["Minuto_int"] / 60
dataset["sin_hora_trade"] = np.sin(2 * np.pi * dataset["hora_decimal_trade"] / 24)
dataset["cos_hora_trade"] = np.cos(2 * np.pi * dataset["hora_decimal_trade"] / 24)

salvar_csv_com_backup(dataset, ARQUIVO_DATASET)
salvar_csv_com_backup(dataset, ARQUIVO_CHECKPOINT_DATASET)

feature_cols = []

for col in dataset.columns:
    if col.startswith("feat_"):
        if pd.api.types.is_numeric_dtype(dataset[col]):
            feature_cols.append(col)

for col in [
    "dir_buy",
    "dir_sell",
    "Hora_int",
    "Minuto_int",
    "DiaSemana",
    "Mes",
    "hora_decimal_trade",
    "sin_hora_trade",
    "cos_hora_trade",
]:
    feature_cols.append(col)

missing = dataset[feature_cols].isna().mean()
feature_cols = [c for c in feature_cols if missing[c] < 0.35]

X = dataset[feature_cols]
y = dataset["y_keep"]

print("\nDataset anti-loss:")
print("Linhas:", len(dataset))
print("Features:", len(feature_cols))
print("Distribuição y_keep:")
print(y.value_counts())


# =====================================================
# TREINAR MODELOS ANTI-LOSS
# =====================================================

modelos = {
    "LogisticRegression": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            class_weight="balanced",
            max_iter=3000,
            random_state=42
        ))
    ]),

    "RandomForest": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=4
        ))
    ]),

    "ExtraTrees": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=4
        ))
    ]),

    "GradientBoosting": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.03,
            max_depth=2,
            random_state=42
        ))
    ])
}

resultados_modelos = []
predicoes_por_modelo = {}

skf = StratifiedKFold(
    n_splits=N_SPLITS_CV,
    shuffle=True,
    random_state=42
)

for nome, modelo in modelos.items():
    print("\n=====================================================")
    print("Treinando modelo:", nome)
    print("=====================================================")

    try:
        probas_cv = cross_val_predict(
            modelo,
            X,
            y,
            cv=skf,
            method="predict_proba",
            n_jobs=None
        )[:, 1]

        pred_cv = (probas_cv >= 0.50).astype(int)

        acc = accuracy_score(y, pred_cv)
        bacc = balanced_accuracy_score(y, pred_cv)

        print("Accuracy CV:", acc)
        print("Balanced Accuracy CV:", bacc)
        print(confusion_matrix(y, pred_cv))
        print(classification_report(y, pred_cv, zero_division=0))

        resultados_modelos.append({
            "modelo": nome,
            "accuracy_cv": acc,
            "balanced_accuracy_cv": bacc,
            "n_trades": len(y),
            "wins": int((y == 1).sum()),
            "losses": int((y == 0).sum())
        })

        predicoes_por_modelo[nome] = probas_cv

        salvar_csv_com_backup(
            pd.DataFrame(resultados_modelos),
            ARQUIVO_RESULTADOS_MODELOS
        )

    except Exception as e:
        print("Erro no modelo:", nome)
        print(e)

resultados_modelos_df = pd.DataFrame(resultados_modelos)
salvar_csv_com_backup(resultados_modelos_df, ARQUIVO_RESULTADOS_MODELOS)


# =====================================================
# TESTAR THRESHOLDS ANTI-LOSS
# =====================================================

thresholds = np.round(np.arange(0.10, 0.991, 0.01), 2)

linhas_thresholds = []
melhor_linha = None
melhor_trades_filtrados = None

for nome, probas in predicoes_por_modelo.items():
    temp = dataset.copy()
    temp["prob_keep_cv"] = probas
    temp["modelo_anti_loss"] = nome

    for th in thresholds:
        filtrados = temp[temp["prob_keep_cv"] >= th].copy()

        if filtrados.empty:
            continue

        fechados = filtrados[filtrados["resultado"].isin(["WIN", "LOSS"])].copy()

        total = len(fechados)
        wins = (fechados["resultado"] == "WIN").sum()
        losses = (fechados["resultado"] == "LOSS").sum()
        winrate = wins / total * 100 if total > 0 else 0
        lucro = fechados["pontos"].sum()

        buy_total = (fechados["Direcao"] == "BUY").sum()
        sell_total = (fechados["Direcao"] == "SELL").sum()

        linha = {
            "modelo": nome,
            "threshold_prob_keep": th,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "lucro_pontos": lucro,
            "buy_total": buy_total,
            "sell_total": sell_total,
            "drawdown_medio_trade": fechados["drawdown"].mean(),
            "drawdown_max_trade": fechados["drawdown"].max(),
            "media_minutos_saida": fechados["minutos_ate_saida"].mean(),
            "max_minutos_saida": fechados["minutos_ate_saida"].max(),
            "media_prob_keep": fechados["prob_keep_cv"].mean(),
            "min_prob_keep": fechados["prob_keep_cv"].min(),
            "max_prob_keep": fechados["prob_keep_cv"].max()
        }

        linhas_thresholds.append(linha)

        chave = (
            linha["winrate"],
            linha["total_trades"],
            linha["lucro_pontos"]
        )

        if melhor_linha is None:
            melhor_linha = linha
            melhor_trades_filtrados = fechados.copy()
        else:
            melhor_chave = (
                melhor_linha["winrate"],
                melhor_linha["total_trades"],
                melhor_linha["lucro_pontos"]
            )

            if chave > melhor_chave:
                melhor_linha = linha
                melhor_trades_filtrados = fechados.copy()

    thresholds_parcial = pd.DataFrame(linhas_thresholds)

    if not thresholds_parcial.empty:
        thresholds_parcial = thresholds_parcial.sort_values(
            by=["winrate", "total_trades", "lucro_pontos"],
            ascending=[False, False, False]
        )

        salvar_csv_com_backup(thresholds_parcial, ARQUIVO_CHECKPOINT_THRESHOLDS)

thresholds_df = pd.DataFrame(linhas_thresholds)

thresholds_df = thresholds_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

salvar_csv_com_backup(thresholds_df, ARQUIVO_THRESHOLDS)
salvar_csv_com_backup(thresholds_df, ARQUIVO_CHECKPOINT_THRESHOLDS)


# =====================================================
# TREINAR MELHOR MODELO EM TODOS OS DADOS PARA IMPORTÂNCIA
# =====================================================

if melhor_linha is not None:
    melhor_modelo_nome = melhor_linha["modelo"]
    melhor_modelo = modelos[melhor_modelo_nome]

    melhor_modelo.fit(X, y)

    modelo_interno = melhor_modelo.named_steps["model"]

    if hasattr(modelo_interno, "feature_importances_"):
        importancia = pd.DataFrame({
            "feature": feature_cols,
            "importancia": modelo_interno.feature_importances_
        }).sort_values("importancia", ascending=False)

        salvar_csv_com_backup(importancia, ARQUIVO_IMPORTANCIA)
    else:
        importancia = pd.DataFrame({
            "feature": feature_cols,
            "importancia": np.nan
        })

        salvar_csv_com_backup(importancia, ARQUIVO_IMPORTANCIA)


# =====================================================
# SALVAR MELHOR RESULTADO
# =====================================================

if melhor_trades_filtrados is not None:
    salvar_csv_com_backup(melhor_trades_filtrados, ARQUIVO_TRADES_FILTRADOS)

resumo_final = pd.DataFrame([{
    "base_total_trades": total_base,
    "base_wins": wins_base,
    "base_losses": losses_base,
    "base_winrate": winrate_base,
    "config_score_buy_min": CONFIG_BASE["score_buy_min"],
    "config_score_sell_min": CONFIG_BASE["score_sell_min"],
    "config_hora_inicio": CONFIG_BASE["hora_inicio"],
    "config_hora_fim": CONFIG_BASE["hora_fim"],
    "config_diferenca_minima": CONFIG_BASE["diferenca_minima"],
    **(melhor_linha if melhor_linha is not None else {})
}])

salvar_csv_com_backup(resumo_final, ARQUIVO_RESUMO_FINAL)
salvar_csv_com_backup(resumo_final, ARQUIVO_CHECKPOINT_RESUMO)


# =====================================================
# RELATÓRIO FINAL
# =====================================================

print("\n=====================================================")
print("RESUMO FINAL ANTI-LOSS")
print("=====================================================")

print("\nBase original:")
print("Trades:", total_base)
print("Wins:", wins_base)
print("Losses:", losses_base)
print("Winrate:", round(winrate_base, 2))

if melhor_linha is not None:
    print("\nMelhor filtro anti-loss:")
    print(pd.Series(melhor_linha))

    print("\nTop 30 thresholds:")
    print(thresholds_df.head(30))

    cem = thresholds_df[thresholds_df["winrate"] == 100.0].copy()

    if not cem.empty:
        print("\nMelhores com 100%:")
        print(cem.sort_values(
            by=["total_trades", "lucro_pontos"],
            ascending=[False, False]
        ).head(30))
    else:
        print("\nNenhum filtro chegou a 100% usando validação cruzada.")

print("\nArquivos gerados:")
print(ARQUIVO_TRADES_BASE)
print(ARQUIVO_DATASET)
print(ARQUIVO_RESULTADOS_MODELOS)
print(ARQUIVO_IMPORTANCIA)
print(ARQUIVO_THRESHOLDS)
print(ARQUIVO_TRADES_FILTRADOS)
print(ARQUIVO_RESUMO_FINAL)

print("\nCheckpoints separados:")
print(PASTA_CHECKPOINT)
print(ARQUIVO_CHECKPOINT)
print(ARQUIVO_CHECKPOINT_TRADES_BASE)
print(ARQUIVO_CHECKPOINT_DATASET)
print(ARQUIVO_CHECKPOINT_THRESHOLDS)
print(ARQUIVO_CHECKPOINT_RESUMO)