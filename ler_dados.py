import pandas as pd

df = pd.read_csv("dados.csv")

df["mm3"] = df["close"].rolling(3).mean()

df["sinal"] = 0
df.loc[df["close"] > df["mm3"], "sinal"] = 1
df.loc[df["close"] < df["mm3"], "sinal"] = -1

print(df[["close", "mm3", "sinal"]])