# -*- coding: utf-8 -*-

from ib_insync import *
from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE_DIR / "dados_mnq_2023_ibkr"
PASTA.mkdir(parents=True, exist_ok=True)

ARQ = PASTA / "DIAGNOSTICO_CONTRATOS_MNQ_NQ_2023.csv"

ib = IB()
ib.connect("127.0.0.1", 7497, clientId=84, timeout=15)

linhas = []

testes = [
    ("MNQ_CME_VAZIO", Future(symbol="MNQ", exchange="CME", currency="USD", includeExpired=True)),
    ("MNQ_GLOBEX_VAZIO", Future(symbol="MNQ", exchange="GLOBEX", currency="USD", includeExpired=True)),
    ("NQ_CME_VAZIO", Future(symbol="NQ", exchange="CME", currency="USD", includeExpired=True)),
    ("NQ_GLOBEX_VAZIO", Future(symbol="NQ", exchange="GLOBEX", currency="USD", includeExpired=True)),
]

for nome, contrato in testes:
    print("\n=====================================================")
    print("TESTE:", nome)
    print("Contrato:", contrato)

    try:
        detalhes = ib.reqContractDetails(contrato)
    except Exception as e:
        print("Erro:", e)
        detalhes = []

    print("Qtd detalhes:", len(detalhes))

    for d in detalhes:
        ct = d.contract

        linha = {
            "teste": nome,
            "conId": ct.conId,
            "symbol": ct.symbol,
            "localSymbol": ct.localSymbol,
            "tradingClass": ct.tradingClass,
            "exchange": ct.exchange,
            "lastTradeDateOrContractMonth": ct.lastTradeDateOrContractMonth,
            "multiplier": ct.multiplier,
            "currency": ct.currency,
        }

        linhas.append(linha)

        print(
            f"conId: {ct.conId} | "
            f"symbol: {ct.symbol} | "
            f"localSymbol: {ct.localSymbol} | "
            f"tradingClass: {ct.tradingClass} | "
            f"exchange: {ct.exchange} | "
            f"lastTradeDate: {ct.lastTradeDateOrContractMonth} | "
            f"multiplier: {ct.multiplier}"
        )

ib.disconnect()

df = pd.DataFrame(linhas)
df.to_csv(ARQ, index=False, encoding="utf-8-sig")

print("\nArquivo salvo:")
print(ARQ)

if not df.empty:
    print("\nFiltrando possíveis 2023:")
    f = df[
        df["localSymbol"].astype(str).str.contains("H3|M3|U3|Z3", regex=True, na=False)
        | df["lastTradeDateOrContractMonth"].astype(str).str.startswith("2023", na=False)
    ]
    print(f.to_string(index=False))
