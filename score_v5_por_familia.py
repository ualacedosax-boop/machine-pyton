#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

BUY_FEATURES = [
    "b_ret_3",
    "b_dist_sma_9",
    "b_run_dn_5",
    "m5_run_dn_3",
    "b_body_pct",
    "b_pos_range_5",
]

SELL_FEATURES = [
    "b_ret_3",
    "b_dist_sma_9",
    "b_run_up_5",
    "b_pos_range_5",
    "m5_close_pos_bar",
    "m5_rsi_9",
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

def median_or_default(df: pd.DataFrame, col: str, default: float = 0.0) -> float:
    if col not in df.columns:
        return default
    s = pd.to_numeric(df[col], errors="coerce")
    if s.notna().sum() == 0:
        return default
    return float(np.nanmedian(s))

def build_thresholds(df: pd.DataFrame) -> dict:
    rev_fundo = df[df["setup_familia"] == "reversao_fundo"].copy()
    rev_topo = df[df["setup_familia"] == "reversao_topo"].copy()

    th = {
        "buy_ret3_max": median_or_default(rev_fundo, "b_ret_3", 0.0),
        "buy_dist_sma9_max": median_or_default(rev_fundo, "b_dist_sma_9", 0.0),
        "buy_run_dn5_min": median_or_default(rev_fundo, "b_run_dn_5", 2.0),
        "buy_m5_run_dn3_min": median_or_default(rev_fundo, "m5_run_dn_3", 1.0),
        "buy_body_pct_min": median_or_default(rev_fundo, "b_body_pct", 0.5),
        "buy_pos_range5_max": median_or_default(rev_fundo, "b_pos_range_5", 0.55),

        "sell_ret3_min": median_or_default(rev_topo, "b_ret_3", 0.0),
        "sell_dist_sma9_min": median_or_default(rev_topo, "b_dist_sma_9", 0.0),
        "sell_run_up5_min": median_or_default(rev_topo, "b_run_up_5", 2.0),
        "sell_pos_range5_min": median_or_default(rev_topo, "b_pos_range_5", 0.65),
        "sell_m5_close_pos_bar_max": median_or_default(rev_topo, "m5_close_pos_bar", 0.45),
        "sell_m5_rsi9_min": median_or_default(rev_topo, "m5_rsi_9", 50.0),
    }
    return th

def add_scores(df: pd.DataFrame, th: dict) -> pd.DataFrame:
    out = df.copy()

    def num(col):
        return pd.to_numeric(out[col], errors="coerce") if col in out.columns else pd.Series(np.nan, index=out.index)

    b_ret_3 = num("b_ret_3")
    b_dist_sma_9 = num("b_dist_sma_9")
    b_run_dn_5 = num("b_run_dn_5")
    m5_run_dn_3 = num("m5_run_dn_3")
    b_body_pct = num("b_body_pct")
    b_pos_range_5 = num("b_pos_range_5")

    b_run_up_5 = num("b_run_up_5")
    m5_close_pos_bar = num("m5_close_pos_bar")
    m5_rsi_9 = num("m5_rsi_9")

    out["score_buy_rf"] = 0
    out["score_buy_rf"] += (b_ret_3 <= th["buy_ret3_max"]).astype(int)
    out["score_buy_rf"] += (b_dist_sma_9 <= th["buy_dist_sma9_max"]).astype(int)
    out["score_buy_rf"] += (b_run_dn_5 >= th["buy_run_dn5_min"]).astype(int)
    out["score_buy_rf"] += (m5_run_dn_3 >= th["buy_m5_run_dn3_min"]).astype(int)
    out["score_buy_rf"] += (b_body_pct >= th["buy_body_pct_min"]).astype(int)
    out["score_buy_rf"] += (b_pos_range_5 <= th["buy_pos_range5_max"]).astype(int)

    out["score_sell_rt"] = 0
    out["score_sell_rt"] += (b_ret_3 >= th["sell_ret3_min"]).astype(int)
    out["score_sell_rt"] += (b_dist_sma_9 >= th["sell_dist_sma9_min"]).astype(int)
    out["score_sell_rt"] += (b_run_up_5 >= th["sell_run_up5_min"]).astype(int)
    out["score_sell_rt"] += (b_pos_range_5 >= th["sell_pos_range5_min"]).astype(int)
    out["score_sell_rt"] += (m5_close_pos_bar <= th["sell_m5_close_pos_bar_max"]).astype(int)
    out["score_sell_rt"] += (m5_rsi_9 >= th["sell_m5_rsi9_min"]).astype(int)

    out["familia_sugerida_score"] = np.where(
        out["score_buy_rf"] > out["score_sell_rt"], "reversao_fundo",
        np.where(out["score_sell_rt"] > out["score_buy_rf"], "reversao_topo", "empate")
    )

    if "setup_familia" in out.columns:
        out["score_acertou_familia"] = (out["familia_sugerida_score"] == out["setup_familia"]).astype(int)

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v5_classificado", required=True, help="Arquivo 01_v5_com_classificacao.csv")
    ap.add_argument("--saida", required=True, help="Pasta de saída")
    args = ap.parse_args()

    outdir = Path(args.saida)
    outdir.mkdir(parents=True, exist_ok=True)

    df = read_any(Path(args.v5_classificado))
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "setup_familia" not in df.columns:
        raise ValueError("O arquivo precisa ter a coluna setup_familia.")

    th = build_thresholds(df)
    scored = add_scores(df, th)

    scored.to_csv(outdir / "01_v5_com_scores_familia.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([th]).to_csv(outdir / "02_thresholds_familia.csv", index=False, encoding="utf-8-sig")

    resumo = []
    resumo.append("RESUMO SCORE POR FAMILIA")
    resumo.append("")
    resumo.append("Thresholds usados:")
    for k, v in th.items():
        resumo.append(f"- {k}: {v:.4f}")

    if "score_acertou_familia" in scored.columns:
        base = scored[scored["setup_familia"].isin(["reversao_fundo", "reversao_topo"])].copy()
        if len(base) > 0:
            acc = float(base["score_acertou_familia"].mean())
            resumo.append("")
            resumo.append(f"Acurácia no conjunto classificado (2 famílias): {acc:.4f}")
            resumo.append(f"Total avaliado: {len(base)}")
            tabela = (
                base.groupby(["setup_familia", "familia_sugerida_score"])
                .size()
                .reset_index(name="qtd")
            )
            tabela.to_csv(outdir / "03_confusao_familia_score.csv", index=False, encoding="utf-8-sig")
        else:
            resumo.append("")
            resumo.append("Sem linhas suficientes nas famílias reversao_fundo/reversao_topo.")
    else:
        resumo.append("")
        resumo.append("Arquivo sem setup_familia real; score gerado sem validação.")

    (outdir / "04_resumo.txt").write_text("\n".join(resumo), encoding="utf-8")
    print("Score por familia gerado.")
    print(f"Saida em: {outdir.resolve()}")

if __name__ == "__main__":
    main()
