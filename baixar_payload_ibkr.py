# -*- coding: utf-8 -*-
"""
baixar_payload_ibkr.py
======================
Baixa candles 2min recentes do MNQM6 via IBKR/TWS e aplica como payload
no blackarrow_ticks.csv (para que o robo inicie com candles suficientes).

TIMEZONE:
  O TWS retorna os timestamps em Chicago time (CDT/CST).
  Este script converte automaticamente para Sao Paulo time (UTC-3)
  usando pytz (lida com DST corretamente).
    CDT (verao, mar-nov): Chicago UTC-5 -> SP UTC-3 = +2h
    CST (inverno, nov-mar): Chicago UTC-6 -> SP UTC-3 = +3h

USO:
  python baixar_payload_ibkr.py             # baixa ultimos 3 dias, porta 7496 (real)
  python baixar_payload_ibkr.py --port 7497 # porta paper trading
  python baixar_payload_ibkr.py --dias 5    # ultimos 5 dias
  python baixar_payload_ibkr.py --apenas-verificar  # nao grava, so mostra
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import pytz
    TZ_CHICAGO = pytz.timezone("America/Chicago")
    TZ_SP = pytz.timezone("America/Sao_Paulo")
    TEM_PYTZ = True
except ImportError:
    TEM_PYTZ = False

try:
    from ib_insync import IB, Future, util
    TEM_IB_INSYNC = True
except ImportError:
    TEM_IB_INSYNC = False


# ============================================================
# CONFIGURACOES
# ============================================================

PASTA_BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA_OPERACIONAL = PASTA_BASE / "operacional_v71_oficial"

ARQUIVO_TICKS = PASTA_OPERACIONAL / "blackarrow_ticks.csv"
ARQUIVO_RECENTE = PASTA_BASE / "MNQ_RECENTE_2MIN_IBKR.csv"

HOST = "127.0.0.1"
DEFAULT_PORT = 7496       # conta real (7497 = paper)
CLIENT_ID = 73

# Contrato atual MNQ junho/2026
CONTRATO_SYMBOL = "MNQ"
CONTRATO_EXPIRACAO = "202606"
CONTRATO_EXCHANGE = "CME"
CONTRATO_CURRENCY = "USD"

BAR_SIZE = "2 mins"
WHAT_TO_SHOW = "TRADES"
USE_RTH = False
DURACAO_BLOCO = "5 D"
PAUSA_SEGUNDOS = 3

ASSET = "MNQM6"

COLUNAS_TICKS = [
    "Asset",
    "DataHora_SP",
    "Data",
    "Hora_SP_Decimal",
    "ultimo",
    "abertura",
    "maximo",
    "minimo",
    "strike",
    "negocios_acumulado",
]


# ============================================================
# CONVERSAO DE TIMEZONE
# ============================================================

def chicago_para_sp(serie_naive: pd.Series) -> pd.Series:
    """Converte timestamps naive (Chicago time) para SP time (naive), respeitando DST."""
    if TEM_PYTZ:
        convertidos = serie_naive.apply(
            lambda dt: TZ_CHICAGO.localize(dt).astimezone(TZ_SP).replace(tzinfo=None)
            if pd.notna(dt)
            else pd.NaT
        )
        return pd.Series(convertidos, index=serie_naive.index)
    else:
        # Fallback: +3h (CST inverno). Erro de ate 1h no verao (CDT).
        return serie_naive + pd.Timedelta(hours=3)


def remover_timezone(serie: pd.Series) -> pd.Series:
    """Remove timezone de uma Series datetime."""
    serie = pd.to_datetime(serie, errors="coerce")
    try:
        if serie.dt.tz is not None:
            # Se for timezone explicito, converte para Chicago naive primeiro
            if TEM_PYTZ:
                return serie.dt.tz_convert(TZ_CHICAGO).dt.tz_localize(None)
            else:
                return serie.dt.tz_localize(None)
    except Exception:
        pass
    return serie


# ============================================================
# IBKR — DOWNLOAD
# ============================================================

def conectar(host: str, port: int, client_id: int) -> "IB":
    print(f"Conectando ao IBKR/TWS em {host}:{port} (clientId={client_id})...")
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=20)
    if not ib.isConnected():
        raise RuntimeError("Nao conectou ao IBKR/TWS.")
    print("[OK] Conectado.")
    return ib


def qualificar_contrato(ib: "IB") -> "Future":
    contrato = Future(
        symbol=CONTRATO_SYMBOL,
        lastTradeDateOrContractMonth=CONTRATO_EXPIRACAO,
        exchange=CONTRATO_EXCHANGE,
        currency=CONTRATO_CURRENCY,
        includeExpired=False,
    )
    qualificados = ib.qualifyContracts(contrato)
    if not qualificados:
        raise RuntimeError(
            f"Nao foi possivel qualificar o contrato {CONTRATO_SYMBOL} {CONTRATO_EXPIRACAO}."
        )
    print(f"[OK] Contrato qualificado: {qualificados[0]}")
    return qualificados[0]


def baixar_bloco(ib: "IB", contrato: "Future", end_dt: pd.Timestamp) -> pd.DataFrame:
    end_str = end_dt.strftime("%Y%m%d %H:%M:%S")
    print(f"  Baixando bloco ate {end_str} (Chicago)...")

    bars = ib.reqHistoricalData(
        contrato,
        endDateTime=end_str,
        durationStr=DURACAO_BLOCO,
        barSizeSetting=BAR_SIZE,
        whatToShow=WHAT_TO_SHOW,
        useRTH=USE_RTH,
        formatDate=1,
        keepUpToDate=False,
    )

    if not bars:
        print("  Sem barras neste bloco.")
        return pd.DataFrame()

    df = util.df(bars)
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.rename(columns={"date": "DataHora"})
    df["DataHora"] = remover_timezone(df["DataHora"])
    return df.dropna(subset=["DataHora"]).copy()


def baixar_periodo(ib: "IB", contrato: "Future", dias: int) -> pd.DataFrame:
    """Baixa candles dos ultimos N dias de trading."""
    agora_chicago = datetime.now()
    if TEM_PYTZ:
        agora_chicago = datetime.now(TZ_SP).astimezone(TZ_CHICAGO).replace(tzinfo=None)

    inicio = pd.Timestamp(agora_chicago) - pd.Timedelta(days=dias + 1)
    fim = pd.Timestamp(agora_chicago)

    cursor = fim
    partes: list[pd.DataFrame] = []

    while cursor > inicio:
        try:
            bloco = baixar_bloco(ib, contrato, cursor)
        except Exception as exc:
            print(f"  Erro ao baixar bloco: {exc}")
            cursor -= pd.Timedelta(days=2)
            time.sleep(PAUSA_SEGUNDOS)
            continue

        if bloco.empty:
            cursor -= pd.Timedelta(days=2)
            time.sleep(PAUSA_SEGUNDOS)
            continue

        bloco = bloco[(bloco["DataHora"] >= inicio) & (bloco["DataHora"] <= fim)].copy()
        if not bloco.empty:
            partes.append(bloco)
            print(f"  Recebidos {len(bloco)} candles: "
                  f"{bloco['DataHora'].min()} -> {bloco['DataHora'].max()}")
            cursor = bloco["DataHora"].min() - pd.Timedelta(minutes=2)
        else:
            cursor -= pd.Timedelta(days=2)

        time.sleep(PAUSA_SEGUNDOS)

    if not partes:
        return pd.DataFrame()

    df = pd.concat(partes, ignore_index=True)
    df = (
        df.drop_duplicates(subset=["DataHora"])
        .sort_values("DataHora")
        .reset_index(drop=True)
    )
    return df


# ============================================================
# CONVERSAO PARA blackarrow_ticks.csv
# ============================================================

def ibkr_para_ticks(df_ibkr: pd.DataFrame) -> pd.DataFrame:
    """Converte DataFrame IBKR (Chicago time) para o formato de blackarrow_ticks.csv (SP time)."""
    df = df_ibkr.copy()

    print("  Convertendo Chicago -> Sao Paulo (com DST)...")
    df["DataHora_SP_dt"] = chicago_para_sp(df["DataHora"])

    df["Asset"] = ASSET
    df["Data"] = df["DataHora_SP_dt"].dt.strftime("%Y-%m-%d")
    df["Hora_SP_Decimal"] = (
        df["DataHora_SP_dt"].dt.hour
        + df["DataHora_SP_dt"].dt.minute / 60.0
        + df["DataHora_SP_dt"].dt.second / 3600.0
    )
    df["DataHora_SP"] = df["DataHora_SP_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df["ultimo"] = df["close"]
    df["abertura"] = df["open"]
    df["maximo"] = df["high"]
    df["minimo"] = df["low"]
    df["strike"] = 0.0
    df["negocios_acumulado"] = df.get("barCount", pd.Series(0.0, index=df.index)).fillna(0.0)

    return df[COLUNAS_TICKS].copy()


# ============================================================
# APLICAR AO blackarrow_ticks.csv
# ============================================================

def aplicar_payload(df_ticks: pd.DataFrame, sobrescrever: bool) -> None:
    if sobrescrever:
        if ARQUIVO_TICKS.exists():
            backup = ARQUIVO_TICKS.with_name("blackarrow_ticks_BACKUP_antes_ibkr.csv")
            shutil.copy2(ARQUIVO_TICKS, backup)
            print(f"[OK] Backup criado: {backup.name}")

        df_ticks.to_csv(ARQUIVO_TICKS, index=False)
        print(f"[OK] blackarrow_ticks.csv substituido com {len(df_ticks):,} ticks.")

    else:
        if ARQUIVO_TICKS.exists():
            df_existente = pd.read_csv(ARQUIVO_TICKS, encoding="utf-8-sig")
            print(f"  Ticks existentes: {len(df_existente):,}")

            df_combinado = pd.concat([df_existente, df_ticks], ignore_index=True)
            df_combinado = (
                df_combinado
                .drop_duplicates(subset=["DataHora_SP"])
                .sort_values("DataHora_SP")
                .reset_index(drop=True)
            )

            novos = len(df_combinado) - len(df_existente)
            print(f"  Ticks novos: {novos:,}")
            print(f"  Total apos merge: {len(df_combinado):,}")

            df_combinado.to_csv(ARQUIVO_TICKS, index=False)
            print("[OK] blackarrow_ticks.csv atualizado.")
        else:
            df_ticks.to_csv(ARQUIVO_TICKS, index=False)
            print(f"[OK] blackarrow_ticks.csv criado com {len(df_ticks):,} ticks.")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baixa candles do IBKR e aplica como payload no blackarrow_ticks.csv."
    )
    parser.add_argument("--host", default=HOST, help=f"Host do TWS (padrao: {HOST})")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Porta do TWS (7496=real, 7497=paper; padrao: {DEFAULT_PORT})"
    )
    parser.add_argument("--client-id", type=int, default=CLIENT_ID)
    parser.add_argument(
        "--dias", type=int, default=3,
        help="Dias de candles a baixar (padrao: 3). 3 dias = ~2100 candles de 2min."
    )
    parser.add_argument(
        "--sobrescrever", action="store_true",
        help="Substitui o blackarrow_ticks.csv inteiro (padrao: acrescenta)."
    )
    parser.add_argument(
        "--apenas-verificar", action="store_true",
        help="Nao grava nada. Apenas mostra o que seria feito."
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("BAIXAR CANDLES IBKR + PAYLOAD blackarrow_ticks.csv")
    print("=" * 60)

    if not TEM_IB_INSYNC:
        print()
        print("[!] ERRO: ib_insync nao instalado.")
        print("    Instale com: pip install ib_insync")
        print()
        print("    Alternativa sem TWS:")
        print("    python payload_candles_ibkr.py --dias 3")
        print("    (usa dados historicos ja disponiveis, ate 20/05/2026)")
        sys.exit(1)

    if not TEM_PYTZ:
        print()
        print("[!] AVISO: pytz nao instalado. Usando +3h fixo (CST inverno).")
        print("    No verao (CDT) a diferenca e +2h — erro de ate 1 hora.")
        print("    Instale com: pip install pytz")

    # Conecta ao IBKR
    print()
    ib = None
    try:
        ib = conectar(args.host, args.port, args.client_id)

        # Qualifica contrato
        print()
        print(f"Qualificando contrato {CONTRATO_SYMBOL} {CONTRATO_EXPIRACAO}...")
        contrato = qualificar_contrato(ib)

        # Baixa candles
        print()
        print(f"Baixando ultimos {args.dias} dias de candles de 2min...")
        df_ibkr = baixar_periodo(ib, contrato, args.dias)

    except Exception as exc:
        print(f"[!] Erro ao conectar/baixar: {exc}")
        print()
        print("Checklist:")
        print("  - TWS ou IB Gateway precisa estar aberto")
        print("  - API precisa estar habilitada no TWS (Edit -> Global Config -> API)")
        print("  - Porta padrao real: 7496 / paper: 7497")
        print(f"  - Tentando porta: {args.port}")
        print()
        print("Alternativa sem TWS:")
        print("  python payload_candles_ibkr.py --dias 3")
        sys.exit(1)
    finally:
        if ib is not None and ib.isConnected():
            ib.disconnect()
            print("Desconectado do IBKR.")

    if df_ibkr.empty:
        print("[!] Nenhum candle baixado do IBKR.")
        sys.exit(1)

    print()
    print(f"[OK] Candles baixados: {len(df_ibkr):,}")
    print(f"     Periodo (Chicago): {df_ibkr['DataHora'].min()} -> {df_ibkr['DataHora'].max()}")

    # Salva arquivo intermediario
    df_ibkr["contrato"] = ASSET
    df_ibkr.to_csv(ARQUIVO_RECENTE, index=False)
    print(f"[OK] Salvo em: {ARQUIVO_RECENTE.name}")

    # Converte para formato ticks
    print()
    print("Convertendo para formato blackarrow_ticks.csv...")
    df_ticks = ibkr_para_ticks(df_ibkr)

    print(f"  Ticks gerados: {len(df_ticks):,}")
    print(f"  Periodo (SP):  {df_ticks['DataHora_SP'].iloc[0]} -> {df_ticks['DataHora_SP'].iloc[-1]}")

    # Mostra amostra da conversao
    print()
    print("Amostra da conversao Chicago -> SP:")
    for i in range(min(3, len(df_ibkr))):
        row = df_ibkr.iloc[i]
        sp = chicago_para_sp(pd.Series([row["DataHora"]])).iloc[0]
        print(f"  {row['DataHora']}  ->  {sp}")

    if args.apenas_verificar:
        print()
        print("=" * 60)
        print("MODO VERIFICACAO — nada foi gravado.")
        print(f"  Seriam gravados {len(df_ticks):,} ticks em:")
        print(f"  {ARQUIVO_TICKS}")
        print("=" * 60)
        print()
        print("Primeiros 3 ticks:")
        print(df_ticks.head(3).to_string(index=False))
        print()
        print("Ultimos 3 ticks:")
        print(df_ticks.tail(3).to_string(index=False))
        return

    # Aplica payload
    print()
    print("Aplicando payload...")
    aplicar_payload(df_ticks, args.sobrescrever)

    # Resumo
    print()
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)

    df_final = pd.read_csv(ARQUIVO_TICKS)
    print(f"  Total de ticks: {len(df_final):,}")
    print(f"  Inicio:  {df_final['DataHora_SP'].iloc[0]}")
    print(f"  Fim:     {df_final['DataHora_SP'].iloc[-1]}")
    print()

    candles_estimados = len(df_final)
    print(f"  Candles estimados (robo): ~{candles_estimados:,}")
    print(f"  Minimo necessario (robo):  220")
    if candles_estimados >= 220:
        print("  [OK] Suficiente para inicializacao imediata!")
    else:
        print("  [!] Insuficiente — aumente --dias.")

    print()


if __name__ == "__main__":
    main()
