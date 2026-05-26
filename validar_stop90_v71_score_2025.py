from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ_ENTRADAS = BASE / r"backtest_0348_2025_busca_janelas_score_acumulado\02_trades_todas_janelas_0348_2025.csv"
ARQ_CANDLES  = BASE / r"MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv"

SAIDA = BASE / "validacao_stop90_v71_score_2025"
SAIDA.mkdir(exist_ok=True)

TAKE = 50.5
STOPS_TESTE = [50, 60, 70, 80, 90, 100, 110, 117, 130, 150]

SCORE_BUY_MIN = 0.74
SCORE_SELL_MIN = 0.50

HORA_INICIO = 2.0
HORA_FIM = 6.0
BLOQUEIO_INICIO = 4.5
BLOQUEIO_FIM = 4.75

MAX_TRADES_DIA = 3
PARAR_APOS_LOSS = True

MODO_AMBIGUO = "conservador"

print("=" * 100)
print("VALIDAÇÃO 2025 - STOP 90 / V7.1 SCORE CONGELADO")
print("=" * 100)
print("Entradas:", ARQ_ENTRADAS)
print("Candles :", ARQ_CANDLES)
print("Saída   :", SAIDA)
print()

if not ARQ_ENTRADAS.exists():
    raise FileNotFoundError(f"Arquivo de entradas não encontrado: {ARQ_ENTRADAS}")

if not ARQ_CANDLES.exists():
    raise FileNotFoundError(f"Arquivo de candles não encontrado: {ARQ_CANDLES}")

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

def achar_coluna(df, opcoes):
    for c in opcoes:
        if c in df.columns:
            return c
    return None

col_dt_ent = achar_coluna(entradas, ["DataHora_SP", "datahora_entrada", "DataHora", "datetime", "dt_entrada"])
col_dir = achar_coluna(entradas, ["Direcao", "direcao", "sinal", "side"])
col_score_buy = achar_coluna(entradas, ["score_BUY", "Score_BUY", "score_buy"])
col_score_sell = achar_coluna(entradas, ["score_SELL", "Score_SELL", "score_sell"])

col_dt_candle = achar_coluna(candles, ["DataHora_SP", "DataHora", "datetime", "date"])
col_open = achar_coluna(candles, ["open", "Open", "abertura", "Abertura"])
col_high = achar_coluna(candles, ["high", "High", "maximo", "Máximo", "Maximo"])
col_low = achar_coluna(candles, ["low", "Low", "minimo", "Mínimo", "Minimo"])
col_close = achar_coluna(candles, ["close", "Close", "fechamento", "Último", "Ultimo"])

for nome, col in {
    "data entradas": col_dt_ent,
    "direcao": col_dir,
    "score_BUY": col_score_buy,
    "score_SELL": col_score_sell,
    "data candles": col_dt_candle,
    "open": col_open,
    "high": col_high,
    "low": col_low,
    "close": col_close,
}.items():
    if not col:
        raise RuntimeError(f"Não encontrei coluna obrigatória: {nome}")

entradas["_dt"] = pd.to_datetime(entradas[col_dt_ent], errors="coerce")
candles["_dt"] = pd.to_datetime(candles[col_dt_candle], errors="coerce")

entradas = entradas.dropna(subset=["_dt"]).copy()
candles = candles.dropna(subset=["_dt"]).copy()

for c in [col_open, col_high, col_low, col_close]:
    candles[c] = pd.to_numeric(candles[c], errors="coerce")

candles = candles.dropna(subset=[col_open, col_high, col_low, col_close]).copy()
candles = candles.sort_values("_dt").reset_index(drop=True)

# Filtrar 2025
entradas = entradas[(entradas["_dt"] >= "2025-01-01") & (entradas["_dt"] < "2026-01-01")].copy()
entradas = entradas.sort_values("_dt").reset_index(drop=True)

entradas["HoraDecimal"] = entradas["_dt"].dt.hour + entradas["_dt"].dt.minute / 60.0
entradas["Data"] = entradas["_dt"].dt.date
entradas["Mes"] = entradas["_dt"].dt.to_period("M").astype(str)

# Horário operacional
entradas = entradas[(entradas["HoraDecimal"] >= HORA_INICIO) & (entradas["HoraDecimal"] < HORA_FIM)].copy()

# Bloqueio 04:30 até 04:45
entradas = entradas[~((entradas["HoraDecimal"] >= BLOQUEIO_INICIO) & (entradas["HoraDecimal"] < BLOQUEIO_FIM))].copy()

entradas[col_score_buy] = pd.to_numeric(entradas[col_score_buy], errors="coerce")
entradas[col_score_sell] = pd.to_numeric(entradas[col_score_sell], errors="coerce")

def normalizar_direcao(x):
    s = str(x).upper()
    if "BUY" in s or "COMPRA" in s or s == "1":
        return "BUY"
    if "SELL" in s or "VENDA" in s or s == "-1":
        return "SELL"
    return "NONE"

entradas["Direcao_Normalizada"] = entradas[col_dir].apply(normalizar_direcao)

# Thresholds congelados do V7.1
mask_buy = (entradas["Direcao_Normalizada"] == "BUY") & (entradas[col_score_buy] >= SCORE_BUY_MIN)
mask_sell = (entradas["Direcao_Normalizada"] == "SELL") & (entradas[col_score_sell] >= SCORE_SELL_MIN)

entradas = entradas[mask_buy | mask_sell].copy()
entradas = entradas.sort_values("_dt").reset_index(drop=True)

print(f"Entradas 2025 após filtros de score/horário: {len(entradas)}")
print(f"Candles 2025 carregados                  : {len(candles)}")
print()

def buscar_preco_entrada(dt):
    pos = candles["_dt"].searchsorted(dt, side="right") - 1
    if pos < 0:
        return np.nan, None
    row = candles.iloc[pos]
    return float(row[col_close]), int(pos)

def simular_trade(dt_entrada, direcao, preco_entrada, idx_candle_entrada, stop_teste, max_barras=500):
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
            bateu_stop = low <= preco_stop
            bateu_take = high >= preco_take
        else:
            contra = max(0.0, high - preco_entrada)
            favor = max(0.0, preco_entrada - low)
            bateu_stop = high >= preco_stop
            bateu_take = low <= preco_take

        pior_contra = max(pior_contra, contra)
        melhor_favor = max(melhor_favor, favor)

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
    return float(dd.min())

def profit_factor(pontos):
    pontos = pd.Series(pontos).fillna(0)
    bruto_win = float(pontos[pontos > 0].sum())
    bruto_loss = abs(float(pontos[pontos < 0].sum()))
    if bruto_loss == 0:
        return None
    return bruto_win / bruto_loss

todos_resultados = []

# Aplica gestão por dia usando a sequência original das entradas filtradas.
# A gestão precisa ser simulada para cada stop, porque loss muda conforme o stop.
for stop in STOPS_TESTE:
    for data, g_dia in entradas.groupby("Data"):
        trades_dia = 0
        teve_loss = False

        for idx, ent in g_dia.sort_values("_dt").iterrows():
            if trades_dia >= MAX_TRADES_DIA:
                continue

            if PARAR_APOS_LOSS and teve_loss:
                continue

            dt_ent = ent["_dt"]
            direcao = ent["Direcao_Normalizada"]
            preco_ent, idx_candle = buscar_preco_entrada(dt_ent)

            if pd.isna(preco_ent) or idx_candle is None or direcao == "NONE":
                continue

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
                "id_original": idx + 1,
                "DataHora_SP": dt_ent,
                "Data": data,
                "Mes": ent["Mes"],
                "Direcao": direcao,
                "score_BUY": ent[col_score_buy],
                "score_SELL": ent[col_score_sell],
                "stop_teste": stop,
                **r,
            }

            todos_resultados.append(linha)
            trades_dia += 1

            if linha["pontos_simulados"] < 0:
                teve_loss = True

df_res = pd.DataFrame(todos_resultados)

if df_res.empty:
    raise RuntimeError("Nenhuma simulação foi gerada.")

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
    max_dd = calcular_drawdown(pontos)
    pf = profit_factor(pontos)

    dias = int(g["Data"].nunique())

    wins_g = g[pontos > 0].copy()
    mae_p90 = float(wins_g["mae_antes_saida"].quantile(0.90)) if len(wins_g) else None
    mae_max = float(wins_g["mae_antes_saida"].max()) if len(wins_g) else None

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
        "dias_operados": dias,
        "media_trades_por_dia": trades / dias if dias else 0,
        "mae_p90_dos_wins": mae_p90,
        "mae_max_dos_wins": mae_max,
    })

df_resumo = pd.DataFrame(resumos).sort_values("stop_teste")

# Comparar cada stop contra 117
base117 = df_res[df_res["stop_teste"] == 117][["id_original", "pontos_simulados"]].rename(
    columns={"pontos_simulados": "pontos_stop_117"}
)

comparacoes = []

for stop, g in df_res.groupby("stop_teste"):
    comp = g.merge(base117, on="id_original", how="left")
    win117 = comp["pontos_stop_117"] > 0
    loss_atual = comp["pontos_simulados"] < 0

    qtd = int((win117 & loss_atual).sum())
    total_win117 = int(win117.sum())

    comparacoes.append({
        "stop_teste": stop,
        "wins_com_117_que_viraram_loss": qtd,
        "wins_117_total": total_win117,
        "pct_wins_117_viraram_loss": qtd / total_win117 * 100 if total_win117 else 0,
    })

df_comp = pd.DataFrame(comparacoes)
df_resumo = df_resumo.merge(df_comp, on="stop_teste", how="left")

# Mensal por stop
mensal = []

for (stop, mes), g in df_res.groupby(["stop_teste", "Mes"]):
    pontos = pd.to_numeric(g["pontos_simulados"], errors="coerce").fillna(0)

    trades = len(g)
    wins = int((pontos > 0).sum())
    losses = int((pontos < 0).sum())

    mensal.append({
        "stop_teste": stop,
        "mes": mes,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate_pct": wins / trades * 100 if trades else 0,
        "lucro_pontos": float(pontos.sum()),
        "drawdown_pontos": calcular_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
    })

df_mensal = pd.DataFrame(mensal).sort_values(["stop_teste", "mes"])

# Análise dos wins com stop 117
wins117 = df_res[(df_res["stop_teste"] == 117) & (df_res["pontos_simulados"] > 0)].copy()

faixas = []
for limite in [50, 60, 70, 80, 90, 100, 110, 117]:
    qtd = int((wins117["mae_antes_saida"] > limite).sum())
    total = len(wins117)
    faixas.append({
        "limite_stop": limite,
        "wins_117_que_passaram_desse_drawdown": qtd,
        "total_wins_117": total,
        "pct": qtd / total * 100 if total else 0,
    })

df_faixas = pd.DataFrame(faixas)

# Salvar arquivos
arq_trades = SAIDA / "01_trades_simulados_por_stop_2025.csv"
arq_resumo = SAIDA / "02_resumo_por_stop_2025.csv"
arq_mensal = SAIDA / "03_mensal_por_stop_2025.csv"
arq_faixas = SAIDA / "04_wins_117_que_respiraram_acima_do_stop_2025.csv"
arq_json = SAIDA / "resumo_validacao_stop90_2025.json"

df_res.to_csv(arq_trades, index=False, encoding="utf-8-sig")
df_resumo.to_csv(arq_resumo, index=False, encoding="utf-8-sig")
df_mensal.to_csv(arq_mensal, index=False, encoding="utf-8-sig")
df_faixas.to_csv(arq_faixas, index=False, encoding="utf-8-sig")

saida_json = {
    "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "arquivo_entradas": str(ARQ_ENTRADAS),
    "arquivo_candles": str(ARQ_CANDLES),
    "observacao": "Validação parcial 2025 com score_BUY/score_SELL congelados. Não aplica prob_v51/prob_v55/prob_v5_3.",
    "take": TAKE,
    "score_buy_min": SCORE_BUY_MIN,
    "score_sell_min": SCORE_SELL_MIN,
    "stops_testados": STOPS_TESTE,
    "modo_ambiguo": MODO_AMBIGUO,
    "resumo_por_stop": df_resumo.to_dict(orient="records"),
    "wins_117_que_respiraram_acima_do_stop": df_faixas.to_dict(orient="records"),
}

with open(arq_json, "w", encoding="utf-8") as f:
    json.dump(saida_json, f, indent=4, ensure_ascii=False, default=str)

try:
    arq_excel = SAIDA / "validacao_stop90_v71_score_2025.xlsx"
    with pd.ExcelWriter(arq_excel, engine="openpyxl") as writer:
        df_resumo.to_excel(writer, sheet_name="Resumo_por_Stop", index=False)
        df_mensal.to_excel(writer, sheet_name="Mensal_por_Stop", index=False)
        df_faixas.to_excel(writer, sheet_name="Wins_117_MAE", index=False)
        df_res.to_excel(writer, sheet_name="Trades_Simulados", index=False)
    gerou_excel = True
except Exception as e:
    print("Não consegui gerar Excel:", e)
    gerou_excel = False
    arq_excel = None

print()
print("=" * 100)
print("RESUMO POR STOP - 2025")
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
print("WINS DO STOP 117 QUE RESPIRARAM MAIS QUE CADA LIMITE - 2025")
print("=" * 100)
print(df_faixas.to_string(index=False))

print()
print("=" * 100)
print("MENSAL DO STOP 90 - 2025")
print("=" * 100)

print(df_mensal[df_mensal["stop_teste"] == 90].to_string(index=False))

print()
print("=" * 100)
print("ARQUIVOS GERADOS")
print("=" * 100)
print(arq_trades)
print(arq_resumo)
print(arq_mensal)
print(arq_faixas)
print(arq_json)

if gerou_excel:
    print(arq_excel)
