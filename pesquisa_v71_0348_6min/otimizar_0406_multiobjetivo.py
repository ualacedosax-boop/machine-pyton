from pathlib import Path
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"
ARQ_XLSX = PESQUISA_DIR / "otimizacao_0406_multiobjetivo.xlsx"
ARQ_RANKING = PESQUISA_DIR / "otimizacao_0406_multiobjetivo_ranking.csv"
ARQ_TRADES = PESQUISA_DIR / "otimizacao_0406_multiobjetivo_trades_top.csv"


MIN_TRADES_FORTE = 80
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
    # Pontua equilibrio: winrate e PF importam, mas punimos DD e meses ruins.
    return (
        row["pontos"] * 1.0
        + row["winrate"] * 25.0
        + min(row["profit_factor"], 10.0) * 350.0
        + row["trades"] * 3.0
        + row["meses_positivos"] * 120.0
        - abs(row["max_drawdown"]) * 2.0
        - row["meses_negativos"] * 350.0
        - max(0.0, ALVO_WINRATE - row["winrate"]) * 80.0
    )


def resumir(trades, nome, setup, filtro):
    if trades.empty:
        return None

    pontos = trades["pontos"].astype(float)
    mensal = trades.groupby("mes")["pontos"].sum()
    anual = trades.groupby("ano")["pontos"].sum()
    wr = float((trades["resultado"] == "TAKE").mean() * 100.0)

    row = {
        "nome": nome,
        "setup": setup,
        "filtro": filtro,
        "trades": int(len(trades)),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "winrate": wr,
        "atingiu_85_34": bool(wr >= ALVO_WINRATE),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "meses_total": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "melhor_mes": float(mensal.max()) if len(mensal) else 0.0,
        "anos_total": int(len(anual)),
        "anos_positivos": int((anual > 0).sum()),
        "pior_ano": float(anual.min()) if len(anual) else 0.0,
        "melhor_ano": float(anual.max()) if len(anual) else 0.0,
    }
    row["score_multiobjetivo"] = score_multi(row)
    return row


def carregar_0406_reversao():
    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df["ano"] = df["DataHora_SP"].dt.year
    df["mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)

    base = df[
        (df["hhmm"] == "04:06")
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
    base["contra_tendencia"] = base["direcao_tendencia"] != base["Direcao"]
    base["mesmo_sentido_candle"] = base["direcao_candle"] == base["Direcao"]
    base = base.replace([np.inf, -np.inf], np.nan)
    return base.sort_values("DataHora_SP").reset_index(drop=True)


def aplicar_condicoes(df, conds):
    mask = pd.Series(True, index=df.index)
    partes = []
    for col, op, valor in conds:
        if col not in df.columns:
            return df.iloc[0:0], "coluna_inexistente"

        if op in ["==", "!="]:
            if op == "==":
                mask &= df[col] == valor
            else:
                mask &= df[col] != valor
        else:
            serie = pd.to_numeric(df[col], errors="coerce")
            if op == ">=":
                mask &= serie >= float(valor)
            elif op == "<=":
                mask &= serie <= float(valor)
            elif op == ">":
                mask &= serie > float(valor)
            elif op == "<":
                mask &= serie < float(valor)

        partes.append(f"{col}{op}{valor}")

    return df[mask].copy(), " & ".join(partes) if partes else "sem_filtro"


def gerar_condicoes():
    specs = [
        ("rsi_14", "<=", [30, 35, 40, 45, 50]),
        ("rsi_14", ">=", [50, 55, 60, 65, 70]),
        ("range_ratio_10", ">=", [0.5, 0.7, 0.9, 1.1, 1.3]),
        ("range_ratio_10", "<=", [0.7, 0.9, 1.1, 1.3, 1.5]),
        ("vol_ratio_10", ">=", [0.5, 0.7, 0.9, 1.1, 1.3]),
        ("body_range_pct", "<=", [0.20, 0.30, 0.40, 0.50, 0.60]),
        ("body_range_pct", ">=", [0.20, 0.30, 0.40, 0.50, 0.60]),
        ("dist_ema20_abs", ">=", [5, 10, 20, 30, 40, 50, 70]),
        ("dist_open_abs", ">=", [10, 20, 40, 60, 80, 100]),
        ("extremo_reversao", ">=", [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]),
        ("pos_range_20", "<=", [0.20, 0.25, 0.30, 0.35, 0.40]),
        ("pos_range_20", ">=", [0.60, 0.65, 0.70, 0.75, 0.80]),
        ("contra_tendencia", "==", [True]),
        ("mesmo_sentido_candle", "==", [True]),
        ("mesmo_sentido_candle", "==", [False]),
    ]

    atomos = []
    for col, op, valores in specs:
        for valor in valores:
            atomos.append((col, op, valor))

    conds = [[]]
    conds += [[a] for a in atomos]

    for tam in [2, 3]:
        for combo in itertools.combinations(atomos, tam):
            cols = [c[0] for c in combo]
            # Evita filtros contraditorios na mesma coluna, exceto booleanos simples.
            if len(set(cols)) != len(cols):
                continue
            conds.append(list(combo))

    return conds


def avaliar_periodo_todo(base, conds):
    linhas = []
    trades_top = []

    for setup, df_setup in base.groupby("setup"):
        for cond in conds:
            filtrado, filtro_txt = aplicar_condicoes(df_setup, cond)
            if len(filtrado) < 20:
                continue
            row = resumir(filtrado, f"{setup}_{filtro_txt}", setup, filtro_txt)
            if row is None or row["pontos"] <= 0:
                continue
            linhas.append(row)

    ranking = pd.DataFrame(linhas)
    if ranking.empty:
        return ranking, pd.DataFrame()

    ranking = ranking.sort_values(
        ["score_multiobjetivo", "winrate", "pontos"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    ranking["ranking"] = np.arange(1, len(ranking) + 1)

    for _, row in ranking.head(30).iterrows():
        df_setup = base[base["setup"] == row["setup"]].copy()
        filtrado = df_setup if row["filtro"] == "sem_filtro" else aplicar_condicoes_texto(df_setup, row["filtro"])
        filtrado = filtrado.copy()
        filtrado["nome_otimizacao"] = row["nome"]
        filtrado["filtro_otimizacao"] = row["filtro"]
        filtrado["ranking_otimizacao"] = int(row["ranking"])
        trades_top.append(filtrado)

    trades = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()
    return ranking, trades


def aplicar_condicoes_texto(df, texto):
    if texto == "sem_filtro":
        return df.copy()
    conds = []
    for parte in texto.split(" & "):
        for op in ["==", "!=", ">=", "<=", ">", "<"]:
            if op in parte:
                col, valor = parte.split(op)
                valor = valor.strip()
                if valor == "True":
                    valor = True
                elif valor == "False":
                    valor = False
                else:
                    valor = float(valor)
                conds.append((col.strip(), op, valor))
                break
    return aplicar_condicoes(df, conds)[0]


def tabelas_auxiliares(trades_top):
    if trades_top.empty:
        return pd.DataFrame(), pd.DataFrame()

    mensal = (
        trades_top.groupby(["ranking_otimizacao", "nome_otimizacao", "mes"])
        .agg(
            trades=("pontos", "size"),
            pontos=("pontos", "sum"),
            takes=("resultado", lambda s: int((s == "TAKE").sum())),
            stops=("resultado", lambda s: int((s == "STOP").sum())),
        )
        .reset_index()
    )
    mensal["winrate"] = mensal["takes"] / mensal["trades"] * 100.0

    anual = (
        trades_top.groupby(["ranking_otimizacao", "nome_otimizacao", "ano"])
        .agg(
            trades=("pontos", "size"),
            pontos=("pontos", "sum"),
            takes=("resultado", lambda s: int((s == "TAKE").sum())),
            stops=("resultado", lambda s: int((s == "STOP").sum())),
        )
        .reset_index()
    )
    anual["winrate"] = anual["takes"] / anual["trades"] * 100.0
    return mensal, anual


def main():
    print("=====================================================")
    print("OTIMIZACAO MULTIOBJETIVO - 04:06 REVERSAO")
    print("Nao altera o robo oficial.")
    print("=====================================================")

    base = carregar_0406_reversao()
    print("Base 04:06 reversao:", len(base))
    print("Setups:", ", ".join(sorted(base["setup"].unique())))

    conds = gerar_condicoes()
    print("Combinacoes de filtros:", len(conds))

    ranking, trades_top = avaliar_periodo_todo(base, conds)
    mensal, anual = tabelas_auxiliares(trades_top)

    ranking.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES, index=False)

    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        anual.to_excel(writer, sheet_name="anual_top", index=False)
        mensal.to_excel(writer, sheet_name="mensal_top", index=False)
        trades_top.to_excel(writer, sheet_name="trades_top", index=False)

    print("\nTOP 20 MULTIOBJETIVO")
    cols = [
        "ranking", "setup", "filtro", "trades", "winrate", "pontos", "max_drawdown",
        "profit_factor", "meses_negativos", "anos_positivos", "score_multiobjetivo",
    ]
    print(ranking[cols].head(20).to_string(index=False))

    print("\nTOP COM >= 100 TRADES E WINRATE >= 85.34")
    forte = ranking[(ranking["trades"] >= 100) & (ranking["winrate"] >= ALVO_WINRATE)].copy()
    if forte.empty:
        print("Nenhum cenario com >=100 trades e winrate >=85.34.")
    else:
        print(forte[cols].head(20).to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
