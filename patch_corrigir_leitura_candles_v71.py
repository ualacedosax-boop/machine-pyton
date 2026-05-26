from pathlib import Path
from datetime import datetime
import shutil
import re

ARQ = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\sinal_v71_blackarrow_tempo_real_log_inteligente.py")
BACKUP = ARQ.with_name(f"sinal_v71_BACKUP_antes_corrigir_leitura_candles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")

shutil.copy2(ARQ, BACKUP)
print("Backup criado:", BACKUP)

txt = ARQ.read_text(encoding="utf-8", errors="ignore")

funcao = r'''

# ============================================================
# LEITURA ROBUSTA DOS CANDLES V7.1
# Aceita CSV com cabeçalho ou sem cabeçalho.
# Garante a coluna DataHora_SP.
# ============================================================
COLUNAS_CANDLES_V71 = [
    "DataHora_SP",
    "DataHora",
    "Data",
    "Hora_SP_Decimal",
    "open",
    "high",
    "low",
    "close",
    "Negocios",
    "preco_close",
    "qtd_ticks",
    "flag",
    "qtd_ticks2",
    "Asset",
    "Asset2",
]

def ler_candles_v71_corrigido(caminho):
    import pandas as pd

    try:
        df = pd.read_csv(caminho)
    except Exception:
        df = pd.read_csv(caminho, header=None)

    # Se leu errado como header=None ou se veio sem DataHora_SP
    if "DataHora_SP" not in df.columns:
        df = pd.read_csv(caminho, header=None)

        # Se a primeira linha for cabeçalho, remove ela
        primeira = [str(x).strip() for x in df.iloc[0].tolist()]
        if "DataHora_SP" in primeira:
            df = df.iloc[1:].copy()

        if df.shape[1] >= len(COLUNAS_CANDLES_V71):
            df = df.iloc[:, :len(COLUNAS_CANDLES_V71)].copy()
            df.columns = COLUNAS_CANDLES_V71
        else:
            raise RuntimeError(f"Arquivo de candles tem {df.shape[1]} colunas; esperado {len(COLUNAS_CANDLES_V71)}.")

    df.columns = [str(c).strip() for c in df.columns]

    # Alias de segurança
    if "DataHora_SP" not in df.columns and "DataHora" in df.columns:
        df["DataHora_SP"] = df["DataHora"]

    if "DataHora_SP" not in df.columns:
        raise RuntimeError("Coluna DataHora_SP não encontrada após leitura robusta dos candles.")

    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df = df.sort_values("DataHora_SP").copy()

    if "DataHora" not in df.columns:
        df["DataHora"] = df["DataHora_SP"]
    else:
        df["DataHora"] = df["DataHora_SP"]

    df["Data"] = df["DataHora_SP"].dt.strftime("%Y-%m-%d")
    df["Hora_SP_Decimal"] = df["DataHora_SP"].dt.hour + df["DataHora_SP"].dt.minute / 60.0

    for c in ["open", "high", "low", "close", "Negocios", "preco_close"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "preco_close" not in df.columns and "close" in df.columns:
        df["preco_close"] = df["close"]

    return df
'''

if "def ler_candles_v71_corrigido" not in txt:
    # coloca depois dos imports
    m = re.search(r"(import .*\n|from .* import .*\n)+", txt)
    if m:
        pos = m.end()
        txt = txt[:pos] + funcao + "\n" + txt[pos:]
    else:
        txt = funcao + "\n" + txt

# Substitui leituras diretas do arquivo de candles por leitura robusta.
# Mantém outras leituras CSV intactas.
padroes = [
    r"pd\.read_csv\(([^)]*blackarrow_candles_2min[^)]*)\)",
    r"pd\.read_csv\(([^)]*ARQ_CANDLES[^)]*)\)",
    r"pd\.read_csv\(([^)]*CAMINHO_CANDLES[^)]*)\)",
    r"pd\.read_csv\(([^)]*arquivo_candles[^)]*)\)",
]

alterou = False

for p in padroes:
    novo, n = re.subn(p, r"ler_candles_v71_corrigido(\1)", txt)
    if n > 0:
        alterou = True
        txt = novo
        print(f"Substituições no padrão {p}: {n}")

# Correção extra: se o código usa variável candles_path/path_candles com pd.read_csv,
# deixa para o diagnóstico caso não substitua.
ARQ.write_text(txt, encoding="utf-8")

print()
if alterou:
    print("Patch aplicado: leitura dos candles agora é robusta.")
else:
    print("ATENÇÃO: não encontrei leitura direta do arquivo de candles para substituir.")
    print("Mesmo assim inseri a função ler_candles_v71_corrigido no código.")

print()
print("Testando compilação...")
import py_compile
py_compile.compile(str(ARQ), doraise=True)
print("OK: robô compilou.")
