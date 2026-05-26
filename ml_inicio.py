import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# LER DADOS
# =========================
df = pd.read_csv("dados.csv")
df["datetime"] = pd.to_datetime(df["datetime"])

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

# =========================
# ALVO 3 CLASSES
# 1  = compra
# -1 = venda
# 0  = neutro
# =========================
df["proximo_close"] = df["close"].shift(-1)
df["ret_futuro"] = (df["proximo_close"] - df["close"]) / df["close"]

limite = 0.0015  # 0,15%

df["alvo"] = 0
df.loc[df["ret_futuro"] > limite, "alvo"] = 1
df.loc[df["ret_futuro"] < -limite, "alvo"] = -1

# =========================
# LIMPEZA
# =========================
df = df.dropna().copy()

# =========================
# ENTRADAS E SAÍDA
# =========================
features = [
    "close", "volume",
    "mm3", "mm5",
    "retorno_1", "retorno_2",
    "dist_mm3", "dist_mm5",
    "hora", "minuto"
]

X = df[features]
y = df["alvo"]

# =========================
# TREINO / TESTE
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
    n_estimators=200,
    max_depth=5,
    min_samples_leaf=2,
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

print("Contagem do alvo:")
print(df["alvo"].value_counts().sort_index())

print("\nFeatures usadas:")
print(features)

print("\nPrevisões:")
print(previsoes)

print("\nReais:")
print(y_teste.values)

print("\nAcurácia:", acc)

print("\nMatriz de confusão:")
print(confusion_matrix(y_teste, previsoes))

print("\nRelatório:")
print(classification_report(y_teste, previsoes, zero_division=0))

# =========================
# TABELA FINAL DE TESTE
# =========================
resultado = df.iloc[divisao:].copy()
resultado["previsto"] = previsoes

print("\nTabela de teste:")
print(resultado[[
    "datetime", "close", "ret_futuro", "alvo", "previsto"
]])

# =========================
# IMPORTÂNCIA DAS FEATURES
# =========================
importancias = pd.DataFrame({
    "feature": features,
    "importancia": modelo.feature_importances_
}).sort_values("importancia", ascending=False)

print("\nImportância das features:")
print(importancias)