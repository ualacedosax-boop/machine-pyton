from pathlib import Path
import shutil
from datetime import datetime
import re

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_coluna_preco_blackarrow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

funcao = r'''

# ============================================================
# OBTER COLUNA FLEXIVEL DO BLACKARROW
# ============================================================

def obter_valor_coluna_flexivel(row, nomes, padrao=np.nan):
    try:
        # tenta nomes exatos
        for nome in nomes:
            if nome in row.index:
                return row.get(nome, padrao)

        # tenta ignorando acentos, maiusculas e caracteres quebrados
        mapa = {}
        for col in row.index:
            chave = str(col).strip().lower()
            chave = (
                chave.replace("á", "a")
                     .replace("à", "a")
                     .replace("ã", "a")
                     .replace("â", "a")
                     .replace("é", "e")
                     .replace("ê", "e")
                     .replace("í", "i")
                     .replace("ó", "o")
                     .replace("ô", "o")
                     .replace("õ", "o")
                     .replace("ú", "u")
                     .replace("ç", "c")
            )
            mapa[chave] = col

        for nome in nomes:
            chave = str(nome).strip().lower()
            chave = (
                chave.replace("á", "a")
                     .replace("à", "a")
                     .replace("ã", "a")
                     .replace("â", "a")
                     .replace("é", "e")
                     .replace("ê", "e")
                     .replace("í", "i")
                     .replace("ó", "o")
                     .replace("ô", "o")
                     .replace("õ", "o")
                     .replace("ú", "u")
                     .replace("ç", "c")
            )
            if chave in mapa:
                return row.get(mapa[chave], padrao)

        return padrao
    except Exception:
        return padrao

'''

if "def obter_valor_coluna_flexivel" not in txt:
    pos = txt.find("\ndef ")
    if pos >= 0:
        txt = txt[:pos + 1] + funcao + "\n" + txt[pos + 1:]
    else:
        txt = funcao + "\n" + txt

# Corrige leitura do preço Último
txt = re.sub(
    r'ultimo\s*=\s*parse_numero_br\(row\.get\(".*?ltimo",\s*np\.nan\)\)',
    'ultimo = parse_numero_br(obter_valor_coluna_flexivel(row, ["Último", "Ultimo", "Ãšltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"], np.nan))',
    txt
)

# Se a substituição acima não encontrar por causa de encoding, tenta forma direta comum
txt = txt.replace(
    'ultimo = parse_numero_br(row.get("Ãšltimo", np.nan))',
    'ultimo = parse_numero_br(obter_valor_coluna_flexivel(row, ["Último", "Ultimo", "Ãšltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"], np.nan))'
)

arquivo.write_text(txt, encoding="utf-8")

print("Patch coluna preço BlackArrow aplicado com sucesso.")
