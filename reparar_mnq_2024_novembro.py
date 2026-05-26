# -*- coding: utf-8 -*-

from ib_insync import *
from pathlib import Path
from datetime import timedelta
import pandas as pd
import time

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 86

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE_DIR / "dados_mnq_2024_ibkr"

ARQ_CONTINUO = PASTA / "MNQ_2024_2MIN_IBKR_CONTINUO.csv"
ARQ_REPARO = PASTA / "MNQ_2024_REPARO_MNQZ4_20241106_20241110.csv"
ARQ_CONTINUO_REPARADO = PASTA / "MNQ_2024_2MIN_IBKR_CONTINUO_REPARADO.csv"

CONID = 654503320
LOCAL_SYMBOL = "MNQZ4"

INICIO = pd.to_datetime("2024-11-06 00:00:00")
FIM = pd.to_datetime("2024-11-11 23:59:59")


def criar_contrato():
    c = Contract()
    c.secType = "FUT"
    c.conId = CONID
    c.symbol = "MNQ"
    c.exchange = "CME"
    c.currency = "USD"
    c.localSymbol = LOCAL_SYMBOL
    c.includeExpired = True
    return c


def baixar_chunk(ib, contrato, end_dt):
    end_str = (end_dt + timedelta(hours=4)).strftime("%Y%m%d-%H:%M:%S")
    print(f"Baixando chunk ate: {end_str}")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime=end_str,
        durationStr="2 D",
        barSizeSetting="2 mins",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
        keepUpToDate=False,
    )

    if not bars:
        return pd.DataFrame()

    df = util.df(bars)
    if df is None or df.empty:
        return pd.DataFrame()

    return df


def padronizar(df):
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")

    if out["date"].dt.tz is None:
        out["DataHora_Eastern"] = out["date"].dt.tz_localize(
            "America/New_York",
            ambiguous="infer",
            nonexistent="shift_forward"
        )
    else:
        out["DataHora_Eastern"] = out["date"].dt.tz_convert("America/New_York")

    out["DataHora_SP"] = out["DataHora_Eastern"].dt.tz_convert("America/Sao_Paulo")
    out["DataHora_UTC"] = out["DataHora_Eastern"].dt.tz_convert("UTC")

    out["DataHora_SP"] = out["DataHora_SP"].dt.tz_localize(None)
    out["DataHora_UTC"] = out["DataHora_UTC"].dt.tz_localize(None)
    out["DataHora_Eastern"] = out["DataHora_Eastern"].dt.tz_localize(None)

    out["Data"] = out["DataHora_SP"].dt.date.astype(str)
    out["Hora_SP_Decimal"] = (
        out["DataHora_SP"].dt.hour
        + out["DataHora_SP"].dt.minute / 60.0
        + out["DataHora_SP"].dt.second / 3600.0
    )

    out["contrato"] = LOCAL_SYMBOL
    out["localSymbol"] = LOCAL_SYMBOL
    out["conId"] = CONID
    out["symbol"] = "MNQ"
    out["fonte"] = "IBKR"

    colunas = [
        "DataHora_SP",
        "DataHora_Eastern",
        "DataHora_UTC",
        "Data",
        "Hora_SP_Decimal",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "average",
        "barCount",
        "contrato",
        "localSymbol",
        "conId",
        "symbol",
        "fonte",
    ]

    for col in colunas:
        if col not in out.columns:
            out[col] = None

    return out[colunas].copy()


def main():
    print("=====================================================")
    print("REPARO MNQZ4 - NOVEMBRO 2024")
    print("=====================================================")

    ib = IB()
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=20)

    try:
        contrato = criar_contrato()
        todos = []

        end_dt = FIM

        while end_dt > INICIO:
            df = baixar_chunk(ib, contrato, end_dt)

            if not df.empty:
                dfp = padronizar(df)
                dfp = dfp[
                    (pd.to_datetime(dfp["DataHora_SP"]) >= INICIO)
                    & (pd.to_datetime(dfp["DataHora_SP"]) <= FIM)
                ].copy()

                if not dfp.empty:
                    print("Linhas:", len(dfp), "|", dfp["DataHora_SP"].min(), "->", dfp["DataHora_SP"].max())
                    todos.append(dfp)
                else:
                    print("Chunk fora do periodo.")
            else:
                print("Chunk vazio.")

            end_dt = end_dt - timedelta(days=2)
            time.sleep(2.5)

        if not todos:
            print("Nenhum dado de reparo baixado.")
            return

        reparo = pd.concat(todos, ignore_index=True)
        reparo = reparo.drop_duplicates(subset=["DataHora_SP"])
        reparo = reparo.sort_values("DataHora_SP").reset_index(drop=True)
        reparo.to_csv(ARQ_REPARO, index=False)

        print("\nReparo salvo:")
        print(ARQ_REPARO)
        print("Linhas reparo:", len(reparo))

        original = pd.read_csv(ARQ_CONTINUO)
        original["DataHora_SP"] = pd.to_datetime(original["DataHora_SP"], errors="coerce")
        reparo["DataHora_SP"] = pd.to_datetime(reparo["DataHora_SP"], errors="coerce")

        combinado = pd.concat([original, reparo], ignore_index=True)
        combinado = combinado.dropna(subset=["DataHora_SP"])
        combinado = combinado.drop_duplicates(subset=["DataHora_SP"])
        combinado = combinado.sort_values("DataHora_SP").reset_index(drop=True)

        combinado.to_csv(ARQ_CONTINUO_REPARADO, index=False)

        print("\nArquivo reparado salvo:")
        print(ARQ_CONTINUO_REPARADO)
        print("Linhas original:", len(original))
        print("Linhas reparado:", len(combinado))
        print("Primeira:", combinado["DataHora_SP"].min())
        print("Ultima:", combinado["DataHora_SP"].max())

    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Desconectado.")


if __name__ == "__main__":
    main()
