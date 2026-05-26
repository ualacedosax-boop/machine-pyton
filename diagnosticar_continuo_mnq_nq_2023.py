# -*- coding: utf-8 -*-

from ib_insync import *
from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE_DIR / "dados_mnq_2023_ibkr"
PASTA.mkdir(parents=True, exist_ok=True)

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=85, timeout=15)

testes = [
    ("MNQ_CONT_CME", ContFuture(symbol="MNQ", exchange="CME", currency="USD")),
    ("NQ_CONT_CME", ContFuture(symbol="NQ", exchange="CME", currency="USD")),
]

for nome, contrato in testes:
    print("\n=====================================================")
    print("TESTE:", nome)
    print("Contrato:", contrato)

    try:
        detalhes = ib.reqContractDetails(contrato)
    except Exception as e:
        print("Erro detalhes:", e)
        detalhes = []

    print("Qtd detalhes:", len(detalhes))

    for d in detalhes:
        ct = d.contract
        print(
            f"conId={ct.conId} | "
            f"symbol={ct.symbol} | "
            f"localSymbol={ct.localSymbol} | "
            f"tradingClass={ct.tradingClass} | "
            f"exchange={ct.exchange} | "
            f"lastTradeDate={ct.lastTradeDateOrContractMonth} | "
            f"multiplier={ct.multiplier}"
        )

    if detalhes:
        ct = detalhes[0].contract

        print("\nTentando baixar amostra 2023...")
        try:
            bars = ib.reqHistoricalData(
                ct,
                endDateTime="20231229-22:00:00",
                durationStr="5 D",
                barSizeSetting="2 mins",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
                keepUpToDate=False,
            )

            df = util.df(bars)

            if df is None or df.empty:
                print("Amostra vazia.")
            else:
                print("Amostra baixada:", len(df), "linhas")
                print(df.head().to_string(index=False))
                print(df.tail().to_string(index=False))

                arq = PASTA / f"AMOSTRA_{nome}_2023_CONT.csv"
                df.to_csv(arq, index=False, encoding="utf-8-sig")
                print("Salvo:", arq)

        except Exception as e:
            print("Erro histórico:", e)

ib.disconnect()
print("\nFinalizado.")
