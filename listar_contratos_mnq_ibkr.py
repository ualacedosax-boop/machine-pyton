from ib_insync import *

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 78

ib = IB()

try:
    print("Conectando...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=10)
    print("Conectado.")

    testes = [
        ("MNQ CME vazio", Future(symbol="MNQ", exchange="CME", currency="USD", includeExpired=True)),
        ("MNQ GLOBEX vazio", Future(symbol="MNQ", exchange="GLOBEX", currency="USD", includeExpired=True)),
        ("NQ CME vazio", Future(symbol="NQ", exchange="CME", currency="USD", includeExpired=True)),
        ("NQ GLOBEX vazio", Future(symbol="NQ", exchange="GLOBEX", currency="USD", includeExpired=True)),
    ]

    for nome, contrato in testes:
        print("\n=====================================================")
        print("TESTE:", nome)
        print("Contrato:", contrato)

        detalhes = ib.reqContractDetails(contrato)
        print("Qtd detalhes:", len(detalhes))

        for d in detalhes[:30]:
            c = d.contract
            print(
                "conId:", c.conId,
                "| symbol:", c.symbol,
                "| localSymbol:", c.localSymbol,
                "| tradingClass:", c.tradingClass,
                "| exchange:", c.exchange,
                "| lastTradeDate:", c.lastTradeDateOrContractMonth,
                "| multiplier:", c.multiplier
            )

finally:
    if ib.isConnected():
        print("\nDesconectando...")
        ib.disconnect()
        print("Desconectado.")
