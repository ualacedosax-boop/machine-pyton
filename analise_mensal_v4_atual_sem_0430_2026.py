from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_VALIDACAO = BASE_DIR / "validacao_v4_2026_fora_amostra"

ARQ_TRADES = PASTA_VALIDACAO / "03_2026_trades_config_atual_sem_0430.csv.gz"

ARQ_SAIDA_MENSAL = PASTA_VALIDACAO / "06_analise_mensal_config_atual_sem_0430.csv"
ARQ_SAIDA_DIRECAO_MENSAL = PASTA_VALIDACAO / "07_analise_mensal_direcao_config_atual_sem_0430.csv"
ARQ_SAIDA_HORARIO_MENSAL = PASTA_VALIDACAO / "08_analise_mensal_horario_config_atual_sem_0430.csv"
ARQ_SAIDA_EQUITY = PASTA_VALIDACAO / "09_equity_trades_config_atual_sem_0430.csv"


# ============================================================
# FUNÇÕES
# ============================================================

def calcular_profit_factor(df):
    ganhos = df.loc[df["pontos"] > 0, "pontos"].sum()
    perdas = abs(df.loc[df["pontos"] < 0, "pontos"].sum())

    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0

    return ganhos / perdas


def calcular_drawdown_serie(pontos):
    equity = pontos.cumsum()
    topo = equity.cummax()
    dd = equity - topo
    return float(dd.min())


def resumir_grupo(df, nome_grupo, valor_grupo):
    total = len(df)
    wins = int((df["resultado"] == "WIN").sum())
    losses = int((df["resultado"] == "LOSS").sum())
    lucro = float(df["pontos"].sum())
    pf = calcular_profit_factor(df)

    dd = calcular_drawdown_serie(df["pontos"].reset_index(drop=True))

    return {
        "grupo": nome_grupo,
        "valor": valor_grupo,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "drawdown_trades": dd,
        "media_pontos_trade": lucro / total if total else 0.0,
        "buy_total": int((df["Direcao"] == "BUY").sum()) if "Direcao" in df.columns else 0,
        "sell_total": int((df["Direcao"] == "SELL").sum()) if "Direcao" in df.columns else 0,
        "media_prob_win": float(df["prob_win_v4"].mean()) if "prob_win_v4" in df.columns else 0.0,
        "min_prob_win": float(df["prob_win_v4"].min()) if "prob_win_v4" in df.columns else 0.0,
        "drawdown_medio_trade": float(df["drawdown_stop_117_0"].mean()) if "drawdown_stop_117_0" in df.columns else 0.0,
        "drawdown_max_trade": float(df["drawdown_stop_117_0"].max()) if "drawdown_stop_117_0" in df.columns else 0.0,
        "runup_medio_trade": float(df["runup_stop_117_0"].mean()) if "runup_stop_117_0" in df.columns else 0.0,
        "runup_max_trade": float(df["runup_stop_117_0"].max()) if "runup_stop_117_0" in df.columns else 0.0,
    }


def main():
    print("=====================================================")
    print("ANÁLISE MENSAL - V4 ATUAL SEM 04:30 - 2026")
    print("=====================================================")

    if not ARQ_TRADES.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQ_TRADES}")

    print("\nLendo trades:")
    print(ARQ_TRADES)

    trades = pd.read_csv(ARQ_TRADES, compression="gzip")

    if trades.empty:
        print("Arquivo de trades vazio.")
        return

    # Padroniza colunas principais
    trades["DataHora_SP"] = pd.to_datetime(trades["DataHora_SP"], errors="coerce")
    trades = trades.dropna(subset=["DataHora_SP"]).copy()

    trades["resultado"] = trades["resultado_stop_117_0"]
    trades["pontos"] = pd.to_numeric(trades["pontos_stop_117_0"], errors="coerce").fillna(0.0)

    trades = trades.sort_values("DataHora_SP").reset_index(drop=True)

    trades["AnoMes"] = trades["DataHora_SP"].dt.strftime("%Y-%m")
    trades["Data"] = trades["DataHora_SP"].dt.date
    trades["Hora"] = trades["DataHora_SP"].dt.hour
    trades["Bloco_15m"] = (
        trades["DataHora_SP"].dt.hour.astype(str).str.zfill(2)
        + ":"
        + ((trades["DataHora_SP"].dt.minute // 15) * 15).astype(str).str.zfill(2)
    )

    # Equity trade a trade
    trades["equity_pontos"] = trades["pontos"].cumsum()
    trades["equity_topo"] = trades["equity_pontos"].cummax()
    trades["drawdown_equity"] = trades["equity_pontos"] - trades["equity_topo"]

    trades.to_csv(ARQ_SAIDA_EQUITY, index=False)

    # ========================================================
    # Resumo geral
    # ========================================================

    resumo_geral = resumir_grupo(trades, "GERAL", "2026")

    print("\n=====================================================")
    print("RESUMO GERAL")
    print("=====================================================")
    for k, v in resumo_geral.items():
        print(f"{k}: {v}")

    # ========================================================
    # Mensal
    # ========================================================

    linhas_mensal = []

    for mes, g in trades.groupby("AnoMes", sort=True):
        linhas_mensal.append(resumir_grupo(g, "MES", mes))

    mensal = pd.DataFrame(linhas_mensal)

    # Adiciona acumulado mês a mês
    mensal["lucro_acumulado"] = mensal["lucro_pontos"].cumsum()
    mensal["mes_positivo"] = mensal["lucro_pontos"] > 0
    mensal["mes_negativo"] = mensal["lucro_pontos"] < 0

    mensal.to_csv(ARQ_SAIDA_MENSAL, index=False)

    # ========================================================
    # Mensal por direção
    # ========================================================

    linhas_direcao = []

    if "Direcao" in trades.columns:
        for (mes, direcao), g in trades.groupby(["AnoMes", "Direcao"], sort=True):
            linhas_direcao.append(resumir_grupo(g, f"MES_DIRECAO_{direcao}", mes))

    direcao_mensal = pd.DataFrame(linhas_direcao)
    direcao_mensal.to_csv(ARQ_SAIDA_DIRECAO_MENSAL, index=False)

    # ========================================================
    # Mensal por bloco horário
    # ========================================================

    linhas_horario = []

    for (mes, bloco), g in trades.groupby(["AnoMes", "Bloco_15m"], sort=True):
        r = resumir_grupo(g, f"MES_BLOCO_{bloco}", mes)
        r["bloco_15m"] = bloco
        linhas_horario.append(r)

    horario_mensal = pd.DataFrame(linhas_horario)
    horario_mensal.to_csv(ARQ_SAIDA_HORARIO_MENSAL, index=False)

    # ========================================================
    # Impressões principais
    # ========================================================

    print("\n=====================================================")
    print("ANÁLISE MENSAL")
    print("=====================================================")

    cols_print = [
        "valor",
        "trades",
        "wins",
        "losses",
        "winrate",
        "lucro_pontos",
        "profit_factor",
        "drawdown_trades",
        "lucro_acumulado",
        "buy_total",
        "sell_total",
    ]

    print(mensal[cols_print].to_string(index=False))

    meses_positivos = int(mensal["mes_positivo"].sum())
    meses_negativos = int(mensal["mes_negativo"].sum())
    meses_total = len(mensal)

    print("\n=====================================================")
    print("DIAGNÓSTICO")
    print("=====================================================")

    print(f"Meses analisados: {meses_total}")
    print(f"Meses positivos: {meses_positivos}")
    print(f"Meses negativos: {meses_negativos}")

    pior_mes = mensal.sort_values("lucro_pontos", ascending=True).head(1)
    melhor_mes = mensal.sort_values("lucro_pontos", ascending=False).head(1)

    print("\nMelhor mês:")
    print(melhor_mes[cols_print].to_string(index=False))

    print("\nPior mês:")
    print(pior_mes[cols_print].to_string(index=False))

    lucro_total = float(mensal["lucro_pontos"].sum())
    lucro_melhor_mes = float(melhor_mes["lucro_pontos"].iloc[0])
    peso_melhor_mes = lucro_melhor_mes / lucro_total * 100 if lucro_total != 0 else 0.0

    print(f"\nLucro total: {lucro_total:.2f} pontos")
    print(f"Peso do melhor mês no lucro total: {peso_melhor_mes:.2f}%")

    if meses_negativos == 0:
        print("\nConclusão: excelente distribuição. Nenhum mês negativo.")
    elif meses_negativos <= 1 and peso_melhor_mes < 50:
        print("\nConclusão: boa distribuição. Resultado não parece depender de um único mês.")
    elif peso_melhor_mes >= 50:
        print("\nAtenção: resultado muito concentrado no melhor mês. Precisa cautela.")
    else:
        print("\nConclusão: resultado positivo, mas com meses negativos. Vale investigar os piores meses.")

    print("\nArquivos gerados:")
    print(ARQ_SAIDA_MENSAL)
    print(ARQ_SAIDA_DIRECAO_MENSAL)
    print(ARQ_SAIDA_HORARIO_MENSAL)
    print(ARQ_SAIDA_EQUITY)


if __name__ == "__main__":
    main()