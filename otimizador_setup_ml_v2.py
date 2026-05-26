import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

# =====================================
# CONFIG
# =====================================
ARQUIVO = "dataset_setup_ml.csv"

MODO = "SELL"   # foco no lado vendedor

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
N_ESTIMATORS_LIST = [100, 200, 300, 400]
MAX_DEPTH_LIST = [4, 6, 8, 10]
MIN_SAMPLES_LEAF_LIST = [2, 4, 6]
MIN_SAMPLES_SPLIT_LIST = [4, 8, 12]

MIN_SINAIS_VALIDACAO = 10
MIN_SINAIS_TESTE = 10

RANDOM_STATE = 42

# =====================================
# LEITURA
# =====================================
df = pd.read_csv(ARQUIVO)

df["datetime_entrada"] = pd.to_datetime(df["datetime_entrada"])
df["datetime_saida"] = pd.to_datetime(df["datetime_saida"])

# bool -> int
bool_cols = [
    "crossUpRecent", "crossDownRecent",
    "stochCaindo", "stochSubindo",
    "toqueNaMedia", "filtroCompraVol", "filtroVendaVol"
]

for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].astype(int)

# tipo numérico
df["tipo_num"] = df["tipo"].map({"BUY": 1, "SELL": -1})

# pnl em pontos
df["pnl_pontos"] = np.where(
    df["tipo"] == "BUY",
    df["preco_saida"] - df["entrada"],
    df["entrada"] - df["preco_saida"]
)

# filtra modo
if MODO in ["BUY", "SELL"]:
    df = df[df["tipo"] == MODO].copy()

df = df.sort_values("datetime_entrada").reset_index(drop=True)

print("Modo selecionado:", MODO)
print("Quantidade de linhas:", len(df))
print("\nResultado geral:")
print(df["resultado"].value_counts())

# =====================================
# FEATURES
# =====================================
features = [
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

features = [col for col in features if col in df.columns]

# =====================================
# SPLIT TEMPORAL 60/20/20
# =====================================
n = len(df)
idx_treino = int(n * 0.60)
idx_valid = int(n * 0.80)

treino = df.iloc[:idx_treino].copy()
valid = df.iloc[idx_treino:idx_valid].copy()
teste = df.iloc[idx_valid:].copy()

print("\nTamanhos dos blocos:")
print("Treino:", len(treino))
print("Validação:", len(valid))
print("Teste final:", len(teste))

# =====================================
# FUNÇÕES
# =====================================
def avaliar_filtrado(base_filtrada):
    if len(base_filtrada) == 0:
        return None

    wins = int((base_filtrada["resultado"] == 1).sum())
    losses = int((base_filtrada["resultado"] == 0).sum())
    taxa = wins / len(base_filtrada) if len(base_filtrada) > 0 else 0.0
    lucro_total = base_filtrada["pnl_pontos"].sum()
    lucro_medio = base_filtrada["pnl_pontos"].mean()

    return {
        "sinais": len(base_filtrada),
        "wins": wins,
        "losses": losses,
        "taxa_acerto": taxa,
        "lucro_total_pontos": lucro_total,
        "lucro_medio_pontos": lucro_medio
    }

# =====================================
# OTIMIZAÇÃO NA VALIDAÇÃO
# =====================================
X_treino = treino[features].copy()
y_treino = treino["resultado"].copy()

X_valid = valid[features].copy()
y_valid = valid["resultado"].copy()

resultados_validacao = []
melhor = None
melhor_modelo = None

for n_estimators, max_depth, min_leaf, min_split in product(
    N_ESTIMATORS_LIST,
    MAX_DEPTH_LIST,
    MIN_SAMPLES_LEAF_LIST,
    MIN_SAMPLES_SPLIT_LIST
):
    modelo = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_leaf,
        min_samples_split=min_split,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    modelo.fit(X_treino, y_treino)

    previsoes_valid = modelo.predict(X_valid)
    probs_valid = modelo.predict_proba(X_valid)[:, 1]
    acc_valid = accuracy_score(y_valid, previsoes_valid)

    base_valid = valid.copy()
    base_valid["previsto"] = previsoes_valid
    base_valid["prob_gain"] = probs_valid

    for threshold in THRESHOLDS:
        filtrado = base_valid[base_valid["prob_gain"] >= threshold].copy()

        if len(filtrado) < MIN_SINAIS_VALIDACAO:
            continue

        met = avaliar_filtrado(filtrado)
        if met is None:
            continue

        registro = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_leaf,
            "min_samples_split": min_split,
            "threshold": threshold,
            "acc_valid_modelo": acc_valid,
            **met
        }

        # score principal
        registro["score"] = (
            registro["lucro_total_pontos"]
            + registro["lucro_medio_pontos"] * 10
            + registro["taxa_acerto"] * 10
        )

        resultados_validacao.append(registro)

        if melhor is None or registro["score"] > melhor["score"]:
            melhor = registro
            melhor_modelo = modelo

# salva ranking validação
if len(resultados_validacao) == 0:
    print("\nNenhum cenário válido encontrado na validação.")
    raise SystemExit

ranking_valid = pd.DataFrame(resultados_validacao).sort_values(
    ["score", "lucro_total_pontos", "taxa_acerto"],
    ascending=False
).reset_index(drop=True)

ranking_valid.to_csv("ranking_validacao_v2_sell.csv", index=False)

print("\n" + "=" * 80)
print("MELHOR CENÁRIO NA VALIDAÇÃO")
print("=" * 80)
print(melhor)

# =====================================
# TESTE FINAL COM O MELHOR CENÁRIO
# =====================================
X_teste = teste[features].copy()
y_teste = teste["resultado"].copy()

previsoes_teste = melhor_modelo.predict(X_teste)
probs_teste = melhor_modelo.predict_proba(X_teste)[:, 1]

acc_teste_modelo = accuracy_score(y_teste, previsoes_teste)

base_teste = teste.copy()
base_teste["previsto"] = previsoes_teste
base_teste["prob_gain"] = probs_teste

filtrado_teste = base_teste[base_teste["prob_gain"] >= melhor["threshold"]].copy()

print("\n" + "=" * 80)
print("RESULTADO NO TESTE FINAL")
print("=" * 80)
print("Acurácia do modelo no teste final:", acc_teste_modelo)

print("\nMatriz de confusão do modelo no teste final:")
print(confusion_matrix(y_teste, previsoes_teste))

print("\nRelatório do modelo no teste final:")
print(classification_report(y_teste, previsoes_teste, zero_division=0))

print("\nSinais filtrados no teste final:", len(filtrado_teste))

if len(filtrado_teste) >= MIN_SINAIS_TESTE:
    met_teste = avaliar_filtrado(filtrado_teste)

    print("Wins:", met_teste["wins"])
    print("Losses:", met_teste["losses"])
    print("Taxa de acerto:", round(met_teste["taxa_acerto"], 4))
    print("Lucro total em pontos:", round(met_teste["lucro_total_pontos"], 2))
    print("Lucro médio em pontos:", round(met_teste["lucro_medio_pontos"], 2))

    print("\nTabela dos sinais filtrados no teste final:")
    print(filtrado_teste[[
        "datetime_entrada", "tipo", "resultado", "prob_gain",
        "entrada", "preco_saida", "pnl_pontos",
        "bias", "k", "d", "atr", "stopFinal", "hora", "minuto"
    ]].head(50))
else:
    print("Poucos sinais passaram no filtro do teste final.")

# =====================================
# IMPORTÂNCIA DAS FEATURES
# =====================================
importancias = pd.DataFrame({
    "feature": features,
    "importancia": melhor_modelo.feature_importances_
}).sort_values("importancia", ascending=False)

print("\nImportância das features:")
print(importancias)

# =====================================
# SALVAR MODELO FINAL
# =====================================
joblib.dump({
    "modelo": melhor_modelo,
    "threshold": melhor["threshold"],
    "features": features,
    "modo": MODO,
    "melhor_validacao": melhor
}, "melhor_modelo_v2_sell.joblib")

filtrado_teste.to_csv("teste_final_filtrado_v2_sell.csv", index=False)

print("\nArquivos gerados:")
print("- ranking_validacao_v2_sell.csv")
print("- melhor_modelo_v2_sell.joblib")
print("- teste_final_filtrado_v2_sell.csv")