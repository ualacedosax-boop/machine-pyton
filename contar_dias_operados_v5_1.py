import pandas as pd
from pathlib import Path

ARQ = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\saida_v5_1_feature_select_threshold_fino\03_predicoes_melhor_v5_1_2026.csv.gz")

df = pd.read_csv(ARQ, compression="gzip")

print("Colunas:")
print(df.columns.tolist())

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")

# Aceitos pela V5.1
aceitos = df[df["aceito_v5_1"].astype(str).str.lower().isin(["true", "1", "sim", "yes"])].copy()

aceitos["DataDia"] = aceitos["DataHora_SP"].dt.strftime("%Y-%m-%d")

dias = aceitos.groupby("DataDia").size().reset_index(name="trades_no_dia")

print("\n==============================================")
print("RESUMO DIAS OPERADOS V5.1")
print("==============================================")
print("Total trades V5.1:", len(aceitos))
print("Dias com entrada:", dias["DataDia"].nunique())
print("Maior quantidade de trades em um dia:", dias["trades_no_dia"].max() if len(dias) else 0)

print("\nDistribuicao de trades por dia:")
print(dias["trades_no_dia"].value_counts().sort_index().to_string())

print("\nLista de dias operados:")
print(dias.to_string(index=False))

saida = ARQ.parent / "06_dias_operados_v5_1_2026.csv"
dias.to_csv(saida, index=False)
print("\nArquivo salvo:", saida)
