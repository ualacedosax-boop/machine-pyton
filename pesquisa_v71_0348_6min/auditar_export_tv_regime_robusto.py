from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
DOWNLOADS = Path(r"C:\Users\ualac\Downloads")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_XLSX = SAIDA_DIR / "auditoria_export_tv_regime_robusto.xlsx"
ARQ_TRADES = SAIDA_DIR / "auditoria_export_tv_regime_robusto_trades.csv"
ARQ_RESUMO = SAIDA_DIR / "auditoria_export_tv_regime_robusto_resumo.csv"


def localizar_export():
    padroes = [
        "V71_Pesquisa_Regime_Robusto_191_89*.csv",
        "V71 Pesquisa Regime Robusto 191 89*.csv",
        "*Regime*Robusto*191*89*.csv",
        "*V71*Regime*Robusto*.csv",
    ]
    encontrados = []
    for padrao in padroes:
        encontrados.extend(DOWNLOADS.glob(padrao))
    if not encontrados:
        raise FileNotFoundError(
            "Nao encontrei export CSV do TradingView para o Regime Robusto em Downloads. "
            "Exporte a aba Lista de negociacoes do TV em CSV e rode novamente."
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


def resumir(df, janela, grupo="TOTAL"):
    if df.empty:
        return {
            "janela": janela,
            "grupo": grupo,
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
        "janela": janela,
        "grupo": grupo,
        "trades": int(len(df)),
        "takes": int((pnl > 0).sum()),
        "stops": int((pnl < 0).sum()),
        "winrate": float((pnl > 0).mean() * 100),
        "pnl_usd": float(pnl.sum()),
        "max_drawdown_usd": max_drawdown(pnl),
        "profit_factor": profit_factor(pnl),
    }


def normalizar_modulo(sinal):
    s = str(sinal).upper()
    mapa = {
        "D3B0348": "DMI3_0348_BUY",
        "D3B1030": "DMI3_1030_BUY",
        "D3B2058": "DMI3_2058_BUY",
        "D3S1030": "DMI3_1030_SELL",
        "R0346S": "REG_0346_SELL",
        "R0348B": "REG_0348_BUY",
        "R1030B": "REG_1030_BUY",
        "R1030S": "REG_1030_SELL",
        "R2052B": "REG_2052_BUY",
        "R2052SA": "REG_2052_SELL_A",
        "R2052SB": "REG_2052_SELL_B",
        "R2058B": "REG_2058_BUY",
    }
    for chave, modulo in mapa.items():
        if chave in s:
            return modulo
    if "BUY" in s:
        return "OUTRO_BUY"
    if "SELL" in s:
        return "OUTRO_SELL"
    return "OUTRO"


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
    entradas["modulo"] = entradas["Sinal"].map(normalizar_modulo)
    entradas["hhmm_execucao"] = entradas["Data e hora"].dt.strftime("%H:%M")
    entradas["dia_semana"] = entradas["Data e hora"].dt.day_name()
    entradas["mes"] = entradas["Data e hora"].dt.to_period("M").astype(str)
    return entradas


def montar_resumo(trades):
    fim = trades["Data e hora"].max()
    linhas = []
    janelas = [
        ("all", trades),
        ("365d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=365)]),
        ("90d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=90)]),
        ("30d", trades[trades["Data e hora"] >= fim - pd.Timedelta(days=30)]),
    ]
    for janela, base in janelas:
        linhas.append(resumir(base, janela))
        for modulo, grupo in base.groupby("modulo", dropna=False):
            linhas.append(resumir(grupo, janela, f"modulo={modulo}"))
        for hhmm, grupo in base.groupby("hhmm_execucao", dropna=False):
            linhas.append(resumir(grupo, janela, f"hora={hhmm}"))
        for mes, grupo in base.groupby("mes", dropna=False):
            if janela == "all":
                linhas.append(resumir(grupo, "mes", f"mes={mes}"))
    return pd.DataFrame(linhas)


def main():
    csv_path = localizar_export()
    trades = consolidar(csv_path)
    resumo = montar_resumo(trades)

    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    print("Export analisado:", csv_path)
    print(resumo.to_string(index=False))
    print("Arquivos:")
    print(ARQ_XLSX)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)


if __name__ == "__main__":
    main()
