import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# =====================================
# CONFIG
# =====================================
ARQUIVO = "dataset_setup_ml.csv"

MODO = "SELL"   # pode trocar para BUY depois

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70]
N_ESTIMATORS_LIST = [100, 200, 300]
MAX_DEPTH_LIST = [4, 6, 8, 10]
MIN_SAMPLES_LEAF_LIST = [2, 4, 6]
MIN_SAMPLES_SPLIT_LIST = [4, 8, 12]

# novos filtros
STOP_MAX_LIST = [90, 100, 105, 110, 117]
HORA_INICIO_LIST = [0, 4, 8]
HORA_FIM_LIST = [12, 16, 20, 23]

MIN_SINAIS_VALIDACAO = 10
MIN_SINAIS_TESTE = 10

RANDOM_STATE = 42

# =====================================
# LEITURA
# =====================================
df = pd.read_csv(ARQUIVO)

df["datetime_entrada"] = pd.to_datetime(df["datetime_entrada"])
df["datetime_saida"] = pd.to_datetime(df["datetime_saida"])

bool_cols = [
    "crossUpRecent", "crossDownRecent",
    "stochCaindo", "stochSubindo",
    "toqueNaMedia", "filtroCompraVol", "filtroVendaVol"
]

for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].astype(int)

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
def aplicar_filtros(base, stop_max, hora_inicio, hora_fim):
    b = base.copy()
    b = b[b["stopFinal"] <= stop_max].copy()

    if hora_inicio <= hora_fim:
        b = b[(b["hora"] >= hora_inicio) & (b["hora"] <= hora_fim)].copy()
    else:
        # caso queira janela atravessando meia-noite
        b = b[(b["hora"] >= hora_inicio) | (b["hora"] <= hora_fim)].copy()

    return b

def avaliar_financeiro(base_filtrada):
    if len(base_filtrada) == 0:
        return None

    n = len(base_filtrada)
    wins = int((base_filtrada["resultado"] == 1).sum())
    losses = int((base_filtrada["resultado"] == 0).sum())

    taxa = wins / n if n > 0 else 0.0

    lucro_total = float(base_filtrada["pnl_pontos"].sum())
    lucro_medio = float(base_filtrada["pnl_pontos"].mean())
    mediana = float(base_filtrada["pnl_pontos"].median())

    ganhos = base_filtrada.loc[base_filtrada["pnl_pontos"] > 0, "pnl_pontos"].sum()
    perdas = base_filtrada.loc[base_filtrada["pnl_pontos"] < 0, "pnl_pontos"].sum()

    perdas_abs = abs(float(perdas))
    ganhos = float(ganhos)

    if perdas_abs > 0:
        profit_factor = ganhos / perdas_abs
    else:
        profit_factor = 999.0 if ganhos > 0 else 0.0

    expectancy = lucro_total / n if n > 0 else 0.0

    return {
        "sinais": n,
        "wins": wins,
        "losses": losses,
        "taxa_acerto": taxa,
        "lucro_total_pontos": lucro_total,
        "lucro_medio_pontos": lucro_medio,
        "mediana_pontos": mediana,
        "profit_factor": profit_factor,
        "expectancy": expectancy
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

    for threshold, stop_max, hora_inicio, hora_fim in product(
        THRESHOLDS,
        STOP_MAX_LIST,
        HORA_INICIO_LIST,
        HORA_FIM_LIST
    ):
        if len(HORA_INICIO_LIST) and len(HORA_FIM_LIST):
            pass

        filtrado = base_valid[base_valid["prob_gain"] >= threshold].copy()
        filtrado = aplicar_filtros(filtrado, stop_max, hora_inicio, hora_fim)

        if len(filtrado) < MIN_SINAIS_VALIDACAO:
            continue

        met = avaliar_financeiro(filtrado)
        if met is None:
            continue

        registro = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_leaf,
            "min_samples_split": min_split,
            "threshold": threshold,
            "stop_max": stop_max,
            "hora_inicio": hora_inicio,
            "hora_fim": hora_fim,
            "acc_valid_modelo": acc_valid,
            **met
        }

        # score financeiro
        # foco: lucro total, expectancy e profit factor
        # penaliza cenários com poucos sinais
        registro["score"] = (
            registro["lucro_total_pontos"]
            + registro["expectancy"] * 20
            + registro["profit_factor"] * 25
            + registro["taxa_acerto"] * 10
            + registro["sinais"] * 0.5
        )

        resultados_validacao.append(registro)

        if melhor is None or registro["score"] > melhor["score"]:
            melhor = registro
            melhor_modelo = modelo

if len(resultados_validacao) == 0:
    print("\nNenhum cenário válido encontrado na validação.")
    raise SystemExit

ranking_valid = pd.DataFrame(resultados_validacao).sort_values(
    ["score", "lucro_total_pontos", "profit_factor", "expectancy"],
    ascending=False
).reset_index(drop=True)

ranking_valid.to_csv("ranking_validacao_v3.csv", index=False)

print("\n" + "=" * 80)
print("TOP 20 VALIDAÇÃO")
print("=" * 80)
print(ranking_valid.head(20))

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
filtrado_teste = aplicar_filtros(
    filtrado_teste,
    melhor["stop_max"],
    melhor["hora_inicio"],
    melhor["hora_fim"]
)

print("\n" + "=" * 80)
print("RESULTADO NO TESTE FINAL")
print("=" * 80)
print("Acurácia do modelo no teste final:", acc_teste_modelo)
print("Sinais filtrados no teste final:", len(filtrado_teste))

if len(filtrado_teste) >= MIN_SINAIS_TESTE:
    met_teste = avaliar_financeiro(filtrado_teste)

    print("Wins:", met_teste["wins"])
    print("Losses:", met_teste["losses"])
    print("Taxa de acerto:", round(met_teste["taxa_acerto"], 4))
    print("Lucro total em pontos:", round(met_teste["lucro_total_pontos"], 2))
    print("Lucro médio em pontos:", round(met_teste["lucro_medio_pontos"], 2))
    print("Mediana em pontos:", round(met_teste["mediana_pontos"], 2))
    print("Profit factor:", round(met_teste["profit_factor"], 4))
    print("Expectancy:", round(met_teste["expectancy"], 4))

    print("\nParâmetros escolhidos:")
    print("threshold:", melhor["threshold"])
    print("stop_max:", melhor["stop_max"])
    print("hora_inicio:", melhor["hora_inicio"])
    print("hora_fim:", melhor["hora_fim"])

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
# SALVAR
# =====================================
joblib.dump({
    "modelo": melhor_modelo,
    "features": features,
    "modo": MODO,
    "melhor_validacao": melhor
}, "melhor_modelo_v3.joblib")

filtrado_teste.to_csv("teste_final_filtrado_v3.csv", index=False)

print("\nArquivos gerados:")
print("- ranking_validacao_v3.csv")
print("- melhor_modelo_v3.joblib")
print("- teste_final_filtrado_v3.csv")