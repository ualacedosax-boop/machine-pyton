#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

FAMILIAS_SUGERIDAS = [
    "reversao_fundo",
    "reversao_topo",
    "pullback_continuacao_buy",
    "pullback_continuacao_sell",
    "sweep_fundo",
    "sweep_topo",
    "rompimento_continuacao",
    "indefinido",
]

def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    for enc in ["utf-8", "utf-8-sig", "utf-16", "latin1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path, sep=None, engine="python")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entradas", required=True, help="CSV/XLSX das entradas classificadas")
    ap.add_argument("--saida", required=True, help="Pasta de saída")
    args = ap.parse_args()

    outdir = Path(args.saida)
    outdir.mkdir(parents=True, exist_ok=True)

    df = read_any(Path(args.entradas))
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "datetime" not in df.columns or "side" not in df.columns:
        raise ValueError("O arquivo precisa ter pelo menos as colunas datetime e side.")
    if "setup_familia" not in df.columns:
        raise ValueError("O arquivo precisa ter a coluna setup_familia.")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["side"] = df["side"].astype(str).str.upper().str.strip()
    df["setup_familia"] = df["setup_familia"].astype(str).str.strip().str.lower()

    df = df.dropna(subset=["datetime"])
    validos = df[df["setup_familia"] != ""].copy()

    resumo_familia = (
        validos.groupby(["setup_familia", "side"])
        .size()
        .reset_index(name="qtd")
        .pivot(index="setup_familia", columns="side", values="qtd")
        .fillna(0)
        .reset_index()
    )

    if "qualidade_1a5" in validos.columns:
        validos["qualidade_1a5"] = pd.to_numeric(validos["qualidade_1a5"], errors="coerce")
        qualidade = (
            validos.groupby("setup_familia")["qualidade_1a5"]
            .agg(["count", "mean", "median"])
            .reset_index()
            .rename(columns={"count": "n_rotulados", "mean": "qualidade_media", "median": "qualidade_mediana"})
        )
    else:
        qualidade = pd.DataFrame(columns=["setup_familia", "n_rotulados", "qualidade_media", "qualidade_mediana"])

    faltando = df[df["setup_familia"] == ""].copy()

    resumo_familia.to_csv(outdir / "01_resumo_por_familia.csv", index=False, encoding="utf-8-sig")
    qualidade.to_csv(outdir / "02_qualidade_por_familia.csv", index=False, encoding="utf-8-sig")
    faltando.to_csv(outdir / "03_entradas_sem_classificacao.csv", index=False, encoding="utf-8-sig")

    texto = []
    texto.append("RESUMO DA CLASSIFICACAO DE SETUPS")
    texto.append("")
    texto.append(f"Total de entradas: {len(df)}")
    texto.append(f"Entradas classificadas: {len(validos)}")
    texto.append(f"Entradas sem classificacao: {len(faltando)}")
    texto.append("")
    texto.append("Familias sugeridas:")
    for fam in FAMILIAS_SUGERIDAS:
        texto.append(f"- {fam}")
    texto.append("")
    texto.append("Use os arquivos CSV gerados para descobrir quais familias valem a pena analisar separadamente.")
    (outdir / "04_resumo.txt").write_text("\n".join(texto), encoding="utf-8")

    print("Classificacao consolidada.")
    print(f"Entradas totais: {len(df)}")
    print(f"Entradas classificadas: {len(validos)}")
    print(f"Entradas sem classificacao: {len(faltando)}")
    print(f"Saida em: {outdir.resolve()}")

if __name__ == "__main__":
    main()
