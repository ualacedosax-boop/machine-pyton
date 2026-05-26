import json
import shutil
from datetime import datetime
from pathlib import Path


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

PASTA_V4 = BASE_DIR / "saida_ml_entradas_video_v4_antiloss"
PASTA_OPERACIONAL = BASE_DIR / "operacional_v4"

ARQ_CONFIG_ATUAL = PASTA_V4 / "config_melhor_v4.json"
ARQ_MODELO_V4 = PASTA_V4 / "modelo_v4_antiloss.joblib"
ARQ_FEATURES_V4 = PASTA_V4 / "features_modelo_v4.joblib"

ARQ_SINAL_TEMPO_REAL = BASE_DIR / "sinal_v4_blackarrow_tempo_real.py"

PASTA_CAMPEOES = BASE_DIR / "CAMPEOES_V4"
PASTA_CAMPEAO = PASTA_CAMPEOES / "V4_CAMPEAO_2026_SEM0430_BUY074"

ARQ_CONFIG_CAMPEAO = PASTA_CAMPEAO / "config_melhor_v4_CAMPEAO_2026_SEM0430_BUY074.json"


# ============================================================
# CONFIGURAÇÃO CAMPEÃ
# ============================================================

CONFIG_CAMPEAO = {
    "nome": "V4_CAMPEAO_2026_SEM0430_BUY074",
    "descricao": "V4 atual campeão validado fora da amostra em 2026 com bloqueio 04:30-04:44 e BUY minimo 0.74",

    "take_pontos": 50.5,
    "stop_pontos": 117.0,

    "prob_win_min": 0.60,
    "max_trades_dia": 3,
    "parar_apos_loss": True,

    "score_buy_min": 0.74,
    "score_sell_min": 0.50,
    "diferenca_minima": 0.0,

    "hora_inicio": 2.0,
    "hora_fim": 6.0,

    "bloquear_0430_0444": True,
    "hora_bloqueio_inicio": 4.5,
    "hora_bloqueio_fim": 4.75,

    "resultado_validacao_2026": {
        "trades": 167,
        "wins": 132,
        "losses": 35,
        "winrate": 79.041916,
        "lucro_pontos": 2571.0,
        "profit_factor": 1.627839,
        "drawdown_trades": -582.5,
        "buy_total": 47,
        "sell_total": 120,
        "meses_positivos": 5,
        "meses_negativos": 0
    },

    "observacao": "Este arquivo é a configuração campeã. O bloqueio 04:30-04:44 exige que o sinal_v4_blackarrow_tempo_real.py esteja atualizado para ler os campos bloquear_0430_0444, hora_bloqueio_inicio e hora_bloqueio_fim."
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def salvar_json(obj, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)


def carregar_texto(caminho: Path) -> str:
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()


def salvar_texto(caminho: Path, texto: str):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)


def copiar_se_existir(origem: Path, destino: Path):
    if origem.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        print(f"Copiado: {origem}")
        print(f"     -> {destino}")
    else:
        print(f"ATENÇÃO: não encontrado para copiar: {origem}")


# ============================================================
# PATCH DO SINAL EM TEMPO REAL
# ============================================================

def aplicar_patch_bloqueio_0430():
    if not ARQ_SINAL_TEMPO_REAL.exists():
        raise FileNotFoundError(f"Não encontrei o script: {ARQ_SINAL_TEMPO_REAL}")

    texto = carregar_texto(ARQ_SINAL_TEMPO_REAL)
    original = texto

    # --------------------------------------------------------
    # 1) carregar_config_v4: adiciona leitura dos campos novos
    # --------------------------------------------------------

    trecho_base = '    config["hora_fim"] = float(config["hora_fim"])\n'
    trecho_novo = '''    config["hora_fim"] = float(config["hora_fim"])

    config["bloquear_0430_0444"] = str(config.get("bloquear_0430_0444", False)).lower() in ["true", "1", "sim", "yes"]
    config["hora_bloqueio_inicio"] = float(config.get("hora_bloqueio_inicio", 999.0))
    config["hora_bloqueio_fim"] = float(config.get("hora_bloqueio_fim", -999.0))
'''

    if 'config["bloquear_0430_0444"]' not in texto:
        if trecho_base in texto:
            texto = texto.replace(trecho_base, trecho_novo)
            print("Patch 1 OK: carregar_config_v4 agora lê o bloqueio 04:30.")
        else:
            print("ATENÇÃO: não achei o ponto para inserir leitura do bloqueio em carregar_config_v4.")
    else:
        print("Patch 1 ignorado: leitura do bloqueio já existe.")

    # --------------------------------------------------------
    # 2) gerar_sinal_tempo_real: cria variáveis de bloqueio
    # --------------------------------------------------------

    trecho_base = '    dentro_horario = config_v4["hora_inicio"] <= hora_decimal <= config_v4["hora_fim"]\n'
    trecho_novo = '''    dentro_horario = config_v4["hora_inicio"] <= hora_decimal <= config_v4["hora_fim"]

    bloqueio_0430 = (
        bool(config_v4.get("bloquear_0430_0444", False))
        and hora_decimal >= float(config_v4.get("hora_bloqueio_inicio", 999.0))
        and hora_decimal < float(config_v4.get("hora_bloqueio_fim", -999.0))
    )

    horario_operacional_valido = dentro_horario and not bloqueio_0430
'''

    if "horario_operacional_valido" not in texto:
        if trecho_base in texto:
            texto = texto.replace(trecho_base, trecho_novo)
            print("Patch 2 OK: criado bloqueio_0430 e horario_operacional_valido.")
        else:
            print("ATENÇÃO: não achei o ponto para inserir bloqueio_0430.")
    else:
        print("Patch 2 ignorado: horario_operacional_valido já existe.")

    # --------------------------------------------------------
    # 3) cond_base passa a usar horario_operacional_valido
    # --------------------------------------------------------

    texto = texto.replace(
        '''    cond_base = (
        dentro_horario and
''',
        '''    cond_base = (
        horario_operacional_valido and
'''
    )

    # --------------------------------------------------------
    # 4) motivo do sinal: tenta adicionar motivo específico
    # --------------------------------------------------------

    trecho_base = '''    elif not dentro_horario:
        motivo = "fora_do_horario_v4"
'''
    trecho_novo = '''    elif not dentro_horario:
        motivo = "fora_do_horario_v4"
    elif bloqueio_0430:
        motivo = "bloqueado_0430_0444"
'''

    if "bloqueado_0430_0444" not in texto:
        if trecho_base in texto:
            texto = texto.replace(trecho_base, trecho_novo)
            print("Patch 4 OK: motivo bloqueado_0430_0444 adicionado.")
        else:
            print("ATENÇÃO: não achei o trecho de motivo fora_do_horario_v4. O bloqueio ainda funcionará na cond_base.")
    else:
        print("Patch 4 ignorado: motivo bloqueado_0430_0444 já existe.")

    # --------------------------------------------------------
    # 5) payload recebe os campos do bloqueio
    # --------------------------------------------------------

    trecho_base = '        "dentro_horario_v4": bool(dentro_horario),\n'
    trecho_novo = '''        "dentro_horario_v4": bool(dentro_horario),
        "bloqueio_0430_0444": bool(bloqueio_0430),
        "horario_operacional_valido": bool(horario_operacional_valido),
        "bloquear_0430_0444": bool(config_v4.get("bloquear_0430_0444", False)),
        "hora_bloqueio_inicio": float(config_v4.get("hora_bloqueio_inicio", 999.0)),
        "hora_bloqueio_fim": float(config_v4.get("hora_bloqueio_fim", -999.0)),
'''

    if '"bloqueio_0430_0444"' not in texto:
        if trecho_base in texto:
            texto = texto.replace(trecho_base, trecho_novo)
            print("Patch 5 OK: payload agora mostra o bloqueio para o monitor.")
        else:
            print("ATENÇÃO: não achei dentro_horario_v4 no payload.")
    else:
        print("Patch 5 ignorado: payload do bloqueio já existe.")

    # --------------------------------------------------------
    # 6) print da config no início
    # --------------------------------------------------------

    trecho_base = '        "parar_apos_loss": config_v4["parar_apos_loss"],\n'
    trecho_novo = '''        "parar_apos_loss": config_v4["parar_apos_loss"],
        "bloquear_0430_0444": config_v4.get("bloquear_0430_0444", False),
        "hora_bloqueio_inicio": config_v4.get("hora_bloqueio_inicio", None),
        "hora_bloqueio_fim": config_v4.get("hora_bloqueio_fim", None),
'''

    if '"hora_bloqueio_inicio": config_v4.get' not in texto:
        if trecho_base in texto:
            texto = texto.replace(trecho_base, trecho_novo)
            print("Patch 6 OK: print inicial da config mostra bloqueio.")
        else:
            print("ATENÇÃO: não achei print de parar_apos_loss para adicionar bloqueio.")
    else:
        print("Patch 6 ignorado: print da config já mostra bloqueio.")

    if texto != original:
        backup_script = PASTA_CAMPEAO / f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        copiar_se_existir(ARQ_SINAL_TEMPO_REAL, backup_script)
        salvar_texto(ARQ_SINAL_TEMPO_REAL, texto)
        print("\nScript operacional atualizado:")
        print(ARQ_SINAL_TEMPO_REAL)
    else:
        print("\nNenhuma alteração feita no script operacional.")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=====================================================")
    print("SALVAR E ATIVAR V4 CAMPEÃO")
    print("=====================================================")

    PASTA_CAMPEAO.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\nPasta do campeão:")
    print(PASTA_CAMPEAO)

    # --------------------------------------------------------
    # 1) Salvar configuração campeã na pasta separada
    # --------------------------------------------------------

    salvar_json(CONFIG_CAMPEAO, ARQ_CONFIG_CAMPEAO)

    print("\nConfiguração campeã salva:")
    print(ARQ_CONFIG_CAMPEAO)

    # --------------------------------------------------------
    # 2) Backup dos arquivos atuais
    # --------------------------------------------------------

    pasta_backup = PASTA_CAMPEAO / f"BACKUP_antes_ativar_campeao_{timestamp}"
    pasta_backup.mkdir(parents=True, exist_ok=True)

    copiar_se_existir(ARQ_CONFIG_ATUAL, pasta_backup / "config_melhor_v4_ANTES.json")
    copiar_se_existir(ARQ_MODELO_V4, pasta_backup / "modelo_v4_antiloss.joblib")
    copiar_se_existir(ARQ_FEATURES_V4, pasta_backup / "features_modelo_v4.joblib")
    copiar_se_existir(ARQ_SINAL_TEMPO_REAL, pasta_backup / "sinal_v4_blackarrow_tempo_real_ANTES.py")

    # Também guarda uma cópia dos resultados da validação, se existirem
    arquivos_validacao = [
        BASE_DIR / "validacao_v4_2026_fora_amostra" / "03_2026_trades_atual_sem_0430_buy074.csv.gz",
        BASE_DIR / "validacao_v4_2026_fora_amostra" / "04_2026_resumo_atual_sem_0430_buy074.csv",
        BASE_DIR / "validacao_v4_2026_fora_amostra" / "05_2026_analise_atual_sem_0430_buy074.csv",
    ]

    for arq in arquivos_validacao:
        copiar_se_existir(arq, PASTA_CAMPEAO / arq.name)

    # --------------------------------------------------------
    # 3) Ativar config campeã no local usado pelo operacional
    # --------------------------------------------------------

    backup_config = PASTA_CAMPEAO / f"config_melhor_v4_BACKUP_original_{timestamp}.json"
    copiar_se_existir(ARQ_CONFIG_ATUAL, backup_config)

    salvar_json(CONFIG_CAMPEAO, ARQ_CONFIG_ATUAL)

    print("\nConfig campeã ativada no operacional:")
    print(ARQ_CONFIG_ATUAL)

    # --------------------------------------------------------
    # 4) Aplicar patch no sinal_v4_blackarrow_tempo_real.py
    # --------------------------------------------------------

    aplicar_patch_bloqueio_0430()

    # --------------------------------------------------------
    # 5) Conferência final
    # --------------------------------------------------------

    print("\n=====================================================")
    print("CONFERÊNCIA FINAL")
    print("=====================================================")

    with open(ARQ_CONFIG_ATUAL, "r", encoding="utf-8") as f:
        config_lida = json.load(f)

    campos = [
        "take_pontos",
        "stop_pontos",
        "prob_win_min",
        "score_buy_min",
        "score_sell_min",
        "diferenca_minima",
        "hora_inicio",
        "hora_fim",
        "bloquear_0430_0444",
        "hora_bloqueio_inicio",
        "hora_bloqueio_fim",
        "max_trades_dia",
        "parar_apos_loss",
    ]

    for campo in campos:
        print(f"{campo}: {config_lida.get(campo)}")

    print("\nPronto.")
    print("Agora rode o operacional:")
    print(r'cd "C:\Users\ualac\Documents\2025\Mercado\machine-pyton"')
    print(r'.\.venv\Scripts\Activate.ps1')
    print(r'python sinal_v4_blackarrow_tempo_real.py')

    print("\nO monitor deverá continuar lendo:")
    print(PASTA_OPERACIONAL / "ultimo_sinal_v4_blackarrow.json")
    print(PASTA_OPERACIONAL / "log_sinal_v4_blackarrow.csv")


if __name__ == "__main__":
    main()