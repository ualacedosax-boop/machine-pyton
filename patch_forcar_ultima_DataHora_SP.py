from pathlib import Path
import shutil
from datetime import datetime
import re

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_patch_forcar_ultima_DataHora_SP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

funcao = r'''

# ============================================================
# CORRIGIR SERIE ULTIMA COM DADOS DE HORARIO DO DF ORIGINAL
# ============================================================

def corrigir_ultima_com_df_feat(ultima, df_feat):
    import pandas as pd

    try:
        if ultima is None:
            return ultima

        if df_feat is None or len(df_feat) == 0:
            if "DataHora_SP" not in ultima.index:
                ultima["DataHora_SP"] = pd.Timestamp.now()
            if "Data" not in ultima.index:
                ultima["Data"] = pd.Timestamp.now().date()
            if "Hora_SP_Decimal" not in ultima.index:
                agora = pd.Timestamp.now()
                ultima["Hora_SP_Decimal"] = agora.hour + agora.minute / 60.0 + agora.second / 3600.0
            return ultima

        base = df_feat.copy()

        if "DataHora_SP" not in base.columns:
            base = garantir_coluna_datahora_sp(base)

        if "DataHora_SP" in base.columns:
            dt = pd.to_datetime(base["DataHora_SP"].iloc[-1], errors="coerce")
            if pd.isna(dt):
                dt = pd.Timestamp.now()

            ultima["DataHora_SP"] = dt

            if "Data" not in ultima.index:
                ultima["Data"] = dt.date()

            if "Hora_SP_Decimal" not in ultima.index:
                ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        else:
            dt = pd.Timestamp.now()
            ultima["DataHora_SP"] = dt

            if "Data" not in ultima.index:
                ultima["Data"] = dt.date()

            if "Hora_SP_Decimal" not in ultima.index:
                ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        return ultima

    except Exception:
        try:
            dt = pd.Timestamp.now()
            ultima["DataHora_SP"] = dt
            ultima["Data"] = dt.date()
            ultima["Hora_SP_Decimal"] = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        except Exception:
            pass

        return ultima

'''

if "def corrigir_ultima_com_df_feat" not in txt:
    pos = txt.find("\ndef ")
    if pos >= 0:
        txt = txt[:pos + 1] + funcao + "\n" + txt[pos + 1:]
    else:
        txt = funcao + "\n" + txt

# Coloca a correcao imediatamente depois de qualquer chamada preparar_X(df_feat, features_v3)
padrao = r"(X_v3,\s*ultima\s*=\s*preparar_X\(df_feat,\s*features_v3\)\s*)"

if "ultima = corrigir_ultima_com_df_feat(ultima, df_feat)" not in txt:
    txt = re.sub(
        padrao,
        r"\1\n    ultima = corrigir_ultima_com_df_feat(ultima, df_feat)\n",
        txt
    )

# Substitui acessos diretos mais perigosos por get seguro
txt = txt.replace('ultima["DataHora_SP"]', 'ultima.get("DataHora_SP", pd.Timestamp.now())')
txt = txt.replace("ultima['DataHora_SP']", "ultima.get('DataHora_SP', pd.Timestamp.now())")

arquivo.write_text(txt, encoding="utf-8")

print("Patch forte DataHora_SP aplicado com sucesso.")
