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

# =====================================================
# 1. DESCOBRIR DATA ATUAL DO RTD
# =====================================================

rtd = pd.read_csv(ARQ_RTD, sep=";", encoding="utf-8-sig")
linha = rtd.iloc[-1]

data_rtd = str(linha["Data"]).strip()
hora_rtd = str(linha["Hora"]).strip()

dt_rtd = pd.to_datetime(data_rtd + " " + hora_rtd, dayfirst=True, errors="coerce")

if pd.isna(dt_rtd):
    raise RuntimeError(f"Não consegui interpretar RTD: {data_rtd} {hora_rtd}")

data_correta = dt_rtd.date()

print("=" * 100)
print("RTD ATUAL")
print("=" * 100)
print("Data/Hora RTD :", dt_rtd)
print("Data correta  :", data_correta)

# =====================================================
# 2. ACHAR BACKUP DE TICKS COM MAIS LINHAS
# =====================================================

backups_ticks = sorted(PASTA.glob("blackarrow_ticks_BACKUP*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

if not backups_ticks:
    raise RuntimeError("Não encontrei backup de blackarrow_ticks.")

melhor_backup = None
melhor_linhas = 0

for arq in backups_ticks:
    try:
        n = sum(1 for _ in open(arq, "r", encoding="utf-8", errors="ignore"))
        if n > melhor_linhas:
            melhor_linhas = n
            melhor_backup = arq
    except Exception:
        pass

if melhor_backup is None:
    raise RuntimeError("Não consegui escolher backup de ticks.")

print()
print("=" * 100)
print("BACKUP ESCOLHIDO")
print("=" * 100)
print("Arquivo:", melhor_backup)
print("Linhas :", melhor_linhas)

# Backup do estado atual antes de sobrescrever
shutil.copy2(ARQ_TICKS, PASTA / f"blackarrow_ticks_BACKUP_estado_atual_antes_normalizar_{DATA_BACKUP}.csv")
shutil.copy2(ARQ_CANDLES, PASTA / f"blackarrow_candles_BACKUP_estado_atual_antes_normalizar_{DATA_BACKUP}.csv")

# Restaura ticks do backup maior
shutil.copy2(melhor_backup, ARQ_TICKS)

# =====================================================
# 3. LER TICKS RESTAURADOS E NORMALIZAR DATA FUTURA
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

# Corrige qualquer tick com data diferente da data do RTD,
# mantendo a hora/minuto/segundo original.
def ajustar_data(dt):
    if pd.isna(dt):
        return dt
    return pd.Timestamp.combine(data_correta, dt.time())

ticks["DataHora_SP"] = ticks["DataHora_SP"].apply(ajustar_data)
ticks["Data"] = str(data_correta)

# Recalcula hora decimal
ticks["Hora_SP_Decimal"] = (
    ticks["DataHora_SP"].dt.hour
    + ticks["DataHora_SP"].dt.minute / 60.0
    + ticks["DataHora_SP"].dt.second / 3600.0
)

# Remove duplicados de tempo/preço se houver
ticks = ticks.sort_values("DataHora_SP").drop_duplicates(subset=["DataHora_SP", "Ultimo"], keep="last").copy()

for c in ["Ultimo", "Abertura", "Maximo", "Minimo", "Negocios", "Strike"]:
    ticks[c] = pd.to_numeric(ticks[c], errors="coerce")

depois = len(ticks)

ticks.to_csv(ARQ_TICKS, index=False, header=False)

print()
print("=" * 100)
print("TICKS NORMALIZADOS")
print("=" * 100)
print("Ticks antes :", antes)
print("Ticks depois:", depois)
print()
print("Últimos ticks:")
print(ticks.tail(10).to_string(index=False))

# =====================================================
# 4. RECRIAR CANDLES 2 MIN COM CABEÇALHO CORRETO
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

saida.to_csv(ARQ_CANDLES, index=False, header=True)

print()
print("=" * 100)
print("CANDLES RECRIADOS")
print("=" * 100)
print("Total candles:", len(saida))
print()
print("Últimos candles:")
print(saida.tail(15).to_string(index=False))

print()
if len(saida) >= 220:
    print("OK: quantidade de candles suficiente para o robô.")
else:
    print("ATENÇÃO: ainda tem poucos candles. O robô pode acusar candles_insuficientes.")

print()
print("CONCLUÍDO. Agora rode o robô V7.1.")
