import os
import json
import time
import warnings
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


# =====================================================
# CONFIGURAÃƒâ€¡Ãƒâ€¢ES GERAIS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V3 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")
PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")
PASTA_V5_1 = os.path.join(BASE_DIR, "OPERACIONAL_V5_1_CAMPEA")
PASTA_OPERACIONAL = os.path.join(BASE_DIR, "operacional_v4")
os.makedirs(PASTA_OPERACIONAL, exist_ok=True)

ARQUIVO_BLACKARROW_RTD = os.path.join(BASE_DIR, "blackarrow_rtd.csv")

ARQUIVO_TICKS = os.path.join(PASTA_OPERACIONAL, "blackarrow_ticks.csv")
ARQUIVO_CANDLES = os.path.join(PASTA_OPERACIONAL, "blackarrow_candles_2min.csv")
ARQUIVO_FEATURES_TEMPO_REAL = os.path.join(PASTA_OPERACIONAL, "features_blackarrow_tempo_real.csv")

ARQUIVO_SINAL_TXT = os.path.join(PASTA_OPERACIONAL, "sinal.txt")
ARQUIVO_ULTIMO_SINAL_JSON = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v4_blackarrow.json")
ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_blackarrow.csv")
ARQUIVO_LOG_RESERVA = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_blackarrow_reserva.csv")
ARQUIVO_ESTADO = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v4_blackarrow.json")

ARQUIVO_MODELO_V3 = os.path.join(PASTA_V3, "modelo_v3_score.joblib")
ARQUIVO_FEATURES_V3 = os.path.join(PASTA_V3, "features_v3_score.joblib")
ARQUIVO_CONFIG_V3 = os.path.join(PASTA_V3, "config_modelo_v3_score.json")

ARQUIVO_CONFIG_V4 = os.path.join(PASTA_V4, "config_melhor_v4.json")
ARQUIVO_MODELO_V4 = os.path.join(PASTA_V5_1, "modelo_v5_1_campea.joblib")
ARQUIVO_FEATURES_V4 = os.path.join(PASTA_V5_1, "features_v5_1_campea.joblib")

RODAR_EM_LOOP = True
INTERVALO_SEGUNDOS = 1

MODO_SEGURO_SEM_ORDEM = True

CANDLES_MINIMOS = 220

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# =====================================================
# FUNÃƒâ€¡Ãƒâ€¢ES DE ARQUIVO
# =====================================================



# ============================================================
# LIMPEZA DE INF / NAN PARA MODELOS ML
# ============================================================



# ============================================================
# GARANTIR COLUNA DataHora_SP
# ============================================================



# ============================================================
# CORRIGIR SERIE ULTIMA COM DADOS DE HORARIO DO DF ORIGINAL
# ============================================================



# ============================================================
# OBTER COLUNA FLEXIVEL DO BLACKARROW
# ============================================================

def obter_valor_coluna_flexivel(row, nomes, padrao=np.nan):
    try:
        # tenta nomes exatos
        for nome in nomes:
            if nome in row.index:
                return row.get(nome, padrao)

        # tenta ignorando acentos, maiusculas e caracteres quebrados
        mapa = {}
        for col in row.index:
            chave = str(col).strip().lower()
            chave = (
                chave.replace("Ã¡", "a")
                     .replace("Ã ", "a")
                     .replace("Ã£", "a")
                     .replace("Ã¢", "a")
                     .replace("Ã©", "e")
                     .replace("Ãª", "e")
                     .replace("Ã­", "i")
                     .replace("Ã³", "o")
                     .replace("Ã´", "o")
                     .replace("Ãµ", "o")
                     .replace("Ãº", "u")
                     .replace("Ã§", "c")
            )
            mapa[chave] = col

        for nome in nomes:
            chave = str(nome).strip().lower()
            chave = (
                chave.replace("Ã¡", "a")
                     .replace("Ã ", "a")
                     .replace("Ã£", "a")
                     .replace("Ã¢", "a")
                     .replace("Ã©", "e")
                     .replace("Ãª", "e")
                     .replace("Ã­", "i")
                     .replace("Ã³", "o")
                     .replace("Ã´", "o")
                     .replace("Ãµ", "o")
                     .replace("Ãº", "u")
                     .replace("Ã§", "c")
            )
            if chave in mapa:
                return row.get(mapa[chave], padrao)

        return padrao
    except Exception:
        return padrao


def corrigir_ultima_com_df_feat(ultima, df_feat):
    import pandas as pd

    try:
        if ultima is None:
            return ultima

        if df_feat is None or len(df_feat) == 0:
            if "DataHora_SP" not in ultima.index:
                ultima["DataHora_SP"] = pd.Timestamp.now()
            if "Data" not in ultima.index:
                ultima["Data"] = pd.Timestamp.now().date()
            if "Hora_SP_Decimal" not in ultima.index:
                agora = pd.Timestamp.now()
                ultima["Hora_SP_Decimal"] = agora.hour + agora.minute / 60.0 + agora.second / 3600.0
            return ultima

        base = df_feat.copy()

        if "DataHora_SP" not in base.columns:
            base = garantir_coluna_datahora_sp(base)

        if "DataHora_SP" in base.columns:
            dt = pd.to_datetime(base["DataHora_SP"].iloc[-1], errors="coerce")
            if pd.isna(dt):
                dt = pd.Timestamp.now()

            ultima["DataHora_SP"] = dt

            if "Data" not in ultima.index:
                ultima["Data"] = dt.date()

            if "Hora_SP_Decimal" not in ultima.index:
                ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        else:
            dt = pd.Timestamp.now()
            ultima["DataHora_SP"] = dt

            if "Data" not in ultima.index:
                ultima["Data"] = dt.date()

            if "Hora_SP_Decimal" not in ultima.index:
                ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        return ultima

    except Exception:
        try:
            dt = pd.Timestamp.now()
            ultima["DataHora_SP"] = dt
            ultima["Data"] = dt.date()
            ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        except Exception:
            pass

        return ultima


def garantir_coluna_datahora_sp(df):
    import pandas as pd

    if df is None:
        return df

    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        return df

    candidatas = [
        "datahora_ultimo_candle_sp",
        "datahora_candle_sp",
        "datahora_sp",
        "DataHora",
        "datahora",
        "datetime",
        "time",
        "date",
        "Date",
        "Time",
    ]

    for col in candidatas:
        if col in df.columns:
            df["DataHora_SP"] = pd.to_datetime(df[col], errors="coerce")
            return df

    return df


def limpar_inf_nan_ml(X):
    import numpy as np
    import pandas as pd

    if isinstance(X, pd.DataFrame):
        X = X.replace([np.inf, -np.inf], 0)
        X = X.fillna(0)

        for col in X.columns:
            try:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
            except Exception:
                X[col] = 0

        return X

    try:
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        return X


def salvar_txt_seguro(texto, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        f.write(str(texto).strip().lower())

    try:
        if os.path.exists(caminho):
            os.remove(caminho)

        os.rename(temp, caminho)

    except PermissionError:
        # Se o arquivo estiver ocupado, tenta escrever direto.
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(str(texto).strip().lower())

        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass


def salvar_json_seguro(obj, caminho):
    temp = caminho + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4, default=str)

    try:
        if os.path.exists(caminho):
            os.remove(caminho)

        os.rename(temp, caminho)

    except PermissionError:
        # Se estiver ocupado, salva reserva.
        reserva = caminho.replace(".json", "_reserva.json")

        with open(reserva, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=4, default=str)

        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass


def salvar_csv_seguro(df, caminho):
    temp = caminho + ".tmp"

    df.to_csv(temp, index=False, encoding="latin1")

    try:
        if os.path.exists(caminho):
            os.remove(caminho)

        os.rename(temp, caminho)

    except PermissionError:
        reserva = caminho.replace(".csv", "_reserva.csv")
        df.to_csv(reserva, index=False, encoding="latin1")

        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass


def append_log(payload):
    """
    Salva o log sem apagar o arquivo existente.
    Isso evita WinError 32 quando o monitor PowerShell estÃƒÂ¡ lendo o CSV.
    """

    df_linha = pd.DataFrame([payload])

    try:
        arquivo_existe = os.path.exists(ARQUIVO_LOG)

        df_linha.to_csv(
            ARQUIVO_LOG,
            mode="a",
            index=False,
            header=not arquivo_existe,
            encoding="latin1"
        )

    except PermissionError:
        arquivo_existe = os.path.exists(ARQUIVO_LOG_RESERVA)

        df_linha.to_csv(
            ARQUIVO_LOG_RESERVA,
            mode="a",
            index=False,
            header=not arquivo_existe,
            encoding="latin1"
        )

        print("AVISO: log principal ocupado. Registro salvo no log reserva:")
        print(ARQUIVO_LOG_RESERVA)


def carregar_json(caminho):
    if not os.path.exists(caminho):
        return {}

    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# CONFIG / MODELOS
# =====================================================

def carregar_config_v4():
    if not os.path.exists(ARQUIVO_CONFIG_V4):
        raise FileNotFoundError(f"NÃƒÂ£o encontrei: {ARQUIVO_CONFIG_V4}")

    config = carregar_json(ARQUIVO_CONFIG_V4)

    config["take_pontos"] = float(config["take_pontos"])
    config["stop_pontos"] = float(config["stop_pontos"])
    config["prob_win_min"] = float(config["prob_win_min"])
    config["max_trades_dia"] = int(config["max_trades_dia"])
    config["parar_apos_loss"] = str(config["parar_apos_loss"]).lower() in ["true", "1", "sim", "yes"]
    config["score_buy_min"] = float(config["score_buy_min"])
    config["score_sell_min"] = float(config["score_sell_min"])
    config["diferenca_minima"] = float(config["diferenca_minima"])
    config["hora_inicio"] = float(config["hora_inicio"])
    config["hora_fim"] = float(config["hora_fim"])

    config["bloquear_0430_0444"] = str(config.get("bloquear_0430_0444", False)).lower() in ["true", "1", "sim", "yes"]
    config["hora_bloqueio_inicio"] = float(config.get("hora_bloqueio_inicio", 999.0))
    config["hora_bloqueio_fim"] = float(config.get("hora_bloqueio_fim", -999.0))

    return config


def carregar_modelo_v3():
    if not os.path.exists(ARQUIVO_MODELO_V3):
        raise FileNotFoundError(f"NÃƒÂ£o encontrei modelo V3: {ARQUIVO_MODELO_V3}")

    if not os.path.exists(ARQUIVO_FEATURES_V3):
        raise FileNotFoundError(f"NÃƒÂ£o encontrei features V3: {ARQUIVO_FEATURES_V3}")

    modelo = joblib.load(ARQUIVO_MODELO_V3)
    features = joblib.load(ARQUIVO_FEATURES_V3)
    config = carregar_json(ARQUIVO_CONFIG_V3)

    print("Modelo V3 carregado:", ARQUIVO_MODELO_V3)
    print("Features V3:", len(features))

    return modelo, features, config


def carregar_modelo_v4():
    if not os.path.exists(ARQUIVO_MODELO_V4):
        raise FileNotFoundError(f"NÃƒÂ£o encontrei modelo V4: {ARQUIVO_MODELO_V4}")

    if not os.path.exists(ARQUIVO_FEATURES_V4):
        raise FileNotFoundError(f"NÃƒÂ£o encontrei features V4: {ARQUIVO_FEATURES_V4}")

    modelo = joblib.load(ARQUIVO_MODELO_V4)
    features = joblib.load(ARQUIVO_FEATURES_V4)

    print("Modelo operacional carregado:", ARQUIVO_MODELO_V4)
    print("Features operacional:", len(features))

    return modelo, features


# =====================================================
# LEITURA BLACKARROW RTD
# =====================================================

def parse_numero_br(valor):
    if pd.isna(valor):
        return np.nan

    s = str(valor).strip().replace('"', '')

    if s == "":
        return np.nan

    s = s.replace(".", "")
    s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return np.nan



def ler_blackarrow_rtd():
    if not os.path.exists(ARQUIVO_BLACKARROW_RTD):
        raise FileNotFoundError(f"Nao encontrei: {ARQUIVO_BLACKARROW_RTD}")

    ultimo_erro = None
    df = None

    # O BlackArrow costuma exportar com ; e encoding ANSI/latin1/cp1252
    for enc in ["latin1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(
                ARQUIVO_BLACKARROW_RTD,
                sep=";",
                encoding=enc,
                dtype=str,
                engine="python"
            )
            break
        except Exception as e:
            ultimo_erro = e
            df = None

    if df is None:
        raise Exception(f"Falha ao ler blackarrow_rtd.csv: {ultimo_erro}")

    if df.empty:
        raise Exception("Arquivo blackarrow_rtd.csv esta vazio.")

    row = df.iloc[-1]

    def valor_pos(pos, padrao=np.nan):
        try:
            if len(row) > pos:
                return row.iloc[pos]
        except Exception:
            pass
        return padrao

    def num(x):
        try:
            if x is None:
                return np.nan

            s = str(x).strip()

            if s == "" or s.lower() in ["nan", "none", "null"]:
                return np.nan

            s = s.replace('"', '').replace("'", "").strip()

            # Formato BR: 29.542,25 ou 29542,25
            if "," in s:
                s = s.replace(".", "")
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")

            return float(s)
        except Exception:
            return np.nan

    asset = str(valor_pos(0, "")).replace('"', '').strip()
    data_txt = str(valor_pos(1, "")).replace('"', '').strip()
    hora_txt = str(valor_pos(2, "")).replace('"', '').strip()

    # Preferencia absoluta pela posicao do arquivo RTD:
    # coluna 3 = Ultimo
    ultimo = num(valor_pos(3, np.nan))

    abertura = num(valor_pos(4, np.nan))
    maximo = num(valor_pos(5, np.nan))
    minimo = num(valor_pos(6, np.nan))
    strike = num(valor_pos(7, np.nan))
    negocios = num(valor_pos(8, np.nan))

    if pd.isna(ultimo):
        # Diagnostico simples para aparecer no erro
        try:
            cols = list(df.columns)
            vals = [str(valor_pos(i, "")) for i in range(min(len(row), 10))]
            raise Exception(f"Preco Ultimo invalido no CSV do BlackArrow. Colunas={cols}; Valores={vals}")
        except Exception as e:
            raise Exception(str(e))

    datahora_sp = pd.to_datetime(
        data_txt + " " + hora_txt,
        dayfirst=True,
        errors="coerce"
    )

    if pd.isna(datahora_sp):
        datahora_sp = pd.Timestamp.now()

    return {
        "Asset": asset,
        "DataHora_SP": datahora_sp,
        "Data": datahora_sp.date(),
        "Hora_SP_Decimal": datahora_sp.hour + datahora_sp.minute / 60.0 + datahora_sp.second / 3600.0,
        "ultimo": float(ultimo),
        "abertura": float(abertura) if not pd.isna(abertura) else np.nan,
        "maximo": float(maximo) if not pd.isna(maximo) else np.nan,
        "minimo": float(minimo) if not pd.isna(minimo) else np.nan,
        "strike": float(strike) if not pd.isna(strike) else np.nan,
        "negocios_acumulado": float(negocios) if not pd.isna(negocios) else np.nan,
    }


def atualizar_ticks(tick):
    df_tick = pd.DataFrame([tick])

    if os.path.exists(ARQUIVO_TICKS):
        ticks = pd.read_csv(ARQUIVO_TICKS, low_memory=False)
        ticks["DataHora_SP"] = pd.to_datetime(ticks["DataHora_SP"], errors="coerce")

        ultimo_registro = ticks.iloc[-1]

        mesmo_tempo = str(ultimo_registro["DataHora_SP"]) == str(tick["DataHora_SP"])
        mesmo_preco = float(ultimo_registro["ultimo"]) == float(tick["ultimo"])
        mesmo_negocios = str(ultimo_registro.get("negocios_acumulado", "")) == str(tick.get("negocios_acumulado", ""))

        if mesmo_tempo and mesmo_preco and mesmo_negocios:
            return ticks

        ticks = pd.concat([ticks, df_tick], ignore_index=True)

        if len(ticks) > 30000:
            ticks = ticks.tail(30000).reset_index(drop=True)

        salvar_csv_seguro(ticks, ARQUIVO_TICKS)

        return ticks

    salvar_csv_seguro(df_tick, ARQUIVO_TICKS)
    return df_tick


# =====================================================
# MONTAR CANDLES 2 MIN
# =====================================================

def montar_candles_2min(ticks):
    if ticks.empty:
        return pd.DataFrame()

    base = ticks.copy()
    base["DataHora_SP"] = pd.to_datetime(base["DataHora_SP"], errors="coerce")
    base = base.dropna(subset=["DataHora_SP"])
    base = base.sort_values("DataHora_SP").reset_index(drop=True)

    base["ultimo"] = pd.to_numeric(base["ultimo"], errors="coerce")
    base["negocios_acumulado"] = pd.to_numeric(base["negocios_acumulado"], errors="coerce")

    base = base.dropna(subset=["ultimo"])

    if base.empty:
        return pd.DataFrame()

    base["candle_time"] = base["DataHora_SP"].dt.floor("2min")

    candles = base.groupby("candle_time").agg(
        open=("ultimo", "first"),
        high=("ultimo", "max"),
        low=("ultimo", "min"),
        close=("ultimo", "last"),
        negocios_inicio=("negocios_acumulado", "first"),
        negocios_fim=("negocios_acumulado", "last"),
        ticks_no_candle=("ultimo", "count"),
        Asset=("Asset", "last"),
    ).reset_index()

    candles = candles.rename(columns={"candle_time": "DataHora_SP"})

    candles["volume"] = candles["negocios_fim"] - candles["negocios_inicio"]
    candles["volume"] = candles["volume"].fillna(0)

    candles.loc[candles["volume"] < 0, "volume"] = candles["ticks_no_candle"]

    candles["Data"] = candles["DataHora_SP"].dt.date
    candles["Hora_SP_Decimal"] = candles["DataHora_SP"].dt.hour + candles["DataHora_SP"].dt.minute / 60.0

    candles["DataHora_Chicago"] = candles["DataHora_SP"]
    candles["contrato"] = candles["Asset"]
    candles["localSymbol"] = candles["Asset"]

    candles["average"] = candles["close"]
    candles["barCount"] = candles["ticks_no_candle"]
    candles["conId"] = 0

    candles = candles[[
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
        "conId",
        "ticks_no_candle",
        "contrato",
        "localSymbol",
    ]].copy()

    salvar_csv_seguro(candles, ARQUIVO_CANDLES)

    return candles


# =====================================================
# INDICADORES / FEATURES
# =====================================================

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def rma(series, n):
    return series.ewm(alpha=1 / n, adjust=False).mean()


def sma(series, n):
    return series.rolling(n).mean()


def calcular_rsi(close, n):
    delta = close.diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    avg_gain = rma(ganho, n)
    avg_loss = rma(perda, n)

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def calcular_stoch_rsi(close, rsi_len=14, stoch_len=14, smooth_k=3, smooth_d=3):
    rsi_base = calcular_rsi(close, rsi_len)

    rsi_min = rsi_base.rolling(stoch_len).min()
    rsi_max = rsi_base.rolling(stoch_len).max()

    stoch_raw = (rsi_base - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100

    k = sma(stoch_raw, smooth_k)
    d = sma(k, smooth_d)

    return k, d


def calcular_macd(close, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    macd_signal = ema(macd_line, signal)
    macd_hist = macd_line - macd_signal

    return macd_line, macd_signal, macd_hist


def calcular_adx(df, n=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    tr_rma = rma(tr, n)

    plus_di = 100 * rma(pd.Series(plus_dm, index=df.index), n) / tr_rma.replace(0, np.nan)
    minus_di = 100 * rma(pd.Series(minus_dm, index=df.index), n) / tr_rma.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = rma(dx, n)

    return adx, plus_di, minus_di, tr


def adicionar_sequencias(base):
    base["candle_alta"] = (base["close"] > base["open"]).astype(int)
    base["candle_baixa"] = (base["close"] < base["open"]).astype(int)

    for n in [2, 3, 4, 5, 8, 10]:
        base[f"seq_alta_{n}"] = base["candle_alta"].rolling(n).sum()
        base[f"seq_baixa_{n}"] = base["candle_baixa"].rolling(n).sum()

    return base


def adicionar_features_prev(base):
    colunas_para_prev = []

    ignorar = {
        "DataHora_SP",
        "DataHora_Chicago",
        "Data",
        "contrato",
        "localSymbol",
        "Asset",
        "Label_Nome",
    }

    for col in base.columns:
        if col in ignorar:
            continue

        if col.startswith("prev_"):
            continue

        if pd.api.types.is_numeric_dtype(base[col]):
            colunas_para_prev.append(col)

    novas = {}

    for col in colunas_para_prev:
        novas[f"prev_{col}"] = base[col].shift(1)

    if novas:
        prev_df = pd.DataFrame(novas, index=base.index)
        base = pd.concat([base, prev_df], axis=1)

    return base.copy()


def garantir_features_esperadas(base, features_esperadas):
    """
    Garante que todas as features esperadas existam e que cada uma seja 1-dimensional.
    Corrige erro:
    Data must be 1-dimensional, got ndarray of shape (..., 2)
    """

    # Remove qualquer coluna duplicada antes de criar features faltantes.
    base = base.loc[:, ~base.columns.duplicated()].copy()

    aliases = {
        "hora_sp": "Hora_SP_Decimal",
        "dia_semana_sp": "dia_semana",
        "mes_sp": "mes",
        "sin_hora_sp": "sin_hora",
        "cos_hora_sp": "cos_hora",
    }

    def pegar_coluna_1d(df, nome):
        """
        Retorna sempre uma Series 1D.
        Se por algum motivo vier DataFrame com colunas duplicadas, pega a primeira.
        """
        if nome not in df.columns:
            return None

        valor = df[nome]

        if isinstance(valor, pd.DataFrame):
            valor = valor.iloc[:, 0]

        return pd.Series(valor, index=df.index)

    novas = {}

    # Remove duplicidade tambÃƒÂ©m da lista de features esperadas.
    features_unicas = []
    vistas = set()

    for f in features_esperadas:
        if f not in vistas:
            features_unicas.append(f)
            vistas.add(f)

    for feature in features_unicas:
        if feature in base.columns:
            continue

        valor_final = None

        if feature.startswith("prev_"):
            sem_prev = feature[5:]

            col = pegar_coluna_1d(base, sem_prev)

            if col is not None:
                valor_final = col.shift(1)

            elif sem_prev in aliases:
                alias = aliases[sem_prev]
                col_alias = pegar_coluna_1d(base, alias)

                if col_alias is not None:
                    valor_final = col_alias.shift(1)

        else:
            if feature in aliases:
                alias = aliases[feature]
                col_alias = pegar_coluna_1d(base, alias)

                if col_alias is not None:
                    valor_final = col_alias

        if valor_final is None:
            valor_final = pd.Series(np.nan, index=base.index)

        # Garantia final: nunca deixar entrar 2D no dicionÃƒÂ¡rio.
        if isinstance(valor_final, pd.DataFrame):
            valor_final = valor_final.iloc[:, 0]

        valor_final = pd.Series(valor_final, index=base.index)

        novas[feature] = valor_final

    if novas:
        novas_df = pd.DataFrame(novas, index=base.index)
        novas_df = novas_df.loc[:, ~novas_df.columns.duplicated()].copy()

        base = pd.concat([base, novas_df], axis=1)
        base = base.loc[:, ~base.columns.duplicated()].copy()

    return base.copy()



def preparar_features_tempo_real(df, features_v3, features_v4):
    base = df.copy()

    base = base.sort_values("DataHora_SP").reset_index(drop=True)

    base["DataHora_SP"] = pd.to_datetime(base["DataHora_SP"], errors="coerce")

    base["open"] = pd.to_numeric(base["open"], errors="coerce")
    base["high"] = pd.to_numeric(base["high"], errors="coerce")
    base["low"] = pd.to_numeric(base["low"], errors="coerce")
    base["close"] = pd.to_numeric(base["close"], errors="coerce")
    base["volume"] = pd.to_numeric(base["volume"], errors="coerce").fillna(0)
    base["average"] = pd.to_numeric(base.get("average", base["close"]), errors="coerce")
    base["barCount"] = pd.to_numeric(base.get("barCount", base.get("ticks_no_candle", 0)), errors="coerce").fillna(0)
    base["conId"] = pd.to_numeric(base.get("conId", 0), errors="coerce").fillna(0)

    novas = {}

    novas["range"] = base["high"] - base["low"]
    novas["body"] = base["close"] - base["open"]
    novas["body_abs"] = novas["body"].abs()

    temp_oc_max = base[["open", "close"]].max(axis=1)
    temp_oc_min = base[["open", "close"]].min(axis=1)

    novas["upper_wick"] = base["high"] - temp_oc_max
    novas["lower_wick"] = temp_oc_min - base["low"]
    novas["body_range_pct"] = novas["body_abs"] / novas["range"].replace(0, np.nan)
    novas["close_pos_range"] = (base["close"] - base["low"]) / novas["range"].replace(0, np.nan)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)
    base = adicionar_sequencias(base)

    novas = {}

    novas["hora_sp"] = base["DataHora_SP"].dt.hour
    novas["minuto_sp"] = base["DataHora_SP"].dt.minute
    novas["Hora_SP_Decimal"] = base["DataHora_SP"].dt.hour + base["DataHora_SP"].dt.minute / 60.0
    novas["dia_semana_sp"] = pd.to_datetime(base["DataHora_SP"]).dt.dayofweek
    novas["mes_sp"] = pd.to_datetime(base["DataHora_SP"]).dt.month
    novas["sin_hora_sp"] = np.sin(2 * np.pi * novas["Hora_SP_Decimal"] / 24.0)
    novas["cos_hora_sp"] = np.cos(2 * np.pi * novas["Hora_SP_Decimal"] / 24.0)
    novas["sin_hora"] = novas["sin_hora_sp"]
    novas["cos_hora"] = novas["cos_hora_sp"]
    novas["dia_semana"] = novas["dia_semana_sp"]
    novas["mes"] = novas["mes_sp"]

    novas["eh_0348"] = ((novas["hora_sp"] == 3) & (novas["minuto_sp"] == 48)).astype(int)
    novas["eh_0448"] = ((novas["hora_sp"] == 4) & (novas["minuto_sp"] == 48)).astype(int)

    novas["janela_0340_0400"] = (
        (novas["Hora_SP_Decimal"] >= 3 + 40 / 60) &
        (novas["Hora_SP_Decimal"] <= 4.0)
    ).astype(int)

    novas["janela_0430_0500"] = (
        (novas["Hora_SP_Decimal"] >= 4.5) &
        (novas["Hora_SP_Decimal"] <= 5.0)
    ).astype(int)

    novas["janela_0000_0600"] = (
        (novas["Hora_SP_Decimal"] >= 0.0) &
        (novas["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    novas["janela_0300_0600"] = (
        (novas["Hora_SP_Decimal"] >= 3.0) &
        (novas["Hora_SP_Decimal"] <= 6.0)
    ).astype(int)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    novas["logret_1"] = np.log(base["close"] / base["close"].shift(1))
    novas["ret_1"] = base["close"].pct_change(1)
    novas["pts_change_1"] = base["close"] - base["close"].shift(1)
    novas["volatilidade_ret_1"] = novas["logret_1"].rolling(2).std()

    for n in [2, 3, 5, 8, 10, 15, 20, 30, 60, 120]:
        novas[f"ret_{n}"] = base["close"].pct_change(n)
        novas[f"pts_change_{n}"] = base["close"] - base["close"].shift(n)
        novas[f"volatilidade_ret_{n}"] = novas["logret_1"].rolling(n).std()

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [3, 5, 8, 9, 10, 12, 17, 20, 21, 26, 34, 50, 55, 72, 89, 100, 144, 200]:
        novas[f"sma_{n}"] = sma(base["close"], n)
        novas[f"ema_{n}"] = ema(base["close"], n)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [9, 17, 34, 50, 72, 100, 200]:
        novas[f"dist_ema_{n}"] = base["close"] - base[f"ema_{n}"]

    novas["ema_17_slope_3"] = base["ema_17"] - base["ema_17"].shift(3)
    novas["ema_34_slope_3"] = base["ema_34"] - base["ema_34"].shift(3)
    novas["ema_50_slope_3"] = base["ema_50"] - base["ema_50"].shift(3)
    novas["ema_200_slope_3"] = base["ema_200"] - base["ema_200"].shift(3)

    novas["ema_9_acima_17"] = (base["ema_9"] > base["ema_17"]).astype(int)
    novas["ema_17_acima_34"] = (base["ema_17"] > base["ema_34"]).astype(int)
    novas["ema_34_acima_50"] = (base["ema_34"] > base["ema_50"]).astype(int)
    novas["ema_50_acima_200"] = (base["ema_50"] > base["ema_200"]).astype(int)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    novas["pv"] = base["close"] * base["volume"]
    volume_acum = base.groupby("Data")["volume"].cumsum().replace(0, np.nan)
    pv_acum = pd.Series(novas["pv"], index=base.index).groupby(base["Data"]).cumsum()

    novas["vwap_dia"] = pv_acum / volume_acum
    novas["dist_vwap_dia"] = base["close"] - novas["vwap_dia"]
    novas["close_acima_vwap"] = (base["close"] > novas["vwap_dia"]).astype(int)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    adx14, plus_di14, minus_di14, tr = calcular_adx(base, 14)

    novas = {}

    novas["tr"] = tr
    novas["adx_14"] = adx14
    novas["plus_di_14"] = plus_di14
    novas["minus_di_14"] = minus_di14
    novas["di_diff_14"] = plus_di14 - minus_di14

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [7, 10, 14, 18, 20, 21, 34, 50]:
        atr_n = rma(base["tr"], n)
        kc_mid = ema(base["close"], n)
        kc_upper = kc_mid + 2.0 * atr_n
        kc_lower = kc_mid - 2.0 * atr_n

        novas[f"atr_{n}"] = atr_n
        novas[f"atrp_{n}"] = atr_n / base["close"] * 100
        novas[f"kc_mid_{n}"] = kc_mid
        novas[f"kc_upper_{n}"] = kc_upper
        novas[f"kc_lower_{n}"] = kc_lower
        novas[f"kc_width_{n}"] = (kc_upper - kc_lower) / kc_mid.replace(0, np.nan) * 100
        novas[f"kc_pos_{n}"] = (base["close"] - kc_lower) / (kc_upper - kc_lower).replace(0, np.nan)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [20, 34]:
        bb_mid = sma(base["close"], n)
        bb_std = base["close"].rolling(n).std()

        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std

        novas[f"bb_mid_{n}"] = bb_mid
        novas[f"bb_upper_{n}"] = bb_upper
        novas[f"bb_lower_{n}"] = bb_lower
        novas[f"bb_width_{n}"] = (bb_upper - bb_lower) / bb_mid.replace(0, np.nan) * 100
        novas[f"bb_pos_{n}"] = (base["close"] - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [7, 9, 14, 21, 34]:
        rsi_n = calcular_rsi(base["close"], n)
        novas[f"rsi_{n}"] = rsi_n
        novas[f"rsi_{n}_slope_3"] = rsi_n - rsi_n.shift(3)

    stoch_k, stoch_d = calcular_stoch_rsi(base["close"], 14, 14, 3, 3)

    novas["stochrsi_k"] = stoch_k
    novas["stochrsi_d"] = stoch_d
    novas["stochrsi_diff"] = stoch_k - stoch_d

    macd_line, macd_signal, macd_hist = calcular_macd(base["close"], 12, 26, 9)

    novas["macd_line"] = macd_line
    novas["macd_signal"] = macd_signal
    novas["macd_hist"] = macd_hist
    novas["macd_hist_slope_3"] = macd_hist - macd_hist.shift(3)

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    novas = {}

    for n in [6, 12, 23, 24]:
        media = sma(base["close"], n)
        novas[f"bias_{n}"] = (base["close"] - media) / media.replace(0, np.nan) * 100

    for n in [5, 10, 20, 30, 50, 60, 120]:
        high_n = base["high"].rolling(n).max()
        low_n = base["low"].rolling(n).min()

        novas[f"high_{n}"] = high_n
        novas[f"low_{n}"] = low_n
        novas[f"pos_range_{n}"] = (base["close"] - low_n) / (high_n - low_n).replace(0, np.nan)
        novas[f"rompeu_min_{n}"] = (base["low"] <= low_n.shift(1)).astype(int)
        novas[f"rompeu_max_{n}"] = (base["high"] >= high_n.shift(1)).astype(int)
        novas[f"dist_low_min_{n}"] = base["close"] - low_n
        novas[f"dist_high_max_{n}"] = high_n - base["close"]

    for n in [10, 20, 50]:
        vol_med = sma(base["volume"], n)
        novas[f"volume_media_{n}"] = vol_med
        novas[f"volume_ratio_{n}"] = base["volume"] / vol_med.replace(0, np.nan)

    novas["Label_Nome"] = ""
    novas["Label"] = 0

    base = pd.concat([base, pd.DataFrame(novas, index=base.index)], axis=1)

    base = adicionar_features_prev(base)

    todas_features = list(set(list(features_v3) + list(features_v4)))
    base = garantir_features_esperadas(base, todas_features)

    return base.copy()


# =====================================================
# SCORE V3 / PROB V4
# =====================================================

def preparar_X(df_features, feature_cols):
    ultima = df_features.iloc[-1].copy()

    linha = {}

    for col in feature_cols:
        if col in df_features.columns:
            linha[col] = ultima[col]
        else:
            linha[col] = np.nan

    X = pd.DataFrame([linha])

    return X, ultima


def calcular_score_v3(modelo_v3, X_v3):
    probas = modelo_v3.predict_proba(limpar_inf_nan_ml(X_v3))
    classes = list(modelo_v3.named_steps["model"].classes_)

    score_none = 0.0
    score_buy = 0.0
    score_sell = 0.0

    for i, classe in enumerate(classes):
        if classe == 0:
            score_none = float(probas[0, i])
        elif classe == 1:
            score_buy = float(probas[0, i])
        elif classe == 2:
            score_sell = float(probas[0, i])

    if score_buy > score_sell:
        direcao = "BUY"
        score_direcao = score_buy
        score_oposto = score_sell
    elif score_sell > score_buy:
        direcao = "SELL"
        score_direcao = score_sell
        score_oposto = score_buy
    else:
        direcao = "NONE"
        score_direcao = score_none
        score_oposto = max(score_buy, score_sell)

    score_diff = score_direcao - score_oposto

    return {
        "score_NONE": score_none,
        "score_BUY": score_buy,
        "score_SELL": score_sell,
        "Direcao": direcao,
        "score_direcao": score_direcao,
        "score_oposto": score_oposto,
        "score_diff": score_diff,
    }


def calcular_prob_v4(modelo_v4, X_v4, direcao=None):
    """
    Compatível com:
    - modelo único antigo da V4
    - modelo V5.1 em dict: {"BUY": modelo_buy, "SELL": modelo_sell}
    """

    modelo_usado = modelo_v4

    if isinstance(modelo_v4, dict):
        direcao_txt = str(direcao or "").upper().strip()

        if direcao_txt in modelo_v4:
            modelo_usado = modelo_v4[direcao_txt]
        else:
            # fallback conservador:
            # se não souber a direção, calcula as duas probabilidades
            # e usa a menor para evitar entrada indevida.
            probs = []

            for chave in ["BUY", "SELL"]:
                if chave in modelo_v4:
                    m = modelo_v4[chave]

                    if hasattr(m, "predict_proba"):
                        probs.append(float(m.predict_proba(limpar_inf_nan_ml(X_v4))[0][1]))
                    else:
                        probs.append(float(m.predict(limpar_inf_nan_ml(X_v4))[0]))

            if probs:
                return float(min(probs))

            raise RuntimeError("Modelo V5.1 em dict, mas sem chaves BUY/SELL válidas.")

    if hasattr(modelo_usado, "predict_proba"):
        prob = modelo_usado.predict_proba(limpar_inf_nan_ml(X_v4))[0][1]
        return float(prob)

    pred = modelo_usado.predict(limpar_inf_nan_ml(X_v4))[0]
    return float(pred)


def montar_X_v4(df_features, ultima, score_v3, feature_cols_v4):
    linha = {}

    for col in feature_cols_v4:
        if col in score_v3:
            linha[col] = score_v3[col]
        elif col in df_features.columns:
            linha[col] = ultima[col]
        else:
            linha[col] = np.nan

    X = pd.DataFrame([linha])

    return X


# =====================================================
# ESTADO OPERACIONAL
# =====================================================

def carregar_estado_operacional():
    if not os.path.exists(ARQUIVO_ESTADO):
        return {
            "data": "",
            "trades_hoje": 0,
            "loss_no_dia": False,
            "ultimo_sinal_datahora": "",
        }

    with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_estado_operacional(estado):
    salvar_json_seguro(estado, ARQUIVO_ESTADO)


def atualizar_estado_para_data(estado, data_atual):
    data_str = str(data_atual)

    if estado.get("data") != data_str:
        estado = {
            "data": data_str,
            "trades_hoje": 0,
            "loss_no_dia": False,
            "ultimo_sinal_datahora": "",
        }

    return estado


# =====================================================
# GERAÃƒâ€¡ÃƒÆ’O DE SINAL
# =====================================================

def gerar_sinal_tempo_real(candles, config_v4, modelo_v3, features_v3, modelo_v4, features_v4):
    if len(candles) < CANDLES_MINIMOS:
        return {
            "sinal": "none",
            "motivo": "candles_insuficientes",
            "candles_disponiveis": len(candles),
            "candles_minimos": CANDLES_MINIMOS,
            "datahora_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    df_feat = preparar_features_tempo_real(candles, features_v3, features_v4)

    salvar_csv_seguro(df_feat.tail(300), ARQUIVO_FEATURES_TEMPO_REAL)

    X_v3, ultima = preparar_X(df_feat, features_v3)

    
    ultima = corrigir_ultima_com_df_feat(ultima, df_feat)
# Garantia: preparar_X pode retornar ultima apenas com colunas do modelo.
    # Entao recolocamos DataHora_SP a partir do df_feat original.
    if "DataHora_SP" not in ultima.index and "DataHora_SP" in df_feat.columns:
        ultima["DataHora_SP"] = df_feat["DataHora_SP"].iloc[-1]

    if "Data" not in ultima.index and "Data" in df_feat.columns:
        ultima["Data"] = df_feat["Data"].iloc[-1]

    if "Hora_SP_Decimal" not in ultima.index and "Hora_SP_Decimal" in df_feat.columns:
        ultima["Hora_SP_Decimal"] = df_feat["Hora_SP_Decimal"].iloc[-1]


    score_v3 = calcular_score_v3(modelo_v3, X_v3)

    X_v4 = montar_X_v4(df_feat, ultima, score_v3, features_v4)

    direcao_modelo_v5_1 = None
    try:
        if isinstance(score_v3, dict):
            direcao_modelo_v5_1 = score_v3.get("Direcao", score_v3.get("direcao", None))
        elif hasattr(score_v3, "get"):
            direcao_modelo_v5_1 = score_v3.get("Direcao", None)
    except Exception:
        direcao_modelo_v5_1 = None

    prob_win_v4 = calcular_prob_v4(modelo_v4, X_v4, direcao_modelo_v5_1)

    hora_decimal = float(ultima["Hora_SP_Decimal"])
    dentro_horario = config_v4["hora_inicio"] <= hora_decimal <= config_v4["hora_fim"]

    bloqueio_0430 = (
        bool(config_v4.get("bloquear_0430_0444", False))
        and hora_decimal >= float(config_v4.get("hora_bloqueio_inicio", 999.0))
        and hora_decimal < float(config_v4.get("hora_bloqueio_fim", -999.0))
    )

    horario_operacional_valido = dentro_horario and not bloqueio_0430

    data_atual = ultima["Data"]

    estado = carregar_estado_operacional()
    estado = atualizar_estado_para_data(estado, data_atual)

    
    if "DataHora_SP" in ultima.index:
        datahora_ultimo_candle = str(ultima.get("DataHora_SP", pd.Timestamp.now()))
    elif "datahora_ultimo_candle_sp" in ultima.index:
        datahora_ultimo_candle = str(ultima["datahora_ultimo_candle_sp"])
    elif "datahora_sp" in ultima.index:
        datahora_ultimo_candle = str(ultima["datahora_sp"])
    elif "DataHora" in ultima.index:
        datahora_ultimo_candle = str(ultima["DataHora"])
    elif "date" in ultima.index:
        datahora_ultimo_candle = str(ultima["date"])
    else:
        datahora_ultimo_candle = str(pd.Timestamp.now())


    ja_enviou_nesse_candle = estado.get("ultimo_sinal_datahora") == datahora_ultimo_candle

    pode_operar_dia = (
        estado.get("trades_hoje", 0) < config_v4["max_trades_dia"] and
        (not config_v4["parar_apos_loss"] or not estado.get("loss_no_dia", False))
    )

    direcao = score_v3["Direcao"]

    cond_base = (
        horario_operacional_valido and
        pode_operar_dia and
        not ja_enviou_nesse_candle and
        prob_win_v4 >= config_v4["prob_win_min"] and
        score_v3["score_diff"] >= config_v4["diferenca_minima"]
    )

    cond_buy = (
        cond_base and
        direcao == "BUY" and
        score_v3["score_BUY"] >= config_v4["score_buy_min"] and
        score_v3["score_BUY"] > score_v3["score_SELL"]
    )

    cond_sell = (
        cond_base and
        direcao == "SELL" and
        score_v3["score_SELL"] >= config_v4["score_sell_min"] and
        score_v3["score_SELL"] > score_v3["score_BUY"]
    )

    sinal = "none"

    if cond_buy:
        sinal = "buy"
    elif cond_sell:
        sinal = "sell"

    preco_entrada_ref = float(ultima["close"])

    if sinal == "buy":
        preco_take = preco_entrada_ref + config_v4["take_pontos"]
        preco_stop = preco_entrada_ref - config_v4["stop_pontos"]
    elif sinal == "sell":
        preco_take = preco_entrada_ref - config_v4["take_pontos"]
        preco_stop = preco_entrada_ref + config_v4["stop_pontos"]
    else:
        preco_take = np.nan
        preco_stop = np.nan

    motivo = "sem_sinal"

    if not dentro_horario:
        motivo = "fora_do_horario_v4"
    elif ja_enviou_nesse_candle:
        motivo = "sinal_ja_enviado_neste_candle"
    elif not pode_operar_dia:
        motivo = "limite_diario_ou_loss_no_dia"
    elif prob_win_v4 < config_v4["prob_win_min"]:
        motivo = "prob_win_v4_abaixo_minimo"
    elif score_v3["score_diff"] < config_v4["diferenca_minima"]:
        motivo = "score_diff_abaixo_minimo"
    elif sinal == "none":
        motivo = "score_buy_sell_nao_passou"
    else:
        motivo = "sinal_valido"

    features_v3_faltando = sum(1 for col in features_v3 if col not in df_feat.columns)
    features_v3_nan_ultimo = sum(1 for col in features_v3 if col in df_feat.columns and pd.isna(ultima[col]))
    features_v3_validas = len(features_v3) - features_v3_faltando - features_v3_nan_ultimo

    payload = {
        "sinal": sinal,
        "motivo": motivo,
        "modo_seguro_sem_ordem": MODO_SEGURO_SEM_ORDEM,
        "datahora_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "datahora_ultimo_candle_sp": datahora_ultimo_candle,
        "data": str(data_atual),
        "preco_close": preco_entrada_ref,
        "preco_take": None if pd.isna(preco_take) else float(preco_take),
        "preco_stop": None if pd.isna(preco_stop) else float(preco_stop),
        "take_pontos": config_v4["take_pontos"],
        "stop_pontos": config_v4["stop_pontos"],
        "hora_decimal_sp": hora_decimal,
        "dentro_horario_v4": bool(dentro_horario),
        "bloqueio_0430_0444": bool(bloqueio_0430),
        "horario_operacional_valido": bool(horario_operacional_valido),
        "bloquear_0430_0444": bool(config_v4.get("bloquear_0430_0444", False)),
        "hora_bloqueio_inicio": float(config_v4.get("hora_bloqueio_inicio", 999.0)),
        "hora_bloqueio_fim": float(config_v4.get("hora_bloqueio_fim", -999.0)),
        "prob_win_v4": float(prob_win_v4),
        "prob_win_min": config_v4["prob_win_min"],
        "Direcao": direcao,
        "score_NONE": float(score_v3["score_NONE"]),
        "score_BUY": float(score_v3["score_BUY"]),
        "score_SELL": float(score_v3["score_SELL"]),
        "score_direcao": float(score_v3["score_direcao"]),
        "score_oposto": float(score_v3["score_oposto"]),
        "score_diff": float(score_v3["score_diff"]),
        "score_buy_min": config_v4["score_buy_min"],
        "score_sell_min": config_v4["score_sell_min"],
        "diferenca_minima": config_v4["diferenca_minima"],
        "trades_hoje": estado.get("trades_hoje", 0),
        "max_trades_dia": config_v4["max_trades_dia"],
        "loss_no_dia": estado.get("loss_no_dia", False),
        "parar_apos_loss": config_v4["parar_apos_loss"],
        "bloquear_0430_0444": config_v4.get("bloquear_0430_0444", False),
        "hora_bloqueio_inicio": config_v4.get("hora_bloqueio_inicio", None),
        "hora_bloqueio_fim": config_v4.get("hora_bloqueio_fim", None),
        "candles_disponiveis": len(candles),
        "features_v3_total": len(features_v3),
        "features_v3_faltando": features_v3_faltando,
        "features_v3_nan_ultimo": features_v3_nan_ultimo,
        "features_v3_validas": features_v3_validas,
    }

    if sinal in ["buy", "sell"]:
        estado["trades_hoje"] = int(estado.get("trades_hoje", 0)) + 1
        estado["ultimo_sinal_datahora"] = datahora_ultimo_candle
        salvar_estado_operacional(estado)

    return payload


def salvar_payload_sinal(payload):
    sinal = payload.get("sinal", "none")

    salvar_txt_seguro(sinal, ARQUIVO_SINAL_TXT)
    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL_JSON)

    append_log(payload)

    print("\n=====================================================")
    print("SINAL ATUAL")
    print("=====================================================")
    print(json.dumps(payload, ensure_ascii=False, indent=4, default=str))


# =====================================================
# EXECUÃƒâ€¡ÃƒÆ’O
# =====================================================

def executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4):
    tick = ler_blackarrow_rtd()

    ticks = atualizar_ticks(tick)

    candles = montar_candles_2min(ticks)

    payload = gerar_sinal_tempo_real(
        candles,
        config_v4,
        modelo_v3,
        features_v3,
        modelo_v4,
        features_v4
    )

    salvar_payload_sinal(payload)


def main():
    print("=====================================================")
    print("SINAL V4 BLACKARROW TEMPO REAL - CORRIGIDO LOG")
    print("=====================================================")

    print("Lendo arquivo:", ARQUIVO_BLACKARROW_RTD)

    config_v4 = carregar_config_v4()

    # ========================================================
    # V5.1 CAMPEÃ - threshold oficial
    # ========================================================
    config_v4["prob_win_min"] = 0.575
    config_v4["modelo_operacional"] = "V5.1_CAMPEA"

    modelo_v3, features_v3, config_v3 = carregar_modelo_v3()
    modelo_v4, features_v4 = carregar_modelo_v4()

    print("\nConfig operacional:")
    print(json.dumps({
        "take": config_v4["take_pontos"],
        "stop": config_v4["stop_pontos"],
        "prob_win_min": config_v4["prob_win_min"],
        "score_buy_min": config_v4["score_buy_min"],
        "score_sell_min": config_v4["score_sell_min"],
        "hora_inicio": config_v4["hora_inicio"],
        "hora_fim": config_v4["hora_fim"],
        "max_trades_dia": config_v4["max_trades_dia"],
        "parar_apos_loss": config_v4["parar_apos_loss"],
        "bloquear_0430_0444": config_v4.get("bloquear_0430_0444", False),
        "hora_bloqueio_inicio": config_v4.get("hora_bloqueio_inicio", None),
        "hora_bloqueio_fim": config_v4.get("hora_bloqueio_fim", None),
    }, indent=4, ensure_ascii=False))

    if RODAR_EM_LOOP:
        while True:
            try:
                executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4)
            except Exception as e:
                payload = {
                    "sinal": "none",
                    "motivo": "erro",
                    "erro": str(e),
                    "datahora_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                try:
                    salvar_payload_sinal(payload)
                except Exception:
                    print("ERRO AO SALVAR PAYLOAD DE ERRO:")
                    print(e)

                print("ERRO:", e)

            time.sleep(INTERVALO_SEGUNDOS)
    else:
        executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()

