import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_dia_230_250 import preparar_candles, simular_lista
from buscar_seletor_diario_230_250 import metricas, preparar_sinais
from buscar_v2_com_fallback_diario_230 import met_periodo, score, sinais_v2


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
MAX_CONFIGS = 22000


def preparar_candidatos_fallback(candles, dias_base):
    df = candles[candles["hhmm"].eq("20:58")].copy()
    df = df[~df["DataHora_SP"].dt.date.isin(dias_base)].copy()
    df["dow"] = df["DataHora_SP"].dt.day_name()

    votos = pd.DataFrame(index=df.index)
    votos["ema17_34"] = np.where(df["ema17"] >= df["ema34"], 1, -1)
    votos["sma17_34"] = np.where(df["sma17"] >= df["sma34"], 1, -1)
    votos["macd"] = np.where(df["macd"] >= df["macd_signal"], 1, -1)
    votos["roc5"] = np.where(df["roc5"] >= 0, 1, -1)
    votos["roc10"] = np.where(df["roc10"] >= 0, 1, -1)
    votos["vwap"] = np.where(df["close"] >= df["vwap"], 1, -1)
    votos["dmi"] = np.where(df["di_plus"] >= df["di_minus"], 1, -1)
    votos["body"] = np.where(df["body"] >= 0, 1, -1)
    votos["ema200"] = np.where(df["close"] >= df["ema200"], 1, -1)
    votos["rsi"] = np.where(df["rsi14"] >= 50, 1, -1)

    df["voto_total"] = votos.sum(axis=1)
    df["forca_voto"] = df["voto_total"].abs()
    df["direcao_voto"] = np.where(df["voto_total"] >= 0, "BUY", "SELL")
    df["tend_buy"] = (df["ema17"] >= df["ema34"]) & (df["di_plus"] >= df["di_minus"])
    df["tend_sell"] = (df["ema17"] < df["ema34"]) & (df["di_minus"] > df["di_plus"])
    df["vwap_ok"] = (
        (df["direcao_voto"].eq("BUY") & (df["close"] >= df["vwap"]))
        | (df["direcao_voto"].eq("SELL") & (df["close"] <= df["vwap"]))
    )
    return df


def gerar_configs(candidatos):
    dows = sorted(candidatos["dow"].dropna().unique().tolist())
    dow_sets = [tuple(dows)]
    for qtd in [6, 5, 4, 3]:
        for subset in itertools.combinations(dows, qtd):
            dow_sets.append(subset)

    for adx_min in [20, 0, 15, 25, 10, 30, 35]:
        for gap_min in [0, 6, 3, 10, 14]:
            for forca_min in [2, 0, 4, 6, 8]:
                for range_max in [None, 85, 60, 40, 120]:
                    for usar_vwap in [False, True]:
                        for usar_tendencia in [False, True]:
                            for direcoes in [("BUY",), ("SELL",), ("BUY", "SELL")]:
                                for dow_set in dow_sets:
                                    yield {
                                        "adx_min": adx_min,
                                        "gap_min": gap_min,
                                        "forca_min": forca_min,
                                        "range_max": range_max,
                                        "usar_vwap": usar_vwap,
                                        "usar_tendencia": usar_tendencia,
                                        "direcoes": direcoes,
                                        "dows": dow_set,
                                    }


def sinais_fallback(candidatos, cfg):
    mask = (
        (candidatos["adx14"] >= cfg["adx_min"])
        & (candidatos["dmi_gap"] >= cfg["gap_min"])
        & (candidatos["forca_voto"] >= cfg["forca_min"])
        & (candidatos["direcao_voto"].isin(cfg["direcoes"]))
        & (candidatos["dow"].isin(cfg["dows"]))
    )
    if cfg["range_max"] is not None:
        mask &= candidatos["range_30m"] <= cfg["range_max"]
    if cfg["usar_vwap"]:
        mask &= candidatos["vwap_ok"]
    if cfg["usar_tendencia"]:
        mask &= (
            (candidatos["direcao_voto"].eq("BUY") & candidatos["tend_buy"])
            | (candidatos["direcao_voto"].eq("SELL") & candidatos["tend_sell"])
        )
    return [
        (int(idx), f"FB2058_REF_{candidatos.at[idx, 'direcao_voto']}", candidatos.at[idx, "direcao_voto"], 50.5, 117.0)
        for idx in candidatos.index[mask]
    ]


def avaliar(candles, base_sinais, candidatos, cfg, cache):
    fallback = sinais_fallback(candidatos, cfg)
    trades = simular_lista(candles, base_sinais + fallback, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    row = {
        "adx_min": cfg["adx_min"],
        "gap_min": cfg["gap_min"],
        "forca_min": cfg["forca_min"],
        "range_max": cfg["range_max"] if cfg["range_max"] is not None else "",
        "usar_vwap": cfg["usar_vwap"],
        "usar_tendencia": cfg["usar_tendencia"],
        "direcoes": ",".join(cfg["direcoes"]),
        "dows": ",".join(cfg["dows"]),
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
    candles["range_30m"] = candles["high"].rolling(15).max() - candles["low"].rolling(15).min()
    cache = {}
    base_sinais = sinais_v2(candles)
    base_trades = simular_lista(candles, base_sinais, cache)
    dias_base = set(base_trades["datahora_entrada"].dt.date) if not base_trades.empty else set()
    candidatos = preparar_candidatos_fallback(candles, dias_base)

    print("Base V2:", metricas(base_trades, 365), flush=True)
    print("Candidatos fallback 20:58:", len(candidatos), flush=True)

    linhas = []
    melhor_trades = pd.DataFrame()
    melhor_score = -10**18
    total = 0
    for cfg in gerar_configs(candidatos):
        total += 1
        row, trades = avaliar(candles, base_sinais, candidatos, cfg, cache)
        linhas.append(row)
        if row["score"] > melhor_score:
            melhor_score = row["score"]
            melhor_trades = trades
        if total % 5000 == 0:
            parcial = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False).iloc[0]
            print(
                f"Avaliados {total} | best trades={parcial['trades_365']} "
                f"wr={parcial['winrate_365']:.2f}% pts={parcial['pontos_365']:.1f}",
                flush=True,
            )
        if total >= MAX_CONFIGS:
            print(f"Parando em {MAX_CONFIGS} configs priorizadas", flush=True)
            break

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "adx_min", "gap_min", "forca_min", "range_max", "usar_vwap", "usar_tendencia", "direcoes", "dows",
        "fallback_brutos", "trades_365", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "score",
    ]
    print("\nTop refino V3B:")
    print(ranking[cols].head(60).to_string(index=False), flush=True)

    alvo = ranking[
        ranking["trades_365"].between(220, 250)
        & (ranking["winrate_365"] >= 85)
        & (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
    ]
    print("\nAlvo 220-250, >=85%, anos positivos:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(30).to_string(index=False), flush=True)

    try:
        ranking.to_csv(SAIDA_DIR / "refino_v3b_fallback_2058_ranking.csv", index=False)
        melhor_trades.to_csv(SAIDA_DIR / "refino_v3b_fallback_2058_trades_top.csv", index=False)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV:", exc, flush=True)


if __name__ == "__main__":
    main()
