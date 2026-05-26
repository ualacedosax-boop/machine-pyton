from ib_insync import *
import pandas as pd

HOST = "127.0.0.1"
PORT = 7497       # Simulated/Paper Trading
CLIENT_ID = 10

SIMBOLO = "MNQ"
EXCHANGE = "CME"
CURRENCY = "USD"


def main():
    print("Conectando ao TWS/IBKR...")

    ib = IB()

    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=15)
    except Exception as e:
        print("Erro ao conectar no TWS:")
        print(e)
        return

    print("Conectado:", ib.isConnected())

    print("\nBuscando contratos MNQ...")

    contrato = Future(
        symbol=SIMBOLO,
        exchange=EXCHANGE,
        currency=CURRENCY
    )

    contratos = ib.reqContractDetails(contrato)

    if not contratos:
        print("Nenhum contrato encontrado para MNQ.")
        print("Vamos precisar informar o vencimento manualmente, exemplo: 202506, 202509, 202512.")
        ib.disconnect()
        return

    print(f"Contratos encontrados: {len(contratos)}")

    for i, cd in enumerate(contratos[:10]):
        c = cd.contract
        print(
            i,
            "symbol:", c.symbol,
            "localSymbol:", c.localSymbol,
            "lastTradeDate:", c.lastTradeDateOrContractMonth,
            "exchange:", c.exchange,
            "conId:", c.conId
        )

    contrato_qualificado = contratos[0].contract

    print("\nContrato escolhido:")
    print(contrato_qualificado)

    print("\nBaixando candles recentes de 2 minutos...")

    try:
        bars = ib.reqHistoricalData(
            contrato_qualificado,
            endDateTime="",
            durationStr="2 D",
            barSizeSetting="2 mins",
            whatToShow="TRADES",
            useRTH=False,
            formatDate=1,
            keepUpToDate=False
        )
    except Exception as e:
        print("Erro ao baixar histórico:")
        print(e)
        ib.disconnect()
        return

    if not bars:
        print("Nenhum candle retornado.")
        ib.disconnect()
        return

    df = util.df(bars)

    print("\nÚltimos candles:")
    print(df.tail(20))

    caminho_saida = "teste_ibkr_mnq_2min.csv"
    df.to_csv(caminho_saida, index=False, encoding="utf-8-sig")

    print("\nArquivo salvo:")
    print(caminho_saida)

    ib.disconnect()
    print("\nDesconectado.")


if __name__ == "__main__":
    main()