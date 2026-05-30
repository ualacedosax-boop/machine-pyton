from pathlib import Path
import itertools
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testar_ema17_34_adx_horarios_3min as base
from testar_ema17_34_adx_horarios_2min import resample_2min

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_RANKING = SAIDA_DIR / "otimizacao_ema_adx_2min_robusto_ranking.csv"
ARQ_TRADES_TOP = SAIDA_DIR / "otimizacao_ema_adx_2min_robusto_trades_top.csv"
ARQ_XLSX = SAIDA_DIR / "otimizacao_ema_adx_2min_robusto.xlsx"

TAKE = 50.5
STOP = 117.0
HORARIOS_BASE = ["03:46", "03:48", "03:50", "10:26", "10:28", "20:52", "20:54", "20:56"]
JANELAS_DIAS = [365, 90, 30]


def max_drawdown(pontos):
    eq = np.cumsum(np.asarray(pontos, dtype=float))
    if len(eq) == 0:
        return 0.0
    return float((eq - np.maximum.accumulate(eq)).min())


def profit_factor(pontos):
    p = pd.Series(pontos, dtype=float)
    ganhos = float(p[p > 0].sum())
    perdas = abs(float(p[p < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def resumir(g):
    p = g["pontos"].astype(float)
    mensal = g.groupby("mes")["pontos"].sum()
    return {
        "trades": int(len(g)),
        "winrate": float((p > 0).mean() * 100) if len(p) else 0.0,
        "pontos": float(p.sum()),
        "max_drawdown": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "meses_negativos": int((mensal < 0).sum()) if len(mensal) else 0,
    }


def preparar_base():
    df = resample_2min(base.carregar_dados())
    df = base.adicionar_indicadores(df)
    for fast in [13, 15, 17, 19, 21]:
        df[f"ema_fast_{fast}"] = df["close"].ewm(span=fast, adjust=False).mean()
    for slow in [26, 30, 34, 38, 42]:
        df[f"ema_slow_{slow}"] = df["close"].ewm(span=slow, adjust=False).mean()
    df = df.reset_index(drop=True)
    df = precomputar_saidas(df)
    return df


def simular_saida(df, idx, direcao):
    row = df.loc[idx]
    entrada = float(row["close"])
    futuro = df[df.index > idx]
    if futuro.empty:
        return None
    if direcao == "BUY":
        take = entrada + TAKE
        stop = entrada - STOP
        for f in futuro.itertuples():
            if float(f.low) <= stop:
                return "STOP", -STOP, f.DataHora_SP, stop
            if float(f.high) >= take:
                return "TAKE", TAKE, f.DataHora_SP, take
    else:
        take = entrada - TAKE
        stop = entrada + STOP
        for f in futuro.itertuples():
            if float(f.high) >= stop:
                return "STOP", -STOP, f.DataHora_SP, stop
            if float(f.low) <= take:
                return "TAKE", TAKE, f.DataHora_SP, take
    return None


def precomputar_saidas(df):
    df = df.copy()
    for direcao in ["BUY", "SELL"]:
        df[f"{direcao}_resultado"] = pd.Series([pd.NA] * len(df), dtype="object")
        df[f"{direcao}_pontos"] = np.nan
        df[f"{direcao}_DataHora_saida"] = pd.Series([pd.NaT] * len(df), dtype="datetime64[ns]")
        df[f"{direcao}_preco_saida"] = np.nan
    candidatos = df.index[df["hhmm"].isin(HORARIOS_BASE)].tolist()
    print("Precalculando saidas dos candles candidatos:", len(candidatos))
    for n, idx in enumerate(candidatos, 1):
        if n % 500 == 0:
            print("  saidas calculadas:", n, "/", len(candidatos))
        for direcao in ["BUY", "SELL"]:
            sim = simular_saida(df, idx, direcao)
            if sim is None:
                continue
            resultado, pontos, saida, preco_saida = sim
            df.loc[idx, f"{direcao}_resultado"] = resultado
            df.loc[idx, f"{direcao}_pontos"] = float(pontos)
            df.loc[idx, f"{direcao}_DataHora_saida"] = saida
            df.loc[idx, f"{direcao}_preco_saida"] = float(preco_saida)
    return df


def gerar_trades(df, fast, slow, adx_min, dmi_gap_min, horarios):
    linhas = []
    candidatos = df[df["hhmm"].isin(horarios)].copy()
    ef = candidatos[f"ema_fast_{fast}"]
    es = candidatos[f"ema_slow_{slow}"]
    dmi_gap = (candidatos["di_plus"] - candidatos["di_minus"]).abs()
    compra = (ef > es) & (candidatos["adx"] >= adx_min) & (candidatos["di_plus"] > candidatos["di_minus"]) & (dmi_gap >= dmi_gap_min)
    venda = (ef < es) & (candidatos["adx"] >= adx_min) & (candidatos["di_minus"] > candidatos["di_plus"]) & (dmi_gap >= dmi_gap_min)
    sinais = candidatos[compra | venda]
    for idx, row in sinais.iterrows():
        direcao = "BUY" if compra.loc[idx] else "SELL"
        resultado = row.get(f"{direcao}_resultado")
        pontos = row.get(f"{direcao}_pontos")
        saida = row.get(f"{direcao}_DataHora_saida")
        preco_saida = row.get(f"{direcao}_preco_saida")
        if pd.isna(resultado) or pd.isna(pontos):
            continue
        linhas.append({
            "DataHora_SP": row["DataHora_SP"],
            "mes": row["mes"],
            "hhmm": row["hhmm"],
            "direcao": direcao,
            "preco_entrada": float(row["close"]),
            "resultado": resultado,
            "pontos": float(pontos),
            "DataHora_saida": saida,
            "preco_saida": float(preco_saida),
            "ema_fast": fast,
            "ema_slow": slow,
            "adx_min": adx_min,
            "dmi_gap_min": dmi_gap_min,
            "horarios": "+".join(horarios),
        })
    return pd.DataFrame(linhas)


def combos_horarios():
    grupos = [
        ["03:48"],
        ["20:54"],
        ["03:48", "20:54"],
        ["03:46", "20:54"],
        ["03:50", "20:54"],
        ["03:48", "20:52"],
        ["03:48", "20:56"],
        ["03:48", "10:26", "20:54"],
        ["03:48", "10:28", "20:54"],
        ["10:26", "20:54"],
        ["10:28", "20:54"],
    ]
    return grupos


def score_linha(row):
    if row["trades_365"] < 70:
        return -999999.0
    if row["pontos_365"] <= 0 or row["pontos_90"] <= 0 or row["pontos_30"] <= 0:
        return -999999.0
    return (
        row["pontos_365"]
        + 2.0 * row["pontos_90"]
        + 3.0 * row["pontos_30"]
        + 20.0 * row["profit_factor_365"]
        - 0.35 * abs(row["max_drawdown_365"])
        - 15.0 * row["meses_negativos_365"]
    )


def main():
    print("=====================================================")
    print("OTIMIZACAO EMA/ADX 2MIN - PESQUISA, NAO OFICIAL")
    print("=====================================================")
    df = preparar_base()
    fim = df["DataHora_SP"].max()
    linhas = []
    trades_top = []

    total = 0
    for fast, slow in itertools.product([13, 15, 17, 19, 21], [26, 30, 34, 38, 42]):
        if fast >= slow:
            continue
        for adx_min in [20, 22, 25, 28, 30]:
            for dmi_gap_min in [0, 2, 4, 6, 8]:
                for horarios in combos_horarios():
                    total += 1
                    trades = gerar_trades(df, fast, slow, adx_min, dmi_gap_min, horarios)
                    if trades.empty:
                        continue
                    row = {
                        "ema_fast": fast,
                        "ema_slow": slow,
                        "adx_min": adx_min,
                        "dmi_gap_min": dmi_gap_min,
                        "horarios": "+".join(horarios),
                    }
                    for dias in JANELAS_DIAS:
                        ini = fim - pd.Timedelta(days=dias)
                        g = trades[trades["DataHora_SP"] >= ini]
                        r = resumir(g) if not g.empty else {
                            "trades": 0, "winrate": 0.0, "pontos": 0.0,
                            "max_drawdown": 0.0, "profit_factor": 0.0, "meses_negativos": 0,
                        }
                        for k, v in r.items():
                            row[f"{k}_{dias}"] = v
                    linhas.append(row)

    ranking = pd.DataFrame(linhas)
    ranking["score_robusto"] = ranking.apply(score_linha, axis=1)
    ranking = ranking.sort_values(
        ["score_robusto", "pontos_365", "profit_factor_365", "winrate_365"],
        ascending=[False, False, False, False],
    )

    for row in ranking.head(10).itertuples(index=False):
        horarios = str(row.horarios).split("+")
        trades = gerar_trades(df, int(row.ema_fast), int(row.ema_slow), float(row.adx_min), float(row.dmi_gap_min), horarios)
        trades_top.append(trades)
    trades_top = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()

    ranking.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES_TOP, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.head(500).to_excel(writer, sheet_name="ranking_top500", index=False)
        trades_top.to_excel(writer, sheet_name="trades_top10", index=False)

    print("Total de combinacoes avaliadas:", total)
    cols = [
        "ema_fast", "ema_slow", "adx_min", "dmi_gap_min", "horarios", "score_robusto",
        "trades_365", "winrate_365", "pontos_365", "max_drawdown_365", "profit_factor_365", "meses_negativos_365",
        "trades_90", "winrate_90", "pontos_90", "max_drawdown_90", "profit_factor_90",
        "trades_30", "winrate_30", "pontos_30", "max_drawdown_30", "profit_factor_30",
    ]
    print(ranking[cols].head(25).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES_TOP)


if __name__ == "__main__":
    main()
