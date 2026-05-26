from pathlib import Path
from datetime import datetime
import shutil
import py_compile

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
ARQ = BASE_DIR / "sinal_v71_blackarrow_tempo_real_log_inteligente.py"
BACKUP_DIR = BASE_DIR / "backups_v71_oficial"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

DATA = datetime.now().strftime("%Y%m%d_%H%M%S")


def ler(caminho: Path) -> str:
    for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
        try:
            return caminho.read_text(encoding=enc)
        except Exception:
            pass
    return caminho.read_text(encoding="utf-8", errors="replace")


def salvar(caminho: Path, texto: str):
    caminho.write_text(texto, encoding="utf-8")


def main():
    backup = BACKUP_DIR / f"sinal_v71_BACKUP_antes_patch_janelas_v3_{DATA}.py"
    shutil.copy2(ARQ, backup)
    print(f"Backup criado: {backup}")

    txt = ler(ARQ)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")

    bloco_funcao = '''
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


'''

    if "def dentro_janela_oficial_v71" not in txt:
        marcador = "def obter_valor_coluna_flexivel"
        pos = txt.find(marcador)

        if pos >= 0:
            txt = txt[:pos] + bloco_funcao + txt[pos:]
            print("Função de janela V7.1 inserida.")
        else:
            txt = bloco_funcao + txt
            print("Função de janela V7.1 inserida no início.")
    else:
        print("Função de janela V7.1 já existia.")

    alvo = "    horario_operacional_valido = dentro_horario and not bloqueio_0430\n"

    novo = '''    horario_operacional_valido = dentro_horario and not bloqueio_0430

    # Trava oficial da V7.1:
    # só permite sinal nas janelas 03:45-03:55 e 04:45-04:55.
    dentro_janela_v71_oficial = dentro_janela_oficial_v71(hora_decimal)

    if not dentro_janela_v71_oficial:
        horario_operacional_valido = False
'''

    if "dentro_janela_v71_oficial = dentro_janela_oficial_v71(hora_decimal)" not in txt:
        if alvo not in txt:
            raise RuntimeError("Não encontrei a linha exata: horario_operacional_valido = dentro_horario and not bloqueio_0430")
        txt = txt.replace(alvo, novo, 1)
        print("Trava de janela V7.1 aplicada.")
    else:
        print("Trava de janela V7.1 já existia.")

    alvo_payload = '        "horario_operacional_valido": bool(horario_operacional_valido),\n'

    novo_payload = '''        "horario_operacional_valido": bool(horario_operacional_valido),
        "dentro_janela_v71_oficial": bool(dentro_janela_v71_oficial),
        "janela_v71_1": "03:45-03:55",
        "janela_v71_2": "04:45-04:55",
'''

    if '"dentro_janela_v71_oficial": bool(dentro_janela_v71_oficial),' not in txt:
        if alvo_payload not in txt:
            raise RuntimeError("Não encontrei o campo horario_operacional_valido no payload.")
        txt = txt.replace(alvo_payload, novo_payload, 1)
        print("Campos de janela V7.1 adicionados no payload.")
    else:
        print("Campos de janela V7.1 já existiam no payload.")

    salvar(ARQ, txt)

    print("Testando compilação...")
    py_compile.compile(str(ARQ), doraise=True)

    print("OK: V7.1 compilou com janelas oficiais.")
    print(f"Arquivo atualizado: {ARQ}")


if __name__ == "__main__":
    main()
