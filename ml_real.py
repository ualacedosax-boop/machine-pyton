import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# LER CSV REAL
# =========================
df = pd.read_csv("mercado_real.csv")
df = df.rename(columns={"time": "datetime"})

# =========================
# MANTER COLUNAS ÚTEIS
# =========================
colunas_base = ["datetime", "open", "high", "low", "close"]
colunas_opcionais = [col for col in ["BIAS3", "K", "D"] if col in df.columns]
df = df[colunas_base + colunas_opcionais].copy()

# =========================
# DATETIME
# =========================
df["datetime"] = pd.to_datetime(df["datetime"])
df = df.sort_values("datetime").reset_index(drop=True)

# =========================
# FEATURES
# =========================
df["mm3"] = df["close"].rolling(3).mean()
df["mm5"] = df["close"].rolling(5).mean()
df["retorno_1"] = df["close"].pct_change(1)
df["retorno_2"] = df["close"].pct_change(2)
df["dist_mm3"] = (df["close"] - df["mm3"]) / df["mm3"]
df["dist_mm5"] = (df["close"] - df["mm5"]) / df["mm5"]
df["hora"] = df["datetime"].dt.hour
df["minuto"] = df["datetime"].dt.minute
df["dia_semana"] = df["datetime"].dt.dayofweek

# =========================
# ALVO BINÁRIO DIRECIONAL
#  1 = compra
# -1 = venda
# ignora neutros
# =========================
df["proximo_close"] = df["close"].shift(-1)
df["ret_futuro"] = (df["proximo_close"] - df["close"]) / df["close"]

limite = 0.0008
df["alvo"] = 0
df.loc[df["ret_futuro"] > limite, "alvo"] = 1
df.loc[df["ret_futuro"] < -limite, "alvo"] = -1

# remove neutros
df = df[df["alvo"] != 0].copy()

# remove NaN
df = df.dropna().copy()

# =========================
# FEATURES USADAS
# =========================
features = [
    "open", "high", "low", "close",
    "mm3", "mm5",
    "retorno_1", "retorno_2",
    "dist_mm3", "dist_mm5",
    "hora", "minuto", "dia_semana"
]

for col in ["BIAS3", "K", "D"]:
    if col in df.columns:
        features.append(col)

X = df[features]
y = df["alvo"]

# =========================
# TREINO / TESTE TEMPORAL
# =========================
divisao = int(len(df) * 0.7)

X_treino = X.iloc[:divisao]
X_teste = X.iloc[divisao:]

y_treino = y.iloc[:divisao]
y_teste = y.iloc[divisao:]

# =========================
# MODELO
# =========================
modelo = RandomForestClassifier(
    n_estimators=300,
    max_depth=8,
    min_samples_leaf=3,
    random_state=42
)

modelo.fit(X_treino, y_treino)

# =========================
# PREVISÃO
# =========================
previsoes = modelo.predict(X_teste)

# =========================
# RESULTADOS
# =========================
acc = accuracy_score(y_teste, previsoes)

print("Quantidade de linhas após remover neutros:", len(df))
print("\nContagem do alvo:")
print(df["alvo"].value_counts().sort_index())

print("\nPrevisões:")
print(previsoes)

print("\nReais:")
print(y_teste.values)

print("\nAcurácia:", acc)

print("\nMatriz de confusão:")
print(confusion_matrix(y_teste, previsoes))

print("\nRelatório:")
print(classification_report(y_teste, previsoes, zero_division=0))

resultado = df.iloc[divisao:].copy()
resultado["previsto"] = previsoes

print("\nTabela de teste:")
print(resultado[["datetime", "close", "ret_futuro", "alvo", "previsto"]].head(30))

importancias = pd.DataFrame({
    "feature": features,
    "importancia": modelo.feature_importances_
}).sort_values("importancia", ascending=False)

print("\nImportância das features:")
print(importancias)