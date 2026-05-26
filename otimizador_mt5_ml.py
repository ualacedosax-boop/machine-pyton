import csv
import os
import random
import re
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sklearn.ensemble import RandomForestRegressor


# ============================================================
# CONFIGURAÇÃO DO USUÁRIO
# ============================================================
MT5_TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_DATA_DIR = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
# ajuste se usar /portable ou outra instalação

WORK_DIR = Path(r"C:\Users\Public\mt5_ml_opt")
WORK_DIR.mkdir(parents=True, exist_ok=True)

EA_NAME = "EA_MNQ_para_US100_Identica_Ao_Pine"
SYMBOL = "US100"
TIMEFRAME = "M2"
MODEL = 0  # 0 = every tick, ajuste conforme seu terminal
DATE_FROM = "2025.04.14"
DATE_TO = "2026.04.14"
DEPOSIT = 1000
CURRENCY = "USD"
LEVERAGE = 100
EXECUTION_DELAY = 0

N_TESTS = 100
SLEEP_AFTER_RUN = 2.0

RESULTS_CSV = WORK_DIR / "resultados_backtest.csv"
BEST_CSV = WORK_DIR / "melhores_parametros.csv"
IMPORTANCE_CSV = WORK_DIR / "importancias.csv"

# arquivo .set base: deixe vazio para usar só os parâmetros gerados
BASE_SET_FILE = None  # ex.: r"C:\...\MQL5\Profiles\Tester\base.set"


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
        Lote=random.choice([0.10, 0.25, 0.50, 1.00]),
        OffsetHorasTV_MT5=random.choice([-7, -6, -5]),
        OffsetPrecoMNQ_US100=round(random.uniform(145.0, 149.5), 2),
        TakePontos=random.choice([45.0, 47.5, 50.5, 52.5, 55.0]),
        MinStop=random.choice([70.0, 75.0, 80.0, 85.0, 90.0]),
        MaxStop=random.choice([105.0, 110.0, 117.0, 120.0, 125.0]),
        ATR_Mult=random.choice([5.0, 5.5, 6.0, 6.5, 7.0]),
        FatorVol=random.choice([0.45, 0.50, 0.55, 0.60, 0.65, 0.70]),
    )


# ============================================================
# CRIAÇÃO DOS ARQUIVOS DO TESTADOR
# ============================================================
def make_set_file(params: ParamSet, out_file: Path) -> None:
    lines = []

    # se tiver um .set base, carrega antes
    if BASE_SET_FILE:
        with open(BASE_SET_FILE, "r", encoding="utf-16", errors="ignore") as f:
            lines = f.read().splitlines()

        existing = {line.split("=")[0] for line in lines if "=" in line}

        for key, value in asdict(params).items():
            if key in existing:
                lines = [
                    f"{key}={value}" if line.startswith(f"{key}=") else line
                    for line in lines
                ]
            else:
                lines.append(f"{key}={value}")
    else:
        for key, value in asdict(params).items():
            lines.append(f"{key}={value}")

    out_file.write_text("\n".join(lines), encoding="utf-16")


def make_ini_file(set_file: Path, report_file: Path, ini_file: Path) -> None:
    content = f"""
[Tester]
Expert={EA_NAME}
ExpertParameters={set_file}
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
Report={report_file}
ReplaceReport=1
ShutdownTerminal=1
Visual=0
"""
    ini_file.write_text(content.strip(), encoding="utf-8")


# ============================================================
# RODAR MT5
# ============================================================
def run_backtest(ini_file: Path, timeout_sec: int = 1800) -> bool:
    cmd = [MT5_TERMINAL, f"/config:{ini_file}"]
    proc = subprocess.Popen(cmd)

    start = time.time()
    while proc.poll() is None:
        if time.time() - start > timeout_sec:
            proc.kill()
            return False
        time.sleep(1)

    time.sleep(SLEEP_AFTER_RUN)
    return proc.returncode == 0


# ============================================================
# PARSE DO RELATÓRIO HTML DO MT5
# ============================================================
def parse_number(text: str) -> Optional[float]:
    if text is None:
        return None
    text = str(text).strip()
    text = text.replace("\xa0", " ")
    text = text.replace(" ", "")
    text = text.replace(".", "").replace(",", ".")
    m = re.search(r"-?\d+(\.\d+)?", text)
    return float(m.group(0)) if m else None


def extract_metrics_from_html(report_file: Path) -> Dict[str, Optional[float]]:
    html = report_file.read_text(encoding="utf-16", errors="ignore")

    patterns = {
        "lucro_liquido": r"Lucro Líquido Total.*?>([-\d\.,]+)<",
        "lucro_bruto": r"Lucro Bruto.*?>([-\d\.,]+)<",
        "perda_bruta": r"Perda Bruta.*?>([-\d\.,]+)<",
        "fator_lucro": r"Fator de Lucro.*?>([-\d\.,]+)<",
        "retorno_esperado": r"Retorno Esperado \(Payoff\).*?>([-\d\.,]+)<",
        "drawdown_max_saldo_abs": r"Rebaixamento Máximo do Saldo.*?>([-\d\.,]+)",
        "drawdown_rel_saldo_pct": r"Rebaixamento Relativo do Saldo.*?>([-\d\.,]+)%",
        "drawdown_max_equity_abs": r"Rebaixamento Máximo do Capital Líquido.*?>([-\d\.,]+)",
        "drawdown_rel_equity_pct": r"Rebaixamento Relativo do Capital Líquido.*?>([-\d\.,]+)%",
        "total_trades": r"Total de Negociações.*?>([-\d\.,]+)<",
        "win_rate_pct": r"Negociações com Lucro \(% of total\).*?>([-\d\.,]+)%",
        "max_loss_trade": r"perda na Negociação.*?>([-\d\.,]+)<",
    }

    out = {}
    for key, pat in patterns.items():
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        out[key] = parse_number(m.group(1)) if m else None

    return out


# ============================================================
# SCORE
# ============================================================
def make_score(row: Dict[str, Optional[float]]) -> float:
    lucro = row.get("lucro_liquido") or -999999
    pf = row.get("fator_lucro") or 0
    dd = row.get("drawdown_rel_equity_pct") or 999
    trades = row.get("total_trades") or 0

    # score balanceado: lucro + PF - DD + penalização por poucos trades
    penalty_trades = 0
    if trades < 1000:
        penalty_trades = (1000 - trades) * 2

    score = lucro + (pf * 5000) - (dd * 300) - penalty_trades
    return score


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def append_result(csv_file: Path, row: Dict) -> None:
    exists = csv_file.exists()
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    print("Iniciando geração de backtests...")

    for i in range(N_TESTS):
        params = sample_params()

        run_dir = WORK_DIR / f"run_{i:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        set_file = run_dir / "params.set"
        ini_file = run_dir / "tester.ini"
        report_file = run_dir / "report.html"

        make_set_file(params, set_file)
        make_ini_file(set_file, report_file, ini_file)

        print(f"[{i+1}/{N_TESTS}] Rodando: {params}")
        ok = run_backtest(ini_file)

        result_row = asdict(params).copy()
        result_row["ok"] = ok
        result_row["report_file"] = str(report_file)

        if ok and report_file.exists():
            metrics = extract_metrics_from_html(report_file)
            result_row.update(metrics)
            result_row["score"] = make_score(result_row)
        else:
            result_row["score"] = -999999

        append_result(RESULTS_CSV, result_row)

    print("Backtests concluídos.")
    analyze_results()


# ============================================================
# ANÁLISE ML
# ============================================================
def analyze_results():
    df = pd.read_csv(RESULTS_CSV)

    df = df[df["score"] > -999999].copy()
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
        "importancia": model.feature_importances_
    }).sort_values("importancia", ascending=False)
    imp.to_csv(IMPORTANCE_CSV, index=False, encoding="utf-8")

    print("\nTop 10 resultados:")
    print(best[
        feature_cols
        + ["lucro_liquido", "fator_lucro", "drawdown_rel_equity_pct", "total_trades", "score"]
    ].head(10).to_string(index=False))

    print("\nImportância dos parâmetros:")
    print(imp.to_string(index=False))

    print(f"\nArquivos salvos em:\n- {RESULTS_CSV}\n- {BEST_CSV}\n- {IMPORTANCE_CSV}")


if __name__ == "__main__":
    main()