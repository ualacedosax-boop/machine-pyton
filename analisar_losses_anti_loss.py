import pandas as pd
import numpy as np
import os

# =====================================================
# ARQUIVOS
# =====================================================

PASTA_SAIDA = "saida_ml_entradas_video"

ARQUIVO_TRADES_BASE = os.path.join(PASTA_SAIDA, "23_anti_loss_trades_base_241.csv")
ARQUIVO_IMPORTANCIA = os.path.join(PASTA_SAIDA, "26_anti_loss_importancia_features.csv")

ARQUIVO_COMPARACAO = os.path.join(PASTA_SAIDA, "30_comparacao_win_loss_features.csv")
ARQUIVO_LOSSES = os.path.join(PASTA_SAIDA, "31_losses_detalhados.csv")
ARQUIVO_WINS = os.path.join(PASTA_SAIDA, "32_wins_detalhados.csv")
ARQUIVO_REGRAS_CANDIDATAS = os.path.join(PASTA_SAIDA, "33_regras_candidatas_anti_loss.csv")

# =====================================================
# CARREGAR
# =====================================================

print("Carregando trades base...")

df = pd.read_csv(ARQUIVO_TRADES_BASE)

df["DataHora_Sinal_SP"] = pd.to_datetime(df["DataHora_Sinal_SP"], errors="coerce")
df["dt_entrada"] = pd.to_datetime(df["dt_entrada"], errors="coerce")
df["dt_saida"] = pd.to_datetime(df["dt_saida"], errors="coerce")

df = df[df["resultado"].isin(["WIN", "LOSS"])].copy()

print("Total trades:", len(df))
print(df["resultado"].value_counts())

losses = df[df["resultado"] == "LOSS"].copy()
wins = df[df["resultado"] == "WIN"].copy()

print("Wins:", len(wins))
print("Losses:", len(losses))

# =====================================================
# SEPARAR FEATURES NUMÉRICAS
# =====================================================

feature_cols = []

for col in df.columns:
    if col.startswith("feat_"):
        if pd.api.types.is_numeric_dtype(df[col]):
            feature_cols.append(col)

# Adiciona algumas colunas úteis fora do prefixo feat_
for col in [
    "score_direcao",
    "score_oposto",
    "score_diff"
]:
    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
        feature_cols.append(col)

feature_cols = list(dict.fromkeys(feature_cols))

print("Features numéricas:", len(feature_cols))

# =====================================================
# COMPARAR MÉDIAS WIN x LOSS
# =====================================================

linhas = []

for col in feature_cols:
    serie_win = wins[col].replace([np.inf, -np.inf], np.nan).dropna()
    serie_loss = losses[col].replace([np.inf, -np.inf], np.nan).dropna()

    if len(serie_win) < 5 or len(serie_loss) < 2:
        continue

    media_win = serie_win.mean()
    media_loss = serie_loss.mean()
    mediana_win = serie_win.median()
    mediana_loss = serie_loss.median()

    std_win = serie_win.std()
    std_loss = serie_loss.std()

    min_loss = serie_loss.min()
    max_loss = serie_loss.max()

    p05_win = serie_win.quantile(0.05)
    p10_win = serie_win.quantile(0.10)
    p25_win = serie_win.quantile(0.25)
    p75_win = serie_win.quantile(0.75)
    p90_win = serie_win.quantile(0.90)
    p95_win = serie_win.quantile(0.95)

    diff_abs = media_loss - media_win
    diff_pct = diff_abs / abs(media_win) * 100 if media_win != 0 else np.nan

    # separação aproximada
    pooled_std = np.sqrt((std_win ** 2 + std_loss ** 2) / 2)
    efeito = diff_abs / pooled_std if pooled_std and pooled_std != 0 else np.nan

    linhas.append({
        "feature": col,
        "media_win": media_win,
        "media_loss": media_loss,
        "diff_loss_menos_win": diff_abs,
        "diff_pct": diff_pct,
        "efeito_aprox": efeito,
        "mediana_win": mediana_win,
        "mediana_loss": mediana_loss,
        "std_win": std_win,
        "std_loss": std_loss,
        "loss_min": min_loss,
        "loss_max": max_loss,
        "win_p05": p05_win,
        "win_p10": p10_win,
        "win_p25": p25_win,
        "win_p75": p75_win,
        "win_p90": p90_win,
        "win_p95": p95_win,
    })

comparacao = pd.DataFrame(linhas)

comparacao["abs_efeito"] = comparacao["efeito_aprox"].abs()
comparacao = comparacao.sort_values("abs_efeito", ascending=False)

comparacao.to_csv(ARQUIVO_COMPARACAO, index=False, encoding="utf-8-sig")

# =====================================================
# GERAR REGRAS CANDIDATAS SIMPLES
# =====================================================

print("Gerando regras candidatas...")

regras = []

for col in feature_cols:
    serie = df[col].replace([np.inf, -np.inf], np.nan)

    if serie.notna().sum() < 30:
        continue

    valores = serie.dropna()

    # thresholds por percentis
    percentis = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75,
                 0.80, 0.85, 0.90, 0.95, 0.98, 0.99]

    thresholds = sorted(set([valores.quantile(p) for p in percentis]))

    for th in thresholds:
        # regra: manter se col >= th
        mantem_ge = df[serie >= th].copy()

        if len(mantem_ge) > 0:
            wins_ge = (mantem_ge["resultado"] == "WIN").sum()
            losses_ge = (mantem_ge["resultado"] == "LOSS").sum()
            total_ge = wins_ge + losses_ge
            winrate_ge = wins_ge / total_ge * 100 if total_ge > 0 else 0

            regras.append({
                "feature": col,
                "operador": ">=",
                "threshold": th,
                "total_trades": total_ge,
                "wins": wins_ge,
                "losses": losses_ge,
                "winrate": winrate_ge,
                "bloqueados": len(df) - total_ge,
                "losses_bloqueados": len(losses) - losses_ge,
                "wins_bloqueados": len(wins) - wins_ge,
            })

        # regra: manter se col <= th
        mantem_le = df[serie <= th].copy()

        if len(mantem_le) > 0:
            wins_le = (mantem_le["resultado"] == "WIN").sum()
            losses_le = (mantem_le["resultado"] == "LOSS").sum()
            total_le = wins_le + losses_le
            winrate_le = wins_le / total_le * 100 if total_le > 0 else 0

            regras.append({
                "feature": col,
                "operador": "<=",
                "threshold": th,
                "total_trades": total_le,
                "wins": wins_le,
                "losses": losses_le,
                "winrate": winrate_le,
                "bloqueados": len(df) - total_le,
                "losses_bloqueados": len(losses) - losses_le,
                "wins_bloqueados": len(wins) - wins_le,
            })

regras_df = pd.DataFrame(regras)

# Prioriza:
# 1. maior winrate
# 2. mais trades
# 3. mais losses bloqueados
# 4. menos wins bloqueados
regras_df = regras_df.sort_values(
    by=["winrate", "total_trades", "losses_bloqueados", "wins_bloqueados"],
    ascending=[False, False, False, True]
)

regras_df.to_csv(ARQUIVO_REGRAS_CANDIDATAS, index=False, encoding="utf-8-sig")

# =====================================================
# SALVAR WINS E LOSSES DETALHADOS
# =====================================================

losses.to_csv(ARQUIVO_LOSSES, index=False, encoding="utf-8-sig")
wins.to_csv(ARQUIVO_WINS, index=False, encoding="utf-8-sig")

# =====================================================
# MOSTRAR RESULTADO
# =====================================================

print("\n=====================================================")
print("TOP 30 FEATURES QUE MAIS DIFERENCIAM LOSS")
print("=====================================================")
print(comparacao.head(30))

print("\n=====================================================")
print("TOP 30 REGRAS CANDIDATAS")
print("=====================================================")
print(regras_df.head(30))

print("\nArquivos gerados:")
print(ARQUIVO_COMPARACAO)
print(ARQUIVO_LOSSES)
print(ARQUIVO_WINS)
print(ARQUIVO_REGRAS_CANDIDATAS)