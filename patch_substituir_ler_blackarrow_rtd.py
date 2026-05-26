from pathlib import Path
import shutil
from datetime import datetime
import re

arquivo = Path("sinal_v4_blackarrow_tempo_real.py")

backup = Path(f"sinal_v4_blackarrow_tempo_real_BACKUP_antes_substituir_ler_blackarrow_rtd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
shutil.copy2(arquivo, backup)

print("Backup criado:")
print(backup)

txt = arquivo.read_text(encoding="utf-8-sig")

nova_funcao = r'''
def ler_blackarrow_rtd():
    if not os.path.exists(ARQUIVO_BLACKARROW_RTD):
        raise FileNotFoundError(f"Nao encontrei: {ARQUIVO_BLACKARROW_RTD}")

    ultimo_erro = None
    df = None

    # O BlackArrow costuma exportar com ; e encoding ANSI/latin1/cp1252
    for enc in ["latin1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(
                ARQUIVO_BLACKARROW_RTD,
                sep=";",
                encoding=enc,
                dtype=str,
                engine="python"
            )
            break
        except Exception as e:
            ultimo_erro = e
            df = None

    if df is None:
        raise Exception(f"Falha ao ler blackarrow_rtd.csv: {ultimo_erro}")

    if df.empty:
        raise Exception("Arquivo blackarrow_rtd.csv esta vazio.")

    row = df.iloc[-1]

    def valor_pos(pos, padrao=np.nan):
        try:
            if len(row) > pos:
                return row.iloc[pos]
        except Exception:
            pass
        return padrao

    def num(x):
        try:
            if x is None:
                return np.nan

            s = str(x).strip()

            if s == "" or s.lower() in ["nan", "none", "null"]:
                return np.nan

            s = s.replace('"', '').replace("'", "").strip()

            # Formato BR: 29.542,25 ou 29542,25
            if "," in s:
                s = s.replace(".", "")
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")

            return float(s)
        except Exception:
            return np.nan

    asset = str(valor_pos(0, "")).replace('"', '').strip()
    data_txt = str(valor_pos(1, "")).replace('"', '').strip()
    hora_txt = str(valor_pos(2, "")).replace('"', '').strip()

    # Preferencia absoluta pela posicao do arquivo RTD:
    # coluna 3 = Ultimo
    ultimo = num(valor_pos(3, np.nan))

    abertura = num(valor_pos(4, np.nan))
    maximo = num(valor_pos(5, np.nan))
    minimo = num(valor_pos(6, np.nan))
    strike = num(valor_pos(7, np.nan))
    negocios = num(valor_pos(8, np.nan))

    if pd.isna(ultimo):
        # Diagnostico simples para aparecer no erro
        try:
            cols = list(df.columns)
            vals = [str(valor_pos(i, "")) for i in range(min(len(row), 10))]
            raise Exception(f"Preco Ultimo invalido no CSV do BlackArrow. Colunas={cols}; Valores={vals}")
        except Exception as e:
            raise Exception(str(e))

    datahora_sp = pd.to_datetime(
        data_txt + " " + hora_txt,
        dayfirst=True,
        errors="coerce"
    )

    if pd.isna(datahora_sp):
        datahora_sp = pd.Timestamp.now()

    return {
        "Asset": asset,
        "DataHora_SP": datahora_sp,
        "Data": datahora_sp.date(),
        "Hora_SP_Decimal": datahora_sp.hour + datahora_sp.minute / 60.0 + datahora_sp.second / 3600.0,
        "ultimo": float(ultimo),
        "abertura": float(abertura) if not pd.isna(abertura) else np.nan,
        "maximo": float(maximo) if not pd.isna(maximo) else np.nan,
        "minimo": float(minimo) if not pd.isna(minimo) else np.nan,
        "strike": float(strike) if not pd.isna(strike) else np.nan,
        "negocios_acumulado": float(negocios) if not pd.isna(negocios) else np.nan,
    }

'''

padrao = r'def ler_blackarrow_rtd\(\):.*?\n(?=def atualizar_ticks\()'

novo_txt, n = re.subn(padrao, nova_funcao + "\n", txt, flags=re.DOTALL)

if n == 0:
    print("ERRO: nao encontrei o bloco def ler_blackarrow_rtd() para substituir.")
else:
    arquivo.write_text(novo_txt, encoding="utf-8")
    print("Funcao ler_blackarrow_rtd substituida com sucesso.")
