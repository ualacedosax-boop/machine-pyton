import csv
import random
import re
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, List

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

print("RODANDO OTIMIZADOR REFINADO POR CÓDIGO")


# ============================================================
# CONFIGURAÇÃO DO USUÁRIO
# ============================================================
MT5_TERMINAL = Path(r"C:\Program Files\Zero Financial MT5 Terminal\terminal64.exe")
METAEDITOR = Path(r"C:\Program Files\Zero Financial MT5 Terminal\MetaEditor64.exe")

WORK_DIR = Path(r"C:\mt5_ml")
WORK_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_MQ5_DIR = WORK_DIR / "debug_mq5"
DEBUG_MQ5_DIR.mkdir(parents=True, exist_ok=True)

TERMINAL_HASH_DIR = Path(
    r"C:\Users\ualac\AppData\Roaming\MetaQuotes\Terminal\75819A81C07603334EE22DE037C78F12"
)

EXPERTS_DIR = TERMINAL_HASH_DIR / "MQL5" / "Experts"
SOURCE_MQ5 = EXPERTS_DIR / "EA_MNQ_para_US100_Identica_Ao_Pine.mq5"

SYMBOL = "US100"
TIMEFRAME = "M2"

# 0 = Every tick
# 1 = OHLC 1 minute
MODEL = 1

DATE_FROM = "2025.04.14"
DATE_TO = "2026.04.16"

DEPOSIT = 1000
CURRENCY = "USD"
LEVERAGE = 100
EXECUTION_DELAY = 0

# ============================================================
# QUANTIDADE DE TESTES
# ============================================================
N_TESTS = 100
RANDOM_SEED = 42

SLEEP_AFTER_RUN = 2.0
COMPILE_TIMEOUT = 180
BACKTEST_TIMEOUT = 1800

RESULTS_CSV = WORK_DIR / "resultados_backtest_codigo_refino.csv"
BEST_CSV = WORK_DIR / "melhores_parametros_codigo_refino.csv"
IMPORTANCE_CSV = WORK_DIR / "importancias_codigo_refino.csv"

EA_PREFIX = "EA_AUTO_REFINO"

# alvo principal
TARGET_DD_ABS = 1600.0


# ============================================================
# FAIXAS REFINADAS
# ============================================================
# foco: reduzir DD mantendo lucro alto
REFINE_LOTE = [2.0]

REFINE_OFFSET_HORAS = [-6, -5]

REFINE_OFFSET_PRECO = [
    147.70, 147.80, 147.90, 148.00, 148.10
]

REFINE_TAKE = [45.0, 47.5, 50.5]
REFINE_MIN_STOP = [80.0, 85.0, 90.0]
REFINE_MAX_STOP = [105.0, 110.0, 117.0]
REFINE_ATR_MULT = [5.5, 5.8, 6.0]
REFINE_FATOR_VOL = [0.68, 0.70, 0.72, 0.75]


# ============================================================
# PARÂMETROS A OTIMIZAR
# ============================================================
@dataclass
class ParamSet:
    Lote: float
    OffsetHorasTV_MT5: int
    OffsetPrecoMNQ_US100: float
    TakePontos: float
    MinStop: float
    MaxStop: float
    ATR_Mult: float
    FatorVol: float


def sample_params() -> ParamSet:
    return ParamSet(
        Lote=random.choice(REFINE_LOTE),
        OffsetHorasTV_MT5=random.choice(REFINE_OFFSET_HORAS),
        OffsetPrecoMNQ_US100=random.choice(REFINE_OFFSET_PRECO),
        TakePontos=random.choice(REFINE_TAKE),
        MinStop=random.choice(REFINE_MIN_STOP),
        MaxStop=random.choice(REFINE_MAX_STOP),
        ATR_Mult=random.choice(REFINE_ATR_MULT),
        FatorVol=random.choice(REFINE_FATOR_VOL),
    )


# ============================================================
# MÉTRICAS
# ============================================================
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
    text = text.strip()
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


def make_score(row: Dict[str, Optional[float]]) -> float:
    lucro = row.get("lucro_liquido") or -999999.0
    pf = row.get("fator_lucro") or 0.0
    dd_pct = row.get("drawdown_rel_equity_pct") or 999.0
    dd_abs = row.get("drawdown_max_equity_abs") or 999999.0
    trades = row.get("total_trades") or 0.0

    penalty_trades = 0.0
    if trades < 1000:
        penalty_trades = (1000 - trades) * 2.0

    # penalização pesada acima do alvo
    excess_dd = max(0.0, dd_abs - TARGET_DD_ABS)

    # bônus forte se encostar no alvo
    dd_bonus = 0.0
    if dd_abs <= TARGET_DD_ABS:
        dd_bonus = 5000.0
    elif dd_abs <= 1800:
        dd_bonus = 2500.0
    elif dd_abs <= 2000:
        dd_bonus = 1000.0

    score = (
        lucro
        + (pf * 3000.0)
        - (dd_pct * 180.0)
        - (dd_abs * 1.5)
        - (excess_dd * 6.0)
        - penalty_trades
        + dd_bonus
    )
    return score


# ============================================================
# EDIÇÃO DO CÓDIGO MQ5
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

    replacements = {
        "Lote": params.Lote,
        "OffsetHorasTV_MT5": params.OffsetHorasTV_MT5,
        "OffsetPrecoMNQ_US100": params.OffsetPrecoMNQ_US100,
        "TakePontos": params.TakePontos,
        "MinStop": params.MinStop,
        "MaxStop": params.MaxStop,
        "ATR_Mult": params.ATR_Mult,
        "FatorVol": params.FatorVol,
    }

    for k, v in replacements.items():
        code = replace_input_default(code, k, v)

    return code


# ============================================================
# COMPILAÇÃO
# ============================================================
def compile_mq5(mq5_file: Path, timeout_sec: int = COMPILE_TIMEOUT) -> bool:
    if not METAEDITOR.exists():
        raise FileNotFoundError(f"MetaEditor não encontrado em: {METAEDITOR}")

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

    print("Return code compilação =", proc.returncode)

    for _ in range(10):
        if log_file.exists():
            break
        time.sleep(0.3)

    compile_log = ""
    if log_file.exists():
        compile_log = read_text_safe(log_file)
        print("\n===== LOG DE COMPILAÇÃO =====")
        print(compile_log[:12000])
        print("===== FIM DO LOG =====\n")
    else:
        print("Log de compilação não encontrado:", log_file)

    log_has_zero_errors = bool(re.search(r"Result:\s*0\s+errors?,\s*0\s+warnings?", compile_log, re.IGNORECASE))
    log_has_errors = bool(re.search(r"\b\d+\s+errors?\b", compile_log, re.IGNORECASE)) and not log_has_zero_errors

    for _ in range(15):
        if ex5_file.exists():
            break
        time.sleep(0.2)

    ex5_exists = ex5_file.exists()

    print("EX5 existe?", ex5_exists)
    print("Log indica 0 errors?", log_has_zero_errors)
    print("Log indica erros?", log_has_errors)

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
    if not MT5_TERMINAL.exists():
        raise FileNotFoundError(f"MT5 não encontrado em: {MT5_TERMINAL}")

    if not ini_file.exists():
        raise FileNotFoundError(f"INI não encontrado em: {ini_file}")

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
    print("Return code MT5 =", proc.returncode)
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
        try:
            for sub in appdata_terminal.iterdir():
                if sub.is_dir():
                    search_dirs.append(sub)
                    tester = sub / "tester"
                    if tester.exists():
                        search_dirs.append(tester)
        except Exception:
            pass

    candidates = []
    for d in search_dirs:
        for suffix in ["", ".htm", ".html", ".xml"]:
            candidates.append(d / f"{report_name}{suffix}")

    seen = set()
    unique_candidates = []
    for c in candidates:
        k = str(c).lower()
        if k not in seen:
            seen.add(k)
            unique_candidates.append(c)

    print("\nArquivos de relatório verificados:")
    for c in unique_candidates:
        print(" -", c, "=>", c.exists())

    for c in unique_candidates:
        if c.exists():
            return c

    return None


def extract_metrics_from_html(report_name: str) -> Dict[str, Optional[float]]:
    metrics = DEFAULT_METRICS.copy()

    report_file = find_report_file(report_name)
    if report_file is None:
        print("Nenhum relatório encontrado.")
        return metrics

    print("Relatório encontrado em:", report_file)

    try:
        html = report_file.read_text(encoding="utf-16", errors="ignore")
    except Exception:
        html = report_file.read_text(encoding="utf-8", errors="ignore")

    raw_dump = WORK_DIR / f"{report_name}_raw_dump.txt"
    raw_dump.write_text(html, encoding="utf-8", errors="ignore")

    def extract_simple(label: str):
        pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        return parse_number(m.group(1))

    def extract_pair(label: str):
        pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if not m:
            return (None, None)

        raw = m.group(1).strip()

        m2 = re.search(r"([-\d\., ]+)\s*\(([-\d\., ]+)%\)", raw)
        if m2:
            abs_val = parse_number(m2.group(1))
            pct_val = parse_number(m2.group(2))
            return (abs_val, pct_val)

        m3 = re.search(r"([-\d\., ]+)%\s*\(([-\d\., ]+)\)", raw)
        if m3:
            pct_val = parse_number(m3.group(1))
            abs_val = parse_number(m3.group(2))
            return (abs_val, pct_val)

        return (parse_number(raw), None)

    def extract_trade_rate(label: str):
        pattern = rf"{re.escape(label)}</td>\s*<td[^>]*><b>(.*?)</b>"
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if not m:
            return (None, None)

        raw = m.group(1).strip()
        m2 = re.search(r"([-\d\., ]+)\s*\(([-\d\., ]+)%\)", raw)
        if m2:
            qty = parse_number(m2.group(1))
            pct = parse_number(m2.group(2))
            return (qty, pct)

        return (parse_number(raw), None)

    lucro_liquido = extract_simple("Lucro Líquido Total:")
    lucro_bruto = extract_simple("Lucro Bruto:")
    perda_bruta = extract_simple("Perda Bruta:")
    fator_lucro = extract_simple("Fator de Lucro:")
    retorno_esperado = extract_simple("Retorno Esperado (Payoff):")
    total_trades = extract_simple("Total de Negociações:")
    max_loss_trade = extract_simple("Maior perda na Negociação:")

    dd_bal_max_abs, dd_bal_max_pct = extract_pair("Rebaixamento Máximo do Saldo :")
    dd_bal_rel_abs, dd_bal_rel_pct = extract_pair("Rebaixamento Relativo do Saldo :")
    dd_eq_max_abs, dd_eq_max_pct = extract_pair("Rebaixamento Máximo do Capital Líquido:")
    dd_eq_rel_abs, dd_eq_rel_pct = extract_pair("Rebaixamento Relativo do Capital Líquido:")

    _, win_rate_pct = extract_trade_rate("Negociações com Lucro (% of total):")

    metrics.update({
        "lucro_liquido": lucro_liquido,
        "lucro_bruto": lucro_bruto,
        "perda_bruta": perda_bruta,
        "fator_lucro": fator_lucro,
        "retorno_esperado": retorno_esperado,
        "drawdown_max_saldo_abs": dd_bal_max_abs,
        "drawdown_rel_saldo_pct": dd_bal_rel_pct,
        "drawdown_max_equity_abs": dd_eq_max_abs,
        "drawdown_rel_equity_pct": dd_eq_rel_pct,
        "total_trades": total_trades,
        "win_rate_pct": win_rate_pct,
        "max_loss_trade": max_loss_trade,
    })

    print("\nMétricas extraídas:", metrics)

    for label in [
        "Lote=",
        "OffsetHorasTV_MT5=",
        "OffsetPrecoMNQ_US100=",
        "FatorVol=",
        "ATR_Mult=",
        "MinStop=",
        "MaxStop=",
        "TakePontos=",
    ]:
        m = re.search(rf"{re.escape(label)}([^\s<]+)", html)
        if m:
            print(f"PARAM_RELATORIO {label}{m.group(1)}")

    return metrics


# ============================================================
# ANÁLISE ML
# ============================================================
def analyze_results():
    if not RESULTS_CSV.exists():
        print("Arquivo de resultados não encontrado.")
        return

    df = pd.read_csv(RESULTS_CSV)

    for col, default_val in DEFAULT_METRICS.items():
        if col not in df.columns:
            df[col] = default_val

    if "ok_compile" not in df.columns:
        df["ok_compile"] = False

    if "ok_backtest" not in df.columns:
        df["ok_backtest"] = False

    if "score" not in df.columns:
        df["score"] = -999999

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

    df["score_pred"] = model.predict(X)
    best = df.sort_values(["score", "lucro_liquido"], ascending=False).head(20)
    best.to_csv(BEST_CSV, index=False, encoding="utf-8")

    imp = pd.DataFrame({
        "parametro": feature_cols,
        "importancia": model.feature_importances_,
    }).sort_values("importancia", ascending=False)
    imp.to_csv(IMPORTANCE_CSV, index=False, encoding="utf-8")

    print("\nTop resultados:")
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

    print("\nImportância dos parâmetros:")
    print(imp.to_string(index=False))

    print(f"\nArquivos salvos em:\n- {RESULTS_CSV}\n- {BEST_CSV}\n- {IMPORTANCE_CSV}")


# ============================================================
# PRINCIPAL
# ============================================================
def main():
    print("Iniciando geração de backtests refinados por código...")
    random.seed(RANDOM_SEED)

    print("MT5_TERMINAL =", MT5_TERMINAL, "| existe?", MT5_TERMINAL.exists())
    print("METAEDITOR   =", METAEDITOR, "| existe?", METAEDITOR.exists())
    print("SOURCE_MQ5   =", SOURCE_MQ5, "| existe?", SOURCE_MQ5.exists())
    print("EXPERTS_DIR  =", EXPERTS_DIR, "| existe?", EXPERTS_DIR.exists())
    print("TARGET_DD_ABS =", TARGET_DD_ABS)

    if not SOURCE_MQ5.exists():
        raise FileNotFoundError(
            f"Arquivo-fonte MQ5 não encontrado em: {SOURCE_MQ5}"
        )

    if not EXPERTS_DIR.exists():
        raise FileNotFoundError(
            f"Pasta Experts não encontrada em: {EXPERTS_DIR}"
        )

    original_code = SOURCE_MQ5.read_text(encoding="utf-8", errors="ignore")

    for i in range(N_TESTS):
        params = sample_params()
        run_dir = WORK_DIR / f"run_refino_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        expert_name = f"{EA_PREFIX}_{i:04d}"
        mq5_target = EXPERTS_DIR / f"{expert_name}.mq5"
        ex5_target = EXPERTS_DIR / f"{expert_name}.ex5"
        ini_file = run_dir / "tester.ini"
        report_name = f"report_refino_{i:04d}"

        print(f"\n[{i + 1}/{N_TESTS}] PARAMS = {params}")

        result_row = asdict(params).copy()
        result_row["expert_name"] = expert_name
        result_row["ok_compile"] = False
        result_row["ok_backtest"] = False
        result_row.update(DEFAULT_METRICS)

        try:
            patched_code = patch_mq5_source(original_code, params)
            mq5_target.write_text(patched_code, encoding="utf-8")

            debug_copy = DEBUG_MQ5_DIR / f"{expert_name}.mq5"
            debug_copy.write_text(patched_code, encoding="utf-8")

            print("MQ5 GERADO =", mq5_target)
            print("MQ5 DEBUG  =", debug_copy)

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

    print("\nBacktests concluídos.")
    analyze_results()


if __name__ == "__main__":
    main()