from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import (
    avaliar,
    gerar_modulos_regime,
    preparar_candles,
    sinais_dmi3,
)


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")


def met_periodo(trades, inicio, fim):
    base = trades[(trades["datahora_entrada"] >= pd.Timestamp(inicio)) & (trades["datahora_entrada"] < pd.Timestamp(fim))]
    if base.empty:
        return 0, 0.0, 0.0
    p = base["pontos"].astype(float)
    return int(len(base)), float((p > 0).mean() * 100), float(p.sum())


def score_robusto(row):
    # Penaliza forte qualquer ano negativo; premia 365d, mas nao deixa o ano antigo sumir.
    penal_ano = 0
    for campo in ["pontos_2024", "pontos_2025", "pontos_2026"]:
        if row[campo] < 0:
            penal_ano += abs(row[campo]) * 4 + 2500
    penal_win = max(0, 76 - row["winrate_all"]) * 350 + max(0, 80 - row["winrate_365"]) * 250
    return (
        row["pontos_all"]
        + row["pontos_365"]
        + 100 * min(row["pf_365"], 4)
        + 20 * row["winrate_365"]
        - 0.45 * abs(row["dd_365"])
        - penal_ano
        - penal_win
    )


def avaliar_robusto(candles, base, combo, cache):
    row, trades = avaliar(candles, base, combo, cache)
    t_all = len(trades)
    if t_all:
        p = trades["pontos"].astype(float)
        row["trades_all"] = int(t_all)
        row["winrate_all"] = float((p > 0).mean() * 100)
        row["pontos_all"] = float(p.sum())
    else:
        row["trades_all"] = 0
        row["winrate_all"] = 0.0
        row["pontos_all"] = 0.0
    for ano in [2024, 2025, 2026]:
        tr, wr, pts = met_periodo(trades, f"{ano}-01-01", f"{ano + 1}-01-01")
        row[f"trades_{ano}"] = tr
        row[f"winrate_{ano}"] = wr
        row[f"pontos_{ano}"] = pts
    row["score_robusto"] = score_robusto(row)
    return row, trades


def main():
    candles = preparar_candles()
    cache = {}
    base = sinais_dmi3(candles)
    modulos = gerar_modulos_regime(candles, cache)
    # Remove variantes com poucos trades demais e conserva diversidade.
    modulos = [m for m in modulos if m[2]["trades"] >= 10][:80]

    linhas = []
    row_base, _ = avaliar_robusto(candles, base, [], cache)
    linhas.append(row_base)
    beam = [()]
    vistos = {""}
    for tamanho in [1, 2, 3, 4, 5, 6, 7, 8]:
        prox = []
        for combo in beam:
            usados = {x[0] for x in combo}
            for modulo in modulos:
                if modulo[0] in usados:
                    continue
                novo = tuple(sorted(combo + (modulo,), key=lambda x: x[0]))
                chave = " + ".join(x[0] for x in novo)
                if chave in vistos:
                    continue
                vistos.add(chave)
                row, trades = avaliar_robusto(candles, base, novo, cache)
                linhas.append(row)
                prox.append((row["score_robusto"], novo, trades))
        prox = sorted(prox, key=lambda x: x[0], reverse=True)[:80]
        beam = [x[1] for x in prox]
        print("Beam", tamanho, len(beam), flush=True)

    ranking = pd.DataFrame(linhas).sort_values(["score_robusto", "winrate_365", "pontos_all"], ascending=False)
    cols = [
        "modulos", "qtd_modulos", "score_robusto",
        "trades_all", "winrate_all", "pontos_all",
        "trades_2024", "winrate_2024", "pontos_2024",
        "trades_2025", "winrate_2025", "pontos_2025",
        "trades_2026", "winrate_2026", "pontos_2026",
        "trades_365", "winrate_365", "pontos_365", "dd_365", "pf_365",
        "trades_90", "winrate_90", "pontos_90",
        "trades_30", "winrate_30", "pontos_30",
    ]
    print("\nTop robusto:")
    print(ranking[cols].head(40).to_string(index=False), flush=True)
    robustos = ranking[
        (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
        & (ranking["winrate_365"] >= 80)
        & (ranking["trades_365"] >= 160)
    ]
    print("\nRobustos multiano, 365d >=160 trades e >=80%:", len(robustos), flush=True)
    if not robustos.empty:
        print(robustos[cols].head(20).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
