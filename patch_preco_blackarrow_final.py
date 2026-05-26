from pathlib import Path
import shutil
from datetime import datetime

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_patch_preco_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

# Troca leitura latin1 para UTF-8
txt = txt.replace('encoding="latin1"', 'encoding="utf-8-sig"')

antigo = 'ultimo = parse_numero_br(obter_valor_coluna_flexivel(row, ["Último", "Ultimo", "Ãšltimo", "�ltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"], np.nan))'

novo = '''ultimo_bruto = obter_valor_coluna_flexivel(
        row,
        ["Último", "Ultimo", "Ãšltimo", "�ltimo", "ultimo", "preco", "preço", "preco_close", "close", "Close", "Last", "last"],
        np.nan
    )

    # Fallback: no blackarrow_rtd.csv a 4ª coluna é o preço Último
    if pd.isna(parse_numero_br(ultimo_bruto)):
        try:
            if len(row) >= 4:
                ultimo_bruto = row.iloc[3]
        except Exception:
            pass

    ultimo = parse_numero_br(ultimo_bruto)'''

if antigo in txt:
    txt = txt.replace(antigo, novo)
else:
    print("ATENCAO: linha exata do ultimo nao encontrada. Nenhuma troca feita nessa parte.")

arquivo.write_text(txt, encoding="utf-8")

print("Patch final de preço aplicado com sucesso.")
