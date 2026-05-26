from pathlib import Path
import pandas as pd

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

colunas_desejadas = [
    "DataHora_SP",
    "prob_v51",
    "prob_v55",
    "score_BUY",
    "score_SELL",
    "prob_v5_3",
    "Direcao",
    "resultado",
    "pnl",
    "pontos",
    "lucro_pontos",
]

arquivos = []
for padrao in ["*.csv", "*.csv.gz"]:
    arquivos.extend(BASE.rglob(padrao))

achados = []

def ler(path):
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False, nrows=5)
        except Exception:
            pass
    return None

for arq in arquivos:
    try:
        df = ler(arq)
        if df is None or df.empty:
            continue

        cols = list(df.columns)
        score = sum(1 for c in colunas_desejadas if c in cols)

        if score >= 3:
            achados.append({
                "score_colunas": score,
                "arquivo": str(arq),
                "colunas_encontradas": ", ".join([c for c in colunas_desejadas if c in cols]),
                "todas_colunas": ", ".join(cols[:80]),
            })
    except Exception:
        pass

res = pd.DataFrame(achados).sort_values("score_colunas", ascending=False)

saida = BASE / "diagnostico_arquivos_v71_predicoes.csv"
res.to_csv(saida, index=False, encoding="utf-8-sig")

print("=" * 100)
print("ARQUIVOS MAIS PROVÁVEIS PARA BACKTEST REAL DO V7.1")
print("=" * 100)

if res.empty:
    print("Nenhum arquivo com colunas suficientes encontrado.")
else:
    print(res.head(20).to_string(index=False))

print()
print("Diagnóstico salvo em:")
print(saida)
