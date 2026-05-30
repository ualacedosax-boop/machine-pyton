from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
TRADES_TV = SAIDA_DIR / "auditoria_tv_3_horarios_trades_consolidados.csv"

ARQ_RANKING = SAIDA_DIR / "otimizacao_take_stop_export_tv_alta_acertividade_ranking.csv"
ARQ_XLSX = SAIDA_DIR / "otimizacao_take_stop_export_tv_alta_acertividade.xlsx"

# MNQ: o export mostra 50,5 pontos = 101 USD, logo 1 ponto = 2 USD.
USD_POR_PONTO = 2.0

MODOS = {
    "87pct_54trades": ["03:48_Monday", "20:58_Sunday"],
    "84pct_78trades": ["03:48_Monday", "20:58_Sunday", "20:58_Tuesday"],
    "81pct_105trades": ["03:48_Monday", "03:48_Tuesday", "20:58_Sunday", "20:58_Tuesday"],
    "79pct_129trades": ["03:48_Monday", "03:48_Tuesday", "20:58_Sunday", "20:58_Tuesday", "20:58_Wednesday"],
}


def max_drawdown(pontos):
    eq = pontos.astype(float).cumsum()
    if len(eq) == 0:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pontos):
    p = pontos.astype(float)
    ganhos = float(p[p > 0].sum())
    perdas = abs(float(p[p < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def carregar_base():
    df = pd.read_csv(TRADES_TV, parse_dates=["Data e hora"])
    base = df[df["horario_sinal"].isin(["03:48", "20:58"]) & df["direcao"].eq("BUY")].copy()
    base["dow"] = base["Data e hora"].dt.day_name()
    base["chave"] = base["horario_sinal"] + "_" + base["dow"]
    base["mfe_usd"] = pd.to_numeric(base["Excursão favorável USD"], errors="coerce").fillna(0.0)
    base["mae_usd_abs"] = pd.to_numeric(base["Excursão adversa USD"], errors="coerce").abs().fillna(0.0)
    return base.sort_values("Data e hora")


def simular_por_excursao(g, take_pts, stop_pts):
    take_usd = take_pts * USD_POR_PONTO
    stop_usd = stop_pts * USD_POR_PONTO

    # Conservador: se no export a excursao contra ja passou o novo stop, conta STOP.
    # Se nao passou stop e a excursao favoravel passou o novo take, conta TAKE.
    # Caso contrario, usa o PnL original limitado pelo novo take/stop.
    pnl = []
    motivo = []
    for row in g.itertuples():
        if float(row.mae_usd_abs) >= stop_usd:
            pnl.append(-stop_usd)
            motivo.append("STOP_SIM")
        elif float(row.mfe_usd) >= take_usd:
            pnl.append(take_usd)
            motivo.append("TAKE_SIM")
        else:
            original = float(row.pnl)
            pnl.append(max(min(original, take_usd), -stop_usd))
            motivo.append("PNL_ORIGINAL_LIMITADO")
    out = g.copy()
    out["pnl_sim"] = pnl
    out["motivo_sim"] = motivo
    return out


def resumir(g):
    p = g["pnl_sim"].astype(float)
    mensal = g.groupby(g["Data e hora"].dt.to_period("M"))["pnl_sim"].sum()
    g2 = g.reset_index(drop=True).copy()
    if len(g2) >= 4:
        g2["quartil"] = pd.qcut(g2.index, q=4, labels=False, duplicates="drop")
        quartis = g2.groupby("quartil")["pnl_sim"].agg(
            min_q_pnl="sum",
            min_q_wr=lambda s: (s > 0).mean() * 100,
        )
        min_q_pnl = float(quartis["min_q_pnl"].min())
        min_q_wr = float(quartis["min_q_wr"].min())
    else:
        min_q_pnl = float(p.sum())
        min_q_wr = float((p > 0).mean() * 100) if len(p) else 0.0
    return {
        "trades": int(len(g)),
        "winrate": float((p > 0).mean() * 100) if len(p) else 0.0,
        "pnl_usd": float(p.sum()),
        "max_drawdown_usd": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "meses_negativos": int((mensal < 0).sum()) if len(mensal) else 0,
        "pior_mes_usd": float(mensal.min()) if len(mensal) else 0.0,
        "min_q_wr": min_q_wr,
        "min_q_pnl": min_q_pnl,
    }


def main():
    print("=====================================================")
    print("OTIMIZACAO TAKE/STOP PELO EXPORT TV - ALTA ACERTIVIDADE")
    print("=====================================================")
    base = carregar_base()
    linhas = []
    for modo, chaves in MODOS.items():
        g = base[base["chave"].isin(chaves)].copy()
        for take in [25, 30, 35, 40, 45, 50.5, 55, 60]:
            for stop in [70, 80, 90, 100, 110, 117]:
                sim = simular_por_excursao(g, take, stop)
                r = resumir(sim)
                r.update({
                    "modo": modo,
                    "take_pts": take,
                    "stop_pts": stop,
                    "rr_take_stop": take / stop,
                    "score": (
                        r["pnl_usd"]
                        + 100 * r["winrate"]
                        + 250 * r["profit_factor"]
                        + 80 * r["min_q_wr"]
                        - 0.4 * abs(r["max_drawdown_usd"])
                        - 500 * r["meses_negativos"]
                    ),
                })
                linhas.append(r)

    ranking = pd.DataFrame(linhas).sort_values(
        ["score", "winrate", "pnl_usd"],
        ascending=[False, False, False],
    )
    ranking.to_csv(ARQ_RANKING, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)

    cols = [
        "modo", "take_pts", "stop_pts", "trades", "winrate", "pnl_usd",
        "max_drawdown_usd", "profit_factor", "meses_negativos",
        "pior_mes_usd", "min_q_wr", "min_q_pnl", "score",
    ]
    print("\nTop geral:")
    print(ranking[cols].head(30).to_string(index=False))
    print("\nTop com winrate >= 85 e pnl positivo:")
    filt = ranking[(ranking["winrate"] >= 85) & (ranking["pnl_usd"] > 0)]
    print(filt[cols].head(30).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)


if __name__ == "__main__":
    main()
