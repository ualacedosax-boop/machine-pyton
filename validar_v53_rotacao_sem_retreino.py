import json
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_V53 = BASE_DIR / "saida_v5_3_validacao_2025_teste_2026"

ARQUIVO_V53_VALIDACAO_2025 = PASTA_V53 / "05_predicoes_validacao_2025_v5_3.csv.gz"
ARQUIVO_V53_TESTE_2026 = PASTA_V53 / "06_predicoes_teste_2026_v5_3.csv.gz"

# MODO:
# "2025"  = somente validação 2025
# "2026"  = somente teste 2026
# "AMBOS" = junta 2025 + 2026
MODO = "AMBOS"

# Converter pontos para dólar do Mini NQ.
# MNQ micro = 2 dólares por ponto.
# NQ mini cheio = 20 dólares por ponto.
VALOR_POR_PONTO_NQ = 20.0

DATA_EXECUCAO = datetime.now().strftime("%Y%m%d_%H%M%S")

PASTA_SAIDA = (
    BASE_DIR
    / "validacao_v53_rotacao_sem_retreino"
    / f"rodada_v53_OFICIAL_aceito_true_{DATA_EXECUCAO}"
)
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_TRADES_NORMALIZADOS = PASTA_SAIDA / "01_v53_oficial_trades_normalizados.csv.gz"
ARQ_RESUMO_GERAL = PASTA_SAIDA / "02_v53_oficial_resumo_geral.csv"
ARQ_RESUMO_FONTE = PASTA_SAIDA / "03_v53_oficial_resumo_por_fonte.csv"
ARQ_RESUMO_MENSAL = PASTA_SAIDA / "04_v53_oficial_resumo_mensal.csv"
ARQ_RESUMO_ROTACOES = PASTA_SAIDA / "05_v53_oficial_resumo_rotacoes.csv"
ARQ_RESUMO_ROTACOES_FONTE = PASTA_SAIDA / "06_v53_oficial_resumo_rotacoes_por_fonte.csv"
ARQ_CONFIG = PASTA_SAIDA / "00_config_execucao.json"
ARQ_RELATORIO_TXT = PASTA_SAIDA / "07_relatorio_v53_oficial_rotacao_sem_retreino.txt"


# ============================================================
# ROTAÇÕES
# ============================================================

ROTACOES = {
    "ROTACAO_A": [3, 6, 9, 12],
    "ROTACAO_B": [2, 5, 8, 11],
    "ROTACAO_C": [1, 4, 7, 10],
}


# ============================================================
# BARRA DE PROGRESSO
# ============================================================

def barra(iteravel, desc="Processando"):
    if tqdm is not None:
        return tqdm(iteravel, desc=desc, unit="item")
    return iteravel


# ============================================================
# LEITURA
# ============================================================

def ler_csv(caminho: Path) -> pd.DataFrame:
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    if str(caminho).lower().endswith(".gz"):
        return pd.read_csv(caminho, compression="gzip")

    return pd.read_csv(caminho)


def carregar_arquivos_v53() -> pd.DataFrame:
    arquivos = []

    modo = MODO.upper().strip()

    if modo == "2025":
        arquivos.append(("VALIDACAO_2025", ARQUIVO_V53_VALIDACAO_2025))

    elif modo == "2026":
        arquivos.append(("TESTE_2026", ARQUIVO_V53_TESTE_2026))

    elif modo == "AMBOS":
        arquivos.append(("VALIDACAO_2025", ARQUIVO_V53_VALIDACAO_2025))
        arquivos.append(("TESTE_2026", ARQUIVO_V53_TESTE_2026))

    else:
        raise ValueError("MODO inválido. Use: 2025, 2026 ou AMBOS.")

    dfs = []

    for fonte, caminho in arquivos:
        print(f"\nLendo {fonte}:")
        print(caminho)

        df = ler_csv(caminho)
        df["Fonte"] = fonte
        dfs.append(df)

        print(f"Linhas lidas {fonte}: {len(df)}")

        if "aceito_v5_3" in df.columns:
            print("\nDistribuição aceito_v5_3:")
            print(df["aceito_v5_3"].value_counts(dropna=False))
        else:
            print("\nATENÇÃO: coluna aceito_v5_3 não encontrada.")

    if not dfs:
        raise RuntimeError("Nenhum arquivo foi carregado.")

    return pd.concat(dfs, ignore_index=True)


# ============================================================
# NORMALIZAÇÃO V5.3 OFICIAL
# ============================================================

def transformar_bool_aceito(serie: pd.Series) -> pd.Series:
    """
    Converte aceito_v5_3 para booleano.
    Aceita True, 1, SIM, YES, S, VERDADEIRO.
    """
    s = serie.astype(str).str.strip().str.upper()

    return s.isin([
        "TRUE",
        "1",
        "SIM",
        "YES",
        "S",
        "VERDADEIRO",
        "V",
    ])


def validar_colunas_obrigatorias(df: pd.DataFrame):
    obrigatorias = [
        "DataHora_SP",
        "Direcao",
        "aceito_v5_3",
        "pontos_v5",
        "target_v5_win",
        "prob_v5_3",
        "threshold_usado",
    ]

    faltantes = [c for c in obrigatorias if c not in df.columns]

    if faltantes:
        print("\nColunas encontradas no arquivo:")
        print(list(df.columns))
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}")


def definir_rotacao(mes: int) -> str:
    for nome, meses in ROTACOES.items():
        if int(mes) in meses:
            return nome
    return "SEM_ROTACAO"


def normalizar_trades_v53_oficial(df: pd.DataFrame) -> pd.DataFrame:
    """
    Este é o ponto mais importante:
    A V5.3 oficial deve considerar somente aceito_v5_3 == True.
    O resultado correto é pontos_v5.
    """

    validar_colunas_obrigatorias(df)

    df = df.copy()

    df["aceito_v5_3_bool"] = transformar_bool_aceito(df["aceito_v5_3"])

    total_linhas = len(df)
    total_aceitos = int(df["aceito_v5_3_bool"].sum())

    print("\nFiltro oficial da V5.3:")
    print(f"Linhas totais antes do filtro: {total_linhas}")
    print(f"Linhas aceitas aceito_v5_3=True: {total_aceitos}")

    df = df[df["aceito_v5_3_bool"]].copy()

    if df.empty:
        raise RuntimeError("Nenhuma linha com aceito_v5_3=True foi encontrada.")

    out = pd.DataFrame()

    out["Fonte"] = df["Fonte"].astype(str)
    out["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    out["Direcao"] = df["Direcao"].astype(str).str.upper()

    out["prob_v5_3"] = pd.to_numeric(df["prob_v5_3"], errors="coerce")
    out["threshold_usado"] = pd.to_numeric(df["threshold_usado"], errors="coerce")

    out["Pontos"] = pd.to_numeric(df["pontos_v5"], errors="coerce")
    out["target_v5_win"] = pd.to_numeric(df["target_v5_win"], errors="coerce")

    out["Resultado"] = np.where(out["Pontos"] > 0, "WIN", "LOSS")

    # Campos auxiliares, se existirem
    campos_opcionais = [
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "score_direcao",
        "score_oposto",
        "score_diff",
        "prob_win_v4",
        "pontos_stop_117_0",
        "resultado_stop_117_0",
        "runup_stop_117_0",
        "drawdown_stop_117_0",
        "Bloco_15m",
        "Hora_SP_Decimal",
    ]

    for col in campos_opcionais:
        if col in df.columns:
            out[col] = df[col].values

    out = out.dropna(subset=["DataHora_SP", "Pontos"]).copy()
    out = out[out["Pontos"] != 0].copy()

    out["Ano"] = out["DataHora_SP"].dt.year
    out["Mes"] = out["DataHora_SP"].dt.month
    out["AnoMes"] = out["DataHora_SP"].dt.strftime("%Y-%m")
    out["Data"] = out["DataHora_SP"].dt.date
    out["Hora"] = out["DataHora_SP"].dt.hour
    out["Minuto"] = out["DataHora_SP"].dt.minute

    if "Bloco_15m" not in out.columns:
        out["Bloco_15m"] = (
            out["Hora"].astype(str).str.zfill(2)
            + ":"
            + ((out["Minuto"] // 15) * 15).astype(str).str.zfill(2)
        )

    out["Rotacao"] = out["Mes"].apply(definir_rotacao)

    out = out.sort_values(["Fonte", "DataHora_SP"]).reset_index(drop=True)

    return out


# ============================================================
# MÉTRICAS
# ============================================================

def calcular_drawdown(pontos):
    pontos = pd.Series(pontos).fillna(0.0)
    equity = pontos.cumsum()
    topo = equity.cummax()
    dd = equity - topo

    if len(dd) == 0:
        return 0.0

    return float(dd.min())


def resumir(df: pd.DataFrame, grupo: str) -> dict:
    if df.empty:
        return {
            "grupo": grupo,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "lucro_pontos": 0.0,
            "lucro_dolar_nq": 0.0,
            "profit_factor": 0.0,
            "drawdown_trades_pontos": 0.0,
            "drawdown_dolar_nq": 0.0,
            "dias_operados": 0,
            "media_trades_por_dia": 0.0,
            "pior_dia_pontos": 0.0,
            "melhor_dia_pontos": 0.0,
            "buy_total": 0,
            "sell_total": 0,
            "media_pontos_trade": 0.0,
            "media_pontos_10_trades": 0.0,
            "media_dolar_trade_nq": 0.0,
            "media_dolar_10_trades_nq": 0.0,
            "media_prob_v5_3": 0.0,
            "min_prob_v5_3": 0.0,
            "max_prob_v5_3": 0.0,
        }

    trades = len(df)
    wins = int((df["Resultado"] == "WIN").sum())
    losses = int((df["Resultado"] == "LOSS").sum())

    lucro = float(df["Pontos"].sum())

    ganhos = float(df.loc[df["Pontos"] > 0, "Pontos"].sum())
    perdas = abs(float(df.loc[df["Pontos"] < 0, "Pontos"].sum()))

    pf = ganhos / perdas if perdas > 0 else 999.0

    dd = calcular_drawdown(df["Pontos"])

    dias_operados = int(df["Data"].nunique())
    media_dia = trades / dias_operados if dias_operados else 0.0

    por_dia = df.groupby("Data")["Pontos"].sum()

    direcao = df["Direcao"].astype(str).str.upper()
    buy_total = int((direcao == "BUY").sum())
    sell_total = int((direcao == "SELL").sum())

    media_trade = lucro / trades if trades else 0.0

    return {
        "grupo": grupo,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "winrate": wins / trades * 100 if trades else 0.0,
        "lucro_pontos": lucro,
        "lucro_dolar_nq": lucro * VALOR_POR_PONTO_NQ,
        "profit_factor": pf,
        "drawdown_trades_pontos": dd,
        "drawdown_dolar_nq": dd * VALOR_POR_PONTO_NQ,
        "dias_operados": dias_operados,
        "media_trades_por_dia": media_dia,
        "pior_dia_pontos": float(por_dia.min()) if len(por_dia) else 0.0,
        "melhor_dia_pontos": float(por_dia.max()) if len(por_dia) else 0.0,
        "buy_total": buy_total,
        "sell_total": sell_total,
        "media_pontos_trade": media_trade,
        "media_pontos_10_trades": media_trade * 10,
        "media_dolar_trade_nq": media_trade * VALOR_POR_PONTO_NQ,
        "media_dolar_10_trades_nq": media_trade * 10 * VALOR_POR_PONTO_NQ,
        "media_prob_v5_3": float(df["prob_v5_3"].mean()),
        "min_prob_v5_3": float(df["prob_v5_3"].min()),
        "max_prob_v5_3": float(df["prob_v5_3"].max()),
    }


def gerar_resumo_geral(trades: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([resumir(trades, "GERAL")])


def gerar_resumo_por_fonte(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for fonte, g in barra(list(trades.groupby("Fonte")), desc="Resumo por fonte"):
        r = resumir(g, fonte)
        r["Fonte"] = fonte
        linhas.append(r)

    return pd.DataFrame(linhas)


def gerar_resumo_mensal(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for (fonte, anomes), g in barra(list(trades.groupby(["Fonte", "AnoMes"])), desc="Resumo mensal"):
        r = resumir(g, f"{fonte}_{anomes}")
        r["Fonte"] = fonte
        r["AnoMes"] = anomes
        r["Ano"] = int(g["Ano"].iloc[0])
        r["Mes"] = int(g["Mes"].iloc[0])
        linhas.append(r)

    return pd.DataFrame(linhas)


def gerar_resumo_rotacoes(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for rotacao, g in barra(list(trades.groupby("Rotacao")), desc="Resumo rotações"):
        r = resumir(g, rotacao)
        r["Rotacao"] = rotacao
        r["Meses_Rotacao"] = ",".join(str(x) for x in ROTACOES.get(rotacao, []))
        linhas.append(r)

    return pd.DataFrame(linhas)


def gerar_resumo_rotacoes_fonte(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for (fonte, rotacao), g in barra(list(trades.groupby(["Fonte", "Rotacao"])), desc="Resumo rotação/fonte"):
        r = resumir(g, f"{fonte}_{rotacao}")
        r["Fonte"] = fonte
        r["Rotacao"] = rotacao
        r["Meses_Rotacao"] = ",".join(str(x) for x in ROTACOES.get(rotacao, []))
        linhas.append(r)

    return pd.DataFrame(linhas)


def gerar_resumo_horario(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for (fonte, hora), g in barra(list(trades.groupby(["Fonte", "Hora"])), desc="Resumo horário"):
        r = resumir(g, f"{fonte}_HORA_{hora}")
        r["Fonte"] = fonte
        r["Hora"] = hora
        linhas.append(r)

    return pd.DataFrame(linhas)


def gerar_resumo_bloco_15m(trades: pd.DataFrame) -> pd.DataFrame:
    linhas = []

    for (fonte, bloco), g in barra(list(trades.groupby(["Fonte", "Bloco_15m"])), desc="Resumo bloco 15m"):
        r = resumir(g, f"{fonte}_BLOCO_{bloco}")
        r["Fonte"] = fonte
        r["Bloco_15m"] = bloco
        linhas.append(r)

    return pd.DataFrame(linhas)


# ============================================================
# RELATÓRIO
# ============================================================

def salvar_config():
    config = {
        "modo": MODO,
        "base_dir": str(BASE_DIR),
        "pasta_v53": str(PASTA_V53),
        "arquivo_validacao_2025": str(ARQUIVO_V53_VALIDACAO_2025),
        "arquivo_teste_2026": str(ARQUIVO_V53_TESTE_2026),
        "pasta_saida": str(PASTA_SAIDA),
        "rotacoes": ROTACOES,
        "valor_por_ponto_nq": VALOR_POR_PONTO_NQ,
        "data_execucao": DATA_EXECUCAO,
        "observacao": (
            "Validacao por rotacao sem retreino. "
            "Filtra somente V5.3 oficial: aceito_v5_3=True. "
            "Usa pontos_v5 como resultado."
        ),
    }

    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def salvar_relatorio(
    trades,
    resumo_geral,
    resumo_fonte,
    resumo_mensal,
    resumo_rotacoes,
    resumo_rotacoes_fonte,
    resumo_horario,
    resumo_bloco,
):
    linhas = []

    def add(x=""):
        linhas.append(str(x))

    add("=" * 100)
    add("RELATÓRIO V5.3 OFICIAL - ROTAÇÃO SEM RETREINO")
    add("=" * 100)
    add("")
    add("IMPORTANTE:")
    add("Este script NÃO retreina a V5.3.")
    add("Este script NÃO altera o modelo.")
    add("Este script NÃO altera a lógica.")
    add("Ele filtra somente aceito_v5_3=True e usa pontos_v5.")
    add("")
    add(f"MODO: {MODO}")
    add(f"Data execução: {DATA_EXECUCAO}")
    add(f"Pasta saída: {PASTA_SAIDA}")
    add(f"Valor por ponto NQ usado: US$ {VALOR_POR_PONTO_NQ:.2f}")
    add("")

    add("=" * 100)
    add("RESUMO GERAL")
    add("=" * 100)
    add(resumo_geral.T.to_string())

    add("")
    add("=" * 100)
    add("RESUMO POR FONTE")
    add("=" * 100)
    add(resumo_fonte.to_string(index=False))

    add("")
    add("=" * 100)
    add("RESUMO POR ROTAÇÃO")
    add("=" * 100)
    add(resumo_rotacoes.to_string(index=False))

    add("")
    add("=" * 100)
    add("RESUMO POR ROTAÇÃO E FONTE")
    add("=" * 100)
    add(resumo_rotacoes_fonte.to_string(index=False))

    add("")
    add("=" * 100)
    add("RESUMO MENSAL")
    add("=" * 100)
    add(resumo_mensal.to_string(index=False))

    add("")
    add("=" * 100)
    add("RESUMO POR HORÁRIO")
    add("=" * 100)
    add(resumo_horario.to_string(index=False))

    add("")
    add("=" * 100)
    add("RESUMO POR BLOCO 15M")
    add("=" * 100)
    add(resumo_bloco.to_string(index=False))

    add("")
    add("=" * 100)
    add("CHECAGEM DE MESES NEGATIVOS")
    add("=" * 100)

    if not resumo_mensal.empty:
        meses_negativos = resumo_mensal[resumo_mensal["lucro_pontos"] < 0].copy()
        meses_positivos = resumo_mensal[resumo_mensal["lucro_pontos"] > 0].copy()

        add(f"Meses positivos: {len(meses_positivos)}")
        add(f"Meses negativos: {len(meses_negativos)}")

        if len(meses_negativos):
            add("")
            add("Meses negativos:")
            add(
                meses_negativos[
                    [
                        "Fonte",
                        "AnoMes",
                        "trades",
                        "wins",
                        "losses",
                        "winrate",
                        "lucro_pontos",
                        "profit_factor",
                        "drawdown_trades_pontos",
                    ]
                ].to_string(index=False)
            )
        else:
            add("Nenhum mês negativo encontrado.")

    add("")
    add("=" * 100)
    add("CHECAGEM DE ROTAÇÕES NEGATIVAS")
    add("=" * 100)

    if not resumo_rotacoes_fonte.empty:
        rot_neg = resumo_rotacoes_fonte[resumo_rotacoes_fonte["lucro_pontos"] < 0].copy()

        add(f"Rotações negativas por fonte: {len(rot_neg)}")

        if len(rot_neg):
            add(rot_neg.to_string(index=False))
        else:
            add("Nenhuma rotação negativa por fonte encontrada.")

    texto = "\n".join(linhas)

    with open(ARQ_RELATORIO_TXT, "w", encoding="utf-8") as f:
        f.write(texto)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 100)
    print("VALIDAÇÃO V5.3 OFICIAL - ROTAÇÃO SEM RETREINO")
    print("=" * 100)

    print("\nMODO:", MODO)

    print("\nPasta V5.3:")
    print(PASTA_V53)

    print("\nArquivos que serão usados:")
    if MODO.upper() in ["2025", "AMBOS"]:
        print("2025:", ARQUIVO_V53_VALIDACAO_2025)

    if MODO.upper() in ["2026", "AMBOS"]:
        print("2026:", ARQUIVO_V53_TESTE_2026)

    print("\nPasta de saída:")
    print(PASTA_SAIDA)

    print("\nATENÇÃO:")
    print("Este script NÃO retreina.")
    print("Este script NÃO altera o modelo.")
    print("Este script NÃO altera a lógica da V5.3.")
    print("Ele considera somente a V5.3 oficial: aceito_v5_3=True.")
    print("Resultado usado: pontos_v5.")

    salvar_config()

    df_original = carregar_arquivos_v53()

    print("\nNormalizando trades oficiais da V5.3...")
    trades = normalizar_trades_v53_oficial(df_original)

    if trades.empty:
        raise RuntimeError("Nenhum trade oficial foi encontrado após filtro aceito_v5_3=True.")

    print("\nTrades oficiais normalizados:", len(trades))
    print("Período:", trades["DataHora_SP"].min(), "até", trades["DataHora_SP"].max())

    print("\nDistribuição por fonte:")
    print(trades["Fonte"].value_counts())

    print("\nDistribuição WIN/LOSS:")
    print(trades["Resultado"].value_counts())

    print("\nDistribuição por ano:")
    print(trades["Ano"].value_counts().sort_index())

    print("\nSalvando trades oficiais normalizados...")
    trades.to_csv(ARQ_TRADES_NORMALIZADOS, index=False, compression="gzip")

    print("\nGerando resumos...")
    resumo_geral = gerar_resumo_geral(trades)
    resumo_fonte = gerar_resumo_por_fonte(trades)
    resumo_mensal = gerar_resumo_mensal(trades)
    resumo_rotacoes = gerar_resumo_rotacoes(trades)
    resumo_rotacoes_fonte = gerar_resumo_rotacoes_fonte(trades)
    resumo_horario = gerar_resumo_horario(trades)
    resumo_bloco = gerar_resumo_bloco_15m(trades)

    resumo_geral.to_csv(ARQ_RESUMO_GERAL, index=False)
    resumo_fonte.to_csv(ARQ_RESUMO_FONTE, index=False)
    resumo_mensal.to_csv(ARQ_RESUMO_MENSAL, index=False)
    resumo_rotacoes.to_csv(ARQ_RESUMO_ROTACOES, index=False)
    resumo_rotacoes_fonte.to_csv(ARQ_RESUMO_ROTACOES_FONTE, index=False)

    ARQ_RESUMO_HORARIO = PASTA_SAIDA / "08_v53_oficial_resumo_horario.csv"
    ARQ_RESUMO_BLOCO = PASTA_SAIDA / "09_v53_oficial_resumo_bloco_15m.csv"

    resumo_horario.to_csv(ARQ_RESUMO_HORARIO, index=False)
    resumo_bloco.to_csv(ARQ_RESUMO_BLOCO, index=False)

    salvar_relatorio(
        trades,
        resumo_geral,
        resumo_fonte,
        resumo_mensal,
        resumo_rotacoes,
        resumo_rotacoes_fonte,
        resumo_horario,
        resumo_bloco,
    )

    print("\n")
    print("=" * 100)
    print("RESULTADO GERAL - V5.3 OFICIAL - ROTAÇÃO SEM RETREINO")
    print("=" * 100)
    print(resumo_geral.T.to_string())

    print("\n")
    print("=" * 100)
    print("RESUMO POR FONTE")
    print("=" * 100)
    print(resumo_fonte.to_string(index=False))

    print("\n")
    print("=" * 100)
    print("RESUMO POR ROTAÇÃO")
    print("=" * 100)
    print(resumo_rotacoes.to_string(index=False))

    print("\n")
    print("=" * 100)
    print("RESUMO POR ROTAÇÃO E FONTE")
    print("=" * 100)
    print(resumo_rotacoes_fonte.to_string(index=False))

    print("\n")
    print("=" * 100)
    print("RESUMO MENSAL")
    print("=" * 100)
    print(resumo_mensal.to_string(index=False))

    print("\n")
    print("=" * 100)
    print("RESUMO POR HORÁRIO")
    print("=" * 100)
    print(resumo_horario.to_string(index=False))

    print("\n")
    print("=" * 100)
    print("RESUMO POR BLOCO 15M")
    print("=" * 100)
    print(resumo_bloco.to_string(index=False))

    print("\nArquivos salvos:")
    print(ARQ_TRADES_NORMALIZADOS)
    print(ARQ_RESUMO_GERAL)
    print(ARQ_RESUMO_FONTE)
    print(ARQ_RESUMO_MENSAL)
    print(ARQ_RESUMO_ROTACOES)
    print(ARQ_RESUMO_ROTACOES_FONTE)
    print(ARQ_RESUMO_HORARIO)
    print(ARQ_RESUMO_BLOCO)
    print(ARQ_RELATORIO_TXT)

    print("\nFinalizado com sucesso.")


if __name__ == "__main__":
    main()