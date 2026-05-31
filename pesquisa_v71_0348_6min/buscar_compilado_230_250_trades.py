from pathlib import Path
from datetime import datetime

import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor, simular_trade


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARQ_RANKING = SAIDA_DIR / f"busca_compilado_230_250_trades_ranking_{STAMP}.csv"
ARQ_TRADES = SAIDA_DIR / f"busca_compilado_230_250_trades_top_{STAMP}.csv"

TAKE = 50.5
STOP = 117.0
ALVO_MIN = 230
ALVO_MAX = 250


def metricas(df, dias=365):
    if df.empty:
        return {
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "dias_com_operacao": 0,
        }
    fim = df["datahora_entrada"].max()
    base = df[df["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return {
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "dias_com_operacao": 0,
        }
    p = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "max_drawdown": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "dias_com_operacao": int(base["datahora_entrada"].dt.date.nunique()),
    }


def sinais_dmi3(candles):
    df = candles.copy()
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    dow = df["DataHora_SP"].dt.day_name()
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
        ("DMI3_0348_BUY", (h == 3) & (m == 48) & ok & (score0348 >= 0) & dow.isin(["Monday", "Tuesday"]), "BUY"),
        ("DMI3_1030_BUY", (h == 10) & (m == 30) & ok & (score1030 >= 0) & dow.eq("Monday"), "BUY"),
        ("DMI3_1030_SELL", (h == 10) & (m == 30) & ok & (score1030 < 0) & dow.eq("Friday"), "SELL"),
        ("DMI3_2058_BUY", (h == 20) & (m == 58) & ok & (score2058 >= 0) & dow.isin(["Sunday", "Wednesday"]), "BUY"),
    ]
    sinais = []
    for modulo, mask, direcao in regras:
        for idx in df.index[mask]:
            sinais.append((idx, modulo, direcao, TAKE, STOP))
    return sinais


def sinais_emaadx(candles, nome, hhmm, lado, adx_min, gap_min):
    df = candles.copy()
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    hora, minuto = [int(x) for x in hhmm.split(":")]
    horario = (h == hora) & (m == minuto)
    ok = horario & (df["adx14"] >= adx_min) & (df["dmi_gap"] >= gap_min)
    if lado == "BUY":
        mask = ok & (df["ema17"] > df["ema34"]) & (df["di_plus"] > df["di_minus"])
    else:
        mask = ok & (df["ema17"] < df["ema34"]) & (df["di_minus"] > df["di_plus"])
    return [(idx, nome, lado, TAKE, STOP) for idx in df.index[mask]]


def sinais_dmi10(candles, nome, hhmm, lado):
    df = candles.copy()
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    hora, minuto = [int(x) for x in hhmm.split(":")]
    horario = (h == hora) & (m == minuto)
    ok = horario & (df["adx14"] >= 25) & (df["dmi_gap"] >= 10)
    if lado == "BUY":
        mask = ok & (df["di_plus"] > df["di_minus"])
    else:
        mask = ok & (df["di_minus"] > df["di_plus"])
    return [(idx, nome, lado, TAKE, STOP) for idx in df.index[mask]]


def simular(candles, sinais, cache=None):
    cache = {} if cache is None else cache
    trades = []
    proxima_liberada = pd.Timestamp.min
    for idx, modulo, direcao, take, stop in sorted(sinais, key=lambda x: (x[0], x[1])):
        data_sinal = candles.at[idx, "DataHora_SP"]
        if data_sinal < proxima_liberada:
            continue
        chave = (idx, direcao, take, stop)
        if chave not in cache:
            cache[chave] = simular_trade(candles, idx, direcao, take, stop)
        sim = cache[chave]
        if sim is None:
            continue
        data_entrada, data_saida, pontos, resultado = sim
        proxima_liberada = data_saida
        trades.append(
            {
                "modulo": modulo,
                "datahora_sinal": data_sinal,
                "datahora_entrada": data_entrada,
                "datahora_saida": data_saida,
                "direcao": direcao,
                "pontos": pontos,
                "resultado": resultado,
            }
        )
    return pd.DataFrame(trades)


def score(row):
    trades = row["trades_365"]
    distancia = 0 if ALVO_MIN <= trades <= ALVO_MAX else min(abs(trades - ALVO_MIN), abs(trades - ALVO_MAX))
    penal_win = max(0.0, 80.0 - row["winrate_365"]) * 500
    penal_trades = distancia * 35
    return (
        row["pontos_365"]
        + 250 * row["profit_factor_365"]
        + 20 * row["winrate_365"]
        - 0.9 * abs(row["max_drawdown_365"])
        - penal_win
        - penal_trades
    )


def avaliar_combo(candles, base, combo, cache):
    nomes = [x[0] for x in combo]
    sinais = list(base)
    for _, s, _ in combo:
        sinais.extend(s)
    trades = simular(candles, sinais, cache)
    m365 = metricas(trades, 365)
    m90 = metricas(trades, 90)
    m30 = metricas(trades, 30)
    row = {
        "modulos_extra": " + ".join(nomes) if nomes else "DMI3_SOZINHO",
        "qtd_modulos_extra": len(combo),
        "trades_365": m365["trades"],
        "dias_com_operacao_365": m365["dias_com_operacao"],
        "winrate_365": m365["winrate"],
        "pontos_365": m365["pontos"],
        "max_drawdown_365": m365["max_drawdown"],
        "profit_factor_365": m365["profit_factor"],
        "trades_90": m90["trades"],
        "winrate_90": m90["winrate"],
        "pontos_90": m90["pontos"],
        "trades_30": m30["trades"],
        "winrate_30": m30["winrate"],
        "pontos_30": m30["pontos"],
    }
    row["score"] = score(row)
    return row


def main():
    candles = indicadores(carregar_candles())
    cache = {}
    base = sinais_dmi3(candles)

    modulos = []
    for hhmm in ["03:46", "03:48", "03:50", "10:26", "10:28", "10:30", "20:52", "20:54", "20:56", "20:58"]:
        for lado in ["BUY", "SELL"]:
            modulos.append((f"DMI10_{hhmm}_{lado}", sinais_dmi10(candles, f"DMI10_{hhmm}_{lado}", hhmm, lado)))
            for adx_min in [25, 28, 30, 32, 35]:
                for gap_min in [4, 6, 8, 10]:
                    nome = f"EA_{hhmm}_{lado}_ADX{adx_min}_G{gap_min}"
                    modulos.append((nome, sinais_emaadx(candles, nome, hhmm, lado, adx_min, gap_min)))

    base_row = avaliar_combo(candles, base, [], cache)
    print("Base DMI3:", base_row, flush=True)

    modulos_filtrados = []
    for nome, sinais in modulos:
        trades = simular(candles, sinais, cache)
        m = metricas(trades, 365)
        if m["trades"] >= 8 and m["pontos"] > -300 and m["winrate"] >= 60:
            modulos_filtrados.append((nome, sinais, m))

    modulos_filtrados = sorted(
        modulos_filtrados,
        key=lambda x: (x[2]["winrate"], x[2]["profit_factor"], x[2]["pontos"], x[2]["trades"]),
        reverse=True,
    )[:25]

    print("Modulos candidatos apos filtro:", len(modulos_filtrados), flush=True)
    print("Top modulos individuais:", flush=True)
    for nome, _, m in sorted(modulos_filtrados, key=lambda x: (x[2]["winrate"], x[2]["trades"]), reverse=True)[:30]:
        print(nome, m, flush=True)

    linhas = [base_row]
    beam = [()]
    vistos = {""}
    for tamanho in [1, 2, 3, 4]:
        proximos = []
        for combo in beam:
            usados = {m[0] for m in combo}
            for modulo in modulos_filtrados:
                if modulo[0] in usados:
                    continue
                novo = tuple(sorted(combo + (modulo,), key=lambda x: x[0]))
                chave = " + ".join(x[0] for x in novo)
                if chave in vistos:
                    continue
                vistos.add(chave)
                row = avaliar_combo(candles, base, novo, cache)
                linhas.append(row)
                proximos.append((row["score"], novo))
        proximos = sorted(proximos, key=lambda x: x[0], reverse=True)[:25]
        beam = [x[1] for x in proximos]
        print(f"Beam tamanho {tamanho}: {len(beam)} combinacoes mantidas", flush=True)

    ranking = pd.DataFrame(linhas).sort_values(
        ["score", "winrate_365", "pontos_365"], ascending=[False, False, False]
    )
    print("\nTop geral:", flush=True)
    print(ranking.head(30).to_string(index=False), flush=True)
    alvo = ranking[
        (ranking["trades_365"].between(ALVO_MIN, ALVO_MAX))
        & (ranking["winrate_365"] >= 80)
        & (ranking["pontos_365"] > 0)
    ]
    print("\nDentro do alvo 230-250 e winrate >= 80:", len(alvo), flush=True)
    if not alvo.empty:
        print(alvo.head(20).to_string(index=False), flush=True)

    try:
        ranking.to_csv(ARQ_RANKING, index=False)
        if not ranking.empty:
            melhor = ranking.iloc[0]["modulos_extra"]
            nomes = [] if melhor == "DMI3_SOZINHO" else str(melhor).split(" + ")
            sinais = list(base)
            mapa = {nome: s for nome, s, _ in modulos_filtrados}
            for nome in nomes:
                sinais.extend(mapa[nome])
            trades_top = simular(candles, sinais)
            trades_top.to_csv(ARQ_TRADES, index=False)
    except PermissionError as exc:
        print("AVISO: nao consegui salvar CSV, provavelmente arquivo aberto/bloqueado:", exc)


if __name__ == "__main__":
    main()
