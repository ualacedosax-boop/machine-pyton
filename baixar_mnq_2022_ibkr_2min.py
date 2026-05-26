from ib_insync import IB, Future, util
from pathlib import Path
import pandas as pd
import time


# ============================================================
# CONFIGURAÇÕES IBKR / TWS
# ============================================================

HOST = "127.0.0.1"

# 7497 = Paper Trading
# 7496 = Conta Real
PORT = 7497

CLIENT_ID = 26


# ============================================================
# PASTA DE SAÍDA
# ============================================================

PASTA_BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_SAIDA = PASTA_BASE / "dados_mnq_2026_ibkr"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONTRATOS MNQ 2026
# ============================================================

CONTRATOS = [
    {
        "symbol": "MNQ",
        "lastTradeDateOrContractMonth": "202603",
        "exchange": "CME",
        "currency": "USD",
        "nome": "MNQH6",
        "inicio": "2026-01-01",
        "fim": "2026-03-20",
        "includeExpired": True,
    },
    {
        "symbol": "MNQ",
        "lastTradeDateOrContractMonth": "202606",
        "exchange": "CME",
        "currency": "USD",
        "nome": "MNQM6",
        "inicio": "2026-03-01",
        "fim": "2026-05-21",
        "includeExpired": False,
    },
]


# ============================================================
# CONFIGURAÇÕES DO HISTÓRICO
# ============================================================

BAR_SIZE = "2 mins"
WHAT_TO_SHOW = "TRADES"
USE_RTH = False

# Se der erro de limite/pacing, reduza para "5 D"
DURACAO_BLOCO = "10 D"

PAUSA_SEGUNDOS = 3


# ============================================================
# FUNÇÃO PARA CORRIGIR TIMEZONE
# ============================================================

def remover_timezone_coluna(serie):
    """
    Remove timezone de uma coluna datetime para evitar erro:
    Cannot compare tz-naive and tz-aware timestamps.
    """
    serie = pd.to_datetime(serie, errors="coerce")

    try:
        if serie.dt.tz is not None:
            serie = serie.dt.tz_localize(None)
    except Exception:
        serie = serie.apply(
            lambda x: x.replace(tzinfo=None)
            if pd.notna(x) and getattr(x, "tzinfo", None) is not None
            else x
        )

    return serie


# ============================================================
# FUNÇÕES IBKR
# ============================================================

def conectar_ibkr() -> IB:
    ib = IB()

    print("=====================================================")
    print("CONECTANDO AO IBKR / TWS")
    print("=====================================================")
    print(f"HOST: {HOST}")
    print(f"PORT: {PORT}")
    print(f"CLIENT_ID: {CLIENT_ID}")

    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=20)

    if not ib.isConnected():
        raise RuntimeError("Não conectou ao IBKR/TWS.")

    print("Conectado com sucesso.")
    return ib


def criar_contrato(cfg: dict) -> Future:
    contrato = Future(
        symbol=cfg["symbol"],
        lastTradeDateOrContractMonth=cfg["lastTradeDateOrContractMonth"],
        exchange=cfg["exchange"],
        currency=cfg["currency"],
        includeExpired=cfg["includeExpired"],
    )

    return contrato


def qualificar_contrato(ib: IB, contrato: Future, nome: str) -> Future:
    print()
    print("Qualificando contrato:", nome)

    contratos = ib.qualifyContracts(contrato)

    if not contratos:
        raise RuntimeError(f"Não conseguiu qualificar o contrato: {nome}")

    contrato_qualificado = contratos[0]

    print("Contrato qualificado:")
    print(contrato_qualificado)

    return contrato_qualificado


def baixar_bloco(ib: IB, contrato: Future, end_datetime: str) -> pd.DataFrame:
    print(f"Baixando bloco até: {end_datetime}")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime=end_datetime,
        durationStr=DURACAO_BLOCO,
        barSizeSetting=BAR_SIZE,
        whatToShow=WHAT_TO_SHOW,
        useRTH=USE_RTH,
        formatDate=1,
        keepUpToDate=False,
    )

    if not bars:
        print("Sem barras retornadas neste bloco.")
        return pd.DataFrame()

    df = util.df(bars)

    if df is None or df.empty:
        print("DataFrame vazio.")
        return pd.DataFrame()

    df = df.rename(
        columns={
            "date": "DataHora",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "barCount": "barCount",
            "average": "average",
        }
    )

    return df


def baixar_periodo_contrato(ib: IB, cfg: dict) -> pd.DataFrame:
    nome = cfg["nome"]

    print()
    print("=====================================================")
    print(f"BAIXANDO CONTRATO {nome}")
    print("=====================================================")

    contrato = criar_contrato(cfg)
    contrato = qualificar_contrato(ib, contrato, nome)

    inicio = pd.Timestamp(cfg["inicio"])
    fim = pd.Timestamp(cfg["fim"])

    cursor = fim
    partes = []

    while cursor > inicio:
        end_str = cursor.strftime("%Y%m%d %H:%M:%S")

        try:
            df_bloco = baixar_bloco(ib, contrato, end_str)
        except Exception as e:
            print("Erro ao baixar bloco:")
            print(e)

            print("Aguardando e pulando bloco...")
            time.sleep(PAUSA_SEGUNDOS * 2)

            cursor = cursor - pd.Timedelta(days=5)
            continue

        if not df_bloco.empty:
            df_bloco["DataHora"] = remover_timezone_coluna(df_bloco["DataHora"])
            df_bloco = df_bloco.dropna(subset=["DataHora"]).copy()

            if not df_bloco.empty:
                partes.append(df_bloco)

                dt_min = df_bloco["DataHora"].min()
                dt_max = df_bloco["DataHora"].max()

                print(f"Recebido: {len(df_bloco)} candles | {dt_min} até {dt_max}")

                cursor = dt_min - pd.Timedelta(minutes=2)
            else:
                cursor = cursor - pd.Timedelta(days=5)
        else:
            cursor = cursor - pd.Timedelta(days=5)

        time.sleep(PAUSA_SEGUNDOS)

    if not partes:
        print(f"Nenhum dado baixado para {nome}.")
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)

    df["DataHora"] = remover_timezone_coluna(df["DataHora"])
    df = df.dropna(subset=["DataHora"]).copy()

    df = df[(df["DataHora"] >= inicio) & (df["DataHora"] <= fim)].copy()

    df = df.drop_duplicates(subset=["DataHora"]).sort_values("DataHora").reset_index(drop=True)

    df["contrato"] = nome

    arquivo = PASTA_SAIDA / f"{nome}_2MIN_IBKR.csv"
    df.to_csv(arquivo, index=False)

    print()
    print(f"Arquivo salvo: {arquivo}")
    print(f"Linhas: {len(df)}")
    print(f"Início: {df['DataHora'].min()}")
    print(f"Fim: {df['DataHora'].max()}")

    return df


# ============================================================
# TRATAMENTO DO CONTÍNUO
# ============================================================

def adicionar_colunas_horario(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["DataHora"] = remover_timezone_coluna(df["DataHora"])
    df = df.dropna(subset=["DataHora"]).copy()

    # ATENÇÃO:
    # A DataHora que vem do TWS normalmente vem no fuso configurado no TWS.
    # Aqui mantemos DataHora como base e criamos nomes compatíveis com seus arquivos anteriores.
    df["DataHora_SP"] = df["DataHora"]

    # Compatível com seus arquivos antigos: SP - 3 horas = Chicago aproximado.
    df["DataHora_Chicago"] = df["DataHora_SP"] - pd.Timedelta(hours=3)

    df["Data"] = df["DataHora_SP"].dt.date

    df["Hora_SP_Decimal"] = (
        df["DataHora_SP"].dt.hour
        + df["DataHora_SP"].dt.minute / 60.0
        + df["DataHora_SP"].dt.second / 3600.0
    )

    return df


def gerar_continuo_2min(lista_dfs: list[pd.DataFrame]) -> pd.DataFrame:
    dfs_validos = [df for df in lista_dfs if df is not None and not df.empty]

    if not dfs_validos:
        raise RuntimeError("Nenhum dataframe válido para gerar contínuo.")

    df = pd.concat(dfs_validos, ignore_index=True)

    df["DataHora"] = remover_timezone_coluna(df["DataHora"])
    df = df.dropna(subset=["DataHora"]).copy()

    # Em sobreposição entre contratos, mantém a última linha ordenada pelo nome do contrato.
    df = df.sort_values(["DataHora", "contrato"]).drop_duplicates(subset=["DataHora"], keep="last")
    df = df.sort_values("DataHora").reset_index(drop=True)

    df = adicionar_colunas_horario(df)

    colunas_saida = [
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora_SP_Decimal",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "barCount",
        "average",
        "contrato",
    ]

    colunas_saida = [c for c in colunas_saida if c in df.columns]

    df_saida = df[colunas_saida].copy()

    arquivo = PASTA_SAIDA / "MNQ_2026_2MIN_IBKR_CONTINUO.csv"
    df_saida.to_csv(arquivo, index=False)

    print()
    print("=====================================================")
    print("ARQUIVO CONTÍNUO 2MIN GERADO")
    print("=====================================================")
    print(arquivo)
    print(f"Linhas: {len(df_saida)}")
    print(f"Início: {df_saida['DataHora_SP'].min()}")
    print(f"Fim: {df_saida['DataHora_SP'].max()}")

    return df_saida


def verificar_gaps(df: pd.DataFrame) -> None:
    if df.empty:
        return

    tmp = df.copy()
    tmp["DataHora_SP"] = remover_timezone_coluna(tmp["DataHora_SP"])
    tmp = tmp.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP")

    tmp["diff_min"] = tmp["DataHora_SP"].diff().dt.total_seconds() / 60.0

    gaps = tmp[tmp["diff_min"] > 2.5].copy()

    print()
    print("=====================================================")
    print("VERIFICAÇÃO DE GAPS")
    print("=====================================================")
    print(f"Total de candles: {len(tmp)}")
    print(f"Gaps maiores que 2 minutos: {len(gaps)}")

    if len(gaps) > 0:
        print()
        print("Primeiros gaps:")
        print(gaps[["DataHora_SP", "diff_min"]].head(20).to_string(index=False))


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():
    ib = conectar_ibkr()

    try:
        lista_dfs = []

        for cfg in CONTRATOS:
            df_contrato = baixar_periodo_contrato(ib, cfg)

            if not df_contrato.empty:
                lista_dfs.append(df_contrato)

        df_continuo = gerar_continuo_2min(lista_dfs)

        verificar_gaps(df_continuo)

        print()
        print("=====================================================")
        print("FINALIZADO COM SUCESSO")
        print("=====================================================")
        print("Arquivo para teste fora da amostra:")
        print(PASTA_SAIDA / "MNQ_2026_2MIN_IBKR_CONTINUO.csv")

    finally:
        print()
        print("Desconectando IBKR...")
        ib.disconnect()
        print("Desconectado.")


if __name__ == "__main__":
    main()