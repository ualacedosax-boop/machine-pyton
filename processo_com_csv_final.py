import csv
import math
import random
import re
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# ============================================================
# CONFIGURAÇÃO
# ============================================================
MT5_TERMINAL = Path(r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe")
METAEDITOR = Path(r"C:\Program Files\Zero Financial MT5 Terminal\MetaEditor64.exe")

TERMINAL_HASH_DIR = Path(
    r"C:\Users\ualac\AppData\Roaming\MetaQuotes\Terminal\75819A81C07603334EE22DE037C78F12"
)
EXPERTS_DIR = TERMINAL_HASH_DIR / "MQL5" / "Experts"

# AJUSTE AQUI O NOME EXATO DO SEU EA
SOURCE_MQ5 = EXPERTS_DIR / "Atr Vari retorno media REv04-colab-rev02.mq5"

WORK_DIR = Path(r"C:\mt5_ml")
WORK_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_MQ5_DIR = WORK_DIR / "debug_mq5_500"
DEBUG_MQ5_DIR.mkdir(parents=True, exist_ok=True)

COMMON_FILES_DIR = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files"
COMMON_FILES_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "US100"
TIMEFRAME = "M2"
MODEL = 1

DATE_FROM = "2025.01.01"
DATE_TO = "2025.12.31"

DEPOSIT = 1000
CURRENCY = "USD"
LEVERAGE = 100
EXECUTION_DELAY = 0

COMPILE_TIMEOUT = 180
BACKTEST_TIMEOUT = 1800
SLEEP_AFTER_RUN = 3.0

TOTAL_TESTES = 2500
PRIMEIRA_FASE_RANDOM = 180
ELITE_POOL = 40

RESULTS_CSV = WORK_DIR / "resultados_500_backtests.csv"
BEST_CSV = WORK_DIR / "melhores_500_backtests.csv"

EA_PREFIX = "EA_OPT500"

# ============================================================
# PARÂMETROS BASE
# Baseados no que você mostrou no print
# ============================================================
BASE = {
    "EMA_Period_17": 17,
    "EMA_Period_34": 34,
    "Bias_Period": 23,
    "Volatility_StdDev_Period": 10,
    "FatorVol": 0.6,
    "VolEMA_Period": 5,
    "RSI_Period": 14,
    "StochRSI_Period": 14,
    "StochRSI_K_Period": 3,
    "StochRSI_D_Period": 3,
    "ATR_Period": 14,
    "ATR_Mult": 6.0,
    "MinStop": 80.0,
    "MaxStop": 117.0,
    "TakePontos": 50.5,
    "Lote": 3.0,
    "OffsetHorasTV_MT5": 0,
    "OffsetPrecoMNQ_US100": 0.0,
    "Close_Hour_SP": 17,
    "Close_Minute_SP": 40,
    "Block_Hour_Start_SP": 17,
    "Block_Minute_Start_SP": 40,
    "Block_Hour_End_1_SP": 18,
    "Block_Hour_End_2_SP": 19,
    "Block_Minute_End_2_SP": 2,
    "BrokerToSP_Hours": 6,
    "SalvarCSVBacktest": True,
    "NomeCSVBacktest": "backtest_resultados.csv",
}

# ============================================================
# LIMITES DE BUSCA AO REDOR DA BASE
# ============================================================
BOUNDS = {
    "EMA_Period_17": (12, 25, "int"),
    "EMA_Period_34": (26, 55, "int"),
    "Bias_Period": (15, 35, "int"),
    "Volatility_StdDev_Period": (5, 20, "int"),
    "FatorVol": (0.30, 1.20, "float"),
    "VolEMA_Period": (2, 12, "int"),
    "RSI_Period": (7, 21, "int"),
    "StochRSI_Period": (7, 21, "int"),
    "StochRSI_K_Period": (2, 7, "int"),
    "StochRSI_D_Period": (2, 7, "int"),
    "ATR_Period": (7, 21, "int"),
    "ATR_Mult": (3.0, 10.0, "float"),
    "MinStop": (40.0, 140.0, "float"),
    "MaxStop": (80.0, 220.0, "float"),
    "TakePontos": (20.0, 120.0, "float"),
    # fixos
    "Lote": (3.0, 3.0, "float"),
    "OffsetHorasTV_MT5": (0, 0, "int"),
    "OffsetPrecoMNQ_US100": (0.0, 0.0, "float"),
    "Close_Hour_SP": (17, 17, "int"),
    "Close_Minute_SP": (40, 40, "int"),
    "Block_Hour_Start_SP": (17, 17, "int"),
    "Block_Minute_Start_SP": (40, 40, "int"),
    "Block_Hour_End_1_SP": (18, 18, "int"),
    "Block_Hour_End_2_SP": (19, 19, "int"),
    "Block_Minute_End_2_SP": (2, 2, "int"),
    "BrokerToSP_Hours": (6, 6, "int"),
}

# ============================================================
# ESTRUTURA
# ============================================================
@dataclass(frozen=True)
class ParamSet:
    EMA_Period_17: int
    EMA_Period_34: int
    Bias_Period: int
    Volatility_StdDev_Period: int
    FatorVol: float
    VolEMA_Period: int
    RSI_Period: int
    StochRSI_Period: int
    StochRSI_K_Period: int
    StochRSI_D_Period: int
    ATR_Period: int
    ATR_Mult: float
    MinStop: float
    MaxStop: float
    TakePontos: float
    Lote: float
    OffsetHorasTV_MT5: int
    OffsetPrecoMNQ_US100: float
    Close_Hour_SP: int
    Close_Minute_SP: int
    Block_Hour_Start_SP: int
    Block_Minute_Start_SP: int
    Block_Hour_End_1_SP: int
    Block_Hour_End_2_SP: int
    Block_Minute_End_2_SP: int
    BrokerToSP_Hours: int
    SalvarCSVBacktest: bool
    NomeCSVBacktest: str


DEFAULT_METRICS = {
    "Profit": None,
    "Gross_Profit": None,
    "Gross_Loss": None,
    "Profit_Factor": None,
    "Payoff": None,
    "Drawdown": None,
    "Balance_Drawdown_Maximal": None,
    "Balance_Drawdown_Relative_Pct": None,
    "Equity_Drawdown_Maximal": None,
    "Equity_Drawdown_Relative_Pct": None,
    "Total_Trades": None,
    "Profit_Trades_Count": None,
    "Loss_Trades_Count": None,
    "WinRate": None,
    "Short_Trades_Count": None,
    "Long_Trades_Count": None,
    "Recovery_Factor": None,
    "Sharpe_Ratio": None,
}

# ============================================================
# UTILIDADES
# ============================================================
def value_to_mq5_literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        txt = f"{value:.8f}".rstrip("0").rstrip(".")
        if txt == "-0":
            txt = "0"
        return txt
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def parse_number(text) -> Optional[float]:
    if text is None:
        return None

    text = str(text).strip()
    if text == "":
        return None

    text = text.replace("\xa0", " ")
    text = text.replace("%", "")
    text = re.sub(r"\s+", "", text)

    # tenta formato BR
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def append_result(csv_file: Path, row: Dict) -> None:
    exists = csv_file.exists()
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def read_text_safe(path: Path) -> str:
    encodings = ["utf-16", "utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except Exception:
            pass
    return ""


def list_inputs_from_code(source_code: str) -> List[str]:
    pattern = re.compile(
        r"^\s*input\s+(?:bool|int|double|float|long|string|ENUM_[A-Za-z0-9_]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
        re.MULTILINE,
    )
    return pattern.findall(source_code)


def replace_input_default(source_code: str, var_name: str, new_value) -> str:
    new_literal = value_to_mq5_literal(new_value)

    pattern = re.compile(
        rf"(^\s*input\s+(?:bool|int|double|float|long|string|ENUM_[A-Za-z0-9_]+)\s+{re.escape(var_name)}\s*=\s*)([^;]+)(\s*;)",
        flags=re.MULTILINE,
    )

    def repl(match):
        return match.group(1) + new_literal + match.group(3)

    new_code, count = pattern.subn(repl, source_code, count=1)

    if count == 0:
        available = list_inputs_from_code(source_code)
        raise ValueError(
            f"Não encontrei o input '{var_name}' no MQ5. Inputs encontrados: {available}"
        )

    return new_code


def patch_mq5_source(original_code: str, params: ParamSet) -> str:
    code = original_code
    replacements = asdict(params)

    for k, v in replacements.items():
        code = replace_input_default(code, k, v)

    return code


def compile_mq5(mq5_file: Path, timeout_sec: int = COMPILE_TIMEOUT) -> bool:
    log_file = mq5_file.with_suffix(".compile.log")
    ex5_file = mq5_file.with_suffix(".ex5")

    if log_file.exists():
        try:
            log_file.unlink()
        except Exception:
            pass

    if ex5_file.exists():
        try:
            ex5_file.unlink()
        except Exception:
            pass

    cmd = [str(METAEDITOR), "/compile:" + str(mq5_file), "/log:" + str(log_file)]
    print("CMD COMPILAR =", cmd)

    proc = subprocess.Popen(cmd)
    start = time.time()

    while proc.poll() is None:
        if time.time() - start > timeout_sec:
            proc.kill()
            print("Tempo limite excedido na compilação.")
            return False
        time.sleep(1)

    compile_log = read_text_safe(log_file) if log_file.exists() else ""
    ex5_exists = ex5_file.exists()

    ok_zero_errors = bool(re.search(r"Result:\s*0\s+errors?,\s*0\s+warnings?", compile_log, re.IGNORECASE))
    if ok_zero_errors:
        return True

    if ex5_exists and "error" not in compile_log.lower():
        return True

    return False


def make_ini_file(expert_name_no_ext: str, ini_file: Path) -> None:
    content = f"""
[Tester]
Expert={expert_name_no_ext}
Symbol={SYMBOL}
Period={TIMEFRAME}
Model={MODEL}
FromDate={DATE_FROM}
ToDate={DATE_TO}
Deposit={DEPOSIT}
Currency={CURRENCY}
Leverage={LEVERAGE}
ExecutionMode={EXECUTION_DELAY}
Optimization=0
ForwardMode=0
ShutdownTerminal=1
Visual=0
"""
    ini_file.write_text(content.strip(), encoding="utf-8")


def run_backtest(ini_file: Path, timeout_sec: int = BACKTEST_TIMEOUT) -> bool:
    cmd = [str(MT5_TERMINAL), f"/config:{ini_file}"]
    print("CMD BACKTEST =", cmd)

    proc = subprocess.Popen(cmd)
    start = time.time()

    while proc.poll() is None:
        if time.time() - start > timeout_sec:
            proc.kill()
            print("Tempo limite excedido no backtest.")
            return False
        time.sleep(1)

    time.sleep(SLEEP_AFTER_RUN)
    return True


def read_ea_csv_result(csv_name: str, timeout_sec: int = 20) -> Dict[str, Optional[float]]:
    csv_path = COMMON_FILES_DIR / csv_name
    start = time.time()

    while time.time() - start < timeout_sec:
        if csv_path.exists() and csv_path.stat().st_size > 0:
            try:
                df = pd.read_csv(csv_path, sep=";")
                if not df.empty:
                    row = df.iloc[-1].to_dict()
                    out = DEFAULT_METRICS.copy()
                    for k in out.keys():
                        if k in row:
                            out[k] = parse_number(row[k]) if k != "WinRate" else parse_number(row[k])
                    return out
            except Exception:
                pass
        time.sleep(1)

    return DEFAULT_METRICS.copy()


def make_score(row: Dict[str, Optional[float]]) -> float:
    profit = row.get("Profit") or -999999.0
    drawdown = row.get("Drawdown") or 999999.0
    pf = row.get("Profit_Factor") or 0.0
    payoff = row.get("Payoff") or 0.0
    winrate = row.get("WinRate") or 0.0

    # favorece lucro alto e drawdown baixo
    return (
        (profit * 4.0)
        - (drawdown * 8.0)
        + (pf * 3000.0)
        + (payoff * 1500.0)
        + (winrate * 60.0)
    )


def normalize_param(name: str, value):
    lo, hi, kind = BOUNDS[name]
    if kind == "int":
        value = int(round(value))
        value = max(int(lo), min(int(hi), value))
    else:
        value = float(value)
        value = max(float(lo), min(float(hi), value))
    return value


def random_param_around_base(name: str):
    base = BASE[name]
    lo, hi, kind = BOUNDS[name]

    if lo == hi:
        return lo

    if kind == "int":
        span = max(1, int(round((hi - lo) * 0.20)))
        candidate = int(round(random.gauss(base, span / 2)))
        return normalize_param(name, candidate)

    span = (hi - lo) * 0.20
    candidate = random.gauss(base, span / 2)
    return normalize_param(name, candidate)


def mutate_from_elite(name: str, elite_value):
    lo, hi, kind = BOUNDS[name]

    if lo == hi:
        return lo

    if kind == "int":
        sigma = max(1, int(round((hi - lo) * 0.08)))
        candidate = int(round(random.gauss(elite_value, sigma)))
        return normalize_param(name, candidate)

    sigma = (hi - lo) * 0.08
    candidate = random.gauss(elite_value, sigma)
    return normalize_param(name, candidate)


def build_paramset(csv_name: str, mode: str, elite_row: Optional[Dict] = None) -> ParamSet:
    params = {}

    for name in BASE.keys():
        if name == "SalvarCSVBacktest":
            params[name] = True
        elif name == "NomeCSVBacktest":
            params[name] = csv_name
        elif name not in BOUNDS:
            params[name] = BASE[name]
        else:
            if mode == "random":
                params[name] = random_param_around_base(name)
            else:
                elite_value = elite_row[name]
                params[name] = mutate_from_elite(name, elite_value)

    # regras de consistência
    if params["EMA_Period_34"] <= params["EMA_Period_17"]:
        params["EMA_Period_34"] = normalize_param("EMA_Period_34", params["EMA_Period_17"] + 5)

    if params["MaxStop"] < params["MinStop"]:
        params["MaxStop"] = params["MinStop"] + 10.0
        params["MaxStop"] = normalize_param("MaxStop", params["MaxStop"])

    params["Lote"] = 3.0

    return ParamSet(**params)


def choose_elite(df: pd.DataFrame) -> Dict:
    elite = df.sort_values(["score", "Profit"], ascending=False).head(ELITE_POOL)
    idx = random.randrange(len(elite))
    return elite.iloc[idx].to_dict()


# ============================================================
# PRINCIPAL
# ============================================================
def main():
    print("INICIANDO OTIMIZAÇÃO DE 500 BACKTESTS")
    print("SOURCE_MQ5 =", SOURCE_MQ5)
    print("COMMON_FILES_DIR =", COMMON_FILES_DIR)

    if not MT5_TERMINAL.exists():
        raise FileNotFoundError(f"MT5 não encontrado: {MT5_TERMINAL}")
    if not METAEDITOR.exists():
        raise FileNotFoundError(f"MetaEditor não encontrado: {METAEDITOR}")
    if not SOURCE_MQ5.exists():
        raise FileNotFoundError(f"EA não encontrado: {SOURCE_MQ5}")

    original_code = read_text_safe(SOURCE_MQ5)
    if not original_code.strip():
        raise ValueError("Não foi possível ler o MQ5.")

    print("Inputs detectados:", list_inputs_from_code(original_code))

    if RESULTS_CSV.exists():
        RESULTS_CSV.unlink()
    if BEST_CSV.exists():
        BEST_CSV.unlink()

    resultados_validos = []

    for i in range(1, TOTAL_TESTES + 1):
        run_dir = WORK_DIR / f"run_opt500_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        expert_name = f"{EA_PREFIX}_{i:04d}"
        mq5_target = EXPERTS_DIR / f"{expert_name}.mq5"
        ex5_target = EXPERTS_DIR / f"{expert_name}.ex5"
        ini_file = run_dir / "tester.ini"

        csv_name = f"bt_result_{i:04d}.csv"
        csv_common_path = COMMON_FILES_DIR / csv_name
        if csv_common_path.exists():
            try:
                csv_common_path.unlink()
            except Exception:
                pass

        if i <= PRIMEIRA_FASE_RANDOM or len(resultados_validos) < 20:
            mode = "random"
            elite_row = None
        else:
            mode = "elite"
            elite_row = choose_elite(pd.DataFrame(resultados_validos))

        params = build_paramset(csv_name, mode, elite_row)

        print(f"\n[{i}/{TOTAL_TESTES}] modo={mode}")
        print(params)

        result_row = asdict(params).copy()
        result_row["expert_name"] = expert_name
        result_row["ok_compile"] = False
        result_row["ok_backtest"] = False
        result_row.update(DEFAULT_METRICS)

        try:
            patched_code = patch_mq5_source(original_code, params)
            mq5_target.write_text(patched_code, encoding="utf-8")
            (DEBUG_MQ5_DIR / f"{expert_name}.mq5").write_text(patched_code, encoding="utf-8")

            ok_compile = compile_mq5(mq5_target)
            result_row["ok_compile"] = ok_compile

            if ok_compile and ex5_target.exists():
                make_ini_file(expert_name, ini_file)
                ok_backtest = run_backtest(ini_file)
                result_row["ok_backtest"] = ok_backtest

                if ok_backtest:
                    metrics = read_ea_csv_result(csv_name)
                    result_row.update(metrics)

        except Exception as e:
            print("ERRO:", e)

        result_row["score"] = make_score(result_row)
        append_result(RESULTS_CSV, result_row)

        if result_row.get("Profit") is not None and result_row.get("Drawdown") is not None:
            resultados_validos.append(result_row)

        if resultados_validos:
            df_now = pd.DataFrame(resultados_validos).sort_values(["score", "Profit"], ascending=False)
            df_now.to_csv(BEST_CSV, index=False, encoding="utf-8")

            best = df_now.iloc[0]
            print(
                f"MELHOR ATÉ AGORA | Profit={best.get('Profit')} | Drawdown={best.get('Drawdown')} | Score={best.get('score')}"
            )
        else:
            print("Ainda sem resultados válidos.")

    print("\nFINALIZADO.")
    if RESULTS_CSV.exists():
        print("CSV geral:", RESULTS_CSV)
    if BEST_CSV.exists():
        print("CSV melhores:", BEST_CSV)


if __name__ == "__main__":
    main()