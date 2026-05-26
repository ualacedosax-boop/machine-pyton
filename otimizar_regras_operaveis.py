import pandas as pd
import numpy as np
import os
import itertools

# =====================================================
# CONFIGURAÇÕES
# =====================================================

PASTA_SAIDA = "saida_ml_entradas_video"

ARQUIVO_TRADES_BASE = os.path.join(PASTA_SAIDA, "23_anti_loss_trades_base_241.csv")
ARQUIVO_REGRAS = os.path.join(PASTA_SAIDA, "33_regras_candidatas_anti_loss.csv")

PASTA_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoints_regras_operaveis")
os.makedirs(PASTA_CHECKPOINT, exist_ok=True)

ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "34_resultados_regras_operaveis.csv.gz")
ARQUIVO_TOP100 = os.path.join(PASTA_SAIDA, "35_top100_regras_operaveis.csv.gz")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "36_melhor_trades_regras_operaveis.csv.gz")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_SAIDA, "37_melhor_resumo_regras_operaveis.csv")

ARQUIVO_CHECKPOINT = os.path.join(PASTA_CHECKPOINT, "checkpoint_resultados_regras_operaveis.csv.gz")
ARQUIVO_CHECKPOINT_MELHOR = os.path.join(PASTA_CHECKPOINT, "checkpoint_melhor_resumo_regras_operaveis.csv")
ARQUIVO_CHECKPOINT_TRADES = os.path.join(PASTA_CHECKPOINT, "checkpoint_melhor_trades_regras_operaveis.csv.gz")

SALVAR_A_CADA = 500

# Quantas regras combinar
MAX_REGRAS_COMBINADAS = 3

# Quantidade máxima de regras candidatas usadas no combinador
TOP_REGRAS_POR_WINRATE = 250

# Mínimo interessante apenas para relatório
MIN_TRADES_INTERESSANTE = 50


# =====================================================
# FUNÇÕES DE SALVAMENTO SEGURO
# =====================================================

def remover_temporarios():
    for pasta in [PASTA_SAIDA, PASTA_CHECKPOINT]:
        if not os.path.exists(pasta):
            continue

        for nome in os.listdir(pasta):
            if nome.endswith(".tmp"):
                caminho = os.path.join(pasta, nome)
                try:
                    os.remove(caminho)
                    print("Arquivo temporário removido:", caminho)
                except Exception as e:
                    print("Não conseguiu remover temporário:", caminho, e)


def salvar_csv_seguro(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(
            temp,
            index=False,
            encoding="utf-8-sig",
            compression="gzip"
        )
    else:
        df.to_csv(
            temp,
            index=False,
            encoding="utf-8-sig"
        )

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)


def carregar_csv(caminho, compactado=False):
    if compactado:
        return pd.read_csv(caminho, compression="gzip")
    return pd.read_csv(caminho)


def limpar_feature_nome(feature):
    return str(feature).strip()


# =====================================================
# LIMPAR TEMPORÁRIOS ANTIGOS
# =====================================================

remover_temporarios()


# =====================================================
# CARREGAR DADOS
# =====================================================

print("Carregando trades base...")

trades = pd.read_csv(ARQUIVO_TRADES_BASE)

trades["DataHora_Sinal_SP"] = pd.to_datetime(trades["DataHora_Sinal_SP"], errors="coerce")
trades = trades[trades["resultado"].isin(["WIN", "LOSS"])].copy()

print("Trades carregados:", len(trades))
print(trades["resultado"].value_counts())

print("\nCarregando regras candidatas...")

regras = pd.read_csv(ARQUIVO_REGRAS)

print("Regras candidatas carregadas:", len(regras))


# =====================================================
# REMOVER FEATURES PROIBIDAS
# =====================================================

proibidas_futuro = [
    "runup",
    "drawdown",
    "candles_ate_saida",
    "minutos_ate_saida",
    "preco_saida",
    "dt_saida",
    "resultado",
    "pontos",
]

proibidas_preco_absoluto = [
    "feat_open",
    "feat_high",
    "feat_low",
    "feat_close",
    "feat_average",
    "feat_high_max",
    "feat_low_min",
    "feat_ema_",
    "feat_bb_mid",
    "feat_bb_upper",
    "feat_bb_lower",
    "feat_kc_mid",
    "feat_kc_upper",
    "feat_kc_lower",
]

permitidas_prefixos = [
    "feat_score_BUY",
    "feat_score_SELL",
    "feat_score_NONE",
    "feat_score_diff_buy_sell",
    "feat_score_max",
    "feat_score_gap_direcional",

    "feat_range",
    "feat_body",
    "feat_body_abs",
    "feat_upper_wick",
    "feat_lower_wick",
    "feat_body_range_pct",
    "feat_close_pos_range",

    "feat_ret_",
    "feat_pts_change_",
    "feat_range_ratio_",
    "feat_volume_ratio_",
    "feat_dist_high_max_",
    "feat_dist_low_min_",
    "feat_pos_range_",

    "feat_dist_ema_",
    "feat_ema_9_slope",
    "feat_ema_17_slope",
    "feat_ema_20_slope",
    "feat_ema_34_slope",
    "feat_ema_50_slope",
    "feat_ema_100_slope",
    "feat_ema_200_slope",

    "feat_bias_",
    "feat_rsi_",
    "feat_stochrsi_",
    "feat_atr_",
    "feat_atrp_",

    "feat_bb_width_",
    "feat_bb_pos_",
    "feat_kc_pos_",

    "feat_ema17_acima_ema34",
    "feat_ema9_acima_ema17",
    "feat_close_acima_ema17",
    "feat_close_acima_ema34",
    "feat_dist_ema17_34",

    "feat_sin_hora",
    "feat_cos_hora",
    "feat_Hora_SP_Decimal",
    "feat_DiaSemana",
    "feat_Mes",
    "feat_DiaMes",

    "score_direcao",
    "score_oposto",
    "score_diff",
]


def feature_permitida(feature):
    f = str(feature)

    for proibida in proibidas_futuro:
        if proibida in f:
            return False

    for proibida in proibidas_preco_absoluto:
        if proibida in f:
            return False

    for pref in permitidas_prefixos:
        if f.startswith(pref):
            return True

    return False


regras["feature"] = regras["feature"].apply(limpar_feature_nome)

regras_filtradas = regras[regras["feature"].apply(feature_permitida)].copy()

# Garante que a feature existe nos trades
regras_filtradas = regras_filtradas[regras_filtradas["feature"].isin(trades.columns)].copy()

regras_filtradas = regras_filtradas.sort_values(
    by=["winrate", "total_trades", "losses_bloqueados", "wins_bloqueados"],
    ascending=[False, False, False, True]
).reset_index(drop=True)

regras_filtradas = regras_filtradas.head(TOP_REGRAS_POR_WINRATE).copy()

print("\nRegras operáveis filtradas:", len(regras_filtradas))
print(regras_filtradas.head(20))


# =====================================================
# CARREGAR CHECKPOINT
# =====================================================

if os.path.exists(ARQUIVO_CHECKPOINT):
    print("\nCheckpoint compactado encontrado. Continuando...")

    resultados_df = carregar_csv(ARQUIVO_CHECKPOINT, compactado=True)
    resultados = resultados_df.to_dict("records")

    configs_testadas = set(resultados_df["config_key"].astype(str).tolist())

    print("Resultados carregados:", len(resultados))
    print("Configurações já testadas:", len(configs_testadas))
else:
    print("\nNenhum checkpoint compactado encontrado. Iniciando do zero...")
    resultados = []
    configs_testadas = set()

melhor_resumo = None
melhor_trades = None

if os.path.exists(ARQUIVO_CHECKPOINT_MELHOR):
    temp = carregar_csv(ARQUIVO_CHECKPOINT_MELHOR, compactado=False)

    if not temp.empty:
        melhor_resumo = temp.iloc[0].to_dict()
        print("Melhor resumo carregado.")

if os.path.exists(ARQUIVO_CHECKPOINT_TRADES):
    temp_trades = carregar_csv(ARQUIVO_CHECKPOINT_TRADES, compactado=True)

    if not temp_trades.empty:
        melhor_trades = temp_trades
        print("Melhores trades carregados.")


# =====================================================
# APLICAR REGRA
# =====================================================

def aplicar_regra(df, regra):
    feature = regra["feature"]
    operador = regra["operador"]
    threshold = regra["threshold"]

    if feature not in df.columns:
        return pd.Series(False, index=df.index)

    serie = pd.to_numeric(df[feature], errors="coerce")

    if operador == ">=":
        return serie >= threshold

    if operador == "<=":
        return serie <= threshold

    return pd.Series(False, index=df.index)


def avaliar_combo(combo_regras):
    mask = pd.Series(True, index=trades.index)

    descricoes = []

    for _, regra in combo_regras.iterrows():
        mask_regra = aplicar_regra(trades, regra)
        mask = mask & mask_regra

        descricoes.append(
            f"{regra['feature']} {regra['operador']} {regra['threshold']}"
        )

    filtrados = trades[mask].copy()

    if filtrados.empty:
        return None, filtrados

    total = len(filtrados)
    wins = (filtrados["resultado"] == "WIN").sum()
    losses = (filtrados["resultado"] == "LOSS").sum()
    winrate = wins / total * 100 if total > 0 else 0
    lucro = filtrados["pontos"].sum() if "pontos" in filtrados.columns else np.nan

    buy_total = (filtrados["Direcao"] == "BUY").sum() if "Direcao" in filtrados.columns else np.nan
    sell_total = (filtrados["Direcao"] == "SELL").sum() if "Direcao" in filtrados.columns else np.nan

    resumo = {
        "qtd_regras": len(combo_regras),
        "descricao_regras": " AND ".join(descricoes),
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro,
        "buy_total": buy_total,
        "sell_total": sell_total,
        "config_key": " || ".join(descricoes),
    }

    for i, (_, regra) in enumerate(combo_regras.iterrows(), start=1):
        resumo[f"regra_{i}_feature"] = regra["feature"]
        resumo[f"regra_{i}_operador"] = regra["operador"]
        resumo[f"regra_{i}_threshold"] = regra["threshold"]

    return resumo, filtrados


def atualizar_melhor(resumo, filtrados):
    global melhor_resumo, melhor_trades

    if resumo is None:
        return

    chave_atual = (
        resumo["winrate"],
        resumo["total_trades"],
        resumo["lucro_pontos"]
    )

    if melhor_resumo is None:
        melhor_resumo = resumo
        melhor_trades = filtrados.copy()

        print("\nNOVO MELHOR:")
        print(pd.Series(melhor_resumo))
        return

    chave_melhor = (
        melhor_resumo["winrate"],
        melhor_resumo["total_trades"],
        melhor_resumo["lucro_pontos"]
    )

    if chave_atual > chave_melhor:
        melhor_resumo = resumo
        melhor_trades = filtrados.copy()

        print("\nNOVO MELHOR:")
        print(pd.Series(melhor_resumo))


def salvar_checkpoint():
    if resultados:
        df_res = pd.DataFrame(resultados)
        salvar_csv_seguro(df_res, ARQUIVO_CHECKPOINT, compactado=True)

    if melhor_resumo is not None:
        salvar_csv_seguro(
            pd.DataFrame([melhor_resumo]),
            ARQUIVO_CHECKPOINT_MELHOR,
            compactado=False
        )

    if melhor_trades is not None and not melhor_trades.empty:
        salvar_csv_seguro(
            melhor_trades,
            ARQUIVO_CHECKPOINT_TRADES,
            compactado=True
        )

    print(f"CHECKPOINT COMPACTADO SALVO | resultados: {len(resultados)}")


# =====================================================
# TESTAR COMBINAÇÕES
# =====================================================

print("\nIniciando teste de combinações operáveis...")

contador = 0
novos_desde_checkpoint = 0

try:
    indices = list(regras_filtradas.index)

    for tamanho in range(1, MAX_REGRAS_COMBINADAS + 1):
        print(f"\nTestando combinações com {tamanho} regra(s)...")

        for combo_idx in itertools.combinations(indices, tamanho):
            combo_regras = regras_filtradas.loc[list(combo_idx)].copy()

            # Evita combinar a mesma feature repetida
            if combo_regras["feature"].duplicated().any():
                continue

            config_key_preview = " || ".join([
                f"{r['feature']} {r['operador']} {r['threshold']}"
                for _, r in combo_regras.iterrows()
            ])

            if config_key_preview in configs_testadas:
                continue

            contador += 1

            resumo, filtrados = avaliar_combo(combo_regras)

            configs_testadas.add(config_key_preview)

            if resumo is not None:
                resultados.append(resumo)
                atualizar_melhor(resumo, filtrados)

            novos_desde_checkpoint += 1

            if novos_desde_checkpoint >= SALVAR_A_CADA:
                print(f"\nSalvando checkpoint após {contador} combinações nesta execução...")
                salvar_checkpoint()
                novos_desde_checkpoint = 0

            if contador % 1000 == 0:
                print(
                    f"Combinações testadas nesta execução: {contador} | "
                    f"Resultados acumulados: {len(resultados)}"
                )

except KeyboardInterrupt:
    print("\nInterrompido pelo usuário. Salvando checkpoint...")
    salvar_checkpoint()
    raise SystemExit

except Exception as e:
    print("\nERRO:")
    print(e)
    print("Salvando checkpoint...")
    salvar_checkpoint()
    raise

print("\nFinalizando e salvando arquivos finais...")

salvar_checkpoint()


# =====================================================
# GERAR ARQUIVOS FINAIS
# =====================================================

resultados_df = pd.DataFrame(resultados)

if resultados_df.empty:
    print("Nenhum resultado gerado.")
    raise SystemExit

resultados_df = resultados_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

salvar_csv_seguro(resultados_df, ARQUIVO_RESULTADOS, compactado=True)

top100 = resultados_df[resultados_df["winrate"] == 100.0].copy()

if not top100.empty:
    top100 = top100.sort_values(
        by=["total_trades", "lucro_pontos"],
        ascending=[False, False]
    )

salvar_csv_seguro(top100, ARQUIVO_TOP100, compactado=True)

if melhor_trades is not None and not melhor_trades.empty:
    salvar_csv_seguro(melhor_trades, ARQUIVO_MELHOR_TRADES, compactado=True)

if melhor_resumo is not None:
    salvar_csv_seguro(pd.DataFrame([melhor_resumo]), ARQUIVO_MELHOR_RESUMO, compactado=False)


# =====================================================
# RELATÓRIO
# =====================================================

print("\n=====================================================")
print("MELHOR RESULTADO")
print("=====================================================")

if melhor_resumo is not None:
    print(pd.Series(melhor_resumo))

print("\n=====================================================")
print("TOP 30 COM 100%")
print("=====================================================")

if top100.empty:
    print("Nenhuma combinação com 100%.")
else:
    print(top100.head(30))

print("\n=====================================================")
print("MELHORES POR FAIXA DE TRADES")
print("=====================================================")

for minimo in [50, 75, 85, 100, 125, 150, 180, 200]:
    filtro = resultados_df[resultados_df["total_trades"] >= minimo].copy()

    if filtro.empty:
        print(f"\nMínimo {minimo}: nenhum resultado.")
        continue

    melhor = filtro.sort_values(
        by=["winrate", "total_trades", "lucro_pontos"],
        ascending=[False, False, False]
    ).iloc[0]

    print(f"\nMínimo {minimo}:")
    print(melhor[[
        "winrate",
        "total_trades",
        "wins",
        "losses",
        "lucro_pontos",
        "descricao_regras"
    ]])


print("\n=====================================================")
print("ARQUIVOS GERADOS")
print("=====================================================")
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_TOP100)
print(ARQUIVO_MELHOR_TRADES)
print(ARQUIVO_MELHOR_RESUMO)

print("\nCheckpoint:")
print(ARQUIVO_CHECKPOINT)
print(ARQUIVO_CHECKPOINT_MELHOR)
print(ARQUIVO_CHECKPOINT_TRADES)