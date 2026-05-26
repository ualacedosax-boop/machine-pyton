import pandas as pd

df = pd.read_csv("mercado_real.csv")

print("Colunas do arquivo:")
print(df.columns.tolist())

print("\nPrimeiras 10 linhas:")
print(df.head(10))