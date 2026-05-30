from pathlib import Path
import sys

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
DOWNLOADS = Path(r"C:\Users\ualac\Downloads")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_XLSX = SAIDA_DIR / "auditoria_export_tv_alta_acertividade_calendario.xlsx"
ARQ_RESUMO = SAIDA_DIR / "auditoria_export_tv_alta_acertividade_calendario_resumo.csv"
ARQ_TRADES = SAIDA_DIR / "auditoria_export_tv_alta_acertividade_calendario_trades.csv"


def encontrar_csv(caminho_arg=None):
    if caminho_arg:
        p = Path(caminho_arg)
        if p.exists():
            return p
        raise FileNotFoundError(f"CSV informado nao existe: {p}")

    padroes = [
        "V71_Pesquisa_TV_Alta_Acertividade_Calendario*.csv",
        "V71 Pesquisa TV Alta Acertividade Calendario*.csv",
        "*Alta*Acertividade*Calendario*.csv",
    ]
    candidatos = []
    for padrao in padroes:
        candidatos.extend(DOWNLOADS.glob(padrao))
    candidatos = sorted(set(candidatos), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise FileNotFoundError(
            "Nao encontrei export CSV do Pine de alta acertividade no Downloads. "
            "Informe o caminho como argumento."
        )
    return candidatos[0]


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


def consolidar(csv_path):
    df = pd.read_csv(csv_path)
    entradas = df[df["Tipo"].astype(str).str.contains("Entrada", na=False)].copy()
    entradas["Data e hora"] = pd.to_datetime(entradas["Data e hora"], errors="coerce")
    entradas = entradas.dropna(subset=["Data e hora"]).sort_values("Trade number")
    entradas["pnl"] = pd.to_numeric(entradas["Net PnL USD"], errors="coerce").fillna(0.0)
    entradas["direcao"] = entradas["Tipo"].str.extract(r"Entrada (long|short)", expand=False).map({
        "long": "BUY",
        "short": "SELL",
    })
    entradas["hhmm_execucao"] = entradas["Data e hora"].dt.strftime("%H:%M")
    entradas["dow"] = entradas["Data e hora"].dt.day_name()
    entradas["resultado"] = np.where(entradas["pnl"] > 0, "TAKE", "STOP")
    entradas["mes"] = entradas["Data e hora"].dt.to_period("M").astype(str)
    return entradas


def resumir(g, grupo):
    p = g["pnl"].astype(float)
    mensal = g.groupby("mes")["pnl"].sum()
    return {
        "grupo": grupo,
        "trades": int(len(g)),
        "wins": int((p > 0).sum()),
        "losses": int((p < 0).sum()),
        "winrate": float((p > 0).mean() * 100) if len(p) else 0.0,
        "pnl_usd": float(p.sum()),
        "max_drawdown_usd": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "meses_negativos": int((mensal < 0).sum()) if len(mensal) else 0,
        "pior_mes_usd": float(mensal.min()) if len(mensal) else 0.0,
    }


def auditar(trades):
    linhas = [resumir(trades, "TOTAL")]
    for hhmm, g in trades.groupby("hhmm_execucao"):
        linhas.append(resumir(g, f"execucao={hhmm}"))
    for dow, g in trades.groupby("dow"):
        linhas.append(resumir(g, f"dow={dow}"))
    for (hhmm, dow), g in trades.groupby(["hhmm_execucao", "dow"]):
        linhas.append(resumir(g, f"execucao={hhmm}|dow={dow}"))
    for mes, g in trades.groupby("mes"):
        linhas.append(resumir(g, f"mes={mes}"))
    return pd.DataFrame(linhas)


def main():
    csv_path = encontrar_csv(sys.argv[1] if len(sys.argv) > 1 else None)
    print("=====================================================")
    print("AUDITORIA EXPORT TV - ALTA ACERTIVIDADE CALENDARIO")
    print("=====================================================")
    print("CSV:", csv_path)

    trades = consolidar(csv_path)
    resumo = auditar(trades)
    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    cols = ["grupo", "trades", "winrate", "pnl_usd", "max_drawdown_usd", "profit_factor", "meses_negativos"]
    print("\nResumo principal:")
    print(resumo[resumo["grupo"].isin(["TOTAL"])][cols].to_string(index=False))
    print("\nPor execucao/dia:")
    print(
        resumo[resumo["grupo"].str.contains("execucao=.*dow=", regex=True)][cols]
        .sort_values("pnl_usd")
        .to_string(index=False)
    )
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RESUMO)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
