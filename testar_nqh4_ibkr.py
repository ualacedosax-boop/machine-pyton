from ib_insync import *

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=79, timeout=10)

testes = [
    Future(symbol="NQ", exchange="CME", currency="USD", localSymbol="NQH4", includeExpired=True),
    Future(symbol="NQ", lastTradeDateOrContractMonth="202403", exchange="CME", currency="USD", includeExpired=True),
    Future(symbol="NQ", lastTradeDateOrContractMonth="20240315", exchange="CME", currency="USD", includeExpired=True),
]

for c in testes:
    print("\nContrato:", c)
    detalhes = ib.reqContractDetails(c)
    print("Qtd:", len(detalhes))
    for d in detalhes:
        ct = d.contract
        print(ct.conId, ct.localSymbol, ct.lastTradeDateOrContractMonth, ct.exchange, ct.multiplier)

ib.disconnect()
