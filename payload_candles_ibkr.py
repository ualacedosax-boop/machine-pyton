# -*- coding: utf-8 -*-
"""
payload_candles_ibkr.py
=======================
Gera o payload de candles para blackarrow_ticks.csv usando dados historicos do IBKR.

TIMEZONE:
  - Os arquivos IBKR (MNQM6_2MIN_IBKR.csv etc.) usam horario de Chicago (CDT/CST).
  - CDT (verao EUA, mar-nov): UTC-5  ->  SP (UTC-3): +2 horas
  - CST (inverno EUA, nov-mar): UTC-6  ->  SP (UTC-3): +3 horas
  - Conversao feita com pytz (lida com DST automaticamente).
  - NOTA: o arquivo MNQ_2026_2MIN_IBKR_CONTINUO.csv tem coluna "DataHora_SP"
    mas o valor e Chicago time (bug do script de geracao) — este script
    trata corretamente, convertendo para SP real.

FONTES (em ordem de preferencia):
  1. Arquivo recente baixado via TWS: MNQ_RECENTE_2MIN_IBKR.csv (se existir)
  2. Arquivo do contrato atual: dados_mnq_2026_ibkr/MNQM6_2MIN_IBKR.csv
  3. Arquivo continuo: dados_mnq_2026_ibkr/MNQ_2026_2MIN_IBKR_CONTINUO.csv

MAPEAMENTO DE COLUNAS:
  blackarrow_ticks.csv  <-  IBKR candle 2min
  -------------------------------------------
  Asset                 <-  "MNQM6" (fixo)
  DataHora_SP           <-  DataHora convertido Chicago -> SP
  Data                  <-  DataHora_SP.date()
  Hora_SP_Decimal       <-  hora + minuto/60 + segundo/3600
  ultimo                <-  close
  abertura              <-  open
  maximo                <-  high
  minimo                <-  low
  strike                <-  0.0 (sem strike para futuros)
  negocios_acumulado    <-  barCount (numero de negocios na barra)

USO:
  python payload_candles_ibkr.py                    # padrao: ultimos 2 dias
  python payload_candles_ibkr.py --dias 5           # ultimos 5 dias de trading
  python payload_candles_ibkr.py --sobrescrever     # substitui blackarrow_ticks.csv
  python payload_candles_ibkr.py --apenas-verificar # nao grava, so mostra o que faria
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

try:
    import pytz
    TZ_CHICAGO = pytz.timezone("America/Chicago")
    TZ_SP = pytz.timezone("America/Sao_Paulo")
    TEM_PYTZ = True
except ImportError:
    TEM_PYTZ = False


# ============================================================
# CAMINHOS
# ============================================================

PASTA_BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PASTA_OPERACIONAL = PASTA_BASE / "operacional_v71_oficial"

ARQUIVO_TICKS = PASTA_OPERACIONAL / "blackarrow_ticks.csv"

# Fontes de dados IBKR (em ordem de preferencia)
FONTES_IBKR = [
    PASTA_BASE / "MNQ_RECENTE_2MIN_IBKR.csv",                        # arquivo baixado manualmente
    PASTA_BASE / "dados_mnq_2026_ibkr" / "MNQM6_2MIN_IBKR.csv",
    PASTA_BASE / "dados_mnq_2026_ibkr" / "MNQ_2026_2MIN_IBKR_CONTINUO.csv",
]

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

ASSET = "MNQM6"


# ============================================================
# CONVERSAO DE TIMEZONE
# ============================================================

def chicago_para_sp(serie_naive: pd.Series) -> pd.Series:
    """
    Converte uma Series de timestamps naive (Chicago time) para SP time (naive).
    Usa pytz se disponivel (correto para DST).
    Fallback: +3h fixo (inverno, conservador - erro max de 1h no verao).
    """
    if TEM_PYTZ:
        localizados = serie_naive.apply(
            lambda dt: TZ_CHICAGO.localize(dt).astimezone(TZ_SP).replace(tzinfo=None)
            if pd.notna(dt)
            else pd.NaT
        )
        return pd.Series(localizados, index=serie_naive.index)
    else:
        # Fallback: +3h (CST/inverno). Aviso emitido no main().
        return serie_naive + pd.Timedelta(hours=3)


def detectar_coluna_datahora(df: pd.DataFrame) -> str:
    """Detecta o nome da coluna de timestamp no arquivo IBKR."""
    candidatas = ["DataHora", "date", "Date", "datetime", "DataHora_SP"]
    for col in candidatas:
        if col in df.columns:
            return col
    raise ValueError(
        "Nenhuma coluna de data/hora encontrada. Colunas: " + str(list(df.columns))
    )


def carregar_ibkr(caminho: Path) -> pd.DataFrame:
    """
    Carrega arquivo IBKR e normaliza para colunas padrao:
    DataHora (Chicago, naive), open, high, low, close, barCount
    """
    print(f"  Lendo: {caminho.name}")

    df = pd.read_csv(caminho, encoding="utf-8-sig")

    if df.empty:
        print("  [!] Arquivo vazio.")
        return pd.DataFrame()

    col_dt = detectar_coluna_datahora(df)

    # Se o arquivo CONTINUO tem DataHora_SP (mas e Chicago — ver TIMEZONE no docstring),
    # vai ser tratado igual: lemos como Chicago e convertemos para SP.
    eh_continuo = col_dt == "DataHora_SP" and "DataHora_Chicago" in df.columns
    if eh_continuo:
        print("  [i] Arquivo continuo detectado. Coluna DataHora_SP sera tratada como Chicago time.")

    # Converte para datetime
    df[col_dt] = pd.to_datetime(df[col_dt], errors="coerce")

    # Se vier com timezone explicito (ex: -05:00), converte para Chicago naive
    try:
        tz = df[col_dt].dt.tz
    except Exception:
        tz = None

    if tz is not None:
        if TEM_PYTZ:
            df[col_dt] = df[col_dt].dt.tz_convert(TZ_CHICAGO).dt.tz_localize(None)
        else:
            df[col_dt] = df[col_dt].dt.tz_localize(None)
    # Se ja e naive, nao faz nada (ja esta em Chicago time)

    df = df.dropna(subset=[col_dt]).copy()

    # Renomeia para "DataHora" (nome padrao interno)
    if col_dt != "DataHora":
        df = df.rename(columns={col_dt: "DataHora"})

    # Normaliza nomes de colunas de preco (case-sensitive)
    renomear = {
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
        "Volume": "volume", "BarCount": "barCount",
    }
    df = df.rename(columns=renomear)

    # Verifica colunas obrigatorias
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(
                f"Coluna '{col}' nao encontrada em {caminho.name}. "
                f"Colunas disponiveis: {list(df.columns)}"
            )

    if "barCount" not in df.columns:
        df["barCount"] = 0.0

    return df[["DataHora", "open", "high", "low", "close", "barCount"]].copy()


# ============================================================
# CONVERSAO PARA FORMATO blackarrow_ticks.csv
# ============================================================

def ibkr_para_ticks(df_ibkr: pd.DataFrame) -> pd.DataFrame:
    """
    Converte DataFrame IBKR (Chicago time) para o formato de blackarrow_ticks.csv (SP time).
    Cada candle de 2min gera um unico tick no timestamp de abertura do candle.
    """
    df = df_ibkr.copy()

    # Converte Chicago -> SP
    print("  Convertendo Chicago -> Sao Paulo (com DST)...")
    df["DataHora_SP_dt"] = chicago_para_sp(df["DataHora"])

    # Colunas derivadas
    df["Asset"] = ASSET
    df["Data"] = df["DataHora_SP_dt"].dt.strftime("%Y-%m-%d")
    df["Hora_SP_Decimal"] = (
        df["DataHora_SP_dt"].dt.hour
        + df["DataHora_SP_dt"].dt.minute / 60.0
        + df["DataHora_SP_dt"].dt.second / 3600.0
    )
    df["DataHora_SP"] = df["DataHora_SP_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Mapeamento de precos
    df["ultimo"] = df["close"]
    df["abertura"] = df["open"]
    df["maximo"] = df["high"]
    df["minimo"] = df["low"]
    df["strike"] = 0.0
    df["negocios_acumulado"] = df["barCount"].fillna(0.0)

    return df[COLUNAS_TICKS].copy()


# ============================================================
# LOGICA PRINCIPAL
# ============================================================

def encontrar_fonte() -> Path | None:
    for caminho in FONTES_IBKR:
        if caminho.exists():
            print(f"[OK] Fonte encontrada: {caminho}")
            return caminho
    return None


def filtrar_ultimos_dias(df: pd.DataFrame, dias: int) -> pd.DataFrame:
    """Filtra para manter apenas os ultimos N dias de trading."""
    df = df.copy()
    df["_dt"] = pd.to_datetime(df["DataHora_SP"])
    data_max = df["_dt"].max()
    data_corte = data_max - pd.Timedelta(days=dias)
    df = df[df["_dt"] >= data_corte].copy()
    df = df.drop(columns=["_dt"])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera payload de candles para blackarrow_ticks.csv usando dados IBKR."
    )
    parser.add_argument(
        "--dias", type=int, default=2,
        help="Numero de dias de trading a incluir no payload (padrao: 2). "
             "2 dias = ~1380 candles de 2min, bem acima do minimo de 220."
    )
    parser.add_argument(
        "--sobrescrever", action="store_true",
        help="Se informado, SUBSTITUI o blackarrow_ticks.csv atual. "
             "Padrao: apenas acrescenta candles mais recentes."
    )
    parser.add_argument(
        "--apenas-verificar", action="store_true",
        help="Nao grava nada. Apenas mostra o que seria feito."
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("PAYLOAD CANDLES IBKR -> blackarrow_ticks.csv")
    print("=" * 60)

    if not TEM_PYTZ:
        print()
        print("[!] AVISO: pytz nao instalado. Usando +3h fixo (CST inverno).")
        print("    No verao (CDT) a diferenca e +2h — erro de ate 1 hora.")
        print("    Instale com: pip install pytz")

    # Localiza arquivo fonte
    fonte = encontrar_fonte()
    if fonte is None:
        print()
        print("[!] Nenhum arquivo IBKR encontrado.")
        print("    Fontes verificadas:")
        for f in FONTES_IBKR:
            print(f"      {f}")
        print()
        print("    Para baixar dados recentes do IBKR:")
        print("    1. Abra o TWS (porta 7496 real / 7497 paper)")
        print("    2. Execute: python baixar_mnq_2026_ibkr_2min.py")
        sys.exit(1)

    # Carrega dados
    print()
    print("Carregando dados IBKR...")
    df_ibkr = carregar_ibkr(fonte)

    if df_ibkr.empty:
        print("[!] Dados IBKR vazios apos carregamento.")
        sys.exit(1)

    print(f"  Candles carregados: {len(df_ibkr):,}")
    print(f"  Periodo (Chicago): {df_ibkr['DataHora'].min()}  ->  {df_ibkr['DataHora'].max()}")

    # Converte para formato de ticks
    print()
    print("Convertendo para formato blackarrow_ticks.csv...")
    df_ticks = ibkr_para_ticks(df_ibkr)

    print(f"  Ticks gerados: {len(df_ticks):,}")
    print(f"  Periodo (SP):  {df_ticks['DataHora_SP'].iloc[0]}  ->  {df_ticks['DataHora_SP'].iloc[-1]}")

    # Filtra pelos ultimos N dias
    print()
    print(f"Filtrando ultimos {args.dias} dias de trading...")
    df_ticks = filtrar_ultimos_dias(df_ticks, args.dias)
    print(f"  Ticks apos filtro: {len(df_ticks):,}")
    if not df_ticks.empty:
        print(f"  Periodo: {df_ticks['DataHora_SP'].iloc[0]}  ->  {df_ticks['DataHora_SP'].iloc[-1]}")

    if df_ticks.empty:
        print("[!] Nenhum tick apos filtro de dias.")
        sys.exit(1)

    # Verifica convertido: mostra 3 candles para inspecao visual
    print()
    print("Amostra da conversao Chicago -> SP:")
    amostra = df_ibkr.head(3).copy()
    amostra["DataHora_SP_calculado"] = chicago_para_sp(amostra["DataHora"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    for _, row in amostra.iterrows():
        print(f"  Chicago: {row['DataHora']}  ->  SP: {row['DataHora_SP_calculado']}")

    # Modo verificacao
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

    # Modo sobrescrever vs. acrescentar
    if args.sobrescrever:
        if ARQUIVO_TICKS.exists():
            backup = ARQUIVO_TICKS.with_name("blackarrow_ticks_BACKUP_antes_ibkr.csv")
            shutil.copy2(ARQUIVO_TICKS, backup)
            print()
            print(f"[OK] Backup criado: {backup.name}")

        print()
        print("Gravando (modo sobrescrever)...")
        df_ticks.to_csv(ARQUIVO_TICKS, index=False)
        print(f"[OK] blackarrow_ticks.csv substituido com {len(df_ticks):,} ticks.")

    else:
        print()
        if ARQUIVO_TICKS.exists():
            print("Acrescentando ao arquivo existente...")
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
            print(f"  Ticks novos adicionados: {novos:,}")
            print(f"  Total apos merge: {len(df_combinado):,}")

            df_combinado.to_csv(ARQUIVO_TICKS, index=False)
            print("[OK] blackarrow_ticks.csv atualizado.")
        else:
            print("Gravando novo arquivo (nao existia)...")
            df_ticks.to_csv(ARQUIVO_TICKS, index=False)
            print(f"[OK] blackarrow_ticks.csv criado com {len(df_ticks):,} ticks.")

    # Resumo final
    print()
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)

    df_final = pd.read_csv(ARQUIVO_TICKS)
    print(f"  Total de ticks: {len(df_final):,}")
    print(f"  Inicio:  {df_final['DataHora_SP'].iloc[0]}")
    print(f"  Fim:     {df_final['DataHora_SP'].iloc[-1]}")

    candles_estimados = len(df_final)
    print()
    print(f"  Candles estimados (robo): ~{candles_estimados:,}")
    print(f"  Minimo necessario (robo):  220")
    if candles_estimados >= 220:
        print("  [OK] Suficiente para inicializacao imediata!")
    else:
        print("  [!] Insuficiente — aumente --dias ou baixe mais dados via IBKR.")

    print()
    print("Primeiros 3 ticks gravados:")
    print(df_final.head(3).to_string(index=False))
    print()
    print("Ultimos 3 ticks gravados:")
    print(df_final.tail(3).to_string(index=False))
    print()


if __name__ == "__main__":
    main()
