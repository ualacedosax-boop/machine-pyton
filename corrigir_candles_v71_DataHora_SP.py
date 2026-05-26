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

BACKUP_TICKS = PASTA / f"blackarrow_ticks_BACKUP_corrigir_DataHora_SP_{DATA_BACKUP}.csv"
BACKUP_CANDLES = PASTA / f"blackarrow_candles_2min_BACKUP_corrigir_DataHora_SP_{DATA_BACKUP}.csv"

if ARQ_TICKS.exists():
    shutil.copy2(ARQ_TICKS, BACKUP_TICKS)

if ARQ_CANDLES.exists():
    shutil.copy2(ARQ_CANDLES, BACKUP_CANDLES)

print("Backup ticks  :", BACKUP_TICKS)
print("Backup candles:", BACKUP_CANDLES)

# =====================================================
# 1. LER RTD ATUAL
# =====================================================

rtd = None
for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
    try:
        rtd = pd.read_csv(ARQ_RTD, sep=";", encoding=enc)
        break
    except Exception:
        pass

if rtd is None or rtd.empty:
    raise RuntimeError("Não consegui ler blackarrow_rtd.csv")

linha = rtd.iloc[-1]

data_rtd = str(linha["Data"]).strip()
hora_rtd = str(linha["Hora"]).strip()

dt_rtd = pd.to_datetime(data_rtd + " " + hora_rtd, dayfirst=True, errors="coerce")

if pd.isna(dt_rtd):
    raise RuntimeError(f"Não consegui interpretar Data/Hora do RTD: {data_rtd} {hora_rtd}")

data_operacional = dt_rtd.date()
limite = dt_rtd + pd.Timedelta(minutes=10)

print()
print("RTD atual:")
print("Data/Hora RTD :", dt_rtd)
print("Data usada    :", data_operacional)
print("Limite usado  :", limite)

# =====================================================
# 2. LER TICKS E REMOVER DATA FUTURA
# =====================================================

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

# Mantém somente ticks da mesma data operacional do RTD
# e remove qualquer coisa futura.
ticks = ticks[
    (ticks["DataHora_SP"].dt.date == data_operacional) &
    (ticks["DataHora_SP"] <= limite)
].copy()

depois = len(ticks)

print()
print("Limpeza dos ticks:")
print("Ticks antes :", antes)
print("Ticks depois:", depois)
print("Removidos   :", antes - depois)

if ticks.empty:
    raise RuntimeError("Depois da limpeza não sobrou tick. Verifique blackarrow_rtd.csv e blackarrow_ticks.csv.")

ticks = ticks.sort_values("DataHora_SP").copy()

for c in ["Ultimo", "Abertura", "Maximo", "Minimo", "Negocios", "Strike"]:
    ticks[c] = pd.to_numeric(ticks[c], errors="coerce")

ticks.to_csv(ARQ_TICKS, index=False, header=False)

print()
print("Últimos ticks limpos:")
print(ticks.tail(10).to_string(index=False))

# =====================================================
# 3. RECRIAR CANDLES 2 MIN COM CABEÇALHO CORRETO
# =====================================================

df = ticks.set_index("DataHora_SP").sort_index()

candles = df.resample("2min").agg({
    "Ultimo": ["first", "max", "min", "last"],
    "Negocios": "last",
    "Asset": "last",
    "Strike": "last",
})

candles.columns = ["open", "high", "low", "close", "Negocios", "Asset", "Strike"]
candles = candles.dropna(subset=["open", "high", "low", "close"]).copy()
candles = candles.reset_index()

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

# Agora salva COM cabeçalho, porque o robô precisa da coluna DataHora_SP
saida.to_csv(ARQ_CANDLES, index=False, header=True)

print()
print("Candles recriados com cabeçalho correto.")
print("Total candles:", len(saida))
print()
print("Colunas:")
print(list(saida.columns))
print()
print("Últimos candles:")
print(saida.tail(15).to_string(index=False))

print()
print("CONCLUÍDO.")
print("Agora rode o robô V7.1 novamente.")
