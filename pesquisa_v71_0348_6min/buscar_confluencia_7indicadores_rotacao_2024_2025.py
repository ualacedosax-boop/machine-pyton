from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_RANKING = SAIDA_DIR / "confluencia_7indicadores_rotacao_2024_2025_ranking.csv"
ARQ_COMBOS = SAIDA_DIR / "confluencia_7indicadores_rotacao_2024_2025_combos.csv"
ARQ_FOLDS = SAIDA_DIR / "confluencia_7indicadores_rotacao_2024_2025_folds.csv"
ARQ_TRADES = SAIDA_DIR / "confluencia_7indicadores_rotacao_2024_2025_trades_top.csv"
ARQ_MD = SAIDA_DIR / "CONFLUENCIA_7INDICADORES_ROTACAO_2024_2025.md"

TAKE = 50.5
STOP = 117.0
MAX_BARRAS_SAIDA = 720
ANOS_MODELO = (2024, 2025)
ANO_HOLDOUT = 2026

HORARIOS = {
    "noite": ["20:52", "20:54", "20:56", "20:58", "21:00", "21:02"],
    "manha": ["10:28", "10:30", "10:32", "10:34", "11:52", "11:54", "11:56"],
}

VOTOS = [
    "ema8_21",
    "ema17_34",
    "ema34_89",
    "preco_ema200",
    "dmi",
    "macd",
    "rsi50",
    "roc5",
    "roc10",
    "vwap",
    "bb_mid",
    "candle",
    "prev_candle",
    "stoch50",
]

REGIME_FILTROS = {
    "sem_filtro": lambda df: np.ones(len(df), dtype=bool),
    "adx20": lambda df: pd.to_numeric(df["adx14"], errors="coerce").to_numpy() >= 20.0,
    "dmi4": lambda df: pd.to_numeric(df["dmi_gap"], errors="coerce").to_numpy() >= 4.0,
    "adx20_dmi4": lambda df: (
        (pd.to_numeric(df["adx14"], errors="coerce").to_numpy() >= 20.0)
        & (pd.to_numeric(df["dmi_gap"], errors="coerce").to_numpy() >= 4.0)
    ),
    "adx25_dmi6": lambda df: (
        (pd.to_numeric(df["adx14"], errors="coerce").to_numpy() >= 25.0)
        & (pd.to_numeric(df["dmi_gap"], errors="coerce").to_numpy() >= 6.0)
    ),
}

DOW_GRUPOS = {
    "ALL": None,
    "WEEK": {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"},
    "SUN": {"Sunday"},
    "MON": {"Monday"},
    "TUE": {"Tuesday"},
    "WED": {"Wednesday"},
    "THU": {"Thursday"},
    "FRI": {"Friday"},
    "MON_TUE": {"Monday", "Tuesday"},
    "SUN_WED": {"Sunday", "Wednesday"},
    "TUE_THU": {"Tuesday", "Thursday"},
    "WED_FRI": {"Wednesday", "Friday"},
}

MIN_MODELO_PRE = 45
MIN_TESTE_TOTAL_PRE = 10
MIN_MODELO_FINAL = 25
MIN_TREINO_FOLD = 3
MIN_TESTE_FOLD = 1
TOP_PRELIM_POR_TOKEN = 25
TOP_FINAL_POR_FAMILIA = 10
TOP_RANKING_SALVAR = 1000
TOP_COMBOS_SALVAR = 200
TOP_TRADES_SALVAR = 80


def preparar():
    df = indicadores(carregar_candles()).reset_index(drop=True)
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df["ano"] = df["DataHora_SP"].dt.year.astype(int)

    for n in [8, 13, 21, 34, 55, 89, 144]:
        df[f"ema{n}"] = df["close"].ewm(span=n, adjust=False).mean()

    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["prev_body"] = df["body"].shift(1)

    bb_mid = df["close"].rolling(20, min_periods=20).mean()
    bb_std = df["close"].rolling(20, min_periods=20).std()
    df["bb_mid"] = bb_mid
    df["bb_up"] = bb_mid + 2 * bb_std
    df["bb_dn"] = bb_mid - 2 * bb_std

    stoch_min = df["low"].rolling(14, min_periods=14).min()
    stoch_max = df["high"].rolling(14, min_periods=14).max()
    stoch_den = (stoch_max - stoch_min).replace(0, np.nan)
    df["stoch14"] = 100 * (df["close"] - stoch_min) / stoch_den
    return df.replace([np.inf, -np.inf], np.nan)


def voto_bool(cond, valido):
    return np.where(valido & cond, 1, np.where(valido, -1, 0)).astype(np.int8)


def montar_votos(df):
    votos = {}
    votos["ema8_21"] = voto_bool(df["ema8"] >= df["ema21"], df["ema8"].notna() & df["ema21"].notna())
    votos["ema17_34"] = voto_bool(df["ema17"] >= df["ema34"], df["ema17"].notna() & df["ema34"].notna())
    votos["ema34_89"] = voto_bool(df["ema34"] >= df["ema89"], df["ema34"].notna() & df["ema89"].notna())
    votos["preco_ema200"] = voto_bool(df["close"] >= df["ema200"], df["close"].notna() & df["ema200"].notna())
    votos["dmi"] = voto_bool(df["di_plus"] >= df["di_minus"], df["di_plus"].notna() & df["di_minus"].notna())
    votos["macd"] = voto_bool(df["macd"] >= df["macd_signal"], df["macd"].notna() & df["macd_signal"].notna())
    votos["rsi50"] = voto_bool(df["rsi14"] >= 50, df["rsi14"].notna())
    votos["roc5"] = voto_bool(df["roc5"] >= 0, df["roc5"].notna())
    votos["roc10"] = voto_bool(df["roc10"] >= 0, df["roc10"].notna())
    votos["vwap"] = voto_bool(df["close"] >= df["vwap"], df["close"].notna() & df["vwap"].notna())
    votos["bb_mid"] = voto_bool(df["close"] >= df["bb_mid"], df["close"].notna() & df["bb_mid"].notna())
    votos["candle"] = voto_bool(df["body"] >= 0, df["body"].notna())
    votos["prev_candle"] = voto_bool(df["prev_body"] >= 0, df["prev_body"].notna())
    votos["stoch50"] = voto_bool(df["stoch14"] >= 50, df["stoch14"].notna())
    return pd.DataFrame(votos, index=df.index)


def folds_2m1m_rolling(meses):
    periodos = sorted(pd.Period(m, freq="M") for m in meses if int(str(m)[:4]) in ANOS_MODELO)
    existentes = set(periodos)
    folds = []
    for p in periodos:
        treino = [p, p + 1]
        teste = p + 2
        if not all(x in existentes for x in treino) or teste not in existentes:
            continue
        if any(x.year not in ANOS_MODELO for x in treino) or teste.year not in ANOS_MODELO:
            continue
        folds.append(
            {
                "fold": f"treina_{treino[0]}_{treino[1]}_testa_{teste}",
                "treino": [str(x) for x in treino],
                "teste": str(teste),
            }
        )
    return folds


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


def montar_token_trades(df, votos, shared, familia, hhmm, direcao):
    rows = df[(df["hhmm"].eq(hhmm)) & (df["dow"] != "Saturday")].copy()
    linhas = []
    for idx in rows.index:
        sim = simular_arrays(shared, int(idx), direcao)
        if sim is None:
            continue
        entrada, saida, pontos, resultado = sim
        row = {
            "idx": int(idx),
            "familia": familia,
            "hhmm": hhmm,
            "direcao": direcao,
            "token": f"{familia}|{hhmm}|{direcao}",
            "datahora_sinal": df.at[int(idx), "DataHora_SP"],
            "datahora_entrada": entrada,
            "datahora_saida": saida,
            "mes": df.at[int(idx), "mes"],
            "ano": int(df.at[int(idx), "ano"]),
            "dow": df.at[int(idx), "dow"],
            "pontos": float(pontos),
            "resultado": resultado,
            "adx14": df.at[int(idx), "adx14"],
            "dmi_gap": df.at[int(idx), "dmi_gap"],
        }
        for nome in VOTOS:
            row[f"v_{nome}"] = int(votos.at[int(idx), nome])
        linhas.append(row)
    return pd.DataFrame(linhas)


def filtrar_aberta(trades):
    if trades.empty:
        return trades.copy()
    linhas = []
    liberado = pd.Timestamp.min
    ordenado = trades.sort_values(["datahora_sinal", "token", "id"], na_position="last")
    for row in ordenado.itertuples(index=False):
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


def resumo_np(pontos):
    pontos = np.asarray(pontos, dtype=float)
    if len(pontos) == 0:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    eq = np.cumsum(pontos)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    return {
        "trades": int(len(pontos)),
        "winrate": float((pontos > 0).mean() * 100.0),
        "pontos": float(pontos.sum()),
        "dd": dd,
        "pf": ganhos / perdas if perdas else 999.0,
    }


def recorte_anos(trades, anos):
    if trades.empty:
        return trades.copy()
    return trades[trades["ano"].isin(anos)].copy()


def recorte_ano(trades, ano):
    if trades.empty:
        return trades.copy()
    return trades[trades["ano"].eq(ano)].copy()


def resumo_recorte(trades, dias):
    if trades.empty:
        return resumo(trades)
    fim = trades["datahora_entrada"].max()
    return resumo(trades[trades["datahora_entrada"] >= fim - pd.Timedelta(days=dias)])


def fold_stats_arrays(pontos, meses, mask, folds):
    folds_treino_ok = 0
    folds_teste_ok = 0
    folds_teste_neg = 0
    teste_masks = []
    for fold in folds:
        treino = mask & np.isin(meses, fold["treino"])
        teste = mask & (meses == fold["teste"])
        rt = resumo_np(pontos[treino])
        rs = resumo_np(pontos[teste])
        treino_ok = rt["trades"] >= MIN_TREINO_FOLD and rt["pontos"] > 0 and rt["winrate"] >= 60.0
        teste_ok = treino_ok and rs["trades"] >= MIN_TESTE_FOLD and rs["pontos"] > 0 and rs["winrate"] >= 55.0
        folds_treino_ok += int(treino_ok)
        folds_teste_ok += int(teste_ok)
        folds_teste_neg += int(treino_ok and rs["pontos"] < 0)
        if treino_ok:
            teste_masks.append(teste)
    if teste_masks:
        teste_pool = np.logical_or.reduce(teste_masks)
    else:
        teste_pool = np.zeros(len(mask), dtype=bool)
    return folds_treino_ok, folds_teste_ok, folds_teste_neg, resumo_np(pontos[teste_pool])


def score_linha(row):
    return (
        row["folds_teste_ok"] * 2400.0
        + row["folds_treino_ok"] * 450.0
        + row["teste_pontos"] * 3.0
        + row["teste_winrate"] * 45.0
        + min(row["teste_pf"], 10.0) * 220.0
        + row["pontos_modelo"] * 0.7
        + row["winrate_modelo"] * 22.0
        + min(row["winrate_2024"], row["winrate_2025"]) * 18.0
        - abs(row["dd_modelo"]) * 0.7
        - row["folds_teste_neg"] * 1200.0
        - max(0, 9 - row["folds_teste_ok"]) * 650.0
    )


def avaliar_prelim(token_trades, mask, folds):
    pontos = token_trades["pontos"].to_numpy(dtype=float)
    anos = token_trades["ano"].to_numpy(dtype=int)
    meses = token_trades["mes"].astype(str).to_numpy()

    mask_modelo = mask & np.isin(anos, ANOS_MODELO)
    rm = resumo_np(pontos[mask_modelo])
    if rm["trades"] < MIN_MODELO_PRE or rm["pontos"] <= 0:
        return None

    folds_treino_ok, folds_teste_ok, folds_teste_neg, rt = fold_stats_arrays(pontos, meses, mask, folds)
    if rt["trades"] < MIN_TESTE_TOTAL_PRE or folds_teste_ok < 4:
        return None

    r2024 = resumo_np(pontos[mask & (anos == 2024)])
    r2025 = resumo_np(pontos[mask & (anos == 2025)])
    if r2024["pontos"] <= 0 or r2025["pontos"] <= 0:
        return None

    row = {
        "folds_treino_ok": folds_treino_ok,
        "folds_teste_ok": folds_teste_ok,
        "folds_teste_neg": folds_teste_neg,
        **{f"teste_{k}": v for k, v in rt.items()},
        **{f"{k}_modelo": v for k, v in rm.items()},
        **{f"{k}_2024": v for k, v in r2024.items()},
        **{f"{k}_2025": v for k, v in r2025.items()},
    }
    row["score"] = score_linha(row)
    return row


def mask_candidato(token_trades, combo, min_votos, regime, dow_grupo):
    lado = 1 if token_trades["direcao"].iloc[0] == "BUY" else -1
    votos = token_trades[[f"v_{nome}" for nome in combo]].to_numpy(dtype=np.int8)
    mask = ((lado * votos) > 0).sum(axis=1) >= int(min_votos)
    mask &= REGIME_FILTROS[regime](token_trades)
    dows = DOW_GRUPOS[dow_grupo]
    if dows is not None:
        mask &= token_trades["dow"].isin(dows).to_numpy()
    return mask


def avaliar_final(token_trades, cand, folds, dow_grupo):
    mask = mask_candidato(token_trades, cand["combo"], cand["min_votos"], cand["regime"], dow_grupo)
    selecionados = token_trades.loc[mask].copy()
    if selecionados.empty:
        return None, pd.DataFrame(), selecionados
    selecionados["id"] = id_candidato(cand, dow_grupo)
    trades = filtrar_aberta(selecionados)
    modelo = recorte_anos(trades, ANOS_MODELO)
    rm = resumo(modelo)
    if rm["trades"] < MIN_MODELO_FINAL or rm["pontos"] <= 0:
        return None, pd.DataFrame(), trades

    fold_rows = []
    testes = []
    folds_treino_ok = 0
    folds_teste_ok = 0
    folds_teste_neg = 0
    for fold in folds:
        treino = trades[trades["mes"].isin(fold["treino"])]
        teste = trades[trades["mes"].eq(fold["teste"])]
        rt = resumo(treino)
        rs = resumo(teste)
        treino_ok = rt["trades"] >= MIN_TREINO_FOLD and rt["pontos"] > 0 and rt["winrate"] >= 60.0
        teste_ok = treino_ok and rs["trades"] >= MIN_TESTE_FOLD and rs["pontos"] > 0 and rs["winrate"] >= 55.0
        folds_treino_ok += int(treino_ok)
        folds_teste_ok += int(teste_ok)
        folds_teste_neg += int(treino_ok and rs["pontos"] < 0)
        if treino_ok:
            testes.append(teste)
        fold_rows.append(
            {
                "tipo": "individual",
                "id": id_candidato(cand, dow_grupo),
                "fold": fold["fold"],
                **{f"treino_{k}": v for k, v in rt.items()},
                **{f"teste_{k}": v for k, v in rs.items()},
                "treino_ok": treino_ok,
                "teste_ok": teste_ok,
            }
        )

    teste_pool = filtrar_aberta(pd.concat(testes, ignore_index=True)) if testes else pd.DataFrame()
    rteste = resumo(teste_pool)
    r2024 = resumo(recorte_ano(trades, 2024))
    r2025 = resumo(recorte_ano(trades, 2025))
    if r2024["pontos"] <= 0 or r2025["pontos"] <= 0:
        return None, pd.DataFrame(fold_rows), trades

    row = {
        "id": id_candidato(cand, dow_grupo),
        "familia": cand["familia"],
        "hhmm": cand["hhmm"],
        "direcao": cand["direcao"],
        "token": cand["token"],
        "combo": "+".join(cand["combo"]),
        "indicadores": ", ".join(cand["combo"]),
        "min_votos": cand["min_votos"],
        "regime": cand["regime"],
        "dow_grupo": dow_grupo,
        "folds_total": len(folds),
        "folds_treino_ok": folds_treino_ok,
        "folds_teste_ok": folds_teste_ok,
        "folds_teste_neg": folds_teste_neg,
        **{f"teste_{k}": v for k, v in rteste.items()},
        **{f"{k}_modelo": v for k, v in rm.items()},
        **{f"{k}_2024": v for k, v in r2024.items()},
        **{f"{k}_2025": v for k, v in r2025.items()},
        **{f"{k}_2026": v for k, v in resumo(recorte_ano(trades, ANO_HOLDOUT)).items()},
        **{f"{k}_90": v for k, v in resumo_recorte(trades, 90).items()},
        **{f"{k}_30": v for k, v in resumo_recorte(trades, 30).items()},
    }
    row["score"] = score_linha(row)
    return row, pd.DataFrame(fold_rows), trades


def id_candidato(cand, dow_grupo):
    combo = "+".join(cand["combo"])
    return f"{cand['token']}|v{cand['min_votos']}|{cand['regime']}|{dow_grupo}|{combo}"


def buscar_token(token_trades, folds, combos_idx, combos_nomes):
    if token_trades.empty or len(recorte_anos(token_trades, ANOS_MODELO)) < MIN_MODELO_PRE:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    votos_mat = token_trades[[f"v_{nome}" for nome in VOTOS]].to_numpy(dtype=np.int8)
    lado = 1 if token_trades["direcao"].iloc[0] == "BUY" else -1
    alinhados = (lado * votos_mat) > 0
    filtros = {nome: fn(token_trades) for nome, fn in REGIME_FILTROS.items()}

    prelim = []
    for idxs, nomes in zip(combos_idx, combos_nomes):
        contagem = alinhados[:, idxs].sum(axis=1)
        for min_votos in [5, 6, 7]:
            base = contagem >= min_votos
            if base.sum() < MIN_MODELO_FINAL:
                continue
            for regime, filtro in filtros.items():
                mask = base & filtro
                row = avaliar_prelim(token_trades, mask, folds)
                if row is None:
                    continue
                row.update(
                    {
                        "familia": token_trades["familia"].iloc[0],
                        "hhmm": token_trades["hhmm"].iloc[0],
                        "direcao": token_trades["direcao"].iloc[0],
                        "token": token_trades["token"].iloc[0],
                        "combo": nomes,
                        "min_votos": min_votos,
                        "regime": regime,
                    }
                )
                prelim.append(row)

    if not prelim:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    prelim = sorted(prelim, key=lambda x: x["score"], reverse=True)[:TOP_PRELIM_POR_TOKEN]
    finais = []
    folds_out = []
    trades_out = []
    for cand in prelim:
        for dow_grupo in DOW_GRUPOS:
            row, fold_df, trades = avaliar_final(token_trades, cand, folds, dow_grupo)
            if row is None:
                continue
            if row["teste_trades"] < MIN_TESTE_TOTAL_PRE or row["folds_teste_ok"] < 4:
                continue
            finais.append(row)
            folds_out.append(fold_df)
            if not trades.empty:
                trades_out.append(trades.assign(candidato_id=row["id"]))

    ranking = pd.DataFrame(finais)
    if not ranking.empty:
        ranking = ranking.sort_values(["score", "folds_teste_ok", "teste_pontos"], ascending=False)
    folds_df = pd.concat(folds_out, ignore_index=True) if folds_out else pd.DataFrame()
    trades_df = pd.concat(trades_out, ignore_index=True) if trades_out else pd.DataFrame()
    return ranking, folds_df, trades_df


def avaliar_trades_combo(combo_id, trades, folds):
    trades = filtrar_aberta(trades.copy())
    modelo = recorte_anos(trades, ANOS_MODELO)
    rm = resumo(modelo)
    if rm["trades"] < MIN_MODELO_FINAL or rm["pontos"] <= 0:
        return None, pd.DataFrame(), trades

    fold_rows = []
    testes = []
    folds_treino_ok = 0
    folds_teste_ok = 0
    folds_teste_neg = 0
    for fold in folds:
        treino = trades[trades["mes"].isin(fold["treino"])]
        teste = trades[trades["mes"].eq(fold["teste"])]
        rt = resumo(treino)
        rs = resumo(teste)
        treino_ok = rt["trades"] >= MIN_TREINO_FOLD and rt["pontos"] > 0 and rt["winrate"] >= 60.0
        teste_ok = treino_ok and rs["trades"] >= MIN_TESTE_FOLD and rs["pontos"] > 0 and rs["winrate"] >= 55.0
        folds_treino_ok += int(treino_ok)
        folds_teste_ok += int(teste_ok)
        folds_teste_neg += int(treino_ok and rs["pontos"] < 0)
        if treino_ok:
            testes.append(teste)
        fold_rows.append(
            {
                "tipo": "combo",
                "id": combo_id,
                "fold": fold["fold"],
                **{f"treino_{k}": v for k, v in rt.items()},
                **{f"teste_{k}": v for k, v in rs.items()},
                "treino_ok": treino_ok,
                "teste_ok": teste_ok,
            }
        )

    teste_pool = filtrar_aberta(pd.concat(testes, ignore_index=True)) if testes else pd.DataFrame()
    r2024 = resumo(recorte_ano(trades, 2024))
    r2025 = resumo(recorte_ano(trades, 2025))
    if r2024["pontos"] <= 0 or r2025["pontos"] <= 0:
        return None, pd.DataFrame(fold_rows), trades

    row = {
        "id": combo_id,
        "folds_total": len(folds),
        "folds_treino_ok": folds_treino_ok,
        "folds_teste_ok": folds_teste_ok,
        "folds_teste_neg": folds_teste_neg,
        **{f"teste_{k}": v for k, v in resumo(teste_pool).items()},
        **{f"{k}_modelo": v for k, v in rm.items()},
        **{f"{k}_2024": v for k, v in r2024.items()},
        **{f"{k}_2025": v for k, v in r2025.items()},
        **{f"{k}_2026": v for k, v in resumo(recorte_ano(trades, ANO_HOLDOUT)).items()},
        **{f"{k}_90": v for k, v in resumo_recorte(trades, 90).items()},
        **{f"{k}_30": v for k, v in resumo_recorte(trades, 30).items()},
    }
    row["score"] = score_linha(row)
    return row, pd.DataFrame(fold_rows), trades


def montar_combos(ranking, trades_top, folds):
    if ranking.empty or trades_top.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    trades_por_id = {
        cand_id: grupo.drop(columns=["candidato_id"], errors="ignore")
        for cand_id, grupo in trades_top.groupby("candidato_id")
    }

    noite = ranking[ranking["familia"].eq("noite")].drop_duplicates("id").head(TOP_FINAL_POR_FAMILIA)
    manha = ranking[ranking["familia"].eq("manha")].drop_duplicates("id").head(TOP_FINAL_POR_FAMILIA)

    linhas = []
    folds_out = []
    trades_out = []
    for _, n in noite.iterrows():
        for _, m in manha.iterrows():
            if n["id"] not in trades_por_id or m["id"] not in trades_por_id:
                continue
            combo_id = f"COMBO::{n['id']} + {m['id']}"
            trades = pd.concat([trades_por_id[n["id"]], trades_por_id[m["id"]]], ignore_index=True)
            row, fdf, tdf = avaliar_trades_combo(combo_id, trades, folds)
            if row is None:
                continue
            row.update(
                {
                    "noite_id": n["id"],
                    "manha_id": m["id"],
                    "noite_token": n["token"],
                    "manha_token": m["token"],
                    "noite_regra": f"{n['combo']} | v{n['min_votos']} | {n['regime']} | {n['dow_grupo']}",
                    "manha_regra": f"{m['combo']} | v{m['min_votos']} | {m['regime']} | {m['dow_grupo']}",
                }
            )
            linhas.append(row)
            folds_out.append(fdf)
            trades_out.append(tdf.assign(candidato_id=combo_id))

    combos = pd.DataFrame(linhas)
    if not combos.empty:
        combos = combos.sort_values(["score", "folds_teste_ok", "teste_pontos"], ascending=False)
    folds_df = pd.concat(folds_out, ignore_index=True) if folds_out else pd.DataFrame()
    trades_df = pd.concat(trades_out, ignore_index=True) if trades_out else pd.DataFrame()
    return combos, folds_df, trades_df


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
        "id",
        "folds_teste_ok",
        "teste_trades",
        "teste_winrate",
        "teste_pontos",
        "trades_modelo",
        "winrate_modelo",
        "pontos_modelo",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
        "trades_90",
        "winrate_90",
        "pontos_90",
        "trades_30",
        "winrate_30",
        "pontos_30",
    ]
    combo_cols = [
        "id",
        "folds_teste_ok",
        "teste_trades",
        "teste_winrate",
        "teste_pontos",
        "trades_modelo",
        "winrate_modelo",
        "pontos_modelo",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
        "trades_90",
        "winrate_90",
        "pontos_90",
        "trades_30",
        "winrate_30",
        "pontos_30",
    ]
    linhas = [
        "# Confluencia 7 indicadores - rotacao 2024-2025",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Metodo:",
        "",
        "- cada candidato usa exatamente 7 votos de indicadores;",
        "- o sinal exige 5, 6 ou 7 votos alinhados com BUY/SELL;",
        "- horarios testados: noite em torno de 20:54-21:00 e manha em torno de 10:30/11:54;",
        "- rotacao mensal 2M/1M dentro de 2024-2025: treina dois meses e testa o terceiro;",
        f"- {ANO_HOLDOUT} fica fora de quantis, score, folds e escolha; aparece apenas como holdout cego.",
        "",
        "Folds usados:",
        "",
    ]
    linhas.extend([f"- {fold['fold']}" for fold in folds])
    linhas.extend(["", "## Top noite", ""])
    linhas.extend(tabela_md(ranking[ranking["familia"].eq("noite")], cols))
    linhas.extend(["", "## Top manha", ""])
    linhas.extend(tabela_md(ranking[ranking["familia"].eq("manha")], cols))
    linhas.extend(["", "## Top combos noite + manha", ""])
    linhas.extend(tabela_md(combos, combo_cols))
    linhas.extend(
        [
            "",
            "## Leitura inicial",
            "",
            "- Promover para TradingView somente candidatos que continuem fortes no holdout 2026 e nos recortes recentes.",
            "- O score acima nao usa 2026; se 2026 estiver ruim, o candidato deve ser tratado como reprovado ou apenas diagnostico.",
            "- Esta busca e a primeira bateria de confluencia. Apos teste no TV, registrar os resultados reais no relatorio principal.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    print("=====================================================", flush=True)
    print("BUSCA CONFLUENCIA 7 INDICADORES - ROTACAO 2024-2025", flush=True)
    print("2026 e holdout cego: nao entra no score nem nos folds.", flush=True)
    print("=====================================================", flush=True)

    df = preparar()
    votos = montar_votos(df)
    folds = folds_2m1m_rolling(sorted(df["mes"].dropna().unique()))
    print("Folds 2M/1M:", len(folds), flush=True)
    for fold in folds:
        print(" ", fold["fold"], flush=True)

    shared = {
        "open": df["open"].to_numpy(dtype=float),
        "high": df["high"].to_numpy(dtype=float),
        "low": df["low"].to_numpy(dtype=float),
        "data": df["DataHora_SP"].to_numpy(),
    }
    combos_nomes = list(combinations(VOTOS, 7))
    combos_idx = [tuple(VOTOS.index(nome) for nome in combo) for combo in combos_nomes]
    print("Combinacoes de 7 indicadores:", len(combos_nomes), flush=True)

    rankings = []
    folds_out = []
    trades_out = []
    for familia, horarios in HORARIOS.items():
        for hhmm in horarios:
            for direcao in ["BUY", "SELL"]:
                token_trades = montar_token_trades(df, votos, shared, familia, hhmm, direcao)
                ranking, fold_df, trades_df = buscar_token(token_trades, folds, combos_idx, combos_nomes)
                if ranking.empty:
                    print(f"{familia} {hhmm} {direcao}: sem candidato", flush=True)
                    continue
                rankings.append(ranking)
                if not fold_df.empty:
                    folds_out.append(fold_df)
                if not trades_df.empty:
                    trades_out.append(trades_df)
                top = ranking.iloc[0]
                print(
                    f"{familia} {hhmm} {direcao}: "
                    f"folds={top['folds_teste_ok']}/{top['folds_total']} "
                    f"teste={top['teste_trades']}tr {top['teste_winrate']:.1f}% {top['teste_pontos']:.1f} "
                    f"modelo={top['trades_modelo']}tr {top['winrate_modelo']:.1f}% {top['pontos_modelo']:.1f} "
                    f"2026={top['trades_2026']}tr {top['winrate_2026']:.1f}% {top['pontos_2026']:.1f} "
                    f"id={top['id']}",
                    flush=True,
                )

    ranking = pd.concat(rankings, ignore_index=True) if rankings else pd.DataFrame()
    if not ranking.empty:
        ranking = ranking.sort_values(["score", "folds_teste_ok", "teste_pontos"], ascending=False)
    folds_df = pd.concat(folds_out, ignore_index=True) if folds_out else pd.DataFrame()
    trades_df = pd.concat(trades_out, ignore_index=True) if trades_out else pd.DataFrame()
    combos, combo_folds, combo_trades = montar_combos(ranking, trades_df, folds)

    ranking_salvar = ranking.head(TOP_RANKING_SALVAR).copy()
    combos_salvar = combos.head(TOP_COMBOS_SALVAR).copy()
    ids_salvar = set(ranking_salvar.head(TOP_TRADES_SALVAR)["id"].astype(str))
    if not combos_salvar.empty:
        ids_salvar.update(combos_salvar.head(20)["id"].astype(str))

    folds_salvar = pd.concat([folds_df, combo_folds], ignore_index=True)
    if not folds_salvar.empty and ids_salvar:
        folds_salvar = folds_salvar[folds_salvar["id"].astype(str).isin(ids_salvar)].copy()

    trades_salvar = pd.concat([trades_df, combo_trades], ignore_index=True)
    if not trades_salvar.empty and ids_salvar:
        trades_salvar = trades_salvar[trades_salvar["candidato_id"].astype(str).isin(ids_salvar)].copy()

    ranking_salvar.to_csv(ARQ_RANKING, index=False)
    combos_salvar.to_csv(ARQ_COMBOS, index=False)
    folds_salvar.to_csv(ARQ_FOLDS, index=False)
    trades_salvar.to_csv(ARQ_TRADES, index=False)
    escrever_md(ranking, combos, folds)

    cols = [
        "id",
        "folds_teste_ok",
        "teste_trades",
        "teste_winrate",
        "teste_pontos",
        "trades_modelo",
        "winrate_modelo",
        "pontos_modelo",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
        "trades_90",
        "winrate_90",
        "pontos_90",
        "trades_30",
        "winrate_30",
        "pontos_30",
    ]
    print("\nTop geral individual:")
    if not ranking.empty:
        print(ranking[cols].head(20).to_string(index=False, max_colwidth=140))
    print("\nTop combos:")
    if not combos.empty:
        print(combos[cols].head(20).to_string(index=False, max_colwidth=140))
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_COMBOS)
    print(ARQ_FOLDS)
    print(ARQ_TRADES)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
