import pandas as pd
import numpy as np
import os
from datetime import datetime, date, time

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, balanced_accuracy_score
from sklearn.model_selection import train_test_split


# =====================================================
# ARQUIVOS
# =====================================================

ARQUIVO_PRECOS = "MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv"
ARQUIVO_ENTRADAS = "Entrada video-priemira amostra.xlsx"
PASTA_SAIDA = "saida_ml_entradas_video"
os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_ENTRADAS_LIMPAS = os.path.join(PASTA_SAIDA, "01_entradas_video_limpas.csv")
ARQUIVO_FEATURES_ENTRADAS = os.path.join(PASTA_SAIDA, "02_features_nas_entradas.csv")
ARQUIVO_DATASET_ML = os.path.join(PASTA_SAIDA, "03_dataset_ml_treino.csv")
ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "04_resultado_modelos.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "05_importancia_features.csv")
ARQUIVO_SCORE = os.path.join(PASTA_SAIDA, "06_score_todos_candles.csv")


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def parse_data(valor):
    if pd.isna(valor):
        return pd.NaT

    if isinstance(valor, pd.Timestamp):
        return valor.normalize()

    if isinstance(valor, datetime):
        return pd.Timestamp(valor).normalize()

    if isinstance(valor, date):
        return pd.Timestamp(valor).normalize()

    if isinstance(valor, (int, float, np.integer, np.floating)):
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(int(valor), unit="D")

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return pd.NaT

    texto = texto.replace("20225", "2025")

    return pd.to_datetime(texto, errors="coerce", dayfirst=True).normalize()


def parse_hora(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, time):
        return valor

    if isinstance(valor, datetime):
        return valor.time()

    if isinstance(valor, pd.Timestamp):
        return valor.time()

    texto = str(valor).strip()

    if texto == "" or texto.lower() == "nan":
        return None

    convertido = pd.to_datetime(texto, errors="coerce")

    if pd.isna(convertido):
        return None

    return convertido.time()


def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    media_perda = perda.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    rs = media_ganho / media_perda.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def criar_features(df):
    df = df.copy()

    df["ret_1"] = df["close"].pct_change()
    df["logret_1"] = np.log(df["close"] / df["close"].shift(1))

    df["range"] = df["high"] - df["low"]
    df["body"] = df["close"] - df["open"]
    df["body_abs"] = df["body"].abs()
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    df["body_range_pct"] = df["body_abs"] / df["range"].replace(0, np.nan)
    df["close_pos_range"] = (df["close"] - df["low"]) / df["range"].replace(0, np.nan)

    for n in [3, 5, 10, 15, 30, 60]:
        df[f"ret_{n}"] = df["close"].pct_change(n)
        df[f"range_ma_{n}"] = df["range"].rolling(n).mean()
        df[f"volume_ma_{n}"] = df["volume"].rolling(n).mean()
        df[f"volume_ratio_{n}"] = df["volume"] / df[f"volume_ma_{n}"].replace(0, np.nan)
        df[f"max_{n}"] = df["high"].rolling(n).max()
        df[f"min_{n}"] = df["low"].rolling(n).min()
        df[f"dist_max_{n}"] = df["close"] - df[f"max_{n}"]
        df[f"dist_min_{n}"] = df["close"] - df[f"min_{n}"]

    for n in [9, 17, 20, 34, 50, 100, 200]:
        df[f"ema_{n}"] = df["close"].ewm(span=n, adjust=False).mean()
        df[f"dist_ema_{n}"] = df["close"] - df[f"ema_{n}"]
        df[f"ema_{n}_slope_3"] = df[f"ema_{n}"] - df[f"ema_{n}"].shift(3)

    for n in [6, 12, 20, 23, 24, 34]:
        sma = df["close"].rolling(n).mean()
        df[f"bias_{n}"] = (df["close"] - sma) / sma * 100

    for n in [7, 8, 14, 21]:
        df[f"rsi_{n}"] = calcular_rsi(df["close"], n)

    for n in [8, 14]:
        rsi_col = df[f"rsi_{n}"]
        minimo = rsi_col.rolling(n).min()
        maximo = rsi_col.rolling(n).max()

        stoch = 100 * (rsi_col - minimo) / (maximo - minimo).replace(0, np.nan)

        df[f"stochrsi_{n}_k"] = stoch.rolling(3).mean()
        df[f"stochrsi_{n}_d"] = df[f"stochrsi_{n}_k"].rolling(3).mean()

    prev_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    for n in [7, 14, 18, 21]:
        df[f"atr_{n}"] = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        df[f"atrp_{n}"] = df[f"atr_{n}"] / df["close"] * 100

    for n in [20, 34]:
        media = df["close"].rolling(n).mean()
        desvio = df["close"].rolling(n).std()

        df[f"bb_mid_{n}"] = media
        df[f"bb_upper_{n}"] = media + 2 * desvio
        df[f"bb_lower_{n}"] = media - 2 * desvio
        df[f"bb_width_{n}"] = (df[f"bb_upper_{n}"] - df[f"bb_lower_{n}"]) / media * 100
        df[f"bb_pos_{n}"] = (df["close"] - df[f"bb_lower_{n}"]) / (
            df[f"bb_upper_{n}"] - df[f"bb_lower_{n}"]
        ).replace(0, np.nan)

    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    atr20 = tr.ewm(alpha=1 / 20, adjust=False, min_periods=20).mean()

    df["kc_mid_20"] = ema20
    df["kc_upper_20"] = ema20 + 2 * atr20
    df["kc_lower_20"] = ema20 - 2 * atr20
    df["kc_pos_20"] = (df["close"] - df["kc_lower_20"]) / (
        df["kc_upper_20"] - df["kc_lower_20"]
    ).replace(0, np.nan)

    df["ema17_acima_ema34"] = (df["ema_17"] > df["ema_34"]).astype(int)
    df["ema9_acima_ema17"] = (df["ema_9"] > df["ema_17"]).astype(int)
    df["close_acima_ema17"] = (df["close"] > df["ema_17"]).astype(int)
    df["close_acima_ema34"] = (df["close"] > df["ema_34"]).astype(int)
    df["dist_ema17_34"] = df["ema_17"] - df["ema_34"]

    df["hora_sp_decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
    df["dia_semana_sp"] = df["DataHora_SP"].dt.dayofweek
    df["minuto_sp"] = df["DataHora_SP"].dt.minute

    df["sin_hora_sp"] = np.sin(2 * np.pi * df["hora_sp_decimal"] / 24)
    df["cos_hora_sp"] = np.cos(2 * np.pi * df["hora_sp_decimal"] / 24)

    return df


# =====================================================
# 1. CARREGAR PREÇOS
# =====================================================

print("Carregando preços...")

precos = pd.read_csv(ARQUIVO_PRECOS)

precos["DataHora_SP"] = pd.to_datetime(precos["DataHora_SP"])
precos["DataHora_Chicago"] = pd.to_datetime(precos["DataHora_Chicago"])

precos = precos.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume", "average", "barCount"]:
    precos[col] = pd.to_numeric(precos[col], errors="coerce")


# =====================================================
# 2. LIMPAR ENTRADAS DO VÍDEO
# =====================================================

print("Limpando entradas do vídeo...")

entradas_raw = pd.read_excel(ARQUIVO_ENTRADAS)

entradas_raw["data_limpa"] = entradas_raw["data"].apply(parse_data)
entradas_raw["data_corrigida"] = entradas_raw["data_limpa"].ffill()
entradas_raw["hora_limpa"] = entradas_raw["hora"].apply(parse_hora)

entradas_raw["Sinal_limpo"] = entradas_raw["Sinal"].astype(str).str.strip().str.lower()

entradas = entradas_raw[entradas_raw["Sinal_limpo"].isin(["comprar", "vender"])].copy()

entradas["DataHora_Video"] = [
    pd.Timestamp.combine(d.date(), h)
    if pd.notna(d) and h is not None
    else pd.NaT
    for d, h in zip(entradas["data_corrigida"], entradas["hora_limpa"])
]

entradas["Direcao"] = entradas["Sinal_limpo"].map({
    "comprar": "BUY",
    "vender": "SELL"
})

entradas = entradas.dropna(subset=["DataHora_Video"]).copy()

entradas = entradas[[
    "DataHora_Video",
    "Direcao",
    "preço",
    "tamanho",
    "lucro",
    "Ru-up",
    "Drawdown",
    "L&p"
]].copy()

entradas["Data"] = entradas["DataHora_Video"].dt.date.astype(str)
entradas["Hora"] = entradas["DataHora_Video"].dt.time.astype(str)

entradas.to_csv(ARQUIVO_ENTRADAS_LIMPAS, index=False, encoding="utf-8-sig")

print("Entradas limpas:", len(entradas))
print(entradas["Direcao"].value_counts())


# =====================================================
# 3. CRIAR FEATURES
# =====================================================

print("Criando indicadores/features...")

base = criar_features(precos)

base["Label"] = 0
base["Label_Nome"] = "NONE"
base["Preco_Entrada_Video"] = np.nan

mapa_label = {
    "BUY": 1,
    "SELL": 2
}

for _, row in entradas.iterrows():
    dt_entrada = row["DataHora_Video"]
    direcao = row["Direcao"]

    idx = base.index[base["DataHora_SP"] == dt_entrada]

    if len(idx) > 0:
        i = idx[0]
        base.loc[i, "Label"] = mapa_label[direcao]
        base.loc[i, "Label_Nome"] = direcao
        base.loc[i, "Preco_Entrada_Video"] = row["preço"]


# =====================================================
# 4. USAR FEATURES DO CANDLE ANTERIOR
# =====================================================

colunas_nao_features = [
    "DataHora_Chicago",
    "Data_Chicago",
    "Hora_Chicago",
    "DataHora_SP",
    "Data_SP",
    "Hora_SP",
    "DataHora_UTC",
    "contrato",
    "localSymbol",
    "Label",
    "Label_Nome",
    "Preco_Entrada_Video"
]

feature_cols = []

for col in base.columns:
    if col not in colunas_nao_features:
        if pd.api.types.is_numeric_dtype(base[col]):
            feature_cols.append(col)

features_previas = base[feature_cols].shift(1)
features_previas.columns = ["prev_" + c for c in features_previas.columns]

dataset = pd.concat([
    base[[
        "DataHora_SP",
        "DataHora_Chicago",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "contrato",
        "localSymbol",
        "Label",
        "Label_Nome",
        "Preco_Entrada_Video"
    ]],
    features_previas
], axis=1)

dataset["Hora_SP_Decimal"] = dataset["DataHora_SP"].dt.hour + dataset["DataHora_SP"].dt.minute / 60

inicio = entradas["DataHora_Video"].min().normalize()
fim = entradas["DataHora_Video"].max().normalize() + pd.Timedelta(days=1)

dataset_periodo = dataset[
    (dataset["DataHora_SP"] >= inicio) &
    (dataset["DataHora_SP"] < fim)
].copy()

dataset_periodo = dataset_periodo[
    (dataset_periodo["Hora_SP_Decimal"] >= 0) &
    (dataset_periodo["Hora_SP_Decimal"] <= 12)
].copy()


# =====================================================
# 5. MONTAR AMOSTRA NEGATIVA
# =====================================================

print("Montando dataset de treino...")

positivos = dataset_periodo[dataset_periodo["Label"] > 0].copy()

dataset_periodo["Perto_Entrada"] = False

for dt_entrada in positivos["DataHora_SP"]:
    mascara = (
        (dataset_periodo["DataHora_SP"] >= dt_entrada - pd.Timedelta(minutes=10)) &
        (dataset_periodo["DataHora_SP"] <= dt_entrada + pd.Timedelta(minutes=10))
    )
    dataset_periodo.loc[mascara, "Perto_Entrada"] = True

negativos_pool = dataset_periodo[
    (dataset_periodo["Label"] == 0) &
    (~dataset_periodo["Perto_Entrada"])
].copy()

quantidade_negativos = min(len(negativos_pool), len(positivos) * 8)

negativos = negativos_pool.sample(
    n=quantidade_negativos,
    random_state=42
)

dataset_ml = pd.concat([positivos, negativos], ignore_index=True)
dataset_ml = dataset_ml.sort_values("DataHora_SP").reset_index(drop=True)

feature_ml_cols = [
    c for c in dataset_ml.columns
    if c.startswith("prev_")
]

missing = dataset_ml[feature_ml_cols].isna().mean()
feature_ml_cols = [
    c for c in feature_ml_cols
    if missing[c] < 0.25
]

dataset_ml.to_csv(ARQUIVO_DATASET_ML, index=False, encoding="utf-8-sig")

features_nas_entradas = dataset_ml[dataset_ml["Label"] > 0].copy()
features_nas_entradas.to_csv(ARQUIVO_FEATURES_ENTRADAS, index=False, encoding="utf-8-sig")

print("Dataset ML:")
print(dataset_ml["Label_Nome"].value_counts())


# =====================================================
# 6. TREINAR MODELOS
# =====================================================

print("Treinando modelos...")

X = dataset_ml[feature_ml_cols]
y = dataset_ml["Label"]

split_date = pd.Timestamp("2025-07-01")

train_mask = dataset_ml["DataHora_SP"] < split_date

X_train = X[train_mask]
y_train = y[train_mask]

X_test = X[~train_mask]
y_test = y[~train_mask]

modelos = {
    "RandomForest": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ]),
    "ExtraTrees": Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", ExtraTreesClassifier(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ])
}

resultados = []
melhor_modelo = None
melhor_nome = None
melhor_score = -999

for nome, modelo in modelos.items():
    modelo.fit(X_train, y_train)

    pred = modelo.predict(X_test)

    acc = accuracy_score(y_test, pred)
    bacc = balanced_accuracy_score(y_test, pred)

    print("\n====================================")
    print(nome)
    print("Accuracy:", acc)
    print("Balanced Accuracy:", bacc)
    print(confusion_matrix(y_test, pred))
    print(classification_report(y_test, pred, zero_division=0))

    resultados.append({
        "modelo": nome,
        "accuracy": acc,
        "balanced_accuracy": bacc,
        "treino_linhas": len(X_train),
        "teste_linhas": len(X_test)
    })

    if bacc > melhor_score:
        melhor_score = bacc
        melhor_modelo = modelo
        melhor_nome = nome

resultados_df = pd.DataFrame(resultados)
resultados_df.to_csv(ARQUIVO_RESULTADOS, index=False, encoding="utf-8-sig")

print("\nMelhor modelo:", melhor_nome)


# =====================================================
# 7. IMPORTÂNCIA DAS FEATURES
# =====================================================

modelo_interno = melhor_modelo.named_steps["model"]

if hasattr(modelo_interno, "feature_importances_"):
    importancia = pd.DataFrame({
        "feature": feature_ml_cols,
        "importancia": modelo_interno.feature_importances_
    }).sort_values("importancia", ascending=False)

    importancia.to_csv(ARQUIVO_IMPORTANCIA, index=False, encoding="utf-8-sig")

    print("\nTop 30 features:")
    print(importancia.head(30))


# =====================================================
# 8. GERAR SCORE PARA TODOS OS CANDLES
# =====================================================

print("Gerando score para todos os candles...")

dataset_score = dataset.copy()

X_score = dataset_score[feature_ml_cols]

probas = melhor_modelo.predict_proba(X_score)

classes = list(melhor_modelo.named_steps["model"].classes_)

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

colunas_saida = [
    "DataHora_SP",
    "DataHora_Chicago",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "contrato",
    "localSymbol",
    "Label_Nome",
    "Preco_Entrada_Video",
    "score_BUY",
    "score_SELL",
    "score_NONE",
    "Sinal_ML"
]

dataset_score[colunas_saida].to_csv(
    ARQUIVO_SCORE,
    index=False,
    encoding="utf-8-sig"
)


# =====================================================
# 9. RESUMO FINAL
# =====================================================

print("\n=====================================================")
print("FINALIZADO")
print("=====================================================")
print("Entradas limpas:", ARQUIVO_ENTRADAS_LIMPAS)
print("Features nas entradas:", ARQUIVO_FEATURES_ENTRADAS)
print("Dataset treino:", ARQUIVO_DATASET_ML)
print("Resultados modelos:", ARQUIVO_RESULTADOS)
print("Importância features:", ARQUIVO_IMPORTANCIA)
print("Score todos candles:", ARQUIVO_SCORE)