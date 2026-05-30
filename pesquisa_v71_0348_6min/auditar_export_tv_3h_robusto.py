from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
DOWNLOADS = Path(r"C:\Users\ualac\Downloads")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_XLSX = SAIDA_DIR / "auditoria_export_tv_3h_robusto.xlsx"
ARQ_TRADES = SAIDA_DIR / "auditoria_export_tv_3h_robusto_trades.csv"
ARQ_RESUMO = SAIDA_DIR / "auditoria_export_tv_3h_robusto_resumo.csv"


def localizar_export():
    padroes = [
        "V71_Pesquisa_TV_3H_80pct_Robusto*.csv",
        "V71 Pesquisa TV 3H 80pct Robusto*.csv",
        "V71_Pesquisa_TV_3H_DMI3_Robusto*.csv",
        "V71 Pesquisa TV 3H DMI3 Robusto*.csv",
        "*3H*DMI3*Robusto*.csv",
        "*3H*80pct*Robusto*.csv",
    ]
    encontrados = []
    for padrao in padroes:
        encontrados.extend(DOWNLOADS.glob(padrao))
    if not encontrados:
        raise FileNotFoundError(
            "Nao encontrei export CSV do TradingView para o Pine 3H robusto em Downloads. "
            "Exporte a Lista de negociacoes do TV em CSV e rode novamente."
        )
    return max(encontrados, key=lambda p: p.stat().st_mtime)


def max_drawdown(pnl):
    eq = pnl.astype(float).cumsum()
    if eq.empty:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pnl):
    ganhos = float(pnl[pnl > 0].sum())
    perdas = abs(float(pnl[pnl < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def resumir(df, nome):
    if df.empty:
        return {
            "janela": nome,
            "trades": 0,
            "takes": 0,
            "stops": 0,
            "winrate": 0.0,
            "pnl_usd": 0.0,
            "max_drawdown_usd": 0.0,
            "profit_factor": 0.0,
        }
    pnl = df["pnl"].astype(float)
    return {
        "janela": nome,
        "trades": int(len(df)),
        "takes": int((pnl > 0).sum()),
        "stops": int((pnl < 0).sum()),
        "winrate": float((pnl > 0).mean() * 100),
        "pnl_usd": float(pnl.sum()),
        "max_drawdown_usd": max_drawdown(pnl),
        "profit_factor": profit_factor(pnl),
    }


def consolidar(csv_path):
    df = pd.read_csv(csv_path)
    entradas = df[df["Tipo"].astype(str).str.contains("Entrada", na=False)].copy()
    entradas["Data e hora"] = pd.to_datetime(entradas["Data e hora"], errors="coerce")
    entradas = entradas.dropna(subset=["Data e hora"]).sort_values("Trade number")
    entradas["pnl"] = pd.to_numeric(entradas["Net PnL USD"], errors="coerce")
    entradas["direcao"] = entradas["Tipo"].str.extract(r"Entrada (long|short)", expand=False).map(
        {"long": "BUY", "short": "SELL"}
    )
    entradas["resultado"] = np.where(entradas["pnl"] > 0, "TAKE", "STOP")
    entradas["hhmm_execucao"] = entradas["Data e hora"].dt.strftime("%H:%M")
    entradas["dia_semana"] = entradas["Data e hora"].dt.day_name()
    entradas["mes"] = entradas["Data e hora"].dt.to_period("M").astype(str)
    return entradas


def main():
    csv_path = localizar_export()
    trades = consolidar(csv_path)
    fim = trades["Data e hora"].max()
    resumo = pd.DataFrame(
        [
            resumir(trades, "365d_export"),
            resumir(trades[trades["Data e hora"] >= fim - pd.Timedelta(days=90)], "90d_export"),
            resumir(trades[trades["Data e hora"] >= fim - pd.Timedelta(days=30)], "30d_export"),
        ]
    )
    por_horario = (
        trades.groupby(["hhmm_execucao", "direcao"], dropna=False)
        .apply(lambda g: pd.Series(resumir(g, "grupo")))
        .reset_index()
    )
    por_mes = (
        trades.groupby("mes", dropna=False)
        .apply(lambda g: pd.Series(resumir(g, "mes")))
        .reset_index()
    )

    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        por_horario.to_excel(writer, sheet_name="por_horario", index=False)
        por_mes.to_excel(writer, sheet_name="por_mes", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    print("Export analisado:", csv_path)
    print(resumo.to_string(index=False))
    print("Arquivos:")
    print(ARQ_XLSX)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)


if __name__ == "__main__":
    main()
