from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ_ENTRADAS = BASE / r"operacional_v71_oficial\trades_base_v71_oficial_2026.csv.gz"
ARQ_CANDLES  = BASE / r"dados_mnq_2026_ibkr\MNQ_2026_2MIN_IBKR_CONTINUO.csv"

SAIDA = BASE / "analise_v71_variacao_stop_intratrade_2026"
SAIDA.mkdir(exist_ok=True)

TAKE = 50.5
STOP_ORIGINAL = 117.0

STOPS_TESTE = [50, 60, 70, 80, 90, 100, 110, 117, 130, 150]

# Se no mesmo candle bater take e stop, temos ambiguidade.
# conservador = considera STOP primeiro
# agressivo = considera TAKE primeiro
MODO_AMBIGUO = "conservador"

print("=" * 100)
print("ANÁLISE V7.1 - VARIAÇÃO INTRATRADE ANTES DO TAKE")
print("=" * 100)
print("Entradas:", ARQ_ENTRADAS)
print("Candles :", ARQ_CANDLES)
print("Saída   :", SAIDA)
print()

if not ARQ_ENTRADAS.exists():
    raise FileNotFoundError(f"Arquivo de entradas não encontrado: {ARQ_ENTRADAS}")

if not ARQ_CANDLES.exists():
    raise FileNotFoundError(f"Arquivo de candles não encontrado: {ARQ_CANDLES}")

# ============================================================
# LEITURA ROBUSTA
# ============================================================

def ler_csv(path):
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            pass
    return pd.read_csv(path, low_memory=False)

entradas = ler_csv(ARQ_ENTRADAS)
candles = ler_csv(ARQ_CANDLES)

print("Colunas entradas:")
print(list(entradas.columns))
print()
print("Colunas candles:")
print(list(candles.columns))
print()

# ============================================================
# NORMALIZAR COLUNAS
# ============================================================

def achar_coluna(df, opcoes):
    for c in opcoes:
        if c in df.columns:
            return c
    return None

col_dt_ent = achar_coluna(entradas, ["DataHora_SP", "datahora_entrada", "DataHora", "datetime", "dt_entrada"])
col_dir = achar_coluna(entradas, ["Direcao", "direcao", "sinal", "side"])
col_pontos_original = achar_coluna(entradas, ["Pontos", "pontos", "resultado_pontos", "lucro_pontos"])
col_resultado_original = achar_coluna(entradas, ["Resultado", "resultado", "Result", "result"])

col_dt_candle = achar_coluna(candles, ["DataHora_SP", "DataHora", "datetime", "date"])
col_open = achar_coluna(candles, ["open", "Open", "abertura", "Abertura"])
col_high = achar_coluna(candles, ["high", "High", "maximo", "Máximo", "Maximo"])
col_low = achar_coluna(candles, ["low", "Low", "minimo", "Mínimo", "Minimo"])
col_close = achar_coluna(candles, ["close", "Close", "fechamento", "Último", "Ultimo"])

if not col_dt_ent:
    raise RuntimeError("Não encontrei coluna de data/hora nas entradas.")

if not col_dir:
    raise RuntimeError("Não encontrei coluna de direção nas entradas.")

if not col_dt_candle:
    raise RuntimeError("Não encontrei coluna de data/hora nos candles.")

for nome, col in {
    "open": col_open,
    "high": col_high,
    "low": col_low,
    "close": col_close,
}.items():
    if not col:
        raise RuntimeError(f"Não encontrei coluna {nome} nos candles.")

entradas["_dt"] = pd.to_datetime(entradas[col_dt_ent], errors="coerce")
candles["_dt"] = pd.to_datetime(candles[col_dt_candle], errors="coerce")

entradas = entradas.dropna(subset=["_dt"]).copy()
candles = candles.dropna(subset=["_dt"]).copy()

candles[col_open] = pd.to_numeric(candles[col_open], errors="coerce")
candles[col_high] = pd.to_numeric(candles[col_high], errors="coerce")
candles[col_low] = pd.to_numeric(candles[col_low], errors="coerce")
candles[col_close] = pd.to_numeric(candles[col_close], errors="coerce")

candles = candles.dropna(subset=[col_open, col_high, col_low, col_close]).copy()
candles = candles.sort_values("_dt").reset_index(drop=True)

# Filtrar entradas de 2026
entradas = entradas[(entradas["_dt"] >= "2026-01-01") & (entradas["_dt"] < "2027-01-01")].copy()
entradas = entradas.sort_values("_dt").reset_index(drop=True)

print(f"Entradas 2026 carregadas: {len(entradas)}")
print(f"Candles carregados       : {len(candles)}")
print()

# ============================================================
# FUNÇÕES
# ============================================================

def normalizar_direcao(x):
    s = str(x).upper()
    if "BUY" in s or "COMPRA" in s or s == "1":
        return "BUY"
    if "SELL" in s or "VENDA" in s or s == "-1":
        return "SELL"
    return "NONE"

def buscar_preco_entrada(dt):
    """
    Usa o close do candle no horário da entrada.
    Se não achar exatamente, usa o candle imediatamente anterior.
    """
    pos = candles["_dt"].searchsorted(dt, side="right") - 1
    if pos < 0:
        return np.nan, None
    row = candles.iloc[pos]
    return float(row[col_close]), int(pos)

def simular_trade(dt_entrada, direcao, preco_entrada, idx_candle_entrada, stop_teste, max_barras=500):
    """
    Simula a partir do candle seguinte ao de entrada.
    Mede MAE antes do take:
    - BUY: queda máxima contra = preco_entrada - menor low antes da saída
    - SELL: alta máxima contra = maior high - preco_entrada antes da saída
    """

    if direcao == "BUY":
        preco_take = preco_entrada + TAKE
        preco_stop = preco_entrada - stop_teste
    elif direcao == "SELL":
        preco_take = preco_entrada - TAKE
        preco_stop = preco_entrada + stop_teste
    else:
        return None

    pior_contra = 0.0
    melhor_favor = 0.0
    barras = 0

    inicio = idx_candle_entrada + 1
    fim = min(len(candles), inicio + max_barras)

    for i in range(inicio, fim):
        c = candles.iloc[i]
        high = float(c[col_high])
        low = float(c[col_low])
        dt_candle = c["_dt"]
        barras += 1

        if direcao == "BUY":
            contra = max(0.0, preco_entrada - low)
            favor = max(0.0, high - preco_entrada)

            pior_contra = max(pior_contra, contra)
            melhor_favor = max(melhor_favor, favor)

            bateu_stop = low <= preco_stop
            bateu_take = high >= preco_take

        else:
            contra = max(0.0, high - preco_entrada)
            favor = max(0.0, preco_entrada - low)

            pior_contra = max(pior_contra, contra)
            melhor_favor = max(melhor_favor, favor)

            bateu_stop = high >= preco_stop
            bateu_take = low <= preco_take

        if bateu_stop and bateu_take:
            if MODO_AMBIGUO == "conservador":
                return {
                    "resultado_simulado": "LOSS_AMBIGUO",
                    "pontos_simulados": -float(stop_teste),
                    "dt_saida_simulada": dt_candle,
                    "preco_entrada": preco_entrada,
                    "preco_take": preco_take,
                    "preco_stop": preco_stop,
                    "mae_antes_saida": pior_contra,
                    "mfe_antes_saida": melhor_favor,
                    "barras_ate_saida": barras,
                    "ambigua": True,
                }
            else:
                return {
                    "resultado_simulado": "WIN_AMBIGUO",
                    "pontos_simulados": float(TAKE),
                    "dt_saida_simulada": dt_candle,
                    "preco_entrada": preco_entrada,
                    "preco_take": preco_take,
                    "preco_stop": preco_stop,
                    "mae_antes_saida": pior_contra,
                    "mfe_antes_saida": melhor_favor,
                    "barras_ate_saida": barras,
                    "ambigua": True,
                }

        if bateu_stop:
            return {
                "resultado_simulado": "LOSS",
                "pontos_simulados": -float(stop_teste),
                "dt_saida_simulada": dt_candle,
                "preco_entrada": preco_entrada,
                "preco_take": preco_take,
                "preco_stop": preco_stop,
                "mae_antes_saida": pior_contra,
                "mfe_antes_saida": melhor_favor,
                "barras_ate_saida": barras,
                "ambigua": False,
            }

        if bateu_take:
            return {
                "resultado_simulado": "WIN",
                "pontos_simulados": float(TAKE),
                "dt_saida_simulada": dt_candle,
                "preco_entrada": preco_entrada,
                "preco_take": preco_take,
                "preco_stop": preco_stop,
                "mae_antes_saida": pior_contra,
                "mfe_antes_saida": melhor_favor,
                "barras_ate_saida": barras,
                "ambigua": False,
            }

    return {
        "resultado_simulado": "SEM_SAIDA",
        "pontos_simulados": 0.0,
        "dt_saida_simulada": pd.NaT,
        "preco_entrada": preco_entrada,
        "preco_take": preco_take,
        "preco_stop": preco_stop,
        "mae_antes_saida": pior_contra,
        "mfe_antes_saida": melhor_favor,
        "barras_ate_saida": barras,
        "ambigua": False,
    }

def calcular_drawdown(pontos):
    curva = pd.Series(pontos).fillna(0).cumsum()
    dd = curva - curva.cummax()
    return float(dd.min()), curva

def profit_factor(pontos):
    pontos = pd.Series(pontos).fillna(0)
    bruto_win = float(pontos[pontos > 0].sum())
    bruto_loss = abs(float(pontos[pontos < 0].sum()))
    if bruto_loss == 0:
        return None
    return bruto_win / bruto_loss

# ============================================================
# SIMULAR TODOS OS STOPS
# ============================================================

todos_resultados = []

for idx, ent in entradas.iterrows():
    dt_ent = ent["_dt"]
    direcao = normalizar_direcao(ent[col_dir])

    preco_ent, idx_candle = buscar_preco_entrada(dt_ent)

    if pd.isna(preco_ent) or idx_candle is None or direcao == "NONE":
        continue

    base = {
        "id_trade": idx + 1,
        "DataHora_SP": dt_ent,
        "Direcao": direcao,
        "preco_entrada_base": preco_ent,
    }

    if col_pontos_original:
        base["Pontos_original_arquivo"] = ent.get(col_pontos_original)

    if col_resultado_original:
        base["Resultado_original_arquivo"] = ent.get(col_resultado_original)

    for stop in STOPS_TESTE:
        r = simular_trade(
            dt_entrada=dt_ent,
            direcao=direcao,
            preco_entrada=preco_ent,
            idx_candle_entrada=idx_candle,
            stop_teste=stop,
        )

        if r is None:
            continue

        linha = {
            **base,
            "stop_teste": stop,
            **r
        }

        todos_resultados.append(linha)

df_res = pd.DataFrame(todos_resultados)

if df_res.empty:
    raise RuntimeError("Nenhuma simulação foi gerada. Verifique datas/preços/direção.")

# ============================================================
# RESUMO POR STOP
# ============================================================

resumos = []

for stop, g in df_res.groupby("stop_teste"):
    pontos = pd.to_numeric(g["pontos_simulados"], errors="coerce").fillna(0)

    trades = len(g)
    wins = int((pontos > 0).sum())
    losses = int((pontos < 0).sum())
    sem_saida = int((g["resultado_simulado"] == "SEM_SAIDA").sum())
    ambiguas = int(g["ambigua"].sum())

    lucro = float(pontos.sum())
    winrate = wins / trades * 100 if trades else 0
    max_dd, curva = calcular_drawdown(pontos)
    pf = profit_factor(pontos)

    mae_medio_wins = float(g.loc[pontos > 0, "mae_antes_saida"].mean()) if wins else None
    mae_max_wins = float(g.loc[pontos > 0, "mae_antes_saida"].max()) if wins else None
    mae_p75_wins = float(g.loc[pontos > 0, "mae_antes_saida"].quantile(0.75)) if wins else None
    mae_p90_wins = float(g.loc[pontos > 0, "mae_antes_saida"].quantile(0.90)) if wins else None
    mae_p95_wins = float(g.loc[pontos > 0, "mae_antes_saida"].quantile(0.95)) if wins else None

    resumos.append({
        "stop_teste": stop,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "sem_saida": sem_saida,
        "ambiguas": ambiguas,
        "winrate_pct": winrate,
        "lucro_pontos": lucro,
        "lucro_dolar_nq_20_por_ponto": lucro * 20,
        "drawdown_pontos": max_dd,
        "drawdown_dolar_nq_20_por_ponto": max_dd * 20,
        "profit_factor": pf,
        "mae_medio_dos_wins": mae_medio_wins,
        "mae_p75_dos_wins": mae_p75_wins,
        "mae_p90_dos_wins": mae_p90_wins,
        "mae_p95_dos_wins": mae_p95_wins,
        "mae_max_dos_wins": mae_max_wins,
    })

df_resumo = pd.DataFrame(resumos).sort_values("stop_teste")

# ============================================================
# COMPARAR COM STOP ORIGINAL 117
# ============================================================

base_117 = df_res[df_res["stop_teste"] == STOP_ORIGINAL][[
    "id_trade",
    "resultado_simulado",
    "pontos_simulados",
    "mae_antes_saida",
    "mfe_antes_saida",
    "barras_ate_saida",
]].copy()

base_117 = base_117.rename(columns={
    "resultado_simulado": "resultado_stop_117",
    "pontos_simulados": "pontos_stop_117",
    "mae_antes_saida": "mae_stop_117",
    "mfe_antes_saida": "mfe_stop_117",
    "barras_ate_saida": "barras_stop_117",
})

comparacoes = []

for stop in STOPS_TESTE:
    g = df_res[df_res["stop_teste"] == stop].copy()
    comp = g.merge(base_117, on="id_trade", how="left")

    win_117 = comp["pontos_stop_117"] > 0
    loss_stop_atual = comp["pontos_simulados"] < 0

    wins_117_viraram_loss = int((win_117 & loss_stop_atual).sum())

    comparacoes.append({
        "stop_teste": stop,
        "wins_com_117_que_viraram_loss": wins_117_viraram_loss,
        "pct_wins_117_viraram_loss": wins_117_viraram_loss / max(1, int(win_117.sum())) * 100,
        "wins_117_total": int(win_117.sum()),
    })

df_comp = pd.DataFrame(comparacoes)

df_resumo = df_resumo.merge(df_comp, on="stop_teste", how="left")

# ============================================================
# ANÁLISE DOS WINS DO STOP 117: QUANTO RESPIRARAM CONTRA
# ============================================================

wins_117 = df_res[(df_res["stop_teste"] == STOP_ORIGINAL) & (df_res["pontos_simulados"] > 0)].copy()

faixas = []
for limite in [50, 60, 70, 80, 90, 100, 110, 117]:
    qtd = int((wins_117["mae_antes_saida"] > limite).sum())
    total = len(wins_117)
    faixas.append({
        "limite_stop": limite,
        "wins_117_que_passaram_desse_drawdown": qtd,
        "total_wins_117": total,
        "pct": qtd / total * 100 if total else 0,
    })

df_faixas = pd.DataFrame(faixas)

# ============================================================
# SALVAR
# ============================================================

arquivo_resultados = SAIDA / "01_trades_simulados_por_stop.csv"
arquivo_resumo = SAIDA / "02_resumo_por_stop.csv"
arquivo_faixas = SAIDA / "03_wins_117_que_respiraram_acima_do_stop.csv"
arquivo_json = SAIDA / "resumo_analise_stop_v71.json"

df_res.to_csv(arquivo_resultados, index=False, encoding="utf-8-sig")
df_resumo.to_csv(arquivo_resumo, index=False, encoding="utf-8-sig")
df_faixas.to_csv(arquivo_faixas, index=False, encoding="utf-8-sig")

saida_json = {
    "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "arquivo_entradas": str(ARQ_ENTRADAS),
    "arquivo_candles": str(ARQ_CANDLES),
    "take": TAKE,
    "stop_original": STOP_ORIGINAL,
    "stops_testados": STOPS_TESTE,
    "modo_ambiguo": MODO_AMBIGUO,
    "resumo_por_stop": df_resumo.to_dict(orient="records"),
    "wins_117_que_respiraram_acima_do_stop": df_faixas.to_dict(orient="records"),
}

with open(arquivo_json, "w", encoding="utf-8") as f:
    json.dump(saida_json, f, indent=4, ensure_ascii=False, default=str)

# Também gerar Excel se openpyxl estiver disponível
try:
    arquivo_excel = SAIDA / "analise_stop_v71_2026.xlsx"
    with pd.ExcelWriter(arquivo_excel, engine="openpyxl") as writer:
        df_resumo.to_excel(writer, sheet_name="Resumo_por_Stop", index=False)
        df_faixas.to_excel(writer, sheet_name="Wins_117_MAE", index=False)
        df_res.to_excel(writer, sheet_name="Trades_Simulados", index=False)
    gerou_excel = True
except Exception as e:
    print("Não consegui gerar Excel:", e)
    gerou_excel = False
    arquivo_excel = None

# ============================================================
# PRINT FINAL
# ============================================================

print()
print("=" * 100)
print("RESUMO POR STOP")
print("=" * 100)

cols_print = [
    "stop_teste",
    "trades",
    "wins",
    "losses",
    "winrate_pct",
    "lucro_pontos",
    "drawdown_pontos",
    "profit_factor",
    "wins_com_117_que_viraram_loss",
    "pct_wins_117_viraram_loss",
    "mae_p90_dos_wins",
    "mae_max_dos_wins",
]

print(df_resumo[cols_print].to_string(index=False))

print()
print("=" * 100)
print("WINS DO STOP 117 QUE RESPIRARAM MAIS QUE CADA LIMITE")
print("=" * 100)
print(df_faixas.to_string(index=False))

print()
print("=" * 100)
print("ARQUIVOS GERADOS")
print("=" * 100)
print(arquivo_resultados)
print(arquivo_resumo)
print(arquivo_faixas)
print(arquivo_json)

if gerou_excel:
    print(arquivo_excel)

print()
print("Leitura rápida:")
print("- Se em stop 70 muitos wins_com_117_que_viraram_loss forem altos, stop 70 é perigoso.")
print("- mae_p90_dos_wins mostra quanto 90% dos trades vencedores precisaram respirar contra.")
print("- mae_max_dos_wins mostra o maior drawdown intra-trade entre os vencedores.")

