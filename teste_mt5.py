from pathlib import Path
import subprocess

print("RODANDO ARQUIVO NOVO")

MT5_TERMINAL = r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe"

print("MT5_TERMINAL =", MT5_TERMINAL)
print("EXISTE?", Path(MT5_TERMINAL).exists())

if not Path(MT5_TERMINAL).exists():
    raise FileNotFoundError(f"MT5 não encontrado em: {MT5_TERMINAL}")

subprocess.Popen([MT5_TERMINAL])
print("MT5 aberto com sucesso")