import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ = BASE / "saida_v5_5_sem_vazamento_rotacoes_teste_2026" / "06_predicoes_teste_2026_v5_5.csv.gz"
SAIDA_DIAS = BASE / "saida_v5_5_sem_vazamento_rotacoes_teste_2026" / "09_distribuicao_trades_por_dia_v5_5.csv"
SAIDA_RESUMO = BASE / "saida_v5_5_sem_vazamento_rotacoes_teste_2026" / "10_resumo_distribuicao_dias_v5_5.csv"

df = pd.read_csv(ARQ, compression="gzip")

df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
df = df.dropna(subset=["DataHora_SP"]).copy()

if "aceito_v5_5" not in df.columns:
    raise RuntimeError("Não encontrei a coluna aceito_v5_5 no arquivo.")

aceitos = df[df["aceito_v5_5"].astype(str).str.lower().isin(["true", "1", "sim", "yes"])].copy()

aceitos["DataDia"] = aceitos["DataHora_SP"].dt.strftime("%Y-%m-%d")

# Resultado por dia
dias = aceitos.groupby("DataDia").agg(
    trades_no_dia=("DataDia", "size"),
    wins=("target_v5_win", lambda x: int((x == 1).sum())),
    losses=("target_v5_win", lambda x: int((x == 0).sum())),
    lucro_pontos=("pontos_v5", "sum"),
).reset_index()

dias["winrate"] = dias["wins"] / dias["trades_no_dia"] * 100
dias["lucro_acumulado"] = dias["lucro_pontos"].cumsum()

# Distribuição: quantos dias tiveram 1, 2, 3... trades
dist = dias["trades_no_dia"].value_counts().sort_index().reset_index()
dist.columns = ["trades_no_dia", "quantidade_dias"]

print("=====================================================")
print("DISTRIBUIÇÃO V5.5 POR DIA")
print("=====================================================")
print("Total trades:", len(aceitos))
print("Dias com entrada:", dias["DataDia"].nunique())
print("Média trades por dia operado:", round(len(aceitos) / max(dias['DataDia'].nunique(), 1), 2))
print("Maior quantidade de trades em um dia:", int(dias["trades_no_dia"].max()) if len(dias) else 0)

print("\nDistribuição:")
print(dist.to_string(index=False))

print("\nLista de dias operados:")
print(dias.to_string(index=False))

dias.to_csv(SAIDA_DIAS, index=False, encoding="utf-8-sig")
dist.to_csv(SAIDA_RESUMO, index=False, encoding="utf-8-sig")

print("\nArquivos salvos:")
print(SAIDA_DIAS)
print(SAIDA_RESUMO)
