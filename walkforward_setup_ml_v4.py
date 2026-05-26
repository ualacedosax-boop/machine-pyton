import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import RandomForestClassifier
import joblib

# =====================================
# CONFIG
# =====================================
ARQUIVO = "dataset_setup_ml.csv"
MODO = "SELL"   # pode trocar para BUY depois

# parâmetros do modelo
N_ESTIMATORS_LIST = [100, 200]
MAX_DEPTH_LIST = [4, 6, 8]
MIN_SAMPLES_LEAF_LIST = [2, 4]
MIN_SAMPLES_SPLIT_LIST = [4, 8]

# filtros
THRESHOLDS = [0.50, 0.55, 0.60, 0.65]
STOP_MAX_LIST = [90, 100, 105, 110, 117]
HORA_INICIO_LIST = [0, 4, 8]
HORA_FIM_LIST = [12, 16, 20, 23]

RANDOM_STATE = 42

# walk-forward
TRAIN_SIZE = 80
TEST_SIZE = 20
STEP_SIZE = 20

MIN_SINAIS_TESTE = 5

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

df["pnl_pontos"] = np.where(
    df["tipo"] == "BUY",
    df["preco_saida"] - df["entrada"],
    df["entrada"] - df["preco_saida"]
)

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
# FUNÇÕES
# =====================================
def aplicar_filtros(base, threshold, stop_max, hora_inicio, hora_fim):
    b = base.copy()
    b = b[b["prob_gain"] >= threshold].copy()
    b = b[b["stopFinal"] <= stop_max].copy()

    if hora_inicio <= hora_fim:
        b = b[(b["hora"] >= hora_inicio) & (b["hora"] <= hora_fim)].copy()
    else:
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

    ganhos = float(base_filtrada.loc[base_filtrada["pnl_pontos"] > 0, "pnl_pontos"].sum())
    perdas = float(base_filtrada.loc[base_filtrada["pnl_pontos"] < 0, "pnl_pontos"].sum())
    perdas_abs = abs(perdas)

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

def gerar_janelas(n_total, train_size, test_size, step_size):
    janelas = []
    inicio_treino = 0

    while True:
        fim_treino = inicio_treino + train_size
        inicio_teste = fim_treino
        fim_teste = inicio_teste + test_size

        if fim_teste > n_total:
            break

        janelas.append((inicio_treino, fim_treino, inicio_teste, fim_teste))
        inicio_treino += step_size

    return janelas

# =====================================
# WALK-FORWARD
# =====================================
janelas = gerar_janelas(len(df), TRAIN_SIZE, TEST_SIZE, STEP_SIZE)

if len(janelas) == 0:
    print("\nPoucos dados para as janelas configuradas.")
    raise SystemExit

print("\nQuantidade de janelas walk-forward:", len(janelas))

resultados_janelas = []
melhor_global = None
melhor_modelo_global = None

for idx, (ini_tr, fim_tr, ini_te, fim_te) in enumerate(janelas, start=1):
    treino = df.iloc[ini_tr:fim_tr].copy()
    teste = df.iloc[ini_te:fim_te].copy()

    X_treino = treino[features].copy()
    y_treino = treino["resultado"].copy()

    X_teste = teste[features].copy()
    y_teste = teste["resultado"].copy()

    melhor_janela = None
    melhor_modelo_janela = None
    base_teste_melhor = None

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

        probs_teste = modelo.predict_proba(X_teste)[:, 1]
        base_teste = teste.copy()
        base_teste["prob_gain"] = probs_teste

        for threshold, stop_max, hora_inicio, hora_fim in product(
            THRESHOLDS,
            STOP_MAX_LIST,
            HORA_INICIO_LIST,
            HORA_FIM_LIST
        ):
            filtrado = aplicar_filtros(base_teste, threshold, stop_max, hora_inicio, hora_fim)

            if len(filtrado) < MIN_SINAIS_TESTE:
                continue

            met = avaliar_financeiro(filtrado)
            if met is None:
                continue

            registro = {
                "janela": idx,
                "treino_inicio": treino["datetime_entrada"].iloc[0],
                "treino_fim": treino["datetime_entrada"].iloc[-1],
                "teste_inicio": teste["datetime_entrada"].iloc[0],
                "teste_fim": teste["datetime_entrada"].iloc[-1],
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "min_samples_leaf": min_leaf,
                "min_samples_split": min_split,
                "threshold": threshold,
                "stop_max": stop_max,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                **met
            }

            registro["score"] = (
                registro["lucro_total_pontos"]
                + registro["expectancy"] * 20
                + registro["profit_factor"] * 25
                + registro["taxa_acerto"] * 10
                + registro["sinais"] * 0.5
            )

            if melhor_janela is None or registro["score"] > melhor_janela["score"]:
                melhor_janela = registro
                melhor_modelo_janela = modelo
                base_teste_melhor = filtrado.copy()

    if melhor_janela is not None:
        resultados_janelas.append(melhor_janela)

        print("\n" + "=" * 80)
        print(f"MELHOR CENÁRIO DA JANELA {idx}")
        print("=" * 80)
        print(melhor_janela)

        if melhor_global is None or melhor_janela["score"] > melhor_global["score"]:
            melhor_global = melhor_janela
            melhor_modelo_global = melhor_modelo_janela
    else:
        print("\n" + "=" * 80)
        print(f"JANELA {idx} sem cenário válido")
        print("=" * 80)

# =====================================
# RESUMO FINAL
# =====================================
if len(resultados_janelas) == 0:
    print("\nNenhum cenário válido encontrado em nenhuma janela.")
    raise SystemExit

resultado_df = pd.DataFrame(resultados_janelas)
resultado_df.to_csv("walkforward_resultados_v4.csv", index=False)

print("\n" + "=" * 80)
print("RESUMO WALK-FORWARD")
print("=" * 80)
print(resultado_df)

print("\nMédias das janelas:")
print(resultado_df[[
    "sinais", "wins", "losses", "taxa_acerto",
    "lucro_total_pontos", "lucro_medio_pontos",
    "profit_factor", "expectancy", "score"
]].mean())

print("\nMedianas das janelas:")
print(resultado_df[[
    "sinais", "wins", "losses", "taxa_acerto",
    "lucro_total_pontos", "lucro_medio_pontos",
    "profit_factor", "expectancy", "score"
]].median())

janelas_positivas = int((resultado_df["lucro_total_pontos"] > 0).sum())
janelas_negativas = int((resultado_df["lucro_total_pontos"] <= 0).sum())

print("\nJanelas positivas:", janelas_positivas)
print("Janelas negativas:", janelas_negativas)

print("\nMelhor cenário global entre as janelas:")
print(melhor_global)

# =====================================
# IMPORTÂNCIA DAS FEATURES
# =====================================
if melhor_modelo_global is not None:
    importancias = pd.DataFrame({
        "feature": features,
        "importancia": melhor_modelo_global.feature_importances_
    }).sort_values("importancia", ascending=False)

    print("\nImportância das features do melhor modelo global:")
    print(importancias)

    joblib.dump({
        "modelo": melhor_modelo_global,
        "features": features,
        "modo": MODO,
        "melhor_global": melhor_global
    }, "melhor_modelo_walkforward_v4.joblib")

print("\nArquivos gerados:")
print("- walkforward_resultados_v4.csv")
print("- melhor_modelo_walkforward_v4.joblib")