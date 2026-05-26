from pathlib import Path
import re
import shutil
from datetime import datetime

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_inf_nan_FINAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

funcao = r'''

# ============================================================
# LIMPEZA DE INF / NAN PARA MODELOS ML
# ============================================================

def limpar_inf_nan_ml(X):
    import numpy as np
    import pandas as pd

    if isinstance(X, pd.DataFrame):
        X = X.replace([np.inf, -np.inf], 0)
        X = X.fillna(0)

        for col in X.columns:
            try:
                X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
            except Exception:
                X[col] = 0

        return X

    try:
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        return X

'''

if "def limpar_inf_nan_ml" not in txt:
    m = re.search(r"\ndef\s+", txt)
    if m:
        pos = m.start() + 1
        txt = txt[:pos] + funcao + "\n" + txt[pos:]
    else:
        txt = funcao + "\n" + txt

txt = re.sub(
    r"probas\s*=\s*modelo_v3\.predict_proba\(\s*X_v3\s*\)",
    "probas = modelo_v3.predict_proba(limpar_inf_nan_ml(X_v3))",
    txt
)

txt = re.sub(
    r"prob\s*=\s*modelo_v4\.predict_proba\(\s*X_v4\s*\)\s*\[0\]\s*\[1\]",
    "prob = modelo_v4.predict_proba(limpar_inf_nan_ml(X_v4))[0][1]",
    txt
)

txt = re.sub(
    r"pred\s*=\s*modelo_v4\.predict\(\s*X_v4\s*\)\s*\[0\]",
    "pred = modelo_v4.predict(limpar_inf_nan_ml(X_v4))[0]",
    txt
)

arquivo.write_text(txt, encoding="utf-8")

print("Patch aplicado com sucesso.")
