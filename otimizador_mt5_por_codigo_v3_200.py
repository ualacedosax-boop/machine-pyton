import csv
import itertools
import re
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, List

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

print("RODANDO OTIMIZADOR REFINADO V3 - 200 TESTES")


# ============================================================
# CONFIGURAÇÃO
# ============================================================
MT5_TERMINAL = Path(r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe")
METAEDITOR = Path(r"C:\Program Files\Zero Financial MT5 Terminal\MetaEditor64.exe")

WORK_DIR = Path(r"C:\mt5_ml")
WORK_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_MQ5_DIR = WORK_DIR / "debug_mq5_v3_200"
DEBUG_MQ5_DIR.mkdir(parents=True, exist_ok=True)

TERMINAL_HASH_DIR = Path(
    r"C:\Users\ualac\AppData\Roaming\MetaQuotes\Terminal\75819A81C07603334EE22DE037C78F12"
)

EXPERTS_DIR = TERMINAL_HASH_DIR / "MQL5" / "Experts"
SOURCE_MQ5 = EXPERTS_DIR / "EA_MNQ_para_US100_Identica_Ao_Pine.mq5"

SYMBOL = "US100"
TIMEFRAME = "M2"
MODEL = 1

DATE_FROM = "2025.01.01"
DATE_TO = "2025.12.31"

DEPOSIT = 1000000
CURRENCY = "USD"
LEVERAGE = 100
EXECUTION_DELAY = 0

COMPILE_TIMEOUT = 180
BACKTEST_TIMEOUT = 1800
SLEEP_AFTER_RUN = 2.0

RESULTS_CSV = WORK_DIR / "resultados_backtest_codigo_refino_v3_200.csv"
BEST_CSV = WORK_DIR / "melhores_parametros_codigo_refino_v3_200.csv"
IMPORTANCE_CSV = WORK_DIR / "importancias_codigo_refino_v3_200.csv"

EA_PREFIX = "EA_AUTO_REFINO_V3_200"

TARGET_DD_ABS = 1600.0
ENABLE_EARLY_STOP = False


# ============================================================
# GRADE V3 - 200 TESTES
# CENTRADA NO 4.TXT, MAS COM LOTE FIXO = 2.0
# ============================================================
GRID = {
    "Lote": [2.0],
    "OffsetHorasTV_MT5": [-5],
    "OffsetPrecoMNQ_US100": [143.37, 144.37, 145.37, 146.37, 147.37],
    "TakePontos": [45.0, 47.5, 50.0, 52.5],
    "MinStop": [70.0, 75.0],
    "MaxStop": [115.0, 120.0],
    "ATR_Mult": [5.3, 5.5],
    "FatorVol": [0.48, 0.50, 0.52, 0.54, 0.56],
}


# ============================================================
# ESTRUTURA
# ============================================================
@dataclass(frozen=True)
class ParamSet:
    Lote: float
    OffsetHorasTV_MT5: int
    OffsetPrecoMNQ_US100: float
    TakePontos: float
    MinStop: float
    MaxStop: float
    ATR_Mult: float
    FatorVol: float


DEFAULT_METRICS = {
    "lucro_liquido": None,
    "lucro_bruto": None,
    "perda_bruta": None,
    "fator_lucro": None,
    "retorno_esperado": None,
    "drawdown_max_saldo_abs": None,
    "drawdown_rel_saldo_pct": None,
    "drawdown_max_equity_abs": None,
    "drawdown_rel_equity_pct": None,
    "total_trades": None,
    "win_rate_pct": None,
    "max_loss_trade": None,
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
    return str(value)


def parse_number(text) -> Optional[float]:
    if text is None:
        return None

    text = str(text).strip()
    if text == "":
        return None

    text = text.replace("\xa0", " ")
    text = text.replace("&nbsp;", " ")
    text = text.replace("%", "")
    text = re.sub(r"\s+", "", text)

    if "," in text:
        text = text.replace(".", "").replace(",", ".")

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
    encodings = ["utf-16", "utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc, errors="ignore")
        except Exception:
            pass
    return ""


def gerar_parametros():
    keys = list(GRID.keys())
    values = [GRID[k] for k in keys]
    for combo in itertools.product(*values):
        d = dict(zip(keys, combo))
        if d["MinStop"] > d["MaxStop"]:
            continue
        yield ParamSet(**d)


def make_score(row: Dict[str, Optional[float]]) -> float:
    lucro = row.get("lucro_liquido") or -999999.0
    pf = row.get("fator_lucro") or 0.0
    dd_pct = row.get("drawdown_rel_equity_pct") or 999.0
    dd_abs = row.get("drawdown_max_equity_abs") or 999999.0
    trades = row.get("total_trades") or 0.0

    penalty_trades = 0.0
    if trades < 1800:
        penalty_trades = (1800 - trades) * 2.5

    excess_dd = max(0.0, dd_abs - TARGET_DD_ABS)

    dd_bonus = 0.0
    if dd_abs <= TARGET_DD_ABS:
        dd_bonus = 12000.0
    elif dd_abs <= 1800:
        dd_bonus = 6000.0
    elif dd_abs <= 2200:
        dd_bonus = 2500.0
    elif dd_abs <= 2600:
        dd_bonus = 1000.0

    score = (
        lucro
        + (pf * 4000.0)
        - (dd_pct * 180.0)
        - (dd_abs * 2.0)
        - (excess_dd * 8.0)
        - penalty_trades
        + dd_bonus
    )
    return score


# ============================================================
# PATCH DO MQ5
# ============================================================
def replace_input_default(source_code: str, var_name: str, new_value) -> str:
    new_literal = value_to_mq5_literal(new_value)

    pattern = (
        rf"(^\s*input\s+"
        rf"(?:bool|int|double|float|long|string|ENUM_[A-Za-z0-9_]+)\s+"
        rf"{re.escape(var_name)}\s*=\s*)"
        rf"([^;]+)(\s*;)"
    )

    new_code, count = re.subn(
        pattern,
        rf"\g<1>{new_literal}\g<3>",
        source_code,
        flags=re.MULTILINE,
    )

    if count == 0:
        raise ValueError(f"Não encontrei o input '{var_name}' no código MQ5.")
    return new_code


def patch_mq5_source(original_code: str, params: ParamSet) -> str:
    code = original_code
    replacements = asdict(params)

    for k, v in replacements.items():
        code = replace_input_default(code, k, v)

    return code


# ============================================================
# COMPILAÇÃO
# ============================================================
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

    for _ in range(10):
        if log_file.exists():
            break
        time.sleep(0.3)

    compile_log = read_text_safe(log_file) if log_file.exists() else ""
    ex5_exists = ex5_file.exists()

    log_has_zero_errors = bool(re.search(r"Result:\s*0\s+errors?,\s*0\s+warnings?", compile_log, re.IGNORECASE))
    log_has_errors = bool(re.search(r"\b\d+\s+errors?\b", compile_log, re.IGNORECASE)) and not log_has_zero_errors

    if log_has_zero_errors:
        return True
    if ex5_exists and not log_has_errors:
        return True
    return False


# ============================================================
# TESTER.INI
# ============================================================
def make_ini_file(expert_name_no_ext: str, report_name: str, ini_file: Path) -> None:
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
Report={report_name}
ReplaceReport=1
ShutdownTerminal=1
Visual=0
"""
    ini_file.write_text(content.strip(), encoding="utf-8")


# ============================================================
# BACKTEST
# ============================================================
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
    return proc.returncode == 0


# ============================================================
# RELATÓRIO
# ============================================================
def find_report_file(report_name: str) -> Optional[Path]:
    search_dirs: List[Path] = [
        WORK_DIR,
        MT5_TERMINAL.parent,
        TERMINAL_HASH_DIR,
        TERMINAL_HASH_DIR / "tester",
    ]

    appdata_terminal = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
    if appdata_terminal.exists():
        search_dirs.append(appdata_terminal)
        for sub in appdata_terminal.iterdir():
            if sub.is_dir():
                search_dirs.append(sub)
                tester = sub / "tester"
                if tester.exists():
                    search_dirs.append(tester)

    for d in search_dirs:
        for suffix in ["", ".htm", ".html", ".xml"]:
            p = d / f"{report_name}{suffix}"
            if p.exists():
                return p
    return None


def extract_metrics_from_html(report_name: str) -> Dict[str, Optional[float]]:
    metrics = DEFAULT_METRICS.copy()

    report_file = find_report_file(report_name)
    if report_file is None:
        print("Nenhum relatório encontrado.")
        return metrics

    try:
        html = report_file.read_text(encoding="utf-16", errors="ignore")
    except Exception:
        html = report_file.read_text(encoding="utf-8", errors="ignore")

    def extract_simple(labels):
        for label in labels:
            pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                return parse_number(m.group(1))
        return None

    def extract_pair(labels):
        for label in labels:
            pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if not m:
                continue

            raw = m.group(1).strip()

            m2 = re.search(r"([-\d\., ]+)\s*\(([-\d\., ]+)%\)", raw)
            if m2:
                return parse_number(m2.group(1)), parse_number(m2.group(2))

            m3 = re.search(r"([-\d\., ]+)%\s*\(([-\d\., ]+)\)", raw)
            if m3:
                return parse_number(m3.group(2)), parse_number(m3.group(1))

            return parse_number(raw), None

        return None, None

    def extract_trade_rate(labels):
        for label in labels:
            pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if not m:
                continue

            raw = m.group(1).strip()
            m2 = re.search(r"([-\d\., ]+)\s*\(([-\d\., ]+)%\)", raw)
            if m2:
                return parse_number(m2.group(1)), parse_number(m2.group(2))
            return parse_number(raw), None

        return None, None

    metrics.update({
        "lucro_liquido": extract_simple(["Lucro Líquido Total:", "Total Net Profit:"]),
        "lucro_bruto": extract_simple(["Lucro Bruto:", "Gross Profit:"]),
        "perda_bruta": extract_simple(["Perda Bruta:", "Gross Loss:"]),
        "fator_lucro": extract_simple(["Fator de Lucro:", "Profit Factor:"]),
        "retorno_esperado": extract_simple(["Retorno Esperado (Payoff):", "Expected Payoff:"]),
        "total_trades": extract_simple(["Total de Negociações:", "Total Trades:"]),
        "max_loss_trade": extract_simple(["Maior perda na Negociação:", "Largest loss trade:"]),
    })

    metrics["drawdown_max_saldo_abs"], metrics["drawdown_rel_saldo_pct"] = extract_pair(
        ["Rebaixamento Máximo do Saldo :", "Balance Drawdown Maximal:"]
    )
    metrics["drawdown_max_equity_abs"], metrics["drawdown_rel_equity_pct"] = extract_pair(
        ["Rebaixamento Máximo do Capital Líquido:", "Equity Drawdown Maximal:"]
    )

    _, metrics["win_rate_pct"] = extract_trade_rate(
        ["Negociações com Lucro (% of total):", "Profit Trades (% of total):"]
    )

    return metrics


# ============================================================
# ANÁLISE
# ============================================================
def analyze_results():
    if not RESULTS_CSV.exists():
        print("Arquivo de resultados não encontrado.")
        return

    df = pd.read_csv(RESULTS_CSV)

    for col, default_val in DEFAULT_METRICS.items():
        if col not in df.columns:
            df[col] = default_val

    df = df[
        (df["ok_compile"] == True) &
        (df["ok_backtest"] == True) &
        (df["lucro_liquido"].notna())
    ].copy()

    if df.empty:
        print("Nenhum resultado válido para analisar.")
        return

    feature_cols = [
        "Lote",
        "OffsetHorasTV_MT5",
        "OffsetPrecoMNQ_US100",
        "TakePontos",
        "MinStop",
        "MaxStop",
        "ATR_Mult",
        "FatorVol",
    ]

    X = df[feature_cols]
    y = df["score"]

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    best = df.sort_values(["score", "lucro_liquido"], ascending=False).head(20)
    best.to_csv(BEST_CSV, index=False, encoding="utf-8")

    imp = pd.DataFrame({
        "parametro": feature_cols,
        "importancia": model.feature_importances_,
    }).sort_values("importancia", ascending=False)
    imp.to_csv(IMPORTANCE_CSV, index=False, encoding="utf-8")

    print("\nTop 10:")
    print(best[
        feature_cols + [
            "lucro_liquido",
            "fator_lucro",
            "drawdown_max_equity_abs",
            "drawdown_rel_equity_pct",
            "total_trades",
            "score",
        ]
    ].head(10).to_string(index=False))


# ============================================================
# PRINCIPAL
# ============================================================
def main():
    print("Iniciando refino V3 - 200 testes...")

    print("MT5_TERMINAL =", MT5_TERMINAL, "| existe?", MT5_TERMINAL.exists())
    print("METAEDITOR   =", METAEDITOR, "| existe?", METAEDITOR.exists())
    print("SOURCE_MQ5   =", SOURCE_MQ5, "| existe?", SOURCE_MQ5.exists())
    print("EXPERTS_DIR  =", EXPERTS_DIR, "| existe?", EXPERTS_DIR.exists())

    if not SOURCE_MQ5.exists():
        raise FileNotFoundError(f"Arquivo-fonte MQ5 não encontrado em: {SOURCE_MQ5}")

    original_code = SOURCE_MQ5.read_text(encoding="utf-8", errors="ignore")

    todos = list(gerar_parametros())
    total = len(todos)
    print("Total de combinações:", total)

    if total != 200:
        raise ValueError(f"A grade não fechou em 200 testes. Total atual: {total}")

    melhor_lucro = -999999.0
    melhor_dd = 999999.0

    for i, params in enumerate(todos, start=1):
        run_dir = WORK_DIR / f"run_refino_v3_200_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        expert_name = f"{EA_PREFIX}_{i:04d}"
        mq5_target = EXPERTS_DIR / f"{expert_name}.mq5"
        ex5_target = EXPERTS_DIR / f"{expert_name}.ex5"
        ini_file = run_dir / "tester.ini"
        report_name = f"report_refino_v3_200_{i:04d}"

        print(f"\n[{i}/{total}] PARAMS = {params}")

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
                make_ini_file(expert_name, report_name, ini_file)
                ok_backtest = run_backtest(ini_file)
                result_row["ok_backtest"] = ok_backtest

                if ok_backtest:
                    metrics = extract_metrics_from_html(report_name)
                    result_row.update(metrics)

        except Exception as e:
            print("ERRO:", e)

        result_row["score"] = make_score(result_row)
        append_result(RESULTS_CSV, result_row)

        lucro = result_row.get("lucro_liquido")
        dd = result_row.get("drawdown_max_equity_abs")

        if lucro is not None and lucro > melhor_lucro:
            melhor_lucro = lucro
        if dd is not None and dd < melhor_dd:
            melhor_dd = dd

        print("Melhor lucro até agora:", melhor_lucro)
        print("Melhor DD até agora:", melhor_dd)

    print("\nBacktests V3 concluídos.")
    analyze_results()


if __name__ == "__main__":
    main()