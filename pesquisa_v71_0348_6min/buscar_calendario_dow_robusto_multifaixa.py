from itertools import combinations
from pathlib import Path

import pandas as pd

from buscar_calendario_dow_horario_230_250 import add_metricas
from buscar_regime_dia_230_250 import preparar_candles
from refinar_calendario_dow_230_85 import (
    aplicar_filtros,
    descreve_filtros,
    gerar_filtros,
    montar_base,
)


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "busca_calendario_dow_robusto_multifaixa_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "busca_calendario_dow_robusto_multifaixa_trades_top.csv"
ARQ_MD = SAIDA_DIR / "BUSCA_CALENDARIO_DOW_ROBUSTO_MULTIFAIXA.md"

TOP_SINGLES = 220
TOP_PARES = 160
MAX_COMBOS_3 = 45000


def min_metricas_anos(row):
    wins = [row[f"winrate_{ano}"] for ano in (2024, 2025, 2026)]
    pontos = [row[f"pontos_{ano}"] for ano in (2024, 2025, 2026)]
    return min(wins), min(pontos)


def score_robusto(row):
    min_win, min_pontos = min_metricas_anos(row)
    trades = row["trades_365"]
    if 170 <= trades <= 260:
        penal_freq = 0
    elif trades < 170:
        penal_freq = (170 - trades) * 70
    else:
        penal_freq = (trades - 260) * 120

    penal_anos = sum(max(0.0, 80.0 - row[f"winrate_{ano}"]) * 950 for ano in (2024, 2025, 2026))
    penal_pontos = sum(max(0.0, -row[f"pontos_{ano}"]) * 5 for ano in (2024, 2025, 2026))
    penal_recente = max(0.0, 82.0 - row["winrate_365"]) * 900

    return (
        row["pontos_365"]
        + row["pontos_all"] * 0.16
        + row["winrate_365"] * 40
        + min(row["pf_365"], 5.0) * 260
        + min_win * 120
        + max(0.0, min_pontos) * 0.35
        - abs(row["dd_365"]) * 0.65
        - penal_freq
        - penal_anos
        - penal_pontos
        - penal_recente
    )


def assinatura(filtros):
    return " ; ".join(f"{a}|{b}|{c}|{d:.8f}" for a, b, c, d in sorted(filtros))


def filtros_validos(filtros):
    por_campo = {}
    for token, coluna, op, valor in filtros:
        chave = (token, coluna)
        limites = por_campo.setdefault(chave, {"GE": None, "LE": None})
        atual = limites[op]
        if atual is None:
            limites[op] = valor
        elif op == "GE":
            limites[op] = max(atual, valor)
        else:
            limites[op] = min(atual, valor)
    for limites in por_campo.values():
        if limites["GE"] is not None and limites["LE"] is not None and limites["GE"] > limites["LE"]:
            return False
    return True


def avaliar(nome, base, filtros):
    trades = aplicar_filtros(base, filtros)
    row = {"cenario": nome, "filtros": descreve_filtros(filtros), "qtd_filtros": len(filtros)}
    add_metricas(row, trades)
    row["min_win_anos"], row["min_pontos_anos"] = min_metricas_anos(row)
    row["todos_anos_80"] = bool(row["min_win_anos"] >= 80)
    row["todos_anos_positivos"] = bool(row["min_pontos_anos"] > 0)
    row["score_robusto"] = score_robusto(row)
    return row, trades


def selecionar_singles(ranking):
    partes = [
        ranking.sort_values(["score_robusto", "min_win_anos", "winrate_365"], ascending=False).head(TOP_SINGLES),
        ranking.sort_values(["winrate_2024", "pontos_2024", "winrate_365"], ascending=False).head(TOP_SINGLES // 2),
        ranking.sort_values(["winrate_365", "pontos_365"], ascending=False).head(TOP_SINGLES // 2),
        ranking[ranking["trades_365"].between(170, 260)]
        .sort_values(["min_win_anos", "score_robusto"], ascending=False)
        .head(TOP_SINGLES // 2),
    ]
    out = pd.concat(partes, ignore_index=True)
    return out.drop_duplicates("assinatura").head(TOP_SINGLES)


def tabela_md(df, colunas, limite=20):
    if df.empty:
        return ["Nenhum cenario encontrado."]
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join(["---"] * len(colunas)) + " |",
    ]
    for row in df[colunas].head(limite).itertuples(index=False):
        valores = []
        for valor in row:
            if isinstance(valor, float):
                valores.append(f"{valor:.2f}")
            else:
                valores.append(str(valor))
        linhas.append("| " + " | ".join(valores) + " |")
    return linhas


def escrever_markdown(ranking):
    cols = [
        "cenario",
        "qtd_filtros",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
        "min_win_anos",
        "trades_2024",
        "winrate_2024",
        "pontos_2024",
        "trades_2025",
        "winrate_2025",
        "pontos_2025",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
        "filtros",
    ]
    robustos_80 = ranking[
        ranking["trades_365"].between(120, 280)
        & ranking["todos_anos_80"]
        & ranking["todos_anos_positivos"]
        & (ranking["winrate_365"] >= 82)
    ].sort_values(["winrate_365", "trades_365", "pontos_365"], ascending=False)
    robustos_85_365 = robustos_80[robustos_80["winrate_365"] >= 85]
    alta_freq = ranking[
        ranking["trades_365"].between(220, 260)
        & (ranking["winrate_365"] >= 85)
        & ranking["todos_anos_80"]
        & ranking["todos_anos_positivos"]
    ].sort_values(["winrate_365", "min_win_anos", "trades_365", "pontos_365"], ascending=False)
    linhas = [
        "# Busca Calendario DOW Robusto Multifaixa",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Objetivo: testar se a mesma familia do Calendario DOW melhora quando a frequencia deixa de ser travada em 230-250 trades.",
        "A ordenacao prioriza pior ano, anos positivos e depois metricas recentes.",
        "",
        "## Robustez anual 80%+ e 365d 85%+",
        "",
    ]
    linhas.extend(tabela_md(robustos_85_365, cols, 20))
    linhas.extend(["", "## Robustez anual 80%+ e 365d 82%+", ""])
    linhas.extend(tabela_md(robustos_80, cols, 20))
    linhas.extend(["", "## Alta frequencia 220-260 e 365d 85%+", ""])
    linhas.extend(tabela_md(alta_freq, cols, 20))
    linhas.extend(["", "## Top geral por score robusto", ""])
    linhas.extend(tabela_md(ranking.sort_values(["score_robusto", "winrate_365"], ascending=False), cols, 25))
    linhas.extend(
        [
            "",
            "## Leitura",
            "",
            f"- Cenarios avaliados: {len(ranking)}.",
            f"- Cenarios com anos 80%+, anos positivos, 120-280 trades e 365d >=85%: {len(robustos_85_365)}.",
            f"- Cenarios com anos 80%+, anos positivos, 120-280 trades e 365d >=82%: {len(robustos_80)}.",
            "- Se a primeira tabela ficar vazia, a meta de 85% recente com estabilidade anual ainda nao apareceu nesta familia.",
            "- Mesmo quando aparecer candidato, ele precisa ser convertido/validado no TradingView antes de qualquer uso operacional.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    candles = preparar_candles()
    base = montar_base(candles)
    filtros = gerar_filtros(base)
    print("Trades base brutos:", len(base), flush=True)
    print("Filtros simples:", len(filtros), flush=True)

    linhas = []
    trades_top = pd.DataFrame()
    melhor_score = -10**18

    row, trades = avaliar("base_sem_filtro", base, tuple())
    row["assinatura"] = assinatura(tuple())
    linhas.append(row)
    trades_top = trades.assign(cenario=row["cenario"])
    melhor_score = row["score_robusto"]

    single_rows = []
    single_map = {}
    for filtro in filtros:
        filtros_tuple = (filtro,)
        row, trades = avaliar("filtro_1", base, filtros_tuple)
        row["assinatura"] = assinatura(filtros_tuple)
        linhas.append(row)
        single_rows.append(row)
        single_map[row["assinatura"]] = filtros_tuple
        if row["score_robusto"] > melhor_score:
            melhor_score = row["score_robusto"]
            trades_top = trades.assign(cenario=row["cenario"])

    singles_rank = selecionar_singles(pd.DataFrame(single_rows))
    top_filtros = [single_map[row.assinatura] for row in singles_rank.itertuples(index=False)]

    pares = []
    vistos = {row["assinatura"] for row in linhas}
    for (f1,), (f2,) in combinations(top_filtros, 2):
        filtros_tuple = (f1, f2)
        if not filtros_validos(filtros_tuple):
            continue
        ass = assinatura(filtros_tuple)
        if ass in vistos:
            continue
        vistos.add(ass)
        row, trades = avaliar("filtro_2", base, filtros_tuple)
        row["assinatura"] = ass
        linhas.append(row)
        pares.append(row)
        if row["score_robusto"] > melhor_score:
            melhor_score = row["score_robusto"]
            trades_top = trades.assign(cenario=row["cenario"])

    pares_rank = (
        pd.DataFrame(pares)
        .sort_values(["score_robusto", "min_win_anos", "winrate_365"], ascending=False)
        .head(TOP_PARES)
    )
    pares_map = {
        row.assinatura: tuple(
            (parte.split(" ")[0], parte.split(" ")[1], parte.split(" ")[2], float(parte.split(" ")[3]))
            for parte in row.filtros.split(" ; ")
        )
        for row in pares_rank.itertuples(index=False)
    }
    combos3 = 0
    for row_par in pares_rank.itertuples(index=False):
        f_par = pares_map[row_par.assinatura]
        usados = set(f_par)
        for (f3,) in top_filtros:
            if f3 in usados:
                continue
            filtros_tuple = tuple(sorted(f_par + (f3,)))
            if not filtros_validos(filtros_tuple):
                continue
            ass = assinatura(filtros_tuple)
            if ass in vistos:
                continue
            vistos.add(ass)
            row, trades = avaliar("filtro_3", base, filtros_tuple)
            row["assinatura"] = ass
            linhas.append(row)
            combos3 += 1
            if row["score_robusto"] > melhor_score:
                melhor_score = row["score_robusto"]
                trades_top = trades.assign(cenario=row["cenario"])
            if combos3 >= MAX_COMBOS_3:
                break
        if combos3 >= MAX_COMBOS_3:
            break

    ranking = (
        pd.DataFrame(linhas)
        .drop_duplicates("filtros")
        .sort_values(["score_robusto", "min_win_anos", "winrate_365"], ascending=False)
    )
    ranking.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES, index=False)
    escrever_markdown(ranking)

    cols = [
        "cenario",
        "qtd_filtros",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
        "min_win_anos",
        "winrate_2024",
        "winrate_2025",
        "winrate_2026",
        "filtros",
    ]
    print("Combos 3 avaliados:", combos3, flush=True)
    print(ranking[cols].head(30).to_string(index=False, max_colwidth=180), flush=True)
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_TRADES)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
