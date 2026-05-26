from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA = BASE / "backtest_v71_score_congelado_dezembro_2025"
SAIDA.mkdir(exist_ok=True)

ARQUIVO = BASE / r"backtest_0348_2025_busca_janelas_score_acumulado\02_trades_todas_janelas_0348_2025.csv"

PARAMS = {
    "versao": "V7.1_SCORE_CONGELADO_PARCIAL",
    "periodo": "2025-12-01 a 2025-12-31",
    "arquivo_usado": str(ARQUIVO),
    "score_buy_min": 0.74,
    "score_sell_min": 0.50,
    "take": 50.5,
    "stop": 117.0,
    "hora_inicio": 2.0,
    "hora_fim": 6.0,
    "bloqueio_inicio": 4.5,
    "bloqueio_fim": 4.75,
    "max_trades_dia": 3,
    "parar_apos_loss": True,
    "observacao": "Teste parcial: aplica score_BUY/score_SELL congelados, horário, bloqueio, máximo trades/dia e parar após loss. Não aplica prob_v51/prob_v55/prob_v5_3 porque este arquivo 2025 não possui essas colunas."
}

print("=" * 100)
print("BACKTEST PARCIAL V7.1 - SCORE CONGELADO - DEZEMBRO 2025")
print("=" * 100)
print("Arquivo:", ARQUIVO)

if not ARQUIVO.exists():
    raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO}")

df = pd.read_csv(ARQUIVO, low_memory=False)

# Normalizar data
df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
df = df.dropna(subset=["DataHora_SP"]).copy()

# Filtrar dezembro/2025
df = df[(df["DataHora_SP"] >= "2025-12-01") & (df["DataHora_SP"] < "2026-01-01")].copy()

# Ordenar
df = df.sort_values("DataHora_SP").reset_index(drop=True)

# Hora decimal
df["HoraDecimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0
df["Data"] = df["DataHora_SP"].dt.date

# Filtro de horário V7.1
df = df[(df["HoraDecimal"] >= PARAMS["hora_inicio"]) & (df["HoraDecimal"] < PARAMS["hora_fim"])].copy()

# Bloqueio 04:30 até 04:45
df = df[~((df["HoraDecimal"] >= PARAMS["bloqueio_inicio"]) & (df["HoraDecimal"] < PARAMS["bloqueio_fim"]))].copy()

# Converter scores
df["score_BUY"] = pd.to_numeric(df["score_BUY"], errors="coerce")
df["score_SELL"] = pd.to_numeric(df["score_SELL"], errors="coerce")

# Padronizar direção
df["Direcao_UP"] = df["Direcao"].astype(str).str.upper()

# Aplicar thresholds congelados
mask_buy = df["Direcao_UP"].str.contains("BUY|COMPRA", regex=True) & (df["score_BUY"] >= PARAMS["score_buy_min"])
mask_sell = df["Direcao_UP"].str.contains("SELL|VENDA", regex=True) & (df["score_SELL"] >= PARAMS["score_sell_min"])

df = df[mask_buy | mask_sell].copy()

# Resultado/pontos
if "pontos" in df.columns:
    df["pontos_calc"] = pd.to_numeric(df["pontos"], errors="coerce")
else:
    def calc_pontos(r):
        txt = str(r.get("resultado", "")).lower()
        if "win" in txt or "take" in txt:
            return PARAMS["take"]
        if "loss" in txt or "stop" in txt:
            return -PARAMS["stop"]
        return np.nan
    df["pontos_calc"] = df.apply(calc_pontos, axis=1)

# Aplicar gestão: max 3 trades/dia e parar após loss
selecionadas = []

for data, g in df.groupby("Data"):
    trades_dia = 0
    teve_loss = False

    for _, row in g.sort_values("DataHora_SP").iterrows():
        if trades_dia >= PARAMS["max_trades_dia"]:
            continue

        if PARAMS["parar_apos_loss"] and teve_loss:
            continue

        selecionadas.append(row)
        trades_dia += 1

        if pd.notna(row["pontos_calc"]) and row["pontos_calc"] < 0:
            teve_loss = True

df_sel = pd.DataFrame(selecionadas)

if df_sel.empty:
    resumo = {
        **PARAMS,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "winrate_pct": 0,
        "lucro_pontos": 0,
        "drawdown_pontos": 0,
        "profit_factor": None,
        "dias_operados": 0,
        "media_trades_por_dia_operado": 0,
    }
else:
    pontos = pd.to_numeric(df_sel["pontos_calc"], errors="coerce").fillna(0)

    trades = len(df_sel)
    wins = int((pontos > 0).sum())
    losses = int((pontos < 0).sum())
    lucro = float(pontos.sum())
    winrate = wins / trades * 100 if trades else 0

    curva = pontos.cumsum()
    dd = curva - curva.cummax()
    max_dd = float(dd.min())

    bruto_win = float(pontos[pontos > 0].sum())
    bruto_loss = abs(float(pontos[pontos < 0].sum()))
    pf = bruto_win / bruto_loss if bruto_loss > 0 else None

    dias = int(df_sel["Data"].nunique())

    resumo = {
        **PARAMS,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate_pct": winrate,
        "lucro_pontos": lucro,
        "lucro_estimado_nq_dolar_20_por_ponto": lucro * 20,
        "drawdown_pontos": max_dd,
        "drawdown_estimado_nq_dolar_20_por_ponto": max_dd * 20,
        "profit_factor": pf,
        "dias_operados": dias,
        "media_trades_por_dia_operado": trades / dias if dias else 0,
    }

# Salvar
df_sel.to_csv(SAIDA / "trades_v71_score_congelado_dezembro_2025.csv", index=False, encoding="utf-8-sig")

with open(SAIDA / "resumo_v71_score_congelado_dezembro_2025.json", "w", encoding="utf-8") as f:
    json.dump(resumo, f, indent=4, ensure_ascii=False)

pd.DataFrame([resumo]).to_csv(SAIDA / "resumo_v71_score_congelado_dezembro_2025.csv", index=False, encoding="utf-8-sig")

print()
print("=" * 100)
print("RESULTADO BACKTEST PARCIAL V7.1 - SCORE CONGELADO - DEZEMBRO 2025")
print("=" * 100)

for k, v in resumo.items():
    print(f"{k}: {v}")

print()
print("Arquivos gerados:")
print(SAIDA / "trades_v71_score_congelado_dezembro_2025.csv")
print(SAIDA / "resumo_v71_score_congelado_dezembro_2025.json")
print(SAIDA / "resumo_v71_score_congelado_dezembro_2025.csv")
