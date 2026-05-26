import warnings
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURAÇÕES PRINCIPAIS
# ============================================================

PASTA_BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_SAIDA = PASTA_BASE / "saida_ml_entradas_video_v4_antiloss_otimizacao_A"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

# Arquivo correto encontrado no seu computador
ARQUIVO_ENTRADAS = PASTA_BASE / "saida_ml_entradas_video_v4_antiloss" / "04_v4_score_candidatos.csv.gz"

# Arquivos de saída
ARQUIVO_RESULTADOS = PASTA_SAIDA / "05_v4_otimizacao_A_resultados.csv.gz"
ARQUIVO_TOP = PASTA_SAIDA / "06_v4_A_top_resultados.csv"
ARQUIVO_MELHOR = PASTA_SAIDA / "07_v4_A_melhor_resumo.csv"
ARQUIVO_TRADES_MELHOR = PASTA_SAIDA / "08_v4_A_melhor_trades.csv.gz"


# ============================================================
# BUSCA EM TORNO DA CONFIGURAÇÃO A
# ============================================================

TAKE_FIXO = 50.5
STOP_FIXO = 117.0

GRID_PROB = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
    0.96,
]

GRID_SCORE_BUY = [
    0.70,
    0.72,
    0.74,
    0.76,
    0.78,
    0.80,
    0.82,
    0.84,
    0.86,
]

GRID_SCORE_SELL = [
    0.50,
    0.52,
    0.55,
    0.57,
    0.60,
    0.62,
    0.65,
    0.70,
    0.75,
    0.80,
    0.84,
    0.86,
]

GRID_DIFERENCA_MINIMA = [
    0.00,
    0.02,
    0.04,
    0.06,
    0.08,
    0.10,
]

GRID_MAX_TRADES_DIA = [
    1,
    2,
    3,
]

GRID_PARAR_APOS_LOSS = [
    True,
]

GRID_HORARIOS = [
    (3.0, 6.0),
    (3.0, 5.0),
    (3.0, 7.0),
    (4.0, 6.0),
    (2.0, 6.0),
]


# ============================================================
# FILTROS DESEJADOS
# ============================================================

MIN_TRADES_DESEJADO = 180
MIN_WINRATE_DESEJADO = 83.0
MIN_PF_DESEJADO = 2.20
MIN_LUCRO_DESEJADO = 5000.0


# ============================================================
# FUNÇÕES
# ============================================================

def carregar_csv(caminho: Path) -> pd.DataFrame:
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if str(caminho).lower().endswith(".csv.gz"):
        return pd.read_csv(caminho, compression="gzip")

    return pd.read_csv(caminho)


def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    print("\nColunas encontradas no arquivo:")
    print(df.columns.tolist())

    # ============================================================
    # DATA/HORA
    # ============================================================
    if "DataHora_SP" in df.columns:
        df["dt"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    elif "DataHora_Sinal_SP" in df.columns:
        df["dt"] = pd.to_datetime(df["DataHora_Sinal_SP"], errors="coerce")
    elif "dt_entrada" in df.columns:
        df["dt"] = pd.to_datetime(df["dt_entrada"], errors="coerce")
    else:
        raise ValueError("Não encontrei coluna de data/hora. Esperado: DataHora_SP.")

    df = df.dropna(subset=["dt"]).copy()

    df["Data"] = df["dt"].dt.date

    if "Hora_SP_Decimal" not in df.columns:
        df["Hora_SP_Decimal"] = (
            df["dt"].dt.hour +
            df["dt"].dt.minute / 60.0 +
            df["dt"].dt.second / 3600.0
        )

    # ============================================================
    # DIREÇÃO
    # ============================================================
    if "Direcao" not in df.columns:
        raise ValueError("Coluna obrigatória ausente: Direcao")

    df["Direcao"] = df["Direcao"].astype(str).str.upper().str.strip()

    df["Direcao"] = df["Direcao"].replace({
        "COMPRA": "BUY",
        "COMPRAR": "BUY",
        "LONG": "BUY",
        "VENDA": "SELL",
        "VENDER": "SELL",
        "SHORT": "SELL",
    })

    df = df[df["Direcao"].isin(["BUY", "SELL"])].copy()

    # ============================================================
    # SCORES E PROBABILIDADE
    # ============================================================
    for col in ["score_BUY", "score_SELL", "score_NONE", "prob_win_v4"]:
        if col not in df.columns:
            if col == "score_NONE":
                df[col] = 0.0
            else:
                raise ValueError(f"Coluna obrigatória ausente: {col}")

        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "score_direcao" not in df.columns:
        df["score_direcao"] = np.where(
            df["Direcao"] == "BUY",
            df["score_BUY"],
            df["score_SELL"]
        )

    if "score_oposto" not in df.columns:
        df["score_oposto"] = np.where(
            df["Direcao"] == "BUY",
            df["score_SELL"],
            df["score_BUY"]
        )

    if "score_diff" not in df.columns:
        df["score_diff"] = df["score_direcao"] - df["score_oposto"]

    df["score_direcao"] = pd.to_numeric(df["score_direcao"], errors="coerce").fillna(0.0)
    df["score_oposto"] = pd.to_numeric(df["score_oposto"], errors="coerce").fillna(0.0)
    df["score_diff"] = pd.to_numeric(df["score_diff"], errors="coerce").fillna(0.0)

    # ============================================================
    # RESULTADO STOP 117
    # ============================================================
    if "resultado_stop_117_0" in df.columns:
        df["resultado"] = df["resultado_stop_117_0"].astype(str).str.upper().str.strip()
    else:
        df["resultado"] = ""

    if "pontos_stop_117_0" in df.columns:
        df["pontos_original"] = pd.to_numeric(df["pontos_stop_117_0"], errors="coerce")
    else:
        df["pontos_original"] = np.nan

    if "runup_stop_117_0" in df.columns:
        df["runup"] = pd.to_numeric(df["runup_stop_117_0"], errors="coerce").fillna(0.0)
    else:
        df["runup"] = np.nan

    if "drawdown_stop_117_0" in df.columns:
        df["drawdown"] = pd.to_numeric(df["drawdown_stop_117_0"], errors="coerce").fillna(0.0)
    else:
        df["drawdown"] = np.nan

    df = df.sort_values("dt").reset_index(drop=True)

    print("\nTotal após preparar:", len(df))
    print("Período:", df["dt"].min(), "até", df["dt"].max())
    print("Direções:")
    print(df["Direcao"].value_counts())

    return df


def simular_resultado_trade(row, take_pontos: float, stop_pontos: float) -> tuple[str, float]:
    resultado = str(row.get("resultado", "")).upper().strip()

    if resultado in {"WIN", "GAIN", "TAKE", "TP"}:
        return "WIN", take_pontos

    if resultado in {"LOSS", "STOP", "SL"}:
        return "LOSS", -stop_pontos

    runup = row.get("runup", np.nan)
    drawdown = row.get("drawdown", np.nan)

    if pd.notna(runup) and pd.notna(drawdown):
        bateu_take = runup >= take_pontos
        bateu_stop = drawdown >= stop_pontos

        if bateu_take and not bateu_stop:
            return "WIN", take_pontos

        if bateu_stop and not bateu_take:
            return "LOSS", -stop_pontos

        if bateu_take and bateu_stop:
            return "LOSS", -stop_pontos

    return "NEUTRO", 0.0


def filtrar_config(
    df: pd.DataFrame,
    prob_win_min: float,
    score_buy_min: float,
    score_sell_min: float,
    diferenca_minima: float,
    hora_inicio: float,
    hora_fim: float,
) -> pd.DataFrame:

    filtro_hora = (
        (df["Hora_SP_Decimal"] >= hora_inicio) &
        (df["Hora_SP_Decimal"] < hora_fim)
    )

    filtro_prob = df["prob_win_v4"] >= prob_win_min

    filtro_buy = (
        (df["Direcao"] == "BUY") &
        (df["score_BUY"] >= score_buy_min)
    )

    filtro_sell = (
        (df["Direcao"] == "SELL") &
        (df["score_SELL"] >= score_sell_min)
    )

    filtro_diff = df["score_diff"] >= diferenca_minima

    filtrado = df[
        filtro_hora &
        filtro_prob &
        (filtro_buy | filtro_sell) &
        filtro_diff
    ].copy()

    return filtrado.sort_values("dt").reset_index(drop=True)


def aplicar_regras_dia(
    df: pd.DataFrame,
    take_pontos: float,
    stop_pontos: float,
    max_trades_dia: int,
    parar_apos_loss: bool,
) -> pd.DataFrame:

    trades = []

    for data, grupo in df.groupby("Data", sort=True):
        qtd_dia = 0
        teve_loss = False

        grupo = grupo.sort_values("dt")

        for _, row in grupo.iterrows():
            if qtd_dia >= max_trades_dia:
                break

            if parar_apos_loss and teve_loss:
                break

            resultado, pontos = simular_resultado_trade(row, take_pontos, stop_pontos)

            if resultado == "NEUTRO":
                continue

            r = row.copy()
            r["resultado_sim"] = resultado
            r["pontos_sim"] = pontos

            trades.append(r)

            qtd_dia += 1

            if resultado == "LOSS":
                teve_loss = True

    if not trades:
        return pd.DataFrame()

    return pd.DataFrame(trades).reset_index(drop=True)


def calcular_metricas(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "media_prob_win": 0.0,
            "min_prob_win": 0.0,
            "drawdown_medio_trade": 0.0,
            "drawdown_max_trade": 0.0,
            "runup_medio_trade": 0.0,
            "runup_max_trade": 0.0,
            "dias_operados": 0,
            "pior_dia_pontos": 0.0,
            "melhor_dia_pontos": 0.0,
        }

    total = len(trades)
    wins = int((trades["resultado_sim"] == "WIN").sum())
    losses = int((trades["resultado_sim"] == "LOSS").sum())

    lucro = float(trades["pontos_sim"].sum())
    winrate = wins / total * 100.0 if total > 0 else 0.0

    soma_gains = float(trades.loc[trades["pontos_sim"] > 0, "pontos_sim"].sum())
    soma_losses = float(abs(trades.loc[trades["pontos_sim"] < 0, "pontos_sim"].sum()))

    profit_factor = soma_gains / soma_losses if soma_losses > 0 else 999.0

    por_dia = trades.groupby("Data")["pontos_sim"].sum()

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "lucro_pontos": lucro,
        "profit_factor": profit_factor,
        "buy_total": int((trades["Direcao"] == "BUY").sum()),
        "sell_total": int((trades["Direcao"] == "SELL").sum()),
        "media_prob_win": float(trades["prob_win_v4"].mean()),
        "min_prob_win": float(trades["prob_win_v4"].min()),
        "drawdown_medio_trade": float(trades["drawdown"].mean()) if "drawdown" in trades.columns else 0.0,
        "drawdown_max_trade": float(trades["drawdown"].max()) if "drawdown" in trades.columns else 0.0,
        "runup_medio_trade": float(trades["runup"].mean()) if "runup" in trades.columns else 0.0,
        "runup_max_trade": float(trades["runup"].max()) if "runup" in trades.columns else 0.0,
        "dias_operados": int(trades["Data"].nunique()),
        "pior_dia_pontos": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia_pontos": float(por_dia.max()) if len(por_dia) else 0.0,
    }


def criar_config_key(
    stop_pontos,
    take_pontos,
    prob_win_min,
    max_trades_dia,
    parar_apos_loss,
    score_buy_min,
    score_sell_min,
    diferenca_minima,
    hora_inicio,
    hora_fim,
):
    return (
        f"stop={stop_pontos}|take={take_pontos}|prob={prob_win_min}|"
        f"maxdia={max_trades_dia}|paraloss={parar_apos_loss}|"
        f"buy={score_buy_min}|sell={score_sell_min}|diff={diferenca_minima}|"
        f"h={hora_inicio}-{hora_fim}"
    )


def rodar_otimizacao(df: pd.DataFrame):
    resultados = []
    melhor_trades = None
    melhor_score = -1e18
    melhor_config = None

    config_id = 0

    total_configs = (
        len(GRID_PROB) *
        len(GRID_SCORE_BUY) *
        len(GRID_SCORE_SELL) *
        len(GRID_DIFERENCA_MINIMA) *
        len(GRID_MAX_TRADES_DIA) *
        len(GRID_PARAR_APOS_LOSS) *
        len(GRID_HORARIOS)
    )

    print(f"\nTotal de combinações: {total_configs:,}")

    for prob_win_min in GRID_PROB:
        for score_buy_min in GRID_SCORE_BUY:
            for score_sell_min in GRID_SCORE_SELL:
                for diferenca_minima in GRID_DIFERENCA_MINIMA:
                    for max_trades_dia in GRID_MAX_TRADES_DIA:
                        for parar_apos_loss in GRID_PARAR_APOS_LOSS:
                            for hora_inicio, hora_fim in GRID_HORARIOS:

                                config_id += 1

                                candidatos = filtrar_config(
                                    df=df,
                                    prob_win_min=prob_win_min,
                                    score_buy_min=score_buy_min,
                                    score_sell_min=score_sell_min,
                                    diferenca_minima=diferenca_minima,
                                    hora_inicio=hora_inicio,
                                    hora_fim=hora_fim,
                                )

                                trades = aplicar_regras_dia(
                                    df=candidatos,
                                    take_pontos=TAKE_FIXO,
                                    stop_pontos=STOP_FIXO,
                                    max_trades_dia=max_trades_dia,
                                    parar_apos_loss=parar_apos_loss,
                                )

                                metricas = calcular_metricas(trades)

                                config_key = criar_config_key(
                                    stop_pontos=STOP_FIXO,
                                    take_pontos=TAKE_FIXO,
                                    prob_win_min=prob_win_min,
                                    max_trades_dia=max_trades_dia,
                                    parar_apos_loss=parar_apos_loss,
                                    score_buy_min=score_buy_min,
                                    score_sell_min=score_sell_min,
                                    diferenca_minima=diferenca_minima,
                                    hora_inicio=hora_inicio,
                                    hora_fim=hora_fim,
                                )

                                row = {
                                    "config_id": config_id,
                                    "config_key": config_key,
                                    "take_pontos": TAKE_FIXO,
                                    "stop_pontos": STOP_FIXO,
                                    "prob_win_min": prob_win_min,
                                    "max_trades_dia": max_trades_dia,
                                    "parar_apos_loss": parar_apos_loss,
                                    "score_buy_min": score_buy_min,
                                    "score_sell_min": score_sell_min,
                                    "diferenca_minima": diferenca_minima,
                                    "hora_inicio": hora_inicio,
                                    "hora_fim": hora_fim,
                                    **metricas,
                                }

                                resultados.append(row)

                                total_trades = metricas["total_trades"]
                                winrate = metricas["winrate"]
                                pf = metricas["profit_factor"]
                                lucro = metricas["lucro_pontos"]
                                pior_dia = abs(metricas["pior_dia_pontos"])

                                penalidade_poucos_trades = 0.0
                                if total_trades < MIN_TRADES_DESEJADO:
                                    penalidade_poucos_trades = (MIN_TRADES_DESEJADO - total_trades) * 25.0

                                penalidade_dd = pior_dia * 2.0

                                score = (
                                    lucro
                                    + pf * 900.0
                                    + winrate * 25.0
                                    + total_trades * 3.0
                                    - penalidade_poucos_trades
                                    - penalidade_dd
                                )

                                if (
                                    total_trades >= 100 and
                                    lucro > 0 and
                                    pf > 1.5 and
                                    score > melhor_score
                                ):
                                    melhor_score = score
                                    melhor_config = row
                                    melhor_trades = trades.copy()

                                if config_id % 500 == 0:
                                    print(f"Processadas {config_id:,}/{total_configs:,} configs...")

    resultados_df = pd.DataFrame(resultados)

    return resultados_df, melhor_config, melhor_trades


def selecionar_top(resultados_df: pd.DataFrame) -> pd.DataFrame:
    df = resultados_df.copy()

    df["passa_filtro_frequencia"] = df["total_trades"] >= MIN_TRADES_DESEJADO
    df["passa_filtro_winrate"] = df["winrate"] >= MIN_WINRATE_DESEJADO
    df["passa_filtro_pf"] = df["profit_factor"] >= MIN_PF_DESEJADO
    df["passa_filtro_lucro"] = df["lucro_pontos"] >= MIN_LUCRO_DESEJADO

    df["passa_todos_filtros"] = (
        df["passa_filtro_frequencia"] &
        df["passa_filtro_winrate"] &
        df["passa_filtro_pf"] &
        df["passa_filtro_lucro"]
    )

    df["score_operacional"] = (
        df["lucro_pontos"] * 1.0
        + df["profit_factor"] * 1000.0
        + df["winrate"] * 35.0
        + df["total_trades"] * 6.0
        - df["losses"] * 25.0
    )

    top_filtrado = df[df["passa_todos_filtros"]].copy()

    if len(top_filtrado) > 0:
        top = top_filtrado.sort_values(
            [
                "score_operacional",
                "lucro_pontos",
                "profit_factor",
                "winrate",
                "total_trades",
            ],
            ascending=[False, False, False, False, False],
        )
    else:
        top = df.sort_values(
            [
                "score_operacional",
                "lucro_pontos",
                "profit_factor",
                "winrate",
                "total_trades",
            ],
            ascending=[False, False, False, False, False],
        )

    return top.head(500).reset_index(drop=True)


def salvar_resultados(resultados_df, top_df, melhor_config, melhor_trades):
    resultados_df.to_csv(ARQUIVO_RESULTADOS, index=False, compression="gzip")
    top_df.to_csv(ARQUIVO_TOP, index=False)

    melhor_df = pd.DataFrame([melhor_config])
    melhor_df.to_csv(ARQUIVO_MELHOR, index=False)

    if melhor_trades is not None and not melhor_trades.empty:
        melhor_trades.to_csv(ARQUIVO_TRADES_MELHOR, index=False, compression="gzip")

    print("\nArquivos gerados:")
    print(ARQUIVO_RESULTADOS)
    print(ARQUIVO_TOP)
    print(ARQUIVO_MELHOR)
    print(ARQUIVO_TRADES_MELHOR)


def imprimir_resultados(melhor_config, top_df):
    print("\n=====================================================")
    print("MELHOR CONFIGURAÇÃO ENCONTRADA")
    print("=====================================================")
    print(pd.Series(melhor_config))

    print("\n=====================================================")
    print("TOP 30")
    print("=====================================================")

    colunas_mostrar = [
        "config_id",
        "take_pontos",
        "stop_pontos",
        "prob_win_min",
        "max_trades_dia",
        "parar_apos_loss",
        "score_buy_min",
        "score_sell_min",
        "diferenca_minima",
        "hora_inicio",
        "hora_fim",
        "total_trades",
        "wins",
        "losses",
        "winrate",
        "lucro_pontos",
        "profit_factor",
        "buy_total",
        "sell_total",
        "pior_dia_pontos",
        "melhor_dia_pontos",
        "passa_todos_filtros",
    ]

    colunas_existentes = [c for c in colunas_mostrar if c in top_df.columns]

    print(top_df[colunas_existentes].head(30).to_string(index=False))


def main():
    warnings.filterwarnings("ignore")

    print("Arquivo usado:")
    print(ARQUIVO_ENTRADAS)

    df = carregar_csv(ARQUIVO_ENTRADAS)
    df = preparar_dataframe(df)

    print("\nRodando otimização em torno da Configuração A...")

    resultados_df, melhor_config, melhor_trades = rodar_otimizacao(df)

    top_df = selecionar_top(resultados_df)

    salvar_resultados(resultados_df, top_df, melhor_config, melhor_trades)

    imprimir_resultados(melhor_config, top_df)


if __name__ == "__main__":
    main()