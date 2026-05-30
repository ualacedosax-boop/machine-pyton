from pathlib import Path
import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"

ARQ_XLSX = PESQUISA_DIR / "teste_ema17_34_0406_realista.xlsx"
ARQ_RANKING = PESQUISA_DIR / "teste_ema17_34_0406_realista_ranking.csv"
ARQ_TRADES = PESQUISA_DIR / "teste_ema17_34_0406_realista_trades.csv"

HORARIOS = ["04:00", "04:06", "04:12"]
HORA_FECHAMENTO = "16:54"
SETUPS = [
    ("V71_505_117", 50.5, 117.0),
    ("V71_505_90", 50.5, 90.0),
    ("TS_139TICKS", 34.75, 34.75),
]


def max_drawdown(pontos):
    if len(pontos) == 0:
        return 0.0
    eq = np.cumsum(np.asarray(pontos, dtype=float))
    pico = np.maximum.accumulate(eq)
    return float((eq - pico).min())


def profit_factor(pontos):
    pontos = pd.Series(pontos, dtype=float)
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0
    return ganhos / perdas


def carregar_candles():
    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    keep = [
        "DataHora_SP", "Data", "hhmm", "open", "high", "low", "close", "volume",
        "range", "rsi_14", "range_med_10", "pos_range_20", "direcao_reversao_20",
    ]
    candles = df[keep].drop_duplicates(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)
    candles["Data"] = candles["DataHora_SP"].dt.date
    candles["ano"] = candles["DataHora_SP"].dt.year
    candles["mes"] = candles["DataHora_SP"].dt.to_period("M").astype(str)
    candles["ema17"] = candles["close"].ewm(span=17, adjust=False).mean()
    candles["ema34"] = candles["close"].ewm(span=34, adjust=False).mean()
    candles["direcao_ema17_34"] = np.where(candles["ema17"] > candles["ema34"], "BUY", "SELL")
    candles["range_ratio_10"] = candles["range"] / candles["range_med_10"].replace(0, np.nan)
    return candles.replace([np.inf, -np.inf], np.nan)


def simular(candles, idx, direcao, take, stop):
    row = candles.loc[idx]
    entrada = float(row["close"])
    data = row["Data"]
    futuro = candles[(candles.index > idx) & (candles["Data"] == data) & (candles["hhmm"] <= HORA_FECHAMENTO)].copy()
    if futuro.empty:
        return None

    if direcao == "BUY":
        preco_take = entrada + take
        preco_stop = entrada - stop
        for f in futuro.itertuples():
            if float(f.low) <= preco_stop:
                return "STOP", -stop, f.DataHora_SP, preco_stop
            if float(f.high) >= preco_take:
                return "TAKE", take, f.DataHora_SP, preco_take
        ult = futuro.iloc[-1]
        return "FECHA_DIA", float(ult["close"]) - entrada, ult["DataHora_SP"], float(ult["close"])

    preco_take = entrada - take
    preco_stop = entrada + stop
    for f in futuro.itertuples():
        if float(f.high) >= preco_stop:
            return "STOP", -stop, f.DataHora_SP, preco_stop
        if float(f.low) <= preco_take:
            return "TAKE", take, f.DataHora_SP, preco_take
    ult = futuro.iloc[-1]
    return "FECHA_DIA", entrada - float(ult["close"]), ult["DataHora_SP"], float(ult["close"])


def escolher_direcao(row, modo):
    rev = row["direcao_reversao_20"]
    ema = row["direcao_ema17_34"]

    if modo == "EMA_DIRECAO":
        return ema
    if modo == "REVERSAO_BASE":
        return rev if rev in ["BUY", "SELL"] else None
    if modo == "REVERSAO_CONFIRMADA_EMA":
        return rev if rev in ["BUY", "SELL"] and rev == ema else None
    if modo == "REVERSAO_CONTRA_EMA":
        return rev if rev in ["BUY", "SELL"] and rev != ema else None
    return None


def gerar_trades(candles):
    modos = ["EMA_DIRECAO", "REVERSAO_BASE", "REVERSAO_CONFIRMADA_EMA", "REVERSAO_CONTRA_EMA"]
    linhas = []
    idxs = candles[candles["hhmm"].isin(HORARIOS)].index.tolist()

    for idx in idxs:
        row = candles.loc[idx]
        for modo in modos:
            direcao = escolher_direcao(row, modo)
            if direcao is None:
                continue
            for setup, take, stop in SETUPS:
                sim = simular(candles, idx, direcao, take, stop)
                if sim is None:
                    continue
                resultado, pontos, dt_saida, preco_saida = sim
                r = row.to_dict()
                r.update({
                    "modo": modo,
                    "setup": setup,
                    "Direcao": direcao,
                    "take": take,
                    "stop": stop,
                    "preco_entrada": float(row["close"]),
                    "resultado": resultado,
                    "pontos": float(pontos),
                    "DataHora_saida": dt_saida,
                    "preco_saida": preco_saida,
                })
                linhas.append(r)
    return pd.DataFrame(linhas)


def resumir(g):
    pontos = g["pontos"].astype(float)
    mensal = g.groupby("mes")["pontos"].sum()
    anual = g.groupby("ano")["pontos"].sum()
    wins = int((pontos > 0).sum())
    return {
        "trades": int(len(g)),
        "wins": wins,
        "losses": int((pontos < 0).sum()),
        "winrate": float(wins / len(g) * 100.0),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "takes": int((g["resultado"] == "TAKE").sum()),
        "stops": int((g["resultado"] == "STOP").sum()),
        "fechamentos_dia": int((g["resultado"] == "FECHA_DIA").sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "anos_positivos": int((anual > 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
    }


def main():
    print("=====================================================")
    print("TESTE EMA17/34 - 04:06 REALISTA")
    print("=====================================================")
    candles = carregar_candles()
    trades = gerar_trades(candles)

    linhas = []
    for (modo, setup, hhmm), g in trades.groupby(["modo", "setup", "hhmm"]):
        row = resumir(g)
        row.update({"modo": modo, "setup": setup, "hhmm": hhmm})
        row["score"] = row["pontos"] + row["profit_factor"] * 250 - abs(row["max_drawdown"]) * 1.5 - row["meses_negativos"] * 200
        linhas.append(row)

    ranking = pd.DataFrame(linhas).sort_values(["score", "pontos", "profit_factor"], ascending=[False, False, False]).reset_index(drop=True)
    ranking["ranking"] = np.arange(1, len(ranking) + 1)

    ranking.to_csv(ARQ_RANKING, index=False)
    trades.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    cols = [
        "ranking", "modo", "setup", "hhmm", "trades", "winrate", "pontos",
        "max_drawdown", "profit_factor", "takes", "stops", "fechamentos_dia",
        "meses_negativos", "anos_positivos",
    ]
    print(ranking[cols].head(30).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
