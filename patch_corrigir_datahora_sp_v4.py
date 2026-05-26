from pathlib import Path
import shutil
from datetime import datetime

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_DataHora_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

funcao = r'''

# ============================================================
# GARANTIR COLUNA DataHora_SP
# ============================================================

def garantir_coluna_datahora_sp(df):
    import pandas as pd

    if df is None:
        return df

    if "DataHora_SP" in df.columns:
        df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        return df

    candidatas = [
        "datahora_ultimo_candle_sp",
        "datahora_candle_sp",
        "datahora_sp",
        "DataHora",
        "datahora",
        "datetime",
        "time",
        "date",
        "Date",
        "Time",
    ]

    for col in candidatas:
        if col in df.columns:
            df["DataHora_SP"] = pd.to_datetime(df[col], errors="coerce")
            return df

    return df

'''

if "def garantir_coluna_datahora_sp" not in txt:
    pos = txt.find("\ndef ")
    if pos >= 0:
        txt = txt[:pos + 1] + funcao + "\n" + txt[pos + 1:]
    else:
        txt = funcao + "\n" + txt

# Aplica a garantia antes dos modelos V3 e V4, se ainda nao existir perto das chamadas
txt = txt.replace(
    "X_v3 = features_v3[features_modelo_v3].copy()",
    "features_v3 = garantir_coluna_datahora_sp(features_v3)\n    X_v3 = features_v3[features_modelo_v3].copy()"
)

txt = txt.replace(
    "X_v4 = features_v4[features_modelo_v4].copy()",
    "features_v4 = garantir_coluna_datahora_sp(features_v4)\n    X_v4 = features_v4[features_modelo_v4].copy()"
)

txt = txt.replace(
    "X_v3 = df[features_modelo_v3].copy()",
    "df = garantir_coluna_datahora_sp(df)\n    X_v3 = df[features_modelo_v3].copy()"
)

txt = txt.replace(
    "X_v4 = df[features_modelo_v4].copy()",
    "df = garantir_coluna_datahora_sp(df)\n    X_v4 = df[features_modelo_v4].copy()"
)

arquivo.write_text(txt, encoding="utf-8")

print("Patch DataHora_SP aplicado com sucesso.")
