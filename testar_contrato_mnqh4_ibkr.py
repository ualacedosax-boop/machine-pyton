from ib_insync import *
import sys

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 77

ib = IB()

try:
    print("Conectando...")
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=10)
    print("Conectado.")

    testes = [
        ("MNQH4 CME localSymbol", Future(symbol="MNQ", exchange="CME", currency="USD", localSymbol="MNQH4", includeExpired=True)),
        ("MNQH4 GLOBEX localSymbol", Future(symbol="MNQ", exchange="GLOBEX", currency="USD", localSymbol="MNQH4", includeExpired=True)),
        ("MNQ 202403 CME", Future(symbol="MNQ", lastTradeDateOrContractMonth="202403", exchange="CME", currency="USD", includeExpired=True)),
        ("MNQ 202403 GLOBEX", Future(symbol="MNQ", lastTradeDateOrContractMonth="202403", exchange="GLOBEX", currency="USD", includeExpired=True)),
        ("MNQ 20240315 CME", Future(symbol="MNQ", lastTradeDateOrContractMonth="20240315", exchange="CME", currency="USD", includeExpired=True)),
        ("MNQ 20240315 GLOBEX", Future(symbol="MNQ", lastTradeDateOrContractMonth="20240315", exchange="GLOBEX", currency="USD", includeExpired=True)),
    ]

    for nome, contrato in testes:
        print("\n=====================================================")
        print("TESTE:", nome)
        print("Contrato:", contrato)
        try:
            detalhes = ib.reqContractDetails(contrato)
            print("Qtd detalhes:", len(detalhes))

            for d in detalhes[:5]:
                c = d.contract
                print("OK:")
                print("  conId:", c.conId)
                print("  symbol:", c.symbol)
                print("  localSymbol:", c.localSymbol)
                print("  tradingClass:", c.tradingClass)
                print("  exchange:", c.exchange)
                print("  lastTradeDate:", c.lastTradeDateOrContractMonth)
                print("  multiplier:", c.multiplier)
        except Exception as e:
            print("ERRO:", e)

finally:
    if ib.isConnected():
        print("\nDesconectando...")
        ib.disconnect()
        print("Desconectado.")
