import itertools
import subprocess
import time
from pathlib import Path

# ============================================================
# CAMINHOS
# ============================================================
MT5_TERMINAL = Path(r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe")
METAEDITOR = Path(r"C:\Program Files\Zero Financial MT5 Terminal\MetaEditor64.exe")

PASTA_TRABALHO = Path.home() / "Documents" / "2025" / "Mercado" / "machine-pyton" / "mt5_batch_tests"
PASTA_SETS = PASTA_TRABALHO / "sets"
PASTA_INIS = PASTA_TRABALHO / "inis"
PASTA_RELATORIOS = PASTA_TRABALHO / "reports"

TERMINAL_HASH_DIR = Path(
    r"C:\Users\ualac\AppData\Roaming\MetaQuotes\Terminal\75819A81C07603334EE22DE037C78F12"
)
EXPERTS_DIR = TERMINAL_HASH_DIR / "MQL5" / "Experts"

# ============================================================
# CONFIG DO TESTE
# ============================================================
EA_NAME = "EA_MNQ_TV_para_US100_MT5_V4_Debug"
SIMBOLO = "US100"
TIMEFRAME = "M2"
DATA_INICIO = "2025.01.01"
DATA_FIM = "2025.12.31"
DEPOSITO = "1000000"
MOEDA = "USD"
MODEL = 0
LEVERAGE = "1:100"

# ============================================================
# PARÂMETROS BASE DO EA
# ============================================================
BASE_PARAMS = {
    "Lote": "2.0",
    "MagicNumber": "20260416",
    "DeviationPoints": "20",
    "OffsetHorasTV_MT5": "-6",
    "OffsetPrecoMNQ_US100": "148.10",
    "UsarPrecoAjustado": "true",
    "PeriodoEMA17": "17",
    "PeriodoEMA34": "34",
    "PeriodoBias": "23",
    "PeriodoRSI": "14",
    "PeriodoStochRSI": "14",
    "SmoothK": "3",
    "SmoothD": "3",
    "PeriodoATR": "14",
    "PeriodoStdRetorno": "10",
    "PeriodoEmaVol": "5",
    "FatorVol": "0.60",
    "ATR_Mult": "6.0",
    "MinStop": "80.0",
    "MaxStop": "117.0",
    "TakePontos": "50.5",
    "UsarFiltroHorario": "true",
    "HoraBloqIni": "17",
    "MinBloqIni": "40",
    "HoraBloqFim": "19",
    "MinBloqFim": "2",
    "FecharNoHorarioForcado": "true",
    "HoraFechamento": "17",
    "MinFechamento": "40",
    "UmaOperacaoPorCandle": "false",
    "BloquearReentradaMesmoCandle": "false",
    "ModoTVFiel": "true",
    "RecalcularStopNoTick": "false",
    "EntradaSomenteNovaBarra": "true",
    "UsarBarraFechadaParaEntrada": "true",
    "DebugLog": "false",
    "DebugCSV": "false",
    "DebugCSVNome": "EA_V4_Debug.csv",
}

# ============================================================
# GRADE DE TESTES
# ============================================================
GRID = {
    "OffsetHorasTV_MT5": [-7, -6, -5],
    "OffsetPrecoMNQ_US100": [120.0, 148.1, 170.0],
    "FatorVol": [0.55, 0.60, 0.65],
    "ATR_Mult": [5.5, 6.0, 6.5],
    "TakePontos": [45.0, 50.5, 55.0],
}

# ============================================================
# UTILITÁRIOS
# ============================================================
def garantir_pastas():
    for pasta in [PASTA_TRABALHO, PASTA_SETS, PASTA_INIS, PASTA_RELATORIOS]:
        pasta.mkdir(parents=True, exist_ok=True)

def valor_mt5(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)

def validar_caminhos():
    print("MT5_TERMINAL =", MT5_TERMINAL, "| existe?", MT5_TERMINAL.exists())
    print("METAEDITOR   =", METAEDITOR, "| existe?", METAEDITOR.exists())
    print("EXPERTS_DIR  =", EXPERTS_DIR, "| existe?", EXPERTS_DIR.exists())

    if not MT5_TERMINAL.exists():
        raise FileNotFoundError(f"MT5 não encontrado em: {MT5_TERMINAL}")

    if not METAEDITOR.exists():
        print("Aviso: MetaEditor não encontrado. Isso não impede o backtest se o EA já estiver compilado.")

    if not EXPERTS_DIR.exists():
        raise FileNotFoundError(f"Pasta Experts não encontrada em: {EXPERTS_DIR}")

def escrever_set_file(path_set: Path, params: dict):
    linhas = []
    for k, v in params.items():
        linhas.append(f"{k}={valor_mt5(v)}")
    path_set.write_text("\n".join(linhas), encoding="utf-16")

def escrever_ini_file(path_ini: Path, path_set: Path, report_name: str):
    conteudo = f"""[Tester]
Expert={EA_NAME}
ExpertParameters={path_set}
Symbol={SIMBOLO}
Period={TIMEFRAME}
Model={MODEL}
FromDate={DATA_INICIO}
ToDate={DATA_FIM}
ForwardMode=0
Deposit={DEPOSITO}
Currency={MOEDA}
Leverage={LEVERAGE}
Optimization=0
ShutdownTerminal=1
ReplaceReport=1
Report={PASTA_RELATORIOS / report_name}
Visual=0
"""
    path_ini.write_text(conteudo, encoding="utf-16")

def rodar_teste(path_ini: Path):
    cmd = [str(MT5_TERMINAL), "/config:" + str(path_ini)]
    print("Rodando:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def gerar_combinacoes(grid: dict):
    chaves = list(grid.keys())
    valores = [grid[k] for k in chaves]
    for combo in itertools.product(*valores):
        yield dict(zip(chaves, combo))

# ============================================================
# EXECUÇÃO
# ============================================================
def main():
    garantir_pastas()
    validar_caminhos()

    resumo_path = PASTA_TRABALHO / "resumo_testes.csv"
    linhas_resumo = []
    linhas_resumo.append("teste_id;set_file;ini_file;return_code;stdout;stderr")

    combinacoes = list(gerar_combinacoes(GRID))
    total = len(combinacoes)

    print("Pasta de trabalho:", PASTA_TRABALHO)
    print("Total de testes:", total)

    for i, combo in enumerate(combinacoes, start=1):
        params = BASE_PARAMS.copy()
        for k, v in combo.items():
            params[k] = valor_mt5(v)

        teste_id = f"teste_{i:04d}"
        set_file = PASTA_SETS / f"{teste_id}.set"
        ini_file = PASTA_INIS / f"{teste_id}.ini"
        report_name = f"{teste_id}"

        escrever_set_file(set_file, params)
        escrever_ini_file(ini_file, set_file, report_name)

        print(f"\n[{i}/{total}] {teste_id} -> {combo}")
        rc, out, err = rodar_teste(ini_file)

        out_limpo = (out or "").replace("\n", " ").replace(";", ",")[:500]
        err_limpo = (err or "").replace("\n", " ").replace(";", ",")[:500]

        linhas_resumo.append(
            f"{teste_id};{set_file};{ini_file};{rc};{out_limpo};{err_limpo}"
        )

        resumo_path.write_text("\n".join(linhas_resumo), encoding="utf-8")
        time.sleep(1)

    print("\nConcluído.")
    print("Resumo em:", resumo_path)

if __name__ == "__main__":
    main()