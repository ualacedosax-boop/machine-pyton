from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_dia_230_250 import preparar_candles, simular_lista
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
TAKE = 50.5
STOP = 117.0
MAX_CONFIGS = 700


def metricas(trades, dias=None):
    if trades.empty:
        return {"trades": 0, "dias": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    base = trades
    if dias is not None:
        fim = trades["datahora_entrada"].max()
        base = trades[trades["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return {"trades": 0, "dias": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    p = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "dd": max_drawdown(p),
        "pf": profit_factor(p),
    }


def periodo(trades, ano):
    base = trades[
        (trades["datahora_entrada"] >= pd.Timestamp(f"{ano}-01-01"))
        & (trades["datahora_entrada"] < pd.Timestamp(f"{ano + 1}-01-01"))
    ]
    return metricas(base)


def preparar_sinais(candles):
    df = candles.copy()
    df["data"] = df["DataHora_SP"].dt.date
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df["ret_15m"] = df["close"] - df["close"].shift(8)
    df["ret_30m"] = df["close"] - df["close"].shift(15)
    df["ret_60m"] = df["close"] - df["close"].shift(30)
    df["range_30m"] = df["high"].rolling(15).max() - df["low"].rolling(15).min()
    df["dist_vwap"] = df["close"] - df["vwap"]
    df["ema200_slope"] = df["ema200"] - df["ema200"].shift(10)

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
    df["direcao_voto"] = np.where(df["voto_total"] >= 0, "BUY", "SELL")
    df["forca_voto"] = df["voto_total"].abs()
    return df


def montar_sinais_diarios(candles, cfg):
    base = candles[candles["hhmm"].isin(cfg["horarios"])].copy()
    base = base[(base["adx14"] >= cfg["adx_min"]) & (base["dmi_gap"] >= cfg["gap_min"]) & (base["forca_voto"] >= cfg["forca_min"])]

    if cfg["usar_tendencia"]:
        base = base[
            ((base["direcao_voto"].eq("BUY")) & (base["ema17"] >= base["ema34"]) & (base["di_plus"] >= base["di_minus"]))
            | ((base["direcao_voto"].eq("SELL")) & (base["ema17"] < base["ema34"]) & (base["di_minus"] > base["di_plus"]))
        ]
    if cfg["usar_vwap"]:
        base = base[
            ((base["direcao_voto"].eq("BUY")) & (base["close"] >= base["vwap"]))
            | ((base["direcao_voto"].eq("SELL")) & (base["close"] <= base["vwap"]))
        ]
    if cfg["range_max"] is not None:
        base = base[base["range_30m"] <= cfg["range_max"]]

    if base.empty:
        return []

    score = (
        base["forca_voto"] * 10
        + base["adx14"].clip(0, 45) * 0.6
        + base["dmi_gap"].clip(0, 30) * 0.9
        - base["range_30m"].fillna(0) * cfg["range_penal"]
    )
    base = base.assign(score_escolha=score)

    escolhidos = []
    for _, grupo in base.groupby("data", sort=True):
        if cfg["modo"] == "primeiro":
            escolhido = grupo.sort_values(["DataHora_SP", "score_escolha"], ascending=[True, False]).iloc[0]
        elif cfg["modo"] == "ultimo":
            escolhido = grupo.sort_values(["DataHora_SP", "score_escolha"], ascending=[False, False]).iloc[0]
        else:
            escolhido = grupo.sort_values(["score_escolha", "DataHora_SP"], ascending=[False, True]).iloc[0]
        idx = int(escolhido.name)
        nome = f"DIARIO_{cfg['nome']}_{escolhido['hhmm']}_{escolhido['direcao_voto']}"
        escolhidos.append((idx, nome, escolhido["direcao_voto"], TAKE, STOP))
    return escolhidos


def avaliar(candles, cfg, cache):
    sinais = montar_sinais_diarios(candles, cfg)
    trades = simular_lista(candles, sinais, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    anos = {ano: periodo(trades, ano) for ano in [2024, 2025, 2026]}
    dist = 0 if 230 <= m365["trades"] <= 250 else min(abs(m365["trades"] - 230), abs(m365["trades"] - 250))
    penal_anos = sum(max(0, -anos[ano]["pontos"]) * 2 for ano in anos)
    score = (
        m365["pontos"]
        + 160 * min(m365["pf"], 4)
        + 35 * m365["winrate"]
        - abs(m365["dd"]) * 0.65
        - 90 * dist
        - 650 * max(0, 80 - m365["winrate"])
        - penal_anos
    )
    row = {
        "nome": cfg["nome"],
        "horarios": ",".join(cfg["horarios"]),
        "modo": cfg["modo"],
        "adx_min": cfg["adx_min"],
        "gap_min": cfg["gap_min"],
        "forca_min": cfg["forca_min"],
        "usar_tendencia": cfg["usar_tendencia"],
        "usar_vwap": cfg["usar_vwap"],
        "range_max": cfg["range_max"] if cfg["range_max"] is not None else "",
        "range_penal": cfg["range_penal"],
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
        "score": score,
    }
    for ano, m in anos.items():
        row[f"trades_{ano}"] = m["trades"]
        row[f"winrate_{ano}"] = m["winrate"]
        row[f"pontos_{ano}"] = m["pontos"]
    return row, trades


def gerar_configs():
    grupos_horarios = [
        ("3H", ["03:48", "10:30", "20:58"]),
        ("5H", ["03:46", "03:48", "10:30", "20:52", "20:58"]),
        ("6H", ["03:46", "03:48", "10:26", "10:30", "20:52", "20:58"]),
    ]
    for nome_base, horarios in grupos_horarios:
        subsets = {
            tuple(horarios),
            ("03:48", "10:30", "20:58"),
            ("03:48", "10:30"),
            ("03:48", "20:58"),
            ("10:30", "20:58"),
            ("03:48", "20:52", "20:58"),
            ("03:46", "03:48", "10:30"),
            ("10:26", "10:30", "20:58"),
        }
        subsets = {tuple(s for s in subset if s in horarios) for subset in subsets}
        subsets = {subset for subset in subsets if len(subset) >= 2}
        for subset in sorted(subsets):
                for modo in ["melhor", "primeiro", "ultimo"]:
                    for adx_min in [0, 20]:
                        for gap_min in [0, 3]:
                            for forca_min in [0, 2, 4]:
                                for usar_tendencia in [False, True]:
                                    for usar_vwap in [False, True]:
                                        for range_max in [None, 60]:
                                            for range_penal in [0.0]:
                                                yield {
                                                    "nome": nome_base,
                                                    "horarios": list(subset),
                                                    "modo": modo,
                                                    "adx_min": adx_min,
                                                    "gap_min": gap_min,
                                                    "forca_min": forca_min,
                                                    "usar_tendencia": usar_tendencia,
                                                    "usar_vwap": usar_vwap,
                                                    "range_max": range_max,
                                                    "range_penal": range_penal,
                                                }


def main():
    candles = preparar_sinais(preparar_candles())
    cache = {}
    linhas = []
    melhor_trades = None
    melhor_score = -10**18
    total = 0
    for cfg in gerar_configs():
        total += 1
        row, trades = avaliar(candles, cfg, cache)
        linhas.append(row)
        if row["score"] > melhor_score:
            melhor_score = row["score"]
            melhor_trades = trades
        if total % 500 == 0:
            print(f"Avaliados {total} configs", flush=True)
        if total >= MAX_CONFIGS:
            print(f"Parando em {MAX_CONFIGS} configs prioritarias", flush=True)
            break

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "nome", "horarios", "modo", "adx_min", "gap_min", "forca_min", "usar_tendencia", "usar_vwap",
        "range_max", "range_penal", "trades_365", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "score",
    ]
    print("\nTop geral seletor diario:")
    print(ranking[cols].head(40).to_string(index=False), flush=True)

    alvo = ranking[
        ranking["trades_365"].between(230, 250)
        & (ranking["winrate_365"] >= 80)
        & (ranking["pontos_365"] > 0)
        & (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
    ]
    print("\nAlvo 230-250, >=80%, anos positivos:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False), flush=True)

    faixa = ranking[ranking["trades_365"].between(230, 250)]
    print("\nMelhores apenas na faixa 230-250:")
    if faixa.empty:
        print("Nenhum na faixa.", flush=True)
    else:
        print(faixa[cols].head(20).to_string(index=False), flush=True)

    try:
        ranking.to_csv(SAIDA_DIR / "busca_seletor_diario_230_250_ranking.csv", index=False)
        if melhor_trades is not None:
            melhor_trades.to_csv(SAIDA_DIR / "busca_seletor_diario_230_250_trades_top.csv", index=False)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV:", exc, flush=True)


if __name__ == "__main__":
    main()
