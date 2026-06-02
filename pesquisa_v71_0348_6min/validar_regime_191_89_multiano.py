from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import (
    TAKE,
    STOP,
    preparar_candles,
    sinais_dmi3,
    simular_lista,
)
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RESUMO = SAIDA_DIR / "validacao_regime_191_89_multiano_resumo.csv"
ARQ_TRADES = SAIDA_DIR / "validacao_regime_191_89_multiano_trades.csv"


MODULOS = [
    ("REG_0346_SELL", "03:46", "SELL", lambda df: (df["dmi_gap"] >= 6) & (df["dist_vwap"] >= -7.26)),
    ("REG_0348_BUY", "03:48", "BUY", lambda df: (df["adx14"] >= 25) & (df["dmi_gap"] >= 3) & (df["ret_60"] <= 17.25)),
    ("REG_1030_BUY", "10:30", "BUY", lambda df: (df["adx14"] >= 30) & (df["ema200_slope10"] >= 5.67)),
    ("REG_1030_SELL", "10:30", "SELL", lambda df: (df["adx14"] >= 25) & (df["range_30"] <= 62.5)),
    ("REG_2052_BUY", "20:52", "BUY", lambda df: (df["adx14"] >= 25) & (df["range_30"] <= 18.44)),
    ("REG_2052_SELL_A", "20:52", "SELL", lambda df: (df["adx14"] >= 20) & (df["dmi_gap"] >= 10) & (df["ret_60"] >= -27.75)),
    ("REG_2052_SELL_B", "20:52", "SELL", lambda df: (df["adx14"] >= 30) & (df["ret_30"] >= -3.25)),
    ("REG_2058_BUY", "20:58", "BUY", lambda df: (df["dmi_gap"] >= 10) & (df["dmi_gap"] <= 13.35)),
]


def enriquecer_candles():
    df = preparar_candles()
    df["dist_vwap"] = df["close"] - df["vwap"]
    return df


def sinais_regime(candles):
    sinais = []
    for nome, hhmm, direcao, filtro in MODULOS:
        mask = candles["hhmm"].eq(hhmm)
        if direcao == "BUY":
            mask &= (candles["ema17"] >= candles["ema34"]) & (candles["di_plus"] >= candles["di_minus"])
        else:
            mask &= (candles["ema17"] < candles["ema34"]) & (candles["di_minus"] > candles["di_plus"])
        mask &= filtro(candles)
        for idx in candles.index[mask]:
            sinais.append((idx, nome, direcao, TAKE, STOP))
    return sinais


def linha_metricas(nome, trades, inicio=None, fim=None):
    base = trades.copy()
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {
            "periodo": nome,
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "dd": 0.0,
            "pf": 0.0,
            "dias": 0,
        }
    p = base["pontos"].astype(float)
    return {
        "periodo": nome,
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "dd": max_drawdown(p),
        "pf": profit_factor(p),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
    }


def main():
    candles = enriquecer_candles()
    cache = {}
    sinais = sinais_dmi3(candles) + sinais_regime(candles)
    trades = simular_lista(candles, sinais, cache)

    resumo = [
        linha_metricas("all", trades),
        linha_metricas("2024", trades, "2024-01-01", "2025-01-01"),
        linha_metricas("2025", trades, "2025-01-01", "2026-01-01"),
        linha_metricas("2026", trades, "2026-01-01", "2027-01-01"),
        linha_metricas("365d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=365)),
        linha_metricas("90d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=90)),
        linha_metricas("30d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=30)),
    ]
    resumo_df = pd.DataFrame(resumo)
    por_mes = trades.assign(mes=trades["datahora_entrada"].dt.to_period("M").astype(str)).groupby("mes").apply(
        lambda g: pd.Series(linha_metricas(g.name, g))
    ).reset_index(drop=True)
    por_modulo = trades.groupby("modulo").apply(lambda g: pd.Series(linha_metricas(g.name, g))).reset_index(drop=True)

    print("Resumo por periodo:")
    print(resumo_df.to_string(index=False))
    print("\nPiores meses:")
    print(por_mes.sort_values("pontos").head(12).to_string(index=False))
    print("\nPor modulo:")
    print(por_modulo.sort_values("pontos", ascending=False).to_string(index=False))

    resumo_out = pd.concat(
        [
            resumo_df.assign(tipo="periodo"),
            por_mes.assign(tipo="mes"),
            por_modulo.assign(tipo="modulo"),
        ],
        ignore_index=True,
    )
    resumo_out.to_csv(ARQ_RESUMO, index=False)
    trades.to_csv(ARQ_TRADES, index=False)
    print("\nArquivos:")
    print(ARQ_RESUMO)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
