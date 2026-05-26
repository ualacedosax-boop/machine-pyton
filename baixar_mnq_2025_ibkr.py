from ib_insync import *
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# =====================================================
# CONFIGURAÇÕES PRINCIPAIS
# =====================================================
HOST = "127.0.0.1"
PORT = 7497          # 7497 = Paper/simulação | 7496 = Conta real
CLIENT_ID = 200

ATIVO = "MNQ"
EXCHANGE = "CME"
CURRENCY = "USD"

PASTA_SAIDA = "dados_mnq_2025_ibkr"

ARQUIVO_FINAL_1MIN = os.path.join(PASTA_SAIDA, "MNQ_2025_1MIN_IBKR_CONTINUO.csv")
ARQUIVO_FINAL_2MIN = os.path.join(PASTA_SAIDA, "MNQ_2025_2MIN_IBKR_CONTINUO.csv")

# Bloco de download.
# Como 1 hora funcionou no seu teste, vamos manter 1 hora para ser mais seguro.
HORAS_POR_BLOCO = 1
DURACAO_SEGUNDOS = HORAS_POR_BLOCO * 60 * 60

# Pausa entre requisições para evitar bloqueio/pacing da IBKR
PAUSA_SEGUNDOS = 2

BAR_SIZE = "1 min"
WHAT_TO_SHOW = "TRADES"
USE_RTH = False

os.makedirs(PASTA_SAIDA, exist_ok=True)

# =====================================================
# CONTRATOS DO ANO 2025
# =====================================================
# A ideia é montar uma série contínua usando o contrato vigente/front.
# Janeiro começa em MNQH5.
# Depois troca para M5, U5, Z5 e H6 no final de dezembro.

CONTRATOS_2025 = [
    {
        "nome": "MNQH5",
        "contract_month": "202503",
        "inicio": datetime(2025, 1, 1, 0, 0, 0),
        "fim": datetime(2025, 3, 21, 23, 59, 59),
        "include_expired": True
    },
    {
        "nome": "MNQM5",
        "contract_month": "202506",
        "inicio": datetime(2025, 3, 22, 0, 0, 0),
        "fim": datetime(2025, 6, 20, 23, 59, 59),
        "include_expired": True
    },
    {
        "nome": "MNQU5",
        "contract_month": "202509",
        "inicio": datetime(2025, 6, 21, 0, 0, 0),
        "fim": datetime(2025, 9, 19, 23, 59, 59),
        "include_expired": True
    },
    {
        "nome": "MNQZ5",
        "contract_month": "202512",
        "inicio": datetime(2025, 9, 20, 0, 0, 0),
        "fim": datetime(2025, 12, 19, 23, 59, 59),
        "include_expired": True
    },
    {
        "nome": "MNQH6",
        "contract_month": "202603",
        "inicio": datetime(2025, 12, 20, 0, 0, 0),
        "fim": datetime(2025, 12, 31, 23, 59, 59),
        "include_expired": False
    },
]


# =====================================================
# FUNÇÕES
# =====================================================
def localizar_contrato(ib, item):
    """
    Localiza o contrato na IBKR pelo mês de vencimento.
    Retorna o contrato qualificado.
    """

    contrato_base = Future(
        symbol=ATIVO,
        lastTradeDateOrContractMonth=item["contract_month"],
        exchange=EXCHANGE,
        currency=CURRENCY,
        includeExpired=item["include_expired"]
    )

    detalhes = ib.reqContractDetails(contrato_base)

    if not detalhes:
        raise Exception(f"Não encontrou contrato {item['nome']} / {item['contract_month']} na IBKR.")

    # Normalmente vem apenas um contrato correto
    contrato = detalhes[0].contract

    # Garante includeExpired quando necessário
    contrato.includeExpired = item["include_expired"]

    print("\nContrato encontrado:")
    print("Nome esperado:", item["nome"])
    print("conId:", contrato.conId)
    print("symbol:", contrato.symbol)
    print("localSymbol:", contrato.localSymbol)
    print("tradingClass:", contrato.tradingClass)
    print("exchange:", contrato.exchange)
    print("lastTradeDate:", contrato.lastTradeDateOrContractMonth)
    print("multiplier:", contrato.multiplier)

    return contrato


def baixar_contrato_em_blocos(ib, contrato, item):
    """
    Baixa um contrato em blocos de 1 hora.
    Salva um CSV parcial por contrato.
    """

    nome = item["nome"]
    inicio = item["inicio"]
    fim = item["fim"]

    arquivo_parcial = os.path.join(PASTA_SAIDA, f"{nome}_1MIN_IBKR.csv")

    print("\n=====================================================")
    print(f"INICIANDO DOWNLOAD DO CONTRATO {nome}")
    print("Período:", inicio, "até", fim)
    print("Arquivo parcial:", arquivo_parcial)
    print("=====================================================")

    dfs = []
    atual = inicio

    while atual <= fim:
        bloco_fim = atual + timedelta(seconds=DURACAO_SEGUNDOS)

        if bloco_fim > fim:
            bloco_fim = fim

        # Formato aceito pela IBKR em UTC:
        # YYYYMMDD-HH:MM:SS
        end_str = bloco_fim.strftime("%Y%m%d-%H:%M:%S")

        print("\n-----------------------------------------")
        print("Contrato:", nome)
        print("Início aproximado:", atual)
        print("Fim do bloco:", bloco_fim)
        print("endDateTime:", end_str)
        print("-----------------------------------------")

        try:
            bars = ib.reqHistoricalData(
                contrato,
                endDateTime=end_str,
                durationStr=f"{DURACAO_SEGUNDOS} S",
                barSizeSetting=BAR_SIZE,
                whatToShow=WHAT_TO_SHOW,
                useRTH=USE_RTH,
                formatDate=1,
                keepUpToDate=False,
                timeout=180
            )

            if bars:
                df_bloco = util.df(bars)

                df_bloco["contrato"] = nome
                df_bloco["conId"] = contrato.conId
                df_bloco["localSymbol"] = contrato.localSymbol

                print("Candles baixados:", len(df_bloco))
                print("Primeiro:", df_bloco.iloc[0]["date"])
                print("Último:", df_bloco.iloc[-1]["date"])

                dfs.append(df_bloco)

                # Salva parcial a cada bloco para não perder tudo se parar
                df_temp = pd.concat(dfs, ignore_index=True)
                df_temp = df_temp.drop_duplicates(subset=["date", "contrato"])
                df_temp = df_temp.sort_values("date")
                df_temp.to_csv(arquivo_parcial, index=False, encoding="utf-8-sig")

            else:
                print("Sem candles neste bloco.")

        except Exception as e:
            print("ERRO NESTE BLOCO:")
            print(e)

        atual = bloco_fim + timedelta(seconds=1)
        time.sleep(PAUSA_SEGUNDOS)

    if not dfs:
        print(f"Nenhum candle baixado para {nome}.")
        return None

    df_contrato = pd.concat(dfs, ignore_index=True)
    df_contrato = df_contrato.drop_duplicates(subset=["date", "contrato"])
    df_contrato = df_contrato.sort_values("date")
    df_contrato.to_csv(arquivo_parcial, index=False, encoding="utf-8-sig")

    print("\nContrato finalizado:", nome)
    print("Linhas:", len(df_contrato))
    print("Arquivo salvo:", arquivo_parcial)

    return df_contrato


def converter_para_2min(df_1min):
    """
    Converte a base de 1 minuto para 2 minutos.
    O candle de 2 minutos usa:
    abertura do primeiro candle,
    máxima dos dois,
    mínima dos dois,
    fechamento do segundo,
    soma do volume e barCount.
    """

    df = df_1min.copy()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")

    agregacoes = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "average": "mean",
        "barCount": "sum",
        "contrato": "last",
        "conId": "last",
        "localSymbol": "last"
    }

    df_2min = df.resample("2min", label="left", closed="left").agg(agregacoes)
    df_2min = df_2min.dropna().reset_index()

    return df_2min


# =====================================================
# EXECUÇÃO PRINCIPAL
# =====================================================
ib = IB()

try:
    ib.connect(HOST, PORT, clientId=CLIENT_ID, readonly=True)
    print("Conectado:", ib.isConnected())

    # Usa dados atrasados/congelados se for o caso
    ib.reqMarketDataType(4)

    todos = []

    for item in CONTRATOS_2025:
        contrato = localizar_contrato(ib, item)
        df_contrato = baixar_contrato_em_blocos(ib, contrato, item)

        if df_contrato is not None and not df_contrato.empty:
            todos.append(df_contrato)

    if not todos:
        raise Exception("Nenhum dado foi baixado para o ano de 2025.")

    # =====================================================
    # JUNTAR TODOS OS CONTRATOS
    # =====================================================
    df_final_1min = pd.concat(todos, ignore_index=True)

    df_final_1min["date"] = pd.to_datetime(df_final_1min["date"])
    df_final_1min = df_final_1min.sort_values("date")

    # Remove duplicados.
    # Como os contratos são separados por períodos, date basta para a série contínua.
    df_final_1min = df_final_1min.drop_duplicates(subset=["date"])

    print("\n=====================================================")
    print("RESUMO FINAL 1 MINUTO")
    print("=====================================================")
    print("Linhas:", len(df_final_1min))
    print("Primeiras linhas:")
    print(df_final_1min.head())
    print("Últimas linhas:")
    print(df_final_1min.tail())

    df_final_1min.to_csv(ARQUIVO_FINAL_1MIN, index=False, encoding="utf-8-sig")

    print("\nArquivo final 1 minuto salvo:")
    print(ARQUIVO_FINAL_1MIN)

    # =====================================================
    # CONVERTER PARA 2 MINUTOS
    # =====================================================
    df_final_2min = converter_para_2min(df_final_1min)

    print("\n=====================================================")
    print("RESUMO FINAL 2 MINUTOS")
    print("=====================================================")
    print("Linhas:", len(df_final_2min))
    print("Primeiras linhas:")
    print(df_final_2min.head())
    print("Últimas linhas:")
    print(df_final_2min.tail())

    df_final_2min.to_csv(ARQUIVO_FINAL_2MIN, index=False, encoding="utf-8-sig")

    print("\nArquivo final 2 minutos salvo:")
    print(ARQUIVO_FINAL_2MIN)

finally:
    if ib.isConnected():
        ib.disconnect()
        print("\nDesconectado.")