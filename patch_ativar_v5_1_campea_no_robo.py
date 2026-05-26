# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import re
import py_compile

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
ARQ = BASE / "sinal_v4_blackarrow_tempo_real.py"

backup = BASE / f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_v5_1_campea_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
backup.write_text(ARQ.read_text(encoding="utf-8"), encoding="utf-8")

txt = ARQ.read_text(encoding="utf-8")

# ============================================================
# 1) ADICIONA PASTA DA V5.1 OPERACIONAL
# ============================================================

if 'PASTA_V5_1 = os.path.join(BASE_DIR, "OPERACIONAL_V5_1_CAMPEA")' not in txt:
    txt = txt.replace(
        'PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")',
        'PASTA_V4 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v4_antiloss")\n'
        'PASTA_V5_1 = os.path.join(BASE_DIR, "OPERACIONAL_V5_1_CAMPEA")'
    )

# Mantém ARQUIVO_CONFIG_V4 antigo, porque ele guarda take/stop/horário.
# Troca só modelo e features para V5.1.
txt = re.sub(
    r'ARQUIVO_MODELO_V4\s*=\s*os\.path\.join\(PASTA_V4,\s*"modelo_v4_antiloss\.joblib"\)',
    'ARQUIVO_MODELO_V4 = os.path.join(PASTA_V5_1, "modelo_v5_1_campea.joblib")',
    txt
)

txt = re.sub(
    r'ARQUIVO_FEATURES_V4\s*=\s*os\.path\.join\(PASTA_V4,\s*"features_modelo_v4\.joblib"\)',
    'ARQUIVO_FEATURES_V4 = os.path.join(PASTA_V5_1, "features_v5_1_campea.joblib")',
    txt
)

# ============================================================
# 2) FORÇA THRESHOLD DA V5.1
# ============================================================

# A V5.1 campeã usa threshold 0.575.
# Vamos garantir isso após carregar config da V4.
padrao_config = 'config_v4 = carregar_config_v4()'
novo_config = '''config_v4 = carregar_config_v4()

    # ========================================================
    # V5.1 CAMPEÃ - threshold oficial
    # ========================================================
    config_v4["prob_win_min"] = 0.575
    config_v4["modelo_operacional"] = "V5.1_CAMPEA"
'''

if 'config_v4["modelo_operacional"] = "V5.1_CAMPEA"' not in txt:
    txt = txt.replace(padrao_config, novo_config, 1)

# ============================================================
# 3) SUBSTITUI FUNÇÃO calcular_prob_v4 PARA SUPORTAR BUY/SELL
# ============================================================

pattern_func = r'def calcular_prob_v4\(modelo_v4, X_v4\):.*?return float\(pred\)\s*'
nova_func = '''def calcular_prob_v4(modelo_v4, X_v4, direcao=None):
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


'''

txt2, n = re.subn(pattern_func, nova_func, txt, flags=re.DOTALL)

if n == 0:
    raise RuntimeError("Não encontrei a função calcular_prob_v4 para substituir.")

txt = txt2

# ============================================================
# 4) ALTERA A CHAMADA PARA PASSAR A DIREÇÃO
# ============================================================

antigo = 'prob_win_v4 = calcular_prob_v4(modelo_v4, X_v4)'
novo = '''direcao_modelo_v5_1 = None
    try:
        if isinstance(score_v3, dict):
            direcao_modelo_v5_1 = score_v3.get("Direcao", score_v3.get("direcao", None))
        elif hasattr(score_v3, "get"):
            direcao_modelo_v5_1 = score_v3.get("Direcao", None)
    except Exception:
        direcao_modelo_v5_1 = None

    prob_win_v4 = calcular_prob_v4(modelo_v4, X_v4, direcao_modelo_v5_1)'''

if antigo in txt:
    txt = txt.replace(antigo, novo, 1)
else:
    print("ATENÇÃO: chamada antiga de calcular_prob_v4 não encontrada. Verifique manualmente.")

# ============================================================
# 5) AJUSTA PRINTS PARA NÃO CONFUNDIR
# ============================================================

txt = txt.replace(
    'print("Modelo V4 carregado:", ARQUIVO_MODELO_V4)',
    'print("Modelo operacional carregado:", ARQUIVO_MODELO_V4)'
)

txt = txt.replace(
    'print("Features V4:", len(features))',
    'print("Features operacional:", len(features))'
)

txt = txt.replace(
    'print("\\nConfig V4:")',
    'print("\\nConfig operacional:")'
)

# ============================================================
# 6) SALVA E TESTA COMPILAÇÃO
# ============================================================

ARQ.write_text(txt, encoding="utf-8")

py_compile.compile(str(ARQ), doraise=True)

print("Patch V5.1 aplicado com sucesso.")
print("Backup criado em:")
print(backup)
print("Arquivo compilou sem erro.")
