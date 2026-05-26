from pathlib import Path
from datetime import datetime
import shutil
import py_compile
import re

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
    if not ARQ.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQ}")

    backup = BACKUP_DIR / f"sinal_v71_BACKUP_antes_patch_janelas_v2_{DATA}.py"
    shutil.copy2(ARQ, backup)
    print(f"Backup criado: {backup}")

    txt = ler(ARQ)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")

    # =====================================================
    # 1. Inserir função de janela oficial V7.1
    # =====================================================

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
            print("Função dentro_janela_oficial_v71 inserida antes de obter_valor_coluna_flexivel.")
        else:
            txt = bloco_funcao + txt
            print("Função dentro_janela_oficial_v71 inserida no início do arquivo.")
    else:
        print("Função dentro_janela_oficial_v71 já existia.")

    # =====================================================
    # 2. Aplicar trava onde existir horario_operacional_valido
    # =====================================================

    if "dentro_janela_v71_oficial = dentro_janela_oficial_v71(hora_decimal)" not in txt:
        padrao = r'(?P<indent>[ \t]*)horario_operacional_valido\s*=\s*bool\((?P<expr>.*?)\)'

        matches = list(re.finditer(padrao, txt))

        if not matches:
            raise RuntimeError("Não encontrei nenhuma linha com horario_operacional_valido = bool(...).")

        # Usa a primeira ocorrência encontrada.
        m = matches[0]
        indent = m.group("indent")
        linha_original = m.group(0)

        bloco_trava = (
            linha_original
            + "\n\n"
            + indent + "# Trava oficial da V7.1:\n"
            + indent + "# só permite sinal nas janelas 03:45-03:55 e 04:45-04:55.\n"
            + indent + "dentro_janela_v71_oficial = dentro_janela_oficial_v71(hora_decimal)\n\n"
            + indent + "if not dentro_janela_v71_oficial:\n"
            + indent + "    horario_operacional_valido = False"
        )

        txt = txt[:m.start()] + bloco_trava + txt[m.end():]
        print("Trava de janela aplicada em horario_operacional_valido.")

    else:
        print("Trava de janela já existia.")

    # =====================================================
    # 3. Garantir variável padrão caso payload use antes
    # =====================================================

    if "dentro_janela_v71_oficial" in txt:
        # Não precisa fazer nada aqui; variável já foi inserida no fluxo.
        pass

    # =====================================================
    # 4. Inserir campos no payload
    # =====================================================

    if '"dentro_janela_v71_oficial"' not in txt:
        alvo_payload = '"horario_operacional_valido": bool(horario_operacional_valido),'

        if alvo_payload in txt:
            novo_payload = (
                alvo_payload
                + '\n        "dentro_janela_v71_oficial": bool(dentro_janela_v71_oficial),'
                + '\n        "janela_v71_1": "03:45-03:55",'
                + '\n        "janela_v71_2": "04:45-04:55",'
            )

            txt = txt.replace(alvo_payload, novo_payload, 1)
            print("Campos de janela V7.1 inseridos no payload.")
        else:
            print("AVISO: não encontrei campo horario_operacional_valido no payload.")
    else:
        print("Campos de janela V7.1 já existem no payload.")

    salvar(ARQ, txt)

    print("Testando compilação...")

    py_compile.compile(str(ARQ), doraise=True)

    print("OK: V7.1 compilou com janelas oficiais.")
    print(f"Arquivo atualizado: {ARQ}")


if __name__ == "__main__":
    main()