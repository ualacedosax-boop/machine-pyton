import os
import json
import numpy as np
import pandas as pd


# =====================================================
# CONFIGURAÇÕES
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")

ARQUIVO_CANDIDATOS_SCORE = os.path.join(PASTA_V4, "04_v4_score_candidatos.csv.gz")
ARQUIVO_MELHOR_CONFIG = os.path.join(PASTA_V4, "checkpoint_v4_melhor.csv")
ARQUIVO_MELHOR_TRADES_ORIGINAL = os.path.join(PASTA_V4, "checkpoint_v4_melhor_trades.csv.gz")

ARQUIVO_SAIDA_TRADES_REPRODUZIDOS = os.path.join(PASTA_V4, "12_v4_trades_reproduzidos.csv.gz")
ARQUIVO_SAIDA_RESUMO_REPRODUZIDO = os.path.join(PASTA_V4, "13_v4_resumo_reproduzido.csv")
ARQUIVO_SAIDA_COMPARACAO = os.path.join(PASTA_V4, "14_v4_comparacao_original_reproduzido.csv")

VALOR_PONTO_MNQ = 2.0


# =====================================================
# FUNÇÕES
# =====================================================

def salvar_csv_seguro(df, caminho, compactado=False):
    temp = caminho + ".tmp"

    if compactado:
        df.to_csv(temp, index=False, encoding="utf-8-sig", compression="gzip")
    else:
        df.to_csv(temp, index=False, encoding="utf-8-sig")

    if os.path.exists(caminho):
        os.remove(caminho)

    os.rename(temp, caminho)
    print("Arquivo salvo:", caminho)


def carregar_config_melhor():
    if not os.path.exists(ARQUIVO_MELHOR_CONFIG):
        raise FileNotFoundError(f"Não encontrei o arquivo: {ARQUIVO_MELHOR_CONFIG}")

    df_config = pd.read_csv(ARQUIVO_MELHOR_CONFIG)

    if df_config.empty:
        raise Exception("Arquivo checkpoint_v4_melhor.csv está vazio.")

    config = df_config.iloc[0].to_dict()

    # Conversões seguras
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

    print("Carregando candidatos com score V4...")
    df = pd.read_csv(ARQUIVO_CANDIDATOS_SCORE, compression="gzip")

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")

    if "DataHora_Chicago" in df.columns:
        df["DataHora_Chicago"] = pd.to_datetime(df["DataHora_Chicago"], errors="coerce")

    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
    else:
        df["Data"] = df["DataHora_SP"].dt.date

    # Garantir tipos numéricos
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


def selecionar_trades(cand_score, config):
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

    print("\nCandidatos após filtros da configuração:", len(candidatos))

    if candidatos.empty:
        return pd.DataFrame()

    candidatos = candidatos.sort_values(["Data", "DataHora_SP"]).copy()

    trades = []

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

            # Não abre nova operação antes da anterior fechar.
            if indice_sinal <= ultimo_indice_saida:
                continue

            resultado = row[resultado_col]

            if resultado not in ["WIN", "LOSS"]:
                continue

            trades_dia += 1
            ultimo_indice_saida = indice_saida

            if resultado == "LOSS":
                teve_loss = True

            trades.append({
                "DataHora_Sinal_SP": row["DataHora_SP"],
                "DataHora_Chicago": row.get("DataHora_Chicago", pd.NaT),
                "Data": row["Data"],
                "Hora_SP_Decimal": row["Hora_SP_Decimal"],
                "Direcao": row["Direcao"],
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
                "prob_win_v4": row["prob_win_v4"],
                "take_pontos": config["take_pontos"],
                "stop_pontos": config["stop_pontos"],
                "resultado": resultado,
                "pontos": row[pontos_col],
                "dt_entrada": row[dt_entrada_col],
                "dt_saida": row[dt_saida_col],
                "indice_sinal": indice_sinal,
                "indice_saida": indice_saida,
                "runup": row[runup_col],
                "drawdown": row[drawdown_col],
            })

    return pd.DataFrame(trades)


def calcular_resumo(trades, config):
    if trades.empty:
        return {
            **config,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "lucro_pontos": 0,
            "lucro_usd_1_mnq": 0,
            "profit_factor": np.nan,
            "buy_total": 0,
            "sell_total": 0,
            "dias_operados": 0,
            "pior_dia_pontos": np.nan,
            "melhor_dia_pontos": np.nan,
            "drawdown_medio_trade": np.nan,
            "drawdown_max_trade": np.nan,
            "runup_medio_trade": np.nan,
            "runup_max_trade": np.nan,
            "media_prob_win": np.nan,
            "min_prob_win": np.nan,
        }

    total = len(trades)
    wins = int((trades["resultado"] == "WIN").sum())
    losses = int((trades["resultado"] == "LOSS").sum())

    winrate = wins / total * 100 if total > 0 else 0
    lucro_pontos = float(trades["pontos"].sum())

    gross_profit = float(trades.loc[trades["pontos"] > 0, "pontos"].sum())
    gross_loss = abs(float(trades.loc[trades["pontos"] < 0, "pontos"].sum()))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    diario = trades.groupby("Data")["pontos"].sum()

    resumo = {
        **config,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro_pontos,
        "lucro_usd_1_mnq": lucro_pontos * VALOR_PONTO_MNQ,
        "profit_factor": profit_factor,
        "buy_total": int((trades["Direcao"] == "BUY").sum()),
        "sell_total": int((trades["Direcao"] == "SELL").sum()),
        "dias_operados": int(trades["Data"].nunique()),
        "pior_dia_pontos": float(diario.min()) if len(diario) else np.nan,
        "melhor_dia_pontos": float(diario.max()) if len(diario) else np.nan,
        "pior_dia_usd_1_mnq": float(diario.min()) * VALOR_PONTO_MNQ if len(diario) else np.nan,
        "melhor_dia_usd_1_mnq": float(diario.max()) * VALOR_PONTO_MNQ if len(diario) else np.nan,
        "drawdown_medio_trade": float(trades["drawdown"].mean()),
        "drawdown_max_trade": float(trades["drawdown"].max()),
        "runup_medio_trade": float(trades["runup"].mean()),
        "runup_max_trade": float(trades["runup"].max()),
        "media_prob_win": float(trades["prob_win_v4"].mean()),
        "min_prob_win": float(trades["prob_win_v4"].min()),
    }

    return resumo


def comparar_com_original(trades_reproduzidos):
    if not os.path.exists(ARQUIVO_MELHOR_TRADES_ORIGINAL):
        print("\nArquivo original de melhores trades não encontrado. Pulando comparação.")
        return pd.DataFrame()

    print("\nCarregando trades originais do checkpoint para comparação...")

    orig = pd.read_csv(ARQUIVO_MELHOR_TRADES_ORIGINAL, compression="gzip")

    orig["DataHora_Sinal_SP"] = pd.to_datetime(orig["DataHora_Sinal_SP"], errors="coerce")
    trades_reproduzidos["DataHora_Sinal_SP"] = pd.to_datetime(
        trades_reproduzidos["DataHora_Sinal_SP"], errors="coerce"
    )

    orig_key = orig.copy()
    rep_key = trades_reproduzidos.copy()

    orig_key["key"] = orig_key["DataHora_Sinal_SP"].astype(str) + "|" + orig_key["Direcao"].astype(str)
    rep_key["key"] = rep_key["DataHora_Sinal_SP"].astype(str) + "|" + rep_key["Direcao"].astype(str)

    set_orig = set(orig_key["key"])
    set_rep = set(rep_key["key"])

    somente_original = sorted(list(set_orig - set_rep))
    somente_reproduzido = sorted(list(set_rep - set_orig))
    em_ambos = sorted(list(set_orig & set_rep))

    comparacao = pd.DataFrame([{
        "trades_original": len(orig),
        "trades_reproduzido": len(trades_reproduzidos),
        "em_ambos": len(em_ambos),
        "somente_original": len(somente_original),
        "somente_reproduzido": len(somente_reproduzido),
        "bate_100_porcento": len(somente_original) == 0 and len(somente_reproduzido) == 0,
    }])

    print("\nComparação original x reproduzido:")
    print(comparacao.T)

    if somente_original:
        print("\nPrimeiros trades que estão no original e não no reproduzido:")
        for item in somente_original[:10]:
            print(item)

    if somente_reproduzido:
        print("\nPrimeiros trades que estão no reproduzido e não no original:")
        for item in somente_reproduzido[:10]:
            print(item)

    return comparacao


# =====================================================
# MAIN
# =====================================================

def main():
    print("=====================================================")
    print("REPRODUZIR MELHOR V4")
    print("=====================================================")

    config = carregar_config_melhor()

    print("\nConfiguração carregada:")
    for k, v in config.items():
        print(f"{k}: {v}")

    cand = carregar_candidatos()

    trades = selecionar_trades(cand, config)

    resumo = calcular_resumo(trades, config)

    resumo_df = pd.DataFrame([resumo])

    print("\n=====================================================")
    print("RESUMO REPRODUZIDO")
    print("=====================================================")
    print(pd.Series(resumo))

    print("\n=====================================================")
    print("RESULTADOS PRINCIPAIS")
    print("=====================================================")
    print(f"Trades: {resumo['total_trades']}")
    print(f"Wins: {resumo['wins']}")
    print(f"Losses: {resumo['losses']}")
    print(f"Winrate: {resumo['winrate']:.2f}%")
    print(f"Lucro pontos: {resumo['lucro_pontos']:.2f}")
    print(f"Lucro 1 MNQ: US$ {resumo['lucro_usd_1_mnq']:.2f}")
    print(f"Profit Factor: {resumo['profit_factor']:.4f}")
    print(f"Pior dia pontos: {resumo['pior_dia_pontos']:.2f}")
    print(f"Pior dia 1 MNQ: US$ {resumo['pior_dia_usd_1_mnq']:.2f}")
    print(f"BUY: {resumo['buy_total']}")
    print(f"SELL: {resumo['sell_total']}")

    salvar_csv_seguro(trades, ARQUIVO_SAIDA_TRADES_REPRODUZIDOS, compactado=True)
    salvar_csv_seguro(resumo_df, ARQUIVO_SAIDA_RESUMO_REPRODUZIDO, compactado=False)

    comparacao = comparar_com_original(trades.copy())

    if not comparacao.empty:
        salvar_csv_seguro(comparacao, ARQUIVO_SAIDA_COMPARACAO, compactado=False)

    print("\n=====================================================")
    print("ARQUIVOS GERADOS")
    print("=====================================================")
    print(ARQUIVO_SAIDA_TRADES_REPRODUZIDOS)
    print(ARQUIVO_SAIDA_RESUMO_REPRODUZIDO)
    print(ARQUIVO_SAIDA_COMPARACAO)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()