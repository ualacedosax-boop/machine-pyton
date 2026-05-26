import pandas as pd
from pathlib import Path

ARQ = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\dados_mnq_2024_ibkr\MNQ_2024_2MIN_IBKR_CONTINUO.csv")

df = pd.read_csv(ARQ)
df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

df["diff_min"] = df["DataHora_SP"].diff().dt.total_seconds() / 60

buracos = df[df["diff_min"] > 10].copy()

print("=====================================================")
print("CHECAGEM MNQ 2024")
print("=====================================================")
print("Arquivo:", ARQ)
print("Linhas:", len(df))
print("Primeira data:", df["DataHora_SP"].min())
print("Ultima data:", df["DataHora_SP"].max())
print("Duplicados DataHora_SP:", df["DataHora_SP"].duplicated().sum())
print("Buracos maiores que 10 minutos:", len(buracos))

if len(buracos):
    print("\nMaiores buracos:")
    cols = ["DataHora_SP", "diff_min", "contrato", "localSymbol"]
    print(buracos.sort_values("diff_min", ascending=False)[cols].head(30).to_string(index=False))

    saida = ARQ.parent / "CHECAGEM_BURACOS_MNQ_2024.csv"
    buracos.to_csv(saida, index=False)
    print("\nArquivo salvo:", saida)
