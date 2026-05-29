from pathlib import Path
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"
ARQ_RANKING = PESQUISA_DIR / "refino_0406_alvo_85_ranking.csv"
ARQ_TRADES = PESQUISA_DIR / "refino_0406_alvo_85_trades_top.csv"
ARQ_XLSX = PESQUISA_DIR / "refino_0406_alvo_85.xlsx"

ALVO_WINRATE = 85.34


def max_drawdown(pontos):
    if len(pontos) == 0:
        return 0.0
    eq = np.cumsum(np.asarray(pontos, dtype=float))
    pico = np.maximum.accumulate(eq)
    return float((eq - pico).min())


def profit_factor(pontos):
    pontos = pd.Series(pontos, dtype=float)
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0
    return ganhos / perdas


def resumo(trades, nome, filtro):
    if trades.empty:
        return None
    pontos = trades["pontos"].astype(float)
    wr = float((trades["resultado"] == "TAKE").mean() * 100.0)
    mensal = trades.groupby("mes")["pontos"].sum()
    return {
        "nome": nome,
        "filtro": filtro,
        "trades": int(len(trades)),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "winrate": wr,
        "distancia_alvo_85_34": abs(wr - ALVO_WINRATE),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "meses_total": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "melhor_mes": float(mensal.max()) if len(mensal) else 0.0,
    }


def carregar_base_0406():
    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df["ano"] = df["DataHora_SP"].dt.year
    df["mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)

    base = df[
        (df["setup"] == "V71_OFICIAL_505_117")
        & (df["hhmm"] == "04:06")
        & (df["direcao_reversao_20"].isin(["BUY", "SELL"]))
        & (df["Direcao"] == df["direcao_reversao_20"])
    ].copy()

    base["range_ratio_3"] = base["range"] / base["range_med_3"].replace(0, np.nan)
    base["range_ratio_10"] = base["range"] / base["range_med_10"].replace(0, np.nan)
    base["vol_ratio_10"] = base["volume"] / base["vol_med_10"].replace(0, np.nan)
    base["body_range_pct"] = base["body_abs"] / base["range"].replace(0, np.nan)
    base["dist_ema20_abs"] = base["dist_ema_20"].abs()
    base["dist_open_abs"] = base["dist_open_dia"].abs()
    base["extremo_reversao"] = np.where(
        base["Direcao"] == "BUY",
        1.0 - base["pos_range_20"],
        base["pos_range_20"],
    )
    base["tendencia_contra_reversao"] = base["direcao_tendencia"] != base["Direcao"]
    base = base.replace([np.inf, -np.inf], np.nan)
    return base.sort_values("DataHora_SP").reset_index(drop=True)


def aplicar_condicoes(df, conds):
    mask = pd.Series(True, index=df.index)
    textos = []
    for col, op, valor in conds:
        if col not in df.columns:
            return df.iloc[0:0], "coluna_inexistente"
        serie = pd.to_numeric(df[col], errors="coerce")
        if op == ">=":
            mask &= serie >= valor
        elif op == "<=":
            mask &= serie <= valor
        elif op == ">":
            mask &= serie > valor
        elif op == "<":
            mask &= serie < valor
        textos.append(f"{col}{op}{valor}")
    return df[mask].copy(), " & ".join(textos) if textos else "sem_filtro"


def gerar_condicoes_quantis(df):
    specs = [
        ("extremo_reversao", ">=", [0.55, 0.60, 0.65, 0.70, 0.75]),
        ("pos_range_20", "<=", [0.20, 0.25, 0.30, 0.35, 0.40]),
        ("pos_range_20", ">=", [0.60, 0.65, 0.70, 0.75, 0.80]),
        ("rsi_14", "<=", [30, 35, 40, 45]),
        ("rsi_14", ">=", [55, 60, 65, 70]),
        ("range_ratio_10", ">=", [0.7, 0.9, 1.1, 1.3]),
        ("range_ratio_10", "<=", [0.7, 0.9, 1.1, 1.3]),
        ("body_range_pct", "<=", [0.25, 0.35, 0.45, 0.55]),
        ("dist_ema20_abs", ">=", [10, 20, 30, 40, 50]),
        ("dist_open_abs", ">=", [20, 40, 60, 80, 100]),
        ("vol_ratio_10", ">=", [0.7, 0.9, 1.1, 1.3]),
    ]

    conds = []
    for col, op, valores in specs:
        for v in valores:
            conds.append([(col, op, v)])

    # Combina apenas condicoes de colunas diferentes para reduzir ajuste excessivo.
    simples = list(conds)
    for a, b in itertools.combinations([c[0] for c in conds], 2):
        if a[0] != b[0]:
            simples.append([a, b])
    for a, b, c in itertools.combinations([c[0] for c in conds], 3):
        if len({a[0], b[0], c[0]}) == 3:
            simples.append([a, b, c])

    return simples


def avaliar_walkforward(df, conds):
    # Escolhe filtro em 2024 e testa 2025; depois escolhe em 2024/2025 e testa 2026.
    folds = [
        ("treina_2024_testa_2025", [2024], 2025),
        ("treina_2024_2025_testa_2026", [2024, 2025], 2026),
    ]
    linhas = []
    trades_top = []

    for nome_fold, anos_treino, ano_teste in folds:
        treino = df[df["ano"].isin(anos_treino)].copy()
        teste = df[df["ano"] == ano_teste].copy()
        candidatos_fold = []

        for cond in conds:
            tr, filtro_txt = aplicar_condicoes(treino, cond)
            if len(tr) < 20:
                continue
            row = resumo(tr, "treino", filtro_txt)
            if row is None:
                continue
            # Busca assertividade, mas exige lucro e alguma frequencia.
            if row["pontos"] <= 0 or row["profit_factor"] < 1.15:
                continue
            row["condicoes"] = cond
            candidatos_fold.append(row)

        if not candidatos_fold:
            continue

        rank_treino = pd.DataFrame(candidatos_fold).sort_values(
            ["winrate", "pontos", "trades"],
            ascending=[False, False, False],
        )

        for pos, cand in rank_treino.head(30).reset_index(drop=True).iterrows():
            te, filtro_txt = aplicar_condicoes(teste, cand["condicoes"])
            if len(te) < 5:
                continue
            row = resumo(te, f"{nome_fold}_rank{pos+1}", filtro_txt)
            row.update({
                "fold": nome_fold,
                "anos_treino": ",".join(map(str, anos_treino)),
                "ano_teste": ano_teste,
                "rank_treino": int(pos + 1),
                "trades_treino": int(cand["trades"]),
                "winrate_treino": float(cand["winrate"]),
                "pontos_treino": float(cand["pontos"]),
                "profit_factor_treino": float(cand["profit_factor"]),
            })
            linhas.append(row)
            top = te.copy()
            top["fold"] = nome_fold
            top["rank_treino"] = int(pos + 1)
            top["filtro_refino"] = filtro_txt
            top["nome_refino"] = row["nome"]
            trades_top.append(top)

    ranking = pd.DataFrame(linhas)
    if ranking.empty:
        return ranking, pd.DataFrame()

    ranking = ranking.sort_values(
        ["winrate", "pontos", "profit_factor", "trades"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    trades = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()
    return ranking, trades


def avaliar_periodo_todo(df, conds):
    linhas = [resumo(df, "base_sem_refino", "sem_filtro")]
    trades_top = []

    for cond in conds:
        filtrado, filtro_txt = aplicar_condicoes(df, cond)
        if len(filtrado) < 50:
            continue
        row = resumo(filtrado, "periodo_todo", filtro_txt)
        if row is None or row["pontos"] <= 0:
            continue
        linhas.append(row)

    ranking = pd.DataFrame(linhas).sort_values(
        ["winrate", "pontos", "profit_factor", "trades"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    for _, row in ranking.head(20).iterrows():
        filtrado = df.copy() if row["filtro"] == "sem_filtro" else aplicar_condicoes_texto(df, row["filtro"])
        filtrado["nome_refino"] = row["nome"]
        filtrado["filtro_refino"] = row["filtro"]
        trades_top.append(filtrado)

    trades = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()
    return ranking, trades


def aplicar_condicoes_texto(df, texto):
    if texto == "sem_filtro":
        return df.copy()
    conds = []
    for parte in texto.split(" & "):
        for op in [">=", "<=", ">", "<"]:
            if op in parte:
                col, valor = parte.split(op)
                conds.append((col, op, float(valor)))
                break
    return aplicar_condicoes(df, conds)[0]


def main():
    print("=====================================================")
    print("REFINO 04:06 REVERSAO - ALVO 85,34%")
    print("Nao altera o robo oficial.")
    print("=====================================================")

    base = carregar_base_0406()
    print("Base 04:06 reversao:", len(base))

    conds = gerar_condicoes_quantis(base)
    print("Filtros testados:", len(conds))

    ranking_todo, trades_todo = avaliar_periodo_todo(base, conds)
    ranking_wf, trades_wf = avaliar_walkforward(base, conds)

    ranking_todo["tipo_validacao"] = "periodo_todo_exploratorio"
    if not ranking_wf.empty:
        ranking_wf["tipo_validacao"] = "walkforward"

    ranking = pd.concat([ranking_wf, ranking_todo], ignore_index=True, sort=False)
    ranking = ranking.sort_values(
        ["tipo_validacao", "winrate", "pontos", "profit_factor", "trades"],
        ascending=[True, False, False, False, False],
    ).reset_index(drop=True)
    ranking.to_csv(ARQ_RANKING, index=False)

    trades = pd.concat([trades_wf, trades_todo], ignore_index=True, sort=False)
    trades.to_csv(ARQ_TRADES, index=False)

    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        ranking_todo.to_excel(writer, sheet_name="exploratorio_periodo_todo", index=False)
        ranking_wf.to_excel(writer, sheet_name="walkforward", index=False)
        trades.to_excel(writer, sheet_name="trades_top", index=False)

    print("\nTOP WALKFORWARD")
    if not ranking_wf.empty:
        cols = ["fold", "rank_treino", "filtro", "trades", "winrate", "pontos", "max_drawdown", "profit_factor", "winrate_treino"]
        print(ranking_wf[cols].head(15).to_string(index=False))
    else:
        print("Sem resultados walkforward.")

    print("\nTOP EXPLORATORIO PERIODO TODO")
    cols = ["filtro", "trades", "winrate", "pontos", "max_drawdown", "profit_factor", "meses_negativos"]
    print(ranking_todo[cols].head(15).to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
