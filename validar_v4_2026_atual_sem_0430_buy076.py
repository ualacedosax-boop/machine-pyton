from pathlib import Path
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

# ============================================================
# USA AS FUNÇÕES DO SCRIPT BASE QUE JÁ FUNCIONA
# ============================================================

import validar_v4_2026_config_antiga as base


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQUIVO_CANDLES_2026 = (
    BASE_DIR
    / "dados_mnq_2026_ibkr"
    / "MNQ_2026_2MIN_IBKR_CONTINUO.csv"
)

PASTA_SAIDA = BASE_DIR / "validacao_v4_2026_fora_amostra"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_FEATURES_2026 = PASTA_SAIDA / "01_2026_features_atual_sem_0430_buy076.csv.gz"
ARQ_SCORE_2026 = PASTA_SAIDA / "02_2026_score_atual_sem_0430_buy076.csv.gz"
ARQ_TRADES_2026 = PASTA_SAIDA / "03_2026_trades_atual_sem_0430_buy076.csv.gz"
ARQ_RESUMO_2026 = PASTA_SAIDA / "04_2026_resumo_atual_sem_0430_buy076.csv"
ARQ_ANALISE_2026 = PASTA_SAIDA / "05_2026_analise_atual_sem_0430_buy076.csv"


# ============================================================
# CONFIGURAÇÃO TESTE
# ============================================================

TAKE_PONTOS = 50.5
STOP_PONTOS = 117.0

PROB_WIN_MIN = 0.60
SCORE_BUY_MIN = 0.76
SCORE_SELL_MIN = 0.50
DIFERENCA_MINIMA = 0.00

HORA_INICIO = 2.0
HORA_FIM = 6.0

MAX_TRADES_DIA = 3
PARAR_APOS_LOSS = True

MAX_CANDLES_FUTURO = 720

# Bloqueio já aprovado no teste anterior
BLOQUEAR_0430_0444 = True
HORA_BLOQUEIO_INICIO = 4.5
HORA_BLOQUEIO_FIM = 4.75


# ============================================================
# APLICA CONFIGURAÇÃO
# ============================================================

def aplicar_config_teste(df):
    if df.empty:
        return pd.DataFrame()

    dados = df.copy()

    bloqueio_0430 = (
        BLOQUEAR_0430_0444
        & (dados["Hora_SP_Decimal"] >= HORA_BLOQUEIO_INICIO)
        & (dados["Hora_SP_Decimal"] < HORA_BLOQUEIO_FIM)
    )

    filtro = (
        (dados["prob_win_v4"] >= PROB_WIN_MIN)
        & (dados["Hora_SP_Decimal"] >= HORA_INICIO)
        & (dados["Hora_SP_Decimal"] < HORA_FIM)
        & (~bloqueio_0430)
        & (dados["score_diff"] >= DIFERENCA_MINIMA)
        & (
            ((dados["Direcao"] == "BUY") & (dados["score_BUY"] >= SCORE_BUY_MIN))
            | ((dados["Direcao"] == "SELL") & (dados["score_SELL"] >= SCORE_SELL_MIN))
        )
    )

    dados = dados[filtro].copy()
    dados = dados.sort_values("DataHora_SP").reset_index(drop=True)

    trades = []

    for data, grupo in dados.groupby("Data", sort=True):
        qtd = 0
        teve_loss = False

        grupo = grupo.sort_values("DataHora_SP")

        for _, row in grupo.iterrows():
            if qtd >= MAX_TRADES_DIA:
                break

            if PARAR_APOS_LOSS and teve_loss:
                break

            resultado = row["resultado_stop_117_0"]

            if resultado not in ["WIN", "LOSS"]:
                continue

            trades.append(row)

            qtd += 1

            if resultado == "LOSS":
                teve_loss = True

    if not trades:
        return pd.DataFrame()

    return pd.DataFrame(trades).reset_index(drop=True)


# ============================================================
# RESUMO
# ============================================================

def resumir_trades(trades):
    if trades.empty:
        return pd.DataFrame([{
            "versao": "V4_atual_sem_0430_buy076",
            "take_pontos": TAKE_PONTOS,
            "stop_pontos": STOP_PONTOS,
            "prob_win_min": PROB_WIN_MIN,
            "score_buy_min": SCORE_BUY_MIN,
            "score_sell_min": SCORE_SELL_MIN,
            "diferenca_minima": DIFERENCA_MINIMA,
            "hora_inicio": HORA_INICIO,
            "hora_fim": HORA_FIM,
            "bloquear_0430_0444": BLOQUEAR_0430_0444,
            "max_trades_dia": MAX_TRADES_DIA,
            "parar_apos_loss": PARAR_APOS_LOSS,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
        }])

    total = len(trades)
    wins = int((trades["resultado_stop_117_0"] == "WIN").sum())
    losses = int((trades["resultado_stop_117_0"] == "LOSS").sum())
    lucro = float(trades["pontos_stop_117_0"].sum())

    ganhos = trades.loc[trades["pontos_stop_117_0"] > 0, "pontos_stop_117_0"].sum()
    perdas = abs(trades.loc[trades["pontos_stop_117_0"] < 0, "pontos_stop_117_0"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    por_dia = trades.groupby("Data")["pontos_stop_117_0"].sum()

    # Drawdown pela curva trade a trade
    equity = trades["pontos_stop_117_0"].cumsum()
    topo = equity.cummax()
    drawdown_trades = float((equity - topo).min()) if len(equity) else 0.0

    return pd.DataFrame([{
        "versao": "V4_atual_sem_0430_buy076",
        "take_pontos": TAKE_PONTOS,
        "stop_pontos": STOP_PONTOS,
        "prob_win_min": PROB_WIN_MIN,
        "score_buy_min": SCORE_BUY_MIN,
        "score_sell_min": SCORE_SELL_MIN,
        "diferenca_minima": DIFERENCA_MINIMA,
        "hora_inicio": HORA_INICIO,
        "hora_fim": HORA_FIM,
        "bloquear_0430_0444": BLOQUEAR_0430_0444,
        "hora_bloqueio_inicio": HORA_BLOQUEIO_INICIO,
        "hora_bloqueio_fim": HORA_BLOQUEIO_FIM,
        "max_trades_dia": MAX_TRADES_DIA,
        "parar_apos_loss": PARAR_APOS_LOSS,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "buy_total": int((trades["Direcao"] == "BUY").sum()),
        "sell_total": int((trades["Direcao"] == "SELL").sum()),
        "dias_operados": int(trades["Data"].nunique()),
        "pior_dia": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia": float(por_dia.max()) if len(por_dia) else 0.0,
        "drawdown_trades": drawdown_trades,
        "media_prob_win": float(trades["prob_win_v4"].mean()),
        "min_prob_win": float(trades["prob_win_v4"].min()),
        "drawdown_medio_trade": float(trades["drawdown_stop_117_0"].mean()),
        "drawdown_max_trade": float(trades["drawdown_stop_117_0"].max()),
        "runup_medio_trade": float(trades["runup_stop_117_0"].mean()),
        "runup_max_trade": float(trades["runup_stop_117_0"].max()),
    }])


# ============================================================
# ANÁLISE POR HORÁRIO / DIREÇÃO / MÊS
# ============================================================

def analise_por_horario(trades):
    if trades.empty:
        return pd.DataFrame()

    df = trades.copy()
    dt = pd.to_datetime(df["DataHora_SP"])

    df["Hora"] = dt.dt.hour
    df["AnoMes"] = dt.dt.strftime("%Y-%m")
    df["Bloco_15m"] = (
        dt.dt.hour.astype(str).str.zfill(2)
        + ":"
        + ((dt.dt.minute // 15) * 15).astype(str).str.zfill(2)
    )

    linhas = []

    grupos = [
        ("Mes", "AnoMes"),
        ("Hora", "Hora"),
        ("Bloco_15m", "Bloco_15m"),
        ("Direcao", "Direcao"),
    ]

    for nome_grupo, col in grupos:
        for valor, g in df.groupby(col):
            total = len(g)
            wins = int((g["resultado_stop_117_0"] == "WIN").sum())
            losses = int((g["resultado_stop_117_0"] == "LOSS").sum())
            lucro = float(g["pontos_stop_117_0"].sum())

            ganhos = g.loc[g["pontos_stop_117_0"] > 0, "pontos_stop_117_0"].sum()
            perdas = abs(g.loc[g["pontos_stop_117_0"] < 0, "pontos_stop_117_0"].sum())
            pf = ganhos / perdas if perdas > 0 else 999.0

            linhas.append({
                "grupo": nome_grupo,
                "valor": valor,
                "trades": total,
                "wins": wins,
                "losses": losses,
                "winrate": wins / total * 100 if total else 0.0,
                "lucro_pontos": lucro,
                "profit_factor": pf,
            })

    return pd.DataFrame(linhas)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("VALIDAÇÃO V4 ATUAL 2026 - SEM 04:30 - BUY 0.76")
    print("=====================================================")

    print("\nConfiguração testada:")
    print(f"Take: {TAKE_PONTOS}")
    print(f"Stop: {STOP_PONTOS}")
    print(f"Prob min: {PROB_WIN_MIN}")
    print(f"BUY min: {SCORE_BUY_MIN}")
    print(f"SELL min: {SCORE_SELL_MIN}")
    print(f"Diff min: {DIFERENCA_MINIMA}")
    print(f"Hora: {HORA_INICIO} até {HORA_FIM}")
    print(f"Bloquear 04:30 até 04:44: {BLOQUEAR_0430_0444}")
    print(f"Max trades/dia: {MAX_TRADES_DIA}")
    print(f"Parar após loss: {PARAR_APOS_LOSS}")

    print("\nArquivos:")
    print("Candles 2026:", ARQUIVO_CANDLES_2026)
    print("Modelo V3:", base.MODELO_V3)
    print("Features V3:", base.FEATURES_V3)
    print("Modelo V4:", base.MODELO_V4)
    print("Features V4:", base.FEATURES_V4)

    print("\nLendo candles 2026...")
    candles = base.carregar_csv(ARQUIVO_CANDLES_2026)
    print("Candles carregados:", len(candles))

    print("\nCalculando features base + prev_...")
    features = base.calcular_features(candles)
    features.to_csv(ARQ_FEATURES_2026, index=False, compression="gzip")

    print("Features salvas:")
    print(ARQ_FEATURES_2026)

    score_v3 = base.aplicar_modelo_v3(features)

    if score_v3.empty:
        print("\nERRO: nenhum candidato foi gerado pelo modelo V3.")
        return

    score_v4 = base.aplicar_modelo_v4(score_v3)

    if score_v4.empty:
        print("\nERRO: nenhum candidato chegou ao modelo V4.")
        return

    score_resultado = base.adicionar_resultados_take_stop(score_v4, features)

    if score_resultado.empty:
        print("\nERRO: nenhum candidato teve resultado WIN/LOSS dentro do horizonte.")
        return

    score_resultado.to_csv(ARQ_SCORE_2026, index=False, compression="gzip")

    print("\nScore candidatos 2026 salvo:")
    print(ARQ_SCORE_2026)

    trades = aplicar_config_teste(score_resultado)
    resumo = resumir_trades(trades)
    analise = analise_por_horario(trades)

    trades.to_csv(ARQ_TRADES_2026, index=False, compression="gzip")
    resumo.to_csv(ARQ_RESUMO_2026, index=False)
    analise.to_csv(ARQ_ANALISE_2026, index=False)

    print("\n=====================================================")
    print("RESULTADO FORA DA AMOSTRA 2026 - SEM 04:30 - BUY 0.76")
    print("=====================================================")
    print(resumo.T.to_string())

    print("\nAnálise por mês/horário/direção:")
    if not analise.empty:
        print(analise.to_string(index=False))
    else:
        print("Sem análise, pois não houve trades finais.")

    print("\nArquivos gerados:")
    print(ARQ_TRADES_2026)
    print(ARQ_RESUMO_2026)
    print(ARQ_ANALISE_2026)

    print("\nComparação alvo:")
    print("Campeão atual : 168 trades | 78,57% | +2454 pontos | PF 1.58 | BUY 0.70")
    print("Este teste   : V4 atual sem 04:30 com BUY 0.76")


if __name__ == "__main__":
    main()
