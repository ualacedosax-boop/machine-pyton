import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# =========================
# LER DATASET DOS SINAIS
# =========================
df = pd.read_csv("dataset_setup_ml.csv")

df["datetime_entrada"] = pd.to_datetime(df["datetime_entrada"])
df["datetime_saida"] = pd.to_datetime(df["datetime_saida"])

# =========================
# AJUSTES
# =========================
df["tipo_num"] = df["tipo"].map({"BUY": 1, "SELL": -1})

# booleanos para int
bool_cols = [
    "crossUpRecent", "crossDownRecent",
    "stochCaindo", "stochSubindo",
    "toqueNaMedia", "filtroCompraVol", "filtroVendaVol"
]

for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].astype(int)

# =========================
# FEATURES
# =========================
features = [
    "tipo_num",
    "open", "high", "low", "close",
    "ema17", "ema34",
    "bias", "limiteAlta", "limiteBaixa",
    "k", "d",
    "atr", "stopFinal",
    "hora", "minuto",
    "crossUpRecent", "crossDownRecent",
    "stochCaindo", "stochSubindo",
    "toqueNaMedia", "filtroCompraVol", "filtroVendaVol"
]

X = df[features].copy()
y = df["resultado"].copy()

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
    max_depth=6,
    min_samples_leaf=4,
    random_state=42
)

modelo.fit(X_treino, y_treino)

# =========================
# PREVISÃO
# =========================
previsoes = modelo.predict(X_teste)
probs = modelo.predict_proba(X_teste)[:, 1]

# =========================
# RESULTADOS
# =========================
acc = accuracy_score(y_teste, previsoes)

print("Quantidade total de sinais:", len(df))
print("\nResultado geral:")
print(df["resultado"].value_counts())

print("\nAcurácia:", acc)

print("\nMatriz de confusão:")
print(confusion_matrix(y_teste, previsoes))

print("\nRelatório:")
print(classification_report(y_teste, previsoes, zero_division=0))

# =========================
# TABELA DE TESTE
# =========================
teste = df.iloc[divisao:].copy()
teste["previsto"] = previsoes
teste["prob_gain"] = probs

print("\nTabela de teste:")
print(teste[[
    "datetime_entrada", "tipo", "resultado", "previsto", "prob_gain",
    "bias", "k", "d", "atr", "stopFinal", "hora", "minuto"
]].head(30))

# =========================
# IMPORTÂNCIA DAS FEATURES
# =========================
importancias = pd.DataFrame({
    "feature": features,
    "importancia": modelo.feature_importances_
}).sort_values("importancia", ascending=False)

print("\nImportância das features:")
print(importancias)

# =========================
# FILTRO POR CONFIANÇA
# =========================
filtro = teste[teste["prob_gain"] >= 0.60].copy()

print("\nSinais filtrados com prob_gain >= 0.60:", len(filtro))
if len(filtro) > 0:
    print("Resultado dos filtrados:")
    print(filtro["resultado"].value_counts())

    taxa = filtro["resultado"].mean()
    print("Taxa de acerto dos filtrados:", taxa)

    print("\nPor tipo:")
    print(pd.crosstab(filtro["tipo"], filtro["resultado"]))
else:
    print("Nenhum sinal passou no filtro.")