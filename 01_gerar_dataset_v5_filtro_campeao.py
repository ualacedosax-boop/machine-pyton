from pathlib import Path
import warnings

import numpy as np
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

PASTA_SAIDA = BASE_DIR / "saida_v5_filtro_campeao"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_DATASET_2025 = PASTA_SAIDA / "01_dataset_v5_campeao_2025.csv.gz"
ARQ_DATASET_2026 = PASTA_SAIDA / "02_dataset_v5_campeao_2026.csv.gz"
ARQ_DATASET_TUDO = PASTA_SAIDA / "03_dataset_v5_campeao_2025_2026.csv.gz"
ARQ_RESUMO = PASTA_SAIDA / "04_resumo_dataset_v5.csv"
ARQ_FEATURES_SUGERIDAS = PASTA_SAIDA / "05_features_sugeridas_v5.txt"


# ============================================================
# CONFIGURAÇÃO CAMPEÃ V4
# ============================================================

TAKE_PONTOS = 50.5
STOP_PONTOS = 117.0

PROB_WIN_MIN = 0.60
SCORE_BUY_MIN = 0.74
SCORE_SELL_MIN = 0.50
DIFERENCA_MINIMA = 0.00

HORA_INICIO = 2.0
HORA_FIM = 6.0

MAX_TRADES_DIA = 3
PARAR_APOS_LOSS = True

MAX_CANDLES_FUTURO = 720

BLOQUEAR_0430_0444 = True
HORA_BLOQUEIO_INICIO = 4.5
HORA_BLOQUEIO_FIM = 4.75


# ============================================================
# LOCALIZAR CANDLES 2025
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
# APLICAR CONFIG CAMPEÃ
# ============================================================

def aplicar_config_campea(df):
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

    out = pd.DataFrame(trades).reset_index(drop=True)

    return out


# ============================================================
# FEATURES EXTRAS PARA V5
# ============================================================

def adicionar_features_v5(df):
    if df.empty:
        return df

    out = df.copy()

    out["DataHora_SP"] = pd.to_datetime(out["DataHora_SP"], errors="coerce")
    out["Ano"] = out["DataHora_SP"].dt.year
    out["AnoMes"] = out["DataHora_SP"].dt.strftime("%Y-%m")
    out["Hora"] = out["DataHora_SP"].dt.hour
    out["Minuto"] = out["DataHora_SP"].dt.minute
    out["Bloco_15m"] = (
        out["DataHora_SP"].dt.hour.astype(str).str.zfill(2)
        + ":"
        + ((out["DataHora_SP"].dt.minute // 15) * 15).astype(str).str.zfill(2)
    )

    out["eh_hora_3"] = (out["Hora"] == 3).astype(int)
    out["eh_hora_4"] = (out["Hora"] == 4).astype(int)
    out["eh_0348"] = (out["DataHora_SP"].dt.strftime("%H:%M") == "03:48").astype(int)
    out["eh_0350"] = (out["DataHora_SP"].dt.strftime("%H:%M") == "03:50").astype(int)
    out["eh_0450"] = (out["DataHora_SP"].dt.strftime("%H:%M") == "04:50").astype(int)

    out["direcao_num"] = np.where(out["Direcao"] == "BUY", 1, -1)

    out["score_direcao_calc"] = np.where(
        out["Direcao"] == "BUY",
        out["score_BUY"],
        out["score_SELL"]
    )

    out["score_oposto_calc"] = np.where(
        out["Direcao"] == "BUY",
        out["score_SELL"],
        out["score_BUY"]
    )

    out["score_diff_calc"] = out["score_direcao_calc"] - out["score_oposto_calc"]

    out["limite_direcao"] = np.where(
        out["Direcao"] == "BUY",
        SCORE_BUY_MIN,
        SCORE_SELL_MIN
    )

    out["forca_score_pct"] = (out["score_direcao_calc"] / out["limite_direcao"]) * 100.0
    out["folga_score"] = out["score_direcao_calc"] - out["limite_direcao"]
    out["folga_prob_v4"] = out["prob_win_v4"] - PROB_WIN_MIN

    out["folga_buy"] = out["score_BUY"] - SCORE_BUY_MIN
    out["folga_sell"] = out["score_SELL"] - SCORE_SELL_MIN

    out["target_v5_win"] = np.where(out["resultado_stop_117_0"] == "WIN", 1, 0)
    out["pontos_v5"] = out["pontos_stop_117_0"]

    return out


# ============================================================
# RESUMO
# ============================================================

def resumir(df, nome):
    if df.empty:
        return {
            "base": nome,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "profit_factor": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "meses": 0,
        }

    total = len(df)
    wins = int((df["target_v5_win"] == 1).sum())
    losses = int((df["target_v5_win"] == 0).sum())
    lucro = float(df["pontos_v5"].sum())

    ganhos = df.loc[df["pontos_v5"] > 0, "pontos_v5"].sum()
    perdas = abs(df.loc[df["pontos_v5"] < 0, "pontos_v5"].sum())
    pf = ganhos / perdas if perdas > 0 else 999.0

    return {
        "base": nome,
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": wins / total * 100 if total else 0.0,
        "lucro_pontos": lucro,
        "profit_factor": pf,
        "buy_total": int((df["Direcao"] == "BUY").sum()),
        "sell_total": int((df["Direcao"] == "SELL").sum()),
        "meses": int(df["AnoMes"].nunique()) if "AnoMes" in df.columns else 0,
        "media_prob_win_v4": float(df["prob_win_v4"].mean()),
        "min_prob_win_v4": float(df["prob_win_v4"].min()),
        "media_forca_score_pct": float(df["forca_score_pct"].mean()),
    }


# ============================================================
# PIPELINE DE UM ANO
# ============================================================

def gerar_dataset_ano(arquivo_candles, ano_nome):
    print("\n=====================================================")
    print(f"GERANDO DATASET V5 - {ano_nome}")
    print("=====================================================")

    print("\nArquivo de candles:")
    print(arquivo_candles)

    candles = base.carregar_csv(arquivo_candles)
    print("Candles carregados:", len(candles))

    print("\nCalculando features...")
    features = base.calcular_features(candles)
    print("Features calculadas:", len(features))

    print("\nAplicando modelo V3...")
    score_v3 = base.aplicar_modelo_v3(features)

    if score_v3.empty:
        print("Nenhum candidato V3.")
        return pd.DataFrame()

    print("\nAplicando modelo V4...")
    score_v4 = base.aplicar_modelo_v4(score_v3)

    if score_v4.empty:
        print("Nenhum candidato V4.")
        return pd.DataFrame()

    print("\nSimulando Take/Stop...")
    score_resultado = base.adicionar_resultados_take_stop(score_v4, features)

    if score_resultado.empty:
        print("Nenhum candidato com resultado.")
        return pd.DataFrame()

    print("\nAplicando configuração campeã...")
    trades_campeoes = aplicar_config_campea(score_resultado)

    if trades_campeoes.empty:
        print("Nenhum trade campeão.")
        return pd.DataFrame()

    trades_campeoes = adicionar_features_v5(trades_campeoes)
    trades_campeoes["base_ano"] = ano_nome

    print("\nResumo do ano:")
    print(pd.Series(resumir(trades_campeoes, ano_nome)).to_string())

    return trades_campeoes


# ============================================================
# FEATURES SUGERIDAS PARA TREINO V5
# ============================================================

def salvar_features_sugeridas(df):
    excluir_prefixos = [
        "resultado_",
        "pontos_",
        "target_",
        "dt_saida",
        "indice_saida",
        "runup_stop",
        "drawdown_stop",
        "DataHora",
        "Data",
        "AnoMes",
        "base_ano",
    ]

    excluir_exatos = {
        "resultado_stop_117_0",
        "pontos_stop_117_0",
        "target_win_stop_117_0",
        "pontos_v5",
        "target_v5_win",
        "dt_saida_stop_117_0",
        "indice_saida_stop_117_0",
    }

    candidatas = []

    for col in df.columns:
        if col in excluir_exatos:
            continue

        if any(col.startswith(pref) for pref in excluir_prefixos):
            continue

        if df[col].dtype.kind in "biufc":
            candidatas.append(col)

    candidatas = sorted(set(candidatas))

    with open(ARQ_FEATURES_SUGERIDAS, "w", encoding="utf-8") as f:
        for col in candidatas:
            f.write(col + "\n")

    print("\nFeatures sugeridas para V5 salvas em:")
    print(ARQ_FEATURES_SUGERIDAS)
    print("Total:", len(candidatas))


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("01 - GERAR DATASET V5 FILTRO CAMPEÃO")
    print("=====================================================")

    print("\nConfiguração campeã usada:")
    print(f"Take: {TAKE_PONTOS}")
    print(f"Stop: {STOP_PONTOS}")
    print(f"Prob min: {PROB_WIN_MIN}")
    print(f"BUY min: {SCORE_BUY_MIN}")
    print(f"SELL min: {SCORE_SELL_MIN}")
    print(f"Hora: {HORA_INICIO} até {HORA_FIM}")
    print(f"Bloquear 04:30-04:44: {BLOQUEAR_0430_0444}")
    print(f"Max trades/dia: {MAX_TRADES_DIA}")
    print(f"Parar após loss: {PARAR_APOS_LOSS}")

    arquivo_2025 = localizar_candles_2025()
    arquivo_2026 = ARQUIVO_CANDLES_2026

    dataset_2025 = gerar_dataset_ano(arquivo_2025, "2025")
    dataset_2026 = gerar_dataset_ano(arquivo_2026, "2026")

    if not dataset_2025.empty:
        dataset_2025.to_csv(ARQ_DATASET_2025, index=False, compression="gzip")
        print("\nDataset 2025 salvo:")
        print(ARQ_DATASET_2025)

    if not dataset_2026.empty:
        dataset_2026.to_csv(ARQ_DATASET_2026, index=False, compression="gzip")
        print("\nDataset 2026 salvo:")
        print(ARQ_DATASET_2026)

    datasets = [d for d in [dataset_2025, dataset_2026] if not d.empty]

    if not datasets:
        print("\nERRO: nenhum dataset foi gerado.")
        return

    dataset_tudo = pd.concat(datasets, ignore_index=True)
    dataset_tudo = dataset_tudo.sort_values("DataHora_SP").reset_index(drop=True)

    dataset_tudo.to_csv(ARQ_DATASET_TUDO, index=False, compression="gzip")

    print("\nDataset consolidado salvo:")
    print(ARQ_DATASET_TUDO)

    resumo = pd.DataFrame([
        resumir(dataset_2025, "2025"),
        resumir(dataset_2026, "2026"),
        resumir(dataset_tudo, "2025_2026"),
    ])

    resumo.to_csv(ARQ_RESUMO, index=False)

    print("\n=====================================================")
    print("RESUMO DATASET V5")
    print("=====================================================")
    print(resumo.to_string(index=False))

    salvar_features_sugeridas(dataset_tudo)

    print("\nArquivos gerados:")
    print(ARQ_DATASET_2025)
    print(ARQ_DATASET_2026)
    print(ARQ_DATASET_TUDO)
    print(ARQ_RESUMO)
    print(ARQ_FEATURES_SUGERIDAS)

    print("\nPróxima etapa:")
    print("Treinar a V5 usando 2025 como treino e 2026 como validação/teste fora da amostra.")


if __name__ == "__main__":
    main()