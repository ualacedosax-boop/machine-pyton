from pathlib import Path

import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RESUMO = SAIDA_DIR / "simulacao_compilado_vencedoras_resumo.csv"
ARQ_TRADES = SAIDA_DIR / "simulacao_compilado_vencedoras_trades.csv"
ARQ_XLSX = SAIDA_DIR / "simulacao_compilado_vencedoras.xlsx"


def max_drawdown(pontos):
    eq = pontos.cumsum()
    if eq.empty:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pontos):
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def metricas(df, nome, dias=None):
    if df.empty:
        return {
            "cenario": nome,
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
        }
    fim = df["datahora_entrada"].max()
    base = df if dias is None else df[df["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return {
            "cenario": nome,
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
        }
    p = base["pontos"].astype(float)
    return {
        "cenario": nome,
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "max_drawdown": max_drawdown(p),
        "profit_factor": profit_factor(p),
    }


def simular_trade(candles, idx_sinal, direcao, take, stop):
    idx_entrada = idx_sinal + 1
    if idx_entrada >= len(candles):
        return None
    entrada = float(candles.at[idx_entrada, "open"])
    if direcao == "BUY":
        preco_take = entrada + take
        preco_stop = entrada - stop
    else:
        preco_take = entrada - take
        preco_stop = entrada + stop

    data_entrada = candles.at[idx_entrada, "DataHora_SP"]
    for j in range(idx_entrada, len(candles)):
        high = float(candles.at[j, "high"])
        low = float(candles.at[j, "low"])
        data_saida = candles.at[j, "DataHora_SP"]
        if direcao == "BUY":
            if low <= preco_stop:
                return data_entrada, data_saida, -stop, "STOP"
            if high >= preco_take:
                return data_entrada, data_saida, take, "TAKE"
        else:
            if high >= preco_stop:
                return data_entrada, data_saida, -stop, "STOP"
            if low <= preco_take:
                return data_entrada, data_saida, take, "TAKE"
    return None


def montar_sinais(candles, usar_dmi3=True, usar_emaadx=True, usar_emaadx_alt=False):
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

    sinais = []
    dmi3_ok = df["dmi_gap"] >= 3
    if usar_dmi3:
        regras = [
            ("DMI3_0348_BUY", (h == 3) & (m == 48) & dmi3_ok & (score0348 >= 0) & dow.isin(["Monday", "Tuesday"]), "BUY", 45.5, 117.0),
            ("DMI3_1030_BUY", (h == 10) & (m == 30) & dmi3_ok & (score1030 >= 0) & dow.eq("Monday"), "BUY", 45.5, 117.0),
            ("DMI3_1030_SELL", (h == 10) & (m == 30) & dmi3_ok & (score1030 < 0) & dow.eq("Friday"), "SELL", 45.5, 117.0),
            ("DMI3_2058_BUY", (h == 20) & (m == 58) & dmi3_ok & (score2058 >= 0) & dow.isin(["Sunday", "Wednesday"]), "BUY", 45.5, 117.0),
        ]
        for modulo, mask, direcao, take, stop in regras:
            for idx in df.index[mask]:
                sinais.append((idx, modulo, direcao, take, stop))

    if usar_emaadx:
        ema_rapida = df["close"].ewm(span=17, adjust=False).mean()
        ema_lenta = df["close"].ewm(span=34, adjust=False).mean()
        horario = ((h == 3) & (m == 50)) | ((h == 20) & (m == 54))
        if usar_emaadx_alt:
            horario = horario | ((h == 20) & (m == 52))
        ok = horario & (df["adx14"] >= 28) & (df["dmi_gap"] >= 4)
        buy = ok & (ema_rapida > ema_lenta) & (df["di_plus"] > df["di_minus"])
        sell = ok & (ema_rapida < ema_lenta) & (df["di_minus"] > df["di_plus"])
        for idx in df.index[buy]:
            sinais.append((idx, "EMAADX_BUY", "BUY", 50.5, 117.0))
        for idx in df.index[sell]:
            sinais.append((idx, "EMAADX_SELL", "SELL", 50.5, 117.0))

    sinais = sorted(sinais, key=lambda x: (x[0], x[1]))
    return sinais


def simular_cenario(candles, nome, usar_dmi3=True, usar_emaadx=True, usar_emaadx_alt=False):
    sinais = montar_sinais(candles, usar_dmi3, usar_emaadx, usar_emaadx_alt)
    trades = []
    proxima_liberada = pd.Timestamp.min
    for idx, modulo, direcao, take, stop in sinais:
        data_sinal = candles.at[idx, "DataHora_SP"]
        if data_sinal < proxima_liberada:
            continue
        sim = simular_trade(candles, idx, direcao, take, stop)
        if sim is None:
            continue
        data_entrada, data_saida, pontos, resultado = sim
        proxima_liberada = data_saida
        trades.append(
            {
                "cenario": nome,
                "modulo": modulo,
                "datahora_sinal": data_sinal,
                "datahora_entrada": data_entrada,
                "datahora_saida": data_saida,
                "direcao": direcao,
                "take": take,
                "stop": stop,
                "pontos": pontos,
                "resultado": resultado,
            }
        )
    return pd.DataFrame(trades)


def main():
    candles = indicadores(carregar_candles())
    cenarios = [
        ("DMI3_TAKE45_SOZINHO", True, False, False),
        ("EMAADX_EXTRA_SOZINHO", False, True, False),
        ("COMPILADO_DMI3_EMAADX", True, True, False),
        ("COMPILADO_COM_2052", True, True, True),
    ]

    todos = []
    resumo = []
    for nome, usar_dmi3, usar_emaadx, usar_alt in cenarios:
        trades = simular_cenario(candles, nome, usar_dmi3, usar_emaadx, usar_alt)
        todos.append(trades)
        resumo.append(metricas(trades, f"{nome}_365d", 365))
        resumo.append(metricas(trades, f"{nome}_90d", 90))
        resumo.append(metricas(trades, f"{nome}_30d", 30))
        if not trades.empty:
            por_modulo = trades.groupby("modulo", dropna=False).apply(lambda g: pd.Series(metricas(g, f"{nome}_modulo"))).reset_index()
            for _, row in por_modulo.iterrows():
                item = row.to_dict()
                item["cenario"] = f"{nome}_{item['modulo']}"
                resumo.append(item)

    trades_all = pd.concat(todos, ignore_index=True) if todos else pd.DataFrame()
    resumo_df = pd.DataFrame(resumo)
    resumo_df.to_csv(ARQ_RESUMO, index=False)
    trades_all.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, sheet_name="resumo", index=False)
        trades_all.to_excel(writer, sheet_name="trades", index=False)

    print(resumo_df[["cenario", "trades", "winrate", "pontos", "max_drawdown", "profit_factor"]].to_string(index=False))
    print("Arquivos:")
    print(ARQ_RESUMO)
    print(ARQ_TRADES)
    print(ARQ_XLSX)


if __name__ == "__main__":
    main()
