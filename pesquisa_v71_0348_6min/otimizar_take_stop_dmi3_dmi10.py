import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SCRIPT_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
sys.path.insert(0, str(SCRIPT_DIR))

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores, mascara_filtro, score_sinais

SAIDA = BASE_DIR / "pesquisa_v71_0348_6min" / "otimizacao_take_stop_dmi3_dmi10.csv"
SAIDA_XLSX = BASE_DIR / "pesquisa_v71_0348_6min" / "otimizacao_take_stop_dmi3_dmi10.xlsx"


def max_drawdown(pontos):
    eq = pontos.cumsum()
    if eq.empty:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pontos):
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def metricas(df, fim, dias=None):
    base = df if dias is None else df[df["datahora_entrada"] >= fim - pd.Timedelta(days=dias)]
    if base.empty:
        return 0, 0.0, 0.0, 0.0, 0.0
    p = base["pontos"].astype(float)
    return len(base), float((p > 0).mean() * 100), float(p.sum()), max_drawdown(p), profit_factor(p)


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


def simular_config(candles, sinais, cfg, take, stop):
    mapa_idx = {dt: i for i, dt in enumerate(candles["DataHora_SP"])}
    selecionados = sinais[mascara_filtro(sinais, cfg)].copy()
    trades = []
    proxima_liberada = pd.Timestamp.min
    for _, sinal in selecionados.iterrows():
        if sinal["DataHora_SP"] < proxima_liberada:
            continue
        idx = mapa_idx.get(sinal["DataHora_SP"])
        if idx is None:
            continue
        sim = simular_trade(candles, idx, sinal["direcao"], take, stop)
        if sim is None:
            continue
        data_entrada, data_saida, pontos, resultado = sim
        proxima_liberada = data_saida
        trades.append(
            {
                "datahora_sinal": sinal["DataHora_SP"],
                "datahora_entrada": data_entrada,
                "datahora_saida": data_saida,
                "horario_sinal": sinal["horario_sinal"],
                "direcao": sinal["direcao"],
                "dow": sinal["dow"],
                "pontos": pontos,
                "resultado": resultado,
            }
        )
    return pd.DataFrame(trades)


def main():
    candidatos = {
        "DMI3_equilibrado": {
            "tokens": {
                "03:48|BUY|Monday",
                "03:48|BUY|Tuesday",
                "10:30|BUY|Monday",
                "10:30|SELL|Friday",
                "20:58|BUY|Sunday",
                "20:58|BUY|Wednesday",
            },
            "adx_min": 0,
            "dmi_gap_min": 3,
            "ema_gap_min": 0,
            "usar_rsi": False,
            "rsi_buy_min": 50,
            "rsi_sell_max": 50,
            "usar_ema200": False,
            "usar_vwap": False,
        },
        "DMI10_alta_acertividade": {
            "tokens": {
                "03:48|BUY|Monday",
                "03:48|BUY|Tuesday",
                "10:30|BUY|Monday",
                "10:30|SELL|Friday",
                "20:58|BUY|Sunday",
                "20:58|BUY|Wednesday",
            },
            "adx_min": 25,
            "dmi_gap_min": 10,
            "ema_gap_min": 0,
            "usar_rsi": False,
            "rsi_buy_min": 50,
            "rsi_sell_max": 50,
            "usar_ema200": False,
            "usar_vwap": False,
        },
    }
    takes = [40.5, 45.5, 50.5, 55.5, 60.5]
    stops = [90.0, 100.0, 110.0, 117.0, 125.0]
    candles = indicadores(carregar_candles())
    sinais = score_sinais(candles).reset_index(drop=True)
    sinais["token"] = sinais["horario_sinal"] + "|" + sinais["direcao"] + "|" + sinais["dow"]
    linhas = []
    for nome, cfg in candidatos.items():
        for take in takes:
            for stop in stops:
                aval = simular_config(candles, sinais, cfg, take, stop)
                if aval.empty:
                    continue
                fim = aval["datahora_entrada"].max()
                m365 = metricas(aval, fim, 365)
                m90 = metricas(aval, fim, 90)
                m30 = metricas(aval, fim, 30)
                linhas.append(
                    {
                        "nome": nome,
                        "take": take,
                        "stop": stop,
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
                        "observacao": "resimulacao_intrabar_stop_primeiro",
                        "config_original": " ; ".join(sorted(cfg["tokens"])),
                    }
                )
    out = pd.DataFrame(linhas)
    out = out.sort_values(["nome", "d365_pontos", "d365_pf"], ascending=[True, False, False])
    out.to_csv(SAIDA, index=False)
    with pd.ExcelWriter(SAIDA_XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="otimizacao", index=False)
    print(out.groupby("nome").head(8).to_string(index=False))
    print("Arquivos:")
    print(SAIDA)
    print(SAIDA_XLSX)


if __name__ == "__main__":
    main()
