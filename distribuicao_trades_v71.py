from pathlib import Path
import pandas as pd

ARQ = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\operacional_v71_oficial\trades_base_v71_oficial_2026.csv.gz")

df = pd.read_csv(ARQ, compression="gzip")

# tenta achar coluna de data/hora
col_dt = None
for c in ["DataHora_SP", "DataHora_Sinal_SP", "dt_entrada", "DataHora"]:
    if c in df.columns:
        col_dt = c
        break

if col_dt is None:
    raise RuntimeError("Não achei coluna de data/hora.")

df["dt"] = pd.to_datetime(df[col_dt], errors="coerce")
df["Data"] = df["dt"].dt.date
df["Hora"] = df["dt"].dt.hour
df["Minuto"] = df["dt"].dt.minute
df["Bloco_15m"] = df["dt"].dt.strftime("%H:") + ((df["dt"].dt.minute // 15) * 15).astype(str).str.zfill(2)

print("="*80)
print("FREQUENCIA GERAL V7.1")
print("="*80)
print("Trades:", len(df))
print("Dias com trade:", df["Data"].nunique())
print("Média trades por dia operado:", len(df) / df["Data"].nunique())

print()
print("="*80)
print("DISTRIBUIÇÃO POR HORA")
print("="*80)
print(df.groupby("Hora").size().reset_index(name="trades").to_string(index=False))

print()
print("="*80)
print("DISTRIBUIÇÃO POR BLOCO 15 MIN")
print("="*80)
print(df.groupby("Bloco_15m").size().reset_index(name="trades").to_string(index=False))

print()
print("="*80)
print("DISTRIBUIÇÃO POR MINUTO")
print("="*80)
print(df.groupby(["Hora","Minuto"]).size().reset_index(name="trades").to_string(index=False))

if "Direcao" in df.columns:
    print()
    print("="*80)
    print("DISTRIBUIÇÃO POR DIREÇÃO")
    print("="*80)
    print(df.groupby("Direcao").size().reset_index(name="trades").to_string(index=False))

    print()
    print("="*80)
    print("HORA X DIREÇÃO")
    print("="*80)
    print(df.groupby(["Hora","Direcao"]).size().reset_index(name="trades").to_string(index=False))
