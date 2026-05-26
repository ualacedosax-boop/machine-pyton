import pandas as pd
import numpy as np
import os
import time
import shutil
from datetime import datetime

# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_SCORE = r"saida_ml_entradas_video\06_score_todos_candles.csv"

PASTA_SAIDA = "saida_ml_entradas_video"
os.makedirs(PASTA_SAIDA, exist_ok=True)

PASTA_BACKUP = os.path.join(PASTA_SAIDA, "backups_otimizacao_cirurgica")
os.makedirs(PASTA_BACKUP, exist_ok=True)

ARQUIVO_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoint_otimizacao_horarios_cirurgico.csv")
ARQUIVO_MELHOR_RESUMO = os.path.join(PASTA_SAIDA, "18_melhor_resumo_horarios_cirurgico.csv")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "19_melhor_trades_horarios_cirurgico.csv")
ARQUIVO_TOP_100 = os.path.join(PASTA_SAIDA, "20_top_100_horarios_cirurgico.csv")
ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "21_resultados_horarios_cirurgico.csv")
ARQUIVO_RESUMO_MINIMOS = os.path.join(PASTA_SAIDA, "22_resumo_minimos_horarios_cirurgico.csv")

# Salvar progresso
SALVAR_A_CADA_CONFIGS = 250
BACKUP_A_CADA_CONFIGS = 1000

# Take e Stop
TAKE_PONTOS = 25.5
STOP_PONTOS = 225.0

# Base de 2 minutos
# 720 candles = 24h
MAX_CANDLES_FUTURO = 720

# Entrada:
# "close_signal" = entra no fechamento do candle do sinal
# "next_open"    = entra na abertura do próximo candle
MODO_ENTRADA = "close_signal"

# 1 operação por dia
APENAS_1_TRADE_POR_DIA = True

# Como escolher se houver mais de um candidato no dia
# "maior_score" = pega maior score
# "primeiro" = pega primeiro horário
MODO_ESCOLHA_DIA = "maior_score"

# Se True, descarta trade ABERTO da estatística
IGNORAR_ABERTOS_NO_RESUMO = True


# =====================================================
# FUNÇÕES DE BACKUP/CHECKPOINT
# =====================================================

def timestamp_agora():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def fazer_backup_arquivo(caminho):
    if os.path.exists(caminho):
        nome = os.path.basename(caminho)
        destino = os.path.join(PASTA_BACKUP, f"{timestamp_agora()}__{nome}")
        shutil.copy2(caminho, destino)
        print(f"Backup criado: {destino}")


def salvar_checkpoint(resultados, configs_testadas, melhor_resumo, melhor_trades, forcar_backup=False):
    checkpoint_df = pd.DataFrame(resultados)

    if not checkpoint_df.empty:
        checkpoint_df.to_csv(ARQUIVO_CHECKPOINT, index=False, encoding="utf-8-sig")

    if melhor_resumo is not None:
        pd.DataFrame([melhor_resumo]).to_csv(
            ARQUIVO_MELHOR_RESUMO,
            index=False,
            encoding="utf-8-sig"
        )

    if melhor_trades is not None and not melhor_trades.empty:
        melhor_trades.to_csv(
            ARQUIVO_MELHOR_TRADES,
            index=False,
            encoding="utf-8-sig"
        )

    print(f"CHECKPOINT SALVO | resultados: {len(resultados)} | configs testadas: {len(configs_testadas)}")

    if forcar_backup:
        fazer_backup_arquivo(ARQUIVO_CHECKPOINT)
        fazer_backup_arquivo(ARQUIVO_MELHOR_RESUMO)
        fazer_backup_arquivo(ARQUIVO_MELHOR_TRADES)


# =====================================================
# CARREGAR SCORE
# =====================================================

print("Carregando score...")

df = pd.read_csv(ARQUIVO_SCORE)

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"])
df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

df = df.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume", "score_BUY", "score_SELL", "score_NONE"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
df["Hora_SP_Texto"] = df["DataHora_SP"].dt.strftime("%H:%M")
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

            # Conservador: se bater take e stop no mesmo candle, considera loss
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

            # Conservador: se bater take e stop no mesmo candle, considera loss
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
# GERAR CANDIDATOS CIRÚRGICOS
# =====================================================

def gerar_candidatos_cirurgico(
    df_base,
    score_buy_min,
    score_sell_min,
    score_diff_min,
    horarios_permitidos,
    modo_direcao,
    usar_score_none_max,
    score_none_max
):
    base = df_base.copy()

    cond_horario = base["Hora_SP_Texto"].isin(horarios_permitidos)

    if usar_score_none_max:
        cond_none = base["score_NONE"] <= score_none_max
    else:
        cond_none = True

    cond_buy = (
        cond_horario &
        cond_none &
        (base["score_BUY"] >= score_buy_min) &
        (base["score_BUY"] > base["score_SELL"]) &
        ((base["score_BUY"] - base["score_SELL"]) >= score_diff_min)
    )

    cond_sell = (
        cond_horario &
        cond_none &
        (base["score_SELL"] >= score_sell_min) &
        (base["score_SELL"] > base["score_BUY"]) &
        ((base["score_SELL"] - base["score_BUY"]) >= score_diff_min)
    )

    if modo_direcao == "BUY_ONLY":
        cond_sell = False

    if modo_direcao == "SELL_ONLY":
        cond_buy = False

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

def testar_configuracao(config):
    candidatos = gerar_candidatos_cirurgico(
        df_base=df,
        score_buy_min=config["score_buy_min"],
        score_sell_min=config["score_sell_min"],
        score_diff_min=config["score_diff_min"],
        horarios_permitidos=config["horarios_permitidos"],
        modo_direcao=config["modo_direcao"],
        usar_score_none_max=config["usar_score_none_max"],
        score_none_max=config["score_none_max"]
    )

    if candidatos.empty:
        return None, pd.DataFrame()

    if APENAS_1_TRADE_POR_DIA:
        candidatos = escolher_um_por_dia(candidatos)

    trades = []

    for _, row in candidatos.iterrows():
        idx_base = df.index[df["DataHora_SP"] == row["DataHora_SP"]]

        if len(idx_base) == 0:
            continue

        indice_sinal = int(idx_base[0])
        direcao = row["Direcao_Candidata"]

        trade = simular_trade(df, indice_sinal, direcao)

        if trade is None:
            continue

        trades.append({
            "indice_sinal": indice_sinal,
            "DataHora_Sinal_SP": row["DataHora_SP"],
            "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
            "Data": row["Data"],
            "Hora_SP": row["Hora_SP_Texto"],
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

    if IGNORAR_ABERTOS_NO_RESUMO:
        fechados = trades_df[trades_df["resultado"].isin(["WIN", "LOSS"])].copy()
    else:
        fechados = trades_df.copy()

    if fechados.empty:
        return None, trades_df

    wins = (fechados["resultado"] == "WIN").sum()
    losses = (fechados["resultado"] == "LOSS").sum()
    abertos = (trades_df["resultado"] == "ABERTO").sum()
    total = len(fechados)

    winrate = wins / total * 100 if total > 0 else 0
    lucro_pontos = fechados["pontos"].sum()

    buy_total = (fechados["Direcao"] == "BUY").sum()
    sell_total = (fechados["Direcao"] == "SELL").sum()

    buy_wins = ((fechados["Direcao"] == "BUY") & (fechados["resultado"] == "WIN")).sum()
    sell_wins = ((fechados["Direcao"] == "SELL") & (fechados["resultado"] == "WIN")).sum()

    buy_winrate = buy_wins / buy_total * 100 if buy_total > 0 else np.nan
    sell_winrate = sell_wins / sell_total * 100 if sell_total > 0 else np.nan

    resumo = {
        "config_id": config["config_id"],
        "score_buy_min": config["score_buy_min"],
        "score_sell_min": config["score_sell_min"],
        "score_diff_min": config["score_diff_min"],
        "modo_direcao": config["modo_direcao"],
        "horarios_nome": config["horarios_nome"],
        "horarios_permitidos": "|".join(config["horarios_permitidos"]),
        "usar_score_none_max": config["usar_score_none_max"],
        "score_none_max": config["score_none_max"],
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "abertos": abertos,
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
# MONTAR LISTAS CIRÚRGICAS
# =====================================================

# Horários principais encontrados
GRUPOS_HORARIOS = {
    "somente_0348": ["03:48"],
    "somente_0448": ["04:48"],
    "0348_0448": ["03:48", "04:48"],

    "nucleo_0348": ["03:48", "03:52", "03:54", "03:56", "03:58"],
    "nucleo_0448": ["04:32", "04:40", "04:42", "04:48", "04:50", "04:52", "04:56", "04:58"],

    "nucleo_0348_0448": [
        "03:48", "03:52", "03:54", "03:56", "03:58",
        "04:32", "04:40", "04:42", "04:48", "04:50", "04:52", "04:56", "04:58"
    ],

    "janela_0340_0400": [
        "03:40", "03:42", "03:44", "03:46", "03:48",
        "03:50", "03:52", "03:54", "03:56", "03:58", "04:00"
    ],

    "janela_0430_0500": [
        "04:30", "04:32", "04:34", "04:36", "04:38",
        "04:40", "04:42", "04:44", "04:46", "04:48",
        "04:50", "04:52", "04:54", "04:56", "04:58", "05:00"
    ],

    "janela_0340_0500": [
        "03:40", "03:42", "03:44", "03:46", "03:48",
        "03:50", "03:52", "03:54", "03:56", "03:58",
        "04:00", "04:02", "04:04", "04:06", "04:08",
        "04:10", "04:12", "04:14", "04:16", "04:18",
        "04:20", "04:22", "04:24", "04:26", "04:28",
        "04:30", "04:32", "04:34", "04:36", "04:38",
        "04:40", "04:42", "04:44", "04:46", "04:48",
        "04:50", "04:52", "04:54", "04:56", "04:58", "05:00"
    ],

    "janela_0300_0600": [
        f"{h:02d}:{m:02d}"
        for h in range(3, 6)
        for m in range(0, 60, 2)
    ],

    "janela_0000_0600": [
        f"{h:02d}:{m:02d}"
        for h in range(0, 6)
        for m in range(0, 60, 2)
    ],
}

score_buy_lista = [
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90
]

score_sell_lista = [
    0.50, 0.55, 0.60, 0.65, 0.70,
    0.72, 0.74, 0.75, 0.76, 0.78,
    0.80, 0.82, 0.84, 0.86, 0.88, 0.90
]

score_diff_lista = [
    0.00, 0.02, 0.04, 0.06, 0.08,
    0.10, 0.12, 0.15, 0.18, 0.20
]

modo_direcao_lista = [
    "BOTH",
    "BUY_ONLY",
    "SELL_ONLY"
]

usar_score_none_lista = [
    False,
    True
]

score_none_max_lista = [
    0.50,
    0.40,
    0.30,
    0.20,
    0.10
]


# =====================================================
# GERAR CONFIGURAÇÕES
# =====================================================

configs = []
config_id = 0

for score_buy in score_buy_lista:
    for score_sell in score_sell_lista:
        for score_diff in score_diff_lista:
            for modo_direcao in modo_direcao_lista:
                for horarios_nome, horarios_permitidos in GRUPOS_HORARIOS.items():
                    for usar_score_none_max in usar_score_none_lista:
                        if usar_score_none_max:
                            for score_none_max in score_none_max_lista:
                                config_id += 1
                                configs.append({
                                    "config_id": config_id,
                                    "score_buy_min": score_buy,
                                    "score_sell_min": score_sell,
                                    "score_diff_min": score_diff,
                                    "modo_direcao": modo_direcao,
                                    "horarios_nome": horarios_nome,
                                    "horarios_permitidos": horarios_permitidos,
                                    "usar_score_none_max": usar_score_none_max,
                                    "score_none_max": score_none_max
                                })
                        else:
                            config_id += 1
                            configs.append({
                                "config_id": config_id,
                                "score_buy_min": score_buy,
                                "score_sell_min": score_sell,
                                "score_diff_min": score_diff,
                                "modo_direcao": modo_direcao,
                                "horarios_nome": horarios_nome,
                                "horarios_permitidos": horarios_permitidos,
                                "usar_score_none_max": usar_score_none_max,
                                "score_none_max": 999.0
                            })

print("Total de configurações cirúrgicas:", len(configs))


# =====================================================
# CARREGAR CHECKPOINT
# =====================================================

if os.path.exists(ARQUIVO_CHECKPOINT):
    print("Checkpoint encontrado. Continuando...")

    checkpoint_df = pd.read_csv(ARQUIVO_CHECKPOINT)
    resultados = checkpoint_df.to_dict("records")
    configs_testadas = set(checkpoint_df["config_id"].astype(int).tolist())

    print("Resultados carregados:", len(resultados))
    print("Configurações já testadas:", len(configs_testadas))
else:
    print("Nenhum checkpoint encontrado. Iniciando do zero...")
    resultados = []
    configs_testadas = set()

melhor_resumo = None
melhor_trades = None

if os.path.exists(ARQUIVO_MELHOR_RESUMO):
    temp = pd.read_csv(ARQUIVO_MELHOR_RESUMO)
    if not temp.empty:
        melhor_resumo = temp.iloc[0].to_dict()
        print("Melhor resumo anterior carregado.")

if os.path.exists(ARQUIVO_MELHOR_TRADES):
    temp_trades = pd.read_csv(ARQUIVO_MELHOR_TRADES)
    if not temp_trades.empty:
        melhor_trades = temp_trades
        print("Melhores trades anteriores carregados.")

# Caso tenha checkpoint mas não tenha melhor carregado
if melhor_resumo is None and resultados:
    temp = pd.DataFrame(resultados)
    temp_100 = temp[temp["winrate"] == 100.0].copy()

    if not temp_100.empty:
        temp_100 = temp_100.sort_values(
            by=["total_trades", "lucro_pontos", "media_score"],
            ascending=[False, False, False]
        )
        melhor_resumo = temp_100.iloc[0].to_dict()


# =====================================================
# EXECUTAR OTIMIZAÇÃO
# =====================================================

print("Iniciando busca cirúrgica com checkpoint...")

inicio = time.time()
novas_configs = 0

try:
    for pos, config in enumerate(configs, start=1):
        cid = int(config["config_id"])

        if cid in configs_testadas:
            continue

        resumo, trades = testar_configuracao(config)

        configs_testadas.add(cid)
        novas_configs += 1

        if resumo is not None:
            resultados.append(resumo)

            if resumo["winrate"] == 100.0:
                if melhor_resumo is None:
                    melhor_resumo = resumo
                    melhor_trades = trades
                    print("\nPRIMEIRO 100% ENCONTRADO:")
                    print(pd.Series(melhor_resumo))
                else:
                    chave_atual = (
                        resumo["total_trades"],
                        resumo["lucro_pontos"],
                        resumo["media_score"]
                    )

                    chave_melhor = (
                        melhor_resumo["total_trades"],
                        melhor_resumo["lucro_pontos"],
                        melhor_resumo["media_score"]
                    )

                    if chave_atual > chave_melhor:
                        melhor_resumo = resumo
                        melhor_trades = trades

                        print("\nNOVO MELHOR 100% ENCONTRADO:")
                        print(pd.Series(melhor_resumo))

        if novas_configs % SALVAR_A_CADA_CONFIGS == 0:
            salvar_checkpoint(
                resultados=resultados,
                configs_testadas=configs_testadas,
                melhor_resumo=melhor_resumo,
                melhor_trades=melhor_trades,
                forcar_backup=False
            )

        if novas_configs % BACKUP_A_CADA_CONFIGS == 0:
            salvar_checkpoint(
                resultados=resultados,
                configs_testadas=configs_testadas,
                melhor_resumo=melhor_resumo,
                melhor_trades=melhor_trades,
                forcar_backup=True
            )

        if pos % 500 == 0:
            minutos = (time.time() - inicio) / 60
            print(
                f"Progresso: {pos}/{len(configs)} | "
                f"testadas nesta execução: {novas_configs} | "
                f"resultados: {len(resultados)} | "
                f"tempo: {minutos:.1f} min"
            )

except KeyboardInterrupt:
    print("\nInterrompido pelo usuário.")
    print("Salvando checkpoint antes de sair...")
    salvar_checkpoint(
        resultados=resultados,
        configs_testadas=configs_testadas,
        melhor_resumo=melhor_resumo,
        melhor_trades=melhor_trades,
        forcar_backup=True
    )
    raise SystemExit

except Exception as e:
    print("\nERRO:")
    print(e)
    print("Salvando checkpoint antes de sair...")
    salvar_checkpoint(
        resultados=resultados,
        configs_testadas=configs_testadas,
        melhor_resumo=melhor_resumo,
        melhor_trades=melhor_trades,
        forcar_backup=True
    )
    raise

# Salvar final
salvar_checkpoint(
    resultados=resultados,
    configs_testadas=configs_testadas,
    melhor_resumo=melhor_resumo,
    melhor_trades=melhor_trades,
    forcar_backup=True
)


# =====================================================
# GERAR ARQUIVOS FINAIS
# =====================================================

print("Gerando arquivos finais...")

resultados_df = pd.DataFrame(resultados)

if resultados_df.empty:
    print("Nenhum resultado foi gerado.")
    raise SystemExit

resultados_df = resultados_df.sort_values(
    by=["winrate", "total_trades", "lucro_pontos"],
    ascending=[False, False, False]
)

resultados_df.to_csv(ARQUIVO_RESULTADOS, index=False, encoding="utf-8-sig")

top_100 = resultados_df[resultados_df["winrate"] == 100.0].copy()

if not top_100.empty:
    top_100 = top_100.sort_values(
        by=["total_trades", "lucro_pontos", "media_score"],
        ascending=[False, False, False]
    )

top_100.to_csv(ARQUIVO_TOP_100, index=False, encoding="utf-8-sig")

# Resumo por mínimos
minimos = [50, 75, 100, 125, 150, 180, 200, 220, 240]
linhas_minimos = []

for minimo in minimos:
    filtro = resultados_df[resultados_df["total_trades"] >= minimo].copy()

    if filtro.empty:
        continue

    melhor = filtro.sort_values(
        by=["winrate", "total_trades", "lucro_pontos"],
        ascending=[False, False, False]
    ).iloc[0]

    linhas_minimos.append(melhor)

resumo_minimos = pd.DataFrame(linhas_minimos)
resumo_minimos.to_csv(ARQUIVO_RESUMO_MINIMOS, index=False, encoding="utf-8-sig")

print("\n=====================================================")
print("MELHOR 100%")
print("=====================================================")

if melhor_resumo is not None:
    print(pd.Series(melhor_resumo))
else:
    print("Nenhuma configuração 100% encontrada.")

print("\n=====================================================")
print("TOP 30 COM 100%")
print("=====================================================")

if top_100.empty:
    print("Nenhuma configuração 100%.")
else:
    print(top_100.head(30))

print("\n=====================================================")
print("MELHORES POR MÍNIMO DE TRADES")
print("=====================================================")

if resumo_minimos.empty:
    print("Nenhum resumo por mínimo.")
else:
    print(resumo_minimos[[
        "total_trades",
        "winrate",
        "wins",
        "losses",
        "lucro_pontos",
        "score_buy_min",
        "score_sell_min",
        "score_diff_min",
        "modo_direcao",
        "horarios_nome",
        "usar_score_none_max",
        "score_none_max"
    ]])

print("\n=====================================================")
print("ARQUIVOS GERADOS")
print("=====================================================")
print(ARQUIVO_CHECKPOINT)
print(ARQUIVO_MELHOR_RESUMO)
print(ARQUIVO_MELHOR_TRADES)
print(ARQUIVO_TOP_100)
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_RESUMO_MINIMOS)
print("Pasta de backups:", PASTA_BACKUP)