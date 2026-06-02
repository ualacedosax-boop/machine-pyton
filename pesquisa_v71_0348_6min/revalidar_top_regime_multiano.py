import re
from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import (
    STOP,
    TAKE,
    preparar_candles,
    sinais_dmi3,
    simular_lista,
)
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING_ORIGEM = SAIDA_DIR / "busca_regime_dia_230_250_ranking_20260602_110826.csv"
ARQ_RANKING = SAIDA_DIR / "revalidacao_top_regime_multiano_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "revalidacao_top_regime_multiano_trades_top.csv"


MOD_RE = re.compile(
    r"^R_(?P<hhmm>\d{2}:\d{2})_(?P<direcao>BUY|SELL)_A(?P<adx>\d+)_G(?P<gap>\d+)"
    r"(?:_(?P<col>.+)_(?P<op>GE|LE)(?P<valor>-?\d+(?:\.\d+)?))?$"
)


def metricas(nome, trades, inicio=None, fim=None):
    base = trades
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {
            f"trades_{nome}": 0,
            f"winrate_{nome}": 0.0,
            f"pontos_{nome}": 0.0,
            f"dd_{nome}": 0.0,
            f"pf_{nome}": 0.0,
            f"dias_{nome}": 0,
        }
    pontos = base["pontos"].astype(float)
    return {
        f"trades_{nome}": int(len(base)),
        f"winrate_{nome}": float((pontos > 0).mean() * 100),
        f"pontos_{nome}": float(pontos.sum()),
        f"dd_{nome}": max_drawdown(pontos),
        f"pf_{nome}": profit_factor(pontos),
        f"dias_{nome}": int(base["datahora_entrada"].dt.date.nunique()),
    }


def parse_modulo(nome):
    match = MOD_RE.match(nome)
    if not match:
        raise ValueError(f"Modulo nao reconhecido: {nome}")
    dados = match.groupdict()
    dados["adx"] = int(dados["adx"])
    dados["gap"] = int(dados["gap"])
    dados["valor"] = float(dados["valor"]) if dados["valor"] is not None else None
    return dados


def sinais_modulo(candles, nome):
    dados = parse_modulo(nome)
    mask = candles["hhmm"].eq(dados["hhmm"])
    if dados["direcao"] == "BUY":
        mask &= (candles["ema17"] >= candles["ema34"]) & (candles["di_plus"] >= candles["di_minus"])
    else:
        mask &= (candles["ema17"] < candles["ema34"]) & (candles["di_minus"] > candles["di_plus"])
    mask &= (candles["adx14"] >= dados["adx"]) & (candles["dmi_gap"] >= dados["gap"])

    if dados["col"] is not None:
        if dados["col"] not in candles.columns:
            raise ValueError(f"Coluna ausente para modulo {nome}: {dados['col']}")
        if dados["op"] == "GE":
            mask &= candles[dados["col"]] >= dados["valor"]
        else:
            mask &= candles[dados["col"]] <= dados["valor"]

    return [(idx, nome, dados["direcao"], TAKE, STOP) for idx in candles.index[mask]]


def avaliar_combo(candles, base, combo, cache):
    sinais = list(base)
    for nome in combo:
        sinais.extend(sinais_modulo(candles, nome))
    trades = simular_lista(candles, sinais, cache)
    row = {
        "modulos": " + ".join(combo) if combo else "DMI3_SOZINHO",
        "qtd_modulos": len(combo),
    }
    row.update(metricas("all", trades))
    for ano in [2024, 2025, 2026]:
        row.update(metricas(str(ano), trades, f"{ano}-01-01", f"{ano + 1}-01-01"))
    if not trades.empty:
        fim = trades["datahora_entrada"].max()
        row.update(metricas("365", trades, fim - pd.Timedelta(days=365)))
        row.update(metricas("90", trades, fim - pd.Timedelta(days=90)))
        row.update(metricas("30", trades, fim - pd.Timedelta(days=30)))
    else:
        for periodo in ["365", "90", "30"]:
            row.update(metricas(periodo, trades))

    penal_ano_negativo = sum(max(0.0, -row[f"pontos_{ano}"]) * 6 + (1800 if row[f"pontos_{ano}"] < 0 else 0) for ano in [2024, 2025, 2026])
    penal_win_365 = max(0.0, 84.0 - row["winrate_365"]) * 420
    penal_win_all = max(0.0, 78.0 - row["winrate_all"]) * 320
    penal_freq = max(0, 170 - row["trades_365"]) * 28 + max(0, row["trades_365"] - 240) * 12
    row["score_robusto"] = (
        row["pontos_365"]
        + row["pontos_all"] * 0.35
        + min(row["pf_365"], 5) * 260
        + row["winrate_365"] * 35
        - abs(row["dd_365"]) * 0.75
        - penal_ano_negativo
        - penal_win_365
        - penal_win_all
        - penal_freq
    )
    return row, trades


def combos_origem(limite=2500):
    origem = pd.read_csv(ARQ_RANKING_ORIGEM)
    fatias = [
        origem.head(limite),
        origem[origem["trades_365"].between(170, 240)].sort_values(["winrate_365", "pontos_365"], ascending=False).head(limite),
        origem[origem["trades_365"].between(220, 260)].sort_values(["winrate_365", "pontos_365"], ascending=False).head(limite),
        origem[(origem["winrate_365"] >= 84) & (origem["pontos_365"] > 0)].head(limite),
    ]
    bruto = pd.concat(fatias, ignore_index=True)
    vistos = set()
    combos = []
    for texto in bruto["modulos"].dropna():
        if texto == "DMI3_SOZINHO":
            combo = tuple()
        else:
            combo = tuple(part.strip() for part in str(texto).split(" + ") if part.strip())
        chave = " + ".join(combo)
        if chave not in vistos:
            vistos.add(chave)
            combos.append(combo)
    return combos


def main():
    candles = preparar_candles()
    cache = {}
    base = sinais_dmi3(candles)
    combos = combos_origem()
    print("Combos para revalidar:", len(combos), flush=True)

    linhas = []
    melhor_trades = pd.DataFrame()
    melhor_score = -10**18
    for i, combo in enumerate(combos, 1):
        row, trades = avaliar_combo(candles, base, combo, cache)
        linhas.append(row)
        if row["score_robusto"] > melhor_score:
            melhor_score = row["score_robusto"]
            melhor_trades = trades
        if i % 250 == 0:
            print("Revalidados:", i, "/", len(combos), flush=True)

    ranking = pd.DataFrame(linhas).sort_values(["score_robusto", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "modulos", "qtd_modulos", "score_robusto",
        "trades_365", "dias_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_all", "winrate_all", "pontos_all",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_90", "winrate_90", "pontos_90",
        "trades_30", "winrate_30", "pontos_30",
    ]
    print("\nTop robustez anual:")
    print(ranking[cols].head(30).to_string(index=False, max_colwidth=160), flush=True)

    alvo = ranking[
        (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
        & (ranking["winrate_365"] >= 84)
        & (ranking["trades_365"] >= 160)
    ]
    print("\nCandidatos anos positivos, 365d >=160 trades e >=84%:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False, max_colwidth=160), flush=True)

    ranking.to_csv(ARQ_RANKING, index=False)
    melhor_trades.to_csv(ARQ_TRADES, index=False)
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
