from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
TRADES_TV = SAIDA_DIR / "auditoria_tv_3_horarios_trades_consolidados.csv"

ARQ_RESUMO = SAIDA_DIR / "validacao_candidato_tv_alta_acertividade_resumo.csv"
ARQ_PERIODOS = SAIDA_DIR / "validacao_candidato_tv_alta_acertividade_periodos.csv"
ARQ_TRADES = SAIDA_DIR / "validacao_candidato_tv_alta_acertividade_trades.csv"
ARQ_XLSX = SAIDA_DIR / "validacao_candidato_tv_alta_acertividade.xlsx"


MODOS = {
    "87pct_54trades": ["03:48_Monday", "20:58_Sunday"],
    "84pct_78trades": ["03:48_Monday", "20:58_Sunday", "20:58_Tuesday"],
    "81pct_105trades": ["03:48_Monday", "03:48_Tuesday", "20:58_Sunday", "20:58_Tuesday"],
    "80pct_105trades_alt": ["03:48_Monday", "03:48_Tuesday", "20:58_Sunday", "20:58_Wednesday"],
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


def resumo(g):
    p = g["pnl"].astype(float)
    mensal = g.groupby(g["Data e hora"].dt.to_period("M"))["pnl"].sum()
    return {
        "trades": int(len(g)),
        "wins": int((p > 0).sum()),
        "losses": int((p < 0).sum()),
        "winrate": float((p > 0).mean() * 100) if len(p) else 0.0,
        "pnl_usd": float(p.sum()),
        "max_drawdown_usd": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "meses_negativos": int((mensal < 0).sum()) if len(mensal) else 0,
        "pior_mes_usd": float(mensal.min()) if len(mensal) else 0.0,
    }


def carregar_base():
    df = pd.read_csv(TRADES_TV, parse_dates=["Data e hora"])
    base = df[df["horario_sinal"].isin(["03:48", "20:58"]) & df["direcao"].eq("BUY")].copy()
    base["dow"] = base["Data e hora"].dt.day_name()
    base["chave"] = base["horario_sinal"] + "_" + base["dow"]
    base = base.sort_values("Data e hora")
    return base


def validar_modos(base):
    linhas_resumo = []
    linhas_periodos = []
    trades_out = []

    for modo, chaves in MODOS.items():
        g = base[base["chave"].isin(chaves)].copy()
        g["modo"] = modo
        g["chaves_modo"] = "+".join(chaves)
        trades_out.append(g)

        r = resumo(g)
        r.update({"modo": modo, "chaves": "+".join(chaves)})
        linhas_resumo.append(r)

        if not g.empty:
            g = g.reset_index(drop=True)
            g["quartil_execucao"] = pd.qcut(g.index, q=4, labels=False, duplicates="drop")
            for q, gg in g.groupby("quartil_execucao"):
                rr = resumo(gg)
                rr.update({
                    "modo": modo,
                    "periodo_tipo": "quartil_execucao",
                    "periodo": int(q) + 1,
                    "inicio": gg["Data e hora"].min(),
                    "fim": gg["Data e hora"].max(),
                })
                linhas_periodos.append(rr)
            for mes, gg in g.groupby(g["Data e hora"].dt.to_period("M")):
                rr = resumo(gg)
                rr.update({
                    "modo": modo,
                    "periodo_tipo": "mes",
                    "periodo": str(mes),
                    "inicio": gg["Data e hora"].min(),
                    "fim": gg["Data e hora"].max(),
                })
                linhas_periodos.append(rr)

    resumo_df = pd.DataFrame(linhas_resumo)
    periodos_df = pd.DataFrame(linhas_periodos)
    trades_df = pd.concat(trades_out, ignore_index=True) if trades_out else pd.DataFrame()

    periodos_q = periodos_df[periodos_df["periodo_tipo"].eq("quartil_execucao")]
    estabilidade = periodos_q.groupby("modo").agg(
        min_winrate_quartil=("winrate", "min"),
        min_pnl_quartil=("pnl_usd", "min"),
    ).reset_index()
    resumo_df = resumo_df.merge(estabilidade, on="modo", how="left")
    resumo_df["score_robustez"] = (
        resumo_df["pnl_usd"]
        + 100 * resumo_df["winrate"]
        + 250 * resumo_df["profit_factor"]
        + 80 * resumo_df["min_winrate_quartil"].fillna(0)
        - 0.4 * resumo_df["max_drawdown_usd"].abs()
        - 500 * resumo_df["meses_negativos"]
    )
    resumo_df = resumo_df.sort_values("score_robustez", ascending=False)
    return resumo_df, periodos_df, trades_df


def main():
    print("=====================================================")
    print("VALIDACAO CANDIDATO TV ALTA ACERTIVIDADE")
    print("=====================================================")
    base = carregar_base()
    resumo_df, periodos_df, trades_df = validar_modos(base)

    resumo_df.to_csv(ARQ_RESUMO, index=False)
    periodos_df.to_csv(ARQ_PERIODOS, index=False)
    trades_df.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, sheet_name="resumo_modos", index=False)
        periodos_df.to_excel(writer, sheet_name="periodos", index=False)
        trades_df.to_excel(writer, sheet_name="trades", index=False)

    cols = [
        "modo",
        "trades",
        "winrate",
        "pnl_usd",
        "max_drawdown_usd",
        "profit_factor",
        "meses_negativos",
        "pior_mes_usd",
        "min_winrate_quartil",
        "min_pnl_quartil",
        "score_robustez",
    ]
    print(resumo_df[cols].to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RESUMO)
    print(ARQ_PERIODOS)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
