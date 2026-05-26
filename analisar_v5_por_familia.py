#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    for enc in ["utf-8", "utf-8-sig", "utf-16", "latin1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path, sep=None, engine="python")

def robust_effect(a: pd.Series, b: pd.Series) -> float:
    med_a = float(np.nanmedian(a))
    med_b = float(np.nanmedian(b))
    allv = pd.concat([a, b], ignore_index=True)
    iqr = float(np.nanpercentile(allv, 75) - np.nanpercentile(allv, 25))
    if iqr == 0 or np.isnan(iqr):
        iqr = float(np.nanstd(allv))
    if iqr == 0 or np.isnan(iqr):
        return 0.0
    return (med_a - med_b) / iqr

def summarize_group(df: pd.DataFrame, target_label: str, compare_label: str, features: list[str]) -> pd.DataFrame:
    rows = []
    a_df = df[df["setup_familia"] == target_label].copy()
    b_df = df[df["setup_familia"] == compare_label].copy()
    for col in features:
        if col not in df.columns:
            continue
        a = pd.to_numeric(a_df[col], errors="coerce")
        b = pd.to_numeric(b_df[col], errors="coerce")
        if a.notna().sum() < 3 or b.notna().sum() < 3:
            continue
        eff = robust_effect(a, b)
        rows.append({
            "variavel": col,
            "median_" + target_label: float(np.nanmedian(a)),
            "median_" + compare_label: float(np.nanmedian(b)),
            "effect": eff,
            "abs_effect": abs(eff),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("abs_effect", ascending=False).reset_index(drop=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classificado", required=True, help="CSV classificado com datetime, side, setup_familia")
    ap.add_argument("--v5", required=True, help="Arquivo 01_entradas_casadas_v5.csv")
    ap.add_argument("--saida", required=True, help="Pasta de saída")
    args = ap.parse_args()

    outdir = Path(args.saida)
    outdir.mkdir(parents=True, exist_ok=True)

    cls = read_any(Path(args.classificado))
    v5 = read_any(Path(args.v5))

    cls.columns = [str(c).strip().lower() for c in cls.columns]
    v5.columns = [str(c).strip().lower() for c in v5.columns]

    required_cls = {"datetime", "side", "setup_familia"}
    required_v5 = {"datetime", "side"}
    if not required_cls.issubset(set(cls.columns)):
        raise ValueError("Arquivo classificado precisa ter datetime, side, setup_familia.")
    if not required_v5.issubset(set(v5.columns)):
        raise ValueError("Arquivo v5 precisa ter datetime e side.")

    cls["datetime"] = pd.to_datetime(cls["datetime"], errors="coerce")
    v5["datetime"] = pd.to_datetime(v5["datetime"], errors="coerce")
    cls["side"] = cls["side"].astype(str).str.upper().str.strip()
    v5["side"] = v5["side"].astype(str).str.upper().str.strip()
    cls["setup_familia"] = cls["setup_familia"].fillna("").astype(str).str.strip().str.lower()

    cls = cls.dropna(subset=["datetime"])
    v5 = v5.dropna(subset=["datetime"])

    merged = v5.merge(cls[["datetime", "side", "setup_familia"]], on=["datetime", "side"], how="left")
    merged["setup_familia"] = merged["setup_familia"].fillna("")

    merged.to_csv(outdir / "01_v5_com_classificacao.csv", index=False, encoding="utf-8-sig")

    fam_counts = (
        merged[merged["setup_familia"] != ""]
        .groupby(["setup_familia", "side"])
        .size()
        .reset_index(name="qtd")
    )
    fam_counts.to_csv(outdir / "02_resumo_familias.csv", index=False, encoding="utf-8-sig")

    ignore_cols = {"datetime", "side", "setup_familia"}
    numeric_features = [c for c in merged.columns if c not in ignore_cols and pd.api.types.is_numeric_dtype(merged[c])]

    rev_fundo = merged[merged["setup_familia"] == "reversao_fundo"].copy()
    rev_topo = merged[merged["setup_familia"] == "reversao_topo"].copy()

    rev_fundo.to_csv(outdir / "03_reversao_fundo.csv", index=False, encoding="utf-8-sig")
    rev_topo.to_csv(outdir / "04_reversao_topo.csv", index=False, encoding="utf-8-sig")

    if len(rev_fundo) >= 3 and len(rev_topo) >= 3:
        ranking = summarize_group(merged, "reversao_fundo", "reversao_topo", numeric_features)
    else:
        ranking = pd.DataFrame()
    ranking.to_csv(outdir / "05_ranking_reversao_fundo_vs_topo.csv", index=False, encoding="utf-8-sig")

    core_cols = [c for c in [
        "m5_run_dn_3", "m5_run_up_3", "m5_close_pos_bar", "m5_rsi_9",
        "b_close_pos_bar", "b_run_dn_5", "b_run_up_5",
        "h1_pos_range_10", "b_pos_day_range_so_far", "m5_pos_range_5"
    ] if c in merged.columns]

    comparativo = []
    for fam_name, fam_df in [("reversao_fundo", rev_fundo), ("reversao_topo", rev_topo)]:
        if fam_df.empty:
            continue
        row = {"setup_familia": fam_name, "n": len(fam_df)}
        for c in core_cols:
            row[c + "_mediana"] = float(np.nanmedian(pd.to_numeric(fam_df[c], errors="coerce")))
        comparativo.append(row)
    comp_df = pd.DataFrame(comparativo)
    comp_df.to_csv(outdir / "06_comparativo_core_features.csv", index=False, encoding="utf-8-sig")

    resumo = []
    resumo.append("RESUMO V5 POR FAMILIA")
    resumo.append("")
    resumo.append("Total V5: " + str(len(merged)))
    resumo.append("reversao_fundo: " + str(len(rev_fundo)))
    resumo.append("reversao_topo: " + str(len(rev_topo)))
    resumo.append("")
    if not ranking.empty:
        resumo.append("Top variáveis: reversao_fundo vs reversao_topo")
        for _, r in ranking.head(15).iterrows():
            resumo.append("- " + str(r["variavel"]) + ": effect=" + f"{r['effect']:.4f}")
    else:
        resumo.append("Ainda não há entradas suficientes em reversao_fundo e reversao_topo para ranking comparativo.")
    (outdir / "07_resumo.txt").write_text("\n".join(resumo), encoding="utf-8")

    print("Analise V5 por familia concluida.")
    print("Total V5: " + str(len(merged)))
    print("reversao_fundo: " + str(len(rev_fundo)))
    print("reversao_topo: " + str(len(rev_topo)))
    print("Saida em: " + str(outdir.resolve()))

if __name__ == "__main__":
    main()
