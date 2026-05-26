import pandas as pd
import numpy as np
import os
import time


# =====================================================
# CONFIGURAÇÕES WINDOWS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

ARQUIVO_SCORE = os.path.join(
    BASE_DIR,
    "saida_ml_entradas_video_v3",
    "05_v3_score_todos_candles.csv.gz"
)

PASTA_SAIDA = os.path.join(
    BASE_DIR,
    "saida_ml_entradas_video_v3_otimizacao_takestop"
)

os.makedirs(PASTA_SAIDA, exist_ok=True)

ARQUIVO_CHECKPOINT = os.path.join(PASTA_SAIDA, "checkpoint_v3_takestop_resultados.csv.gz")
ARQUIVO_CHECKPOINT_MELHOR = os.path.join(PASTA_SAIDA, "checkpoint_v3_takestop_melhor.csv")
ARQUIVO_CHECKPOINT_TRADES = os.path.join(PASTA_SAIDA, "checkpoint_v3_takestop_melhor_trades.csv.gz")

ARQUIVO_RESULTADOS = os.path.join(PASTA_SAIDA, "01_v3_takestop_resultados.csv.gz")
ARQUIVO_TOP = os.path.join(PASTA_SAIDA, "02_v3_takestop_top_resultados.csv")
ARQUIVO_MELHOR = os.path.join(PASTA_SAIDA, "03_v3_takestop_melhor.csv")
ARQUIVO_MELHOR_TRADES = os.path.join(PASTA_SAIDA, "04_v3_takestop_melhor_trades.csv.gz")

SALVAR_A_CADA = 500

MAX_CANDLES_FUTURO = 720
MODO_ENTRADA = "close_signal"

# Para mesa proprietária:
# True = depois de 1 loss no dia, para de operar naquele dia.
# False = continua até bater o limite de entradas do dia.
PARAR_DIA_APOS_LOSS_LISTA = [True, False]

TAKES = [25.5, 40.0, 50.5, 60.0, 75.0, 100.0]
STOPS = [80.0, 100.0, 117.0, 120.0, 125.0, 150.0, 180.0, 225.0]

MAX_TRADES_DIA_LISTA = [1, 3, 5]

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

diferencas = [
    0.00, 0.02, 0.04, 0.06, 0.08,
    0.10, 0.12, 0.15, 0.18, 0.20
]

horarios = [
    (0.0, 6.0),
    (3.0, 6.0),
    (3.5, 4.1),
    (3.6, 4.0),
    (3.75, 3.90),
    (4.0, 8.0),
    (6.0, 10.0),
    (8.0, 12.0),
    (0.0, 12.0),
    (0.0, 17.0),
]

WINRATE_MINIMO_DESTAQUE = 85.0
TRADES_MINIMO_DESTAQUE = 100


# =====================================================
# FUNÇÕES DE SALVAMENTO
# =====================================================

def remover_temporarios():
    if not os.path.exists(PASTA_SAIDA):
        return

    for nome in os.listdir(PASTA_SAIDA):
        if nome.endswith(".tmp"):
            caminho = os.path.join(PASTA_SAIDA, nome)

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


def salvar_checkpoint(resultados, melhor, melhores_trades):
    if resultados:
        salvar_csv_seguro(
            pd.DataFrame(resultados),
            ARQUIVO_CHECKPOINT,
            compactado=True
        )

    if melhor is not None:
        salvar_csv_seguro(
            pd.DataFrame([melhor]),
            ARQUIVO_CHECKPOINT_MELHOR,
            compactado=False
        )

    if melhores_trades is not None and not melhores_trades.empty:
        salvar_csv_seguro(
            melhores_trades,
            ARQUIVO_CHECKPOINT_TRADES,
            compactado=True
        )

    print(f"CHECKPOINT SALVO: {len(resultados)} resultados.")


# =====================================================
# SIMULAÇÃO DE TRADE
# =====================================================

def simular_trade(df_base, indice_sinal, direcao, take_pontos, stop_pontos):
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
        preco_take = preco_entrada + take_pontos
        preco_stop = preco_entrada - stop_pontos
    else:
        preco_take = preco_entrada - take_pontos
        preco_stop = preco_entrada + stop_pontos

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
            maior_runup = max(maior_runup, high - preco_entrada)
            maior_drawdown = max(maior_drawdown, preco_entrada - low)

            bateu_take = high >= preco_take
            bateu_stop = low <= preco_stop

            # Conservador:
            # se take e stop forem tocados no mesmo candle, considera stop primeiro.
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -stop_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -stop_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": take_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

        else:
            maior_runup = max(maior_runup, preco_entrada - low)
            maior_drawdown = max(maior_drawdown, high - preco_entrada)

            bateu_take = low <= preco_take
            bateu_stop = high >= preco_stop

            # Conservador:
            # se take e stop forem tocados no mesmo candle, considera stop primeiro.
            if bateu_stop and bateu_take:
                return {
                    "resultado": "LOSS",
                    "pontos": -stop_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_stop:
                return {
                    "resultado": "LOSS",
                    "pontos": -stop_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_stop,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
                    "candles_ate_saida": j - indice_entrada,
                    "minutos_ate_saida": (j - indice_entrada) * 2,
                    "runup": maior_runup,
                    "drawdown": maior_drawdown
                }

            if bateu_take:
                return {
                    "resultado": "WIN",
                    "pontos": take_pontos,
                    "preco_entrada": preco_entrada,
                    "preco_saida": preco_take,
                    "dt_entrada": dt_entrada,
                    "dt_saida": dt_saida,
                    "indice_saida": j,
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
        "indice_saida": fim,
        "candles_ate_saida": np.nan,
        "minutos_ate_saida": np.nan,
        "runup": maior_runup,
        "drawdown": maior_drawdown
    }


# =====================================================
# GERAR CANDIDATOS
# =====================================================

def gerar_candidatos(df_base, score_buy_min, score_sell_min, hora_inicio, hora_fim, diferenca_minima):
    base = df_base.copy()

    cond_horario = (
        (base["Hora_SP_Decimal"] >= hora_inicio) &
        (base["Hora_SP_Decimal"] <= hora_fim)
    )

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
# SELECIONAR TRADES POR DIA
# =====================================================

def selecionar_trades_por_dia(
    candidatos,
    df_base,
    take_pontos,
    stop_pontos,
    max_trades_dia,
    parar_apos_loss
):
    if candidatos.empty:
        return pd.DataFrame()

    trades = []

    candidatos = candidatos.sort_values(["Data", "DataHora_SP"]).copy()

    for data, grupo in candidatos.groupby("Data"):
        grupo = grupo.sort_values(
            by=["score_direcao", "score_diff", "DataHora_SP"],
            ascending=[False, False, True]
        ).copy()

        trades_dia = 0
        ultimo_indice_saida = -1
        teve_loss_no_dia = False

        for _, row in grupo.iterrows():
            if trades_dia >= max_trades_dia:
                break

            if parar_apos_loss and teve_loss_no_dia:
                break

            idx_base = df_base.index[df_base["DataHora_SP"] == row["DataHora_SP"]]

            if len(idx_base) == 0:
                continue

            indice_sinal = int(idx_base[0])

            # Não deixa abrir nova operação antes da anterior fechar.
            if indice_sinal <= ultimo_indice_saida:
                continue

            direcao = row["Direcao_Candidata"]

            trade = simular_trade(
                df_base=df_base,
                indice_sinal=indice_sinal,
                direcao=direcao,
                take_pontos=take_pontos,
                stop_pontos=stop_pontos
            )

            if trade is None:
                continue

            trades_dia += 1
            ultimo_indice_saida = int(trade["indice_saida"])

            if trade["resultado"] == "LOSS":
                teve_loss_no_dia = True

            trades.append({
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
                "indice_saida": trade["indice_saida"],
                "candles_ate_saida": trade["candles_ate_saida"],
                "minutos_ate_saida": trade["minutos_ate_saida"],
                "runup": trade["runup"],
                "drawdown": trade["drawdown"]
            })

    return pd.DataFrame(trades)


# =====================================================
# AVALIAR CONFIGURAÇÃO
# =====================================================

def avaliar_config(config):
    candidatos = gerar_candidatos(
        df_base=df,
        score_buy_min=config["score_buy_min"],
        score_sell_min=config["score_sell_min"],
        hora_inicio=config["hora_inicio"],
        hora_fim=config["hora_fim"],
        diferenca_minima=config["diferenca_minima"]
    )

    if candidatos.empty:
        return None, pd.DataFrame()

    trades = selecionar_trades_por_dia(
        candidatos=candidatos,
        df_base=df,
        take_pontos=config["take_pontos"],
        stop_pontos=config["stop_pontos"],
        max_trades_dia=config["max_trades_dia"],
        parar_apos_loss=config["parar_apos_loss"]
    )

    if trades.empty:
        return None, trades

    fechados = trades[trades["resultado"].isin(["WIN", "LOSS"])].copy()

    if fechados.empty:
        return None, trades

    total = len(fechados)
    wins = (fechados["resultado"] == "WIN").sum()
    losses = (fechados["resultado"] == "LOSS").sum()
    winrate = wins / total * 100
    lucro = fechados["pontos"].sum()

    gross_profit = fechados.loc[fechados["pontos"] > 0, "pontos"].sum()
    gross_loss = abs(fechados.loc[fechados["pontos"] < 0, "pontos"].sum())

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    if wins > 0 and losses > 0 and gross_loss > 0:
        payoff = (gross_profit / wins) / (gross_loss / losses)
    else:
        payoff = np.inf

    diario = fechados.groupby("Data")["pontos"].sum()
    pior_dia = diario.min() if len(diario) > 0 else np.nan
    melhor_dia = diario.max() if len(diario) > 0 else np.nan

    resumo = {
        **config,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro,
        "profit_factor": profit_factor,
        "payoff": payoff,
        "buy_total": (fechados["Direcao"] == "BUY").sum(),
        "sell_total": (fechados["Direcao"] == "SELL").sum(),
        "drawdown_medio_trade": fechados["drawdown"].mean(),
        "drawdown_max_trade": fechados["drawdown"].max(),
        "runup_medio_trade": fechados["runup"].mean(),
        "runup_max_trade": fechados["runup"].max(),
        "media_minutos_saida": fechados["minutos_ate_saida"].mean(),
        "max_minutos_saida": fechados["minutos_ate_saida"].max(),
        "dias_operados": fechados["Data"].nunique(),
        "pior_dia_pontos": pior_dia,
        "melhor_dia_pontos": melhor_dia,
    }

    return resumo, trades


def melhor_chave(resumo):
    bonus = 0

    if resumo["winrate"] >= 95:
        bonus += 2_000_000

    if resumo["winrate"] >= 90:
        bonus += 1_000_000

    if resumo["winrate"] >= 85:
        bonus += 500_000

    if resumo["total_trades"] >= 180:
        bonus += 300_000

    if resumo["total_trades"] >= 150:
        bonus += 150_000

    lucro = resumo["lucro_pontos"]
    winrate = resumo["winrate"]
    total = resumo["total_trades"]
    pf = resumo["profit_factor"]

    if pf == np.inf:
        pf = 9999

    return (
        bonus + lucro,
        winrate,
        total,
        pf
    )


# =====================================================
# CARREGAR SCORE V3
# =====================================================

remover_temporarios()

print("Carregando score V3...")

if not os.path.exists(ARQUIVO_SCORE):
    raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SCORE}")

df = pd.read_csv(ARQUIVO_SCORE, compression="gzip")

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"])
df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

df = df.sort_values("DataHora_SP").reset_index(drop=True)

for col in ["open", "high", "low", "close", "volume", "score_BUY", "score_SELL", "score_NONE"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60
df["Data"] = df["DataHora_SP"].dt.date

print("Linhas:", len(df))
print("Início:", df["DataHora_SP"].min())
print("Fim:", df["DataHora_SP"].max())


# =====================================================
# CARREGAR CHECKPOINT
# =====================================================

if os.path.exists(ARQUIVO_CHECKPOINT):
    print("Checkpoint encontrado. Continuando...")

    cp = pd.read_csv(ARQUIVO_CHECKPOINT, compression="gzip")
    resultados = cp.to_dict("records")
    configs_testadas = set(cp["config_key"].astype(str).tolist())

    print("Resultados carregados:", len(resultados))
    print("Configurações já testadas:", len(configs_testadas))

else:
    print("Sem checkpoint. Iniciando do zero.")
    resultados = []
    configs_testadas = set()

melhor = None
melhores_trades = None

if os.path.exists(ARQUIVO_CHECKPOINT_MELHOR):
    temp = pd.read_csv(ARQUIVO_CHECKPOINT_MELHOR)

    if not temp.empty:
        melhor = temp.iloc[0].to_dict()
        print("Melhor anterior carregado.")

if os.path.exists(ARQUIVO_CHECKPOINT_TRADES):
    temp_trades = pd.read_csv(ARQUIVO_CHECKPOINT_TRADES, compression="gzip")

    if not temp_trades.empty:
        melhores_trades = temp_trades
        print("Trades do melhor carregados.")


# =====================================================
# GERAR CONFIGURAÇÕES
# =====================================================

configs = []
cid = 0

for take in TAKES:
    for stop in STOPS:
        for max_trades_dia in MAX_TRADES_DIA_LISTA:
            for parar_apos_loss in PARAR_DIA_APOS_LOSS_LISTA:
                for score_buy in score_buy_lista:
                    for score_sell in score_sell_lista:
                        for diff in diferencas:
                            for hora_inicio, hora_fim in horarios:
                                cid += 1

                                config_key = (
                                    f"take={take}|stop={stop}|maxdia={max_trades_dia}|"
                                    f"paraloss={parar_apos_loss}|buy={score_buy}|sell={score_sell}|"
                                    f"diff={diff}|h={hora_inicio}-{hora_fim}"
                                )

                                configs.append({
                                    "config_id": cid,
                                    "config_key": config_key,
                                    "take_pontos": take,
                                    "stop_pontos": stop,
                                    "max_trades_dia": max_trades_dia,
                                    "parar_apos_loss": parar_apos_loss,
                                    "score_buy_min": score_buy,
                                    "score_sell_min": score_sell,
                                    "diferenca_minima": diff,
                                    "hora_inicio": hora_inicio,
                                    "hora_fim": hora_fim
                                })

print("Total de configurações:", len(configs))
print("Já testadas:", len(configs_testadas))


# =====================================================
# OTIMIZAÇÃO
# =====================================================

inicio = time.time()
novos = 0

try:
    for i, config in enumerate(configs, start=1):
        if config["config_key"] in configs_testadas:
            continue

        resumo, trades = avaliar_config(config)

        configs_testadas.add(config["config_key"])

        if resumo is not None:
            resultados.append(resumo)
            novos += 1

            if melhor is None or melhor_chave(resumo) > melhor_chave(melhor):
                melhor = resumo
                melhores_trades = trades.copy()

                print("\nNOVO MELHOR:")
                print(pd.Series(melhor))

        if novos >= SALVAR_A_CADA:
            salvar_checkpoint(resultados, melhor, melhores_trades)
            novos = 0

        if i % 1000 == 0:
            print(
                f"{i}/{len(configs)} | resultados={len(resultados)} | "
                f"testadas={len(configs_testadas)} | "
                f"tempo={(time.time() - inicio) / 60:.1f} min"
            )

except KeyboardInterrupt:
    print("\nInterrompido. Salvando checkpoint...")
    salvar_checkpoint(resultados, melhor, melhores_trades)
    raise SystemExit

except Exception as e:
    print("\nErro:")
    print(e)
    print("Salvando checkpoint...")
    salvar_checkpoint(resultados, melhor, melhores_trades)
    raise

salvar_checkpoint(resultados, melhor, melhores_trades)


# =====================================================
# RESULTADOS FINAIS
# =====================================================

res = pd.DataFrame(resultados)

if res.empty:
    print("Nenhum resultado.")
    raise SystemExit

res["profit_factor_ordem"] = res["profit_factor"].replace(np.inf, 9999)

res["score_final"] = (
    res["lucro_pontos"] +
    res["winrate"] * 10 +
    res["total_trades"] * 2 +
    res["profit_factor_ordem"]
)

res = res.sort_values(
    by=["lucro_pontos", "winrate", "total_trades", "profit_factor_ordem"],
    ascending=[False, False, False, False]
)

salvar_csv_seguro(res, ARQUIVO_RESULTADOS, compactado=True)

top = res[
    (res["total_trades"] >= TRADES_MINIMO_DESTAQUE) &
    (res["winrate"] >= WINRATE_MINIMO_DESTAQUE)
].copy()

top = top.sort_values(
    by=["lucro_pontos", "winrate", "total_trades", "profit_factor_ordem"],
    ascending=[False, False, False, False]
)

salvar_csv_seguro(top.head(300), ARQUIVO_TOP, compactado=False)

if melhor is not None:
    salvar_csv_seguro(pd.DataFrame([melhor]), ARQUIVO_MELHOR, compactado=False)

if melhores_trades is not None and not melhores_trades.empty:
    salvar_csv_seguro(melhores_trades, ARQUIVO_MELHOR_TRADES, compactado=True)

print("\n=====================================================")
print("MELHOR RESULTADO")
print("=====================================================")
print(pd.Series(melhor))

print("\n=====================================================")
print("TOP 30 COM >= 85% E >= 100 TRADES")
print("=====================================================")

if top.empty:
    print("Nenhum resultado com os filtros de destaque.")
else:
    print(top.head(30))

print("\n=====================================================")
print("ARQUIVOS GERADOS")
print("=====================================================")
print(ARQUIVO_RESULTADOS)
print(ARQUIVO_TOP)
print(ARQUIVO_MELHOR)
print(ARQUIVO_MELHOR_TRADES)