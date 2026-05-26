import pandas as pd
import numpy as np
import os

# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_SCORE = r"saida_ml_entradas_video\06_score_todos_candles.csv"

PASTA_SAIDA = "saida_ml_entradas_video"
os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "13_otimizacao_max_trades_100_acerto.csv")
ARQUIVO_TOP_100 = os.path.join(PASTA_SAIDA, "14_top_configuracoes_100_acerto.csv")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "15_melhor_trades_max_100_acerto.csv")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_SAIDA, "16_melhor_resumo_max_100_acerto.csv")

# Take e Stop do operacional
TAKE_PONTOS = 25.5
STOP_PONTOS = 225.0

# Como sua base é 2 minutos:
# 720 candles = 24 horas
MAX_CANDLES_FUTURO = 720

# Entrada no fechamento do candle de sinal
# Alternativas:
# "close_signal" = entra no fechamento do candle do sinal
# "next_open"    = entra na abertura do próximo candle
MODO_ENTRADA = "close_signal"

# Apenas uma operação por dia
APENAS_1_TRADE_POR_DIA = True

# Quando houver vários sinais no mesmo dia:
# "maior_score" = escolhe o sinal com maior score da direção no dia
# "primeiro"    = escolhe o primeiro sinal do dia
MODO_ESCOLHA_DIA = "maior_score"

# Exigir que o sinal BUY/SELL tenha diferença mínima entre scores?
# Exemplo: score_buy 0.80 e score_sell 0.75, diferença = 0.05
USAR_DIFERENCA_MINIMA = True

# =====================================================
# CARREGAR BASE
# =====================================================

print("Carregando score...")

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
    """
    Simula uma operação com:
    Take = 25,5 pontos
    Stop = 225 pontos

    BUY:
        take = entrada + 25.5
        stop = entrada - 225

    SELL:
        take = entrada - 25.5
        stop = entrada + 225
    """

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

            # Conservador:
            # Se take e stop baterem no mesmo candle, considera stop primeiro.
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

            # Conservador:
            # Se take e stop baterem no mesmo candle, considera stop primeiro.
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
            # Prioriza:
            # 1. maior score da direção
            # 2. maior diferença entre score da direção e score oposto
            # 3. mais cedo no dia
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
# GRID DE OTIMIZAÇÃO
# =====================================================

print("Iniciando otimização para máximo de trades com 100%...")

# Scores mais amplos para tentar aumentar operações
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

# Diferença mínima entre score da direção e score oposto
diferencas = [
    0.00, 0.02, 0.04, 0.06, 0.08,
    0.10, 0.12, 0.15, 0.18, 0.20
]

# Janelas de horário
# Inclui:
# - faixa das 03:48
# - madrugada
# - manhã
# - janelas amplas
horarios = [
    # Bem focadas perto de 03:48
    (3.50, 4.10),   # 03:30 até 04:06
    (3.60, 4.00),   # 03:36 até 04:00
    (3.70, 3.95),   # 03:42 até 03:57
    (3.75, 3.90),   # 03:45 até 03:54
    (3.80, 3.90),   # 03:48 até 03:54

    # Madrugada
    (0.00, 6.00),
    (1.00, 6.00),
    (2.00, 6.00),
    (3.00, 6.00),
    (3.00, 7.00),
    (3.00, 8.00),
    (4.00, 8.00),
    (5.00, 9.00),

    # Manhã
    (6.00, 10.00),
    (7.00, 11.00),
    (8.00, 12.00),
    (8.00, 13.00),
    (9.00, 14.00),

    # Meio dia / tarde curta
    (10.00, 15.00),
    (11.00, 16.00),
    (12.00, 17.00),

    # Janelas amplas
    (0.00, 12.00),
    (2.00, 12.00),
    (3.00, 12.00),
    (0.00, 17.00),
    (3.00, 17.00)
]

resultados = []
melhor_resumo_100 = None
melhor_trades_100 = None

melhor_resumo_geral = None
melhor_trades_geral = None

contador = 0

total_configuracoes = (
    len(score_buy_lista) *
    len(score_sell_lista) *
    len(diferencas) *
    len(horarios)
)

print("Total de configurações previstas:", total_configuracoes)

for score_buy in score_buy_lista:
    for score_sell in score_sell_lista:
        for diferenca_minima in diferencas:
            for hora_inicio, hora_fim in horarios:
                contador += 1

                if contador % 500 == 0:
                    print(f"Testadas {contador}/{total_configuracoes} configurações...")

                resumo, trades = testar_configuracao(
                    df_base=df,
                    score_buy_min=score_buy,
                    score_sell_min=score_sell,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    diferenca_minima=diferenca_minima
                )

                if resumo is None:
                    continue

                resultados.append(resumo)

                # Melhor geral:
                # 1. maior winrate
                # 2. maior número de trades
                # 3. maior lucro
                chave_geral = (
                    resumo["winrate"],
                    resumo["total_trades"],
                    resumo["lucro_pontos"]
                )

                if melhor_resumo_geral is None:
                    melhor_resumo_geral = resumo
                    melhor_trades_geral = trades
                else:
                    melhor_chave_geral = (
                        melhor_resumo_geral["winrate"],
                        melhor_resumo_geral["total_trades"],
                        melhor_resumo_geral["lucro_pontos"]
                    )

                    if chave_geral > melhor_chave_geral:
                        melhor_resumo_geral = resumo
                        melhor_trades_geral = trades

                # Melhor com 100%:
                # 1. precisa ter winrate 100
                # 2. maior número de trades
                # 3. maior lucro
                if resumo["winrate"] == 100.0:
                    chave_100 = (
                        resumo["total_trades"],
                        resumo["lucro_pontos"],
                        resumo["media_score"]
                    )

                    if melhor_resumo_100 is None:
                        melhor_resumo_100 = resumo
                        melhor_trades_100 = trades
                    else:
                        melhor_chave_100 = (
                            melhor_resumo_100["total_trades"],
                            melhor_resumo_100["lucro_pontos"],
                            melhor_resumo_100["media_score"]
                        )

                        if chave_100 > melhor_chave_100:
                            melhor_resumo_100 = resumo
                            melhor_trades_100 = trades

print("Configurações testadas:", contador)

resultados_df = pd.DataFrame(resultados)

if resultados_df.empty:
    print("Nenhum resultado gerado.")
    raise SystemExit

# Ordena:
# primeiro winrate,
# depois quantidade de trades,
# depois lucro.
resultados_df = resultados_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

resultados_df.to_csv(ARQUIVO_RESULTADOS, index=False, encoding="utf-8-sig")

# Apenas configurações 100%
cem_porcento = resultados_df[resultados_df["winrate"] == 100.0].copy()

if not cem_porcento.empty:
    cem_porcento = cem_porcento.sort_values(
        by=["total_trades", "lucro_pontos", "media_score"],
        ascending=[False, False, False]
    )

    cem_porcento.to_csv(ARQUIVO_TOP_100, index=False, encoding="utf-8-sig")
else:
    pd.DataFrame().to_csv(ARQUIVO_TOP_100, index=False, encoding="utf-8-sig")


# =====================================================
# RESUMO POR MÍNIMO DE TRADES
# =====================================================

print("\n=====================================================")
print("MELHORES RESULTADOS POR MÍNIMO DE TRADES")
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

ARQUIVO_RESUMO_MINIMOS = os.path.join(PASTA_SAIDA, "17_resumo_por_minimo_trades.csv")
resumo_minimos.to_csv(ARQUIVO_RESUMO_MINIMOS, index=False, encoding="utf-8-sig")


# =====================================================
# SALVAR MELHOR CONFIGURAÇÃO 100%
# =====================================================

print("\n=====================================================")
print("MELHOR CONFIGURAÇÃO COM 100%")
print("=====================================================")

if melhor_resumo_100 is not None:
    melhor_resumo_df = pd.DataFrame([melhor_resumo_100])
    melhor_resumo_df.to_csv(ARQUIVO_MELHOR_RESUMO, index=False, encoding="utf-8-sig")

    melhor_trades_100.to_csv(ARQUIVO_MELHOR_TRADES, index=False, encoding="utf-8-sig")

    print(pd.Series(melhor_resumo_100))

    print("\nDistribuição por direção:")
    fechados_100 = melhor_trades_100[melhor_trades_100["resultado"].isin(["WIN", "LOSS"])].copy()
    print(fechados_100["Direcao"].value_counts())

    print("\nDistribuição por horário:")
    print(fechados_100["Hora_SP"].astype(str).str.slice(0, 5).value_counts().head(30))

    print("\nTrades da melhor configuração 100% salvos em:")
    print(ARQUIVO_MELHOR_TRADES)

    print("Resumo da melhor configuração 100% salvo em:")
    print(ARQUIVO_MELHOR_RESUMO)
else:
    print("Nenhuma configuração com 100% encontrada.")
    print("Melhor configuração geral foi:")
    print(pd.Series(melhor_resumo_geral))

    if melhor_trades_geral is not None:
        melhor_trades_geral.to_csv(ARQUIVO_MELHOR_TRADES, index=False, encoding="utf-8-sig")
        pd.DataFrame([melhor_resumo_geral]).to_csv(ARQUIVO_MELHOR_RESUMO, index=False, encoding="utf-8-sig")


# =====================================================
# TOP 30 GERAL E TOP 30 100%
# =====================================================

print("\n=====================================================")
print("TOP 30 GERAL")
print("=====================================================")
print(resultados_df.head(30))

print("\n=====================================================")
print("TOP 30 COM 100% ORDENADO POR MAIS TRADES")
print("=====================================================")

if cem_porcento.empty:
    print("Nenhuma configuração com 100%.")
else:
    print(cem_porcento.head(30))


# =====================================================
# ARQUIVOS GERADOS
# =====================================================

print("\n=====================================================")
print("ARQUIVOS GERADOS")
print("=====================================================")
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_TOP_100)
print(ARQUIVO_MELHOR_TRADES)
print(ARQUIVO_MELHOR_RESUMO)
print(ARQUIVO_RESUMO_MINIMOS)