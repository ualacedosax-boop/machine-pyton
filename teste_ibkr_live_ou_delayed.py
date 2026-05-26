from ib_insync import *
from datetime import datetime
import time

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 33

def main():
    ib = IB()

    print("Conectando...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=15)
    print("Conectado:", ib.isConnected())

    contrato = Future(symbol="MNQ", exchange="CME", currency="USD")

    detalhes = ib.reqContractDetails(contrato)
    if not detalhes:
        print("Nenhum contrato MNQ encontrado.")
        ib.disconnect()
        return

    contrato = detalhes[0].contract

    print("Contrato:", contrato.localSymbol, contrato.conId)

    print("\nForçando market data LIVE tipo 1...")
    ib.reqMarketDataType(1)

    ticker = ib.reqMktData(contrato, "", False, False)

    for i in range(20):
        ib.sleep(1)

        print(
            datetime.now().strftime("%H:%M:%S"),
            "| last:", ticker.last,
            "| bid:", ticker.bid,
            "| ask:", ticker.ask,
            "| marketDataType:", ticker.marketDataType
        )

    ib.cancelMktData(contrato)
    ib.disconnect()

if __name__ == "__main__":
    main()