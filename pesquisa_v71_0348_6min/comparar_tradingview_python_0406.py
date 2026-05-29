from pathlib import Path
import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_TV = Path(r"C:\Users\ualac\Downloads\V71_0406_Diag_CME_MINI_MNQ1!_2026-05-29.csv")
ARQ_PY = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"

ARQ_SAIDA_XLSX = PESQUISA_DIR / "comparacao_tradingview_python_0406.xlsx"
ARQ_SAIDA_CSV = PESQUISA_DIR / "comparacao_tradingview_python_0406.csv"


def ler_tv():
    tv = pd.read_csv(ARQ_TV)
    tv.columns = [str(c).strip() for c in tv.columns]
    tv["Data e hora"] = pd.to_datetime(tv["Data e hora"], errors="coerce")
    tv["Preço USD"] = pd.to_numeric(tv["Preço USD"], errors="coerce")
    tv["Net PnL USD"] = pd.to_numeric(tv["Net PnL USD"], errors="coerce")

    entradas = tv[tv["Tipo"].astype(str).str.contains("Entrada", case=False, na=False)].copy()
    saidas = tv[tv["Tipo"].astype(str).str.contains("Sa", case=False, na=False)].copy()

    entradas = entradas.rename(columns={
        "Trade number": "trade_number",
        "Tipo": "tipo_entrada",
        "Data e hora": "dt_entrada_tv",
        "Sinal": "sinal_entrada_tv",
        "Preço USD": "preco_entrada_tv",
        "Net PnL USD": "net_pnl_usd_tv",
    })
    saidas = saidas.rename(columns={
        "Trade number": "trade_number",
        "Tipo": "tipo_saida",
        "Data e hora": "dt_saida_tv",
        "Sinal": "sinal_saida_tv",
        "Preço USD": "preco_saida_tv",
        "Net PnL USD": "net_pnl_usd_tv_saida",
    })

    cols_e = ["trade_number", "tipo_entrada", "dt_entrada_tv", "sinal_entrada_tv", "preco_entrada_tv", "net_pnl_usd_tv"]
    cols_s = ["trade_number", "tipo_saida", "dt_saida_tv", "sinal_saida_tv", "preco_saida_tv", "net_pnl_usd_tv_saida"]
    out = entradas[cols_e].merge(saidas[cols_s], on="trade_number", how="left")
    out["Direcao_tv"] = np.where(out["sinal_entrada_tv"].astype(str).str.contains("BUY", case=False), "BUY", "SELL")
    out["resultado_tv"] = np.where(out["net_pnl_usd_tv"] > 0, "TAKE", "STOP")
    out["pontos_tv_bruto"] = np.where(
        out["Direcao_tv"] == "BUY",
        out["preco_saida_tv"] - out["preco_entrada_tv"],
        out["preco_entrada_tv"] - out["preco_saida_tv"],
    )
    return out.sort_values("dt_entrada_tv").reset_index(drop=True)


def ler_python():
    df = pd.read_csv(ARQ_PY, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df["DataHora_saida"] = pd.to_datetime(df["DataHora_saida"], errors="coerce")
    base = df[
        (df["setup"] == "V71_OFICIAL_505_117")
        & (df["hhmm"] == "04:06")
        & (df["direcao_reversao_20"].isin(["BUY", "SELL"]))
        & (df["Direcao"] == df["direcao_reversao_20"])
    ].copy()
    base["range_ratio_10"] = base["range"] / base["range_med_10"].replace(0, np.nan)
    base = base[base["range_ratio_10"] <= 1.5].copy()
    base = base.rename(columns={
        "DataHora_SP": "dt_entrada_py",
        "DataHora_saida": "dt_saida_py",
        "close": "preco_entrada_py",
        "preco_saida": "preco_saida_py",
        "resultado": "resultado_py",
        "pontos": "pontos_py",
    })
    cols = [
        "dt_entrada_py", "Direcao", "preco_entrada_py", "dt_saida_py", "preco_saida_py",
        "resultado_py", "pontos_py", "open", "high", "low",
        "range_ratio_10", "pos_range_20",
    ]
    return base[cols].sort_values("dt_entrada_py").reset_index(drop=True)


def comparar():
    tv = ler_tv()
    py = ler_python()

    inicio_tv = tv["dt_entrada_tv"].min()
    fim_tv = tv["dt_entrada_tv"].max()
    py = py[(py["dt_entrada_py"] >= inicio_tv) & (py["dt_entrada_py"] <= fim_tv)].copy()

    comp = tv.merge(py, left_on="dt_entrada_tv", right_on="dt_entrada_py", how="outer", indicator=True)
    comp["match_entrada"] = comp["_merge"] == "both"
    comp["match_direcao"] = comp["Direcao_tv"].fillna("") == comp["Direcao"].fillna("")
    comp["match_preco_entrada"] = (comp["preco_entrada_tv"] - comp["preco_entrada_py"]).abs() < 0.01
    comp["match_saida_hora"] = comp["dt_saida_tv"] == comp["dt_saida_py"]
    comp["match_preco_saida"] = (comp["preco_saida_tv"] - comp["preco_saida_py"]).abs() < 0.01
    comp["match_resultado"] = comp["resultado_tv"].fillna("") == comp["resultado_py"].fillna("")
    comp["diff_preco_entrada"] = comp["preco_entrada_tv"] - comp["preco_entrada_py"]
    comp["diff_preco_saida"] = comp["preco_saida_tv"] - comp["preco_saida_py"]
    comp["diff_pontos_bruto_vs_py"] = comp["pontos_tv_bruto"] - comp["pontos_py"]

    resumo = pd.DataFrame([
        {"metrica": "trades_tv", "valor": len(tv)},
        {"metrica": "trades_python", "valor": len(py)},
        {"metrica": "inicio_tv", "valor": str(inicio_tv)},
        {"metrica": "fim_tv", "valor": str(fim_tv)},
        {"metrica": "entradas_em_ambos", "valor": int((comp["_merge"] == "both").sum())},
        {"metrica": "so_tv", "valor": int((comp["_merge"] == "left_only").sum())},
        {"metrica": "so_python", "valor": int((comp["_merge"] == "right_only").sum())},
        {"metrica": "direcao_diferente", "valor": int(((comp["_merge"] == "both") & (~comp["match_direcao"])).sum())},
        {"metrica": "preco_entrada_diferente", "valor": int(((comp["_merge"] == "both") & (~comp["match_preco_entrada"])).sum())},
        {"metrica": "resultado_diferente", "valor": int(((comp["_merge"] == "both") & (~comp["match_resultado"])).sum())},
        {"metrica": "saida_hora_diferente", "valor": int(((comp["_merge"] == "both") & (~comp["match_saida_hora"])).sum())},
        {"metrica": "preco_saida_diferente", "valor": int(((comp["_merge"] == "both") & (~comp["match_preco_saida"])).sum())},
    ])

    diverg = comp[
        (comp["_merge"] != "both")
        | (~comp["match_direcao"])
        | (~comp["match_preco_entrada"])
        | (~comp["match_resultado"])
        | (~comp["match_saida_hora"])
        | (~comp["match_preco_saida"])
    ].copy()

    comp.to_csv(ARQ_SAIDA_CSV, index=False)
    with pd.ExcelWriter(ARQ_SAIDA_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo", index=False)
        diverg.to_excel(writer, sheet_name="divergencias", index=False)
        comp.to_excel(writer, sheet_name="comparacao_completa", index=False)
        tv.to_excel(writer, sheet_name="tradingview", index=False)
        py.to_excel(writer, sheet_name="python", index=False)

    print("RESUMO")
    print(resumo.to_string(index=False))
    print("\nPRIMEIRAS DIVERGENCIAS")
    cols = [
        "trade_number", "_merge", "dt_entrada_tv", "dt_entrada_py", "Direcao_tv", "Direcao",
        "preco_entrada_tv", "preco_entrada_py", "resultado_tv", "resultado_py",
        "dt_saida_tv", "dt_saida_py", "preco_saida_tv", "preco_saida_py",
        "range_ratio_10", "pos_range_20",
    ]
    print(diverg[cols].head(30).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_SAIDA_XLSX)
    print(ARQ_SAIDA_CSV)


if __name__ == "__main__":
    comparar()
