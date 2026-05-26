import os
import re
import shutil
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQUIVO_ROBO_V7 = BASE_DIR / "sinal_v7_blackarrow_tempo_real_log_inteligente.py"
ARQUIVO_MONITOR_V7 = BASE_DIR / "monitor_alarme_v7_oficial_completo.ps1"

ARQUIVO_ROBO_V71 = BASE_DIR / "sinal_v71_blackarrow_tempo_real_log_inteligente.py"
ARQUIVO_MONITOR_V71 = BASE_DIR / "monitor_alarme_v71_oficial_completo.ps1"

PASTA_BACKUP = BASE_DIR / "backups_v71_oficial"
PASTA_BACKUP.mkdir(parents=True, exist_ok=True)

DATA = datetime.now().strftime("%Y%m%d_%H%M%S")


def ler_texto(caminho: Path) -> str:
    for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
        try:
            return caminho.read_text(encoding=enc)
        except Exception:
            pass

    return caminho.read_text(encoding="utf-8", errors="replace")


def salvar_texto(caminho: Path, texto: str):
    caminho.write_text(texto, encoding="utf-8")


def backup(caminho: Path):
    if caminho.exists():
        destino = PASTA_BACKUP / f"{caminho.stem}_BACKUP_antes_v71_{DATA}{caminho.suffix}"
        shutil.copy2(caminho, destino)
        print(f"Backup criado: {destino}")


def substituir_obrigatorio(texto: str, antigo: str, novo: str, descricao: str) -> str:
    if antigo not in texto:
        raise RuntimeError(f"Não encontrei trecho obrigatório para substituir: {descricao}")

    return texto.replace(antigo, novo)


def inserir_apos(texto: str, marcador: str, bloco: str, descricao: str) -> str:
    if bloco.strip() in texto:
        print(f"Bloco já existe, pulando: {descricao}")
        return texto

    pos = texto.find(marcador)
    if pos < 0:
        raise RuntimeError(f"Não encontrei marcador para inserir: {descricao}")

    pos_fim = pos + len(marcador)
    return texto[:pos_fim] + "\n" + bloco + texto[pos_fim:]


def criar_robo_v71():
    if not ARQUIVO_ROBO_V7.exists():
        raise FileNotFoundError(f"Não encontrei o robô V7: {ARQUIVO_ROBO_V7}")

    backup(ARQUIVO_ROBO_V7)

    texto = ler_texto(ARQUIVO_ROBO_V7)

    # ============================================================
    # 1. Pastas principais
    # ============================================================

    texto = substituir_obrigatorio(
        texto,
        'PASTA_V7 = os.path.join(BASE_DIR, "OPERACIONAL_V7_OFICIAL")\nPASTA_OPERACIONAL = os.path.join(BASE_DIR, "operacional_v4")',
        'PASTA_V7 = os.path.join(BASE_DIR, "OPERACIONAL_V7_OFICIAL")\n'
        'PASTA_V53 = os.path.join(BASE_DIR, "saida_v5_3_validacao_2025_teste_2026")\n'
        'PASTA_V71 = os.path.join(BASE_DIR, "operacional_v71_oficial")\n'
        'PASTA_OPERACIONAL = PASTA_V71',
        "pastas V7/V5.3/V7.1"
    )

    # ============================================================
    # 2. Arquivos operacionais
    # ============================================================

    texto = texto.replace(
        'ARQUIVO_ULTIMO_SINAL_JSON = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v4_blackarrow.json")',
        'ARQUIVO_ULTIMO_SINAL_JSON = os.path.join(PASTA_OPERACIONAL, "ultimo_sinal_v71_blackarrow.json")'
    )

    texto = texto.replace(
        'ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_blackarrow.csv")',
        'ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v71_blackarrow.csv")'
    )

    texto = texto.replace(
        'ARQUIVO_LOG_RESERVA = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_blackarrow_reserva.csv")',
        'ARQUIVO_LOG_RESERVA = os.path.join(PASTA_OPERACIONAL, "log_sinal_v71_blackarrow_reserva.csv")'
    )

    texto = texto.replace(
        'ARQUIVO_ESTADO = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v4_blackarrow.json")',
        'ARQUIVO_ESTADO = os.path.join(PASTA_OPERACIONAL, "estado_operacional_v71_blackarrow.json")'
    )

    # ============================================================
    # 3. Aprendizado V7 -> V7.1
    # ============================================================

    texto = texto.replace(
        'PASTA_APRENDIZADO_V7 = os.path.join(PASTA_OPERACIONAL, "aprendizado_v7")',
        'PASTA_APRENDIZADO_V7 = os.path.join(PASTA_OPERACIONAL, "aprendizado_v71")'
    )

    texto = texto.replace(
        'ARQUIVO_APRENDIZADO_EVENTOS = os.path.join(PASTA_APRENDIZADO_EVENTOS, "eventos_v7_inteligente.csv")',
        'ARQUIVO_APRENDIZADO_EVENTOS = os.path.join(PASTA_APRENDIZADO_EVENTOS, "eventos_v71_inteligente.csv")'
    )

    texto = texto.replace(
        'ARQUIVO_APRENDIZADO_PENDENTES = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "operacoes_pendentes_v7.csv")',
        'ARQUIVO_APRENDIZADO_PENDENTES = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "operacoes_pendentes_v71.csv")'
    )

    texto = texto.replace(
        'ARQUIVO_APRENDIZADO_RESULTADOS = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "resultados_v7_inteligente.csv")',
        'ARQUIVO_APRENDIZADO_RESULTADOS = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "resultados_v71_inteligente.csv")'
    )

    marcador_aprendizado = 'ARQUIVO_APRENDIZADO_RESULTADOS = os.path.join(PASTA_APRENDIZADO_RESULTADOS, "resultados_v71_inteligente.csv")'

    bloco_logs_v71 = '''

# =====================================================
# LOGS EXTRAS V7.1 OFICIAL
# =====================================================

ARQUIVO_LOG_TODOS_CANDIDATOS_V71 = os.path.join(PASTA_OPERACIONAL, "log_todos_candidatos_v71.csv")
ARQUIVO_LOG_REJEITADOS_V71 = os.path.join(PASTA_OPERACIONAL, "log_rejeitados_v71.csv")
ARQUIVO_DATASET_TREINO_FUTURO_V71 = os.path.join(PASTA_OPERACIONAL, "dataset_treino_futuro_v71.csv")
'''

    texto = inserir_apos(
        texto,
        marcador_aprendizado,
        bloco_logs_v71,
        "logs extras V7.1"
    )

    # ============================================================
    # 4. Modelo V5.3
    # ============================================================

    marcador_modelo_v7 = 'ARQUIVO_FEATURES_V7 = os.path.join(PASTA_V7, "features_final_v7_oficial.joblib")'

    bloco_modelo_v53 = '''

# =====================================================
# MODELO/FILTRO V5.3 PARA CONFIRMAR A V7.1
# =====================================================

ARQUIVO_MODELO_V53 = os.path.join(PASTA_V53, "modelo_final_v5_3.joblib")
ARQUIVO_FEATURES_V53 = os.path.join(PASTA_V53, "features_final_v5_3.joblib")
ARQUIVO_CONFIG_V53 = os.path.join(PASTA_V53, "07_config_v5_3.json")

PROB_V53_MIN_OFICIAL = 0.50
'''

    texto = inserir_apos(
        texto,
        marcador_modelo_v7,
        bloco_modelo_v53,
        "modelo V5.3"
    )

    # ============================================================
    # 5. Função carregar_modelo_v53
    # ============================================================

    marcador_fim_carregar_modelo_v4 = '''def carregar_modelo_v4():
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
'''

    bloco_carregar_v53 = '''

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
'''

    texto = substituir_obrigatorio(
        texto,
        marcador_fim_carregar_modelo_v4,
        marcador_fim_carregar_modelo_v4 + bloco_carregar_v53,
        "função carregar_modelo_v53"
    )

    # ============================================================
    # 6. Função calcular_prob_v53
    # ============================================================

    marcador_montar_x = '''def montar_X_v4(df_features, ultima, score_v3, feature_cols_v4):'''

    bloco_prob_v53 = '''

def calcular_prob_v53(modelo_v53, features_v53, df_feat, ultima, score_v3):
    """
    Calcula a probabilidade da V5.3 no candle atual.
    A V7.1 só libera entrada se:
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


'''

    texto = inserir_apos(
        texto,
        marcador_montar_x,
        bloco_prob_v53,
        "função calcular_prob_v53"
    )

    # Corrige possível inserção antes do def montar_X_v4 duplicando ordem:
    texto = texto.replace(
        bloco_prob_v53 + "def montar_X_v4",
        bloco_prob_v53 + "def montar_X_v4"
    )

    # ============================================================
    # 7. Assinatura gerar_sinal_tempo_real
    # ============================================================

    texto = substituir_obrigatorio(
        texto,
        'def gerar_sinal_tempo_real(candles, config_v4, modelo_v3, features_v3, modelo_v4, features_v4):',
        'def gerar_sinal_tempo_real(candles, config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53=None, features_v53=None):',
        "assinatura gerar_sinal_tempo_real"
    )

    # ============================================================
    # 8. Calcular prob V5.3 após prob V7
    # ============================================================

    marcador_apos_probs = '''    try:
        gap_v51_v55 = float(probs_operacionais["gap_v51_v55"])
    except Exception:
        gap_v51_v55 = np.nan
'''

    bloco_calculo_v53 = '''
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
'''

    texto = substituir_obrigatorio(
        texto,
        marcador_apos_probs,
        marcador_apos_probs + bloco_calculo_v53,
        "cálculo prob V5.3"
    )

    # ============================================================
    # 9. Aplicar filtro V5.3 depois da V7 decidir candidato
    # ============================================================

    marcador_antes_sinal = '''    sinal = "none"

    if cond_buy:
        sinal = "buy"
    elif cond_sell:
        sinal = "sell"
'''

    bloco_filtro_v53 = '''    # =====================================================
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

'''

    texto = substituir_obrigatorio(
        texto,
        marcador_antes_sinal,
        bloco_filtro_v53 + marcador_antes_sinal,
        "aplicação filtro V5.3"
    )

    # ============================================================
    # 10. Motivo rejeição V5.3
    # ============================================================

    marcador_motivo = '''    elif score_v3["score_diff"] < config_v4["diferenca_minima"]:
        motivo = "score_diff_abaixo_minimo"
    elif sinal == "none":
        motivo = "score_buy_sell_nao_passou"
    else:
        motivo = "sinal_valido"
'''

    novo_motivo = '''    elif score_v3["score_diff"] < config_v4["diferenca_minima"]:
        motivo = "score_diff_abaixo_minimo"
    elif candidato_v7 and not v53_aprovou:
        motivo = "rejeitado_filtro_v53"
    elif sinal == "none":
        motivo = "score_buy_sell_nao_passou"
    else:
        motivo = "sinal_valido"
'''

    texto = substituir_obrigatorio(
        texto,
        marcador_motivo,
        novo_motivo,
        "motivo rejeitado filtro V5.3"
    )

    # ============================================================
    # 11. Payload V7.1
    # ============================================================

    texto = texto.replace(
        '"versao_robo": "V7_OFICIAL",',
        '"versao_robo": "V7_1_OFICIAL",'
    )

    marcador_payload_modelo = '''        "modelo_operacional": config_v4.get("modelo_operacional", ""),'''

    bloco_payload_v53 = '''
        "candidato_v7": bool(candidato_v7),
        "cond_buy_v7_sem_filtro_v53": bool(cond_buy_v7_sem_filtro_v53),
        "cond_sell_v7_sem_filtro_v53": bool(cond_sell_v7_sem_filtro_v53),
        "v53_aprovou": bool(v53_aprovou),
        "v53_aprovou_modelo": bool(v53_aprovou_modelo),
        "prob_v5_3": None if pd.isna(prob_v5_3) else float(prob_v5_3),
        "prob_v53_min": float(prob_v53_min),
        "erro_v53": erro_v53,
'''

    texto = inserir_apos(
        texto,
        marcador_payload_modelo,
        bloco_payload_v53,
        "payload filtro V5.3"
    )

    # ============================================================
    # 12. Logs extras V7.1
    # ============================================================

    marcador_salvar_payload = '''def salvar_payload_sinal(payload):
    sinal = payload.get("sinal", "none")

    salvar_txt_seguro(sinal, ARQUIVO_SINAL_TXT)
    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL_JSON)

    append_log(payload)
    salvar_evento_aprendizado(payload)
'''

    novo_salvar_payload = '''def salvar_logs_extras_v71(payload):
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
    sinal = payload.get("sinal", "none")

    salvar_txt_seguro(sinal, ARQUIVO_SINAL_TXT)
    salvar_json_seguro(payload, ARQUIVO_ULTIMO_SINAL_JSON)

    append_log(payload)
    salvar_evento_aprendizado(payload)
    salvar_logs_extras_v71(payload)
'''

    texto = substituir_obrigatorio(
        texto,
        marcador_salvar_payload,
        novo_salvar_payload,
        "logs extras no salvar_payload_sinal"
    )

    # ============================================================
    # 13. Assinatura executar_uma_vez e chamada gerar_sinal
    # ============================================================

    texto = substituir_obrigatorio(
        texto,
        'def executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4):',
        'def executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53=None, features_v53=None):',
        "assinatura executar_uma_vez"
    )

    texto = substituir_obrigatorio(
        texto,
        '''    payload = gerar_sinal_tempo_real(
        candles,
        config_v4,
        modelo_v3,
        features_v3,
        modelo_v4,
        features_v4
    )''',
        '''    payload = gerar_sinal_tempo_real(
        candles,
        config_v4,
        modelo_v3,
        features_v3,
        modelo_v4,
        features_v4,
        modelo_v53,
        features_v53
    )''',
        "chamada gerar_sinal em executar_uma_vez"
    )

    # ============================================================
    # 14. Main: carregar V5.3 e passar adiante
    # ============================================================

    texto = substituir_obrigatorio(
        texto,
        '    config_v4["modelo_operacional"] = "V7_OFICIAL"',
        '    config_v4["modelo_operacional"] = "V7_1_OFICIAL"',
        "modelo operacional V7.1"
    )

    texto = substituir_obrigatorio(
        texto,
        '''    modelo_v3, features_v3, config_v3 = carregar_modelo_v3()
    modelo_v4, features_v4 = carregar_modelo_v4()
''',
        '''    modelo_v3, features_v3, config_v3 = carregar_modelo_v3()
    modelo_v4, features_v4 = carregar_modelo_v4()
    modelo_v53, features_v53 = carregar_modelo_v53()
''',
        "carregar modelo V5.3 no main"
    )

    texto = texto.replace(
        '''                executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4)''',
        '''                executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53, features_v53)'''
    )

    texto = texto.replace(
        '''        executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4)''',
        '''        executar_uma_vez(config_v4, modelo_v3, features_v3, modelo_v4, features_v4, modelo_v53, features_v53)'''
    )

    # ============================================================
    # 15. Textos visuais
    # ============================================================

    texto = texto.replace(
        "SINAL V7 OFICIAL BLACKARROW TEMPO REAL - LOG INTELIGENTE",
        "SINAL V7.1 OFICIAL BLACKARROW TEMPO REAL - V7 + FILTRO V5.3"
    )

    texto = texto.replace("V7_OFICIAL", "V7_1_OFICIAL")

    salvar_texto(ARQUIVO_ROBO_V71, texto)

    print(f"Robô V7.1 criado em: {ARQUIVO_ROBO_V71}")


def criar_monitor_v71():
    if not ARQUIVO_MONITOR_V7.exists():
        print("Monitor V7 não encontrado. Pulando criação do monitor V7.1.")
        return

    backup(ARQUIVO_MONITOR_V7)

    texto = ler_texto(ARQUIVO_MONITOR_V7)

    texto = texto.replace("V7 OFICIAL", "V7.1 OFICIAL")
    texto = texto.replace("V7_OFICIAL", "V7_1_OFICIAL")
    texto = texto.replace("V7", "V7.1")

    texto = texto.replace("operacional_v4", "operacional_v71_oficial")
    texto = texto.replace("ultimo_sinal_v4_blackarrow.json", "ultimo_sinal_v71_blackarrow.json")
    texto = texto.replace("log_sinal_v4_blackarrow.csv", "log_sinal_v71_blackarrow.csv")
    texto = texto.replace("estado_operacional_v4_blackarrow.json", "estado_operacional_v71_blackarrow.json")

    # Ajuste visual dos mínimos principais da V7.1.
    texto = texto.replace("$minProbV4 = 0.590", "$minProbV4 = 0.590")
    texto = texto.replace("$minV55 = 0.425", "$minV55 = 0.425")

    salvar_texto(ARQUIVO_MONITOR_V71, texto)

    print(f"Monitor V7.1 criado em: {ARQUIVO_MONITOR_V71}")


def criar_bat_v71():
    bat_robo = BASE_DIR / "RODAR_ROBO_V71_OFICIAL.bat"
    bat_monitor = BASE_DIR / "RODAR_MONITOR_V71_OFICIAL.bat"

    bat_robo.write_text(
        '@echo off\n'
        'cd /d "C:\\Users\\ualac\\Documents\\2025\\Mercado\\machine-pyton"\n'
        'call ".\\.venv\\Scripts\\activate.bat"\n'
        'python "sinal_v71_blackarrow_tempo_real_log_inteligente.py"\n'
        'pause\n',
        encoding="utf-8"
    )

    bat_monitor.write_text(
        '@echo off\n'
        'cd /d "C:\\Users\\ualac\\Documents\\2025\\Mercado\\machine-pyton"\n'
        'powershell -ExecutionPolicy Bypass -File ".\\monitor_alarme_v71_oficial_completo.ps1"\n'
        'pause\n',
        encoding="utf-8"
    )

    print(f"BAT robô criado: {bat_robo}")
    print(f"BAT monitor criado: {bat_monitor}")


def checar_arquivos():
    obrigatorios = [
        BASE_DIR / "saida_v5_3_validacao_2025_teste_2026" / "modelo_final_v5_3.joblib",
        BASE_DIR / "saida_v5_3_validacao_2025_teste_2026" / "features_final_v5_3.joblib",
        BASE_DIR / "OPERACIONAL_V7_OFICIAL" / "modelos_final_v7_oficial.joblib",
        BASE_DIR / "OPERACIONAL_V7_OFICIAL" / "features_final_v7_oficial.joblib",
    ]

    print("\nChecando arquivos obrigatórios:")

    for arq in obrigatorios:
        if arq.exists():
            print(f"OK: {arq}")
        else:
            print(f"FALTOU: {arq}")


def main():
    print("=" * 100)
    print("CRIAR ROBÔ V7.1 OFICIAL = V7 + FILTRO V5.3")
    print("=" * 100)

    checar_arquivos()
    criar_robo_v71()
    criar_monitor_v71()
    criar_bat_v71()

    print("\nFinalizado.")
    print("\nArquivos principais criados:")
    print(ARQUIVO_ROBO_V71)
    print(ARQUIVO_MONITOR_V71)
    print(BASE_DIR / "RODAR_ROBO_V71_OFICIAL.bat")
    print(BASE_DIR / "RODAR_MONITOR_V71_OFICIAL.bat")


if __name__ == "__main__":
    main()