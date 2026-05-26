# -*- coding: utf-8 -*-
from ib_insync import *
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import time


# ============================================================
# CONFIGURAÇÕES IBKR
# ============================================================

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 84

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA_SAIDA = BASE_DIR / "dados_nq_2024_ibkr"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_FINAL = PASTA_SAIDA / "NQ_2024_2MIN_IBKR_CONTINUO.csv"


# ============================================================
# CONTRATOS NQ 2024 RECONHECIDOS PELO IBKR
# ============================================================

CONTRATOS = [
    {
        "nome": "NQM4",
        "conId": 620730920,
        "localSymbol": "NQM4",
        "inicio": "2024-03-15 00:00:00",
        "fim": "2024-06-21 23:59:59",
    },
    {
        "nome": "NQU4",
        "conId": 637533450,
        "localSymbol": "NQU4",
        "inicio": "2024-06-21 00:00:00",
        "fim": "2024-09-20 23:59:59",
    },
    {
        "nome": "NQZ4",
        "conId": 563947733,
        "localSymbol": "NQZ4",
        "inicio": "2024-09-20 00:00:00",
        "fim": "2024-12-20 23:59:59",
    },
]


# ============================================================
# FUNÇÕES
# ============================================================

def conectar_ib():
    ib = IB()

    print("Conectando ao IBKR...")
    print(f"HOST: {HOST}")
    print(f"PORT: {PORT}")
    print(f"CLIENT_ID: {CLIENT_ID}")

    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=20)

    print("Conectado com sucesso.")
    return ib


def criar_contrato_por_conid(cfg):
    contrato = Contract()
    contrato.secType = "FUT"
    contrato.conId = int(cfg["conId"])
    contrato.symbol = "NQ"
    contrato.exchange = "CME"
    contrato.currency = "USD"
    contrato.localSymbol = cfg["localSymbol"]
    contrato.includeExpired = True
    return contrato


def baixar_chunk(ib, contrato, end_dt):
    end_str = (end_dt + timedelta(hours=4)).strftime("%Y%m%d-%H:%M:%S")

    print(f"Baixando chunk até: {end_str}")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime=end_str,
        durationStr="5 D",
        barSizeSetting="2 mins",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
        keepUpToDate=False,
    )

    if not bars:
        return pd.DataFrame()

    df = util.df(bars)

    if df is None or df.empty:
        return pd.DataFrame()

    return df


def padronizar_dataframe(df, cfg):
    if df.empty:
        return df

    out = df.copy()

    out["date"] = pd.to_datetime(out["date"], errors="coerce")

    # A data retornada pelo IBKR vem na timezone do TWS ou sem timezone.
    # Vamos tratar como horário US/Eastern e converter para São Paulo.
    if out["date"].dt.tz is None:
        out["DataHora_Eastern"] = out["date"].dt.tz_localize(
            "America/New_York",
            ambiguous="infer",
            nonexistent="shift_forward"
        )
    else:
        out["DataHora_Eastern"] = out["date"].dt.tz_convert("America/New_York")

    out["DataHora_SP"] = out["DataHora_Eastern"].dt.tz_convert("America/Sao_Paulo")
    out["DataHora_UTC"] = out["DataHora_Eastern"].dt.tz_convert("UTC")

    out["DataHora_SP"] = out["DataHora_SP"].dt.tz_localize(None)
    out["DataHora_UTC"] = out["DataHora_UTC"].dt.tz_localize(None)
    out["DataHora_Eastern"] = out["DataHora_Eastern"].dt.tz_localize(None)

    out["Data"] = out["DataHora_SP"].dt.date.astype(str)
    out["Hora_SP_Decimal"] = (
        out["DataHora_SP"].dt.hour
        + out["DataHora_SP"].dt.minute / 60.0
        + out["DataHora_SP"].dt.second / 3600.0
    )

    out["contrato"] = cfg["nome"]
    out["localSymbol"] = cfg["localSymbol"]
    out["conId"] = int(cfg["conId"])
    out["symbol"] = "NQ"
    out["fonte"] = "IBKR"

    # Garante nomes OHLC esperados
    colunas = [
        "DataHora_SP",
        "DataHora_Eastern",
        "DataHora_UTC",
        "Data",
        "Hora_SP_Decimal",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "average",
        "barCount",
        "contrato",
        "localSymbol",
        "conId",
        "symbol",
        "fonte",
    ]

    for col in colunas:
        if col not in out.columns:
            out[col] = None

    out = out[colunas].copy()

    return out


def baixar_contrato(ib, cfg):
    print("\n=====================================================")
    print(f"BAIXANDO {cfg['nome']}")
    print("=====================================================")

    contrato = criar_contrato_por_conid(cfg)

    print("Contrato:")
    print(contrato)

    inicio = pd.to_datetime(cfg["inicio"])
    fim = pd.to_datetime(cfg["fim"])

    todos = []

    end_dt = fim

    while end_dt > inicio:
        try:
            df = baixar_chunk(ib, contrato, end_dt)

            if df.empty:
                print("Chunk vazio.")
            else:
                df_pad = padronizar_dataframe(df, cfg)

                df_pad = df_pad[
                    (pd.to_datetime(df_pad["DataHora_SP"]) >= inicio)
                    & (pd.to_datetime(df_pad["DataHora_SP"]) <= fim)
                ].copy()

                if not df_pad.empty:
                    print(f"Linhas recebidas: {len(df_pad)}")
                    print(f"Primeira: {df_pad['DataHora_SP'].min()}")
                    print(f"Última  : {df_pad['DataHora_SP'].max()}")
                    todos.append(df_pad)
                else:
                    print("Chunk fora do período após filtro.")

            end_dt = end_dt - timedelta(days=5)

            # Evita pacing do IBKR
            time.sleep(2.0)

        except Exception as e:
            print("ERRO no chunk:")
            print(e)
            end_dt = end_dt - timedelta(days=5)
            time.sleep(5.0)

    if not todos:
        print(f"Nenhum dado baixado para {cfg['nome']}.")
        return pd.DataFrame()

    final = pd.concat(todos, ignore_index=True)

    final = final.drop_duplicates(subset=["DataHora_SP", "contrato"])
    final = final.sort_values("DataHora_SP").reset_index(drop=True)

    arq_contrato = PASTA_SAIDA / f"NQ_2024_2MIN_IBKR_{cfg['nome']}.csv"
    final.to_csv(arq_contrato, index=False)

    print(f"\nArquivo salvo do contrato {cfg['nome']}:")
    print(arq_contrato)
    print("Linhas:", len(final))

    return final


def main():
    print("=====================================================")
    print("BAIXAR NQ 2024 IBKR - 2 MIN")
    print("=====================================================")

    ib = None

    try:
        ib = conectar_ib()

        todos = []

        for cfg in CONTRATOS:
            df = baixar_contrato(ib, cfg)

            if not df.empty:
                todos.append(df)

        if not todos:
            print("\nNenhum dado foi baixado.")
            return

        final = pd.concat(todos, ignore_index=True)

        final = final.drop_duplicates(subset=["DataHora_SP"])
        final = final.sort_values("DataHora_SP").reset_index(drop=True)

        final.to_csv(ARQ_FINAL, index=False)

        print("\n=====================================================")
        print("FINALIZADO")
        print("=====================================================")
        print("Arquivo contínuo salvo:")
        print(ARQ_FINAL)
        print("Linhas:", len(final))
        print("Primeira data:", final["DataHora_SP"].min())
        print("Última data  :", final["DataHora_SP"].max())

    finally:
        if ib is not None and ib.isConnected():
            print("\nDesconectando IBKR...")
            ib.disconnect()
            print("Desconectado.")


if __name__ == "__main__":
    main()

