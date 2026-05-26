import os
import json
import numpy as np
import pandas as pd
from datetime import datetime


# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")

ARQUIVO_CANDIDATOS_SCORE = os.path.join(PASTA_V4, "04_v4_score_candidatos.csv.gz")
ARQUIVO_MELHOR_CONFIG = os.path.join(PASTA_V4, "checkpoint_v4_melhor.csv")

PASTA_OPERACIONAL = os.path.join(BASE_DIR, "operacional_v4")
os.makedirs(PASTA_OPERACIONAL, exist_ok=True)

ARQUIVO_SINAIS = os.path.join(PASTA_OPERACIONAL, "01_sinais_v4_operacional.csv")
ARQUIVO_RESUMO = os.path.join(PASTA_OPERACIONAL, "02_resumo_v4_operacional.csv")
ARQUIVO_SINAL_TXT = os.path.join(PASTA_OPERACIONAL, "sinal.txt")
ARQUIVO_ULTIMO_SINAL = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v4.json")

VALOR_PONTO_MNQ = 2.0


# =====================================================
# FUNÇÕES DE ARQUIVO
# =====================================================

def salvar_csv_seguro(df, caminho):
    temp = caminho + ".tmp"
    df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def salvar_txt_seguro(texto, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        f.write(texto)

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def salvar_json_seguro(obj, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4, default=str)

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


# =====================================================
# CARREGAMENTO
# =====================================================

def carregar_config_melhor():
    if not os.path.exists(ARQUIVO_MELHOR_CONFIG):
        raise FileNotFoundError(f"Não encontrei o arquivo: {ARQUIVO_MELHOR_CONFIG}")

    df_config = pd.read_csv(ARQUIVO_MELHOR_CONFIG)

    if df_config.empty:
        raise Exception("Arquivo checkpoint_v4_melhor.csv está vazio.")

    config = df_config.iloc[0].to_dict()

    config["take_pontos"] = float(config["take_pontos"])
    config["stop_pontos"] = float(config["stop_pontos"])
    config["prob_win_min"] = float(config["prob_win_min"])
    config["max_trades_dia"] = int(config["max_trades_dia"])
    config["parar_apos_loss"] = str(config["parar_apos_loss"]).lower() in ["true", "1", "sim", "yes"]
    config["score_buy_min"] = float(config["score_buy_min"])
    config["score_sell_min"] = float(config["score_sell_min"])
    config["diferenca_minima"] = float(config["diferenca_minima"])
    config["hora_inicio"] = float(config["hora_inicio"])
    config["hora_fim"] = float(config["hora_fim"])

    return config


def carregar_candidatos():
    if not os.path.exists(ARQUIVO_CANDIDATOS_SCORE):
        raise FileNotFoundError(f"Não encontrei o arquivo: {ARQUIVO_CANDIDATOS_SCORE}")

    print("Carregando candidatos V4...")

    df = pd.read_csv(ARQUIVO_CANDIDATOS_SCORE, compression="gzip")

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")

    if "DataHora_Chicago" in df.columns:
        df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
    else:
        df["Data"] = df["DataHora_SP"].dt.date

    cols_numericas = [
        "indice_sinal",
        "Hora_SP_Decimal",
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
    ]

    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    print("Candidatos carregados:", len(df))
    print("Início:", df["DataHora_SP"].min())
    print("Fim:", df["DataHora_SP"].max())

    return df


# =====================================================
# LÓGICA V4 FIEL
# =====================================================

def selecionar_sinais_v4(cand_score, config):
    stop_sufixo = str(config["stop_pontos"]).replace(".", "_")

    resultado_col = f"resultado_stop_{stop_sufixo}"
    pontos_col = f"pontos_stop_{stop_sufixo}"
    dt_entrada_col = f"dt_entrada_stop_{stop_sufixo}"
    dt_saida_col = f"dt_saida_stop_{stop_sufixo}"
    indice_saida_col = f"indice_saida_stop_{stop_sufixo}"
    runup_col = f"runup_stop_{stop_sufixo}"
    drawdown_col = f"drawdown_stop_{stop_sufixo}"

    colunas_obrigatorias = [
        resultado_col,
        pontos_col,
        dt_entrada_col,
        dt_saida_col,
        indice_saida_col,
        runup_col,
        drawdown_col,
    ]

    for col in colunas_obrigatorias:
        if col not in cand_score.columns:
            raise Exception(f"Coluna obrigatória não encontrada: {col}")

    base = cand_score.copy()

    base[dt_entrada_col] = pd.to_datetime(base[dt_entrada_col], errors="coerce")
    base[dt_saida_col] = pd.to_datetime(base[dt_saida_col], errors="coerce")

    for col in [pontos_col, indice_saida_col, runup_col, drawdown_col]:
        base[col] = pd.to_numeric(base[col], errors="coerce")

    cond_base = (
        (base["prob_win_v4"] >= config["prob_win_min"]) &
        (base["Hora_SP_Decimal"] >= config["hora_inicio"]) &
        (base["Hora_SP_Decimal"] <= config["hora_fim"]) &
        (base["score_diff"] >= config["diferenca_minima"])
    )

    cond_buy = (
        cond_base &
        (base["Direcao"] == "BUY") &
        (base["score_BUY"] >= config["score_buy_min"])
    )

    cond_sell = (
        cond_base &
        (base["Direcao"] == "SELL") &
        (base["score_SELL"] >= config["score_sell_min"])
    )

    candidatos = base[cond_buy | cond_sell].copy()

    print("\nCandidatos após filtro operacional:", len(candidatos))

    if candidatos.empty:
        return pd.DataFrame()

    candidatos = candidatos.sort_values(["Data", "DataHora_SP"]).copy()

    sinais = []

    for data, grupo in candidatos.groupby("Data"):
        grupo = grupo.sort_values(
            by=["prob_win_v4", "score_direcao", "score_diff", "DataHora_SP"],
            ascending=[False, False, False, True]
        ).copy()

        trades_dia = 0
        ultimo_indice_saida = -1
        teve_loss = False

        for _, row in grupo.iterrows():
            if trades_dia >= config["max_trades_dia"]:
                break

            if config["parar_apos_loss"] and teve_loss:
                break

            indice_sinal = int(row["indice_sinal"])
            indice_saida = int(row[indice_saida_col])

            if indice_sinal <= ultimo_indice_saida:
                continue

            resultado = row[resultado_col]

            if resultado not in ["WIN", "LOSS"]:
                continue

            direcao = row["Direcao"]
            preco_entrada = float(row["close"])

            if direcao == "BUY":
                preco_take = preco_entrada + config["take_pontos"]
                preco_stop = preco_entrada - config["stop_pontos"]
                sinal_txt = "buy"
            else:
                preco_take = preco_entrada - config["take_pontos"]
                preco_stop = preco_entrada + config["stop_pontos"]
                sinal_txt = "sell"

            trades_dia += 1
            ultimo_indice_saida = indice_saida

            if resultado == "LOSS":
                teve_loss = True

            sinais.append({
                "DataHora_Sinal_SP": row["DataHora_SP"],
                "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
                "Data": row["Data"],
                "Hora_SP_Decimal": row["Hora_SP_Decimal"],
                "SINAL": sinal_txt,
                "Direcao": direcao,
                "preco_entrada_referencia": preco_entrada,
                "preco_take": preco_take,
                "preco_stop": preco_stop,
                "take_pontos": config["take_pontos"],
                "stop_pontos": config["stop_pontos"],
                "score_BUY": row["score_BUY"],
                "score_SELL": row["score_SELL"],
                "score_NONE": row["score_NONE"],
                "score_direcao": row["score_direcao"],
                "score_oposto": row["score_oposto"],
                "score_diff": row["score_diff"],
                "prob_win_v4": row["prob_win_v4"],
                "resultado_backtest": resultado,
                "pontos_backtest": row[pontos_col],
                "dt_entrada_backtest": row[dt_entrada_col],
                "dt_saida_backtest": row[dt_saida_col],
                "runup_backtest": row[runup_col],
                "drawdown_backtest": row[drawdown_col],
                "indice_sinal": indice_sinal,
                "indice_saida": indice_saida,
                "trade_numero_dia": trades_dia,
                "parar_apos_loss": config["parar_apos_loss"],
                "max_trades_dia": config["max_trades_dia"],
            })

    sinais_df = pd.DataFrame(sinais)

    if not sinais_df.empty:
        sinais_df = sinais_df.sort_values("DataHora_Sinal_SP").reset_index(drop=True)

    return sinais_df


# =====================================================
# RESUMO
# =====================================================

def calcular_resumo(sinais, config):
    if sinais.empty:
        return {
            "total_sinais": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "lucro_pontos": 0,
            "lucro_usd_1_mnq": 0,
            "profit_factor": np.nan,
        }

    total = len(sinais)
    wins = int((sinais["resultado_backtest"] == "WIN").sum())
    losses = int((sinais["resultado_backtest"] == "LOSS").sum())

    winrate = wins / total * 100 if total else 0
    lucro_pontos = float(sinais["pontos_backtest"].sum())

    gross_profit = float(sinais.loc[sinais["pontos_backtest"] > 0, "pontos_backtest"].sum())
    gross_loss = abs(float(sinais.loc[sinais["pontos_backtest"] < 0, "pontos_backtest"].sum()))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    diario = sinais.groupby("Data")["pontos_backtest"].sum()

    resumo = {
        "data_execucao_script": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "take_pontos": config["take_pontos"],
        "stop_pontos": config["stop_pontos"],
        "prob_win_min": config["prob_win_min"],
        "score_buy_min": config["score_buy_min"],
        "score_sell_min": config["score_sell_min"],
        "hora_inicio": config["hora_inicio"],
        "hora_fim": config["hora_fim"],
        "max_trades_dia": config["max_trades_dia"],
        "parar_apos_loss": config["parar_apos_loss"],
        "total_sinais": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro_pontos,
        "lucro_usd_1_mnq": lucro_pontos * VALOR_PONTO_MNQ,
        "profit_factor": profit_factor,
        "buy_total": int((sinais["Direcao"] == "BUY").sum()),
        "sell_total": int((sinais["Direcao"] == "SELL").sum()),
        "dias_operados": int(sinais["Data"].nunique()),
        "pior_dia_pontos": float(diario.min()) if len(diario) else np.nan,
        "melhor_dia_pontos": float(diario.max()) if len(diario) else np.nan,
        "pior_dia_usd_1_mnq": float(diario.min()) * VALOR_PONTO_MNQ if len(diario) else np.nan,
        "melhor_dia_usd_1_mnq": float(diario.max()) * VALOR_PONTO_MNQ if len(diario) else np.nan,
        "media_prob_win": float(sinais["prob_win_v4"].mean()),
        "min_prob_win": float(sinais["prob_win_v4"].min()),
    }

    return resumo


# =====================================================
# SINAL.TXT
# =====================================================

def salvar_ultimo_sinal(sinais):
    if sinais.empty:
        salvar_txt_seguro("none", ARQUIVO_SINAL_TXT)
        salvar_json_seguro({"sinal": "none", "motivo": "nenhum sinal encontrado"}, ARQUIVO_ULTIMO_SINAL)
        return

    ultimo = sinais.iloc[-1].to_dict()

    sinal_txt = str(ultimo["SINAL"]).lower()

    salvar_txt_seguro(sinal_txt, ARQUIVO_SINAL_TXT)

    payload = {
        "sinal": sinal_txt,
        "datahora_sinal_sp": str(ultimo["DataHora_Sinal_SP"]),
        "direcao": ultimo["Direcao"],
        "preco_entrada_referencia": float(ultimo["preco_entrada_referencia"]),
        "preco_take": float(ultimo["preco_take"]),
        "preco_stop": float(ultimo["preco_stop"]),
        "take_pontos": float(ultimo["take_pontos"]),
        "stop_pontos": float(ultimo["stop_pontos"]),
        "prob_win_v4": float(ultimo["prob_win_v4"]),
        "score_buy": float(ultimo["score_BUY"]),
        "score_sell": float(ultimo["score_SELL"]),
        "resultado_backtest": ultimo["resultado_backtest"],
        "pontos_backtest": float(ultimo["pontos_backtest"]),
    }

    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL)

    print("\n=====================================================")
    print("ÚLTIMO SINAL SALVO")
    print("=====================================================")
    print(json.dumps(payload, ensure_ascii=False, indent=4, default=str))


# =====================================================
# MAIN
# =====================================================

def main():
    print("=====================================================")
    print("SINAL V4 OPERACIONAL - MODO SEGURO")
    print("=====================================================")

    config = carregar_config_melhor()

    print("\nConfiguração operacional V4:")
    print(f"Take: {config['take_pontos']}")
    print(f"Stop: {config['stop_pontos']}")
    print(f"Prob mínima: {config['prob_win_min']}")
    print(f"Score BUY mínimo: {config['score_buy_min']}")
    print(f"Score SELL mínimo: {config['score_sell_min']}")
    print(f"Horário: {config['hora_inicio']} até {config['hora_fim']}")
    print(f"Máximo trades/dia: {config['max_trades_dia']}")
    print(f"Parar após loss: {config['parar_apos_loss']}")

    candidatos = carregar_candidatos()

    sinais = selecionar_sinais_v4(candidatos, config)

    resumo = calcular_resumo(sinais, config)

    print("\n=====================================================")
    print("RESUMO DOS SINAIS V4")
    print("=====================================================")
    print(pd.Series(resumo))

    if not sinais.empty:
        print("\nPrimeiros 10 sinais:")
        print(sinais.head(10)[[
            "DataHora_Sinal_SP",
            "SINAL",
            "preco_entrada_referencia",
            "preco_take",
            "preco_stop",
            "prob_win_v4",
            "score_BUY",
            "score_SELL",
            "resultado_backtest",
            "pontos_backtest",
        ]])

        print("\nÚltimos 10 sinais:")
        print(sinais.tail(10)[[
            "DataHora_Sinal_SP",
            "SINAL",
            "preco_entrada_referencia",
            "preco_take",
            "preco_stop",
            "prob_win_v4",
            "score_BUY",
            "score_SELL",
            "resultado_backtest",
            "pontos_backtest",
        ]])

    salvar_csv_seguro(sinais, ARQUIVO_SINAIS)
    salvar_csv_seguro(pd.DataFrame([resumo]), ARQUIVO_RESUMO)

    salvar_ultimo_sinal(sinais)

    print("\n=====================================================")
    print("ARQUIVOS GERADOS")
    print("=====================================================")
    print(ARQUIVO_SINAIS)
    print(ARQUIVO_RESUMO)
    print(ARQUIVO_SINAL_TXT)
    print(ARQUIVO_ULTIMO_SINAL)

    print("\nFINALIZADO.")
    print("Observação: este script ainda está em modo seguro/histórico.")
    print("Ele reproduz os sinais do V4. A próxima etapa é conectar candles novos em tempo real.")


if __name__ == "__main__":
    main()