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

BACKUP_TICKS = PASTA / f"blackarrow_ticks_BACKUP_antes_limpar_futuro_{DATA_BACKUP}.csv"
BACKUP_CANDLES = PASTA / f"blackarrow_candles_2min_BACKUP_antes_limpar_futuro_{DATA_BACKUP}.csv"

shutil.copy2(ARQ_TICKS, BACKUP_TICKS)
shutil.copy2(ARQ_CANDLES, BACKUP_CANDLES)

print("Backup ticks  :", BACKUP_TICKS)
print("Backup candles:", BACKUP_CANDLES)

# =====================================================
# 1. LER RTD ATUAL COMO REFERÊNCIA
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

# margem para não apagar tick que chegou alguns segundos/minutos depois
limite = dt_rtd + pd.Timedelta(minutes=10)

print()
print("RTD atual:")
print("Data/Hora RTD :", dt_rtd)
print("Limite usado  :", limite)

# =====================================================
# 2. LER TICKS E REMOVER TICKS FUTUROS
# =====================================================

ticks = pd.read_csv(ARQ_TICKS, header=None)

ticks.columns = [
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

ticks["DataHora"] = pd.to_datetime(ticks["DataHora"], errors="coerce")
ticks = ticks.dropna(subset=["DataHora"]).copy()

antes = len(ticks)

ticks_limpo = ticks[ticks["DataHora"] <= limite].copy()
depois = len(ticks_limpo)

removidos = antes - depois

print()
print("Limpeza dos ticks:")
print("Ticks antes   :", antes)
print("Ticks depois  :", depois)
print("Removidos     :", removidos)

if ticks_limpo.empty:
    raise RuntimeError("Depois da limpeza, não sobrou nenhum tick. Abortando.")

ticks_limpo = ticks_limpo.sort_values("DataHora").copy()

# Salva ticks limpos
ticks_limpo.to_csv(ARQ_TICKS, index=False, header=False)

print()
print("Últimos ticks limpos:")
print(ticks_limpo.tail(10).to_string(index=False))

# =====================================================
# 3. RECRIAR CANDLES DE 2 MINUTOS
# =====================================================

for c in ["Ultimo", "Abertura", "Maximo", "Minimo", "Negocios", "Strike"]:
    ticks_limpo[c] = pd.to_numeric(ticks_limpo[c], errors="coerce")

df = ticks_limpo.set_index("DataHora").sort_index()

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

print()
print("Candles recriados com sucesso.")
print("Total candles:", len(saida))
print()
print("Últimos candles recriados:")
print(saida.tail(15).to_string(index=False))

print()
print("CONCLUÍDO.")
print("Agora rode o robô V7.1 novamente.")
