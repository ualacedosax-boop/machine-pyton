# -*- coding: utf-8 -*-
"""
Verifica se o blackarrow_rtd.csv tem dados de hoje.
Retorna codigo 0 se OK, 1 se desatualizado.
Chamado pelo INICIAR_V71.bat
"""
import os
import sys
from datetime import datetime

BASE = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"
CSV  = os.path.join(BASE, "blackarrow_rtd.csv")

if not os.path.exists(CSV):
    print("      CSV nao encontrado:", CSV)
    sys.exit(1)

# Verificar idade do arquivo
import time
idade = time.time() - os.path.getmtime(CSV)
if idade > 300:  # mais de 5 minutos sem atualizar
    print(f"      CSV desatualizado (sem update ha {int(idade)}s)")
    sys.exit(1)

# Verificar se tem data de hoje
hoje = datetime.now().strftime("%d/%m/%Y")
try:
    with open(CSV, encoding='latin-1') as f:
        conteudo = f.read()
    if hoje in conteudo:
        print(f"      CSV com dados de hoje ({hoje}). OK")
        sys.exit(0)
    else:
        print(f"      CSV sem dados de hoje ({hoje})")
        sys.exit(1)
except Exception as e:
    print(f"      Erro ao ler CSV: {e}")
    sys.exit(1)
