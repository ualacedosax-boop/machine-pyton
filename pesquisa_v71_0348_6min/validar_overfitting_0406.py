from pathlib import Path
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"
ARQ_XLSX = PESQUISA_DIR / "validacao_overfitting_0406.xlsx"
ARQ_CSV = PESQUISA_DIR / "validacao_overfitting_0406.csv"


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


def score_multi(row):
    return (
        row["pontos"]
        + row["winrate"] * 25.0
        + min(row["profit_factor"], 10.0) * 350.0
        + row["trades"] * 3.0
        + row["meses_positivos"] * 120.0
        - abs(row["max_drawdown"]) * 2.0
        - row["meses_negativos"] * 350.0
        - max(0.0, ALVO_WINRATE - row["winrate"]) * 80.0
    )


def resumir(trades, nome, filtro, etapa):
    if trades.empty:
        return None
    pontos = trades["pontos"].astype(float)
    mensal = trades.groupby("mes")["pontos"].sum()
    wr = float((trades["resultado"] == "TAKE").mean() * 100.0)
    row = {
        "nome": nome,
        "etapa": etapa,
        "filtro": filtro,
        "trades": int(len(trades)),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "winrate": wr,
        "atingiu_85_34": bool(wr >= ALVO_WINRATE),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "melhor_mes": float(mensal.max()) if len(mensal) else 0.0,
    }
    row["score_multiobjetivo"] = score_multi(row)
    return row


def carregar_base():
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
    base["range_ratio_10"] = base["range"] / base["range_med_10"].replace(0, np.nan)
    base["extremo_reversao"] = np.where(
        base["Direcao"] == "BUY",
        1.0 - base["pos_range_20"],
        base["pos_range_20"],
    )
    base["mesmo_sentido_candle"] = base["direcao_candle"] == base["Direcao"]
    base["dist_ema20_abs"] = base["dist_ema_20"].abs()
    base["vol_ratio_10"] = base["volume"] / base["vol_med_10"].replace(0, np.nan)
    base["body_range_pct"] = base["body_abs"] / base["range"].replace(0, np.nan)
    base = base.replace([np.inf, -np.inf], np.nan)
    return base.sort_values("DataHora_SP").reset_index(drop=True)


def aplicar_condicoes(df, conds):
    mask = pd.Series(True, index=df.index)
    partes = []
    for col, op, valor in conds:
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
            elif op == ">":
                mask &= s > float(valor)
            elif op == "<":
                mask &= s < float(valor)
        partes.append(f"{col}{op}{valor}")
    return df[mask].copy(), " & ".join(partes) if partes else "sem_filtro"


def gerar_condicoes():
    specs = [
        ("rsi_14", "<=", [30, 35, 40, 45, 50]),
        ("range_ratio_10", ">=", [0.5, 0.7, 0.9, 1.1, 1.3]),
        ("range_ratio_10", "<=", [0.7, 0.9, 1.1, 1.3, 1.5]),
        ("vol_ratio_10", ">=", [0.5, 0.7, 0.9, 1.1, 1.3]),
        ("body_range_pct", "<=", [0.2, 0.3, 0.4, 0.5, 0.6]),
        ("body_range_pct", ">=", [0.2, 0.3, 0.4, 0.5, 0.6]),
        ("dist_ema20_abs", ">=", [5, 10, 20, 30, 40, 50]),
        ("extremo_reversao", ">=", [0.55, 0.6, 0.65, 0.7, 0.75, 0.8]),
        ("pos_range_20", "<=", [0.2, 0.25, 0.3, 0.35, 0.4]),
        ("mesmo_sentido_candle", "==", [True, False]),
    ]
    atomos = [(c, op, v) for c, op, vals in specs for v in vals]
    conds = [[]] + [[a] for a in atomos]
    for tam in [2, 3]:
        for combo in itertools.combinations(atomos, tam):
            cols = [c[0] for c in combo]
            if len(set(cols)) == len(cols):
                conds.append(list(combo))
    return conds


def escolher_no_treino(treino, conds):
    linhas = []
    for cond in conds:
        filtrado, filtro = aplicar_condicoes(treino, cond)
        if len(filtrado) < 20:
            continue
        row = resumir(filtrado, "treino", filtro, "treino")
        if row and row["pontos"] > 0 and row["profit_factor"] >= 1.15:
            row["cond"] = cond
            linhas.append(row)
    rank = pd.DataFrame(linhas)
    if rank.empty:
        return None, rank
    rank = rank.sort_values(
        ["score_multiobjetivo", "winrate", "pontos"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    return rank.iloc[0], rank


def main():
    print("=====================================================")
    print("VALIDACAO ANTI-OVERFITTING - 04:06")
    print("=====================================================")
    base = carregar_base()
    conds = gerar_condicoes()

    filtros_fixos = {
        "candidato_escolhido_periodo_todo": [
            ("range_ratio_10", "<=", 1.5),
            ("extremo_reversao", ">=", 0.8),
            ("mesmo_sentido_candle", "==", False),
        ],
        "filtro_simples_85": [
            ("rsi_14", "<=", 40),
            ("range_ratio_10", ">=", 0.7),
        ],
        "sem_filtro": [],
    }

    linhas = []
    for nome, cond in filtros_fixos.items():
        filtrado, filtro = aplicar_condicoes(base, cond)
        linhas.append(resumir(filtrado, nome, filtro, "periodo_todo"))
        for ano, g in filtrado.groupby("ano"):
            linhas.append(resumir(g, nome, filtro, f"ano_{int(ano)}"))

    folds = [
        ("escolhe_2024_testa_2025", [2024], 2025),
        ("escolhe_2024_2025_testa_2026", [2024, 2025], 2026),
    ]
    for nome_fold, anos_treino, ano_teste in folds:
        treino = base[base["ano"].isin(anos_treino)].copy()
        teste = base[base["ano"] == ano_teste].copy()
        best, rank = escolher_no_treino(treino, conds)
        if best is None:
            continue
        filtrado_teste, filtro = aplicar_condicoes(teste, best["cond"])
        row_teste = resumir(filtrado_teste, nome_fold, filtro, "teste_futuro")
        row_treino = resumir(aplicar_condicoes(treino, best["cond"])[0], nome_fold, filtro, "treino_escolha")
        if row_treino:
            row_treino["anos_treino"] = ",".join(map(str, anos_treino))
            row_treino["ano_teste"] = ano_teste
            linhas.append(row_treino)
        if row_teste:
            row_teste["anos_treino"] = ",".join(map(str, anos_treino))
            row_teste["ano_teste"] = ano_teste
            linhas.append(row_teste)

    out = pd.DataFrame([r for r in linhas if r is not None])
    out.to_csv(ARQ_CSV, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="validacao", index=False)

    print(out[[
        "nome", "etapa", "filtro", "trades", "winrate", "pontos",
        "max_drawdown", "profit_factor", "meses_negativos"
    ]].to_string(index=False))
    print("\nArquivos gerados:")
    print(ARQ_XLSX)
    print(ARQ_CSV)


if __name__ == "__main__":
    main()
