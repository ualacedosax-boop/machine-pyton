import os
import numpy as np
import pandas as pd


# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")

ARQUIVO_CANDIDATOS_SCORE = os.path.join(PASTA_V4, "04_v4_score_candidatos.csv.gz")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_V4, "checkpoint_v4_melhor_trades.csv.gz")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_V4, "checkpoint_v4_melhor.csv")

ARQUIVO_SAIDA_IMPORTANCIA = os.path.join(PASTA_V4, "09_v4_importancia_por_separacao_win_loss.csv")
ARQUIVO_SAIDA_REGRAS = os.path.join(PASTA_V4, "10_v4_regras_sugeridas_para_pine.csv")
ARQUIVO_TRADES_COM_FEATURES = os.path.join(PASTA_V4, "11_v4_melhor_trades_com_features.csv.gz")


# =====================================================
# FUNÇÕES
# =====================================================

def salvar_csv(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(temp, index=False, encoding="utf-8-sig", compression="gzip")
    else:
        df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def detectar_features(df):
    proibidas = {
        "indice_sinal",
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora_SP",
        "Direcao",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "prob_win_v4",
        "take_pontos",
        "stop_pontos",
        "resultado",
        "pontos",
        "dt_entrada",
        "dt_saida",
        "indice_saida",
        "runup",
        "drawdown",
    }

    proibidas_prefixos = [
        "resultado_stop_",
        "pontos_stop_",
        "dt_entrada_stop_",
        "dt_saida_stop_",
        "indice_saida_stop_",
        "runup_stop_",
        "drawdown_stop_",
        "target_win_stop_",
    ]

    features = []

    for col in df.columns:
        if col in proibidas:
            continue

        if any(col.startswith(p) for p in proibidas_prefixos):
            continue

        if pd.api.types.is_numeric_dtype(df[col]):
            features.append(col)

    return features


def classificar_sentido(media_win, media_loss):
    if pd.isna(media_win) or pd.isna(media_loss):
        return ""

    if media_win > media_loss:
        return "WIN_MAIOR"
    elif media_win < media_loss:
        return "WIN_MENOR"
    else:
        return "IGUAL"


# =====================================================
# CARREGAR DADOS
# =====================================================

print("Carregando resumo do melhor...")
melhor = pd.read_csv(ARQUIVO_MELHOR_RESUMO)

print("\nMelhor atual:")
print(melhor.T)

print("\nCarregando trades do melhor...")
trades = pd.read_csv(ARQUIVO_MELHOR_TRADES, compression="gzip")

trades["DataHora_Sinal_SP"] = pd.to_datetime(trades["DataHora_Sinal_SP"])

print("Trades:", len(trades))
print(trades["resultado"].value_counts())

print("\nCarregando candidatos com features...")
cand = pd.read_csv(ARQUIVO_CANDIDATOS_SCORE, compression="gzip")

cand["DataHora_SP"] = pd.to_datetime(cand["DataHora_SP"])

print("Candidatos:", len(cand))


# =====================================================
# JUNTAR TRADES COM FEATURES DOS CANDIDATOS
# =====================================================

trades_key = trades.copy()
cand_key = cand.copy()

trades_key["key"] = (
    trades_key["DataHora_Sinal_SP"].astype(str) + "|" +
    trades_key["Direcao"].astype(str)
)

cand_key["key"] = (
    cand_key["DataHora_SP"].astype(str) + "|" +
    cand_key["Direcao"].astype(str)
)

cols_cand = [c for c in cand_key.columns if c not in trades_key.columns or c == "key"]

trades_feat = trades_key.merge(
    cand_key[cols_cand],
    on="key",
    how="left",
    suffixes=("", "_cand")
)

print("\nTrades com features:", len(trades_feat))
print("Linhas sem match:", trades_feat["DataHora_SP"].isna().sum() if "DataHora_SP" in trades_feat.columns else "verificar")


# =====================================================
# DETECTAR FEATURES E CALCULAR SEPARAÇÃO
# =====================================================

features = detectar_features(trades_feat)

print("Features detectadas:", len(features))

registros = []

wins_df = trades_feat[trades_feat["resultado"] == "WIN"].copy()
loss_df = trades_feat[trades_feat["resultado"] == "LOSS"].copy()

for feature in features:
    serie_win = pd.to_numeric(wins_df[feature], errors="coerce")
    serie_loss = pd.to_numeric(loss_df[feature], errors="coerce")

    media_win = serie_win.mean()
    media_loss = serie_loss.mean()

    mediana_win = serie_win.median()
    mediana_loss = serie_loss.median()

    std_win = serie_win.std()
    std_loss = serie_loss.std()

    std_pool = np.nanmean([std_win, std_loss])

    diff = media_win - media_loss

    if pd.isna(std_pool) or std_pool == 0:
        forca = np.nan
    else:
        forca = abs(diff) / std_pool

    q25_win = serie_win.quantile(0.25)
    q75_win = serie_win.quantile(0.75)
    q25_loss = serie_loss.quantile(0.25)
    q75_loss = serie_loss.quantile(0.75)

    sentido = classificar_sentido(media_win, media_loss)

    registros.append({
        "feature": feature,
        "media_win": media_win,
        "media_loss": media_loss,
        "diff_win_loss": diff,
        "forca_separacao": forca,
        "mediana_win": mediana_win,
        "mediana_loss": mediana_loss,
        "q25_win": q25_win,
        "q75_win": q75_win,
        "q25_loss": q25_loss,
        "q75_loss": q75_loss,
        "std_win": std_win,
        "std_loss": std_loss,
        "sentido": sentido,
        "n_win_validos": serie_win.notna().sum(),
        "n_loss_validos": serie_loss.notna().sum(),
    })

imp = pd.DataFrame(registros)

imp = imp.sort_values(
    by=["forca_separacao", "diff_win_loss"],
    ascending=[False, False]
).reset_index(drop=True)

salvar_csv(imp, ARQUIVO_SAIDA_IMPORTANCIA, compactado=False)


# =====================================================
# GERAR REGRAS SUGERIDAS
# =====================================================

regras = []

for _, row in imp.head(80).iterrows():
    feature = row["feature"]

    if row["sentido"] == "WIN_MAIOR":
        operador = ">="
        threshold_suave = row["q25_win"]
        threshold_forte = row["mediana_win"]
    elif row["sentido"] == "WIN_MENOR":
        operador = "<="
        threshold_suave = row["q75_win"]
        threshold_forte = row["mediana_win"]
    else:
        operador = ""
        threshold_suave = np.nan
        threshold_forte = np.nan

    regras.append({
        "feature": feature,
        "sentido": row["sentido"],
        "operador_sugerido": operador,
        "threshold_suave": threshold_suave,
        "threshold_forte": threshold_forte,
        "forca_separacao": row["forca_separacao"],
        "media_win": row["media_win"],
        "media_loss": row["media_loss"],
        "mediana_win": row["mediana_win"],
        "mediana_loss": row["mediana_loss"],
        "q25_win": row["q25_win"],
        "q75_win": row["q75_win"],
        "q25_loss": row["q25_loss"],
        "q75_loss": row["q75_loss"],
    })

regras_df = pd.DataFrame(regras)

salvar_csv(regras_df, ARQUIVO_SAIDA_REGRAS, compactado=False)

salvar_csv(trades_feat, ARQUIVO_TRADES_COM_FEATURES, compactado=True)


# =====================================================
# RELATÓRIO
# =====================================================

print("\n=====================================================")
print("TOP 40 FEATURES QUE MAIS SEPARAM WIN X LOSS")
print("=====================================================")

print(imp.head(40)[[
    "feature",
    "forca_separacao",
    "media_win",
    "media_loss",
    "mediana_win",
    "mediana_loss",
    "sentido"
]])

print("\n=====================================================")
print("TOP 40 REGRAS SUGERIDAS PARA PINE")
print("=====================================================")

print(regras_df.head(40)[[
    "feature",
    "operador_sugerido",
    "threshold_suave",
    "threshold_forte",
    "forca_separacao"
]])

print("\nArquivos gerados:")
print(ARQUIVO_SAIDA_IMPORTANCIA)
print(ARQUIVO_SAIDA_REGRAS)
print(ARQUIVO_TRADES_COM_FEATURES)