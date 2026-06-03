from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from buscar_regime_3h_candles_ibkr import carregar_candles, indicadores
from simular_compilado_vencedoras import max_drawdown, profit_factor, simular_trade


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "busca_rewrite_tvsafe_rapido_ranking.csv"
ARQ_MODULOS = SAIDA_DIR / "busca_rewrite_tvsafe_rapido_modulos.csv"
ARQ_TRADES = SAIDA_DIR / "busca_rewrite_tvsafe_rapido_trades_top.csv"

TAKE = 50.5
STOP = 117.0
QUANTIS = [0.25, 0.4, 0.6, 0.75]

TOKENS = [
    ("Monday", "03:48", "BUY"),
    ("Tuesday", "03:48", "BUY"),
    ("Friday", "03:48", "SELL"),
    ("Monday", "10:30", "BUY"),
    ("Friday", "10:30", "SELL"),
    ("Sunday", "20:58", "BUY"),
    ("Wednesday", "20:58", "BUY"),
    ("Monday", "04:02", "BUY"),
    ("Tuesday", "03:12", "SELL"),
    ("Wednesday", "02:56", "BUY"),
    ("Thursday", "04:30", "SELL"),
    ("Friday", "09:30", "BUY"),
]


def metricas(trades, inicio=None):
    base = trades if inicio is None else trades[trades["datahora_entrada"] >= inicio]
    if base.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    p = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "dd": max_drawdown(p),
        "pf": profit_factor(p),
    }


def add_metricas(row, trades):
    fim = trades["datahora_entrada"].max() if not trades.empty else pd.Timestamp("2026-01-01")
    for nome, dias in [("365", 365), ("90", 90), ("30", 30)]:
        m = metricas(trades, fim - pd.Timedelta(days=dias))
        for k, v in m.items():
            row[f"{k}_{nome}"] = v
    for nome, ini, fim_abs in [
        ("2024", "2024-01-01", "2025-01-01"),
        ("2025", "2025-01-01", "2026-01-01"),
        ("2026", "2026-01-01", "2027-01-01"),
    ]:
        base = trades[(trades["datahora_entrada"] >= pd.Timestamp(ini)) & (trades["datahora_entrada"] < pd.Timestamp(fim_abs))]
        m = metricas(base)
        for k, v in m.items():
            row[f"{k}_{nome}"] = v
    return row


def preparar():
    df = indicadores(carregar_candles()).reset_index(drop=True)
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["dist_vwap"] = df["close"] - df["vwap"]
    df["dist_ema200"] = df["close"] - df["ema200"]
    df["range_30"] = df["high"].rolling(15).max() - df["low"].rolling(15).min()
    df["ret_60"] = df["close"] - df["close"].shift(30)
    max20 = df["high"].rolling(20).max()
    min20 = df["low"].rolling(20).min()
    df["pos_range20"] = (df["close"] - min20) / (max20 - min20).replace(0, np.nan)
    df["ema_trend"] = df["ema17"] - df["ema34"]
    return df


def simular_idx(df, idx, direcao, cache):
    chave = (int(idx), direcao)
    if chave not in cache:
        cache[chave] = simular_trade(df, int(idx), direcao, TAKE, STOP)
    sim = cache[chave]
    if sim is None:
        return None
    entrada, saida, pontos, resultado = sim
    return {
        "idx": int(idx),
        "datahora_sinal": df.at[int(idx), "DataHora_SP"],
        "datahora_entrada": entrada,
        "datahora_saida": saida,
        "pontos": float(pontos),
        "resultado": resultado,
    }


def filtrar_aberta(trades):
    if trades.empty:
        return trades
    out = []
    liberado = pd.Timestamp.min
    for row in trades.sort_values(["datahora_sinal", "modulo"]).itertuples(index=False):
        if row.datahora_sinal < liberado:
            continue
        liberado = row.datahora_saida
        out.append(row._asdict())
    return pd.DataFrame(out)


def filtro_mask(rows, filtro):
    if filtro is None:
        return pd.Series(True, index=rows.index)
    col, op, val = filtro
    return rows[col] >= val if op == ">=" else rows[col] <= val


def filtro_txt(filtro):
    if filtro is None:
        return "sem_filtro"
    col, op, val = filtro
    return f"{col} {op} {val:.4f}"


def gerar_modulos(df):
    features = ["rsi14", "macd_hist", "roc5", "roc10", "prev_roc5", "body", "ema_trend", "dist_vwap", "dist_ema200", "range_30", "ret_60", "pos_range20"]
    cache = {}
    modulos = []
    for dow, hhmm, direcao in TOKENS:
        rows = df[df["dow"].eq(dow) & df["hhmm"].eq(hhmm)].copy()
        if rows.empty:
            continue
        filtros = [None]
        for col in features:
            vals = rows[col].dropna()
            if len(vals) < 20:
                continue
            for q in vals.quantile(QUANTIS).dropna().unique():
                filtros.append((col, ">=", float(q)))
                filtros.append((col, "<=", float(q)))
        candidatos = []
        for filtro in filtros:
            mask = filtro_mask(rows, filtro)
            linhas = []
            for idx in rows.index[mask]:
                sim = simular_idx(df, idx, direcao, cache)
                if sim is None:
                    continue
                modulo = f"{dow}|{hhmm}|{direcao}|{filtro_txt(filtro)}"
                sim.update({"modulo": modulo, "token": f"{dow}|{hhmm}|{direcao}", "dow": dow, "hhmm": hhmm, "direcao": direcao, "filtro": filtro_txt(filtro)})
                linhas.append(sim)
            trades = filtrar_aberta(pd.DataFrame(linhas))
            row = {"modulo": f"{dow}|{hhmm}|{direcao}|{filtro_txt(filtro)}", "token": f"{dow}|{hhmm}|{direcao}", "dow": dow, "hhmm": hhmm, "direcao": direcao, "filtro": filtro_txt(filtro)}
            add_metricas(row, trades)
            if row["trades_365"] < 4 or row["pontos_365"] <= 0:
                continue
            row["score_modulo"] = row["winrate_365"] * 100 + row["pontos_365"] + min(row["pf_365"], 10) * 120 - abs(row["dd_365"]) * 0.4
            candidatos.append((row, trades))
        candidatos.sort(key=lambda x: (x[0]["score_modulo"], x[0]["winrate_365"], x[0]["pontos_365"]), reverse=True)
        modulos.extend(candidatos[:6])
        print(f"{dow} {hhmm} {direcao}: {len(candidatos)} candidatos, usando {min(6, len(candidatos))}", flush=True)
    return modulos


def avaliar_combo(combo):
    frames = [tr for _, tr in combo if not tr.empty]
    trades = filtrar_aberta(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame()
    row = {"modulos": " + ".join(r["modulo"] for r, _ in combo), "qtd_modulos": len(combo)}
    add_metricas(row, trades)
    row["score"] = (
        row["winrate_365"] * 120
        + row["pontos_365"]
        + row["pontos_90"] * 2
        + row["pontos_30"]
        + min(row["pf_365"], 10) * 250
        - abs(row["dd_365"]) * 0.55
        - max(0, 35 - row["trades_365"]) * 150
        - max(0, 85 - row["winrate_365"]) * 900
        - max(0, 75 - row["winrate_90"]) * 200
    )
    return row, trades


def buscar(modulos):
    linhas = []
    melhor_trades = pd.DataFrame()
    melhor_score = -10**18
    beam = [tuple()]
    for tamanho in range(1, 6):
        prox = []
        for combo in beam:
            usados = {r["token"] for r, _ in combo}
            start = 0
            if combo:
                ultimo = combo[-1][0]["modulo"]
                start = next((i + 1 for i, m in enumerate(modulos) if m[0]["modulo"] == ultimo), 0)
            for modulo in modulos[start:]:
                if modulo[0]["token"] in usados:
                    continue
                novo = combo + (modulo,)
                row, trades = avaliar_combo(novo)
                linhas.append(row)
                prox.append((row["score"], novo, trades))
                if row["score"] > melhor_score:
                    melhor_score = row["score"]
                    melhor_trades = trades
        prox.sort(key=lambda x: x[0], reverse=True)
        beam = [x[1] for x in prox[:80]]
        print("Beam", tamanho, len(beam), flush=True)
    ranking = pd.DataFrame(linhas).drop_duplicates("modulos").sort_values(["score", "winrate_365", "pontos_365"], ascending=False)
    return ranking, melhor_trades


def main():
    print("BUSCA REWRITE TVSAFE RAPIDO", flush=True)
    df = preparar()
    modulos = gerar_modulos(df)
    modulos_df = pd.DataFrame([m[0] for m in modulos]).sort_values("score_modulo", ascending=False)
    ranking, trades_top = buscar(modulos)
    modulos_df.to_csv(ARQ_MODULOS, index=False)
    ranking.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES, index=False)
    cols = ["modulos", "qtd_modulos", "trades_365", "winrate_365", "pontos_365", "dd_365", "pf_365", "trades_90", "winrate_90", "pontos_90", "trades_30", "winrate_30", "pontos_30", "score"]
    print("\nTop combos:")
    print(ranking[cols].head(25).to_string(index=False, max_colwidth=180), flush=True)
    print("\nTop modulos:")
    print(modulos_df[["modulo", "trades_365", "winrate_365", "pontos_365", "pf_365"]].head(30).to_string(index=False, max_colwidth=160), flush=True)
    print("\nArquivos:")
    print(ARQ_RANKING)
    print(ARQ_MODULOS)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
