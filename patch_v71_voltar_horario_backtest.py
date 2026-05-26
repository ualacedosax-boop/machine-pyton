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
    backup = BACKUP_DIR / f"sinal_v71_BACKUP_antes_voltar_horario_backtest_{DATA}.py"
    shutil.copy2(ARQ, backup)
    print(f"Backup criado: {backup}")

    txt = ler(ARQ)
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")

    antigo = '''    horario_operacional_valido = dentro_horario and not bloqueio_0430

    # Trava oficial da V7.1:
    # só permite sinal nas janelas 03:45-03:55 e 04:45-04:55.
    dentro_janela_v71_oficial = dentro_janela_oficial_v71(hora_decimal)

    if not dentro_janela_v71_oficial:
        horario_operacional_valido = False
'''

    novo = '''    # Horário oficial fiel ao backtest V7.1:
    # 02:00 até 06:00, respeitando o bloqueio 04:30 até 04:45.
    horario_operacional_valido = dentro_horario and not bloqueio_0430

    # Campo mantido no JSON para o monitor.
    # Agora significa: dentro do horário do backtest.
    dentro_janela_v71_oficial = bool(horario_operacional_valido)
'''

    if antigo in txt:
        txt = txt.replace(antigo, novo, 1)
        print("Trava estreita removida.")
    else:
        print("AVISO: não encontrei o bloco exato da trava estreita.")
        print("Vou tentar ajustar pela linha principal.")

        alvo = "    horario_operacional_valido = dentro_horario and not bloqueio_0430\n"
        if alvo not in txt:
            raise RuntimeError("Não encontrei a linha horario_operacional_valido.")

        # Remove apenas o efeito da trava, se ela já existir.
        txt = re.sub(
            r'\n    # Trava oficial da V7\.1:\n'
            r'    # só permite sinal nas janelas 03:45-03:55 e 04:45-04:55\.\n'
            r'    dentro_janela_v71_oficial = dentro_janela_oficial_v71\(hora_decimal\)\n\n'
            r'    if not dentro_janela_v71_oficial:\n'
            r'        horario_operacional_valido = False\n',
            '\n    dentro_janela_v71_oficial = bool(horario_operacional_valido)\n',
            txt,
            count=1
        )

    txt = txt.replace('"janela_v71_1": "03:45-03:55"', '"janela_v71_1": "02:00-06:00"')
    txt = txt.replace('"janela_v71_2": "04:45-04:55"', '"janela_v71_2": "bloqueio 04:30-04:45"')

    salvar(ARQ, txt)

    print("Testando compilação...")
    py_compile.compile(str(ARQ), doraise=True)

    print("OK: V7.1 compilou.")
    print("Agora está fiel ao horário do backtest: 02:00-06:00 com bloqueio 04:30-04:45.")
    print(f"Arquivo atualizado: {ARQ}")

if __name__ == "__main__":
    main()
