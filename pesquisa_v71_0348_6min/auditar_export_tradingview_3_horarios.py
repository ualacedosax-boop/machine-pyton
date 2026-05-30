from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
CSV_TV = Path(r"C:\Users\ualac\Downloads\V71_Pesquisa_3_Horarios_Fixos_Multi_Indicadores_CME_MINI_MNQ1!_2026-05-30.csv")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_XLSX = SAIDA_DIR / "auditoria_tv_3_horarios_multi_indicadores.xlsx"
ARQ_TRADES = SAIDA_DIR / "auditoria_tv_3_horarios_trades_consolidados.csv"
ARQ_RESUMO = SAIDA_DIR / "auditoria_tv_3_horarios_resumo.csv"


def max_drawdown(pontos):
    eq = pontos.astype(float).cumsum()
    if len(eq) == 0:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pontos):
    p = pontos.astype(float)
    ganhos = float(p[p > 0].sum())
    perdas = abs(float(p[p < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def resumir(g, grupo):
    if g.empty:
        return {}
    p = g["pnl"].astype(float)
    return {
        "grupo": grupo,
        "trades": int(len(g)),
        "wins": int((p > 0).sum()),
        "losses": int((p < 0).sum()),
        "winrate": float((p > 0).mean() * 100),
        "pnl_usd": float(p.sum()),
        "max_drawdown_usd": max_drawdown(p),
        "profit_factor": profit_factor(p),
    }


def consolidar_trades():
    df = pd.read_csv(CSV_TV)
    entradas = df[df["Tipo"].astype(str).str.contains("Entrada", na=False)].copy()
    entradas["Data e hora"] = pd.to_datetime(entradas["Data e hora"], errors="coerce")
    entradas = entradas.dropna(subset=["Data e hora"]).sort_values("Trade number")
    entradas["pnl"] = pd.to_numeric(entradas["Net PnL USD"], errors="coerce")
    entradas["direcao"] = entradas["Tipo"].str.extract(r"Entrada (long|short)", expand=False).map({
        "long": "BUY",
        "short": "SELL",
    })
    entradas["hhmm_execucao"] = entradas["Data e hora"].dt.strftime("%H:%M")
    mapa = {
        "03:50": "03:48",
        "10:32": "10:30",
        "21:00": "20:58",
    }
    entradas["horario_sinal"] = entradas["hhmm_execucao"].map(mapa).fillna(entradas["hhmm_execucao"])
    entradas["resultado"] = np.where(entradas["pnl"] > 0, "TAKE", "STOP")
    entradas["data"] = entradas["Data e hora"].dt.date
    entradas["mes"] = entradas["Data e hora"].dt.to_period("M").astype(str)
    return entradas


def montar_resumos(trades):
    fim = trades["Data e hora"].max()
    linhas = []
    for janela in ["total", "365d", "90d", "30d"]:
        if janela == "total":
            base = trades.copy()
        else:
            dias = int(janela.replace("d", ""))
            base = trades[trades["Data e hora"] >= fim - pd.Timedelta(days=dias)].copy()

        linhas.append({"janela": janela, **resumir(base, "TOTAL")})
        for horario, g in base.groupby("horario_sinal"):
            linhas.append({"janela": janela, **resumir(g, f"horario={horario}")})
        for (horario, direcao), g in base.groupby(["horario_sinal", "direcao"]):
            linhas.append({"janela": janela, **resumir(g, f"horario={horario}|direcao={direcao}")})
        for direcao, g in base.groupby("direcao"):
            linhas.append({"janela": janela, **resumir(g, f"direcao={direcao}")})

    resumo = pd.DataFrame(linhas)
    return resumo


def main():
    print("=====================================================")
    print("AUDITORIA EXPORT TRADINGVIEW - 3 HORARIOS")
    print("=====================================================")
    trades = consolidar_trades()
    resumo = montar_resumos(trades)
    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)

    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        trades.to_excel(writer, sheet_name="trades_consolidados", index=False)

    print("Periodo:", trades["Data e hora"].min(), "ate", trades["Data e hora"].max())
    print("Trades:", len(trades))
    cols = ["janela", "grupo", "trades", "winrate", "pnl_usd", "max_drawdown_usd", "profit_factor"]
    for janela in ["365d", "90d", "30d"]:
        print(f"\n=== {janela} ===")
        r = resumo[(resumo["janela"] == janela) & resumo["grupo"].str.startswith("horario=")]
        print(r[cols].sort_values("pnl_usd").to_string(index=False))
    print("\n=== 365d por horario/direcao ===")
    r = resumo[(resumo["janela"] == "365d") & resumo["grupo"].str.contains("direcao=")]
    print(r[cols].sort_values("pnl_usd").to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)


if __name__ == "__main__":
    main()
