import csv
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

SOURCE_MQ5 = Path(
    r"C:\Users\ualac\AppData\Roaming\MetaQuotes\Terminal\75819A81C07603334EE22DE037C78F12\MQL5\Experts\2 min retorno media BB.mq5"
)

WORK_DIR = Path(r"C:\mt5_ml")
WORK_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_MQ5_DIR = WORK_DIR / "debug_rev07_2min_800_refino"
DEBUG_MQ5_DIR.mkdir(parents=True, exist_ok=True)

COMMON_FILES_DIR = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files"
COMMON_FILES_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "US100"
TIMEFRAME = "M2"
MODEL = 4  # Every tick based on real ticks

DATE_FROM = "2025.01.01"
DATE_TO = "2025.12.31"

DEPOSIT = 5000
CURRENCY = "USD"
LEVERAGE = 100
EXECUTION_DELAY = 0

COMPILE_TIMEOUT = 180
BACKTEST_TIMEOUT = 3000
SLEEP_AFTER_RUN = 3.0

# ============================================================
# TESTES
# ============================================================
TOTAL_TESTES = 800
PRIMEIRA_FASE_RANDOM = 220
ELITE_POOL = 80

RESULTS_CSV = WORK_DIR / "resultados_rev07_2min_800_refino.csv"
BEST_CSV = WORK_DIR / "melhores_rev07_2min_800_refino.csv"

EA_PREFIX = "EA_REV07_2M_REF"

# ============================================================
# BASE REFINADA
# ============================================================
BASE = {
    "Lote": 2.0,

    "BrokerToSP_Hours": 6,
    "Close_Hour_SP": 17,
    "Close_Minute_SP": 20,
    "Block_Hour_Start_SP": 17,
    "Block_Minute_Start_SP": 20,
    "Block_Hour_End_1_SP": 18,
    "Block_Hour_End_2_SP": 19,
    "Block_Minute_End_2_SP": 2,

    "BB_Period": 15,
    "BB_Desvio": 2.20,

    "Bias_Period": 30,
    "Bias_Compra_Nivel": -0.55,
    "Bias_Venda_Nivel": 0.55,

    "RSI_Period": 15,
    "StochRSI_Period": 14,
    "StochRSI_K_Period": 3,
    "StochRSI_D_Period": 3,
    "K_Max_Compra": 22.0,
    "K_Min_Venda": 84.0,

    "Lookback_ToqueBB": 2,
    "Lookback_Cruzamento": 2,
    "StopPontos": 90,

    "ModoValidacao": True,
    "LogSomenteSinais": True,

    "SalvarCSVBacktest": True,
    "NomeCSVBacktest": "rev07_2min_backtest.csv",
}

# ============================================================
# BOUNDS REFINADOS
# ============================================================
BOUNDS = {
    "BB_Period": (12, 18, "int"),
    "BB_Desvio": (1.20, 2.70, "float"),

    "Bias_Period": (20, 45, "int"),
    "Bias_Compra_Nivel": (-1.00, -0.25, "float"),
    "Bias_Venda_Nivel": (0.35, 0.80, "float"),

    "RSI_Period": (11, 18, "int"),
    "StochRSI_Period": (13, 21, "int"),
    "StochRSI_K_Period": (2, 6, "int"),
    "StochRSI_D_Period": (2, 5, "int"),

    "K_Max_Compra": (10.0, 32.0, "float"),
    "K_Min_Venda": (77.0, 90.0, "float"),

    "Lookback_ToqueBB": (2, 3, "int"),
    "Lookback_Cruzamento": (1, 2, "int"),

    "StopPontos": (70, 130, "int"),
}

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
# ESTRUTURA
# ============================================================
@dataclass(frozen=True)
class ParamSet:
    Lote: float

    BrokerToSP_Hours: int
    Close_Hour_SP: int
    Close_Minute_SP: int
    Block_Hour_Start_SP: int
    Block_Minute_Start_SP: int
    Block_Hour_End_1_SP: int
    Block_Hour_End_2_SP: int
    Block_Minute_End_2_SP: int

    BB_Period: int
    BB_Desvio: float

    Bias_Period: int
    Bias_Compra_Nivel: float
    Bias_Venda_Nivel: float

    RSI_Period: int
    StochRSI_Period: int
    StochRSI_K_Period: int
    StochRSI_D_Period: int
    K_Max_Compra: float
    K_Min_Venda: float

    Lookback_ToqueBB: int
    Lookback_Cruzamento: int
    StopPontos: int

    ModoValidacao: bool
    LogSomenteSinais: bool

    SalvarCSVBacktest: bool
    NomeCSVBacktest: str


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

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def append_result(csv_file: Path, row: Dict) -> None:
    exists = csv_file.exists()
    with open(csv_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()), delimiter=";")
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
        raise ValueError(f"Não encontrei o input '{var_name}' no MQ5. Inputs encontrados: {available}")

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


def read_strategy_report_metrics(csv_name: str, timeout_sec: int = 30) -> Dict[str, Optional[float]]:
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
                            out[k] = parse_number(row[k])
                    return out
            except Exception:
                pass
        time.sleep(1)

    return DEFAULT_METRICS.copy()


def trade_range_bonus(total_trades: float) -> float:
    if total_trades is None:
        return -2500.0

    if total_trades < 20:
        return -2500.0
    if 40 <= total_trades <= 120:
        center = 75.0
        dist = abs(total_trades - center)
        return max(0.0, 5200.0 - dist * 55.0)
    if 121 <= total_trades <= 220:
        return 1400.0
    if total_trades > 500:
        return -1500.0

    return 0.0


def make_score(row: Dict[str, Optional[float]]) -> float:
    profit = row.get("Profit") or -999999.0
    drawdown = row.get("Drawdown") or 999999.0
    pf = row.get("Profit_Factor") or 0.0
    payoff = row.get("Payoff") or 0.0
    winrate = row.get("WinRate") or 0.0
    total_trades = row.get("Total_Trades") or 0.0

    penalty_pf = 0.0
    if pf < 1.20:
        penalty_pf = (1.20 - pf) * 7500.0

    return (
        (profit * 5.8)
        - (drawdown * 6.0)
        + (pf * 3800.0)
        + (payoff * 650.0)
        + (winrate * 18.0)
        + trade_range_bonus(total_trades)
        - penalty_pf
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

    if kind == "int":
        span = max(1, int(round((hi - lo) * 0.42)))
        candidate = int(round(random.gauss(base, max(1, span / 2))))
        return normalize_param(name, candidate)

    span = (hi - lo) * 0.42
    candidate = random.gauss(base, max(0.0001, span / 2))
    return normalize_param(name, candidate)


def mutate_from_elite(name: str, elite_value):
    lo, hi, kind = BOUNDS[name]

    if kind == "int":
        sigma = max(1, int(round((hi - lo) * 0.18)))
        candidate = int(round(random.gauss(elite_value, sigma)))
        return normalize_param(name, candidate)

    sigma = (hi - lo) * 0.18
    candidate = random.gauss(elite_value, sigma)
    return normalize_param(name, candidate)


def build_paramset(csv_name: str, mode: str, elite_row: Optional[Dict] = None) -> ParamSet:
    params = {}

    for name, value in BASE.items():
        if name == "NomeCSVBacktest":
            params[name] = csv_name
        elif name == "Lote":
            params[name] = 2.0
        elif name in BOUNDS:
            if mode == "random":
                params[name] = random_param_around_base(name)
            else:
                params[name] = mutate_from_elite(name, elite_row[name])
        else:
            params[name] = value

    if params["Bias_Compra_Nivel"] >= -0.05:
        params["Bias_Compra_Nivel"] = -0.05

    if params["Bias_Venda_Nivel"] <= 0.05:
        params["Bias_Venda_Nivel"] = 0.05

    if params["K_Max_Compra"] >= params["K_Min_Venda"]:
        mid = (params["K_Max_Compra"] + params["K_Min_Venda"]) / 2.0
        params["K_Max_Compra"] = max(8.0, mid - 10.0)
        params["K_Min_Venda"] = min(99.0, mid + 10.0)

    return ParamSet(**params)


def choose_elite(df: pd.DataFrame) -> Dict:
    elite = df.sort_values(["score", "Profit"], ascending=False).head(ELITE_POOL)
    idx = random.randrange(len(elite))
    return elite.iloc[idx].to_dict()


# ============================================================
# PRINCIPAL
# ============================================================
def main():
    print("INICIANDO OTIMIZAÇÃO REV07 2 MIN | 800 TESTES REFINO | REAL TICKS | LOTE 2")
    print("SOURCE_MQ5 =", SOURCE_MQ5)
    print("COMMON_FILES_DIR =", COMMON_FILES_DIR)
    print("MODEL =", MODEL)

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
        run_dir = WORK_DIR / f"run_rev07_2min_800_refino_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        expert_name = f"{EA_PREFIX}_{i:04d}"
        mq5_target = EXPERTS_DIR / f"{expert_name}.mq5"
        ex5_target = EXPERTS_DIR / f"{expert_name}.ex5"
        ini_file = run_dir / "tester.ini"

        csv_name = f"bt_result_ref_{i:04d}.csv"
        csv_common_path = COMMON_FILES_DIR / csv_name
        if csv_common_path.exists():
            try:
                csv_common_path.unlink()
            except Exception:
                pass

        if i <= PRIMEIRA_FASE_RANDOM or len(resultados_validos) < 25:
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
        result_row["csv_name"] = csv_name
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
                    metrics = read_strategy_report_metrics(csv_name)
                    result_row.update(metrics)

        except Exception as e:
            print("ERRO:", e)

        result_row["score"] = make_score(result_row)
        append_result(RESULTS_CSV, result_row)

        if result_row.get("Profit") is not None and result_row.get("Drawdown") is not None:
            resultados_validos.append(result_row)

        if resultados_validos:
            df_now = pd.DataFrame(resultados_validos).sort_values(["score", "Profit"], ascending=False)
            df_now.to_csv(BEST_CSV, index=False, encoding="utf-8-sig", sep=";")

            best = df_now.iloc[0]
            print(
                f"MELHOR ATÉ AGORA | "
                f"Profit={best.get('Profit')} | "
                f"Drawdown={best.get('Drawdown')} | "
                f"PF={best.get('Profit_Factor')} | "
                f"Trades={best.get('Total_Trades')} | "
                f"Score={best.get('score')}"
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