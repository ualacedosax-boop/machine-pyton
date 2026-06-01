from pathlib import Path

import pandas as pd

from auditar_modulos_regime_robusto import MODULOS, sinais_modulo
from buscar_regime_dia_230_250 import preparar_candles, sinais_dmi3, simular_lista
from buscar_seletor_diario_230_250 import gerar_configs, metricas, montar_sinais_diarios, preparar_sinais
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
REMOVIDOS_V2 = {"REG_1030_BUY", "REG_2052_SELL_B"}
MAX_CONFIGS = 900


def met_periodo(trades, ano):
    base = trades[
        (trades["datahora_entrada"] >= pd.Timestamp(f"{ano}-01-01"))
        & (trades["datahora_entrada"] < pd.Timestamp(f"{ano + 1}-01-01"))
    ]
    return metricas(base)


def score(row):
    dist = 0 if 230 <= row["trades_365"] <= 250 else min(abs(row["trades_365"] - 230), abs(row["trades_365"] - 250))
    penal_anos = 0
    for ano in [2024, 2025, 2026]:
        if row[f"pontos_{ano}"] < 0:
            penal_anos += abs(row[f"pontos_{ano}"]) * 3 + 2000
    return (
        row["pontos_365"]
        + 200 * min(row["pf_365"], 4)
        + 45 * row["winrate_365"]
        - abs(row["dd_365"]) * 0.7
        - 70 * dist
        - 800 * max(0, 80 - row["winrate_365"])
        - penal_anos
    )


def sinais_v2(candles):
    sinais = list(sinais_dmi3(candles))
    for modulo in MODULOS:
        if modulo[0] not in REMOVIDOS_V2:
            sinais.extend(sinais_modulo(candles, modulo))
    return sinais


def avaliar(candles, base_sinais, dias_base, cfg, cache):
    fallback = montar_sinais_diarios(candles, cfg)
    fallback = [s for s in fallback if candles.at[s[0], "DataHora_SP"].date() not in dias_base]
    trades = simular_lista(candles, base_sinais + fallback, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    row = {
        "horarios": ",".join(cfg["horarios"]),
        "modo": cfg["modo"],
        "adx_min": cfg["adx_min"],
        "gap_min": cfg["gap_min"],
        "forca_min": cfg["forca_min"],
        "usar_tendencia": cfg["usar_tendencia"],
        "usar_vwap": cfg["usar_vwap"],
        "range_max": cfg["range_max"] if cfg["range_max"] is not None else "",
        "trades_fallback_brutos": len(fallback),
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
    candles_base = preparar_candles()
    candles = preparar_sinais(candles_base)
    cache = {}
    base_sinais = sinais_v2(candles)
    base_trades = simular_lista(candles, base_sinais, cache)
    dias_base = set(base_trades["datahora_entrada"].dt.date) if not base_trades.empty else set()
    base_m = metricas(base_trades, 365)
    print("Base V2:", base_m, flush=True)

    linhas = []
    melhor_trades = pd.DataFrame()
    melhor_score = -10**18
    total = 0
    for cfg in gerar_configs():
        total += 1
        row, trades = avaliar(candles, base_sinais, dias_base, cfg, cache)
        linhas.append(row)
        if row["score"] > melhor_score:
            melhor_score = row["score"]
            melhor_trades = trades
        if total % 300 == 0:
            print(f"Avaliados {total} fallbacks", flush=True)
        if total >= MAX_CONFIGS:
            break

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "horarios", "modo", "adx_min", "gap_min", "forca_min", "usar_tendencia", "usar_vwap", "range_max",
        "trades_fallback_brutos", "trades_365", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "score",
    ]
    print("\nTop V2 + fallback:")
    print(ranking[cols].head(40).to_string(index=False), flush=True)

    alvo = ranking[
        ranking["trades_365"].between(220, 250)
        & (ranking["winrate_365"] >= 80)
        & (ranking["pontos_365"] > 0)
        & (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
    ]
    print("\nAlvo V2 + fallback 220-250, >=80%, anos positivos:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False), flush=True)

    try:
        ranking.to_csv(SAIDA_DIR / "busca_v2_com_fallback_diario_230_ranking.csv", index=False)
        melhor_trades.to_csv(SAIDA_DIR / "busca_v2_com_fallback_diario_230_trades_top.csv", index=False)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV:", exc, flush=True)


if __name__ == "__main__":
    main()
