import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# =====================================
# CONFIGURAÇÕES
# =====================================
ARQUIVO = "dataset_setup_ml.csv"

# se quiser exigir um mínimo de sinais no teste
MIN_SINAIS_TESTE = 15

# thresholds testados
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]

# grade de parâmetros
N_ESTIMATORS_LIST = [100, 200, 300, 400]
MAX_DEPTH_LIST = [4, 6, 8, 10]
MIN_SAMPLES_LEAF_LIST = [2, 4, 6]
MIN_SAMPLES_SPLIT_LIST = [4, 8, 12]

RANDOM_STATE = 42

# =====================================
# LEITURA E PREPARO
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

# lucro real em pontos
# BUY: saida - entrada
# SELL: entrada - saida
df["pnl_pontos"] = np.where(
    df["tipo"] == "BUY",
    df["preco_saida"] - df["entrada"],
    df["entrada"] - df["preco_saida"]
)

# =====================================
# FEATURES
# =====================================
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

# mantém só colunas existentes
features = [col for col in features if col in df.columns]

# =====================================
# FUNÇÕES
# =====================================
def split_temporal(dataframe, pct=0.7):
    dataframe = dataframe.sort_values("datetime_entrada").reset_index(drop=True)
    corte = int(len(dataframe) * pct)
    treino = dataframe.iloc[:corte].copy()
    teste = dataframe.iloc[corte:].copy()
    return treino, teste

def avaliar_cenario(teste_filtrado):
    if len(teste_filtrado) == 0:
        return None

    n = len(teste_filtrado)
    wins = int((teste_filtrado["resultado"] == 1).sum())
    losses = int((teste_filtrado["resultado"] == 0).sum())
    taxa_acerto = wins / n if n > 0 else 0.0

    lucro_total = teste_filtrado["pnl_pontos"].sum()
    lucro_medio = teste_filtrado["pnl_pontos"].mean()
    mediana_lucro = teste_filtrado["pnl_pontos"].median()

    buy_n = int((teste_filtrado["tipo"] == "BUY").sum()) if "tipo" in teste_filtrado.columns else 0
    sell_n = int((teste_filtrado["tipo"] == "SELL").sum()) if "tipo" in teste_filtrado.columns else 0

    return {
        "sinais_teste_filtrados": n,
        "wins": wins,
        "losses": losses,
        "taxa_acerto": taxa_acerto,
        "lucro_total_pontos": lucro_total,
        "lucro_medio_pontos": lucro_medio,
        "mediana_lucro_pontos": mediana_lucro,
        "buy_filtrados": buy_n,
        "sell_filtrados": sell_n
    }

def rodar_modo(df_base, modo_nome):
    resultados = []
    melhor_modelo = None
    melhor_resultado = None
    melhor_threshold = None
    melhor_features = None

    treino, teste = split_temporal(df_base, pct=0.7)

    X_treino = treino[features].copy()
    y_treino = treino["resultado"].copy()

    X_teste = teste[features].copy()
    y_teste = teste["resultado"].copy()

    total_combinacoes = (
        len(N_ESTIMATORS_LIST)
        * len(MAX_DEPTH_LIST)
        * len(MIN_SAMPLES_LEAF_LIST)
        * len(MIN_SAMPLES_SPLIT_LIST)
        * len(THRESHOLDS)
    )

    contador = 0

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

        previsoes = modelo.predict(X_teste)
        probs = modelo.predict_proba(X_teste)[:, 1]

        acc = accuracy_score(y_teste, previsoes)

        teste_temp = teste.copy()
        teste_temp["previsto"] = previsoes
        teste_temp["prob_gain"] = probs

        for threshold in THRESHOLDS:
            contador += 1
            filtrado = teste_temp[teste_temp["prob_gain"] >= threshold].copy()

            if len(filtrado) < MIN_SINAIS_TESTE:
                continue

            met = avaliar_cenario(filtrado)
            if met is None:
                continue

            registro = {
                "modo": modo_nome,
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "min_samples_leaf": min_leaf,
                "min_samples_split": min_split,
                "threshold": threshold,
                "accuracy_modelo": acc,
                **met
            }

            # score principal = lucro total
            # desempate por lucro médio e taxa de acerto
            registro["score"] = (
                registro["lucro_total_pontos"]
                + registro["lucro_medio_pontos"] * 10
                + registro["taxa_acerto"] * 10
            )

            resultados.append(registro)

            if melhor_resultado is None or registro["score"] > melhor_resultado["score"]:
                melhor_resultado = registro
                melhor_modelo = modelo
                melhor_threshold = threshold
                melhor_features = features.copy()

    if melhor_resultado is None:
        return None, None, None, None, None

    return pd.DataFrame(resultados), melhor_resultado, melhor_modelo, melhor_threshold, melhor_features

# =====================================
# TESTAR MODOS
# =====================================
bases = {
    "GERAL": df.copy(),
    "BUY": df[df["tipo"] == "BUY"].copy(),
    "SELL": df[df["tipo"] == "SELL"].copy()
}

ranking_final = []
modelos_salvos = []

for modo, base in bases.items():
    if len(base) < 50:
        print(f"\nModo {modo}: poucos dados, ignorado.")
        continue

    print(f"\nTestando modo: {modo} | linhas: {len(base)}")

    resultados_df, melhor, modelo, threshold, feats = rodar_modo(base, modo)

    if resultados_df is None or melhor is None:
        print(f"Modo {modo}: nenhum cenário válido.")
        continue

    nome_csv = f"ranking_{modo.lower()}.csv"
    resultados_df = resultados_df.sort_values(
        ["score", "lucro_total_pontos", "taxa_acerto"],
        ascending=False
    ).reset_index(drop=True)

    resultados_df.to_csv(nome_csv, index=False)

    nome_modelo = f"melhor_modelo_{modo.lower()}.joblib"
    joblib.dump({
        "modelo": modelo,
        "threshold": threshold,
        "features": feats,
        "modo": modo
    }, nome_modelo)

    melhor["arquivo_ranking"] = nome_csv
    melhor["arquivo_modelo"] = nome_modelo

    ranking_final.append(melhor)
    modelos_salvos.append(nome_modelo)

# =====================================
# RESULTADO FINAL
# =====================================
if len(ranking_final) == 0:
    print("\nNenhum cenário válido encontrado.")
else:
    ranking_final_df = pd.DataFrame(ranking_final)
    ranking_final_df = ranking_final_df.sort_values(
        ["score", "lucro_total_pontos", "taxa_acerto"],
        ascending=False
    ).reset_index(drop=True)

    ranking_final_df.to_csv("ranking_final_melhores_cenarios.csv", index=False)

    print("\n" + "=" * 80)
    print("MELHORES CENÁRIOS ENCONTRADOS")
    print("=" * 80)
    print(ranking_final_df)

    print("\nMelhor cenário geral encontrado:")
    top = ranking_final_df.iloc[0]

    print(f"Modo: {top['modo']}")
    print(f"n_estimators: {top['n_estimators']}")
    print(f"max_depth: {top['max_depth']}")
    print(f"min_samples_leaf: {top['min_samples_leaf']}")
    print(f"min_samples_split: {top['min_samples_split']}")
    print(f"threshold: {top['threshold']}")
    print(f"Sinais filtrados no teste: {top['sinais_teste_filtrados']}")
    print(f"Wins: {top['wins']}")
    print(f"Losses: {top['losses']}")
    print(f"Taxa de acerto: {top['taxa_acerto']:.4f}")
    print(f"Lucro total em pontos: {top['lucro_total_pontos']:.2f}")
    print(f"Lucro médio em pontos: {top['lucro_medio_pontos']:.2f}")
    print(f"Score: {top['score']:.4f}")
    print(f"Arquivo ranking: {top['arquivo_ranking']}")
    print(f"Arquivo modelo: {top['arquivo_modelo']}")

    print("\nArquivos gerados:")
    print("- ranking_final_melhores_cenarios.csv")
    for item in modelos_salvos:
        print("-", item)