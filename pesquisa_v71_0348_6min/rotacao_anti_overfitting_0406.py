from pathlib import Path
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"

ARQ_XLSX = PESQUISA_DIR / "rotacao_anti_overfitting_0406.xlsx"
ARQ_RANKING = PESQUISA_DIR / "rotacao_anti_overfitting_0406_ranking.csv"
ARQ_TESTES = PESQUISA_DIR / "rotacao_anti_overfitting_0406_testes.csv"

ALVO_WINRATE = 85.34
MIN_TRADES_TREINO = 30
MIN_TRADES_TESTE = 8
TOP_N_TREINO_POR_FOLD = 15

HORARIOS = ["04:00", "04:06", "04:12"]
SETUPS = ["V71_OFICIAL_505_117"]
CUSTOS_POR_TRADE = [0.0, 2.0]


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


def resumir(trades, custo=0.0):
    if trades.empty:
        return None
    pts = trades["pontos"].astype(float) - float(custo)
    mensal = trades.assign(pontos_liq=pts).groupby("periodo_mes")["pontos_liq"].sum()
    wr = float((trades["resultado"] == "TAKE").mean() * 100.0)
    return {
        "trades": int(len(trades)),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "winrate": wr,
        "pontos": float(pts.sum()),
        "max_drawdown": max_drawdown(pts),
        "profit_factor": profit_factor(pts),
        "media_pontos": float(pts.mean()),
        "meses_total": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "melhor_mes": float(mensal.max()) if len(mensal) else 0.0,
    }


def score_treino(row):
    return (
        row["pontos"]
        + row["winrate"] * 35.0
        + min(row["profit_factor"], 8.0) * 300.0
        + row["trades"] * 4.0
        - abs(row["max_drawdown"]) * 2.5
        - row["meses_negativos"] * 350.0
        - max(0.0, ALVO_WINRATE - row["winrate"]) * 100.0
    )


def carregar_base():
    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df["ano"] = df["DataHora_SP"].dt.year
    df["periodo_mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)
    df = df[
        df["setup"].isin(SETUPS)
        & df["hhmm"].isin(HORARIOS)
        & df["direcao_reversao_20"].isin(["BUY", "SELL"])
        & (df["Direcao"] == df["direcao_reversao_20"])
    ].copy()

    df["range_ratio_10"] = df["range"] / df["range_med_10"].replace(0, np.nan)
    df["vol_ratio_10"] = df["volume"] / df["vol_med_10"].replace(0, np.nan)
    df["body_range_pct"] = df["body_abs"] / df["range"].replace(0, np.nan)
    df["dist_ema20_abs"] = df["dist_ema_20"].abs()
    df["extremo_reversao"] = np.where(df["Direcao"] == "BUY", 1.0 - df["pos_range_20"], df["pos_range_20"])
    df["contra_tendencia"] = df["direcao_tendencia"] != df["Direcao"]
    df["mesmo_sentido_candle"] = df["direcao_candle"] == df["Direcao"]
    return df.replace([np.inf, -np.inf], np.nan).sort_values("DataHora_SP").reset_index(drop=True)


def aplicar_condicoes(df, conds):
    mask = pd.Series(True, index=df.index)
    partes = []
    for col, op, valor in conds:
        if col not in df.columns:
            return df.iloc[0:0], "coluna_inexistente"
        if op == "==":
            mask &= df[col] == valor
        elif op == "!=":
            mask &= df[col] != valor
        else:
            s = pd.to_numeric(df[col], errors="coerce")
            if op == ">=":
                mask &= s >= float(valor)
            elif op == "<=":
                mask &= s <= float(valor)
        partes.append(f"{col}{op}{valor}")
    return df[mask].copy(), " & ".join(partes) if partes else "sem_filtro"


def gerar_condicoes():
    specs = [
        ("rsi_14", "<=", [35, 40, 45, 50]),
        ("range_ratio_10", ">=", [0.5, 0.7, 0.9, 1.1]),
        ("range_ratio_10", "<=", [1.1, 1.3, 1.5]),
        ("vol_ratio_10", ">=", [0.7, 0.9, 1.1]),
        ("body_range_pct", ">=", [0.2, 0.3, 0.4]),
        ("dist_ema20_abs", ">=", [5, 10, 20, 30]),
        ("extremo_reversao", ">=", [0.65, 0.7, 0.75, 0.8]),
        ("mesmo_sentido_candle", "==", [False]),
    ]
    atomos = [(c, op, v) for c, op, vals in specs for v in vals]
    conds = [[]] + [[a] for a in atomos]
    for tam in [2]:
        for combo in itertools.combinations(atomos, tam):
            cols = [x[0] for x in combo]
            if len(set(cols)) == len(cols):
                conds.append(list(combo))
    extras = [
        [("range_ratio_10", "<=", 1.5), ("extremo_reversao", ">=", 0.8), ("mesmo_sentido_candle", "==", False)],
        [("rsi_14", "<=", 40), ("range_ratio_10", ">=", 0.7)],
        [("rsi_14", "<=", 40), ("range_ratio_10", ">=", 0.7), ("dist_ema20_abs", ">=", 5)],
        [("rsi_14", "<=", 45), ("range_ratio_10", ">=", 0.7), ("body_range_pct", ">=", 0.2)],
    ]
    return conds + extras


def gerar_condicoes_refino(ranking_previo):
    if ranking_previo.empty:
        return []

    filtros = ranking_previo["filtro"].head(80).tolist()
    atomos = []
    for filtro in filtros:
        if filtro == "sem_filtro":
            continue
        for parte in filtro.split(" & "):
            for op in ["==", ">=", "<="]:
                if op in parte:
                    col, valor = parte.split(op)
                    valor = valor.strip()
                    if valor == "True":
                        valor = True
                    elif valor == "False":
                        valor = False
                    else:
                        valor = float(valor)
                    atomos.append((col.strip(), op, valor))
                    break

    atomos_unicos = []
    vistos = set()
    for a in atomos:
        if a not in vistos:
            atomos_unicos.append(a)
            vistos.add(a)

    conds = []
    for combo in itertools.combinations(atomos_unicos, 3):
        cols = [x[0] for x in combo]
        if len(set(cols)) == len(cols):
            conds.append(list(combo))
    return conds[:2500]


def folds_rotacao():
    return [
        ("treina_2024_testa_2025", ["2024"], ["2025"]),
        ("treina_2024_2025_testa_2026", ["2024", "2025"], ["2026"]),
        ("treina_2024Q4_2025Q1_testa_2025Q2", ["2024-10", "2024-11", "2024-12", "2025-01", "2025-02", "2025-03"], ["2025-04", "2025-05", "2025-06"]),
        ("treina_2025H1_testa_2025H2", ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"], ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]),
    ]


def filtrar_periodos(df, periodos):
    anos = {int(p) for p in periodos if len(p) == 4}
    meses = {p for p in periodos if len(p) == 7}
    mask = pd.Series(False, index=df.index)
    if anos:
        mask |= df["ano"].isin(anos)
    if meses:
        mask |= df["periodo_mes"].isin(meses)
    return df[mask].copy()


def selecionar_no_treino(treino, conds):
    linhas = []
    for hhmm in HORARIOS:
        for setup in SETUPS:
            base_cfg = treino[(treino["hhmm"] == hhmm) & (treino["setup"] == setup)].copy()
            if len(base_cfg) < MIN_TRADES_TREINO:
                continue
            for custo in CUSTOS_POR_TRADE:
                for cond in conds:
                    filtrado, filtro = aplicar_condicoes(base_cfg, cond)
                    if len(filtrado) < MIN_TRADES_TREINO:
                        continue
                    row = resumir(filtrado, custo)
                    if row is None or row["pontos"] <= 0 or row["profit_factor"] < 1.15:
                        continue
                    row.update({
                        "hhmm": hhmm,
                        "setup": setup,
                        "custo_por_trade": custo,
                        "filtro": filtro,
                        "cond": cond,
                    })
                    row["score_treino"] = score_treino(row)
                    linhas.append(row)
    rank = pd.DataFrame(linhas)
    if rank.empty:
        return rank
    return rank.sort_values(["score_treino", "winrate", "pontos"], ascending=[False, False, False]).reset_index(drop=True)


def avaliar_rotacoes(base, conds):
    resultados = []
    for nome_fold, periodos_treino, periodos_teste in folds_rotacao():
        treino = filtrar_periodos(base, periodos_treino)
        teste = filtrar_periodos(base, periodos_teste)
        rank = selecionar_no_treino(treino, conds)
        if rank.empty:
            continue
        for pos, cand in rank.head(TOP_N_TREINO_POR_FOLD).reset_index(drop=True).iterrows():
            teste_cfg = teste[(teste["hhmm"] == cand["hhmm"]) & (teste["setup"] == cand["setup"])].copy()
            filtrado_teste, _ = aplicar_condicoes(teste_cfg, cand["cond"])
            if len(filtrado_teste) < MIN_TRADES_TESTE:
                continue
            rt = resumir(filtrado_teste, cand["custo_por_trade"])
            if rt is None:
                continue
            rt.update({
                "fold": nome_fold,
                "periodos_treino": ",".join(periodos_treino),
                "periodos_teste": ",".join(periodos_teste),
                "rank_treino": int(pos + 1),
                "hhmm": cand["hhmm"],
                "setup": cand["setup"],
                "custo_por_trade": cand["custo_por_trade"],
                "filtro": cand["filtro"],
                "trades_treino": int(cand["trades"]),
                "winrate_treino": float(cand["winrate"]),
                "pontos_treino": float(cand["pontos"]),
                "pf_treino": float(cand["profit_factor"]),
                "score_treino": float(cand["score_treino"]),
            })
            resultados.append(rt)
    return pd.DataFrame(resultados)


def agregar_robustez(testes):
    if testes.empty:
        return pd.DataFrame()
    keys = ["hhmm", "setup", "custo_por_trade", "filtro"]
    linhas = []
    for key, g in testes.groupby(keys):
        row = {
            "hhmm": key[0],
            "setup": key[1],
            "custo_por_trade": key[2],
            "filtro": key[3],
            "folds": int(len(g)),
            "folds_positivos": int((g["pontos"] > 0).sum()),
            "folds_winrate_85": int((g["winrate"] >= ALVO_WINRATE).sum()),
            "trades_teste_total": int(g["trades"].sum()),
            "winrate_medio_teste": float(np.average(g["winrate"], weights=g["trades"])),
            "pontos_teste_total": float(g["pontos"].sum()),
            "pior_fold_pontos": float(g["pontos"].min()),
            "pior_fold_winrate": float(g["winrate"].min()),
            "max_dd_pior_fold": float(g["max_drawdown"].min()),
            "pf_medio_teste": float(g["profit_factor"].replace(999.0, np.nan).mean()),
            "meses_negativos_total": int(g["meses_negativos"].sum()),
            "score_teste_robusto": float(
                g["pontos"].sum()
                + np.average(g["winrate"], weights=g["trades"]) * 35
                + (g["pontos"] > 0).sum() * 500
                + (g["winrate"] >= ALVO_WINRATE).sum() * 250
                - abs(g["max_drawdown"].min()) * 2
                - g["meses_negativos"].sum() * 250
            ),
        }
        linhas.append(row)
    out = pd.DataFrame(linhas)
    return out.sort_values(
        ["folds_positivos", "score_teste_robusto", "winrate_medio_teste", "pontos_teste_total"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def executar(base, conds):
    testes = avaliar_rotacoes(base, conds)
    ranking = agregar_robustez(testes)
    return ranking, testes


def main():
    print("=====================================================")
    print("ROTACAO ANTI-OVERFITTING - 6MIN REVERSAO")
    print("=====================================================")
    base = carregar_base()
    conds = gerar_condicoes()
    print("Base:", len(base), "Filtros etapa 1:", len(conds), "Horarios:", HORARIOS)

    ranking1, testes1 = executar(base, conds)
    conds_refino = gerar_condicoes_refino(ranking1)
    print("Filtros etapa 2:", len(conds_refino))

    if conds_refino:
        ranking2, testes2 = executar(base, conds_refino)
        testes = pd.concat([testes1, testes2], ignore_index=True)
        ranking = agregar_robustez(testes)
    else:
        testes = testes1
        ranking = ranking1

    testes.to_csv(ARQ_TESTES, index=False)
    ranking.to_csv(ARQ_RANKING, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking_robusto", index=False)
        testes.to_excel(writer, sheet_name="testes_por_fold", index=False)

    print("\nTOP 20 ROBUSTEZ")
    if ranking.empty:
        print("Sem resultados.")
    else:
        cols = [
            "hhmm", "setup", "custo_por_trade", "filtro", "folds", "folds_positivos",
            "folds_winrate_85", "trades_teste_total", "winrate_medio_teste",
            "pontos_teste_total", "pior_fold_pontos", "max_dd_pior_fold",
        ]
        print(ranking[cols].head(20).to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TESTES)


if __name__ == "__main__":
    main()
