from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor, simular_trade


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARQ_RANKING = SAIDA_DIR / f"busca_regime_dia_230_250_ranking_{STAMP}.csv"
ARQ_TRADES = SAIDA_DIR / f"busca_regime_dia_230_250_trades_{STAMP}.csv"

TAKE = 50.5
STOP = 117.0
HORARIOS = ["03:46", "03:48", "03:50", "10:26", "10:28", "10:30", "20:52", "20:54", "20:56", "20:58"]


def metricas(df, dias=365):
    if df.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0, "dias": 0}
    fim = df["datahora_entrada"].max()
    base = df[df["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0, "dias": 0}
    p = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "dd": max_drawdown(p),
        "pf": profit_factor(p),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
    }


def preparar_candles():
    df = indicadores(carregar_candles()).reset_index(drop=True)
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df["data"] = df["DataHora_SP"].dt.date
    df["ema200_slope10"] = df["ema200"] - df["ema200"].shift(10)
    df["ema34_slope10"] = df["ema34"] - df["ema34"].shift(10)
    df["vwap_slope10"] = df["vwap"] - df["vwap"].shift(10)
    df["dist_vwap"] = df["close"] - df["vwap"]
    df["dist_ema200"] = df["close"] - df["ema200"]
    df["range_30"] = (df["high"].rolling(15).max() - df["low"].rolling(15).min())
    df["range_60"] = (df["high"].rolling(30).max() - df["low"].rolling(30).min())
    df["ret_30"] = df["close"] - df["close"].shift(15)
    df["ret_60"] = df["close"] - df["close"].shift(30)
    return df


def sinais_dmi3(candles):
    df = candles.copy()
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    voto_macd = (df["macd"] >= df["macd_signal"]).map({True: 1, False: -1})
    voto_candle = (df["body"] >= 0).map({True: 1, False: -1})
    voto_prev_roc5_contra = (df["prev_roc5"] <= 0).map({True: 1, False: -1})
    voto_sma1734 = (df["sma17"] >= df["sma34"]).map({True: 1, False: -1})
    voto_roc10 = (df["roc10"] >= 0).map({True: 1, False: -1})
    voto_ema1734 = (df["ema17"] >= df["ema34"]).map({True: 1, False: -1})
    voto_roc5 = (df["roc5"] >= 0).map({True: 1, False: -1})
    voto_vwap = (df["close"] >= df["vwap"]).map({True: 1, False: -1})
    score0348 = voto_macd + voto_candle + voto_prev_roc5_contra
    score1030 = voto_sma1734 + voto_roc10 + voto_prev_roc5_contra
    score2058 = voto_ema1734 + voto_roc5 + voto_vwap
    ok = df["dmi_gap"] >= 3
    regras = [
        ("DMI3_0348_BUY", (h == 3) & (m == 48) & ok & (score0348 >= 0) & df["dow"].isin(["Monday", "Tuesday"]), "BUY"),
        ("DMI3_1030_BUY", (h == 10) & (m == 30) & ok & (score1030 >= 0) & df["dow"].eq("Monday"), "BUY"),
        ("DMI3_1030_SELL", (h == 10) & (m == 30) & ok & (score1030 < 0) & df["dow"].eq("Friday"), "SELL"),
        ("DMI3_2058_BUY", (h == 20) & (m == 58) & ok & (score2058 >= 0) & df["dow"].isin(["Sunday", "Wednesday"]), "BUY"),
    ]
    sinais = []
    for nome, mask, direcao in regras:
        for idx in df.index[mask]:
            sinais.append((idx, nome, direcao, TAKE, STOP))
    return sinais


def simular_lista(candles, sinais, cache):
    trades = []
    proxima_liberada = pd.Timestamp.min
    for idx, modulo, direcao, take, stop in sorted(sinais, key=lambda x: (x[0], x[1])):
        data_sinal = candles.at[idx, "DataHora_SP"]
        if data_sinal < proxima_liberada:
            continue
        chave = (idx, direcao)
        if chave not in cache:
            cache[chave] = simular_trade(candles, idx, direcao, take, stop)
        sim = cache[chave]
        if sim is None:
            continue
        entrada, saida, pontos, resultado = sim
        proxima_liberada = saida
        trades.append({
            "modulo": modulo,
            "datahora_sinal": data_sinal,
            "datahora_entrada": entrada,
            "datahora_saida": saida,
            "direcao": direcao,
            "pontos": pontos,
            "resultado": resultado,
        })
    return pd.DataFrame(trades)


def gerar_modulos_regime(candles, cache):
    candidatos = []
    idxs = candles.index[candles["hhmm"].isin(HORARIOS)].tolist()
    base_cols = [
        "adx14", "dmi_gap", "range_30", "range_60", "ret_30", "ret_60",
        "dist_vwap", "dist_ema200", "ema34_slope10", "ema200_slope10", "vwap_slope10",
    ]

    for hhmm in HORARIOS:
        for direcao in ["BUY", "SELL"]:
            mask_hd = candles["hhmm"].eq(hhmm)
            if direcao == "BUY":
                mask_base = mask_hd & (candles["ema17"] >= candles["ema34"]) & (candles["di_plus"] >= candles["di_minus"])
            else:
                mask_base = mask_hd & (candles["ema17"] < candles["ema34"]) & (candles["di_minus"] > candles["di_plus"])
            for adx_min in [0, 20, 25, 30]:
                for gap_min in [0, 3, 6, 10]:
                    mask = mask_base & (candles["adx14"] >= adx_min) & (candles["dmi_gap"] >= gap_min)
                    idx_base = candles.index[mask].tolist()
                    if len(idx_base) < 12:
                        continue
                    raw_sinais = [(idx, f"R_{hhmm}_{direcao}_A{adx_min}_G{gap_min}", direcao, TAKE, STOP) for idx in idx_base]
                    raw_trades = simular_lista(candles, raw_sinais, cache)
                    if raw_trades.empty:
                        continue
                    m_raw = metricas(raw_trades, 365)
                    if m_raw["trades"] >= 8 and m_raw["pontos"] > -400 and m_raw["winrate"] >= 58:
                        candidatos.append((raw_sinais[0][1], raw_sinais, m_raw))

                    for col in base_cols:
                        vals = candles.loc[idx_base, col].dropna()
                        if len(vals) < 12:
                            continue
                        qs = vals.quantile([0.25, 0.5, 0.75]).dropna().unique()
                        for q in qs:
                            for op, suffix in [(">=", "GE"), ("<=", "LE")]:
                                if op == ">=":
                                    idx_filtrado = candles.index[mask & (candles[col] >= q)].tolist()
                                else:
                                    idx_filtrado = candles.index[mask & (candles[col] <= q)].tolist()
                                if len(idx_filtrado) < 8:
                                    continue
                                nome = f"R_{hhmm}_{direcao}_A{adx_min}_G{gap_min}_{col}_{suffix}{round(float(q), 2)}"
                                sinais = [(idx, nome, direcao, TAKE, STOP) for idx in idx_filtrado]
                                trades = simular_lista(candles, sinais, cache)
                                m = metricas(trades, 365)
                                if m["trades"] >= 8 and m["pontos"] > -250 and m["winrate"] >= 62:
                                    candidatos.append((nome, sinais, m))

    candidatos = sorted(
        candidatos,
        key=lambda x: (x[2]["winrate"], x[2]["pf"], x[2]["pontos"], x[2]["trades"]),
        reverse=True,
    )
    # Evita centenas de variantes quase iguais por horario/direcao.
    escolhidos = []
    buckets = {}
    for nome, sinais, m in candidatos:
        partes = nome.split("_")
        bucket = "_".join(partes[:3])
        buckets[bucket] = buckets.get(bucket, 0) + 1
        if buckets[bucket] <= 8:
            escolhidos.append((nome, sinais, m))
        if len(escolhidos) >= 80:
            break
    return escolhidos


def score(row):
    trades = row["trades_365"]
    dist = 0 if 230 <= trades <= 250 else min(abs(trades - 230), abs(trades - 250))
    return (
        row["pontos_365"]
        + 250 * min(row["pf_365"], 5)
        + 25 * row["winrate_365"]
        - 0.8 * abs(row["dd_365"])
        - 120 * dist
        - 750 * max(0, 80 - row["winrate_365"])
    )


def avaliar(candles, base, combo, cache):
    sinais = list(base)
    nomes = []
    for nome, s, _ in combo:
        nomes.append(nome)
        sinais.extend(s)
    trades = simular_lista(candles, sinais, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    row = {
        "modulos": " + ".join(nomes) if nomes else "DMI3_SOZINHO",
        "qtd_modulos": len(combo),
        "trades_365": m365["trades"],
        "dias_365": m365["dias"],
        "winrate_365": m365["winrate"],
        "pontos_365": m365["pontos"],
        "dd_365": m365["dd"],
        "pf_365": m365["pf"],
        "trades_90": m90["trades"],
        "winrate_90": m90["winrate"],
        "pontos_90": m90["pontos"],
        "trades_30": m30["trades"],
        "winrate_30": m30["winrate"],
        "pontos_30": m30["pontos"],
    }
    row["score"] = score(row)
    return row, trades


def main():
    candles = preparar_candles()
    cache = {}
    base = sinais_dmi3(candles)
    base_row, _ = avaliar(candles, base, [], cache)
    print("Base DMI3:", base_row, flush=True)

    modulos = gerar_modulos_regime(candles, cache)
    print("Modulos regime:", len(modulos), flush=True)
    for nome, _, m in modulos[:30]:
        print(nome, m, flush=True)

    linhas = [base_row]
    melhor_trades = pd.DataFrame()
    beam = [()]
    vistos = {""}
    for tamanho in [1, 2, 3, 4, 5, 6]:
        prox = []
        for combo in beam:
            usados = {x[0] for x in combo}
            for modulo in modulos:
                if modulo[0] in usados:
                    continue
                novo = tuple(sorted(combo + (modulo,), key=lambda x: x[0]))
                chave = " + ".join(x[0] for x in novo)
                if chave in vistos:
                    continue
                vistos.add(chave)
                row, trades = avaliar(candles, base, novo, cache)
                linhas.append(row)
                prox.append((row["score"], novo, trades))
        prox = sorted(prox, key=lambda x: x[0], reverse=True)[:60]
        beam = [x[1] for x in prox]
        if prox and (melhor_trades.empty or prox[0][0] > max(x.get("score", -999999) for x in linhas[:-1])):
            melhor_trades = prox[0][2]
        print(f"Beam {tamanho}: {len(beam)}", flush=True)

    ranking = pd.DataFrame(linhas).sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    cols = [
        "modulos", "qtd_modulos", "score", "trades_365", "dias_365", "winrate_365",
        "pontos_365", "dd_365", "pf_365", "trades_90", "winrate_90", "pontos_90",
        "trades_30", "winrate_30", "pontos_30",
    ]
    print("\nTop geral:")
    print(ranking[cols].head(30).to_string(index=False), flush=True)
    alvo = ranking[(ranking["trades_365"].between(230, 250)) & (ranking["winrate_365"] >= 80) & (ranking["pontos_365"] > 0)]
    print("\nAlvo 230-250 e >=80:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo[cols].head(20).to_string(index=False), flush=True)

    try:
        ranking.to_csv(ARQ_RANKING, index=False)
        melhor = ranking.iloc[0]["modulos"]
        nomes = [] if melhor == "DMI3_SOZINHO" else str(melhor).split(" + ")
        mapa = {nome: s for nome, s, _ in modulos}
        sinais = list(base)
        for nome in nomes:
            sinais.extend(mapa[nome])
        trades = simular_lista(candles, sinais, cache)
        trades.to_csv(ARQ_TRADES, index=False)
        print("Arquivos:", flush=True)
        print(ARQ_RANKING, flush=True)
        print(ARQ_TRADES, flush=True)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV:", exc, flush=True)


if __name__ == "__main__":
    main()
