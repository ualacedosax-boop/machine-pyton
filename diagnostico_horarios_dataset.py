import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA = BASE / "saida_v5_filtro_campeao_2024_2025_2026"

arquivos = [
    PASTA / "04_dataset_v5_TREINO_2024_2025.csv.gz",
    PASTA / "05_dataset_v5_TESTE_2026.csv.gz",
]

for arq in arquivos:
    print("=" * 80)
    print(arq)

    df = pd.read_csv(arq, compression="gzip")
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()

    df["Ano"] = df["DataHora_SP"].dt.year
    df["Hora"] = df["DataHora_SP"].dt.hour
    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0

    dist = df.groupby(["Ano", "Hora"]).size().reset_index(name="qtd")
    print(dist.to_string(index=False))

    print()
    print("Resumo por faixa:")
    faixas = {
        "00_02": (0, 2),
        "02_06": (2, 6),
        "06_08": (6, 8),
        "08_12": (8, 12),
        "12_15": (12, 15),
        "15_18": (15, 18),
        "18_23": (18, 23),
    }

    for nome, (ini, fim) in faixas.items():
        qtd = len(df[(df["Hora_SP_Decimal"] >= ini) & (df["Hora_SP_Decimal"] < fim)])
        print(f"{nome}: {qtd}")
