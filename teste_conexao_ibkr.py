from ib_insync import *
import pandas as pd

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 90

ib = IB()

try:
    ib.connect(HOST, PORT, clientId=CLIENT_ID, readonly=True)
    print("Conectado:", ib.isConnected())

    ib.reqMarketDataType(4)

    contract = Future(
        conId=672387468,
        symbol="MNQ",
        lastTradeDateOrContractMonth="20250321",
        exchange="CME",
        currency="USD",
        localSymbol="MNQH5",
        tradingClass="MNQ",
        includeExpired=True
    )

    print("Contrato usado:")
    print(contract)

    bars = ib.reqHistoricalData(
        contract,
        endDateTime="20250102-15:00:00",
        durationStr="3600 S",
        barSizeSetting="1 min",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
        keepUpToDate=False,
        timeout=180
    )

    print("Candles recebidos:", len(bars))

    if bars:
        df = util.df(bars)
        print(df.head())
        print(df.tail())

        df.to_csv("MNQH5_TESTE_2025_01_02_1H_1MIN.csv", index=False, encoding="utf-8-sig")
        print("Arquivo salvo: MNQH5_TESTE_2025_01_02_1H_1MIN.csv")
    else:
        print("Não retornou candles.")

finally:
    if ib.isConnected():
        ib.disconnect()
        print("Desconectado.")