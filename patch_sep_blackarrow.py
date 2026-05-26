from pathlib import Path
import shutil
from datetime import datetime
import re

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_sep_blackarrow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

# Garante leitura do RTD com separador ;
txt = re.sub(
    r'pd\.read_csv\(\s*ARQUIVO_BLACKARROW_RTD\s*,\s*encoding="utf-8-sig"\s*\)',
    'pd.read_csv(ARQUIVO_BLACKARROW_RTD, sep=";", encoding="utf-8-sig")',
    txt
)

txt = re.sub(
    r'pd\.read_csv\(\s*ARQUIVO_BLACKARROW_RTD\s*\)',
    'pd.read_csv(ARQUIVO_BLACKARROW_RTD, sep=";", encoding="utf-8-sig")',
    txt
)

txt = txt.replace(
    'pd.read_csv(\n        ARQUIVO_BLACKARROW_RTD,\n        encoding="utf-8-sig",',
    'pd.read_csv(\n        ARQUIVO_BLACKARROW_RTD,\n        sep=";",\n        encoding="utf-8-sig",'
)

# Inclui também a coluna com caractere quebrado no PowerShell: �ltimo
txt = txt.replace(
    '["Último", "Ultimo", "Ãšltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"]',
    '["Último", "Ultimo", "Ãšltimo", "�ltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"]'
)

arquivo.write_text(txt, encoding="utf-8")

print("Patch separador ; e coluna preco aplicado com sucesso.")
