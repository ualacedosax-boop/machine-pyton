from pathlib import Path
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"

ARQ_XLSX = PESQUISA_DIR / "backtest_0406_intraday_realista.xlsx"
ARQ_RANKING = PESQUISA_DIR / "backtest_0406_intraday_realista_ranking.csv"
ARQ_TRADES = PESQUISA_DIR / "backtest_0406_intraday_realista_trades.csv"

HORARIOS = ["04:00", "04:06", "04:12"]
SETUPS = [
    ("V71_505_117", 50.5, 117.0),
    ("V71_505_90", 50.5, 90.0),
    ("TS_139TICKS", 34.75, 34.75),
]
HORA_FECHAMENTO = "16:54"
ALVO_WINRATE = 85.34


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


def resumir(trades, nome, filtro, setup, hhmm):
    if trades.empty:
        return None
    pontos = trades["pontos"].astype(float)
    mensal = trades.groupby("mes")["pontos"].sum()
    anual = trades.groupby("ano")["pontos"].sum()
    wins = (pontos > 0).sum()
    row = {
        "nome": nome,
        "setup": setup,
        "hhmm": hhmm,
        "filtro": filtro,
        "trades": int(len(trades)),
        "wins": int(wins),
        "losses": int((pontos < 0).sum()),
        "zerados": int((pontos == 0).sum()),
        "winrate": float(wins / len(trades) * 100.0),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "fechamentos_dia": int((trades["resultado"] == "FECHA_DIA").sum()),
        "meses_total": int(len(mensal)),
        "meses_positivos": int((mensal > 0).sum()),
        "meses_negativos": int((mensal < 0).sum()),
        "pior_mes": float(mensal.min()) if len(mensal) else 0.0,
        "anos_positivos": int((anual > 0).sum()),
        "pior_ano": float(anual.min()) if len(anual) else 0.0,
    }
    row["score"] = (
        row["pontos"]
        + row["winrate"] * 20
        + min(row["profit_factor"], 5) * 250
        - abs(row["max_drawdown"]) * 1.8
        - row["meses_negativos"] * 250
        - row["fechamentos_dia"] * 5
    )
    return row


def carregar_candles_6min_dos_candidatos():
    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()

    keep = [
        "DataHora_SP", "Data", "hhmm", "ano", "open", "high", "low", "close", "volume",
        "range", "body", "body_abs", "rsi_14", "range_med_10", "vol_med_10", "dist_ema_20",
        "pos_range_20", "direcao_reversao_20", "direcao_tendencia", "direcao_candle",
    ]
    candles = df[keep].drop_duplicates(subset=["DataHora_SP"]).sort_values("DataHora_SP").reset_index(drop=True)
    candles["Data"] = pd.to_datetime(candles["DataHora_SP"]).dt.date
    candles["ano"] = candles["DataHora_SP"].dt.year
    candles["mes"] = candles["DataHora_SP"].dt.to_period("M").astype(str)
    candles["range_ratio_10"] = candles["range"] / candles["range_med_10"].replace(0, np.nan)
    candles["vol_ratio_10"] = candles["volume"] / candles["vol_med_10"].replace(0, np.nan)
    candles["body_range_pct"] = candles["body_abs"] / candles["range"].replace(0, np.nan)
    candles["dist_ema20_abs"] = candles["dist_ema_20"].abs()
    candles["extremo_reversao"] = np.where(
        candles["direcao_reversao_20"] == "BUY",
        1.0 - candles["pos_range_20"],
        np.where(candles["direcao_reversao_20"] == "SELL", candles["pos_range_20"], np.nan),
    )
    candles["mesmo_sentido_candle"] = candles["direcao_candle"] == candles["direcao_reversao_20"]
    candles = candles.replace([np.inf, -np.inf], np.nan)
    return candles


def simular_intraday(candles, idx, direcao, take, stop):
    row = candles.loc[idx]
    entrada = float(row["close"])
    data = row["Data"]
    futuro = candles[(candles.index > idx) & (candles["Data"] == data)].copy()
    futuro = futuro[futuro["hhmm"] <= HORA_FECHAMENTO].copy()

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
        pontos = float(ult["close"]) - entrada
        return "FECHA_DIA", pontos, ult["DataHora_SP"], float(ult["close"])

    if direcao == "SELL":
        preco_take = entrada - take
        preco_stop = entrada + stop
        for f in futuro.itertuples():
            if float(f.high) >= preco_stop:
                return "STOP", -stop, f.DataHora_SP, preco_stop
            if float(f.low) <= preco_take:
                return "TAKE", take, f.DataHora_SP, preco_take
        ult = futuro.iloc[-1]
        pontos = entrada - float(ult["close"])
        return "FECHA_DIA", pontos, ult["DataHora_SP"], float(ult["close"])

    return None


def gerar_trades_base(candles):
    linhas = []
    idxs = candles[
        candles["hhmm"].isin(HORARIOS)
        & candles["direcao_reversao_20"].isin(["BUY", "SELL"])
    ].index.tolist()

    for idx in idxs:
        row = candles.loc[idx]
        direcao = row["direcao_reversao_20"]
        for setup, take, stop in SETUPS:
            sim = simular_intraday(candles, idx, direcao, take, stop)
            if sim is None:
                continue
            resultado, pontos, saida, preco_saida = sim
            r = row.to_dict()
            r.update({
                "setup": setup,
                "Direcao": direcao,
                "take": take,
                "stop": stop,
                "preco_entrada": float(row["close"]),
                "resultado": resultado,
                "pontos": float(pontos),
                "DataHora_saida": saida,
                "preco_saida": preco_saida,
            })
            linhas.append(r)
    return pd.DataFrame(linhas)


def aplicar_condicoes(df, conds):
    mask = pd.Series(True, index=df.index)
    partes = []
    for col, op, valor in conds:
        if op == "==":
            mask &= df[col] == valor
        else:
            s = pd.to_numeric(df[col], errors="coerce")
            if op == ">=":
                mask &= s >= float(valor)
            elif op == "<=":
                mask &= s <= float(valor)
        partes.append(f"{col}{op}{valor}")
    return df[mask].copy(), " & ".join(partes) if partes else "sem_filtro"


def gerar_condicoes():
    atomos = [
        ("range_ratio_10", "<=", 1.5),
        ("range_ratio_10", "<=", 1.3),
        ("range_ratio_10", ">=", 0.7),
        ("extremo_reversao", ">=", 0.7),
        ("extremo_reversao", ">=", 0.75),
        ("extremo_reversao", ">=", 0.8),
        ("rsi_14", "<=", 40),
        ("rsi_14", "<=", 45),
        ("body_range_pct", ">=", 0.2),
        ("dist_ema20_abs", ">=", 5),
        ("mesmo_sentido_candle", "==", False),
    ]
    conds = [[]] + [[a] for a in atomos]
    for combo in itertools.combinations(atomos, 2):
        if len({combo[0][0], combo[1][0]}) == 2:
            conds.append(list(combo))
    for combo in itertools.combinations(atomos, 3):
        if len({combo[0][0], combo[1][0], combo[2][0]}) == 3:
            conds.append(list(combo))
    return conds


def avaliar(trades):
    linhas = []
    trades_top = []
    conds = gerar_condicoes()
    for hhmm in HORARIOS:
        for setup, _, _ in SETUPS:
            base = trades[(trades["hhmm"] == hhmm) & (trades["setup"] == setup)].copy()
            if len(base) < 20:
                continue
            for cond in conds:
                filtrado, filtro = aplicar_condicoes(base, cond)
                if len(filtrado) < 20:
                    continue
                row = resumir(filtrado, f"{setup}_{hhmm}_{filtro}", filtro, setup, hhmm)
                if row and row["pontos"] > 0:
                    linhas.append(row)
    ranking = pd.DataFrame(linhas).sort_values(["score", "pontos", "profit_factor"], ascending=[False, False, False])
    ranking = ranking.reset_index(drop=True)
    ranking["ranking"] = np.arange(1, len(ranking) + 1)

    for _, row in ranking.head(30).iterrows():
        base = trades[(trades["hhmm"] == row["hhmm"]) & (trades["setup"] == row["setup"])].copy()
        filtrado, _ = aplicar_condicoes(base, texto_para_condicoes(row["filtro"]))
        filtrado["ranking"] = int(row["ranking"])
        filtrado["nome_ranking"] = row["nome"]
        trades_top.append(filtrado)

    return ranking, pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()


def texto_para_condicoes(texto):
    if texto == "sem_filtro":
        return []
    conds = []
    for parte in texto.split(" & "):
        for op in ["==", ">=", "<="]:
            if op in parte:
                col, valor = parte.split(op)
                valor = valor.strip()
                if valor == "False":
                    valor = False
                elif valor == "True":
                    valor = True
                else:
                    valor = float(valor)
                conds.append((col.strip(), op, valor))
                break
    return conds


def main():
    print("=====================================================")
    print("BACKTEST 04:06 INTRADAY REALISTA")
    print("Conta FECHA_DIA quando nao bate take/stop.")
    print("=====================================================")
    candles = carregar_candles_6min_dos_candidatos()
    trades = gerar_trades_base(candles)
    ranking, trades_top = avaliar(trades)

    ranking.to_csv(ARQ_RANKING, index=False)
    trades.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        trades_top.to_excel(writer, sheet_name="trades_top30", index=False)
        trades.to_excel(writer, sheet_name="todos_trades", index=False)

    cols = [
        "ranking", "setup", "hhmm", "filtro", "trades", "winrate", "pontos",
        "max_drawdown", "profit_factor", "takes", "stops", "fechamentos_dia",
        "meses_negativos", "anos_positivos",
    ]
    print(ranking[cols].head(25).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
