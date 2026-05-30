from pathlib import Path

import pandas as pd

import testar_ema17_34_adx_horarios_3min as base


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

base.ARQ_XLSX = SAIDA_DIR / "teste_ema17_34_adx_horarios_2min.xlsx"
base.ARQ_RANKING = SAIDA_DIR / "teste_ema17_34_adx_horarios_2min_ranking.csv"
base.ARQ_TRADES = SAIDA_DIR / "teste_ema17_34_adx_horarios_2min_trades.csv"
base.ARQ_JANELAS = SAIDA_DIR / "teste_ema17_34_adx_horarios_2min_janelas.csv"


def resample_2min(df):
    out = df.set_index("DataHora_SP").resample(
        "2min",
        origin="start_day",
        label="left",
        closed="left",
    ).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"]).reset_index()
    out["Data"] = out["DataHora_SP"].dt.date
    out["ano"] = out["DataHora_SP"].dt.year
    out["mes"] = out["DataHora_SP"].dt.to_period("M").astype(str)
    out["hhmm"] = out["DataHora_SP"].dt.strftime("%H:%M")
    return out


base.resample_3min = resample_2min


if __name__ == "__main__":
    print("ATENCAO: rodando equivalencia em 2 minutos.")
    base.main()
