from itertools import combinations
from pathlib import Path

import pandas as pd

from buscar_calendario_dow_horario_230_250 import (
    ARQ_MD as ARQ_MD_BASE,
    add_metricas,
    filtrar_operacao_aberta,
    simular_arrays,
)
from buscar_regime_dia_230_250 import preparar_candles


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "refino_calendario_dow_230_85_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "refino_calendario_dow_230_85_trades_top.csv"
ARQ_MD = SAIDA_DIR / "REFINO_CALENDARIO_DOW_230_85.md"

TOKENS_BASE = [
    "Monday|04:02|BUY",
    "Tuesday|03:12|SELL",
    "Wednesday|02:56|BUY",
    "Thursday|04:30|SELL",
    "Friday|09:30|BUY",
]

FEATURES = [
    "adx14",
    "dmi_gap",
    "ema_gap",
    "range_30",
    "range_60",
    "ret_30",
    "ret_60",
    "dist_vwap",
    "dist_ema200",
    "ema34_slope10",
    "ema200_slope10",
    "vwap_slope10",
    "rsi14",
]


def preparar_features(candles):
    df = candles.copy()
    df["dist_vwap"] = df["close"] - df["vwap"]
    return df


def montar_base(candles):
    trades_por_token = precomputar_tokens_base(candles)
    frames = [trades_por_token[token] for token in TOKENS_BASE]
    base = pd.concat(frames, ignore_index=True)
    features = preparar_features(candles)
    extras = features[FEATURES].copy()
    extras["idx"] = features.index.astype(int)
    base = base.merge(extras, on="idx", how="left")
    return base


def precomputar_tokens_base(candles):
    shared = {
        "_open_arr": candles["open"].to_numpy(),
        "_high_arr": candles["high"].to_numpy(),
        "_low_arr": candles["low"].to_numpy(),
        "_data_arr": candles["DataHora_SP"].to_numpy(),
    }
    colunas = [
        "idx",
        "token",
        "dow",
        "hhmm",
        "direcao",
        "datahora_sinal",
        "datahora_entrada",
        "datahora_saida",
        "pontos",
        "resultado",
    ]
    saida = {}
    for token in TOKENS_BASE:
        dow, hhmm, direcao = token.split("|")
        sinais = candles[
            candles["DataHora_SP"].dt.day_name().eq(dow)
            & candles["DataHora_SP"].dt.strftime("%H:%M").eq(hhmm)
        ]
        linhas = []
        for row in sinais[["DataHora_SP"]].itertuples():
            idx = int(row.Index)
            sim = simular_arrays(shared, idx, direcao)
            if sim is None:
                continue
            data_entrada, data_saida, pontos, resultado = sim
            linhas.append(
                {
                    "idx": idx,
                    "token": token,
                    "dow": dow,
                    "hhmm": hhmm,
                    "direcao": direcao,
                    "datahora_sinal": row.DataHora_SP,
                    "datahora_entrada": pd.Timestamp(data_entrada),
                    "datahora_saida": pd.Timestamp(data_saida),
                    "pontos": float(pontos),
                    "resultado": resultado,
                }
            )
        saida[token] = pd.DataFrame(linhas, columns=colunas)
    return saida


def aplicar_filtros(base, filtros):
    filtrado = base.copy()
    for filtro in filtros:
        token, coluna, op, valor = filtro
        mask_token = filtrado["token"].eq(token)
        if op == "GE":
            remove = mask_token & (filtrado[coluna] < valor)
        else:
            remove = mask_token & (filtrado[coluna] > valor)
        filtrado = filtrado[~remove]
    return filtrar_operacao_aberta(filtrado)


def avaliar(nome, base, filtros):
    trades = aplicar_filtros(base, filtros)
    row = {"cenario": nome, "filtros": descreve_filtros(filtros)}
    add_metricas(row, trades)
    row["score"] = score_refino(row)
    return row, trades


def score_refino(row):
    dist = 0 if 230 <= row["trades_365"] <= 250 else min(abs(row["trades_365"] - 230), abs(row["trades_365"] - 250))
    penal_win = max(0.0, 85.0 - row["winrate_365"]) * 1400
    penal_ano = (
        max(0.0, -row["pontos_2024"]) * 6
        + max(0.0, -row["pontos_2025"]) * 6
        + max(0.0, -row["pontos_2026"]) * 6
    )
    return (
        row["pontos_365"]
        + row["pontos_all"] * 0.2
        + min(row["pf_365"], 5.0) * 260
        + row["winrate_365"] * 70
        - abs(row["dd_365"]) * 0.7
        - dist * 180
        - penal_win
        - penal_ano
    )


def descreve_filtros(filtros):
    if not filtros:
        return "SEM_FILTRO"
    return " ; ".join(f"{token} {coluna} {op} {valor:.4f}" for token, coluna, op, valor in filtros)


def gerar_filtros(base):
    filtros = []
    for token in TOKENS_BASE:
        parte = base[base["token"].eq(token)]
        for coluna in FEATURES:
            vals = parte[coluna].dropna()
            if vals.nunique() < 8:
                continue
            for q in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
                valor = float(vals.quantile(q))
                filtros.append((token, coluna, "GE", valor))
                filtros.append((token, coluna, "LE", valor))
    return filtros


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
        "filtros",
    ]
    alvo = ranking[
        ranking["trades_365"].between(230, 250)
        & (ranking["winrate_365"] >= 85)
        & (ranking["pontos_365"] > 0)
    ].sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    linhas = [
        "# Refino Calendario DOW 230-85",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Base refinada:",
        "",
        "- Monday 04:02 BUY",
        "- Tuesday 03:12 SELL",
        "- Wednesday 02:56 BUY",
        "- Thursday 04:30 SELL",
        "- Friday 09:30 BUY",
        "",
        "## Cenarios na meta 230-250 trades e 85%+",
        "",
    ]
    linhas.extend(tabela_md(alvo, cols, 20))
    linhas.extend(["", "## Top geral do refino", ""])
    linhas.extend(tabela_md(ranking, cols, 25))
    linhas.extend(
        [
            "",
            "## Leitura",
            "",
            f"- Relatorio-base anterior: `{ARQ_MD_BASE.name}`.",
            "- Os filtros sao simples e por token, para facilitar conversao para Pine.",
            "- O candidato ainda precisa ser confirmado no TradingView antes de qualquer decisao operacional.",
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
    melhores_trades = pd.DataFrame()
    melhor_score = -10**18
    row, trades = avaliar("base_sem_filtro", base, tuple())
    linhas.append(row)
    melhores_trades = trades.assign(cenario=row["cenario"])
    melhor_score = row["score"]

    avaliacoes = []
    for filtro in filtros:
        row, trades = avaliar("filtro_1", base, (filtro,))
        linhas.append(row)
        avaliacoes.append((row["score"], filtro))
        if row["score"] > melhor_score:
            melhor_score = row["score"]
            melhores_trades = trades.assign(cenario=row["cenario"])

    top_filtros = [f for _, f in sorted(avaliacoes, reverse=True)[:80]]
    for f1, f2 in combinations(top_filtros, 2):
        if f1[0] == f2[0] and f1[1] == f2[1] and f1[2] != f2[2]:
            continue
        row, trades = avaliar("filtro_2", base, (f1, f2))
        linhas.append(row)
        if row["score"] > melhor_score:
            melhor_score = row["score"]
            melhores_trades = trades.assign(cenario=row["cenario"])

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    ranking.to_csv(ARQ_RANKING, index=False)
    melhores_trades.to_csv(ARQ_TRADES, index=False)
    escrever_markdown(ranking)

    cols = [
        "cenario",
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
        "filtros",
    ]
    print(ranking[cols].head(30).to_string(index=False, max_colwidth=180), flush=True)
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_TRADES)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
