from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import (
    TAKE,
    STOP,
    avaliar,
    metricas,
    preparar_candles,
    sinais_dmi3,
    simular_lista,
)


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA = BASE_DIR / "pesquisa_v71_0348_6min" / "validacao_regime_190_88_trades.csv"


MODULOS = [
    ("REG_0348_SELL", "03:48", "SELL", lambda df: (df["adx14"] >= 20) & (df["ema34_slope10"] >= -4.01)),
    ("REG_1030_BUY", "10:30", "BUY", lambda df: (df["adx14"] >= 30) & (df["ema200_slope10"] >= 5.67)),
    ("REG_1030_SELL", "10:30", "SELL", lambda df: (df["adx14"] >= 25) & (df["dmi_gap"] >= 3) & (df["ema200_slope10"] >= -10.26)),
    ("REG_2052_BUY", "20:52", "BUY", lambda df: (df["adx14"] >= 25) & (df["range_30"] <= 18.44)),
    ("REG_2052_SELL", "20:52", "SELL", lambda df: (df["adx14"] >= 20) & (df["dmi_gap"] >= 10) & (df["ret_60"] >= -27.75)),
    ("REG_2058_SELL", "20:58", "SELL", lambda df: (df["adx14"] >= 20) & (df["dmi_gap"] >= 10) & (df["adx14"] <= 25.10)),
]


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
    from simular_compilado_vencedoras import max_drawdown, profit_factor

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
    candles = preparar_candles()
    cache = {}
    sinais = sinais_dmi3(candles) + sinais_regime(candles)
    trades = simular_lista(candles, sinais, cache)
    resumo = []
    resumo.append(linha_metricas("all", trades))
    resumo.append(linha_metricas("2024", trades, "2024-01-01", "2025-01-01"))
    resumo.append(linha_metricas("2025", trades, "2025-01-01", "2026-01-01"))
    resumo.append(linha_metricas("2026", trades, "2026-01-01", "2027-01-01"))
    resumo.append(linha_metricas("365d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=365)))
    resumo.append(linha_metricas("90d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=90)))
    resumo.append(linha_metricas("30d", trades, trades["datahora_entrada"].max() - pd.Timedelta(days=30)))
    por_mes = trades.assign(mes=trades["datahora_entrada"].dt.to_period("M").astype(str)).groupby("mes").apply(
        lambda g: pd.Series(linha_metricas(g.name, g))
    ).reset_index(drop=True)
    por_modulo = trades.groupby("modulo").apply(lambda g: pd.Series(linha_metricas(g.name, g))).reset_index(drop=True)
    print("Resumo por periodo:")
    print(pd.DataFrame(resumo).to_string(index=False))
    print("\nPiores meses:")
    print(por_mes.sort_values("pontos").head(12).to_string(index=False))
    print("\nPor modulo:")
    print(por_modulo.sort_values("pontos", ascending=False).to_string(index=False))
    try:
        trades.to_csv(SAIDA, index=False)
        print("\nArquivo:", SAIDA)
    except PermissionError as exc:
        print("\nAVISO: nao consegui salvar CSV:", exc)


if __name__ == "__main__":
    main()
