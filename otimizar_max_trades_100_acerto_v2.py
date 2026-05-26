import pandas as pd
import numpy as np
import os
import time

# =====================================================
# CONFIGURAÇÕES - V2
# =====================================================

ARQUIVO_SCORE = r"saida_ml_entradas_video_v2\06_v2_score_todos_candles.csv"

PASTA_SAIDA = "saida_ml_entradas_video_v2_otimizacao"
os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "13_v2_otimizacao_max_trades_100_acerto.csv.gz")
ARQUIVO_TOP_100 = os.path.join(PASTA_SAIDA, "14_v2_top_configuracoes_100_acerto.csv.gz")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "15_v2_melhor_trades_max_100_acerto.csv.gz")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_SAIDA, "16_v2_melhor_resumo_max_100_acerto.csv")
ARQUIVO_RESUMO_MINIMOS = os.path.join(PASTA_SAIDA, "17_v2_resumo_por_minimo_trades.csv")

# Checkpoint V2 compactado
ARQUIVO_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoint_v2_otimizacao_max_trades.csv.gz")
ARQUIVO_CHECKPOINT_TRADES = os.path.join(PASTA_SAIDA, "checkpoint_v2_melhor_trades_100.csv.gz")
ARQUIVO_CHECKPOINT_RESUMO = os.path.join(PASTA_SAIDA, "checkpoint_v2_melhor_resumo_100.csv")

SALVAR_A_CADA_RESULTADOS = 500

# Take e Stop
TAKE_PONTOS = 25.5
STOP_PONTOS = 225.0

# Base 2 minutos:
# 720 candles = 24 horas
MAX_CANDLES_FUTURO = 720

# Entrada:
# "close_signal" = fechamento do candle do sinal
# "next_open"    = abertura do próximo candle
MODO_ENTRADA = "close_signal"

# Apenas uma operação por dia
APENAS_1_TRADE_POR_DIA = True

# Quando houver vários sinais no mesmo dia:
# "maior_score" = escolhe o maior score do dia
# "primeiro"    = escolhe o primeiro sinal do dia
MODO_ESCOLHA_DIA = "maior_score"

# Usar diferença mínima entre score da direção e score oposto
USAR_DIFERENCA_MINIMA = True


# =====================================================
# FUNÇÕES DE SALVAMENTO SEGURO
# =====================================================

def salvar_csv_seguro(df, caminho, compactado=False):
    """
    Salva CSV usando arquivo temporário.
    Isso evita corromper o arquivo principal se faltar energia/espaço no meio.
    """

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


def salvar_checkpoint(resultados, melhor_resumo_100, melhor_trades_100):
    """
    Salva checkpoint V2 de forma compactada.
    """

    if resultados:
        df_resultados = pd.DataFrame(resultados)
        salvar_csv_seguro(
            df_resultados,
            ARQUIVO_CHECKPOINT,
            compactado=True
        )

    if melhor_resumo_100 is not None:
        df_resumo = pd.DataFrame([melhor_resumo_100])
        salvar_csv_seguro(
            df_resumo,
            ARQUIVO_CHECKPOINT_RESUMO,
            compactado=False
        )

    if melhor_trades_100 is not None and not melhor_trades_100.empty:
        salvar_csv_seguro(
            melhor_trades_100,
            ARQUIVO_CHECKPOINT_TRADES,
            compactado=True
        )

    print(f"CHECKPOINT V2 COMPACTADO SALVO: {len(resultados)} resultados.")


# =====================================================
# LIMPAR ARQUIVOS TEMPORÁRIOS ANTIGOS
# =====================================================

for nome in os.listdir(PASTA_SAIDA):
    if nome.endswith(".tmp"):
        caminho_tmp = os.path.join(PASTA_SAIDA, nome)
        try:
            os.remove(caminho_tmp)
            print("Arquivo temporário removido:", caminho_tmp)
        except Exception as e:
            print("Não conseguiu remover temporário:", caminho_tmp, e)


# =====================================================
# CARREGAR BASE V2
# =====================================================

print("Carregando score V2...")

df = pd.read_csv(ARQUIVO_SCORE)

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"])
df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

df = df.sort_values("DataHora_SP").reset_index(drop=True)

colunas_numericas = [
    "open", "high", "low", "close", "volume",
    "score_BUY", "score_SELL", "score_NONE"
]

for col in colunas_numericas:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
df["Data"] = df["DataHora_SP"].dt.date

print("Linhas carregadas:", len(df))
print("Início:", df["DataHora_SP"].min())
print("Fim:", df["DataHora_SP"].max())


# =====================================================
# SIMULAR TAKE/STOP
# =====================================================

def simular_trade(df_base, indice_sinal, direcao):
    if MODO_ENTRADA == "next_open":
        indice_entrada = indice_sinal + 1

        if indice_entrada >= len(df_base):
            return None

        preco_entrada = df_base.loc[indice_entrada, "open"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]

    else:
        indice_entrada = indice_sinal
        preco_entrada = df_base.loc[indice_entrada, "close"]
        dt_entrada = df_base.loc[indice_entrada, "DataHora_SP"]

    if pd.isna(preco_entrada):
        return None

    if direcao == "BUY":
        preco_take = preco_entrada + TAKE_PONTOS
        preco_stop = preco_entrada - STOP_PONTOS
    else:
        preco_take = preco_entrada - TAKE_PONTOS
        preco_stop = preco_entrada + STOP_PONTOS

    fim = min(indice_entrada + MAX_CANDLES_FUTURO, len(df_base) - 1)

    maior_runup = 0.0
    maior_drawdown = 0.0

    for j in range(indice_entrada + 1, fim + 1):
        high = df_base.loc[j, "high"]
        low = df_base.loc[j, "low"]
        dt_saida = df_base.loc[j, "DataHora_SP"]

        if pd.isna(high) or pd.isna(low):
            continue

        if direcao == "BUY":
            runup_atual = high - preco_entrada
            drawdown_atual = preco_entrada - low

            maior_runup = max(maior_runup, runup_atual)
            maior_drawdown = max(maior_drawdown, drawdown_atual)

            bateu_take = high >= preco_take
            bateu_stop = low <= preco_stop

            # Conservador: se bater take e stop no mesmo candle, considera stop primeiro
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

        else:
            runup_atual = preco_entrada - low
            drawdown_atual = high - preco_entrada

            maior_runup = max(maior_runup, runup_atual)
            maior_drawdown = max(maior_drawdown, drawdown_atual)

            bateu_take = low <= preco_take
            bateu_stop = high >= preco_stop

            # Conservador: se bater take e stop no mesmo candle, considera stop primeiro
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

    return {
        "resultado": "ABERTO",
        "pontos": 0.0,
        "preco_entrada": preco_entrada,
        "preco_saida": np.nan,
        "dt_entrada": dt_entrada,
        "dt_saida": pd.NaT,
        "candles_ate_saida": np.nan,
        "minutos_ate_saida": np.nan,
        "runup": maior_runup,
        "drawdown": maior_drawdown
    }


# =====================================================
# GERAR CANDIDATOS
# =====================================================

def gerar_candidatos(
    df_base,
    score_buy_min,
    score_sell_min,
    hora_inicio,
    hora_fim,
    diferenca_minima
):
    base = df_base.copy()

    cond_horario = (
        (base["Hora_SP_Decimal"] >= hora_inicio) &
        (base["Hora_SP_Decimal"] <= hora_fim)
    )

    if USAR_DIFERENCA_MINIMA:
        cond_buy = (
            cond_horario &
            (base["score_BUY"] >= score_buy_min) &
            (base["score_BUY"] > base["score_SELL"]) &
            ((base["score_BUY"] - base["score_SELL"]) >= diferenca_minima)
        )

        cond_sell = (
            cond_horario &
            (base["score_SELL"] >= score_sell_min) &
            (base["score_SELL"] > base["score_BUY"]) &
            ((base["score_SELL"] - base["score_BUY"]) >= diferenca_minima)
        )
    else:
        cond_buy = (
            cond_horario &
            (base["score_BUY"] >= score_buy_min) &
            (base["score_BUY"] > base["score_SELL"])
        )

        cond_sell = (
            cond_horario &
            (base["score_SELL"] >= score_sell_min) &
            (base["score_SELL"] > base["score_BUY"])
        )

    base["Direcao_Candidata"] = "NONE"
    base.loc[cond_buy, "Direcao_Candidata"] = "BUY"
    base.loc[cond_sell, "Direcao_Candidata"] = "SELL"

    candidatos = base[base["Direcao_Candidata"] != "NONE"].copy()

    if candidatos.empty:
        return candidatos

    candidatos["score_direcao"] = np.where(
        candidatos["Direcao_Candidata"] == "BUY",
        candidatos["score_BUY"],
        candidatos["score_SELL"]
    )

    candidatos["score_oposto"] = np.where(
        candidatos["Direcao_Candidata"] == "BUY",
        candidatos["score_SELL"],
        candidatos["score_BUY"]
    )

    candidatos["score_diff"] = candidatos["score_direcao"] - candidatos["score_oposto"]

    return candidatos


# =====================================================
# ESCOLHER 1 TRADE POR DIA
# =====================================================

def escolher_um_por_dia(candidatos):
    if candidatos.empty:
        return candidatos

    escolhidos = []

    for data, grupo in candidatos.groupby("Data"):
        grupo = grupo.copy()

        if MODO_ESCOLHA_DIA == "primeiro":
            escolhido = grupo.sort_values("DataHora_SP").iloc[0]
        else:
            escolhido = grupo.sort_values(
                by=["score_direcao", "score_diff", "DataHora_SP"],
                ascending=[False, False, True]
            ).iloc[0]

        escolhidos.append(escolhido)

    return pd.DataFrame(escolhidos).sort_values("DataHora_SP").reset_index(drop=True)


# =====================================================
# TESTAR CONFIGURAÇÃO
# =====================================================

def testar_configuracao(
    df_base,
    score_buy_min,
    score_sell_min,
    hora_inicio,
    hora_fim,
    diferenca_minima
):
    candidatos = gerar_candidatos(
        df_base=df_base,
        score_buy_min=score_buy_min,
        score_sell_min=score_sell_min,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        diferenca_minima=diferenca_minima
    )

    if candidatos.empty:
        return None, pd.DataFrame()

    if APENAS_1_TRADE_POR_DIA:
        candidatos = escolher_um_por_dia(candidatos)

    trades = []

    for _, row in candidatos.iterrows():
        idx_base = df_base.index[df_base["DataHora_SP"] == row["DataHora_SP"]]

        if len(idx_base) == 0:
            continue

        indice_sinal = int(idx_base[0])
        direcao = row["Direcao_Candidata"]

        trade = simular_trade(df_base, indice_sinal, direcao)

        if trade is None:
            continue

        trades.append({
            "indice_sinal": indice_sinal,
            "DataHora_Sinal_SP": row["DataHora_SP"],
            "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
            "Data": row["Data"],
            "Hora_SP": row["DataHora_SP"].time(),
            "Direcao": direcao,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "score_BUY": row["score_BUY"],
            "score_SELL": row["score_SELL"],
            "score_NONE": row["score_NONE"],
            "score_direcao": row["score_direcao"],
            "score_oposto": row["score_oposto"],
            "score_diff": row["score_diff"],
            "resultado": trade["resultado"],
            "pontos": trade["pontos"],
            "preco_entrada": trade["preco_entrada"],
            "preco_saida": trade["preco_saida"],
            "dt_entrada": trade["dt_entrada"],
            "dt_saida": trade["dt_saida"],
            "candles_ate_saida": trade["candles_ate_saida"],
            "minutos_ate_saida": trade["minutos_ate_saida"],
            "runup": trade["runup"],
            "drawdown": trade["drawdown"],
            "contrato": row.get("contrato", ""),
            "localSymbol": row.get("localSymbol", "")
        })

    trades_df = pd.DataFrame(trades)

    if trades_df.empty:
        return None, trades_df

    fechados = trades_df[trades_df["resultado"].isin(["WIN", "LOSS"])].copy()

    if fechados.empty:
        return None, trades_df

    wins = (fechados["resultado"] == "WIN").sum()
    losses = (fechados["resultado"] == "LOSS").sum()
    total = len(fechados)

    winrate = wins / total * 100
    lucro_pontos = fechados["pontos"].sum()

    buy_total = (fechados["Direcao"] == "BUY").sum()
    sell_total = (fechados["Direcao"] == "SELL").sum()

    buy_wins = ((fechados["Direcao"] == "BUY") & (fechados["resultado"] == "WIN")).sum()
    sell_wins = ((fechados["Direcao"] == "SELL") & (fechados["resultado"] == "WIN")).sum()

    buy_winrate = buy_wins / buy_total * 100 if buy_total > 0 else np.nan
    sell_winrate = sell_wins / sell_total * 100 if sell_total > 0 else np.nan

    resumo = {
        "score_buy_min": score_buy_min,
        "score_sell_min": score_sell_min,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "diferenca_minima": diferenca_minima,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro_pontos,
        "buy_total": buy_total,
        "sell_total": sell_total,
        "buy_winrate": buy_winrate,
        "sell_winrate": sell_winrate,
        "media_score": fechados["score_direcao"].mean(),
        "min_score": fechados["score_direcao"].min(),
        "max_score": fechados["score_direcao"].max(),
        "media_score_diff": fechados["score_diff"].mean(),
        "min_score_diff": fechados["score_diff"].min(),
        "max_score_diff": fechados["score_diff"].max(),
        "media_candles_saida": fechados["candles_ate_saida"].mean(),
        "max_candles_saida": fechados["candles_ate_saida"].max(),
        "media_minutos_saida": fechados["minutos_ate_saida"].mean(),
        "max_minutos_saida": fechados["minutos_ate_saida"].max(),
        "drawdown_medio_trade": fechados["drawdown"].mean(),
        "drawdown_max_trade": fechados["drawdown"].max(),
        "runup_medio_trade": fechados["runup"].mean(),
        "runup_max_trade": fechados["runup"].max()
    }

    return resumo, trades_df


# =====================================================
# LISTAS DE OTIMIZAÇÃO V2
# =====================================================

score_buy_lista = [
    0.50, 0.52, 0.54, 0.56, 0.58,
    0.60, 0.62, 0.64, 0.66, 0.68,
    0.70, 0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90,
    0.92, 0.94, 0.96
]

score_sell_lista = [
    0.50, 0.52, 0.54, 0.56, 0.58,
    0.60, 0.62, 0.64, 0.66, 0.68,
    0.70, 0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90,
    0.92, 0.94, 0.96
]

diferencas = [
    0.00, 0.02, 0.04, 0.06, 0.08,
    0.10, 0.12, 0.15, 0.18, 0.20
]

horarios = [
    (3.50, 4.10),
    (3.60, 4.00),
    (3.70, 3.95),
    (3.75, 3.90),
    (3.80, 3.90),

    (0.00, 6.00),
    (1.00, 6.00),
    (2.00, 6.00),
    (3.00, 6.00),
    (3.00, 7.00),
    (3.00, 8.00),
    (4.00, 8.00),
    (5.00, 9.00),

    (6.00, 10.00),
    (7.00, 11.00),
    (8.00, 12.00),
    (8.00, 13.00),
    (9.00, 14.00),

    (10.00, 15.00),
    (11.00, 16.00),
    (12.00, 17.00),

    (0.00, 12.00),
    (2.00, 12.00),
    (3.00, 12.00),
    (0.00, 17.00),
    (3.00, 17.00)
]


# =====================================================
# CARREGAR CHECKPOINT SE EXISTIR
# =====================================================

if os.path.exists(ARQUIVO_CHECKPOINT):
    print("\nCheckpoint V2 compactado encontrado. Continuando de onde parou...")

    checkpoint_df = carregar_csv(ARQUIVO_CHECKPOINT, compactado=True)
    resultados = checkpoint_df.to_dict("records")

    configs_ja_testadas = set(
        zip(
            checkpoint_df["score_buy_min"].round(6),
            checkpoint_df["score_sell_min"].round(6),
            checkpoint_df["hora_inicio"].round(6),
            checkpoint_df["hora_fim"].round(6),
            checkpoint_df["diferenca_minima"].round(6)
        )
    )

    print("Resultados carregados do checkpoint:", len(resultados))
    print("Configurações já testadas:", len(configs_ja_testadas))

else:
    print("\nNenhum checkpoint V2 compactado encontrado. Iniciando do zero...")
    resultados = []
    configs_ja_testadas = set()


# Melhor 100% salvo no checkpoint, se existir
melhor_resumo_100 = None
melhor_trades_100 = None

if os.path.exists(ARQUIVO_CHECKPOINT_RESUMO):
    resumo_cp = carregar_csv(ARQUIVO_CHECKPOINT_RESUMO, compactado=False)

    if not resumo_cp.empty:
        melhor_resumo_100 = resumo_cp.iloc[0].to_dict()
        print("Melhor resumo 100% V2 carregado do checkpoint.")

if os.path.exists(ARQUIVO_CHECKPOINT_TRADES):
    melhor_trades_100 = carregar_csv(ARQUIVO_CHECKPOINT_TRADES, compactado=True)

    if not melhor_trades_100.empty:
        print("Melhores trades 100% V2 carregados do checkpoint.")


# =====================================================
# SE TIVER RESULTADOS, RECALCULAR MELHOR 100%
# =====================================================

if resultados and melhor_resumo_100 is None:
    temp_df = pd.DataFrame(resultados)
    temp_100 = temp_df[temp_df["winrate"] == 100.0].copy()

    if not temp_100.empty:
        temp_100 = temp_100.sort_values(
            by=["total_trades", "lucro_pontos", "media_score"],
            ascending=[False, False, False]
        )

        melhor_resumo_100 = temp_100.iloc[0].to_dict()


# =====================================================
# OTIMIZAÇÃO COM CHECKPOINT V2
# =====================================================

print("\nIniciando otimização V2 com checkpoint compactado...")

total_configuracoes = (
    len(score_buy_lista) *
    len(score_sell_lista) *
    len(diferencas) *
    len(horarios)
)

print("Total de configurações previstas:", total_configuracoes)
print("Configurações já testadas:", len(configs_ja_testadas))
print("Restantes aproximadas:", total_configuracoes - len(configs_ja_testadas))

contador_loop = 0
novos_resultados_desde_checkpoint = 0
inicio_tempo = time.time()

try:
    for score_buy in score_buy_lista:
        for score_sell in score_sell_lista:
            for diferenca_minima in diferencas:
                for hora_inicio, hora_fim in horarios:

                    contador_loop += 1

                    chave_config = (
                        round(score_buy, 6),
                        round(score_sell, 6),
                        round(hora_inicio, 6),
                        round(hora_fim, 6),
                        round(diferenca_minima, 6)
                    )

                    if chave_config in configs_ja_testadas:
                        continue

                    if contador_loop % 500 == 0:
                        tempo_passado = time.time() - inicio_tempo
                        print(
                            f"Loop {contador_loop}/{total_configuracoes} | "
                            f"Resultados: {len(resultados)} | "
                            f"Restantes: {total_configuracoes - len(configs_ja_testadas)} | "
                            f"Tempo: {tempo_passado / 60:.1f} min"
                        )

                    resumo, trades = testar_configuracao(
                        df_base=df,
                        score_buy_min=score_buy,
                        score_sell_min=score_sell,
                        hora_inicio=hora_inicio,
                        hora_fim=hora_fim,
                        diferenca_minima=diferenca_minima
                    )

                    configs_ja_testadas.add(chave_config)

                    if resumo is None:
                        continue

                    resultados.append(resumo)
                    novos_resultados_desde_checkpoint += 1

                    # Atualizar melhor configuração 100%
                    if resumo["winrate"] == 100.0:
                        if melhor_resumo_100 is None:
                            melhor_resumo_100 = resumo
                            melhor_trades_100 = trades

                            print("\nPRIMEIRO MELHOR 100% V2 ENCONTRADO:")
                            print(pd.Series(melhor_resumo_100))

                        else:
                            chave_atual = (
                                resumo["total_trades"],
                                resumo["lucro_pontos"],
                                resumo["media_score"]
                            )

                            chave_melhor = (
                                melhor_resumo_100["total_trades"],
                                melhor_resumo_100["lucro_pontos"],
                                melhor_resumo_100["media_score"]
                            )

                            if chave_atual > chave_melhor:
                                melhor_resumo_100 = resumo
                                melhor_trades_100 = trades

                                print("\nNOVO MELHOR 100% V2 ENCONTRADO:")
                                print(pd.Series(melhor_resumo_100))

                    # Salvar checkpoint
                    if novos_resultados_desde_checkpoint >= SALVAR_A_CADA_RESULTADOS:
                        salvar_checkpoint(resultados, melhor_resumo_100, melhor_trades_100)
                        novos_resultados_desde_checkpoint = 0

except KeyboardInterrupt:
    print("\nExecução V2 interrompida pelo usuário.")
    print("Salvando checkpoint V2 antes de sair...")
    salvar_checkpoint(resultados, melhor_resumo_100, melhor_trades_100)
    raise SystemExit

except Exception as e:
    print("\nERRO DURANTE EXECUÇÃO V2:")
    print(e)
    print("Salvando checkpoint V2 antes de sair...")
    salvar_checkpoint(resultados, melhor_resumo_100, melhor_trades_100)
    raise

# Salva checkpoint final
salvar_checkpoint(resultados, melhor_resumo_100, melhor_trades_100)


# =====================================================
# GERAR RESULTADOS FINAIS
# =====================================================

print("\nGerando arquivos finais V2...")

resultados_df = pd.DataFrame(resultados)

if resultados_df.empty:
    print("Nenhum resultado V2 gerado.")
    raise SystemExit

resultados_df = resultados_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

salvar_csv_seguro(resultados_df, ARQUIVO_RESULTADOS, compactado=True)

cem_porcento = resultados_df[resultados_df["winrate"] == 100.0].copy()

if not cem_porcento.empty:
    cem_porcento = cem_porcento.sort_values(
        by=["total_trades", "lucro_pontos", "media_score"],
        ascending=[False, False, False]
    )

salvar_csv_seguro(cem_porcento, ARQUIVO_TOP_100, compactado=True)


# =====================================================
# RESUMO POR MÍNIMO DE TRADES
# =====================================================

print("\n=====================================================")
print("MELHORES RESULTADOS V2 POR MÍNIMO DE TRADES")
print("=====================================================")

minimos = [50, 75, 100, 125, 150, 180, 200, 220, 240]

linhas_minimos = []

for minimo in minimos:
    filtro = resultados_df[resultados_df["total_trades"] >= minimo].copy()

    if filtro.empty:
        print(f"\nMínimo {minimo} trades: nenhum resultado.")
        continue

    melhor = filtro.sort_values(
        by=["winrate", "total_trades", "lucro_pontos"],
        ascending=[False, False, False]
    ).iloc[0]

    linhas_minimos.append(melhor)

    print(f"\nMínimo {minimo} trades:")
    print(melhor[[
        "winrate",
        "total_trades",
        "wins",
        "losses",
        "lucro_pontos",
        "score_buy_min",
        "score_sell_min",
        "hora_inicio",
        "hora_fim",
        "diferenca_minima",
        "buy_total",
        "sell_total",
        "drawdown_max_trade",
        "max_minutos_saida"
    ]])

resumo_minimos = pd.DataFrame(linhas_minimos)
salvar_csv_seguro(resumo_minimos, ARQUIVO_RESUMO_MINIMOS, compactado=False)


# =====================================================
# SALVAR MELHOR 100%
# =====================================================

print("\n=====================================================")
print("MELHOR CONFIGURAÇÃO V2 COM 100%")
print("=====================================================")

if melhor_resumo_100 is not None:
    melhor_resumo_df = pd.DataFrame([melhor_resumo_100])
    salvar_csv_seguro(melhor_resumo_df, ARQUIVO_MELHOR_RESUMO, compactado=False)

    if melhor_trades_100 is not None and not melhor_trades_100.empty:
        salvar_csv_seguro(melhor_trades_100, ARQUIVO_MELHOR_TRADES, compactado=True)

    print(pd.Series(melhor_resumo_100))

    if melhor_trades_100 is not None and not melhor_trades_100.empty:
        fechados_100 = melhor_trades_100[
            melhor_trades_100["resultado"].isin(["WIN", "LOSS"])
        ].copy()

        print("\nDistribuição por direção:")
        print(fechados_100["Direcao"].value_counts())

        print("\nDistribuição por horário:")
        print(fechados_100["Hora_SP"].astype(str).str.slice(0, 5).value_counts().head(30))

else:
    print("Nenhuma configuração V2 com 100% encontrada.")


# =====================================================
# TOP 30
# =====================================================

print("\n=====================================================")
print("TOP 30 GERAL V2")
print("=====================================================")
print(resultados_df.head(30))

print("\n=====================================================")
print("TOP 30 V2 COM 100% ORDENADO POR MAIS TRADES")
print("=====================================================")

if cem_porcento.empty:
    print("Nenhuma configuração V2 com 100%.")
else:
    print(cem_porcento.head(30))


# =====================================================
# ARQUIVOS GERADOS
# =====================================================

print("\n=====================================================")
print("ARQUIVOS GERADOS V2")
print("=====================================================")
print("Checkpoint:")
print(ARQUIVO_CHECKPOINT)
print(ARQUIVO_CHECKPOINT_RESUMO)
print(ARQUIVO_CHECKPOINT_TRADES)

print("\nFinais:")
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_TOP_100)
print(ARQUIVO_MELHOR_TRADES)
print(ARQUIVO_MELHOR_RESUMO)
print(ARQUIVO_RESUMO_MINIMOS)