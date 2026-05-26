# -*- coding: utf-8 -*-

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ_FEATURES_PACOTE = BASE_DIR / "PACOTE_V4_CAMPEAO_COMPLETO" / "05_operacional_v4" / "features_blackarrow_tempo_real.csv"
ARQ_RTD = BASE_DIR / "blackarrow_rtd.csv"

PASTA_OPERACIONAL = BASE_DIR / "operacional_v4"
ARQ_CANDLES = PASTA_OPERACIONAL / "blackarrow_candles_2min.csv"
ARQ_TICKS = PASTA_OPERACIONAL / "blackarrow_ticks.csv"

QTD_CANDLES = 300


def parse_numero_br(x):
    try:
        if x is None:
            return np.nan
        s = str(x).strip().replace('"', '').replace("'", "")
        if s == "" or s.lower() in ["nan", "none", "null"]:
            return np.nan
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return np.nan


def ler_rtd():
    if not ARQ_RTD.exists():
        return None

    for enc in ["latin1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(ARQ_RTD, sep=";", encoding=enc, dtype=str, engine="python")
            if df.empty:
                continue

            row = df.iloc[-1]
            data_txt = str(row.iloc[1]).replace('"', '').strip()
            hora_txt = str(row.iloc[2]).replace('"', '').strip()
            preco = parse_numero_br(row.iloc[3])
            dt = pd.to_datetime(data_txt + " " + hora_txt, dayfirst=True, errors="coerce")

            if pd.isna(dt):
                dt = pd.Timestamp.now()

            return {"DataHora_SP": dt, "preco": preco}
        except Exception:
            pass

    return None


def main():
    print("=====================================================")
    print("RESTAURAR CANDLES V4 A PARTIR DO PACOTE CAMPEAO")
    print("=====================================================")

    if not ARQ_FEATURES_PACOTE.exists():
        raise FileNotFoundError(f"Nao encontrei: {ARQ_FEATURES_PACOTE}")

    PASTA_OPERACIONAL.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(ARQ_FEATURES_PACOTE, low_memory=False)

    obrigatorias = ["DataHora_SP", "open", "high", "low", "close"]
    faltando = [c for c in obrigatorias if c not in df.columns]

    if faltando:
        raise RuntimeError(f"Features do pacote nao tem colunas necessarias: {faltando}")

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["DataHora_SP", "open", "high", "low", "close"]).copy()
    df = df.sort_values("DataHora_SP").drop_duplicates(subset=["DataHora_SP"], keep="last")

    if "volume" not in df.columns:
        df["volume"] = 0
    if "average" not in df.columns:
        df["average"] = df["close"]
    if "barCount" not in df.columns:
        df["barCount"] = 0
    if "ticks_no_candle" not in df.columns:
        df["ticks_no_candle"] = df["barCount"]

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df["average"] = pd.to_numeric(df["average"], errors="coerce").fillna(df["close"])
    df["barCount"] = pd.to_numeric(df["barCount"], errors="coerce").fillna(0)
    df["ticks_no_candle"] = pd.to_numeric(df["ticks_no_candle"], errors="coerce").fillna(df["barCount"])

    df["DataHora_SP"] = df["DataHora_SP"].dt.floor("2min")
    df["DataHora_Chicago"] = df["DataHora_SP"]
    df["Data"] = df["DataHora_SP"].dt.date.astype(str)
    df["Hora_SP_Decimal"] = (
        df["DataHora_SP"].dt.hour
        + df["DataHora_SP"].dt.minute / 60.0
        + df["DataHora_SP"].dt.second / 3600.0
    )

    colunas_candles = [
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "Hora_SP_Decimal",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "average",
        "barCount",
        "ticks_no_candle",
    ]

    candles = df[colunas_candles].tail(QTD_CANDLES).copy().reset_index(drop=True)

    agora = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_backup = PASTA_OPERACIONAL / f"BACKUP_antes_restaurar_features_pacote_{agora}"
    pasta_backup.mkdir(parents=True, exist_ok=True)

    for arq in [ARQ_CANDLES, ARQ_TICKS]:
        if arq.exists():
            destino = pasta_backup / arq.name
            arq.replace(destino)
            print("Backup:", destino)

    candles.to_csv(ARQ_CANDLES, index=False, encoding="utf-8-sig")

    rtd = ler_rtd()

    if rtd is not None and not pd.isna(rtd["preco"]):
        dt = pd.to_datetime(rtd["DataHora_SP"], errors="coerce")
        tick = pd.DataFrame([{
            "DataHora_SP": dt,
            "Data": dt.date(),
            "Hora_SP_Decimal": dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
            "ultimo": float(rtd["preco"]),
            "abertura": np.nan,
            "maximo": np.nan,
            "minimo": np.nan,
            "negocios_acumulado": np.nan,
        }])
    else:
        ult = candles.iloc[-1]
        dt = pd.to_datetime(ult["DataHora_SP"])
        tick = pd.DataFrame([{
            "DataHora_SP": dt,
            "Data": ult["Data"],
            "Hora_SP_Decimal": ult["Hora_SP_Decimal"],
            "ultimo": ult["close"],
            "abertura": ult["open"],
            "maximo": ult["high"],
            "minimo": ult["low"],
            "negocios_acumulado": np.nan,
        }])

    tick.to_csv(ARQ_TICKS, index=False, encoding="utf-8-sig")

    print("\nArquivos restaurados:")
    print(ARQ_CANDLES)
    print(ARQ_TICKS)

    print("\nResumo candles:")
    print("Linhas:", len(candles))
    print("Primeiro:", candles["DataHora_SP"].min())
    print("Ultimo  :", candles["DataHora_SP"].max())
    print("Close ultimo:", candles["close"].iloc[-1])

    print("\nResumo tick:")
    print(tick.tail(1).to_string(index=False))

    print("\nPronto. Reinicie o robo V4.")


if __name__ == "__main__":
    main()
