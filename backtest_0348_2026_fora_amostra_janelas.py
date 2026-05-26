from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ============================================================
# IMPORTA O CÓDIGO BASE QUE JÁ FUNCIONA
# ============================================================

import validar_v4_2026_config_antiga as base


# ============================================================
# CONFIGURAÇÃO GERAL
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQUIVO_CANDLES_2026 = Path(
    r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\dados_mnq_2026_ibkr\MNQ_2026_2MIN_IBKR_CONTINUO.csv"
)

HORA_ENTRADA = "03:48"

# Configuração do robô atual
PROB_WIN_MIN = 0.60
SCORE_BUY_MIN = 0.70
SCORE_SELL_MIN = 0.50

TAKE_PONTOS = 50.5
STOP_PONTOS = 117.0

MAX_CANDLES_FUTURO = 720

# Testa com e sem filtro V4
TESTAR_FILTRO_V4 = [False, True]

# Janelas acumuladas testadas até 03:48
# None = desde 00:00 até 03:48
# 0 = somente o candle das 03:48
JANELAS_TESTE = [
    ("DIA_0000_0348", None),
    ("ULT_180_MIN", 180),
    ("ULT_120_MIN", 120),
    ("ULT_90_MIN", 90),
    ("ULT_60_MIN", 60),
    ("ULT_48_MIN", 48),
    ("ULT_30_MIN", 30),
    ("ULT_20_MIN", 20),
    ("ULT_15_MIN", 15),
    ("ULT_10_MIN", 10),
    ("CANDLE_0348", 0),
]

PASTA_SAIDA = BASE_DIR / "backtest_0348_2026_fora_amostra_janelas"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_SCORE = PASTA_SAIDA / "01_score_todas_janelas_0348_2026.csv.gz"
ARQ_TRADES = PASTA_SAIDA / "02_trades_todas_janelas_0348_2026.csv"
ARQ_RESUMO = PASTA_SAIDA / "03_ranking_janelas_0348_2026.csv"
ARQ_DETALHE = PASTA_SAIDA / "04_detalhe_por_dia_janelas_0348_2026.csv"


# ============================================================
# UTILITÁRIOS
# ============================================================

def hhmm_para_minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def minutos_para_hhmm(minutos: int) -> str:
    minutos = max(0, int(minutos))
    h = minutos // 60
    m = minutos % 60
    return f"{h:02d}:{m:02d}"


def localizar_candles_2026():
    if ARQUIVO_CANDLES_2026.exists():
        return ARQUIVO_CANDLES_2026

    encontrados = list(BASE_DIR.rglob("*2026*2MIN*.csv"))

    if encontrados:
        print("\nArquivos 2026 encontrados automaticamente:")
        for i, arq in enumerate(encontrados[:20], start=1):
            print(f"{i} - {arq}")

        return encontrados[0]

    raise FileNotFoundError(
        f"Arquivo de candles 2026 não encontrado: {ARQUIVO_CANDLES_2026}"
    )


# ============================================================
# APLICAR MODELO V3 EM TODOS OS CANDLES
# ============================================================

def aplicar_modelo_v3_todos(df_features):
    print("\nCarregando modelo V3...")

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
# APLICAR MODELO V4 ANTI-LOSS
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
# MONTA ENTRADAS PARA TODAS AS JANELAS
# ============================================================

def montar_entradas_todas_janelas(df_score):
    df = df_score.copy()

    df["DataHora_SP"] = base.remover_timezone(df["DataHora_SP"])
    df["Data"] = df["DataHora_SP"].dt.date
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["minuto_dia"] = df["DataHora_SP"].dt.hour * 60 + df["DataHora_SP"].dt.minute

    minuto_entrada = hhmm_para_minutos(HORA_ENTRADA)

    df["forca_BUY_pct"] = (df["score_BUY"] / SCORE_BUY_MIN) * 100.0
    df["forca_SELL_pct"] = (df["score_SELL"] / SCORE_SELL_MIN) * 100.0

    entradas_0348 = df[df["hhmm"] == HORA_ENTRADA].copy()

    if entradas_0348.empty:
        print(f"\nATENÇÃO: não encontrei candles exatamente às {HORA_ENTRADA}.")
        return pd.DataFrame()

    linhas = []

    print("\nMontando entradas para todas as janelas...")

    for data, candle_entrada_grupo in entradas_0348.groupby("Data"):
        candle_entrada = candle_entrada_grupo.iloc[0].copy()

        df_dia = df[df["Data"] == data].copy()

        for nome_janela, minutos_lookback in JANELAS_TESTE:
            if minutos_lookback is None:
                inicio_minuto = 0
            else:
                inicio_minuto = max(0, minuto_entrada - minutos_lookback)

            if minutos_lookback == 0:
                janela = df_dia[df_dia["hhmm"] == HORA_ENTRADA].copy()
            else:
                janela = df_dia[
                    (df_dia["minuto_dia"] >= inicio_minuto)
                    & (df_dia["minuto_dia"] <= minuto_entrada)
                ].copy()

            if janela.empty:
                continue

            idx_melhor_buy = janela["forca_BUY_pct"].idxmax()
            idx_melhor_sell = janela["forca_SELL_pct"].idxmax()

            melhor_buy = janela.loc[idx_melhor_buy]
            melhor_sell = janela.loc[idx_melhor_sell]

            melhor_forca_buy = float(melhor_buy["forca_BUY_pct"])
            melhor_forca_sell = float(melhor_sell["forca_SELL_pct"])

            entrada = candle_entrada.copy()

            entrada["janela_nome"] = nome_janela
            entrada["janela_minutos"] = -1 if minutos_lookback is None else minutos_lookback
            entrada["janela_inicio"] = minutos_para_hhmm(inicio_minuto)
            entrada["janela_fim"] = HORA_ENTRADA

            entrada["melhor_score_BUY_janela"] = float(melhor_buy["score_BUY"])
            entrada["melhor_score_SELL_janela"] = float(melhor_sell["score_SELL"])

            entrada["melhor_forca_BUY_pct_janela"] = melhor_forca_buy
            entrada["melhor_forca_SELL_pct_janela"] = melhor_forca_sell

            entrada["hora_melhor_BUY"] = melhor_buy["DataHora_SP"]
            entrada["hora_melhor_SELL"] = melhor_sell["DataHora_SP"]

            if melhor_forca_buy >= melhor_forca_sell:
                entrada["Direcao"] = "BUY"
                entrada["forca_direcao_pct"] = melhor_forca_buy
                entrada["forca_oposta_pct"] = melhor_forca_sell
                entrada["score_direcao"] = float(melhor_buy["score_BUY"])
                entrada["score_oposto"] = float(melhor_sell["score_SELL"])
                entrada["hora_score_decisao"] = melhor_buy["DataHora_SP"]
            else:
                entrada["Direcao"] = "SELL"
                entrada["forca_direcao_pct"] = melhor_forca_sell
                entrada["forca_oposta_pct"] = melhor_forca_buy
                entrada["score_direcao"] = float(melhor_sell["score_SELL"])
                entrada["score_oposto"] = float(melhor_buy["score_BUY"])
                entrada["hora_score_decisao"] = melhor_sell["DataHora_SP"]

            entrada["vantagem_pct"] = entrada["forca_direcao_pct"] - entrada["forca_oposta_pct"]

            linhas.append(entrada)

    entradas = pd.DataFrame(linhas)

    if entradas.empty:
        print("\nNenhuma entrada montada.")
        return entradas

    entradas = entradas.sort_values(["janela_nome", "DataHora_SP"]).reset_index(drop=True)

    print("\nTotal de entradas montadas:", len(entradas))

    print("\nEntradas por janela:")
    print(entradas["janela_nome"].value_counts().sort_index())

    print("\nDistribuição geral de direção:")
    print(entradas["Direcao"].value_counts())

    print("\nExemplo das primeiras entradas:")
    print(
        entradas[
            [
                "DataHora_SP",
                "janela_nome",
                "janela_inicio",
                "janela_fim",
                "Direcao",
                "score_BUY",
                "score_SELL",
                "melhor_forca_BUY_pct_janela",
                "melhor_forca_SELL_pct_janela",
                "hora_score_decisao",
                "vantagem_pct",
            ]
        ].head(30).to_string(index=False)
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
# RESUMIR POR JANELA
# ============================================================

def resumir_por_janela(trades):
    if trades.empty:
        return pd.DataFrame()

    linhas = []

    for (usar_filtro_v4, janela_nome), g in trades.groupby(["usar_filtro_v4", "janela_nome"]):
        total = len(g)
        wins = int((g["resultado"] == "WIN").sum())
        losses = int((g["resultado"] == "LOSS").sum())
        lucro = float(g["pontos"].sum())

        ganhos = g.loc[g["pontos"] > 0, "pontos"].sum()
        perdas = abs(g.loc[g["pontos"] < 0, "pontos"].sum())
        pf = ganhos / perdas if perdas > 0 else 999.0

        por_dia = g.groupby(pd.to_datetime(g["DataHora_SP"]).dt.date)["pontos"].sum()

        linhas.append({
            "usar_filtro_v4": bool(usar_filtro_v4),
            "janela_nome": janela_nome,
            "janela_inicio": str(g["janela_inicio"].iloc[0]),
            "janela_fim": str(g["janela_fim"].iloc[0]),
            "janela_minutos": int(g["janela_minutos"].iloc[0]),
            "take_pontos": TAKE_PONTOS,
            "stop_pontos": STOP_PONTOS,
            "prob_win_min": PROB_WIN_MIN,
            "score_buy_min": SCORE_BUY_MIN,
            "score_sell_min": SCORE_SELL_MIN,
            "trades": total,
            "wins": wins,
            "losses": losses,
            "winrate": wins / total * 100 if total else 0.0,
            "lucro_pontos": lucro,
            "profit_factor": pf,
            "buy_total": int((g["Direcao"] == "BUY").sum()),
            "sell_total": int((g["Direcao"] == "SELL").sum()),
            "dias_operados": int(pd.to_datetime(g["DataHora_SP"]).dt.date.nunique()),
            "pior_dia": float(por_dia.min()) if len(por_dia) else 0.0,
            "melhor_dia": float(por_dia.max()) if len(por_dia) else 0.0,
            "media_forca_direcao_pct": float(g["forca_direcao_pct"].mean()),
            "media_vantagem_pct": float(g["vantagem_pct"].mean()),
            "media_prob_win_v4": float(g["prob_win_v4"].mean()) if "prob_win_v4" in g.columns else 0.0,
            "min_prob_win_v4": float(g["prob_win_v4"].min()) if "prob_win_v4" in g.columns else 0.0,
            "drawdown_medio": float(g["drawdown"].mean()),
            "drawdown_max": float(g["drawdown"].max()),
            "runup_medio": float(g["runup"].mean()),
            "runup_max": float(g["runup"].max()),
        })

    resumo = pd.DataFrame(linhas)

    if resumo.empty:
        return resumo

    resumo = resumo.sort_values(
        ["lucro_pontos", "profit_factor", "winrate", "trades"],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)

    resumo["ranking"] = np.arange(1, len(resumo) + 1)

    cols = ["ranking"] + [c for c in resumo.columns if c != "ranking"]
    resumo = resumo[cols]

    return resumo


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("BACKTEST 2026 FORA DA AMOSTRA - 03:48 - JANELAS DE SCORE")
    print("=====================================================")

    print("\nRegra:")
    print(f"Entrada fixa às {HORA_ENTRADA}.")
    print("A direção é escolhida pela maior força acumulada em cada janela.")
    print(f"Força BUY  = score_BUY / {SCORE_BUY_MIN} * 100")
    print(f"Força SELL = score_SELL / {SCORE_SELL_MIN} * 100")
    print(f"Take: {TAKE_PONTOS}")
    print(f"Stop: {STOP_PONTOS}")
    print(f"Prob V4 mínimo, quando usado: {PROB_WIN_MIN}")

    print("\nJanelas testadas:")
    for nome, minutos in JANELAS_TESTE:
        if minutos is None:
            print(f"- {nome}: 00:00 até {HORA_ENTRADA}")
        elif minutos == 0:
            print(f"- {nome}: somente candle {HORA_ENTRADA}")
        else:
            inicio = minutos_para_hhmm(hhmm_para_minutos(HORA_ENTRADA) - minutos)
            print(f"- {nome}: {inicio} até {HORA_ENTRADA}")

    arquivo_candles = localizar_candles_2026()

    print("\nArquivo de candles 2026 usado:")
    print(arquivo_candles)

    print("\nLendo candles 2026...")
    candles = base.carregar_csv(arquivo_candles)
    print("Candles carregados:", len(candles))

    print("\nCalculando features...")
    features = base.calcular_features(candles)
    print("Features calculadas:", len(features))

    score = aplicar_modelo_v3_todos(features)

    entradas = montar_entradas_todas_janelas(score)

    if entradas.empty:
        print("\nERRO: nenhuma entrada montada.")
        return

    entradas = aplicar_modelo_v4(entradas)
    entradas.to_csv(ARQ_SCORE, index=False, compression="gzip")

    todos_trades = []

    print("\nSimulando take/stop para cada janela e cada filtro V4...")

    for usar_filtro in TESTAR_FILTRO_V4:
        base_entradas = entradas.copy()
        base_entradas["usar_filtro_v4"] = usar_filtro

        if usar_filtro:
            antes = len(base_entradas)
            base_entradas = base_entradas[base_entradas["prob_win_v4"] >= PROB_WIN_MIN].copy()
            depois = len(base_entradas)
            print(f"Filtro V4 aplicado: {antes} -> {depois} entradas")
        else:
            print(f"Sem filtro V4: {len(base_entradas)} entradas")

        trades = simular_entradas(base_entradas, features)

        if not trades.empty:
            trades["usar_filtro_v4"] = usar_filtro
            todos_trades.append(trades)

    if not todos_trades:
        print("\nERRO: nenhuma operação com resultado WIN/LOSS.")
        return

    trades_final = pd.concat(todos_trades, ignore_index=True)

    resumo = resumir_por_janela(trades_final)

    trades_final.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_RESUMO, index=False)

    detalhe_cols = [
        "DataHora_SP",
        "janela_nome",
        "usar_filtro_v4",
        "janela_inicio",
        "janela_fim",
        "Direcao",
        "score_BUY",
        "score_SELL",
        "melhor_forca_BUY_pct_janela",
        "melhor_forca_SELL_pct_janela",
        "hora_score_decisao",
        "prob_win_v4",
        "resultado",
        "pontos",
        "dt_saida",
    ]

    cols_existentes = [c for c in detalhe_cols if c in trades_final.columns]
    trades_final[cols_existentes].to_csv(ARQ_DETALHE, index=False)

    print("\n=====================================================")
    print("RANKING DAS JANELAS - 03:48 - 2026 FORA DA AMOSTRA")
    print("=====================================================")

    if not resumo.empty:
        print(
            resumo[
                [
                    "ranking",
                    "usar_filtro_v4",
                    "janela_nome",
                    "janela_inicio",
                    "janela_fim",
                    "trades",
                    "wins",
                    "losses",
                    "winrate",
                    "lucro_pontos",
                    "profit_factor",
                    "buy_total",
                    "sell_total",
                    "drawdown_max",
                    "media_prob_win_v4",
                ]
            ].to_string(index=False)
        )
    else:
        print("Resumo vazio.")

    print("\nArquivos gerados:")
    print(ARQ_SCORE)
    print(ARQ_TRADES)
    print(ARQ_RESUMO)
    print(ARQ_DETALHE)

    print("\nTOP 5 melhores janelas:")
    if not resumo.empty:
        print(
            resumo.head(5)[
                [
                    "ranking",
                    "usar_filtro_v4",
                    "janela_nome",
                    "janela_inicio",
                    "janela_fim",
                    "trades",
                    "winrate",
                    "lucro_pontos",
                    "profit_factor",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()