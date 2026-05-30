from datetime import datetime
from itertools import combinations
from pathlib import Path

import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
ENTRADA = BASE_DIR / "pesquisa_v71_0348_6min" / "auditoria_tv_3_horarios_trades_consolidados.csv"
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
SAIDA_CSV = SAIDA_DIR / "busca_tv_calendario_robusto_ranking.csv"
SAIDA_XLSX = SAIDA_DIR / "busca_tv_calendario_robusto.xlsx"


def max_drawdown(pontos):
    equity = pontos.astype(float).cumsum()
    if equity.empty:
        return 0.0
    return float((equity - equity.cummax()).min())


def profit_factor(pontos):
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def metricas(df):
    if df.empty:
        return {
            "trades": 0,
            "winrate": 0.0,
            "pnl_usd": 0.0,
            "max_drawdown_usd": 0.0,
            "profit_factor": 0.0,
        }

    pnl = df["pnl"].astype(float)
    return {
        "trades": int(len(df)),
        "winrate": float((pnl > 0).mean() * 100),
        "pnl_usd": float(pnl.sum()),
        "max_drawdown_usd": max_drawdown(pnl),
        "profit_factor": profit_factor(pnl),
    }


def avaliar(df, tokens, fim):
    mascara = df["token"].isin(tokens)
    base = df[mascara].copy()
    base_90 = df[mascara & (df["Data e hora"] >= fim - pd.Timedelta(days=90))].copy()
    base_30 = df[mascara & (df["Data e hora"] >= fim - pd.Timedelta(days=30))].copy()

    m365 = metricas(base)
    m90 = metricas(base_90)
    m30 = metricas(base_30)

    linha = {
        "tokens": " ; ".join(tokens),
        "qtd_tokens": len(tokens),
    }
    for prefixo, met in [("d365", m365), ("d90", m90), ("d30", m30)]:
        for chave, valor in met.items():
            linha[f"{prefixo}_{chave}"] = valor
    return linha


def main():
    df = pd.read_csv(ENTRADA, parse_dates=["Data e hora"])
    df["dow"] = df["Data e hora"].dt.day_name()
    df["token"] = df["horario_sinal"] + "|" + df["direcao"] + "|" + df["dow"]
    fim = df["Data e hora"].max()

    token_stats = df.groupby("token")["pnl"].agg(["size", "sum"]).reset_index()
    candidatos_token = token_stats[(token_stats["size"] >= 5) & (token_stats["sum"] > 0)]["token"].tolist()

    linhas = []
    for tamanho in range(1, len(candidatos_token) + 1):
        for tokens in combinations(candidatos_token, tamanho):
            linha = avaliar(df, tokens, fim)
            if linha["d365_trades"] < 50:
                continue
            if linha["d365_pnl_usd"] <= 0 or linha["d90_pnl_usd"] <= 0 or linha["d30_pnl_usd"] <= 0:
                continue
            linhas.append(linha)

    ranking = pd.DataFrame(linhas)
    ranking["score_robustez"] = (
        ranking["d365_pnl_usd"] / 1000
        + ranking["d365_winrate"] / 10
        + ranking["d90_winrate"] / 20
        + ranking["d30_winrate"] / 20
        + ranking["d365_profit_factor"]
        + ranking["d365_max_drawdown_usd"] / 1000
    )
    ranking = ranking.sort_values(
        ["d365_winrate", "d90_winrate", "d30_winrate", "d365_pnl_usd"],
        ascending=[False, False, False, False],
    )

    saida_csv = SAIDA_CSV
    saida_xlsx = SAIDA_XLSX
    try:
        ranking.to_csv(saida_csv, index=False)
    except PermissionError:
        sufixo = datetime.now().strftime("%Y%m%d_%H%M%S")
        saida_csv = SAIDA_DIR / f"busca_tv_calendario_robusto_ranking_{sufixo}.csv"
        ranking.to_csv(saida_csv, index=False)

    try:
        writer = pd.ExcelWriter(saida_xlsx, engine="openpyxl")
    except PermissionError:
        sufixo = datetime.now().strftime("%Y%m%d_%H%M%S")
        saida_xlsx = SAIDA_DIR / f"busca_tv_calendario_robusto_{sufixo}.xlsx"
        writer = pd.ExcelWriter(saida_xlsx, engine="openpyxl")

    with writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        token_stats.to_excel(writer, sheet_name="tokens", index=False)

    print("Ranking salvo em:")
    print(saida_csv)
    print(saida_xlsx)
    print()
    cols = [
        "d365_trades",
        "d365_winrate",
        "d365_pnl_usd",
        "d365_max_drawdown_usd",
        "d365_profit_factor",
        "d90_trades",
        "d90_winrate",
        "d90_pnl_usd",
        "d30_trades",
        "d30_winrate",
        "d30_pnl_usd",
        "tokens",
    ]
    print(ranking[cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
