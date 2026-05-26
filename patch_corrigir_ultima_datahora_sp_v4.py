from pathlib import Path
import shutil
from datetime import datetime

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_ultima_DataHora_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

antigo = 'datahora_ultimo_candle = str(ultima["DataHora_SP"])'

novo = '''
    if "DataHora_SP" in ultima.index:
        datahora_ultimo_candle = str(ultima["DataHora_SP"])
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
'''

if antigo not in txt:
    print("ATENCAO: linha exata nao encontrada. Vou tentar substituir por trecho parecido.")
    txt = txt.replace('str(ultima["DataHora_SP"])', 'str(ultima.get("DataHora_SP", pd.Timestamp.now()))')
else:
    txt = txt.replace(antigo, novo)

arquivo.write_text(txt, encoding="utf-8")

print("Patch ultima DataHora_SP aplicado com sucesso.")
