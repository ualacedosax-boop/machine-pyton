from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CAMINHOS
# ============================================================

PASTA_BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQUIVO_TRADES = (
    PASTA_BASE
    / "saida_ml_entradas_video_v4_antiloss_otimizacao_A"
    / "08_v4_A_melhor_trades.csv.gz"
)

PASTA_SAIDA = PASTA_BASE / "analise_v4_A_melhor_trades"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQUIVO_EXCEL = PASTA_SAIDA / "analise_v4_A_melhor_trades.xlsx"


# ============================================================
# FUNÇÕES
# ============================================================

def carregar_trades():
    if not ARQUIVO_TRADES.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_TRADES}")

    df = pd.read_csv(ARQUIVO_TRADES, compression="gzip")

    print("Colunas encontradas:")
    print(df.columns.tolist())

    # Data/hora
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    elif "DataHora_SP" in df.columns:
        df["dt"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    elif "dt_entrada_stop_117_0" in df.columns:
        df["dt"] = pd.to_datetime(df["dt_entrada_stop_117_0"], errors="coerce")
    else:
        raise ValueError("Não encontrei coluna de data/hora.")

    df = df.dropna(subset=["dt"]).copy()

    # Resultado
    if "resultado_sim" not in df.columns:
        if "resultado_stop_117_0" in df.columns:
            df["resultado_sim"] = df["resultado_stop_117_0"].astype(str).str.upper().str.strip()
        else:
            raise ValueError("Não encontrei coluna resultado_sim ou resultado_stop_117_0.")

    df["resultado_sim"] = df["resultado_sim"].astype(str).str.upper().str.strip()

    # Pontos
    if "pontos_sim" not in df.columns:
        if "pontos_stop_117_0" in df.columns:
            df["pontos_sim"] = pd.to_numeric(df["pontos_stop_117_0"], errors="coerce")
        else:
            raise ValueError("Não encontrei coluna pontos_sim ou pontos_stop_117_0.")

    df["pontos_sim"] = pd.to_numeric(df["pontos_sim"], errors="coerce").fillna(0.0)

    # Direção
    df["Direcao"] = df["Direcao"].astype(str).str.upper().str.strip()

    # Datas e horários
    df["Data"] = df["dt"].dt.date
    df["Hora"] = df["dt"].dt.hour
    df["Minuto"] = df["dt"].dt.minute
    df["Hora_Minuto"] = df["dt"].dt.strftime("%H:%M")

    df["Bloco_15m"] = (
        df["dt"].dt.hour.astype(str).str.zfill(2)
        + ":"
        + ((df["dt"].dt.minute // 15) * 15).astype(str).str.zfill(2)
    )

    df["DiaSemana_Num"] = df["dt"].dt.dayofweek
    df["DiaSemana"] = df["DiaSemana_Num"].map({
        0: "Segunda",
        1: "Terça",
        2: "Quarta",
        3: "Quinta",
        4: "Sexta",
        5: "Sábado",
        6: "Domingo",
    })

    df["eh_win"] = df["resultado_sim"].isin(["WIN", "GAIN", "TAKE", "TP"])
    df["eh_loss"] = df["resultado_sim"].isin(["LOSS", "STOP", "SL"])

    # Prob e scores
    for col in ["prob_win_v4", "score_BUY", "score_SELL", "score_direcao", "score_oposto", "score_diff"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Runup/drawdown
    if "runup" not in df.columns and "runup_stop_117_0" in df.columns:
        df["runup"] = df["runup_stop_117_0"]

    if "drawdown" not in df.columns and "drawdown_stop_117_0" in df.columns:
        df["drawdown"] = df["drawdown_stop_117_0"]

    for col in ["runup", "drawdown"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("dt").reset_index(drop=True)

    return df


def resumir_grupo(df, grupo):
    g = df.groupby(grupo, dropna=False)

    resumo = g.agg(
        trades=("pontos_sim", "count"),
        wins=("eh_win", "sum"),
        losses=("eh_loss", "sum"),
        lucro=("pontos_sim", "sum"),
        media_pontos=("pontos_sim", "mean"),
        pior_trade=("pontos_sim", "min"),
        melhor_trade=("pontos_sim", "max"),
        media_prob=("prob_win_v4", "mean") if "prob_win_v4" in df.columns else ("pontos_sim", "count"),
        min_prob=("prob_win_v4", "min") if "prob_win_v4" in df.columns else ("pontos_sim", "count"),
    ).reset_index()

    resumo["winrate"] = np.where(
        resumo["trades"] > 0,
        resumo["wins"] / resumo["trades"] * 100.0,
        0.0
    )

    # Profit factor por grupo
    pf_lista = []
    for _, sub in g:
        gains = sub.loc[sub["pontos_sim"] > 0, "pontos_sim"].sum()
        losses = abs(sub.loc[sub["pontos_sim"] < 0, "pontos_sim"].sum())
        pf = gains / losses if losses > 0 else 999.0
        pf_lista.append(pf)

    resumo["profit_factor"] = pf_lista

    resumo = resumo.sort_values(
        ["lucro", "profit_factor", "winrate", "trades"],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)

    return resumo


def resumo_geral(df):
    total = len(df)
    wins = int(df["eh_win"].sum())
    losses = int(df["eh_loss"].sum())
    lucro = float(df["pontos_sim"].sum())

    ganhos = df.loc[df["pontos_sim"] > 0, "pontos_sim"].sum()
    perdas = abs(df.loc[df["pontos_sim"] < 0, "pontos_sim"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    por_dia = df.groupby("Data")["pontos_sim"].sum()

    return pd.DataFrame([{
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total > 0 else 0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "dias_operados": df["Data"].nunique(),
        "media_trades_dia": total / df["Data"].nunique() if df["Data"].nunique() > 0 else 0,
        "pior_dia": por_dia.min(),
        "melhor_dia": por_dia.max(),
        "media_dia": por_dia.mean(),
        "drawdown_medio_trade": df["drawdown"].mean() if "drawdown" in df.columns else np.nan,
        "drawdown_max_trade": df["drawdown"].max() if "drawdown" in df.columns else np.nan,
        "runup_medio_trade": df["runup"].mean() if "runup" in df.columns else np.nan,
        "runup_max_trade": df["runup"].max() if "runup" in df.columns else np.nan,
    }])


def analisar_ordem_trade_dia(df):
    df = df.copy()
    df["ordem_trade_dia"] = df.groupby("Data").cumcount() + 1

    return resumir_grupo(df, "ordem_trade_dia")


def simular_max_trades(df, max_trades):
    trades = []

    for data, grupo in df.groupby("Data", sort=True):
        grupo = grupo.sort_values("dt").head(max_trades)
        trades.append(grupo)

    if not trades:
        return pd.DataFrame()

    sim = pd.concat(trades, ignore_index=True)
    return sim


def comparar_max_trades(df):
    linhas = []

    for max_trades in [1, 2, 3]:
        sim = simular_max_trades(df, max_trades)
        rg = resumo_geral(sim).iloc[0].to_dict()
        rg["max_trades_dia_simulado"] = max_trades
        linhas.append(rg)

    return pd.DataFrame(linhas)[[
        "max_trades_dia_simulado",
        "trades",
        "wins",
        "losses",
        "winrate",
        "lucro_pontos",
        "profit_factor",
        "dias_operados",
        "pior_dia",
        "melhor_dia",
        "media_dia",
    ]]


def analisar_losses(df):
    losses = df[df["eh_loss"]].copy()

    cols = [
        "dt",
        "Data",
        "Hora_Minuto",
        "Bloco_15m",
        "Direcao",
        "pontos_sim",
        "prob_win_v4",
        "score_BUY",
        "score_SELL",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "runup",
        "drawdown",
        "open",
        "high",
        "low",
        "close",
    ]

    cols = [c for c in cols if c in losses.columns]

    return losses[cols].sort_values("dt").reset_index(drop=True)


def analisar_gains(df):
    gains = df[df["eh_win"]].copy()

    cols = [
        "dt",
        "Data",
        "Hora_Minuto",
        "Bloco_15m",
        "Direcao",
        "pontos_sim",
        "prob_win_v4",
        "score_BUY",
        "score_SELL",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "runup",
        "drawdown",
        "open",
        "high",
        "low",
        "close",
    ]

    cols = [c for c in cols if c in gains.columns]

    return gains[cols].sort_values("dt").reset_index(drop=True)


def salvar_excel(abas):
    with pd.ExcelWriter(ARQUIVO_EXCEL, engine="openpyxl") as writer:
        for nome, df in abas.items():
            df.to_excel(writer, sheet_name=nome[:31], index=False)

    print("\nArquivo Excel gerado:")
    print(ARQUIVO_EXCEL)


def main():
    df = carregar_trades()

    print("\nResumo geral:")
    print(resumo_geral(df).to_string(index=False))

    abas = {
        "Resumo": resumo_geral(df),
        "Por Hora": resumir_grupo(df, "Hora"),
        "Por Bloco 15m": resumir_grupo(df, "Bloco_15m"),
        "Por Direcao": resumir_grupo(df, "Direcao"),
        "Hora x Direcao": resumir_grupo(df, ["Hora", "Direcao"]),
        "Bloco15 x Direcao": resumir_grupo(df, ["Bloco_15m", "Direcao"]),
        "Por Dia Semana": resumir_grupo(df, "DiaSemana"),
        "Ordem Trade Dia": analisar_ordem_trade_dia(df),
        "Comparar Max Trades Dia": comparar_max_trades(df),
        "Losses": analisar_losses(df),
        "Gains": analisar_gains(df),
        "Trades": df,
    }

    print("\nPor hora:")
    print(abas["Por Hora"].to_string(index=False))

    print("\nPor bloco de 15 minutos:")
    print(abas["Por Bloco 15m"].to_string(index=False))

    print("\nPor direção:")
    print(abas["Por Direcao"].to_string(index=False))

    print("\nComparar max trades por dia:")
    print(abas["Comparar Max Trades Dia"].to_string(index=False))

    salvar_excel(abas)


if __name__ == "__main__":
    main()