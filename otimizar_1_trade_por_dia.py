import pandas as pd
import numpy as np
import os

# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_SCORE = r"saida_ml_entradas_video\06_score_todos_candles.csv"

PASTA_SAIDA = "saida_ml_entradas_video"
os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "08_otimizacao_1_trade_por_dia.csv")
ARQUIVO_MELHORES_TRADES = os.path.join(PASTA_SAIDA, "09_melhores_trades_1_trade_por_dia.csv")
ARQUIVO_MELHOR_SINAIS = os.path.join(PASTA_SAIDA, "10_melhor_sinais_1_trade_por_dia.csv")

# Take e Stop do operacional
TAKE_PONTOS = 25.5
STOP_PONTOS = 225.0

# Como sua base é 2 minutos:
# 720 candles = 24 horas
MAX_CANDLES_FUTURO = 720

# Entrada no fechamento do candle do sinal
MODO_ENTRADA = "close_signal"  # "close_signal" ou "next_open"

# Apenas 1 operação por dia
APENAS_1_TRADE_POR_DIA = True

# Quando houver vários sinais no mesmo dia:
# "maior_score" = pega o sinal com maior score da direção
# "primeiro" = pega o primeiro sinal do dia
MODO_ESCOLHA_DIA = "maior_score"

# =====================================================
# CARREGAR DADOS
# =====================================================

print("Carregando score...")

df = pd.read_csv(ARQUIVO_SCORE)

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"])
df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

df = df.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume", "score_BUY", "score_SELL", "score_NONE"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
df["Data"] = df["DataHora_SP"].dt.date

print("Linhas carregadas:", len(df))
print("Início:", df["DataHora_SP"].min())
print("Fim:", df["DataHora_SP"].max())


# =====================================================
# FUNÇÃO PARA SIMULAR TAKE/STOP
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

    for j in range(indice_entrada + 1, fim + 1):
        high = df_base.loc[j, "high"]
        low = df_base.loc[j, "low"]
        dt_saida = df_base.loc[j, "DataHora_SP"]

        if pd.isna(high) or pd.isna(low):
            continue

        if direcao == "BUY":
            bateu_take = high >= preco_take
            bateu_stop = low <= preco_stop

            # Conservador: se take e stop baterem no mesmo candle, considera stop primeiro
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

        else:
            bateu_take = low <= preco_take
            bateu_stop = high >= preco_stop

            # Conservador: se take e stop baterem no mesmo candle, considera stop primeiro
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -STOP_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": TAKE_PONTOS,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "candles_ate_saida": j - indice_entrada
                }

    return {
        "resultado": "ABERTO",
        "pontos": 0.0,
        "preco_entrada": preco_entrada,
        "preco_saida": np.nan,
        "dt_entrada": dt_entrada,
        "dt_saida": pd.NaT,
        "candles_ate_saida": np.nan
    }


# =====================================================
# GERAR CANDIDATOS
# =====================================================

def gerar_candidatos(df_base, score_buy_min, score_sell_min, hora_inicio, hora_fim):
    base = df_base.copy()

    cond_horario = (
        (base["Hora_SP_Decimal"] >= hora_inicio) &
        (base["Hora_SP_Decimal"] <= hora_fim)
    )

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
                by=["score_direcao", "DataHora_SP"],
                ascending=[False, True]
            ).iloc[0]

        escolhidos.append(escolhido)

    return pd.DataFrame(escolhidos).sort_values("DataHora_SP").reset_index(drop=True)


# =====================================================
# TESTAR CONFIGURAÇÃO
# =====================================================

def testar_configuracao(df_base, score_buy_min, score_sell_min, hora_inicio, hora_fim):
    candidatos = gerar_candidatos(
        df_base=df_base,
        score_buy_min=score_buy_min,
        score_sell_min=score_sell_min,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim
    )

    if candidatos.empty:
        return None, pd.DataFrame()

    if APENAS_1_TRADE_POR_DIA:
        candidatos = escolher_um_por_dia(candidatos)

    sinais = []

    for _, row in candidatos.iterrows():
        indice_sinal = int(row.name)

        # Como o índice pode ter sido resetado no DataFrame de candidatos,
        # localizamos pelo DataHora_SP na base original
        idx_base = df_base.index[df_base["DataHora_SP"] == row["DataHora_SP"]]

        if len(idx_base) == 0:
            continue

        i = int(idx_base[0])

        direcao = row["Direcao_Candidata"]

        trade = simular_trade(df_base, i, direcao)

        if trade is None:
            continue

        sinais.append({
            "indice_sinal": i,
            "DataHora_Sinal_SP": row["DataHora_SP"],
            "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
            "Data": row["Data"],
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
            "resultado": trade["resultado"],
            "pontos": trade["pontos"],
            "preco_entrada": trade["preco_entrada"],
            "preco_saida": trade["preco_saida"],
            "dt_entrada": trade["dt_entrada"],
            "dt_saida": trade["dt_saida"],
            "candles_ate_saida": trade["candles_ate_saida"],
            "contrato": row.get("contrato", ""),
            "localSymbol": row.get("localSymbol", "")
        })

    trades = pd.DataFrame(sinais)

    if trades.empty:
        return None, trades

    fechados = trades[trades["resultado"].isin(["WIN", "LOSS"])].copy()

    if fechados.empty:
        return None, trades

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
        "media_candles_saida": fechados["candles_ate_saida"].mean(),
        "max_candles_saida": fechados["candles_ate_saida"].max()
    }

    return resumo, trades


# =====================================================
# GRID DE OTIMIZAÇÃO
# =====================================================

print("Iniciando otimização com 1 trade por dia...")

score_buy_lista = [
    0.70, 0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90,
    0.92, 0.94, 0.96
]

score_sell_lista = [
    0.70, 0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90,
    0.92, 0.94, 0.96
]

# Horários focados em 03:48 e também janelas maiores para comparação
horarios = [
    # Janelas bem focadas em 03:48
    (3.50, 4.10),   # 03:30 até 04:06
    (3.60, 4.00),   # 03:36 até 04:00
    (3.70, 3.95),   # 03:42 até 03:57
    (3.75, 3.90),   # 03:45 até 03:54
    (3.80, 3.90),   # 03:48 até 03:54

    # Janelas ao redor da madrugada
    (3.00, 5.00),
    (3.00, 6.00),
    (3.50, 5.50),
    (4.00, 6.00),

    # Janelas da manhã
    (6.00, 9.00),
    (7.00, 10.00),
    (8.00, 11.00),
    (8.00, 12.00),

    # Janelas amplas para comparar
    (0.00, 12.00),
    (2.00, 12.00),
    (3.00, 12.00),
]

resultados = []
melhor_trades = None
melhor_resumo = None

contador = 0

for score_buy in score_buy_lista:
    for score_sell in score_sell_lista:
        for hora_inicio, hora_fim in horarios:
            contador += 1

            resumo, trades = testar_configuracao(
                df_base=df,
                score_buy_min=score_buy,
                score_sell_min=score_sell,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim
            )

            if resumo is None:
                continue

            resultados.append(resumo)

            # Melhor critério:
            # 1. maior winrate
            # 2. mais trades
            # 3. maior lucro em pontos
            atual_chave = (
                resumo["winrate"],
                resumo["total_trades"],
                resumo["lucro_pontos"]
            )

            if melhor_resumo is None:
                melhor_resumo = resumo
                melhor_trades = trades
            else:
                melhor_chave = (
                    melhor_resumo["winrate"],
                    melhor_resumo["total_trades"],
                    melhor_resumo["lucro_pontos"]
                )

                if atual_chave > melhor_chave:
                    melhor_resumo = resumo
                    melhor_trades = trades

print("Configurações testadas:", contador)

resultados_df = pd.DataFrame(resultados)

if resultados_df.empty:
    print("Nenhum resultado gerado.")
    raise SystemExit

resultados_df = resultados_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

resultados_df.to_csv(ARQUIVO_RESULTADOS, index=False, encoding="utf-8-sig")

print("\n=====================================================")
print("TOP 30 CONFIGURAÇÕES")
print("=====================================================")
print(resultados_df.head(30))

cem_porcento = resultados_df[resultados_df["winrate"] == 100.0].copy()

print("\n=====================================================")
print("CONFIGURAÇÕES COM 100%")
print("=====================================================")

if cem_porcento.empty:
    print("Nenhuma configuração com 100% encontrada nesse grid.")
    print("\nMelhor configuração encontrada:")
    print(resultados_df.iloc[0])
else:
    print("Quantidade de configurações com 100%:", len(cem_porcento))
    print(cem_porcento.head(30))

if melhor_trades is not None and not melhor_trades.empty:
    melhor_trades.to_csv(ARQUIVO_MELHORES_TRADES, index=False, encoding="utf-8-sig")

    print("\n=====================================================")
    print("MELHOR CONFIGURAÇÃO")
    print("=====================================================")
    print(pd.Series(melhor_resumo))

    colunas_sinais = [
        "DataHora_Sinal_SP",
        "DataHora_Chicago",
        "Data",
        "Direcao",
        "preco_entrada",
        "preco_saida",
        "resultado",
        "pontos",
        "dt_entrada",
        "dt_saida",
        "candles_ate_saida",
        "score_BUY",
        "score_SELL",
        "score_direcao",
        "contrato",
        "localSymbol"
    ]

    melhor_trades[colunas_sinais].to_csv(
        ARQUIVO_MELHOR_SINAIS,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nTrades da melhor configuração salvos em:")
    print(ARQUIVO_MELHORES_TRADES)

    print("Sinais da melhor configuração salvos em:")
    print(ARQUIVO_MELHOR_SINAIS)

print("\nArquivos gerados:")
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_MELHORES_TRADES)
print(ARQUIVO_MELHOR_SINAIS)