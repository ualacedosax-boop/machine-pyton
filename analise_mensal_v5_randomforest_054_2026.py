# -*- coding: utf-8 -*-

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ_PRED = BASE_DIR / "saida_v5_treino_2024_2025_teste_2026" / "02_predicoes_v5_2026.csv.gz"
PASTA_SAIDA = BASE_DIR / "saida_v5_treino_2024_2025_teste_2026"

ARQ_MENSAL = PASTA_SAIDA / "04_analise_mensal_v5_randomforest_054_2026.csv"
ARQ_MENSAL_DIR = PASTA_SAIDA / "05_analise_mensal_direcao_v5_randomforest_054_2026.csv"

THRESHOLD = 0.54
MODELO = "RandomForest"

def resumo(df, grupo, valor):
    if df.empty:
        return {
            "grupo": grupo,
            "valor": valor,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "lucro_pontos": 0,
            "profit_factor": 0,
            "drawdown_trades": 0,
            "buy_total": 0,
            "sell_total": 0,
        }

    total = len(df)
    wins = int((df["target_v5_win"] == 1).sum())
    losses = int((df["target_v5_win"] == 0).sum())
    lucro = float(df["pontos_v5"].sum())

    ganhos = df.loc[df["pontos_v5"] > 0, "pontos_v5"].sum()
    perdas = abs(df.loc[df["pontos_v5"] < 0, "pontos_v5"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    equity = df["pontos_v5"].cumsum()
    dd = float((equity - equity.cummax()).min()) if len(equity) else 0.0

    return {
        "grupo": grupo,
        "valor": valor,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "drawdown_trades": dd,
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
    }

def main():
    print("=====================================================")
    print("ANALISE MENSAL - V5 RANDOMFOREST 0.54 - 2026")
    print("=====================================================")

    df = pd.read_csv(ARQ_PRED, compression="gzip")
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

    df = df[(df["modelo_v5"] == MODELO) & (df["prob_v5"] >= THRESHOLD)].copy()
    df["AnoMes"] = df["DataHora_SP"].dt.strftime("%Y-%m")

    geral = resumo(df, "GERAL", "2026")
    print("\nRESUMO GERAL")
    print(pd.Series(geral).to_string())

    linhas = []
    for mes, g in df.groupby("AnoMes", sort=True):
        linhas.append(resumo(g, "Mes", mes))

    mensal = pd.DataFrame(linhas)

    mensal["lucro_acumulado"] = mensal["lucro_pontos"].cumsum()

    print("\nANALISE MENSAL")
    print(mensal.to_string(index=False))

    mensal.to_csv(ARQ_MENSAL, index=False)

    linhas_dir = []
    for (mes, direcao), g in df.groupby(["AnoMes", "Direcao"], sort=True):
        linhas_dir.append(resumo(g, "Mes_Direcao", f"{mes}_{direcao}"))

    mensal_dir = pd.DataFrame(linhas_dir)
    mensal_dir.to_csv(ARQ_MENSAL_DIR, index=False)

    meses_pos = int((mensal["lucro_pontos"] > 0).sum())
    meses_neg = int((mensal["lucro_pontos"] < 0).sum())

    print("\nDIAGNOSTICO")
    print("Meses positivos:", meses_pos)
    print("Meses negativos:", meses_neg)
    print("Lucro total:", mensal["lucro_pontos"].sum())
    print("Melhor mes:")
    print(mensal.sort_values("lucro_pontos", ascending=False).head(1).to_string(index=False))
    print("Pior mes:")
    print(mensal.sort_values("lucro_pontos", ascending=True).head(1).to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_MENSAL)
    print(ARQ_MENSAL_DIR)

if __name__ == "__main__":
    main()
