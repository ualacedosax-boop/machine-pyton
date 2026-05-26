from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ============================================================
# IMPORTA O CÓDIGO BASE QUE VOCÊ JÁ TEM
# ============================================================

import validar_v4_2026_config_antiga as base


# ============================================================
# CONFIGURAÇÃO DO TESTE
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

# Horário fixo da entrada
HORA_FIXA = "03:48"

# Configuração do robô atual encontrada em 2025
PROB_WIN_MIN = 0.60
SCORE_BUY_MIN = 0.70
SCORE_SELL_MIN = 0.50

# Take e stop usados no operacional
TAKE_PONTOS = 50.5
STOP_PONTOS = 117.0

MAX_CANDLES_FUTURO = 720

# Se True, só aceita entrada se o V4 anti-loss também passar no prob_win_min.
# Como você pediu entrada obrigatória às 03:48, deixei False.
USAR_FILTRO_V4 = False

PASTA_SAIDA = BASE_DIR / "backtest_0348_2025_robo_atual"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_SCORE = PASTA_SAIDA / "01_score_0348_2025_robo_atual.csv.gz"
ARQ_TRADES = PASTA_SAIDA / "02_trades_0348_2025_robo_atual.csv"
ARQ_RESUMO = PASTA_SAIDA / "03_resumo_0348_2025_robo_atual.csv"


# ============================================================
# LOCALIZAR ARQUIVO DE CANDLES 2025
# ============================================================

def localizar_candles_2025():
    candidatos = [
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQ_2025_2MIN_IBKR_CONTINUO.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQ_2025_2MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025" / "MNQ_2025_2MIN_IBKR_CONTINUO.csv",
        BASE_DIR / "MNQ_2025_2MIN_IBKR_CONTINUO.csv",
    ]

    for caminho in candidatos:
        if caminho.exists():
            return caminho

    encontrados = list(BASE_DIR.rglob("*2025*2MIN*.csv"))

    if encontrados:
        print("\nArquivos 2025 encontrados automaticamente:")
        for i, arq in enumerate(encontrados[:20], start=1):
            print(f"{i} - {arq}")

        return encontrados[0]

    raise FileNotFoundError(
        "Não encontrei o arquivo de candles 2025. "
        "Verifique se existe MNQ_2025_2MIN_IBKR_CONTINUO.csv dentro do projeto."
    )


# ============================================================
# APLICAR MODELO V3 EM TODOS OS CANDLES
# ============================================================

def aplicar_modelo_v3_todos(df_features):
    print("\nCarregando modelo V3 atual/base...")

    modelo_v3 = joblib.load(base.MODELO_V3)
    features_v3 = joblib.load(base.FEATURES_V3)

    X3 = base.preparar_X(df_features, features_v3, nome_modelo="V3")

    print("Gerando score BUY/SELL/NONE...")
    probas = modelo_v3.predict_proba(X3)

    print("Classes do modelo V3:")
    print(modelo_v3.classes_)

    df = df_features.copy()

    df["score_NONE"] = 0.0
    df["score_BUY"] = 0.0
    df["score_SELL"] = 0.0

    classes = list(modelo_v3.classes_)

    for i, classe in enumerate(classes):
        if int(classe) == 0:
            df["score_NONE"] = probas[:, i]
        elif int(classe) == 1:
            df["score_BUY"] = probas[:, i]
        elif int(classe) == 2:
            df["score_SELL"] = probas[:, i]

    return df


# ============================================================
# APLICAR V4 ANTI-LOSS NOS CANDIDATOS DE 03:48
# ============================================================

def aplicar_modelo_v4(df):
    print("\nCarregando modelo V4 anti-loss...")

    if df.empty:
        return df.copy()

    modelo_v4 = joblib.load(base.MODELO_V4)
    features_v4 = joblib.load(base.FEATURES_V4)

    X4 = base.preparar_X(df, features_v4, nome_modelo="V4")
    probas = modelo_v4.predict_proba(X4)

    print("Classes do modelo V4:")
    print(modelo_v4.classes_)

    classes = list(modelo_v4.classes_)

    out = df.copy()
    out["prob_win_v4"] = 0.0

    if len(classes) == 2:
        if 1 in classes:
            idx = classes.index(1)
        elif True in classes:
            idx = classes.index(True)
        else:
            idx = 1

        out["prob_win_v4"] = probas[:, idx]

    return out


# ============================================================
# SELECIONAR 03:48 E ESCOLHER DIREÇÃO PELO MAIOR PERCENTUAL
# ============================================================

def selecionar_entradas_0348(df_score):
    df = df_score.copy()

    df["hhmm"] = pd.to_datetime(df["DataHora_SP"]).dt.strftime("%H:%M")

    entradas = df[df["hhmm"] == HORA_FIXA].copy()
    entradas = entradas.sort_values("DataHora_SP").reset_index(drop=True)

    if entradas.empty:
        print(f"\nATENÇÃO: não encontrei candles exatamente às {HORA_FIXA}.")
        return entradas

    entradas["forca_BUY_pct"] = (entradas["score_BUY"] / SCORE_BUY_MIN) * 100.0
    entradas["forca_SELL_pct"] = (entradas["score_SELL"] / SCORE_SELL_MIN) * 100.0

    entradas["Direcao"] = np.where(
        entradas["forca_BUY_pct"] >= entradas["forca_SELL_pct"],
        "BUY",
        "SELL"
    )

    entradas["score_direcao"] = np.where(
        entradas["Direcao"] == "BUY",
        entradas["score_BUY"],
        entradas["score_SELL"]
    )

    entradas["forca_direcao_pct"] = np.where(
        entradas["Direcao"] == "BUY",
        entradas["forca_BUY_pct"],
        entradas["forca_SELL_pct"]
    )

    entradas["forca_oposta_pct"] = np.where(
        entradas["Direcao"] == "BUY",
        entradas["forca_SELL_pct"],
        entradas["forca_BUY_pct"]
    )

    entradas["vantagem_pct"] = entradas["forca_direcao_pct"] - entradas["forca_oposta_pct"]

    print("\nEntradas encontradas às 03:48:", len(entradas))
    print("\nDistribuição de direção escolhida:")
    print(entradas["Direcao"].value_counts())

    print("\nPrimeiras entradas escolhidas:")
    print(
        entradas[
            [
                "DataHora_SP",
                "score_BUY",
                "score_SELL",
                "forca_BUY_pct",
                "forca_SELL_pct",
                "Direcao",
                "vantagem_pct",
            ]
        ].head(20).to_string(index=False)
    )

    return entradas


# ============================================================
# SIMULAR TAKE/STOP
# ============================================================

def simular_entradas(df_entradas, df_features):
    if df_entradas.empty:
        return pd.DataFrame()

    df_base = df_features.reset_index(drop=True).copy()
    df_base["DataHora_SP"] = base.remover_timezone(df_base["DataHora_SP"])

    mapa_idx = pd.Series(df_base.index.values, index=df_base["DataHora_SP"]).to_dict()

    linhas = []

    for _, row in df_entradas.iterrows():
        dt = row["DataHora_SP"]

        if dt not in mapa_idx:
            continue

        idx = int(mapa_idx[dt])
        direcao = row["Direcao"]

        resultado, pontos, runup, drawdown, dt_saida, idx_saida = base.simular_trade(
            df_base,
            idx,
            direcao,
            TAKE_PONTOS,
            STOP_PONTOS,
            MAX_CANDLES_FUTURO,
        )

        if resultado == "NEUTRO":
            continue

        r = row.copy()
        r["resultado"] = resultado
        r["pontos"] = pontos
        r["runup"] = runup
        r["drawdown"] = drawdown
        r["dt_saida"] = dt_saida
        r["indice_saida"] = idx_saida
        r["take_pontos"] = TAKE_PONTOS
        r["stop_pontos"] = STOP_PONTOS

        linhas.append(r)

    return pd.DataFrame(linhas)


# ============================================================
# RESUMO
# ============================================================

def resumir(trades):
    if trades.empty:
        return pd.DataFrame([{
            "horario_entrada": HORA_FIXA,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
        }])

    total = len(trades)
    wins = int((trades["resultado"] == "WIN").sum())
    losses = int((trades["resultado"] == "LOSS").sum())
    lucro = float(trades["pontos"].sum())

    ganhos = trades.loc[trades["pontos"] > 0, "pontos"].sum()
    perdas = abs(trades.loc[trades["pontos"] < 0, "pontos"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    por_dia = trades.groupby(pd.to_datetime(trades["DataHora_SP"]).dt.date)["pontos"].sum()

    return pd.DataFrame([{
        "horario_entrada": HORA_FIXA,
        "take_pontos": TAKE_PONTOS,
        "stop_pontos": STOP_PONTOS,
        "score_buy_min": SCORE_BUY_MIN,
        "score_sell_min": SCORE_SELL_MIN,
        "prob_win_min": PROB_WIN_MIN,
        "usar_filtro_v4": USAR_FILTRO_V4,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "buy_total": int((trades["Direcao"] == "BUY").sum()),
        "sell_total": int((trades["Direcao"] == "SELL").sum()),
        "dias_operados": int(pd.to_datetime(trades["DataHora_SP"]).dt.date.nunique()),
        "pior_dia": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia": float(por_dia.max()) if len(por_dia) else 0.0,
        "media_score_buy": float(trades["score_BUY"].mean()),
        "media_score_sell": float(trades["score_SELL"].mean()),
        "media_forca_buy_pct": float(trades["forca_BUY_pct"].mean()),
        "media_forca_sell_pct": float(trades["forca_SELL_pct"].mean()),
        "media_vantagem_pct": float(trades["vantagem_pct"].mean()),
        "media_prob_win_v4": float(trades["prob_win_v4"].mean()) if "prob_win_v4" in trades.columns else 0.0,
        "min_prob_win_v4": float(trades["prob_win_v4"].min()) if "prob_win_v4" in trades.columns else 0.0,
        "drawdown_medio": float(trades["drawdown"].mean()),
        "drawdown_max": float(trades["drawdown"].max()),
        "runup_medio": float(trades["runup"].mean()),
        "runup_max": float(trades["runup"].max()),
    }])


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("BACKTEST 2025 - ROBÔ ATUAL - ENTRADA FIXA 03:48")
    print("=====================================================")

    print("\nRegra:")
    print(f"Todo dia às {HORA_FIXA}, escolher BUY ou SELL pela maior força percentual.")
    print(f"Força BUY  = score_BUY / {SCORE_BUY_MIN}")
    print(f"Força SELL = score_SELL / {SCORE_SELL_MIN}")
    print(f"Take: {TAKE_PONTOS}")
    print(f"Stop: {STOP_PONTOS}")
    print(f"Usar filtro V4: {USAR_FILTRO_V4}")

    arquivo_candles = localizar_candles_2025()
    print("\nArquivo de candles 2025 usado:")
    print(arquivo_candles)

    print("\nLendo candles 2025...")
    candles = base.carregar_csv(arquivo_candles)
    print("Candles carregados:", len(candles))

    print("\nCalculando features...")
    features = base.calcular_features(candles)
    print("Features calculadas:", len(features))

    score = aplicar_modelo_v3_todos(features)

    entradas = selecionar_entradas_0348(score)

    if entradas.empty:
        print("\nERRO: sem entradas 03:48 para testar.")
        return

    entradas = aplicar_modelo_v4(entradas)

    if USAR_FILTRO_V4:
        antes = len(entradas)
        entradas = entradas[entradas["prob_win_v4"] >= PROB_WIN_MIN].copy()
        depois = len(entradas)
        print(f"\nFiltro V4 aplicado: {antes} -> {depois} entradas")

    entradas.to_csv(ARQ_SCORE, index=False, compression="gzip")

    print("\nSimulando take/stop...")
    trades = simular_entradas(entradas, features)

    resumo = resumir(trades)

    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)

    print("\n=====================================================")
    print("RESULTADO BACKTEST 2025 - ENTRADA FIXA 03:48")
    print("=====================================================")
    print(resumo.T.to_string())

    print("\nArquivos gerados:")
    print(ARQ_SCORE)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)

    if not trades.empty:
        print("\nÚltimas 20 operações:")
        print(
            trades[
                [
                    "DataHora_SP",
                    "Direcao",
                    "score_BUY",
                    "score_SELL",
                    "forca_BUY_pct",
                    "forca_SELL_pct",
                    "prob_win_v4",
                    "resultado",
                    "pontos",
                    "dt_saida",
                ]
            ].tail(20).to_string(index=False)
        )


if __name__ == "__main__":
    main()