from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE / "operacional_v71_oficial"

ARQ_RTD = BASE / "blackarrow_rtd.csv"
ARQ_TICKS = PASTA / "blackarrow_ticks.csv"
ARQ_CANDLES = PASTA / "blackarrow_candles_2min.csv"

DATA_BACKUP = datetime.now().strftime("%Y%m%d_%H%M%S")


def ler_rtd(caminho):
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(caminho, sep=";", encoding=enc)
        except Exception:
            pass
    raise RuntimeError("Não consegui ler blackarrow_rtd.csv")


print("=" * 100)
print("CORTAR CANDLES FUTUROS E RECRIAR V7.1")
print("=" * 100)

rtd = ler_rtd(ARQ_RTD)
linha = rtd.iloc[-1]

dt_rtd = pd.to_datetime(
    str(linha["Data"]).strip() + " " + str(linha["Hora"]).strip(),
    dayfirst=True,
    errors="coerce"
)

if pd.isna(dt_rtd):
    raise RuntimeError("Não consegui interpretar Data/Hora do RTD.")

print("RTD atual:", dt_rtd)

shutil.copy2(ARQ_TICKS, PASTA / f"blackarrow_ticks_BACKUP_antes_cortar_futuro_{DATA_BACKUP}.csv")
shutil.copy2(ARQ_CANDLES, PASTA / f"blackarrow_candles_BACKUP_antes_cortar_futuro_{DATA_BACKUP}.csv")

ticks = pd.read_csv(ARQ_TICKS, header=None)

ticks.columns = [
    "DataHora_SP",
    "Data",
    "Hora_SP_Decimal",
    "Ultimo",
    "Abertura",
    "Maximo",
    "Minimo",
    "Negocios",
    "Asset",
    "Strike",
]

ticks["DataHora_SP"] = pd.to_datetime(ticks["DataHora_SP"], errors="coerce")
ticks = ticks.dropna(subset=["DataHora_SP"]).copy()

antes = len(ticks)

# Remove qualquer tick depois do horário real do RTD
ticks = ticks[ticks["DataHora_SP"] <= dt_rtd].copy()

depois = len(ticks)

for c in ["Ultimo", "Abertura", "Maximo", "Minimo", "Negocios", "Strike"]:
    ticks[c] = pd.to_numeric(ticks[c], errors="coerce")

ticks = ticks.sort_values("DataHora_SP").drop_duplicates(
    subset=["DataHora_SP", "Ultimo"],
    keep="last"
).copy()

ticks["Data"] = ticks["DataHora_SP"].dt.strftime("%Y-%m-%d")
ticks["Hora_SP_Decimal"] = (
    ticks["DataHora_SP"].dt.hour
    + ticks["DataHora_SP"].dt.minute / 60.0
    + ticks["DataHora_SP"].dt.second / 3600.0
)

ticks.to_csv(ARQ_TICKS, index=False, header=False)

print()
print("Ticks antes :", antes)
print("Ticks depois:", depois)
print("Removidos   :", antes - depois)
print()
print("Últimos ticks após corte:")
print(ticks.tail(10).to_string(index=False))

df = ticks.set_index("DataHora_SP").sort_index()

candles = df.resample("2min").agg({
    "Ultimo": ["first", "max", "min", "last"],
    "Negocios": "last",
    "Asset": "last",
    "Strike": "last",
})

candles.columns = ["open", "high", "low", "close", "Negocios", "Asset", "Strike"]
candles = candles.dropna(subset=["open", "high", "low", "close"]).reset_index()

candles["DataHora"] = candles["DataHora_SP"]
candles["Data"] = candles["DataHora_SP"].dt.strftime("%Y-%m-%d")
candles["Hora_SP_Decimal"] = candles["DataHora_SP"].dt.hour + candles["DataHora_SP"].dt.minute / 60.0
candles["preco_close"] = candles["close"]
candles["qtd_ticks"] = 1
candles["flag"] = 0
candles["qtd_ticks2"] = 1
candles["Asset2"] = candles["Asset"]

saida = candles[
    [
        "DataHora_SP",
        "DataHora",
        "Data",
        "Hora_SP_Decimal",
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

saida.to_csv(ARQ_CANDLES, index=False, header=True)

print()
print("=" * 100)
print("CANDLES RECRIADOS SEM FUTURO")
print("=" * 100)
print("Total candles:", len(saida))
print()
print("Últimos candles:")
print(saida.tail(15).to_string(index=False))

if len(saida) >= 220:
    print()
    print("OK: candles suficientes.")
else:
    print()
    print("ATENÇÃO: poucos candles.")

print()
print("Agora pode rodar o robô V7.1.")
