import pandas as pd

from buscar_seletor_diario_230_250 import metricas, preparar_sinais, montar_sinais_diarios
from buscar_v2_com_fallback_diario_230 import met_periodo, score, sinais_v2
from buscar_regime_dia_230_250 import preparar_candles, simular_lista


def configs_2058():
    for adx_min in [0, 15, 20, 25, 30]:
        for gap_min in [0, 3, 6, 10]:
            for forca_min in [0, 2, 4, 6, 8]:
                for usar_tendencia in [False, True]:
                    for usar_vwap in [False, True]:
                        for range_max in [None, 40, 60, 85]:
                            yield {
                                "nome": "FB2058",
                                "horarios": ["20:58"],
                                "modo": "primeiro",
                                "adx_min": adx_min,
                                "gap_min": gap_min,
                                "forca_min": forca_min,
                                "usar_tendencia": usar_tendencia,
                                "usar_vwap": usar_vwap,
                                "range_max": range_max,
                                "range_penal": 0.0,
                            }


def avaliar(candles, base_sinais, dias_base, cfg, cache):
    fallback = montar_sinais_diarios(candles, cfg)
    fallback = [s for s in fallback if candles.at[s[0], "DataHora_SP"].date() not in dias_base]
    trades = simular_lista(candles, base_sinais + fallback, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    row = {
        "horarios": ",".join(cfg["horarios"]),
        "adx_min": cfg["adx_min"],
        "gap_min": cfg["gap_min"],
        "forca_min": cfg["forca_min"],
        "usar_tendencia": cfg["usar_tendencia"],
        "usar_vwap": cfg["usar_vwap"],
        "range_max": cfg["range_max"] if cfg["range_max"] is not None else "",
        "fallback_brutos": len(fallback),
        "trades_365": m365["trades"],
        "dias_365": m365["dias"],
        "winrate_365": m365["winrate"],
        "pontos_365": m365["pontos"],
        "dd_365": m365["dd"],
        "pf_365": m365["pf"],
        "trades_90": m90["trades"],
        "winrate_90": m90["winrate"],
        "pontos_90": m90["pontos"],
        "trades_30": m30["trades"],
        "winrate_30": m30["winrate"],
        "pontos_30": m30["pontos"],
    }
    for ano in [2024, 2025, 2026]:
        m = met_periodo(trades, ano)
        row[f"trades_{ano}"] = m["trades"]
        row[f"winrate_{ano}"] = m["winrate"]
        row[f"pontos_{ano}"] = m["pontos"]
    row["score"] = score(row)
    return row, trades


def main():
    candles = preparar_sinais(preparar_candles())
    cache = {}
    base_sinais = sinais_v2(candles)
    base_trades = simular_lista(candles, base_sinais, cache)
    dias_base = set(base_trades["datahora_entrada"].dt.date) if not base_trades.empty else set()
    print("Base V2:", metricas(base_trades, 365), flush=True)

    linhas = []
    for cfg in configs_2058():
        row, _ = avaliar(candles, base_sinais, dias_base, cfg, cache)
        linhas.append(row)

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "horarios", "adx_min", "gap_min", "forca_min", "usar_tendencia", "usar_vwap", "range_max", "fallback_brutos",
        "trades_365", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "score",
    ]
    print("\nTop fallback 20:58 operavel:")
    print(ranking[cols].head(40).to_string(index=False), flush=True)

    alvo = ranking[
        ranking["trades_365"].between(220, 250)
        & (ranking["winrate_365"] >= 80)
        & (ranking["pontos_365"] > 0)
        & (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
    ]
    print("\nAlvo 220-250, >=80%, anos positivos:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
