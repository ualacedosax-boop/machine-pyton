from pathlib import Path
import shutil
from datetime import datetime

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_ultima_pos_preparar_X_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

antigo = "    X_v3, ultima = preparar_X(df_feat, features_v3)"

novo = '''    X_v3, ultima = preparar_X(df_feat, features_v3)

    # Garantia: preparar_X pode retornar ultima apenas com colunas do modelo.
    # Entao recolocamos DataHora_SP a partir do df_feat original.
    if "DataHora_SP" not in ultima.index and "DataHora_SP" in df_feat.columns:
        ultima["DataHora_SP"] = df_feat["DataHora_SP"].iloc[-1]

    if "Data" not in ultima.index and "Data" in df_feat.columns:
        ultima["Data"] = df_feat["Data"].iloc[-1]

    if "Hora_SP_Decimal" not in ultima.index and "Hora_SP_Decimal" in df_feat.columns:
        ultima["Hora_SP_Decimal"] = df_feat["Hora_SP_Decimal"].iloc[-1]
'''

if antigo not in txt:
    print("ATENCAO: trecho exato nao encontrado.")
else:
    txt = txt.replace(antigo, novo)

arquivo.write_text(txt, encoding="utf-8")

print("Patch aplicado com sucesso.")
