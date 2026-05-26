from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE / "operacional_v71_oficial"

ARQ_CANDLES = PASTA / "blackarrow_candles_2min.csv"
BACKUP = PASTA / f"blackarrow_candles_2min_BACKUP_antes_corrigir_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

shutil.copy2(ARQ_CANDLES, BACKUP)
print("Backup criado:", BACKUP)

df = pd.read_csv(ARQ_CANDLES, header=None)

# Pelo seu arquivo:
# coluna 0 = DataHora
# coluna 1 = DataHora repetida
# coluna 2 = Data
# coluna 3 = Hora decimal
df[0] = pd.to_datetime(df[0], errors="coerce")
df[1] = pd.to_datetime(df[1], errors="coerce")

# Troca apenas a DATA para 2026-05-26 mantendo hora/minuto/segundo
nova_data = pd.Timestamp("2026-05-26")

df[0] = df[0].apply(lambda x: pd.Timestamp.combine(nova_data.date(), x.time()) if pd.notna(x) else x)
df[1] = df[1].apply(lambda x: pd.Timestamp.combine(nova_data.date(), x.time()) if pd.notna(x) else x)
df[2] = "2026-05-26"

df.to_csv(ARQ_CANDLES, index=False, header=False)

print("Datas dos candles corrigidas para 2026-05-26.")
print("Últimas linhas agora:")
print(pd.read_csv(ARQ_CANDLES, header=None).tail(5).to_string(index=False))
