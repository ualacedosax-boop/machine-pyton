from pathlib import Path

import pandas as pd

from refinar_calendario_dow_230_85 import aplicar_filtros, montar_base
from buscar_calendario_dow_horario_230_250 import add_metricas
from buscar_regime_dia_230_250 import preparar_candles
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "refino_calendario_dow_230_85_ranking.csv"
ARQ_MD = SAIDA_DIR / "AUDITORIA_CALENDARIO_DOW_230_85_ROTACAO.md"
ARQ_RESUMO = SAIDA_DIR / "auditoria_calendario_dow_230_85_resumo.csv"
ARQ_MESES = SAIDA_DIR / "auditoria_calendario_dow_230_85_meses.csv"
ARQ_TRADES = SAIDA_DIR / "auditoria_calendario_dow_230_85_trades.csv"

PERFIS = [
    {
        "nome": "01 Max 365d",
        "descricao": "Prioriza resultado anual local",
        "filtros": (
            ("Wednesday|02:56|BUY", "dmi_gap", "GE", 3.5237),
            ("Thursday|04:30|SELL", "ema200_slope10", "LE", 4.7472),
        ),
    },
    {
        "nome": "02 Recente forte",
        "descricao": "Prioriza 90d/30d sem sair de 230-250 trades",
        "filtros": (
            ("Monday|04:02|BUY", "vwap_slope10", "LE", 4.6748),
            ("Tuesday|03:12|SELL", "dist_vwap", "LE", 22.2546),
        ),
    },
    {
        "nome": "03 Pior ano melhor",
        "descricao": "Melhor pior-ano encontrado no ranking de dois filtros",
        "filtros": (
            ("Tuesday|03:12|SELL", "dmi_gap", "GE", 2.7238),
            ("Thursday|04:30|SELL", "dmi_gap", "LE", 12.7108),
        ),
    },
]


def metricas_df(trades):
    if trades.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    pontos = trades["pontos"].astype(float)
    return {
        "trades": int(len(trades)),
        "winrate": float((pontos > 0).mean() * 100),
        "pontos": float(pontos.sum()),
        "dd": max_drawdown(pontos),
        "pf": profit_factor(pontos),
    }


def metricas_periodo(trades, inicio=None, fim=None):
    base = trades
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    return metricas_df(base)


def auditar_perfil(base, perfil):
    trades = aplicar_filtros(base, perfil["filtros"])
    resumo = []
    row = {
        "perfil": perfil["nome"],
        "descricao": perfil["descricao"],
        "filtros": descreve_filtros(perfil["filtros"]),
    }
    add_metricas(row, trades)
    resumo.append(row)

    fim = trades["datahora_entrada"].max() if not trades.empty else None
    recortes = []
    if fim is not None:
        for dias in [30, 60, 90, 180, 365]:
            m = metricas_periodo(trades, fim - pd.Timedelta(days=dias))
            m.update({"perfil": perfil["nome"], "periodo": f"ultimos_{dias}d"})
            recortes.append(m)
    for ano in [2024, 2025, 2026]:
        m = metricas_periodo(trades, f"{ano}-01-01", f"{ano + 1}-01-01")
        m.update({"perfil": perfil["nome"], "periodo": str(ano)})
        recortes.append(m)
    return trades.assign(perfil=perfil["nome"]), row, recortes


def descreve_filtros(filtros):
    return " ; ".join(f"{token} {coluna} {op} {valor:.4f}" for token, coluna, op, valor in filtros)


def tabela_md(df, colunas, limite=None):
    if df.empty:
        return ["Nenhum dado."]
    dados = df[colunas] if limite is None else df[colunas].head(limite)
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join(["---"] * len(colunas)) + " |",
    ]
    for row in dados.itertuples(index=False):
        vals = []
        for valor in row:
            if isinstance(valor, float):
                vals.append(f"{valor:.2f}")
            else:
                vals.append(str(valor))
        linhas.append("| " + " | ".join(vals) + " |")
    return linhas


def resumo_ranking():
    ranking = pd.read_csv(ARQ_RANKING)
    base = ranking[
        ranking["trades_365"].between(230, 250)
        & (ranking["winrate_365"] >= 85)
        & (ranking["pontos_2024"] > 0)
        & (ranking["pontos_2025"] > 0)
        & (ranking["pontos_2026"] > 0)
    ].copy()
    base["min_win_anos"] = base[["winrate_2024", "winrate_2025", "winrate_2026"]].min(axis=1)
    base["todos_anos_80"] = base["min_win_anos"] >= 80
    base["todos_anos_85"] = base["min_win_anos"] >= 85
    melhor_pior_ano = base.sort_values(
        ["min_win_anos", "winrate_365", "pontos_365"],
        ascending=False,
    ).head(10)
    recortes = base[
        (base["winrate_90"] >= 85)
        & (base["winrate_30"] >= 85)
        & (base["pontos_90"] > 0)
        & (base["pontos_30"] > 0)
    ].sort_values(["winrate_30", "winrate_90", "pontos_365"], ascending=False).head(10)
    return base, melhor_pior_ano, recortes


def escrever_md(resumo_df, recortes_df, meses_df, melhor_pior_ano, recortes_ranking, universo):
    cols_recortes = ["perfil", "periodo", "trades", "winrate", "pontos", "dd", "pf"]
    cols_resumo = [
        "perfil",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
        "trades_2024",
        "winrate_2024",
        "pontos_2024",
        "trades_2025",
        "winrate_2025",
        "pontos_2025",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
    ]
    cols_ranking = [
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
        "winrate_2024",
        "winrate_2025",
        "winrate_2026",
        "winrate_90",
        "winrate_30",
        "min_win_anos",
        "filtros",
    ]
    linhas = [
        "# Auditoria Calendario DOW 230-85",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "## Resumo",
        "",
    ]
    linhas.extend(tabela_md(resumo_df, cols_resumo))
    linhas.extend(["", "## Recortes Dos Perfis", ""])
    linhas.extend(tabela_md(recortes_df, cols_recortes))
    linhas.extend(["", "## Melhores Do Ranking Para Pior Ano", ""])
    linhas.extend(tabela_md(melhor_pior_ano, cols_ranking, 10))
    linhas.extend(["", "## Melhores Do Ranking Com 90d E 30d Fortes", ""])
    linhas.extend(tabela_md(recortes_ranking, cols_ranking, 10))
    linhas.extend(
        [
            "",
            "## Diagnostico",
            "",
            f"- Candidatos no universo 230-250 trades, 85%+ em 365d e anos positivos: {len(universo)}.",
            f"- Candidatos com todos os anos acima de 80%: {int(universo['todos_anos_80'].sum())}.",
            f"- Candidatos com todos os anos acima de 85%: {int(universo['todos_anos_85'].sum())}.",
            "- O melhor pior-ano encontrado neste refino fica abaixo de 80%; portanto, a familia atual ainda tem risco de overfitting em 2024.",
            "- O perfil 02 melhora os recortes recentes, mas nao corrige a queda dos anos completos.",
            "",
            "## Arquivos",
            "",
            f"- `{ARQ_RESUMO.name}`",
            f"- `{ARQ_MESES.name}`",
            f"- `{ARQ_TRADES.name}`",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    candles = preparar_candles()
    base = montar_base(candles)
    trades_lista = []
    resumo = []
    recortes = []
    for perfil in PERFIS:
        trades, row, rec = auditar_perfil(base, perfil)
        trades_lista.append(trades)
        resumo.append(row)
        recortes.extend(rec)

    trades_df = pd.concat(trades_lista, ignore_index=True)
    resumo_df = pd.DataFrame(resumo)
    recortes_df = pd.DataFrame(recortes)
    meses_df = (
        trades_df.assign(mes=trades_df["datahora_entrada"].dt.to_period("M").astype(str))
        .groupby(["perfil", "mes"], dropna=False)
        .apply(lambda g: pd.Series(metricas_df(g)))
        .reset_index()
    )
    universo, melhor_pior_ano, recortes_ranking = resumo_ranking()

    resumo_df.to_csv(ARQ_RESUMO, index=False)
    meses_df.to_csv(ARQ_MESES, index=False)
    trades_df.to_csv(ARQ_TRADES, index=False)
    escrever_md(resumo_df, recortes_df, meses_df, melhor_pior_ano, recortes_ranking, universo)

    print("Resumo perfis:")
    print(
        resumo_df[
            [
                "perfil",
                "trades_365",
                "winrate_365",
                "pontos_365",
                "dd_365",
                "pf_365",
                "winrate_2024",
                "winrate_2025",
                "winrate_2026",
            ]
        ].to_string(index=False)
    )
    print("\nUniverso:", len(universo))
    print("Todos anos >=80:", int(universo["todos_anos_80"].sum()))
    print("Todos anos >=85:", int(universo["todos_anos_85"].sum()))
    print("Arquivos:")
    print(ARQ_MD)
    print(ARQ_RESUMO)
    print(ARQ_MESES)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
