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

ARQ_RANKING = SAIDA_DIR / "busca_3_horarios_fixos_multi_indicadores_2min_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "busca_3_horarios_fixos_multi_indicadores_2min_trades_top.csv"
ARQ_XLSX = SAIDA_DIR / "busca_3_horarios_fixos_multi_indicadores_2min.xlsx"

TAKE = 50.5
STOP = 117.0
HORARIOS_FIXOS = ["03:48", "10:30", "20:58"]
JANELAS = [365, 90, 30]


def rma(s, length):
    return s.ewm(alpha=1 / length, adjust=False).mean()


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
    dias_com_op = g["DataHora_SP"].dt.date.nunique()
    return {
        "trades": int(len(g)),
        "dias_com_operacao": int(dias_com_op),
        "winrate": float((p > 0).mean() * 100) if len(p) else 0.0,
        "pontos": float(p.sum()),
        "max_drawdown": max_drawdown(p),
        "profit_factor": profit_factor(p),
        "meses_negativos": int((mensal < 0).sum()) if len(mensal) else 0,
    }


def preparar_indicadores():
    df = resample_2min(base.carregar_dados()).reset_index(drop=True)
    df = base.adicionar_indicadores(df)

    for n in [5, 8, 13, 17, 21, 34, 55, 89, 144, 200]:
        df[f"ema{n}"] = df["close"].ewm(span=n, adjust=False).mean()
        df[f"sma{n}"] = df["close"].rolling(n, min_periods=n).mean()

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    rs = rma(gain, 14) / rma(loss, 14).replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))
    df["roc5"] = df["close"].diff(5)
    df["roc10"] = df["close"].diff(10)
    df["range10_media"] = (df["high"] - df["low"]).rolling(10, min_periods=10).mean()
    typical = (df["high"] + df["low"] + df["close"]) / 3
    data = df["DataHora_SP"].dt.date
    pv = typical * df["volume"].fillna(0)
    df["vwap_dia"] = pv.groupby(data).cumsum() / df["volume"].fillna(0).groupby(data).cumsum().replace(0, np.nan)
    mid = df["close"].rolling(20, min_periods=20).mean()
    std = df["close"].rolling(20, min_periods=20).std()
    df["bb_mid"] = mid
    df["bb_up"] = mid + 2 * std
    df["bb_dn"] = mid - 2 * std
    df["body"] = df["close"] - df["open"]
    df["prev_body"] = df["body"].shift(1)
    df["prev_roc5"] = df["roc5"].shift(1)

    df = precomputar_resultados(df)
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


def precomputar_resultados(df):
    df = df.copy()
    for direcao in ["BUY", "SELL"]:
        df[f"{direcao}_resultado"] = pd.Series([pd.NA] * len(df), dtype="object")
        df[f"{direcao}_pontos"] = np.nan
        df[f"{direcao}_saida"] = pd.Series([pd.NaT] * len(df), dtype="datetime64[ns]")
        df[f"{direcao}_preco_saida"] = np.nan
    idxs = df.index[df["hhmm"].isin(HORARIOS_FIXOS)].tolist()
    print("Precalculando BUY/SELL nos horarios fixos:", len(idxs), flush=True)
    for n, idx in enumerate(idxs, 1):
        if n % 500 == 0:
            print("  calculados:", n, "/", len(idxs), flush=True)
        for direcao in ["BUY", "SELL"]:
            sim = simular_saida(df, idx, direcao)
            if sim is None:
                continue
            resultado, pontos, saida, preco_saida = sim
            df.loc[idx, f"{direcao}_resultado"] = resultado
            df.loc[idx, f"{direcao}_pontos"] = float(pontos)
            df.loc[idx, f"{direcao}_saida"] = saida
            df.loc[idx, f"{direcao}_preco_saida"] = float(preco_saida)
    return df


def direcoes_base(c):
    pred = {}
    pred["ema17_34"] = np.where(c["ema17"] >= c["ema34"], 1, -1)
    pred["ema13_34"] = np.where(c["ema13"] >= c["ema34"], 1, -1)
    pred["ema21_55"] = np.where(c["ema21"] >= c["ema55"], 1, -1)
    pred["ema34_89"] = np.where(c["ema34"] >= c["ema89"], 1, -1)
    pred["sma17_34"] = np.where(c["sma17"] >= c["sma34"], 1, -1)
    pred["preco_ema34"] = np.where(c["close"] >= c["ema34"], 1, -1)
    pred["preco_ema200"] = np.where(c["close"] >= c["ema200"], 1, -1)
    pred["dmi"] = np.where(c["di_plus"] >= c["di_minus"], 1, -1)
    pred["macd"] = np.where(c["macd"] >= c["macd_signal"], 1, -1)
    pred["rsi50"] = np.where(c["rsi14"] >= 50, 1, -1)
    pred["rsi_contra"] = np.where(c["rsi14"] <= 45, 1, np.where(c["rsi14"] >= 55, -1, np.where(c["ema17"] >= c["ema34"], 1, -1)))
    pred["roc5"] = np.where(c["roc5"] >= 0, 1, -1)
    pred["roc10"] = np.where(c["roc10"] >= 0, 1, -1)
    pred["vwap"] = np.where(c["close"] >= c["vwap_dia"], 1, -1)
    pred["bb_tendencia"] = np.where(c["close"] >= c["bb_mid"], 1, -1)
    pred["bb_contra"] = np.where(c["close"] <= c["bb_mid"], 1, -1)
    pred["candle"] = np.where(c["body"] >= 0, 1, -1)
    pred["prev_candle"] = np.where(c["prev_body"] >= 0, 1, -1)
    pred["prev_roc5_contra"] = np.where(c["prev_roc5"] <= 0, 1, -1)
    pred["horario_bias"] = np.where(c["hhmm"].eq("20:58"), -1, np.where(c["hhmm"].eq("10:30"), 1, np.where(c["hhmm"].eq("03:48"), 1, -1)))
    return pd.DataFrame(pred, index=c.index).fillna(0).replace(0, 1).astype(int)


def trades_por_direcao(c, direcao_num, nome):
    linhas = []
    for idx, row in c.iterrows():
        direcao = "BUY" if int(direcao_num.loc[idx]) >= 0 else "SELL"
        resultado = row[f"{direcao}_resultado"]
        pontos = row[f"{direcao}_pontos"]
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
            "DataHora_saida": row[f"{direcao}_saida"],
            "preco_saida": float(row[f"{direcao}_preco_saida"]),
            "estrategia": nome,
        })
    return pd.DataFrame(linhas)


def avaliar(trades, fim):
    row = {}
    for dias in JANELAS:
        ini = fim - pd.Timedelta(days=dias)
        g = trades[trades["DataHora_SP"] >= ini]
        r = resumir(g) if not g.empty else {
            "trades": 0, "dias_com_operacao": 0, "winrate": 0.0, "pontos": 0.0,
            "max_drawdown": 0.0, "profit_factor": 0.0, "meses_negativos": 0,
        }
        for k, v in r.items():
            row[f"{k}_{dias}"] = v
    return row


def avaliar_direcao(c, direcao_num, fim):
    d = pd.Series(direcao_num, index=c.index).astype(int)
    pontos = np.where(d >= 0, c["BUY_pontos"].astype(float).values, c["SELL_pontos"].astype(float).values)
    g = c[["DataHora_SP", "mes"]].copy()
    g["pontos"] = pontos
    row = {}
    for dias in JANELAS:
        ini = fim - pd.Timedelta(days=dias)
        gg = g[g["DataHora_SP"] >= ini]
        r = resumir(gg) if not gg.empty else {
            "trades": 0, "dias_com_operacao": 0, "winrate": 0.0, "pontos": 0.0,
            "max_drawdown": 0.0, "profit_factor": 0.0, "meses_negativos": 0,
        }
        for k, v in r.items():
            row[f"{k}_{dias}"] = v
    return row


def score(row):
    if row["trades_365"] < 600:
        return -999999.0
    if row["pontos_365"] <= 0:
        return -999999.0
    return (
        80 * row["winrate_365"]
        + row["pontos_365"]
        + 2 * row["pontos_90"]
        + 3 * row["pontos_30"]
        - 0.25 * abs(row["max_drawdown_365"])
        + 60 * row["profit_factor_365"]
        - 20 * row["meses_negativos_365"]
    )


def main():
    print("=====================================================", flush=True)
    print("BUSCA 3 HORARIOS FIXOS MULTI-INDICADORES 2MIN", flush=True)
    print("Horarios: 03:48, 10:30, 20:58", flush=True)
    print("=====================================================", flush=True)
    df = preparar_indicadores()
    c = df[df["hhmm"].isin(HORARIOS_FIXOS)].copy()
    c = c.dropna(subset=["BUY_pontos", "SELL_pontos"])
    fim = c["DataHora_SP"].max()
    preds = direcoes_base(c)
    nomes = list(preds.columns)
    linhas = []
    top_trades = []

    print("Candles/sinais fixos avaliaveis:", len(c), c["DataHora_SP"].min(), fim, flush=True)
    print("Preditores base:", len(nomes), flush=True)

    candidatos = []
    for tamanho in [1, 2, 3]:
        candidatos.extend(itertools.combinations(nomes, tamanho))
    print("Combinacoes de indicadores:", len(candidatos), flush=True)

    for n, combo in enumerate(candidatos, 1):
        if n % 5000 == 0:
            print("  avaliadas:", n, "/", len(candidatos), flush=True)
        votos = preds[list(combo)].sum(axis=1)
        empate = preds[list(combo)[0]]
        direcao = pd.Series(np.where(votos > 0, 1, np.where(votos < 0, -1, empate)), index=c.index)
        nome = "+".join(combo)
        row = {"estrategia": nome, "indicadores": len(combo)}
        row.update(avaliar_direcao(c, direcao, fim))
        row["score"] = score(row)
        linhas.append(row)

    # Tambem testa combinacoes diferentes por horario.
    melhores_por_hora = []
    ranking_parcial = pd.DataFrame(linhas)
    for h in HORARIOS_FIXOS:
        c_h = c[c["hhmm"].eq(h)]
        preds_h = preds.loc[c_h.index]
        rows_h = []
        for combo in candidatos:
            votos = preds_h[list(combo)].sum(axis=1)
            empate = preds_h[list(combo)[0]]
            direcao = pd.Series(np.where(votos > 0, 1, np.where(votos < 0, -1, empate)), index=c_h.index)
            row = {"hhmm": h, "estrategia": "+".join(combo)}
            row.update(avaliar_direcao(c_h, direcao, fim))
            rows_h.append(row)
        rh = pd.DataFrame(rows_h)
        rh = rh[(rh["trades_365"] >= 150) & (rh["pontos_365"] > 0)].sort_values(
            ["winrate_365", "profit_factor_365", "pontos_365"], ascending=[False, False, False]
        )
        melhores_por_hora.append(rh.head(10))

    for a in melhores_por_hora[0]["estrategia"].head(5):
        for b in melhores_por_hora[1]["estrategia"].head(5):
            for d in melhores_por_hora[2]["estrategia"].head(5):
                dirs = pd.Series(index=c.index, dtype=int)
                for h, est in zip(HORARIOS_FIXOS, [a, b, d]):
                    combo = est.split("+")
                    idx_h = c.index[c["hhmm"].eq(h)]
                    votos = preds.loc[idx_h, combo].sum(axis=1)
                    empate = preds.loc[idx_h, combo[0]]
                    dirs.loc[idx_h] = np.where(votos > 0, 1, np.where(votos < 0, -1, empate))
                nome = f"03:48[{a}] | 10:30[{b}] | 20:58[{d}]"
                row = {"estrategia": nome, "indicadores": -1}
                row.update(avaliar_direcao(c, dirs, fim))
                row["score"] = score(row)
                linhas.append(row)

    ranking = pd.DataFrame(linhas).sort_values(
        ["winrate_365", "pontos_365", "profit_factor_365"],
        ascending=[False, False, False],
    )
    ranking_score = ranking.sort_values(["score", "winrate_365"], ascending=[False, False])

    for est in ranking_score.head(10)["estrategia"]:
        if " | " in est:
            dirs = pd.Series(index=c.index, dtype=int)
            partes = est.split(" | ")
            for parte in partes:
                h = parte[:5]
                combo = parte.split("[", 1)[1].rstrip("]").split("+")
                idx_h = c.index[c["hhmm"].eq(h)]
                votos = preds.loc[idx_h, combo].sum(axis=1)
                empate = preds.loc[idx_h, combo[0]]
                dirs.loc[idx_h] = np.where(votos > 0, 1, np.where(votos < 0, -1, empate))
        else:
            combo = est.split("+")
            votos = preds[combo].sum(axis=1)
            empate = preds[combo[0]]
            dirs = pd.Series(np.where(votos > 0, 1, np.where(votos < 0, -1, empate)), index=c.index)
        top_trades.append(trades_por_direcao(c, dirs, est))

    trades_top = pd.concat(top_trades, ignore_index=True) if top_trades else pd.DataFrame()
    ranking_score.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking_score.head(1000).to_excel(writer, sheet_name="ranking_top1000", index=False)
        pd.concat(melhores_por_hora).to_excel(writer, sheet_name="melhores_por_hora", index=False)
        trades_top.to_excel(writer, sheet_name="trades_top10", index=False)

    cols = [
        "estrategia", "indicadores", "score",
        "trades_365", "dias_com_operacao_365", "winrate_365", "pontos_365", "max_drawdown_365", "profit_factor_365", "meses_negativos_365",
        "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30",
    ]
    print("\nTop por score robusto:")
    print(ranking_score[cols].head(30).to_string(index=False))
    acima80 = ranking_score[(ranking_score["winrate_365"] >= 80) & (ranking_score["trades_365"] >= 600)]
    print("\nEstrategias >=80% anual com >=600 trades:", len(acima80))
    if len(acima80):
        print(acima80[cols].head(20).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_XLSX)
    print(ARQ_RANKING)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
