from pathlib import Path
from datetime import datetime
import py_compile
import shutil

BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

ARQ = BASE_DIR / "sinal_v71_blackarrow_tempo_real_log_inteligente.py"
PASTA_BACKUP = BASE_DIR / "backups_v71_oficial"
PASTA_BACKUP.mkdir(parents=True, exist_ok=True)

DATA = datetime.now().strftime("%Y%m%d_%H%M%S")


def ler_texto(caminho: Path) -> str:
    for enc in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
        try:
            return caminho.read_text(encoding=enc)
        except Exception:
            pass
    return caminho.read_text(encoding="utf-8", errors="replace")


def salvar_texto(caminho: Path, texto: str):
    caminho.write_text(texto, encoding="utf-8")


def mostrar_linhas(texto: str, ini: int, fim: int):
    linhas = texto.splitlines()
    for i in range(max(1, ini), min(len(linhas), fim) + 1):
        print(f"{i:05d}: {linhas[i - 1]}")


def main():
    if not ARQ.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQ}")

    backup = PASTA_BACKUP / f"sinal_v71_BACKUP_antes_corrigir_indent_{DATA}.py"
    shutil.copy2(ARQ, backup)
    print(f"Backup criado: {backup}")

    texto = ler_texto(ARQ)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    def_montar = "def montar_X_v4(df_features, ultima, score_v3, feature_cols_v4):"
    def_calc = "def calcular_prob_v53("

    pos_montar = texto.find(def_montar)
    if pos_montar < 0:
        print("Não encontrei def montar_X_v4.")
        raise RuntimeError("Não foi possível corrigir automaticamente.")

    pos_calc = texto.find(def_calc, pos_montar)

    if pos_calc < 0:
        print("Não encontrei def calcular_prob_v53 depois de montar_X_v4.")
        print("Mostrando trecho ao redor da linha 1754:")
        mostrar_linhas(texto, 1735, 1785)
        raise RuntimeError("Não foi possível corrigir automaticamente.")

    # Se a função calcular_prob_v53 ficou logo depois do cabeçalho de montar_X_v4,
    # significa que ela entrou dentro do lugar errado.
    trecho_entre = texto[pos_montar + len(def_montar):pos_calc]

    if len(trecho_entre.strip()) > 0:
        print("Existe conteúdo entre montar_X_v4 e calcular_prob_v53. Vou mostrar para conferência:")
        print(trecho_entre[:500])
        raise RuntimeError("Estrutura diferente do esperado. Precisa corrigir manualmente.")

    marcador_fim_calc = '''        return {
            "prob_v5_3": np.nan,
            "prob_v53_min": PROB_V53_MIN_OFICIAL,
            "v53_aprovou_modelo": False,
            "erro_v53": str(e),
        }


'''

    pos_fim_calc = texto.find(marcador_fim_calc, pos_calc)

    if pos_fim_calc < 0:
        print("Não encontrei marcador final da função calcular_prob_v53.")
        print("Mostrando trecho ao redor da linha 1754:")
        mostrar_linhas(texto, 1735, 1835)
        raise RuntimeError("Não foi possível corrigir automaticamente.")

    pos_fim_calc += len(marcador_fim_calc)

    cabecalho_montar = def_montar + "\n"
    prefixo = texto[:pos_montar]
    bloco_calc = texto[pos_calc:pos_fim_calc]
    resto_montar_corpo = texto[pos_fim_calc:]

    novo_texto = prefixo + bloco_calc + "\n" + cabecalho_montar + resto_montar_corpo.lstrip("\n")

    salvar_texto(ARQ, novo_texto)

    print("Indentação corrigida.")
    print("Testando compilação...")

    try:
        py_compile.compile(str(ARQ), doraise=True)
        print("OK: compilou sem erro.")
    except Exception as e:
        print("Ainda existe erro de compilação:")
        print(e)
        print("\nTrecho ao redor da linha 1754:")
        texto2 = ler_texto(ARQ)
        mostrar_linhas(texto2, 1735, 1810)
        raise

    print("\nArquivo corrigido:")
    print(ARQ)


if __name__ == "__main__":
    main()