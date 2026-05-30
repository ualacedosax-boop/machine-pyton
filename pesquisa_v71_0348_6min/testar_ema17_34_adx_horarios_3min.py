from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_XLSX = SAIDA_DIR / "teste_ema17_34_adx_horarios_3min.xlsx"
ARQ_RANKING = SAIDA_DIR / "teste_ema17_34_adx_horarios_3min_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "teste_ema17_34_adx_horarios_3min_trades.csv"
ARQ_JANELAS = SAIDA_DIR / "teste_ema17_34_adx_horarios_3min_janelas.csv"

TAKE = 50.5
STOP = 117.0
HORARIOS = ["03:48", "10:27", "20:54"]
FECHAMENTO_DIA = "16:54"


def normalizar_ohlcv(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "DataHora_SP" in df.columns:
        dt = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    elif "date" in df.columns:
        dt = pd.to_datetime(df["date"], errors="coerce", utc=True)
        dt = dt.dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    else:
        raise RuntimeError("Coluna de data/hora nao encontrada.")
    df["DataHora_SP"] = dt
    df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP")
    for c in ["open", "high", "low", "close", "volume"]:
        if c not in df.columns:
            df[c] = 0.0 if c == "volume" else np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"])[["DataHora_SP", "open", "high", "low", "close", "volume"]]


def carregar_dados():
    arquivos = [
        BASE_DIR / "dados_mnq_2024_ibkr" / "MNQ_2024_2MIN_IBKR_CONTINUO.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQH5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQM5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQU5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQZ5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2026_ibkr" / "MNQ_2026_2MIN_IBKR_CONTINUO.csv",
    ]
    partes = []
    usados = []
    for arq in arquivos:
        if arq.exists():
            partes.append(normalizar_ohlcv(pd.read_csv(arq, low_memory=False)))
            usados.append(str(arq))
    if not partes:
        raise FileNotFoundError("Nao encontrei dados MNQ.")
    df = pd.concat(partes, ignore_index=True).drop_duplicates(subset=["DataHora_SP"]).sort_values("DataHora_SP")
    print("Arquivos usados:")
    for u in usados:
        print(" -", u)
    print("Candles base:", len(df), df["DataHora_SP"].min(), df["DataHora_SP"].max())
    return df


def resample_3min(df):
    out = df.set_index("DataHora_SP").resample("3min", origin="start_day", label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"]).reset_index()
    out["Data"] = out["DataHora_SP"].dt.date
    out["ano"] = out["DataHora_SP"].dt.year
    out["mes"] = out["DataHora_SP"].dt.to_period("M").astype(str)
    out["hhmm"] = out["DataHora_SP"].dt.strftime("%H:%M")
    return out


def rma(s, length):
    return s.ewm(alpha=1 / length, adjust=False).mean()


def adicionar_indicadores(df):
    out = df.copy()
    out["ema17"] = out["close"].ewm(span=17, adjust=False).mean()
    out["ema34"] = out["close"].ewm(span=34, adjust=False).mean()

    up = out["high"].diff()
    down = -out["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    prev_close = out["close"].shift(1)
    tr = pd.concat([
        out["high"] - out["low"],
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = rma(tr, 14)
    out["di_plus"] = 100 * rma(pd.Series(plus_dm, index=out.index), 14) / atr.replace(0, np.nan)
    out["di_minus"] = 100 * rma(pd.Series(minus_dm, index=out.index), 14) / atr.replace(0, np.nan)
    dx = 100 * (out["di_plus"] - out["di_minus"]).abs() / (out["di_plus"] + out["di_minus"]).replace(0, np.nan)
    out["adx"] = rma(dx, 9)
    return out.replace([np.inf, -np.inf], np.nan)


def simular(df, idx, direcao, fechamento_dia=False):
    row = df.loc[idx]
    entrada = float(row["close"])
    data = row["Data"]
    futuro = df[(df.index > idx) & (df["Data"] == data)].copy() if fechamento_dia else df[df.index > idx].copy()
    if fechamento_dia:
        futuro = futuro[futuro["hhmm"] <= FECHAMENTO_DIA]
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
        ult = futuro.iloc[-1]
        return "FECHA_DIA", float(ult["close"]) - entrada, ult["DataHora_SP"], float(ult["close"])
    take = entrada - TAKE
    stop = entrada + STOP
    for f in futuro.itertuples():
        if float(f.high) >= stop:
            return "STOP", -STOP, f.DataHora_SP, stop
        if float(f.low) <= take:
            return "TAKE", TAKE, f.DataHora_SP, take
    ult = futuro.iloc[-1]
    return "FECHA_DIA", entrada - float(ult["close"]), ult["DataHora_SP"], float(ult["close"])


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
        "wins": int((p > 0).sum()),
        "losses": int((p < 0).sum()),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "max_drawdown": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "takes": int((g["resultado"] == "TAKE").sum()),
        "stops": int((g["resultado"] == "STOP").sum()),
        "fechamentos_dia": int((g["resultado"] == "FECHA_DIA").sum()),
        "meses_negativos": int((mensal < 0).sum()),
    }


def gerar_resumo_janelas(trades):
    linhas = []
    fim = trades["DataHora_SP"].max()
    horarios = sorted(trades["hhmm"].dropna().unique())
    for modo, base in trades.groupby("modo_fechamento"):
        for dias in [365, 90, 30]:
            inicio = fim - pd.Timedelta(days=dias)
            for tamanho in range(1, len(horarios) + 1):
                for combo in __import__("itertools").combinations(horarios, tamanho):
                    g = base[(base["DataHora_SP"] >= inicio) & (base["hhmm"].isin(combo))]
                    if g.empty:
                        continue
                    row = resumir(g)
                    row.update({
                        "modo_fechamento": modo,
                        "janela_dias": dias,
                        "periodo_inicio": inicio,
                        "periodo_fim": fim,
                        "horarios": "+".join(combo),
                    })
                    linhas.append(row)
    return pd.DataFrame(linhas).sort_values(
        ["janela_dias", "pontos", "profit_factor"],
        ascending=[True, False, False],
    )


def gerar_trades(df):
    linhas = []
    for fechamento_dia in [False, True]:
        for idx, row in df[df["hhmm"].isin(HORARIOS)].iterrows():
            compra = row["ema17"] > row["ema34"] and row["adx"] > 25 and row["di_plus"] > row["di_minus"]
            venda = row["ema17"] < row["ema34"] and row["adx"] > 25 and row["di_minus"] > row["di_plus"]
            direcao = "BUY" if compra else "SELL" if venda else None
            if direcao is None:
                continue
            sim = simular(df, idx, direcao, fechamento_dia=fechamento_dia)
            if sim is None:
                continue
            resultado, pontos, saida, preco_saida = sim
            r = row.to_dict()
            r.update({
                "modo_fechamento": "FECHA_DIA" if fechamento_dia else "TV_OVERNIGHT",
                "Direcao": direcao,
                "preco_entrada": float(row["close"]),
                "resultado": resultado,
                "pontos": float(pontos),
                "DataHora_saida": saida,
                "preco_saida": preco_saida,
            })
            linhas.append(r)
    return pd.DataFrame(linhas)


def main():
    print("=====================================================")
    print("EMA17/34 + ADX/DMI - HORARIOS 03:48 10:27 20:54")
    print("=====================================================")
    df = adicionar_indicadores(resample_3min(carregar_dados()))
    trades = gerar_trades(df)

    linhas = []
    for (modo, hhmm), g in trades.groupby(["modo_fechamento", "hhmm"]):
        row = resumir(g)
        row.update({"modo_fechamento": modo, "hhmm": hhmm})
        linhas.append(row)
    for modo, g in trades.groupby("modo_fechamento"):
        row = resumir(g)
        row.update({"modo_fechamento": modo, "hhmm": "TODOS"})
        linhas.append(row)
    ranking = pd.DataFrame(linhas).sort_values(["pontos", "profit_factor"], ascending=[False, False])

    ranking.to_csv(ARQ_RANKING, index=False)
    trades.to_csv(ARQ_TRADES, index=False)
    janelas = gerar_resumo_janelas(trades)
    janelas.to_csv(ARQ_JANELAS, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        janelas.to_excel(writer, sheet_name="janelas_365_90_30", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    print(ranking.to_string(index=False))
    print("\nMelhores combinacoes por janela:")
    for (modo, dias), g in janelas.groupby(["modo_fechamento", "janela_dias"]):
        print(f"\n{modo} - {dias} dias")
        print(g.head(5).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)
    print(ARQ_JANELAS)


if __name__ == "__main__":
    main()
