from datetime import datetime
from pathlib import Path

import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor, simular_trade


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
SAIDA = BASE_DIR / "pesquisa_v71_0348_6min" / f"otimizacao_compilado_emaadx_{STAMP}.csv"
SAIDA_XLSX = BASE_DIR / "pesquisa_v71_0348_6min" / f"otimizacao_compilado_emaadx_{STAMP}.xlsx"


def metricas(df, dias=365):
    if df.empty:
        return 0, 0.0, 0.0, 0.0, 0.0
    fim = df["datahora_entrada"].max()
    base = df[df["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return 0, 0.0, 0.0, 0.0, 0.0
    p = base["pontos"].astype(float)
    return len(base), float((p > 0).mean() * 100), float(p.sum()), max_drawdown(p), profit_factor(p)


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
        ("DMI3_0348_BUY", (h == 3) & (m == 48) & ok & (score0348 >= 0) & dow.isin(["Monday", "Tuesday"]), "BUY", 50.5, 117.0),
        ("DMI3_1030_BUY", (h == 10) & (m == 30) & ok & (score1030 >= 0) & dow.eq("Monday"), "BUY", 50.5, 117.0),
        ("DMI3_1030_SELL", (h == 10) & (m == 30) & ok & (score1030 < 0) & dow.eq("Friday"), "SELL", 50.5, 117.0),
        ("DMI3_2058_BUY", (h == 20) & (m == 58) & ok & (score2058 >= 0) & dow.isin(["Sunday", "Wednesday"]), "BUY", 50.5, 117.0),
    ]
    sinais = []
    for modulo, mask, direcao, take, stop in regras:
        for idx in df.index[mask]:
            sinais.append((idx, modulo, direcao, take, stop))
    return sinais


def sinais_emaadx(candles, adx_min, gap_min, lado, usar2052):
    df = candles.copy()
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    horario = ((h == 3) & (m == 50)) | ((h == 20) & (m == 54))
    if usar2052:
        horario = horario | ((h == 20) & (m == 52))
    ok = horario & (df["adx14"] >= adx_min) & (df["dmi_gap"] >= gap_min)
    buy = ok & (df["ema17"] > df["ema34"]) & (df["di_plus"] > df["di_minus"])
    sell = ok & (df["ema17"] < df["ema34"]) & (df["di_minus"] > df["di_plus"])
    sinais = []
    if lado in ("BUY", "AMBOS"):
        for idx in df.index[buy]:
            sinais.append((idx, "EMAADX_BUY", "BUY", 50.5, 117.0))
    if lado in ("SELL", "AMBOS"):
        for idx in df.index[sell]:
            sinais.append((idx, "EMAADX_SELL", "SELL", 50.5, 117.0))
    return sinais


def simular(candles, sinais):
    trades = []
    proxima_liberada = pd.Timestamp.min
    for idx, modulo, direcao, take, stop in sorted(sinais, key=lambda x: (x[0], x[1])):
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


def main():
    candles = indicadores(carregar_candles())
    base_dmi3 = sinais_dmi3(candles)
    linhas = []
    combos = [
        (28, 4, "AMBOS", False),
        (30, 6, "AMBOS", False),
        (32, 8, "AMBOS", False),
        (35, 10, "AMBOS", False),
        (30, 6, "SELL", False),
        (32, 8, "SELL", False),
        (35, 10, "SELL", False),
        (30, 6, "BUY", False),
        (32, 8, "BUY", False),
        (35, 10, "BUY", False),
    ]
    for adx_min, gap_min, lado, usar2052 in combos:
        sinais = base_dmi3 + sinais_emaadx(candles, adx_min, gap_min, lado, usar2052)
        trades = simular(candles, sinais)
        m365 = metricas(trades, 365)
        m90 = metricas(trades, 90)
        m30 = metricas(trades, 30)
        linhas.append(
            {
                "adx_min": adx_min,
                "gap_min": gap_min,
                "lado": lado,
                "usar2052": usar2052,
                "d365_trades": m365[0],
                "d365_winrate": m365[1],
                "d365_pontos": m365[2],
                "d365_dd": m365[3],
                "d365_pf": m365[4],
                "d90_trades": m90[0],
                "d90_winrate": m90[1],
                "d90_pontos": m90[2],
                "d30_trades": m30[0],
                "d30_winrate": m30[1],
                "d30_pontos": m30[2],
            }
        )
    out = pd.DataFrame(linhas)
    out = out.sort_values(["d365_winrate", "d365_trades", "d365_pontos"], ascending=[False, False, False])
    print(out.head(30).to_string(index=False))
    out.to_csv(SAIDA, index=False)
    with pd.ExcelWriter(SAIDA_XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="ranking", index=False)
    print("Arquivos:")
    print(SAIDA)
    print(SAIDA_XLSX)


if __name__ == "__main__":
    main()
