import os
import json
import time
import warnings
import joblib
import numpy as np
import pandas as pd
from datetime import datetime


# ============================================================
# LEITURA ROBUSTA DOS CANDLES V7.1
# Aceita CSV com cabeçalho ou sem cabeçalho.
# Garante a coluna DataHora_SP.
# ============================================================
COLUNAS_CANDLES_V71 = [
    "DataHora_SP",
    "DataHora",
    "Data",
    "Hora_SP_Decimal",
    "open",
    "high",
    "low",
    "close",
    "Negocios",
    "preco_close",
    "qtd_ticks",
    "flag",
    "qtd_ticks2",
    "Asset",
    "Asset2",
]

def ler_candles_v71_corrigido(caminho):
    import pandas as pd

    try:
        df = pd.read_csv(caminho)
    except Exception:
        df = pd.read_csv(caminho, header=None)

    # Se leu errado como header=None ou se veio sem DataHora_SP
    if "DataHora_SP" not in df.columns:
        df = pd.read_csv(caminho, header=None)

        # Se a primeira linha for cabeçalho, remove ela
        primeira = [str(x).strip() for x in df.iloc[0].tolist()]
        if "DataHora_SP" in primeira:
            df = df.iloc[1:].copy()

        if df.shape[1] >= len(COLUNAS_CANDLES_V71):
            df = df.iloc[:, :len(COLUNAS_CANDLES_V71)].copy()
            df.columns = COLUNAS_CANDLES_V71
        else:
            raise RuntimeError(f"Arquivo de candles tem {df.shape[1]} colunas; esperado {len(COLUNAS_CANDLES_V71)}.")

    df.columns = [str(c).strip() for c in df.columns]

    # Alias de segurança
    if "DataHora_SP" not in df.columns and "DataHora" in df.columns:
        df["DataHora_SP"] = df["DataHora"]

    if "DataHora_SP" not in df.columns:
        raise RuntimeError("Coluna DataHora_SP não encontrada após leitura robusta dos candles.")

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df = df.sort_values("DataHora_SP").copy()

    if "DataHora" not in df.columns:
        df["DataHora"] = df["DataHora_SP"]
    else:
        df["DataHora"] = df["DataHora_SP"]

    df["Data"] = df["DataHora_SP"].dt.strftime("%Y-%m-%d")
    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0

    for c in ["open", "high", "low", "close", "Negocios", "preco_close"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "preco_close" not in df.columns and "close" in df.columns:
        df["preco_close"] = df["close"]

    return df



# =====================================================
# CONFIGURAÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ES GERAIS
# =====================================================

BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V3 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")
PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")
PASTA_V5_1 = os.path.join(BASE_DIR, "OPERACIONAL_V5_1_CAMPEA")
PASTA_V7 = os.path.join(BASE_DIR, "OPERACIONAL_V7_OFICIAL")
PASTA_V53 = os.path.join(BASE_DIR, "saida_v5_3_validacao_2025_teste_2026")
PASTA_V71 = os.path.join(BASE_DIR, "operacional_v71_oficial")
PASTA_OPERACIONAL = PASTA_V71
os.makedirs(PASTA_OPERACIONAL, exist_ok=True)

ARQUIVO_BLACKARROW_RTD = os.path.join(BASE_DIR, "blackarrow_rtd.csv")

ARQUIVO_TICKS = os.path.join(PASTA_OPERACIONAL, "blackarrow_ticks.csv")
ARQUIVO_CANDLES = os.path.join(PASTA_OPERACIONAL, "blackarrow_candles_2min.csv")
ARQUIVO_FEATURES_TEMPO_REAL = os.path.join(PASTA_OPERACIONAL, "features_blackarrow_tempo_real.csv")

ARQUIVO_SINAL_TXT = os.path.join(PASTA_OPERACIONAL, "sinal.txt")
ARQUIVO_ULTIMO_SINAL_JSON = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v71_blackarrow.json")
ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v71_blackarrow.csv")
ARQUIVO_LOG_RESERVA = os.path.join(PASTA_OPERACIONAL, "log_sinal_v71_blackarrow_reserva.csv")
ARQUIVO_ESTADO = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v71_blackarrow.json")

# =====================================================
# APRENDIZADO INTELIGENTE V7
# =====================================================

PASTA_APRENDIZADO_V7 = os.path.join(PASTA_OPERACIONAL, "aprendizado_v71")
PASTA_APRENDIZADO_EVENTOS = os.path.join(PASTA_APRENDIZADO_V7, "eventos")
PASTA_APRENDIZADO_RESULTADOS = os.path.join(PASTA_APRENDIZADO_V7, "resultados")
PASTA_APRENDIZADO_TREINOS_SEMANAIS = os.path.join(PASTA_APRENDIZADO_V7, "treinos_semanais")
PASTA_APRENDIZADO_TREINOS_MENSAIS = os.path.join(PASTA_APRENDIZADO_V7, "treinos_mensais")

for _pasta in [
    PASTA_APRENDIZADO_V7,
    PASTA_APRENDIZADO_EVENTOS,
    PASTA_APRENDIZADO_RESULTADOS,
    PASTA_APRENDIZADO_TREINOS_SEMANAIS,
    PASTA_APRENDIZADO_TREINOS_MENSAIS,
]:
    os.makedirs(_pasta, exist_ok=True)

ARQUIVO_APRENDIZADO_EVENTOS = os.path.join(PASTA_APRENDIZADO_EVENTOS, "eventos_v71_inteligente.csv")
ARQUIVO_APRENDIZADO_PENDENTES = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "operacoes_pendentes_v71.csv")
ARQUIVO_APRENDIZADO_RESULTADOS = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "resultados_v71_inteligente.csv")


def csv_vazio_ou_sem_cabecalho(caminho):
    if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
        return True

    try:
        with open(caminho, "r", encoding="utf-8-sig") as f:
            return not f.read(4096).strip()
    except OSError:
        return False


def ler_csv_aprendizado_seguro(caminho, **kwargs):
    if csv_vazio_ou_sem_cabecalho(caminho):
        return pd.DataFrame()

    try:
        return pd.read_csv(caminho, encoding="utf-8-sig", low_memory=False, **kwargs)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


# =====================================================
# LOGS EXTRAS V7.1 OFICIAL
# =====================================================

ARQUIVO_LOG_TODOS_CANDIDATOS_V71 = os.path.join(PASTA_OPERACIONAL, "log_todos_candidatos_v71.csv")
ARQUIVO_LOG_REJEITADOS_V71 = os.path.join(PASTA_OPERACIONAL, "log_rejeitados_v71.csv")
ARQUIVO_DATASET_TREINO_FUTURO_V71 = os.path.join(PASTA_OPERACIONAL, "dataset_treino_futuro_v71.csv")


ARQUIVO_MODELO_V3 = os.path.join(PASTA_V3, "modelo_v3_score.joblib")
ARQUIVO_FEATURES_V3 = os.path.join(PASTA_V3, "features_v3_score.joblib")
ARQUIVO_CONFIG_V3 = os.path.join(PASTA_V3, "config_modelo_v3_score.json")

ARQUIVO_CONFIG_V4 = os.path.join(PASTA_V4, "config_melhor_v4.json")

ARQUIVO_CONFIG_V7 = os.path.join(PASTA_V7, "config_v7_oficial.json")
ARQUIVO_MODELO_V7 = os.path.join(PASTA_V7, "modelos_final_v7_oficial.joblib")
ARQUIVO_FEATURES_V7 = os.path.join(PASTA_V7, "features_final_v7_oficial.joblib")


# =====================================================
# MODELO/FILTRO V5.3 PARA CONFIRMAR A V7.1
# =====================================================

ARQUIVO_MODELO_V53 = os.path.join(PASTA_V53, "modelo_final_v5_3.joblib")
ARQUIVO_FEATURES_V53 = os.path.join(PASTA_V53, "features_final_v5_3.joblib")
ARQUIVO_CONFIG_V53 = os.path.join(PASTA_V53, "07_config_v5_3.json")

PROB_V53_MIN_OFICIAL = 0.50


# Mantive os nomes V4 internamente para reduzir risco de quebrar o restante do cÃ³digo.
# A partir desta versÃ£o, eles apontam para a V7 OFICIAL.
ARQUIVO_MODELO_V4 = ARQUIVO_MODELO_V7
ARQUIVO_FEATURES_V4 = ARQUIVO_FEATURES_V7

RODAR_EM_LOOP = True
INTERVALO_SEGUNDOS = 1

MODO_SEGURO_SEM_ORDEM = True

CANDLES_MINIMOS = 220
COOLDOWN_ENTRADAS_MINUTOS = 5

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# =====================================================
# FUNÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ES DE ARQUIVO
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


# =====================================================
# JANELAS OFICIAIS V7.1
# =====================================================

def dentro_janela_oficial_v71(hora_decimal):
    """
    Janelas oficiais da V7.1:
    03:45 até 03:55
    04:45 até 04:55
    """
    try:
        h = float(hora_decimal)
    except Exception:
        return False

    janela_1 = (h >= 3.75 and h <= 3.9166667)
    janela_2 = (h >= 4.75 and h <= 4.9166667)

    return bool(janela_1 or janela_2)


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
                chave.replace("ÃƒÆ’Ã‚Â¡", "a")
                     .replace("ÃƒÆ’Ã‚Â ", "a")
                     .replace("ÃƒÆ’Ã‚Â£", "a")
                     .replace("ÃƒÆ’Ã‚Â¢", "a")
                     .replace("ÃƒÆ’Ã‚Â©", "e")
                     .replace("ÃƒÆ’Ã‚Âª", "e")
                     .replace("ÃƒÆ’Ã‚Â­", "i")
                     .replace("ÃƒÆ’Ã‚Â³", "o")
                     .replace("ÃƒÆ’Ã‚Â´", "o")
                     .replace("ÃƒÆ’Ã‚Âµ", "o")
                     .replace("ÃƒÆ’Ã‚Âº", "u")
                     .replace("ÃƒÆ’Ã‚Â§", "c")
            )
            mapa[chave] = col

        for nome in nomes:
            chave = str(nome).strip().lower()
            chave = (
                chave.replace("ÃƒÆ’Ã‚Â¡", "a")
                     .replace("ÃƒÆ’Ã‚Â ", "a")
                     .replace("ÃƒÆ’Ã‚Â£", "a")
                     .replace("ÃƒÆ’Ã‚Â¢", "a")
                     .replace("ÃƒÆ’Ã‚Â©", "e")
                     .replace("ÃƒÆ’Ã‚Âª", "e")
                     .replace("ÃƒÆ’Ã‚Â­", "i")
                     .replace("ÃƒÆ’Ã‚Â³", "o")
                     .replace("ÃƒÆ’Ã‚Â´", "o")
                     .replace("ÃƒÆ’Ã‚Âµ", "o")
                     .replace("ÃƒÆ’Ã‚Âº", "u")
                     .replace("ÃƒÆ’Ã‚Â§", "c")
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
    conteudo = json.dumps(obj, ensure_ascii=False, indent=4, default=str)
    temp = caminho + ".tmp"

    # Escreve no temp primeiro
    with open(temp, "w", encoding="utf-8") as f:
        f.write(conteudo)

    # Tentativa 1: os.replace (atomico, nao exige remover antes)
    try:
        os.replace(temp, caminho)
        return
    except Exception:
        pass

    # Tentativa 2: escrita direta (funciona mesmo com leitores compartilhados no Windows)
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        try:
            os.remove(temp)
        except Exception:
            pass
        return
    except Exception:
        pass

    # Tentativa 3: salva na reserva para nao perder o dado
    reserva = caminho.replace(".json", "_reserva.json")
    try:
        with open(reserva, "w", encoding="utf-8") as f:
            f.write(conteudo)
    except Exception:
        pass

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
    Isso evita WinError 32 quando o monitor PowerShell estÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ lendo o CSV.
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


def append_csv_generico(payload, caminho, encoding="utf-8-sig"):
    """
    Append seguro para CSV de aprendizado.
    Nao apaga arquivo existente e usa reserva se o arquivo estiver ocupado.
    """

    df_linha = pd.DataFrame([payload])

    try:
        arquivo_existe = os.path.exists(caminho) and not csv_vazio_ou_sem_cabecalho(caminho)

        df_linha.to_csv(
            caminho,
            mode="a",
            index=False,
            header=not arquivo_existe,
            encoding=encoding
        )

    except PermissionError:
        reserva = caminho.replace(".csv", "_reserva.csv")
        arquivo_existe = os.path.exists(reserva) and not csv_vazio_ou_sem_cabecalho(reserva)

        df_linha.to_csv(
            reserva,
            mode="a",
            index=False,
            header=not arquivo_existe,
            encoding=encoding
        )

        print("AVISO: arquivo de aprendizado ocupado. Registro salvo na reserva:")
        print(reserva)


def gerar_event_id(datahora_ultimo_candle, sinal, direcao, preco):
    texto = f"{datahora_ultimo_candle}|{sinal}|{direcao}|{preco}"
    texto = texto.replace(" ", "_").replace(":", "").replace("-", "").replace(".", "_")
    return texto


def ja_registrou_evento_aprendizado(event_id):
    if not os.path.exists(ARQUIVO_APRENDIZADO_EVENTOS):
        return False

    try:
        df = ler_csv_aprendizado_seguro(
            ARQUIVO_APRENDIZADO_EVENTOS,
            usecols=["event_id"],
        )

        if df.empty:
            return False

        return str(event_id) in set(df["event_id"].astype(str).tail(500).tolist())

    except Exception:
        return False


def salvar_evento_aprendizado(payload):
    """
    Salva 1 evento por candle para aprendizado futuro:
    - entradas aceitas
    - entradas bloqueadas
    - motivo de nao entrada
    """

    try:
        datahora_candle = str(payload.get("datahora_ultimo_candle_sp", ""))
        sinal = str(payload.get("sinal", "none"))
        direcao = str(payload.get("Direcao", "NONE"))
        preco = payload.get("preco_close", np.nan)

        event_id = payload.get("event_id", "")
        if not event_id:
            event_id = gerar_event_id(datahora_candle, sinal, direcao, preco)
            payload["event_id"] = event_id

        if ja_registrou_evento_aprendizado(event_id):
            return

        evento = {
            "event_id": event_id,
            "versao_robo": payload.get("versao_robo", "V7_1_OFICIAL"),
            "tipo_evento": "entrada" if sinal in ["buy", "sell"] else "bloqueio_ou_sem_sinal",
            "sinal": sinal,
            "motivo": payload.get("motivo", ""),
            "modo_seguro_sem_ordem": payload.get("modo_seguro_sem_ordem", None),
            "datahora_execucao": payload.get("datahora_execucao", ""),
            "datahora_ultimo_candle_sp": datahora_candle,
            "data": payload.get("data", ""),
            "preco_close": payload.get("preco_close", np.nan),
            "preco_take": payload.get("preco_take", np.nan),
            "preco_stop": payload.get("preco_stop", np.nan),
            "take_pontos": payload.get("take_pontos", np.nan),
            "stop_pontos": payload.get("stop_pontos", np.nan),
            "hora_decimal_sp": payload.get("hora_decimal_sp", np.nan),
            "Direcao": direcao,
            "prob_v51": payload.get("prob_v51", payload.get("prob_win_v4", np.nan)),
            "prob_v55": payload.get("prob_v55", np.nan),
            "gap_v51_v55": payload.get("gap_v51_v55", np.nan),
            "prob_v51_min": payload.get("prob_v51_min", payload.get("prob_win_min", np.nan)),
            "prob_v55_min": payload.get("prob_v55_min", np.nan),
            "score_NONE": payload.get("score_NONE", np.nan),
            "score_BUY": payload.get("score_BUY", np.nan),
            "score_SELL": payload.get("score_SELL", np.nan),
            "score_direcao": payload.get("score_direcao", np.nan),
            "score_oposto": payload.get("score_oposto", np.nan),
            "score_diff": payload.get("score_diff", np.nan),
            "score_buy_min": payload.get("score_buy_min", np.nan),
            "score_sell_min": payload.get("score_sell_min", np.nan),
            "diferenca_minima": payload.get("diferenca_minima", np.nan),
            "dentro_horario_v7": payload.get("dentro_horario_v7", payload.get("dentro_horario_v4", None)),
            "bloqueio_0430_0444": payload.get("bloqueio_0430_0444", None),
            "horario_operacional_valido": payload.get("horario_operacional_valido", None),
            "trades_hoje": payload.get("trades_hoje", np.nan),
            "max_trades_dia": payload.get("max_trades_dia", np.nan),
            "loss_no_dia": payload.get("loss_no_dia", None),
            "parar_apos_loss": payload.get("parar_apos_loss", None),
            "candles_disponiveis": payload.get("candles_disponiveis", np.nan),
        }

        append_csv_generico(evento, ARQUIVO_APRENDIZADO_EVENTOS)

        if sinal in ["buy", "sell"]:
            salvar_operacao_pendente_aprendizado(evento)

    except Exception as e:
        print("AVISO: falha ao salvar evento de aprendizado:", e)


def salvar_operacao_pendente_aprendizado(evento):
    """
    Registra entrada aceita para depois descobrir se bateu take ou stop.
    """

    try:
        event_id = str(evento.get("event_id", ""))

        if not event_id:
            return

        if os.path.exists(ARQUIVO_APRENDIZADO_PENDENTES):
            try:
                pend = ler_csv_aprendizado_seguro(ARQUIVO_APRENDIZADO_PENDENTES)
                if "event_id" in pend.columns and event_id in set(pend["event_id"].astype(str).tolist()):
                    return
            except Exception:
                pass

        pendente = dict(evento)
        pendente["status_resultado"] = "pendente"
        pendente["datahora_registro_pendente"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        append_csv_generico(pendente, ARQUIVO_APRENDIZADO_PENDENTES)

    except Exception as e:
        print("AVISO: falha ao salvar operacao pendente:", e)


def atualizar_loss_no_dia_se_stop(data_operacao):
    """
    Se uma operacao pendente bater stop, marca loss_no_dia no estado.
    Isso ajuda o filtro 'parar apos loss' a funcionar melhor no tempo real.
    """

    try:
        estado = carregar_estado_operacional()
        estado = atualizar_estado_para_data(estado, data_operacao)
        estado["loss_no_dia"] = True
        salvar_estado_operacional(estado)
    except Exception as e:
        print("AVISO: nao consegui atualizar loss_no_dia:", e)


def atualizar_resultados_aprendizado(candles):
    """
    Usa os candles ja formados para verificar operacoes pendentes:
    - take
    - stop
    - maxima a favor
    - maxima contra

    Regra conservadora:
    se take e stop forem tocados no mesmo candle, considera STOP primeiro.
    """

    try:
        if candles is None or len(candles) == 0:
            return

        if not os.path.exists(ARQUIVO_APRENDIZADO_PENDENTES):
            return

        pend = ler_csv_aprendizado_seguro(ARQUIVO_APRENDIZADO_PENDENTES)

        if pend.empty:
            return

        base = candles.copy()
        base["DataHora_SP"] = pd.to_datetime(base["DataHora_SP"], errors="coerce")
        base = base.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)

        for col in ["high", "low", "close"]:
            base[col] = pd.to_numeric(base[col], errors="coerce")

        resolvidos = []
        manter = []

        for _, op in pend.iterrows():
            try:
                event_id = str(op.get("event_id", ""))
                sinal = str(op.get("sinal", "")).lower()
                direcao = str(op.get("Direcao", "")).upper()

                entrada = float(op.get("preco_close", np.nan))
                take = float(op.get("preco_take", np.nan))
                stop = float(op.get("preco_stop", np.nan))

                dt_entrada = pd.to_datetime(op.get("datahora_ultimo_candle_sp", ""), errors="coerce")

                if pd.isna(dt_entrada) or pd.isna(entrada) or pd.isna(take) or pd.isna(stop):
                    manter.append(op.to_dict())
                    continue

                futuro = base[base["DataHora_SP"] > dt_entrada].copy()

                if futuro.empty:
                    manter.append(op.to_dict())
                    continue

                resultado = None
                dt_saida = None
                preco_saida = np.nan
                motivo_resultado = ""
                candles_ate_resultado = 0

                if sinal == "buy" or direcao == "BUY":
                    mfe = float((futuro["high"] - entrada).max())
                    mae = float((futuro["low"] - entrada).min())

                    for i, row in enumerate(futuro.itertuples(index=False), start=1):
                        tocou_stop = float(row.low) <= stop
                        tocou_take = float(row.high) >= take

                        if tocou_stop and tocou_take:
                            resultado = "stop"
                            motivo_resultado = "take_e_stop_mesmo_candle_conservador_stop"
                            dt_saida = row.DataHora_SP
                            preco_saida = stop
                            candles_ate_resultado = i
                            break
                        elif tocou_stop:
                            resultado = "stop"
                            motivo_resultado = "stop"
                            dt_saida = row.DataHora_SP
                            preco_saida = stop
                            candles_ate_resultado = i
                            break
                        elif tocou_take:
                            resultado = "take"
                            motivo_resultado = "take"
                            dt_saida = row.DataHora_SP
                            preco_saida = take
                            candles_ate_resultado = i
                            break

                    if resultado == "take":
                        pontos_resultado = abs(take - entrada)
                    elif resultado == "stop":
                        pontos_resultado = -abs(entrada - stop)
                    else:
                        pontos_resultado = np.nan

                elif sinal == "sell" or direcao == "SELL":
                    mfe = float((entrada - futuro["low"]).max())
                    mae = float((entrada - futuro["high"]).min())

                    for i, row in enumerate(futuro.itertuples(index=False), start=1):
                        tocou_stop = float(row.high) >= stop
                        tocou_take = float(row.low) <= take

                        if tocou_stop and tocou_take:
                            resultado = "stop"
                            motivo_resultado = "take_e_stop_mesmo_candle_conservador_stop"
                            dt_saida = row.DataHora_SP
                            preco_saida = stop
                            candles_ate_resultado = i
                            break
                        elif tocou_stop:
                            resultado = "stop"
                            motivo_resultado = "stop"
                            dt_saida = row.DataHora_SP
                            preco_saida = stop
                            candles_ate_resultado = i
                            break
                        elif tocou_take:
                            resultado = "take"
                            motivo_resultado = "take"
                            dt_saida = row.DataHora_SP
                            preco_saida = take
                            candles_ate_resultado = i
                            break

                    if resultado == "take":
                        pontos_resultado = abs(entrada - take)
                    elif resultado == "stop":
                        pontos_resultado = -abs(stop - entrada)
                    else:
                        pontos_resultado = np.nan

                else:
                    manter.append(op.to_dict())
                    continue

                if resultado is None:
                    op_dict = op.to_dict()
                    op_dict["mfe_atual"] = mfe
                    op_dict["mae_atual"] = mae
                    manter.append(op_dict)
                    continue

                res = op.to_dict()
                res.update({
                    "status_resultado": "finalizado",
                    "resultado": resultado,
                    "motivo_resultado": motivo_resultado,
                    "datahora_saida": str(dt_saida),
                    "preco_saida": float(preco_saida),
                    "pontos_resultado": float(pontos_resultado),
                    "mfe_pontos": float(mfe),
                    "mae_pontos": float(mae),
                    "candles_ate_resultado": int(candles_ate_resultado),
                    "minutos_ate_resultado": int(candles_ate_resultado * 2),
                    "datahora_resultado_registrado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

                resolvidos.append(res)

                if resultado == "stop":
                    atualizar_loss_no_dia_se_stop(str(op.get("data", "")))

            except Exception:
                manter.append(op.to_dict())

        if resolvidos:
            for res in resolvidos:
                append_csv_generico(res, ARQUIVO_APRENDIZADO_RESULTADOS)

        colunas_pendentes = list(pend.columns)
        pd.DataFrame(manter, columns=colunas_pendentes).to_csv(
            ARQUIVO_APRENDIZADO_PENDENTES,
            index=False,
            encoding="utf-8-sig"
        )

        if resolvidos:
            print(f"Aprendizado V7: {len(resolvidos)} operacao(oes) finalizada(s).")

    except Exception as e:
        print("AVISO: falha ao atualizar resultados de aprendizado:", e)



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
        raise FileNotFoundError(f"NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o encontrei: {ARQUIVO_CONFIG_V4}")

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
        raise FileNotFoundError(f"NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o encontrei modelo V3: {ARQUIVO_MODELO_V3}")

    if not os.path.exists(ARQUIVO_FEATURES_V3):
        raise FileNotFoundError(f"NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o encontrei features V3: {ARQUIVO_FEATURES_V3}")

    modelo = joblib.load(ARQUIVO_MODELO_V3)
    features = joblib.load(ARQUIVO_FEATURES_V3)
    config = carregar_json(ARQUIVO_CONFIG_V3)

    print("Modelo V3 carregado:", ARQUIVO_MODELO_V3)
    print("Features V3:", len(features))

    return modelo, features, config


def carregar_modelo_v4():
    if not os.path.exists(ARQUIVO_MODELO_V4):
        raise FileNotFoundError(f"Nao encontrei modelo V7: {ARQUIVO_MODELO_V4}")

    if not os.path.exists(ARQUIVO_FEATURES_V4):
        raise FileNotFoundError(f"Nao encontrei features V7: {ARQUIVO_FEATURES_V4}")

    modelo = joblib.load(ARQUIVO_MODELO_V4)
    features = joblib.load(ARQUIVO_FEATURES_V4)

    print("Modelo operacional V7 carregado:", ARQUIVO_MODELO_V4)

    if isinstance(features, dict):
        print("Features V7 v51:", len(features.get("v51", [])))
        print("Features V7 v55:", len(features.get("v55", [])))
    else:
        print("Features operacional:", len(features))

    return modelo, features


def carregar_modelo_v53():
    if not os.path.exists(ARQUIVO_MODELO_V53):
        raise FileNotFoundError(f"Nao encontrei modelo V5.3: {ARQUIVO_MODELO_V53}")

    if not os.path.exists(ARQUIVO_FEATURES_V53):
        raise FileNotFoundError(f"Nao encontrei features V5.3: {ARQUIVO_FEATURES_V53}")

    modelo = joblib.load(ARQUIVO_MODELO_V53)
    features = joblib.load(ARQUIVO_FEATURES_V53)

    print("Modelo filtro V5.3 carregado:", ARQUIVO_MODELO_V53)

    if isinstance(features, dict):
        print("Features V5.3 em dict:", list(features.keys()))
    else:
        print("Features V5.3:", len(features))

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

    # Remove duplicidade tambÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©m da lista de features esperadas.
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

        # Garantia final: nunca deixar entrar 2D no dicionÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡rio.
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




def achatar_features_modelo(features):
    """
    Aceita:
    - lista antiga de features
    - dict da V7: {"v51": [...], "v55": [...]}
    """

    if features is None:
        return []

    if isinstance(features, dict):
        saida = []

        for _, valor in features.items():
            if isinstance(valor, dict):
                for _, subvalor in valor.items():
                    if isinstance(subvalor, (list, tuple, set)):
                        saida.extend(list(subvalor))
            elif isinstance(valor, (list, tuple, set)):
                saida.extend(list(valor))

        return list(dict.fromkeys([str(x) for x in saida]))

    if isinstance(features, (list, tuple, set)):
        return list(dict.fromkeys([str(x) for x in features]))

    return []


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

    todas_features = list(set(list(features_v3) + achatar_features_modelo(features_v4)))
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
    CompatÃƒÂ­vel com:
    - modelo ÃƒÂºnico antigo da V4
    - modelo V5.1 em dict: {"BUY": modelo_buy, "SELL": modelo_sell}
    """

    modelo_usado = modelo_v4

    if isinstance(modelo_v4, dict):
        direcao_txt = str(direcao or "").upper().strip()

        if direcao_txt in modelo_v4:
            modelo_usado = modelo_v4[direcao_txt]
        else:
            # fallback conservador:
            # se nÃƒÂ£o souber a direÃƒÂ§ÃƒÂ£o, calcula as duas probabilidades
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

            raise RuntimeError("Modelo V5.1 em dict, mas sem chaves BUY/SELL vÃƒÂ¡lidas.")

    if hasattr(modelo_usado, "predict_proba"):
        prob = modelo_usado.predict_proba(limpar_inf_nan_ml(X_v4))[0][1]
        return float(prob)

    pred = modelo_usado.predict(limpar_inf_nan_ml(X_v4))[0]
    return float(pred)



def prever_probabilidade_modelo_binario(modelo, X):
    if hasattr(modelo, "predict_proba"):
        return float(modelo.predict_proba(limpar_inf_nan_ml(X))[0][1])

    pred = modelo.predict(limpar_inf_nan_ml(X))[0]
    return float(pred)


def calcular_probs_operacionais_v7(modelo_v4, features_v4, df_feat, ultima, score_v3):
    """
    Calcula probabilidades oficiais da V7.

    Formato esperado:
    modelos_final_v7_oficial.joblib:
        {
            "v51": {"BUY": modelo, "SELL": modelo},
            "v55": modelo_global
        }

    features_final_v7_oficial.joblib:
        {
            "v51": [...],
            "v55": [...]
        }

    Se cair em modelo antigo, mantÃ©m compatibilidade usando prob_win_v4.
    """

    direcao = str(score_v3.get("Direcao", "NONE")).upper().strip()

    # V7 oficial
    if isinstance(modelo_v4, dict) and "v51" in modelo_v4 and "v55" in modelo_v4:
        if not isinstance(features_v4, dict):
            raise RuntimeError("Modelo V7 carregado, mas features V7 nao estao em dict.")

        features_v51 = features_v4.get("v51", [])
        features_v55 = features_v4.get("v55", [])

        X_v51 = montar_X_v4(df_feat, ultima, score_v3, features_v51)
        X_v55 = montar_X_v4(df_feat, ultima, score_v3, features_v55)

        modelo_v51 = modelo_v4["v51"]
        modelo_v55 = modelo_v4["v55"]

        prob_v51 = calcular_prob_v4(modelo_v51, X_v51, direcao)
        prob_v55 = prever_probabilidade_modelo_binario(modelo_v55, X_v55)

        return {
            "prob_win_v4": float(prob_v51),  # compatibilidade com monitor antigo
            "prob_v51": float(prob_v51),
            "prob_v55": float(prob_v55),
            "gap_v51_v55": float(prob_v51 - prob_v55),
            "modelo_operacional": "V7_1_OFICIAL",
        }

    # Compatibilidade com V5.1/V4 antiga
    features_lista = achatar_features_modelo(features_v4)
    X_v4 = montar_X_v4(df_feat, ultima, score_v3, features_lista)
    prob = calcular_prob_v4(modelo_v4, X_v4, direcao)

    return {
        "prob_win_v4": float(prob),
        "prob_v51": float(prob),
        "prob_v55": np.nan,
        "gap_v51_v55": np.nan,
        "modelo_operacional": "COMPATIBILIDADE_V5_1_OU_V4",
    }


def calcular_prob_v53(modelo_v53, features_v53, df_feat, ultima, score_v3):
    """
    Calcula a probabilidade da V5.3 no candle atual.
    A V7.1 sÃ³ libera entrada se:
    - V7 gerar candidato
    - V5.3 confirmar com prob_v5_3 >= 0.50
    """

    try:
        if modelo_v53 is None or features_v53 is None:
            return {
                "prob_v5_3": np.nan,
                "prob_v53_min": PROB_V53_MIN_OFICIAL,
                "v53_aprovou_modelo": False,
                "erro_v53": "modelo_ou_features_v53_nao_carregado",
            }

        if isinstance(features_v53, dict):
            # Se um dia a V5.3 vier em dict, usa a primeira lista encontrada.
            features_lista = None

            for chave in ["features", "v53", "modelo", "default"]:
                if chave in features_v53:
                    features_lista = features_v53[chave]
                    break

            if features_lista is None:
                for valor in features_v53.values():
                    if isinstance(valor, (list, tuple)):
                        features_lista = list(valor)
                        break

            if features_lista is None:
                features_lista = achatar_features_modelo(features_v53)
        else:
            features_lista = list(features_v53)

        X_v53 = montar_X_v4(df_feat, ultima, score_v3, features_lista)

        direcao = str(score_v3.get("Direcao", "NONE")).upper().strip()

        if isinstance(modelo_v53, dict):
            prob = calcular_prob_v4(modelo_v53, X_v53, direcao)
        else:
            prob = prever_probabilidade_modelo_binario(modelo_v53, X_v53)

        prob = float(prob)

        return {
            "prob_v5_3": prob,
            "prob_v53_min": PROB_V53_MIN_OFICIAL,
            "v53_aprovou_modelo": bool(prob >= PROB_V53_MIN_OFICIAL),
            "erro_v53": "",
        }

    except Exception as e:
        return {
            "prob_v5_3": np.nan,
            "prob_v53_min": PROB_V53_MIN_OFICIAL,
            "v53_aprovou_modelo": False,
            "erro_v53": str(e),
        }



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
            "cooldown_entradas_minutos": COOLDOWN_ENTRADAS_MINUTOS,
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
            "cooldown_entradas_minutos": COOLDOWN_ENTRADAS_MINUTOS,
        }

    return estado


# =====================================================
# GERAÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢O DE SINAL
# =====================================================

def gerar_sinal_tempo_real(candles, config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53=None, features_v53=None):
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

    probs_operacionais = calcular_probs_operacionais_v7(
        modelo_v4=modelo_v4,
        features_v4=features_v4,
        df_feat=df_feat,
        ultima=ultima,
        score_v3=score_v3
    )

    prob_win_v4 = float(probs_operacionais["prob_win_v4"])
    prob_v51 = float(probs_operacionais["prob_v51"])

    try:
        prob_v55 = float(probs_operacionais["prob_v55"])
    except Exception:
        prob_v55 = np.nan

    try:
        gap_v51_v55 = float(probs_operacionais["gap_v51_v55"])
    except Exception:
        gap_v51_v55 = np.nan

    probs_v53 = calcular_prob_v53(
        modelo_v53=modelo_v53,
        features_v53=features_v53,
        df_feat=df_feat,
        ultima=ultima,
        score_v3=score_v3
    )

    try:
        prob_v5_3 = float(probs_v53.get("prob_v5_3", np.nan))
    except Exception:
        prob_v5_3 = np.nan

    prob_v53_min = float(probs_v53.get("prob_v53_min", PROB_V53_MIN_OFICIAL))
    v53_aprovou_modelo = bool(probs_v53.get("v53_aprovou_modelo", False))
    erro_v53 = str(probs_v53.get("erro_v53", ""))

    hora_decimal = float(ultima["Hora_SP_Decimal"])
    dentro_horario = config_v4["hora_inicio"] <= hora_decimal <= config_v4["hora_fim"]

    bloqueio_0430 = (
        bool(config_v4.get("bloquear_0430_0444", False))
        and hora_decimal >= float(config_v4.get("hora_bloqueio_inicio", 999.0))
        and hora_decimal < float(config_v4.get("hora_bloqueio_fim", -999.0))
    )

    # Horário oficial fiel ao backtest V7.1:
    # 02:00 até 06:00, respeitando o bloqueio 04:30 até 04:45.
    horario_operacional_valido = dentro_horario and not bloqueio_0430

    # Campo mantido no JSON para o monitor.
    # Agora significa: dentro do horário do backtest.
    dentro_janela_v71_oficial = bool(horario_operacional_valido)

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

    ultimo_sinal_dt = pd.to_datetime(estado.get("ultimo_sinal_datahora", ""), errors="coerce")
    candle_atual_dt = pd.to_datetime(datahora_ultimo_candle, errors="coerce")
    cooldown_entradas = pd.Timedelta(minutes=COOLDOWN_ENTRADAS_MINUTOS)
    cooldown_ativo = False
    proxima_entrada_liberada_em = ""

    if not pd.isna(ultimo_sinal_dt) and not pd.isna(candle_atual_dt):
        proxima_dt = ultimo_sinal_dt + cooldown_entradas
        cooldown_ativo = bool(candle_atual_dt < proxima_dt)
        proxima_entrada_liberada_em = str(proxima_dt)

    # =====================================================
    # V7.1 OFICIAL - COOLDOWN DE ENTRADAS
    # =====================================================
    # Objetivo:
    # Depois que o robô envia BUY/SELL válido, bloqueia apenas
    # novos sinais nos próximos 5 minutos.
    #
    # Isso evita duplicidade como:
    # 03:50 SELL válido
    # 03:52 SELL repetido
    #
    # Mas libera novas entradas legítimas depois da janela:
    # 04:48 SELL válido, mesmo que o trade de 03:50 ainda exista.
    # =====================================================

    operacao_aberta = bool(estado.get("operacao_aberta", False))
    operacao_fechou_agora = False
    operacao_fechamento_motivo = ""

    if operacao_aberta:
        try:
            op_sinal = str(estado.get("operacao_sinal", "")).lower()
            op_take = float(estado.get("operacao_preco_take", np.nan))
            op_stop = float(estado.get("operacao_preco_stop", np.nan))

            candle_high = float(ultima.get("high", ultima.get("High", ultima.get("close", np.nan))))
            candle_low = float(ultima.get("low", ultima.get("Low", ultima.get("close", np.nan))))

            bateu_take = False
            bateu_stop = False

            if op_sinal == "buy":
                bateu_take = candle_high >= op_take
                bateu_stop = candle_low <= op_stop

            elif op_sinal == "sell":
                bateu_take = candle_low <= op_take
                bateu_stop = candle_high >= op_stop

            # Em caso raro de take e stop no mesmo candle, assume STOP primeiro por segurança.
            if bateu_stop:
                estado["operacao_aberta"] = False
                estado["operacao_fechamento_motivo"] = "stop"
                estado["operacao_fechamento_datahora"] = datahora_ultimo_candle
                estado["loss_no_dia"] = True
                operacao_aberta = False
                operacao_fechou_agora = True
                operacao_fechamento_motivo = "stop"
                salvar_estado_operacional(estado)

            elif bateu_take:
                estado["operacao_aberta"] = False
                estado["operacao_fechamento_motivo"] = "take"
                estado["operacao_fechamento_datahora"] = datahora_ultimo_candle
                operacao_aberta = False
                operacao_fechou_agora = True
                operacao_fechamento_motivo = "take"
                salvar_estado_operacional(estado)

        except Exception as e:
            print("AVISO: erro ao verificar operação aberta:", e)
            operacao_aberta = bool(estado.get("operacao_aberta", False))

    pode_operar_dia = (
        estado.get("trades_hoje", 0) < config_v4["max_trades_dia"] and
        (not config_v4["parar_apos_loss"] or not estado.get("loss_no_dia", False))
    )

    direcao = score_v3["Direcao"]

    cond_base = (
        horario_operacional_valido and
        pode_operar_dia and
        not ja_enviou_nesse_candle and
        not cooldown_ativo and
        prob_v51 >= config_v4["prob_win_min"] and
        (pd.isna(prob_v55) or prob_v55 >= float(config_v4.get("prob_v55_min", 0.0))) and
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

    # =====================================================
    # FILTRO OFICIAL V7.1
    # =====================================================
    # Primeiro a V7 gera o candidato.
    # Depois a V5.3 precisa confirmar.
    cond_buy_v7_sem_filtro_v53 = bool(cond_buy)
    cond_sell_v7_sem_filtro_v53 = bool(cond_sell)
    candidato_v7 = bool(cond_buy_v7_sem_filtro_v53 or cond_sell_v7_sem_filtro_v53)

    v53_aprovou = bool(
        candidato_v7 and
        v53_aprovou_modelo and
        (not pd.isna(prob_v5_3)) and
        prob_v5_3 >= prob_v53_min and
        str(direcao).upper() in ["BUY", "SELL"]
    )

    if candidato_v7 and not v53_aprovou:
        cond_buy = False
        cond_sell = False

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
    elif cooldown_ativo:
        motivo = "cooldown_5_min_apos_ultima_entrada"
    elif not pode_operar_dia:
        motivo = "limite_diario_ou_loss_no_dia"
    elif prob_v51 < config_v4["prob_win_min"]:
        motivo = "prob_v51_abaixo_minimo"
    elif (not pd.isna(prob_v55)) and prob_v55 < float(config_v4.get("prob_v55_min", 0.0)):
        motivo = "prob_v55_abaixo_minimo"
    elif score_v3["score_diff"] < config_v4["diferenca_minima"]:
        motivo = "score_diff_abaixo_minimo"
    elif candidato_v7 and not v53_aprovou:
        motivo = "rejeitado_filtro_v53"
    elif sinal == "none":
        motivo = "score_buy_sell_nao_passou"
    else:
        motivo = "sinal_valido"

    features_v3_faltando = sum(1 for col in features_v3 if col not in df_feat.columns)
    features_v3_nan_ultimo = sum(1 for col in features_v3 if col in df_feat.columns and pd.isna(ultima[col]))
    features_v3_validas = len(features_v3) - features_v3_faltando - features_v3_nan_ultimo

    event_id = gerar_event_id(datahora_ultimo_candle, sinal, direcao, preco_entrada_ref)

    payload = {
        "event_id": event_id,
        "versao_robo": "V7_1_OFICIAL",
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
        "dentro_horario_v7": bool(dentro_horario),
        "bloqueio_0430_0444": bool(bloqueio_0430),
        "horario_operacional_valido": bool(horario_operacional_valido),
        "dentro_janela_v71_oficial": bool(dentro_janela_v71_oficial),
        "janela_v71_1": "02:00-06:00",
        "janela_v71_2": "bloqueio 04:30-04:45",
        "bloquear_0430_0444": bool(config_v4.get("bloquear_0430_0444", False)),
        "hora_bloqueio_inicio": float(config_v4.get("hora_bloqueio_inicio", 999.0)),
        "hora_bloqueio_fim": float(config_v4.get("hora_bloqueio_fim", -999.0)),
        "prob_win_v4": float(prob_win_v4),
        "prob_v51": float(prob_v51),
        "prob_v55": None if pd.isna(prob_v55) else float(prob_v55),
        "gap_v51_v55": None if pd.isna(gap_v51_v55) else float(gap_v51_v55),
        "modelo_operacional": config_v4.get("modelo_operacional", ""),

        "candidato_v7": bool(candidato_v7),
        "cond_buy_v7_sem_filtro_v53": bool(cond_buy_v7_sem_filtro_v53),
        "cond_sell_v7_sem_filtro_v53": bool(cond_sell_v7_sem_filtro_v53),
        "v53_aprovou": bool(v53_aprovou),
        "v53_aprovou_modelo": bool(v53_aprovou_modelo),
        "prob_v5_3": None if pd.isna(prob_v5_3) else float(prob_v5_3),
        "prob_v53_min": float(prob_v53_min),
        "erro_v53": erro_v53,

        "prob_v51_min": config_v4["prob_win_min"],
        "prob_v55_min": config_v4.get("prob_v55_min", None),
        "prob_v51_min": config_v4["prob_win_min"],
        "prob_v55_min": float(config_v4.get("prob_v55_min", 0.0)),
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
        "cooldown_entradas_minutos": COOLDOWN_ENTRADAS_MINUTOS,
        "cooldown_ativo": bool(cooldown_ativo),
        "proxima_entrada_liberada_em": proxima_entrada_liberada_em,
        "ultimo_sinal_datahora": estado.get("ultimo_sinal_datahora", ""),
        "bloquear_0430_0444": config_v4.get("bloquear_0430_0444", False),
        "hora_bloqueio_inicio": config_v4.get("hora_bloqueio_inicio", None),
        "hora_bloqueio_fim": config_v4.get("hora_bloqueio_fim", None),
        "candles_disponiveis": len(candles),
        "features_v3_total": len(features_v3),
        "features_v3_faltando": features_v3_faltando,
        "features_v3_nan_ultimo": features_v3_nan_ultimo,
        "features_v3_validas": features_v3_validas,

        # Controle informativo da última operação acompanhada.
        # A liberação oficial de nova entrada é por cooldown de 5 minutos.
        "operacao_aberta": bool(estado.get("operacao_aberta", False)),
        "operacao_fechou_agora": bool(operacao_fechou_agora),
        "operacao_fechamento_motivo": operacao_fechamento_motivo,
        "operacao_sinal": estado.get("operacao_sinal", ""),
        "operacao_preco_entrada": estado.get("operacao_preco_entrada", np.nan),
        "operacao_preco_take": estado.get("operacao_preco_take", np.nan),
        "operacao_preco_stop": estado.get("operacao_preco_stop", np.nan),
        "operacao_datahora_entrada": estado.get("operacao_datahora_entrada", ""),
    }

    if sinal in ["buy", "sell"] and motivo == "sinal_valido":
        estado["trades_hoje"] = int(estado.get("trades_hoje", 0)) + 1
        estado["ultimo_sinal_datahora"] = datahora_ultimo_candle
        estado["cooldown_entradas_minutos"] = COOLDOWN_ENTRADAS_MINUTOS

        # Mantém a última operação para acompanhamento/aprendizado.
        # Isso não bloqueia nova entrada depois do cooldown oficial de 5 minutos.
        estado["operacao_aberta"] = True
        estado["operacao_sinal"] = sinal
        estado["operacao_direcao"] = direcao
        estado["operacao_preco_entrada"] = float(preco_entrada_ref)
        estado["operacao_preco_take"] = None if pd.isna(preco_take) else float(preco_take)
        estado["operacao_preco_stop"] = None if pd.isna(preco_stop) else float(preco_stop)
        estado["operacao_datahora_entrada"] = datahora_ultimo_candle
        estado["operacao_event_id"] = event_id
        estado["operacao_fechamento_motivo"] = ""
        estado["operacao_fechamento_datahora"] = ""

        salvar_estado_operacional(estado)

    return payload


def salvar_logs_extras_v71(payload):
    """
    Salva logs extras da V7.1 para treino futuro:
    - todos os candidatos gerados pela V7
    - rejeitados pelo filtro V5.3
    - dataset futuro
    """

    try:
        candidato_v7 = bool(payload.get("candidato_v7", False))
        sinal = str(payload.get("sinal", "none")).lower()
        motivo = str(payload.get("motivo", ""))

        if candidato_v7:
            append_csv_generico(payload, ARQUIVO_LOG_TODOS_CANDIDATOS_V71)
            append_csv_generico(payload, ARQUIVO_DATASET_TREINO_FUTURO_V71)

        if candidato_v7 and motivo == "rejeitado_filtro_v53":
            append_csv_generico(payload, ARQUIVO_LOG_REJEITADOS_V71)

    except Exception as e:
        print("AVISO: falha ao salvar logs extras V7.1:", e)


def salvar_payload_sinal(payload):
    sinal = str(payload.get("sinal", "none")).lower()
    motivo = str(payload.get("motivo", ""))

    # Segurança:
    # Só escreve BUY/SELL no sinal.txt quando o sinal é realmente válido.
    # Qualquer bloqueio, inclusive cooldown de 5 minutos, escreve NONE.
    if motivo != "sinal_valido" or sinal not in ["buy", "sell"]:
        sinal_txt = "none"
        payload["sinal"] = "none"
    else:
        sinal_txt = sinal

    salvar_txt_seguro(sinal_txt, ARQUIVO_SINAL_TXT)
    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL_JSON)

    append_log(payload)
    salvar_evento_aprendizado(payload)
    salvar_logs_extras_v71(payload)

    print("\n=====================================================")
    print("SINAL ATUAL")
    print("=====================================================")
    print(json.dumps(payload, ensure_ascii=False, indent=4, default=str))


# =====================================================
# EXECUÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢O
# =====================================================

def _alertar_candle_travado(tick):
    agora = pd.Timestamp.now()
    dt_tick = pd.to_datetime(tick.get("DataHora_SP"), errors="coerce")
    if pd.isna(dt_tick):
        return
    minutos_atrasado = (agora - dt_tick).total_seconds() / 60.0
    if minutos_atrasado > 5:
        print(
            f"\n*** AVISO: candle travado! Ultimo dado do BlackArrow tem "
            f"{minutos_atrasado:.0f} min de atraso "
            f"({dt_tick.strftime('%H:%M')} vs agora {agora.strftime('%H:%M')}). "
            f"Verifique se a macro Excel esta rodando. ***\n"
        )


def executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53=None, features_v53=None):
    tick = ler_blackarrow_rtd()

    _alertar_candle_travado(tick)

    ticks = atualizar_ticks(tick)

    candles = montar_candles_2min(ticks)

    atualizar_resultados_aprendizado(candles)

    payload = gerar_sinal_tempo_real(
        candles,
        config_v4,
        modelo_v3,
        features_v3,
        modelo_v4,
        features_v4,
        modelo_v53,
        features_v53
    )

    salvar_payload_sinal(payload)


def main():
    print("=====================================================")
    print("SINAL V7.1 OFICIAL BLACKARROW TEMPO REAL - V7 + FILTRO V5.3")
    print("=====================================================")

    print("Lendo arquivo:", ARQUIVO_BLACKARROW_RTD)

    config_v4 = carregar_config_v4()

    # ========================================================
    # V7 OFICIAL
    # Resultado 2026:
    # 134 trades | +2914.5 pontos | PF 2.08 | DD -314.0 | 5 meses positivos
    # ========================================================
    config_v4["prob_win_min"] = 0.590      # prob_v51_min oficial V7
    config_v4["prob_v55_min"] = 0.425      # prob_v55_min oficial V7
    config_v4["modelo_operacional"] = "V7_1_OFICIAL"
    config_v4["max_trades_dia"] = 3
    config_v4["parar_apos_loss"] = True

    modelo_v3, features_v3, config_v3 = carregar_modelo_v3()
    modelo_v4, features_v4 = carregar_modelo_v4()
    modelo_v53, features_v53 = carregar_modelo_v53()

    print("\nConfig operacional:")
    print(json.dumps({
        "take": config_v4["take_pontos"],
        "stop": config_v4["stop_pontos"],
        "modelo_operacional": config_v4.get("modelo_operacional", ""),
        "prob_v51_min": config_v4["prob_win_min"],
        "prob_v55_min": config_v4.get("prob_v55_min", None),
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
                executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53, features_v53)
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
        executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53, features_v53)

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()


