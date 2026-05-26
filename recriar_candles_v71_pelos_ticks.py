from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE / "operacional_v71_oficial"

ARQ_TICKS = PASTA / "blackarrow_ticks.csv"
ARQ_CANDLES = PASTA / "blackarrow_candles_2min.csv"

BACKUP = PASTA / f"blackarrow_candles_2min_BACKUP_recriar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

if ARQ_CANDLES.exists():
    shutil.copy2(ARQ_CANDLES, BACKUP)
    print("Backup criado:", BACKUP)

df = pd.read_csv(ARQ_TICKS, header=None)

# Estrutura do tick:
# 0 DataHora
# 1 Data
# 2 Hora decimal
# 3 Ultimo
# 4 Abertura
# 5 Maximo
# 6 Minimo
# 7 Negocios
# 8 Asset
# 9 Strike

df.columns = [
    "DataHora",
    "Data",
    "HoraDecimal",
    "Ultimo",
    "Abertura",
    "Maximo",
    "Minimo",
    "Negocios",
    "Asset",
    "Strike",
]

df["DataHora"] = pd.to_datetime(df["DataHora"], errors="coerce")
df = df.dropna(subset=["DataHora"]).copy()

for c in ["Ultimo", "Abertura", "Maximo", "Minimo", "Negocios", "Strike"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.sort_values("DataHora").copy()
df = df.set_index("DataHora")

candles = df.resample("2min").agg({
    "Ultimo": ["first", "max", "min", "last"],
    "Negocios": "last",
    "Asset": "last",
    "Strike": "last",
})

candles.columns = ["open", "high", "low", "close", "Negocios", "Asset", "Strike"]
candles = candles.dropna(subset=["open", "high", "low", "close"]).copy()
candles = candles.reset_index()

candles["DataHora2"] = candles["DataHora"]
candles["Data"] = candles["DataHora"].dt.strftime("%Y-%m-%d")
candles["HoraDecimal"] = candles["DataHora"].dt.hour + candles["DataHora"].dt.minute / 60.0
candles["preco_close"] = candles["close"]
candles["qtd_ticks"] = 1
candles["flag"] = 0
candles["qtd_ticks2"] = 1
candles["Asset2"] = candles["Asset"]

saida = candles[
    [
        "DataHora",
        "DataHora2",
        "Data",
        "HoraDecimal",
        "open",
        "high",
        "low",
        "close",
        "Negocios",
        "preco_close",
        "qtd_ticks",
        "flag",
        "qtd_ticks2",
        "Asset",
        "Asset2",
    ]
].copy()

saida.to_csv(ARQ_CANDLES, index=False, header=False)

print("Candles recriados com sucesso.")
print("Total candles:", len(saida))
print("Últimas linhas:")
print(saida.tail(10).to_string(index=False))
