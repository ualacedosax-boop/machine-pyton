from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "rotacao_2m1m_noite_manha_ranking.csv"
ARQ_COMBOS = SAIDA_DIR / "rotacao_2m1m_noite_manha_combos.csv"
ARQ_FOLDS = SAIDA_DIR / "rotacao_2m1m_noite_manha_folds.csv"
ARQ_TRADES_TOP = SAIDA_DIR / "rotacao_2m1m_noite_manha_trades_top.csv"
ARQ_MD = SAIDA_DIR / "ROTACAO_2M1M_NOITE_MANHA.md"

TAKE = 50.5
STOP = 117.0

FAMILIAS = {
    "noite": ["20:54", "20:56", "20:58", "21:00"],
    "manha": [
        "10:28",
        "10:30",
        "10:32",
        "11:52",
        "11:54",
        "11:56",
    ],
}

FEATURES = [
    "rsi14",
    "macd_hist",
    "roc5",
    "roc10",
    "prev_roc5",
    "body",
    "ema_trend",
    "dist_vwap",
    "dist_ema200",
    "range_30",
    "ret_60",
    "pos_range20",
    "adx14",
    "dmi_gap",
]
QUANTIS = [0.2, 0.35, 0.5, 0.65, 0.8]

MIN_TREINO = 8
MIN_TESTE = 3
TOP_ATOMOS = 16
TOP_POR_FAMILIA = 18
TOP_COMBO_POR_FAMILIA = 8
MAX_BARRAS_SAIDA = 720


def preparar():
    df = indicadores(carregar_candles()).reset_index(drop=True)
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["ema_trend"] = df["ema17"] - df["ema34"]
    df["dist_vwap"] = df["close"] - df["vwap"]
    df["dist_ema200"] = df["close"] - df["ema200"]
    df["range_30"] = df["high"].rolling(15).max() - df["low"].rolling(15).min()
    df["ret_60"] = df["close"] - df["close"].shift(30)
    max20 = df["high"].rolling(20).max()
    min20 = df["low"].rolling(20).min()
    df["pos_range20"] = (df["close"] - min20) / (max20 - min20).replace(0, np.nan)
    return df.replace([np.inf, -np.inf], np.nan)


def folds_2m1m(meses):
    meses_set = set(meses)
    folds = []
    anos = sorted({int(m[:4]) for m in meses})
    for ano in anos:
        for inicio in [1, 4, 7, 10]:
            treino = [f"{ano}-{inicio:02d}", f"{ano}-{inicio + 1:02d}"]
            teste = f"{ano}-{inicio + 2:02d}"
            if all(m in meses_set for m in treino) and teste in meses_set:
                folds.append(
                    {
                        "fold": f"treina_{treino[0]}_{treino[1]}_testa_{teste}",
                        "treino": treino,
                        "teste": teste,
                    }
                )
    return folds


def filtrar_aberta(trades):
    if trades.empty:
        return trades
    linhas = []
    liberado = pd.Timestamp.min
    for row in trades.sort_values(["datahora_sinal", "token"]).itertuples(index=False):
        if row.datahora_sinal < liberado:
            continue
        liberado = row.datahora_saida
        linhas.append(row._asdict())
    return pd.DataFrame(linhas)


def resumo(trades):
    if trades.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    pontos = trades["pontos"].astype(float)
    return {
        "trades": int(len(trades)),
        "winrate": float((pontos > 0).mean() * 100.0),
        "pontos": float(pontos.sum()),
        "dd": max_drawdown(pontos),
        "pf": profit_factor(pontos),
    }


def resumo_recorte(trades, dias):
    if trades.empty:
        return resumo(trades)
    fim = trades["datahora_entrada"].max()
    return resumo(trades[trades["datahora_entrada"] >= fim - pd.Timedelta(days=dias)])


def simular_arrays(shared, idx_sinal, direcao):
    idx_entrada = idx_sinal + 1
    if idx_entrada >= len(shared["open"]):
        return None
    entrada = float(shared["open"][idx_entrada])
    if direcao == "BUY":
        preco_take = entrada + TAKE
        preco_stop = entrada - STOP
    else:
        preco_take = entrada - TAKE
        preco_stop = entrada + STOP

    fim = min(len(shared["open"]), idx_entrada + MAX_BARRAS_SAIDA)
    highs = shared["high"][idx_entrada:fim]
    lows = shared["low"][idx_entrada:fim]
    if direcao == "BUY":
        stop_hits = np.flatnonzero(lows <= preco_stop)
        take_hits = np.flatnonzero(highs >= preco_take)
    else:
        stop_hits = np.flatnonzero(highs >= preco_stop)
        take_hits = np.flatnonzero(lows <= preco_take)

    primeiro_stop = int(stop_hits[0]) if len(stop_hits) else 10**9
    primeiro_take = int(take_hits[0]) if len(take_hits) else 10**9
    if primeiro_stop == primeiro_take == 10**9:
        return None
    if primeiro_stop <= primeiro_take:
        j = idx_entrada + primeiro_stop
        return pd.Timestamp(shared["data"][idx_entrada]), pd.Timestamp(shared["data"][j]), -STOP, "STOP"
    j = idx_entrada + primeiro_take
    return pd.Timestamp(shared["data"][idx_entrada]), pd.Timestamp(shared["data"][j]), TAKE, "TAKE"


def simular_token(df, shared, familia, hhmm, direcao):
    linhas = []
    rows = df[(df["hhmm"] == hhmm) & (df["dow"] != "Saturday")]
    for idx in rows.index:
        sim = simular_arrays(shared, int(idx), direcao)
        if sim is None:
            continue
        entrada, saida, pontos, resultado = sim
        row = {
            "idx": int(idx),
            "familia": familia,
            "token": f"{familia}|{hhmm}|{direcao}",
            "hhmm": hhmm,
            "direcao": direcao,
            "datahora_sinal": df.at[int(idx), "DataHora_SP"],
            "datahora_entrada": entrada,
            "datahora_saida": saida,
            "mes": df.at[int(idx), "mes"],
            "pontos": float(pontos),
            "resultado": resultado,
        }
        for col in FEATURES:
            row[col] = df.at[int(idx), col]
        linhas.append(row)
    return pd.DataFrame(linhas)


def aplicar_cond(trades, cond):
    if trades.empty or not cond:
        return trades.copy()
    mask = pd.Series(True, index=trades.index)
    for col, op, val in cond:
        serie = pd.to_numeric(trades[col], errors="coerce")
        if op == ">=":
            mask &= serie >= float(val)
        else:
            mask &= serie <= float(val)
    return trades[mask].copy()


def cond_txt(cond):
    if not cond:
        return "sem_filtro"
    return " & ".join(f"{col} {op} {val:.4f}" for col, op, val in cond)


def atomos_token(trades):
    atomos = []
    for col in FEATURES:
        vals = pd.to_numeric(trades[col], errors="coerce").dropna()
        if len(vals) < 40:
            continue
        for val in vals.quantile(QUANTIS).dropna().unique():
            val = float(val)
            atomos.append(((col, ">=", val),))
            atomos.append(((col, "<=", val),))
    return atomos


def score_linha(row):
    return (
        row["folds_teste_ok"] * 1800
        + row["folds_treino_ok"] * 400
        + row["teste_pontos"] * 3.0
        + row["teste_winrate"] * 45.0
        + min(row["teste_pf"], 10.0) * 220.0
        + row["pontos_365"] * 0.8
        + row["pontos_90"] * 1.6
        + row["pontos_30"] * 1.2
        + row["winrate_365"] * 18.0
        - abs(row["teste_dd"]) * 1.1
        - row["folds_teste_neg"] * 750
        - max(0, 4 - row["folds_teste_ok"]) * 900
    )


def avaliar_candidato(token_trades, cond, folds, meta):
    trades = filtrar_aberta(aplicar_cond(token_trades, cond))
    fold_rows = []
    testes_ok = []
    testes_todos = []
    folds_treino_ok = 0
    folds_teste_ok = 0
    folds_teste_neg = 0
    for fold in folds:
        treino = trades[trades["mes"].isin(fold["treino"])]
        teste = trades[trades["mes"].eq(fold["teste"])]
        mt = resumo(treino)
        ms = resumo(teste)
        treino_ok = mt["trades"] >= MIN_TREINO and mt["pontos"] > 0 and mt["winrate"] >= 70
        teste_ok = treino_ok and ms["trades"] >= MIN_TESTE and ms["pontos"] > 0 and ms["winrate"] >= 60
        folds_treino_ok += int(treino_ok)
        folds_teste_ok += int(teste_ok)
        folds_teste_neg += int(treino_ok and ms["pontos"] < 0)
        if treino_ok:
            testes_todos.append(teste)
        if teste_ok:
            testes_ok.append(teste)
        fold_rows.append(
            {
                **meta,
                "filtro": cond_txt(cond),
                "fold": fold["fold"],
                "treino_meses": ",".join(fold["treino"]),
                "teste_mes": fold["teste"],
                "treino_ok": treino_ok,
                "teste_ok": teste_ok,
                **{f"treino_{k}": v for k, v in mt.items()},
                **{f"teste_{k}": v for k, v in ms.items()},
            }
        )

    teste_pool = filtrar_aberta(pd.concat(testes_todos, ignore_index=True)) if testes_todos else pd.DataFrame()
    mtodos = resumo(teste_pool)
    m365 = resumo_recorte(trades, 365)
    m90 = resumo_recorte(trades, 90)
    m30 = resumo_recorte(trades, 30)
    row = {
        **meta,
        "filtro": cond_txt(cond),
        "cond": cond,
        "folds_total": len(folds),
        "folds_treino_ok": folds_treino_ok,
        "folds_teste_ok": folds_teste_ok,
        "folds_teste_neg": folds_teste_neg,
        **{f"teste_{k}": v for k, v in mtodos.items()},
        **{f"{k}_365": v for k, v in m365.items()},
        **{f"{k}_90": v for k, v in m90.items()},
        **{f"{k}_30": v for k, v in m30.items()},
    }
    row["score"] = score_linha(row)
    return row, pd.DataFrame(fold_rows), trades


def buscar_token(token_trades, folds, meta):
    linhas = []
    folds_linhas = []
    melhores_trades = []

    conds_base = [tuple()] + atomos_token(token_trades)
    avaliados = []
    for cond in conds_base:
        row, fold_df, trades = avaliar_candidato(token_trades, cond, folds, meta)
        avaliados.append((row, fold_df, trades))
        linhas.append(row)
        folds_linhas.append(fold_df)

    atomos_rank = [
        item for item in avaliados
        if item[0]["filtro"] != "sem_filtro" and item[0]["teste_trades"] >= 8
    ]
    atomos_rank.sort(key=lambda x: x[0]["score"], reverse=True)
    atomos_top = [tuple(item[0]["cond"]) for item in atomos_rank[:TOP_ATOMOS]]

    pares = []
    for a, b in combinations(atomos_top, 2):
        if a[0][0] == b[0][0]:
            continue
        par = tuple(sorted([a[0], b[0]], key=lambda x: x[0] + x[1]))
        if par not in pares:
            pares.append(par)

    for cond in pares[:120]:
        row, fold_df, trades = avaliar_candidato(token_trades, cond, folds, meta)
        linhas.append(row)
        folds_linhas.append(fold_df)

    ranking = pd.DataFrame(linhas).sort_values(["score", "folds_teste_ok", "teste_pontos"], ascending=False)
    if not ranking.empty:
        for _, row in ranking.head(3).iterrows():
            trades = filtrar_aberta(aplicar_cond(token_trades, row["cond"]))
            melhores_trades.append(trades.assign(candidato=row["candidato"], filtro=row["filtro"]))
    folds_df = pd.concat(folds_linhas, ignore_index=True) if folds_linhas else pd.DataFrame()
    trades_df = pd.concat(melhores_trades, ignore_index=True) if melhores_trades else pd.DataFrame()
    return ranking, folds_df, trades_df


def buscar():
    df = preparar()
    shared = {
        "open": df["open"].to_numpy(dtype=float),
        "high": df["high"].to_numpy(dtype=float),
        "low": df["low"].to_numpy(dtype=float),
        "data": df["DataHora_SP"].to_numpy(),
    }
    folds = folds_2m1m(sorted(df["mes"].dropna().unique()))
    print("Folds 2m/1m:", len(folds), flush=True)
    for fold in folds:
        print(fold["fold"], flush=True)

    rankings = []
    folds_out = []
    trades_top = []

    for familia, horarios in FAMILIAS.items():
        for hhmm in horarios:
            for direcao in ["BUY", "SELL"]:
                token_trades = simular_token(df, shared, familia, hhmm, direcao)
                if len(token_trades) < 60:
                    continue
                meta = {
                    "familia": familia,
                    "hhmm": hhmm,
                    "direcao": direcao,
                    "candidato": f"{familia}|{hhmm}|{direcao}",
                }
                ranking, fold_df, trades_df = buscar_token(token_trades, folds, meta)
                rankings.append(ranking)
                folds_out.append(fold_df)
                if not trades_df.empty:
                    trades_top.append(trades_df)
                top = ranking.iloc[0]
                print(
                    f"{familia} {hhmm} {direcao}: score={top['score']:.1f} "
                    f"folds_ok={top['folds_teste_ok']}/{top['folds_total']} "
                    f"teste={top['teste_trades']}tr {top['teste_winrate']:.1f}% {top['teste_pontos']:.1f} "
                    f"filtro={top['filtro']}",
                    flush=True,
                )

    ranking = pd.concat(rankings, ignore_index=True).sort_values(
        ["score", "folds_teste_ok", "teste_pontos"],
        ascending=False,
    )
    folds_df = pd.concat(folds_out, ignore_index=True)
    trades_df = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()
    return ranking, folds_df, trades_df, folds


def avaliar_combo(row_a, row_b, trades_por_chave, folds):
    chave_a = (row_a["candidato"], row_a["filtro"])
    chave_b = (row_b["candidato"], row_b["filtro"])
    trades = pd.concat([trades_por_chave[chave_a], trades_por_chave[chave_b]], ignore_index=True)
    trades = filtrar_aberta(trades)
    meta = {
        "combo": f"{row_a['candidato']} [{row_a['filtro']}] + {row_b['candidato']} [{row_b['filtro']}]",
        "noite": row_a["candidato"] if row_a["familia"] == "noite" else row_b["candidato"],
        "manha": row_a["candidato"] if row_a["familia"] == "manha" else row_b["candidato"],
    }
    fold_rows = []
    folds_teste_ok = 0
    folds_teste_neg = 0
    testes = []
    for fold in folds:
        treino = trades[trades["mes"].isin(fold["treino"])]
        teste = trades[trades["mes"].eq(fold["teste"])]
        mt = resumo(treino)
        ms = resumo(teste)
        treino_ok = mt["trades"] >= MIN_TREINO and mt["pontos"] > 0 and mt["winrate"] >= 70
        teste_ok = treino_ok and ms["trades"] >= MIN_TESTE and ms["pontos"] > 0 and ms["winrate"] >= 60
        folds_teste_ok += int(teste_ok)
        folds_teste_neg += int(treino_ok and ms["pontos"] < 0)
        if treino_ok:
            testes.append(teste)
        fold_rows.append({"fold": fold["fold"], **meta, **{f"teste_{k}": v for k, v in ms.items()}, "teste_ok": teste_ok})
    teste_pool = filtrar_aberta(pd.concat(testes, ignore_index=True)) if testes else pd.DataFrame()
    row = {
        **meta,
        "folds_total": len(folds),
        "folds_teste_ok": folds_teste_ok,
        "folds_teste_neg": folds_teste_neg,
        **{f"teste_{k}": v for k, v in resumo(teste_pool).items()},
        **{f"{k}_365": v for k, v in resumo_recorte(trades, 365).items()},
        **{f"{k}_90": v for k, v in resumo_recorte(trades, 90).items()},
        **{f"{k}_30": v for k, v in resumo_recorte(trades, 30).items()},
    }
    row["score"] = score_linha({**row, "folds_treino_ok": folds_teste_ok})
    return row, pd.DataFrame(fold_rows), trades


def montar_combos(ranking, trades_top, folds):
    if ranking.empty or trades_top.empty:
        return pd.DataFrame(), pd.DataFrame()

    trades_por_chave = {}
    for (cand, filtro), grupo in trades_top.groupby(["candidato", "filtro"]):
        trades_por_chave[(cand, filtro)] = grupo.drop(columns=["candidato", "filtro"], errors="ignore")

    noite = ranking[ranking["familia"].eq("noite")].drop_duplicates(["candidato", "filtro"]).head(TOP_COMBO_POR_FAMILIA)
    manha = ranking[ranking["familia"].eq("manha")].drop_duplicates(["candidato", "filtro"]).head(TOP_COMBO_POR_FAMILIA)
    linhas = []
    fold_linhas = []
    for _, n in noite.iterrows():
        for _, m in manha.iterrows():
            if (n["candidato"], n["filtro"]) not in trades_por_chave:
                continue
            if (m["candidato"], m["filtro"]) not in trades_por_chave:
                continue
            row, fdf, _ = avaliar_combo(n, m, trades_por_chave, folds)
            linhas.append(row)
            fold_linhas.append(fdf)
    combos = pd.DataFrame(linhas).sort_values(["score", "folds_teste_ok", "teste_pontos"], ascending=False)
    combo_folds = pd.concat(fold_linhas, ignore_index=True) if fold_linhas else pd.DataFrame()
    return combos, combo_folds


def tabela_md(df, cols, n=12):
    if df.empty:
        return ["Nenhum resultado."]
    linhas = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in df[cols].head(n).itertuples(index=False):
        vals = []
        for val in row:
            if isinstance(val, float):
                vals.append(f"{val:.2f}")
            else:
                vals.append(str(val))
        linhas.append("| " + " | ".join(vals) + " |")
    return linhas


def escrever_md(ranking, combos, folds):
    cols = [
        "candidato",
        "filtro",
        "folds_teste_ok",
        "teste_trades",
        "teste_winrate",
        "teste_pontos",
        "teste_dd",
        "teste_pf",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "trades_90",
        "winrate_90",
        "pontos_90",
        "trades_30",
        "winrate_30",
        "pontos_30",
    ]
    combo_cols = [
        "combo",
        "folds_teste_ok",
        "teste_trades",
        "teste_winrate",
        "teste_pontos",
        "teste_dd",
        "teste_pf",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "trades_90",
        "winrate_90",
        "pontos_90",
        "trades_30",
        "winrate_30",
        "pontos_30",
    ]
    linhas = [
        "# Rotacao 2M/1M Noite e Manha",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Metodo: blocos trimestrais. Treina os dois primeiros meses e testa o terceiro.",
        "",
        "Folds usados:",
        "",
    ]
    linhas.extend([f"- {f['fold']}" for f in folds])
    linhas.extend(["", "## Top noite", ""])
    linhas.extend(tabela_md(ranking[ranking["familia"].eq("noite")], cols))
    linhas.extend(["", "## Top manha", ""])
    linhas.extend(tabela_md(ranking[ranking["familia"].eq("manha")], cols))
    linhas.extend(["", "## Top combinacoes noite + manha", ""])
    linhas.extend(tabela_md(combos, combo_cols, 12))
    linhas.extend(
        [
            "",
            "## Leitura",
            "",
            "- Uma regra so e candidata se passar em meses de teste, nao apenas no periodo total.",
            "- Se a combinacao for pior que os blocos separados, manter scripts separados e juntar apenas depois de validacao no TV.",
            "- Proximo passo apos escolher candidatos: converter para Pine simples e validar no TradingView com Backtesting Profundo.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    ranking, folds_df, trades_top, folds = buscar()
    combos, combo_folds = montar_combos(ranking, trades_top, folds)
    ranking.drop(columns=["cond"], errors="ignore").to_csv(ARQ_RANKING, index=False)
    combos.to_csv(ARQ_COMBOS, index=False)
    pd.concat([folds_df, combo_folds], ignore_index=True).to_csv(ARQ_FOLDS, index=False)
    trades_top.to_csv(ARQ_TRADES_TOP, index=False)
    escrever_md(ranking, combos, folds)

    print("\nTop noite:")
    print(ranking[ranking["familia"].eq("noite")].head(10)[["candidato", "filtro", "folds_teste_ok", "teste_trades", "teste_winrate", "teste_pontos", "trades_365", "winrate_365", "pontos_365", "trades_30", "winrate_30", "pontos_30"]].to_string(index=False, max_colwidth=100))
    print("\nTop manha:")
    print(ranking[ranking["familia"].eq("manha")].head(10)[["candidato", "filtro", "folds_teste_ok", "teste_trades", "teste_winrate", "teste_pontos", "trades_365", "winrate_365", "pontos_365", "trades_30", "winrate_30", "pontos_30"]].to_string(index=False, max_colwidth=100))
    print("\nTop combos:")
    if not combos.empty:
        print(combos.head(10)[["combo", "folds_teste_ok", "teste_trades", "teste_winrate", "teste_pontos", "trades_365", "winrate_365", "pontos_365", "trades_30", "winrate_30", "pontos_30"]].to_string(index=False, max_colwidth=120))
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_COMBOS)
    print(ARQ_FOLDS)
    print(ARQ_TRADES_TOP)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
