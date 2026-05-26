# -*- coding: utf-8 -*-

from ib_insync import *
from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE_DIR / "dados_mnq_2023_ibkr"
PASTA.mkdir(parents=True, exist_ok=True)

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=86, timeout=15)

testes = [
    ("MNQ_CONT_CME", ContFuture(symbol="MNQ", exchange="CME", currency="USD")),
    ("NQ_CONT_CME", ContFuture(symbol="NQ", exchange="CME", currency="USD")),
]

duracoes = [
    "1 W",
    "1 M",
    "3 M",
    "6 M",
    "1 Y",
    "2 Y",
    "3 Y",
]

for nome, contrato in testes:
    print("\n=====================================================")
    print("TESTE:", nome)
    print("Contrato:", contrato)

    detalhes = ib.reqContractDetails(contrato)
    print("Qtd detalhes:", len(detalhes))

    if not detalhes:
        continue

    ct = detalhes[0].contract

    print(
        f"conId={ct.conId} | "
        f"symbol={ct.symbol} | "
        f"localSymbol={ct.localSymbol} | "
        f"tradingClass={ct.tradingClass} | "
        f"exchange={ct.exchange} | "
        f"lastTradeDate={ct.lastTradeDateOrContractMonth} | "
        f"multiplier={ct.multiplier}"
    )

    for dur in duracoes:
        print("\n---------------------------------------------")
        print(f"Tentando durationStr={dur}, endDateTime vazio")

        try:
            bars = ib.reqHistoricalData(
                ct,
                endDateTime="",
                durationStr=dur,
                barSizeSetting="2 mins",
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
                keepUpToDate=False,
            )

            df = util.df(bars)

            if df is None or df.empty:
                print("Vazio.")
                continue

            print("Linhas:", len(df))
            print("Primeira:", df["date"].min())
            print("Ultima  :", df["date"].max())

            arq = PASTA / f"AMOSTRA_{nome}_{dur.replace(' ', '')}_CONT.csv"
            df.to_csv(arq, index=False, encoding="utf-8-sig")
            print("Salvo:", arq)

        except Exception as e:
            print("Erro:", e)

ib.disconnect()
print("\nFinalizado.")
