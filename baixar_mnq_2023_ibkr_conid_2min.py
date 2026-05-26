# -*- coding: utf-8 -*-

from ib_insync import *
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import time
import traceback

# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_SAIDA = BASE_DIR / "dados_mnq_2023_ibkr"
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

ARQ_CONTINUO = PASTA_SAIDA / "MNQ_2023_2MIN_IBKR_CONTINUO.csv"
ARQ_CONTRATOS_ENCONTRADOS = PASTA_SAIDA / "CONTRATOS_MNQ_2023_ENCONTRADOS.csv"

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 83

BAR_SIZE = "2 mins"
WHAT_TO_SHOW = "TRADES"
USE_RTH = False

# Duração por chamada. 2 D costuma ser mais estável no IBKR.
DURATION_STR = "2 D"

# Pausa para evitar pacing violation
PAUSA_SEGUNDOS = 1.2

# ============================================================
# CONTRATOS / JANELAS
# ============================================================
# Observação:
# Para montar 2023 contínuo, usamos:
# MNQH3: início do ano até vencimento março
# MNQM3: março até vencimento junho
# MNQU3: junho até vencimento setembro
# MNQZ3: setembro até vencimento dezembro
# MNQH4: dezembro até fim de 2023

CONTRATOS_PLANO = [
    {
        "nome": "MNQH3",
        "localSymbol": "MNQH3",
        "lastTradeDate": "20230317",
        "inicio_sp": "2023-01-02 00:00:00",
        "fim_sp": "2023-03-17 18:58:00",
    },
    {
        "nome": "MNQM3",
        "localSymbol": "MNQM3",
        "lastTradeDate": "20230616",
        "inicio_sp": "2023-03-17 19:00:00",
        "fim_sp": "2023-06-16 18:58:00",
    },
    {
        "nome": "MNQU3",
        "localSymbol": "MNQU3",
        "lastTradeDate": "20230915",
        "inicio_sp": "2023-06-16 19:00:00",
        "fim_sp": "2023-09-15 18:58:00",
    },
    {
        "nome": "MNQZ3",
        "localSymbol": "MNQZ3",
        "lastTradeDate": "20231215",
        "inicio_sp": "2023-09-15 19:00:00",
        "fim_sp": "2023-12-15 18:58:00",
    },
    {
        "nome": "MNQH4",
        "localSymbol": "MNQH4",
        "lastTradeDate": "20240315",
        "inicio_sp": "2023-12-15 19:00:00",
        "fim_sp": "2023-12-29 18:58:00",
    },
]


# ============================================================
# FUNÇÕES
# ============================================================

def conectar_ib():
    ib = IB()
    print("Conectando IBKR...")
    print(f"HOST={HOST} | PORT={PORT} | CLIENT_ID={CLIENT_ID}")
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=15)
    print("Conectado com sucesso.")
    return ib


def dt_sp(txt):
    return pd.to_datetime(txt)


def sp_para_enddate_ib(dt_sp_val):
    """
    Mantemos o mesmo padrão que funcionou no script anterior:
    DataHora_SP + 4 horas -> formato IBKR UTC-like: yyyyMMdd-HH:mm:ss
    """
    return (dt_sp_val + timedelta(hours=4)).strftime("%Y%m%d-%H:%M:%S")


def salvar_csv_seguro(df, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")


def tentar_detalhes(ib, contrato, descricao):
    try:
        detalhes = ib.reqContractDetails(contrato)
        print(f"  Tentativa {descricao}: {len(detalhes)} detalhe(s)")
        return detalhes
    except Exception as e:
        print(f"  Tentativa {descricao} falhou: {e}")
        return []


def descobrir_contrato(ib, cfg):
    nome = cfg["nome"]
    local_symbol = cfg["localSymbol"]
    ltd = cfg["lastTradeDate"]
    mes = ltd[:6]

    print("\n-----------------------------------------------------")
    print(f"Descobrindo contrato: {nome}")
    print("-----------------------------------------------------")

    tentativas = []

    # Tentativa 1: localSymbol
    tentativas.append((
        Future(
            symbol="MNQ",
            exchange="CME",
            currency="USD",
            localSymbol=local_symbol,
            includeExpired=True,
        ),
        "MNQ + localSymbol",
    ))

    # Tentativa 2: lastTradeDate cheio
    tentativas.append((
        Future(
            symbol="MNQ",
            lastTradeDateOrContractMonth=ltd,
            exchange="CME",
            currency="USD",
            includeExpired=True,
        ),
        "MNQ + lastTradeDate cheio",
    ))

    # Tentativa 3: mês
    tentativas.append((
        Future(
            symbol="MNQ",
            lastTradeDateOrContractMonth=mes,
            exchange="CME",
            currency="USD",
            includeExpired=True,
        ),
        "MNQ + mês",
    ))

    # Tentativa 4: tradingClass
    c4 = Future(
        symbol="MNQ",
        lastTradeDateOrContractMonth=ltd,
        exchange="CME",
        currency="USD",
        includeExpired=True,
    )
    c4.tradingClass = "MNQ"
    tentativas.append((c4, "MNQ + tradingClass + lastTradeDate"))

    achados = []

    for contrato, descricao in tentativas:
        detalhes = tentar_detalhes(ib, contrato, descricao)

        for d in detalhes:
            ct = d.contract
            ls = getattr(ct, "localSymbol", "")
            conid = getattr(ct, "conId", None)
            tclass = getattr(ct, "tradingClass", "")
            mult = getattr(ct, "multiplier", "")
            exp = getattr(ct, "lastTradeDateOrContractMonth", "")

            print(
                f"    conId={conid} | localSymbol={ls} | "
                f"tradingClass={tclass} | exp={exp} | multiplier={mult}"
            )

            if str(ls).upper() == local_symbol.upper() or str(exp).startswith(ltd):
                achados.append(d)

        if achados:
            break

    if not achados:
        print(f"\nERRO: não consegui descobrir conId para {nome}.")
        return None

    contrato = achados[0].contract

    print("\nContrato escolhido:")
    print("  nome:", nome)
    print("  conId:", contrato.conId)
    print("  localSymbol:", contrato.localSymbol)
    print("  lastTradeDate:", contrato.lastTradeDateOrContractMonth)
    print("  exchange:", contrato.exchange)
    print("  multiplier:", contrato.multiplier)

    return contrato


def baixar_chunk(ib, contrato, end_dt_sp):
    end_str = sp_para_enddate_ib(end_dt_sp)

    print(f"Baixando chunk até: {end_str}")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime=end_str,
        durationStr=DURATION_STR,
        barSizeSetting=BAR_SIZE,
        whatToShow=WHAT_TO_SHOW,
        useRTH=USE_RTH,
        formatDate=1,
        keepUpToDate=False,
    )

    if not bars:
        return pd.DataFrame()

    df = util.df(bars)

    if df is None or df.empty:
        return pd.DataFrame()

    return df


def normalizar_df_barras(df, contrato, cfg):
    out = df.copy()

    if "date" not in out.columns:
        raise RuntimeError("DataFrame não tem coluna date.")

    out["DataHora_UTC_ORIG"] = pd.to_datetime(out["date"], errors="coerce")

    # O padrão usado anteriormente foi trazer para SP subtraindo 4 horas.
    out["DataHora_SP"] = out["DataHora_UTC_ORIG"] - pd.Timedelta(hours=4)

    out["DataHora_SP"] = pd.to_datetime(out["DataHora_SP"], errors="coerce")
    out = out.dropna(subset=["DataHora_SP"]).copy()

    out["Data"] = out["DataHora_SP"].dt.date.astype(str)
    out["Hora"] = out["DataHora_SP"].dt.strftime("%H:%M:%S")

    out["DataHora_Chicago"] = out["DataHora_SP"]

    out["contrato"] = cfg["nome"]
    out["localSymbol"] = getattr(contrato, "localSymbol", cfg["nome"])
    out["conId"] = getattr(contrato, "conId", None)
    out["symbol"] = "MNQ"

    colunas_base = [
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora",
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
    ]

    for col in colunas_base:
        if col not in out.columns:
            out[col] = None

    out = out[colunas_base].copy()

    return out


def baixar_periodo_contrato(ib, cfg, contrato):
    nome = cfg["nome"]

    inicio = dt_sp(cfg["inicio_sp"])
    fim = dt_sp(cfg["fim_sp"])

    print("\n=====================================================")
    print(f"BAIXANDO CONTRATO {nome}")
    print("=====================================================")
    print("Início SP:", inicio)
    print("Fim SP   :", fim)

    partes = []

    end_dt = fim

    while end_dt > inicio:
        try:
            df_chunk = baixar_chunk(ib, contrato, end_dt)
            time.sleep(PAUSA_SEGUNDOS)

            if df_chunk.empty:
                print("Chunk vazio.")
                end_dt = end_dt - timedelta(days=2)
                continue

            df_norm = normalizar_df_barras(df_chunk, contrato, cfg)

            # filtra janela do contrato
            df_norm = df_norm[
                (df_norm["DataHora_SP"] >= inicio)
                & (df_norm["DataHora_SP"] <= fim)
            ].copy()

            if not df_norm.empty:
                print(
                    f"Linhas: {len(df_norm)} | "
                    f"{df_norm['DataHora_SP'].min()} -> {df_norm['DataHora_SP'].max()}"
                )
                partes.append(df_norm)

            menor_dt = pd.to_datetime(df_chunk["date"], errors="coerce").min()

            if pd.isna(menor_dt):
                end_dt = end_dt - timedelta(days=2)
            else:
                # voltamos um pouco antes do candle mais antigo baixado
                menor_sp = menor_dt - pd.Timedelta(hours=4)
                end_dt = menor_sp - timedelta(minutes=2)

        except Exception as e:
            print("ERRO no chunk:")
            print(e)
            traceback.print_exc()
            end_dt = end_dt - timedelta(days=2)
            time.sleep(3)

    if not partes:
        print(f"Nenhuma barra baixada para {nome}.")
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    df = df.sort_values("DataHora_SP")
    df = df.drop_duplicates(subset=["DataHora_SP"], keep="last").reset_index(drop=True)

    arq_contrato = PASTA_SAIDA / f"MNQ_2023_2MIN_IBKR_{nome}.csv"
    salvar_csv_seguro(df, arq_contrato)

    print("\nArquivo contrato salvo:")
    print(arq_contrato)
    print("Linhas:", len(df))
    print("Primeira:", df["DataHora_SP"].min())
    print("Última  :", df["DataHora_SP"].max())

    return df


def salvar_contratos_encontrados(contratos_info):
    df = pd.DataFrame(contratos_info)
    salvar_csv_seguro(df, ARQ_CONTRATOS_ENCONTRADOS)
    print("\nContratos encontrados salvos em:")
    print(ARQ_CONTRATOS_ENCONTRADOS)


def checar_buracos(df):
    if df.empty:
        return

    temp = df.copy()
    temp["DataHora_SP"] = pd.to_datetime(temp["DataHora_SP"], errors="coerce")
    temp = temp.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

    temp["diff_min"] = temp["DataHora_SP"].diff().dt.total_seconds() / 60
    buracos = temp[temp["diff_min"] > 10].copy()

    print("\n=====================================================")
    print("CHECAGEM CONTÍNUO 2023")
    print("=====================================================")
    print("Linhas:", len(temp))
    print("Primeira:", temp["DataHora_SP"].min())
    print("Última  :", temp["DataHora_SP"].max())
    print("Duplicados DataHora_SP:", temp["DataHora_SP"].duplicated().sum())
    print("Buracos maiores que 10 minutos:", len(buracos))

    if len(buracos):
        print("\nMaiores buracos:")
        cols = ["DataHora_SP", "diff_min", "contrato", "localSymbol"]
        print(buracos.sort_values("diff_min", ascending=False)[cols].head(30).to_string(index=False))

        arq_buracos = PASTA_SAIDA / "CHECAGEM_BURACOS_MNQ_2023.csv"
        salvar_csv_seguro(buracos, arq_buracos)
        print("\nArquivo buracos salvo:")
        print(arq_buracos)


def main():
    ib = None

    try:
        ib = conectar_ib()

        contratos = {}
        contratos_info = []

        print("\n=====================================================")
        print("DESCOBRINDO CONIDs MNQ 2023")
        print("=====================================================")

        for cfg in CONTRATOS_PLANO:
            contrato = descobrir_contrato(ib, cfg)

            if contrato is None:
                raise RuntimeError(
                    f"Não consegui descobrir conId para {cfg['nome']}. "
                    f"Pare aqui e me mande o log desta parte."
                )

            contratos[cfg["nome"]] = contrato

            contratos_info.append({
                "nome": cfg["nome"],
                "conId": contrato.conId,
                "localSymbol": contrato.localSymbol,
                "lastTradeDateOrContractMonth": contrato.lastTradeDateOrContractMonth,
                "exchange": contrato.exchange,
                "currency": contrato.currency,
                "multiplier": contrato.multiplier,
                "inicio_sp": cfg["inicio_sp"],
                "fim_sp": cfg["fim_sp"],
            })

        salvar_contratos_encontrados(contratos_info)

        partes = []

        for cfg in CONTRATOS_PLANO:
            contrato = contratos[cfg["nome"]]
            df_contrato = baixar_periodo_contrato(ib, cfg, contrato)

            if not df_contrato.empty:
                partes.append(df_contrato)

        if not partes:
            raise RuntimeError("Nenhum dado foi baixado.")

        continuo = pd.concat(partes, ignore_index=True)
        continuo["DataHora_SP"] = pd.to_datetime(continuo["DataHora_SP"], errors="coerce")
        continuo = continuo.dropna(subset=["DataHora_SP"]).copy()

        continuo = continuo.sort_values("DataHora_SP")
        continuo = continuo.drop_duplicates(subset=["DataHora_SP"], keep="last").reset_index(drop=True)

        salvar_csv_seguro(continuo, ARQ_CONTINUO)

        print("\n=====================================================")
        print("CONTÍNUO 2023 SALVO")
        print("=====================================================")
        print(ARQ_CONTINUO)
        print("Linhas:", len(continuo))
        print("Primeira:", continuo["DataHora_SP"].min())
        print("Última  :", continuo["DataHora_SP"].max())

        checar_buracos(continuo)

    finally:
        if ib is not None and ib.isConnected():
            print("\nDesconectando IBKR...")
            ib.disconnect()
            print("Desconectado.")


if __name__ == "__main__":
    main()