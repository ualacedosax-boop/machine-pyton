from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
ARQUIVOS_CANDLES = [
    BASE_DIR / "dados_mnq_2024_ibkr" / "MNQ_2024_2MIN_IBKR_CONTINUO_REPARADO.csv",
    BASE_DIR / "MNQ_2025_2MIN_IBKR_CONTINUO_UPLOADS.csv",
    BASE_DIR / "dados_mnq_2026_ibkr" / "MNQ_2026_2MIN_IBKR_CONTINUO.csv",
]
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "busca_regime_3h_candles_ibkr_ranking.csv"
ARQ_TRADES = SAIDA_DIR / "busca_regime_3h_candles_ibkr_trades_top.csv"
ARQ_XLSX = SAIDA_DIR / "busca_regime_3h_candles_ibkr.xlsx"

TAKE = 50.5
STOP = 117.0
PONTO_USD = 2.0


def carregar_candles():
    partes = []
    for caminho in ARQUIVOS_CANDLES:
        df = pd.read_csv(caminho)
        cols = {c.lower(): c for c in df.columns}
        data_col = cols.get("datahora_sp")
        if not data_col:
            raise ValueError(f"Arquivo sem DataHora_SP: {caminho}")
        base = df[[data_col, "open", "high", "low", "close", "volume"]].copy()
        base.columns = ["DataHora_SP", "open", "high", "low", "close", "volume"]
        base["DataHora_SP"] = pd.to_datetime(base["DataHora_SP"], errors="coerce")
        partes.append(base.dropna(subset=["DataHora_SP"]))

    candles = pd.concat(partes, ignore_index=True)
    candles = candles.drop_duplicates("DataHora_SP").sort_values("DataHora_SP").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        candles[col] = pd.to_numeric(candles[col], errors="coerce")
    candles = candles.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return candles


def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def indicadores(df):
    out = df.copy()
    out["ema17"] = out["close"].ewm(span=17, adjust=False).mean()
    out["ema34"] = out["close"].ewm(span=34, adjust=False).mean()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean()
    out["sma17"] = out["close"].rolling(17).mean()
    out["sma34"] = out["close"].rolling(34).mean()
    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["roc5"] = out["close"] - out["close"].shift(5)
    out["roc10"] = out["close"] - out["close"].shift(10)
    out["prev_roc5"] = out["roc5"].shift(1)
    out["body"] = out["close"] - out["open"]
    out["ema_gap"] = (out["ema17"] - out["ema34"]).abs()

    data = out["DataHora_SP"].dt.date
    typical_x_vol = ((out["high"] + out["low"] + out["close"]) / 3) * out["volume"].fillna(0)
    out["vwap"] = typical_x_vol.groupby(data).cumsum() / out["volume"].fillna(0).groupby(data).cumsum().replace(0, np.nan)

    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = rma(gain, 14) / rma(loss, 14).replace(0, np.nan)
    out["rsi14"] = 100 - (100 / (1 + rs))

    up_move = out["high"].diff()
    down_move = -out["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["close"].shift()).abs(),
            (out["low"] - out["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = rma(tr, 14)
    out["di_plus"] = 100 * rma(pd.Series(plus_dm, index=out.index), 14) / atr.replace(0, np.nan)
    out["di_minus"] = 100 * rma(pd.Series(minus_dm, index=out.index), 14) / atr.replace(0, np.nan)
    dx = 100 * (out["di_plus"] - out["di_minus"]).abs() / (out["di_plus"] + out["di_minus"]).replace(0, np.nan)
    out["adx14"] = rma(dx, 14)
    out["dmi_gap"] = (out["di_plus"] - out["di_minus"]).abs()
    return out


def score_sinais(df):
    out = df.copy()
    h = out["DataHora_SP"].dt.hour
    m = out["DataHora_SP"].dt.minute
    out["hhmm"] = out["DataHora_SP"].dt.strftime("%H:%M")
    out["dow"] = out["DataHora_SP"].dt.day_name()

    voto_macd = np.where(out["macd"] >= out["macd_signal"], 1, -1)
    voto_candle = np.where(out["body"] >= 0, 1, -1)
    voto_prev_roc5_contra = np.where(out["prev_roc5"] <= 0, 1, -1)
    voto_sma1734 = np.where(out["sma17"] >= out["sma34"], 1, -1)
    voto_roc10 = np.where(out["roc10"] >= 0, 1, -1)
    voto_ema1734 = np.where(out["ema17"] >= out["ema34"], 1, -1)
    voto_roc5 = np.where(out["roc5"] >= 0, 1, -1)
    voto_vwap = np.where(out["close"] >= out["vwap"], 1, -1)

    out["score0348"] = voto_macd + voto_candle + voto_prev_roc5_contra
    out["score1030"] = voto_sma1734 + voto_roc10 + voto_prev_roc5_contra
    out["score2058"] = voto_ema1734 + voto_roc5 + voto_vwap
    out["horario_sinal"] = np.select(
        [(h == 3) & (m == 48), (h == 10) & (m == 30), (h == 20) & (m == 58)],
        ["03:48", "10:30", "20:58"],
        default="",
    )
    score = np.select(
        [out["horario_sinal"].eq("03:48"), out["horario_sinal"].eq("10:30"), out["horario_sinal"].eq("20:58")],
        [out["score0348"], out["score1030"], out["score2058"]],
        default=np.nan,
    )
    out["direcao"] = np.where(score >= 0, "BUY", "SELL")
    return out[out["horario_sinal"] != ""].copy()


def mascara_filtro(sinais, cfg):
    mask = (
        sinais["token"].isin(cfg["tokens"])
        & (sinais["adx14"] >= cfg["adx_min"])
        & (sinais["dmi_gap"] >= cfg["dmi_gap_min"])
        & (sinais["ema_gap"] >= cfg["ema_gap_min"])
    )
    if cfg["usar_rsi"]:
        mask &= (
            (sinais["direcao"].eq("BUY") & (sinais["rsi14"] >= cfg["rsi_buy_min"]))
            | (sinais["direcao"].eq("SELL") & (sinais["rsi14"] <= cfg["rsi_sell_max"]))
        )
    if cfg["usar_ema200"]:
        mask &= (
            (sinais["direcao"].eq("BUY") & (sinais["close"] >= sinais["ema200"]))
            | (sinais["direcao"].eq("SELL") & (sinais["close"] <= sinais["ema200"]))
        )
    if cfg["usar_vwap"]:
        mask &= (
            (sinais["direcao"].eq("BUY") & (sinais["close"] >= sinais["vwap"]))
            | (sinais["direcao"].eq("SELL") & (sinais["close"] <= sinais["vwap"]))
        )
    return mask


def simular_trade(candles, idx_sinal, direcao):
    idx_entrada = idx_sinal + 1
    if idx_entrada >= len(candles):
        return None
    entrada = float(candles.at[idx_entrada, "open"])
    if direcao == "BUY":
        take = entrada + TAKE
        stop = entrada - STOP
    else:
        take = entrada - TAKE
        stop = entrada + STOP

    data_entrada = candles.at[idx_entrada, "DataHora_SP"]
    for j in range(idx_entrada, len(candles)):
        high = float(candles.at[j, "high"])
        low = float(candles.at[j, "low"])
        data_saida = candles.at[j, "DataHora_SP"]
        if direcao == "BUY":
            if low <= stop:
                return data_entrada, data_saida, -STOP, "STOP"
            if high >= take:
                return data_entrada, data_saida, TAKE, "TAKE"
        else:
            if high >= stop:
                return data_entrada, data_saida, -STOP, "STOP"
            if low <= take:
                return data_entrada, data_saida, TAKE, "TAKE"
    return None


def max_drawdown(pontos):
    eq = pontos.cumsum()
    if eq.empty:
        return 0.0
    return float((eq - eq.cummax()).min())


def profit_factor(pontos):
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    return ganhos / perdas if perdas else 999.0


def metricas(trades, inicio=None):
    base = trades if inicio is None else trades[trades["datahora_entrada"] >= inicio]
    if base.empty:
        return 0, 0.0, 0.0, 0.0, 0.0
    p = base["pontos"].astype(float)
    return len(base), float((p > 0).mean() * 100), float(p.sum()), max_drawdown(p), profit_factor(p)


def main():
    candles = indicadores(carregar_candles())
    sinais = score_sinais(candles)
    sinais["token"] = sinais["horario_sinal"] + "|" + sinais["direcao"] + "|" + sinais["dow"]
    token_stats = sinais["token"].value_counts()

    configs = []
    candidatos_token = [
        ("3h_80_tv", ["03:48|BUY|Monday", "03:48|BUY|Tuesday", "10:30|BUY|Monday", "10:30|SELL|Friday", "20:58|BUY|Sunday", "20:58|BUY|Wednesday"]),
        ("81_tv", ["03:48|BUY|Monday", "03:48|BUY|Tuesday", "20:58|BUY|Sunday"]),
        ("87_tv", ["03:48|BUY|Monday", "20:58|BUY|Sunday"]),
    ]
    for nome_tokens, tokens in candidatos_token:
        for adx_min, dmi_gap_min, ema_gap_min, usar_rsi, usar_ema200, usar_vwap in product(
            [0, 15, 20, 25, 30],
            [0, 3, 6, 10],
            [0, 2, 5, 10],
            [False, True],
            [False, True],
            [False, True],
        ):
            configs.append(
                {
                    "nome_tokens": nome_tokens,
                    "tokens": set(tokens),
                    "adx_min": adx_min,
                    "dmi_gap_min": dmi_gap_min,
                    "ema_gap_min": ema_gap_min,
                    "usar_rsi": usar_rsi,
                    "rsi_buy_min": 50,
                    "rsi_sell_max": 50,
                    "usar_ema200": usar_ema200,
                    "usar_vwap": usar_vwap,
                }
            )

    mapa_idx = {dt: i for i, dt in enumerate(candles["DataHora_SP"])}
    trades_pre = []
    for sinal_id, sinal in sinais.reset_index(drop=True).iterrows():
        idx = mapa_idx.get(sinal["DataHora_SP"])
        if idx is None:
            continue
        sim = simular_trade(candles, idx, sinal["direcao"])
        if sim is None:
            continue
        data_entrada, data_saida, pontos, resultado = sim
        trades_pre.append(
            {
                "sinal_id": sinal_id,
                "datahora_sinal": sinal["DataHora_SP"],
                "datahora_entrada": data_entrada,
                "datahora_saida": data_saida,
                "horario_sinal": sinal["horario_sinal"],
                "direcao": sinal["direcao"],
                "dow": sinal["dow"],
                "token": sinal["token"],
                "pontos": pontos,
                "resultado": resultado,
            }
        )
    trades_pre = pd.DataFrame(trades_pre)
    sinais = sinais.reset_index(drop=True)

    linhas = []
    trades_top = []
    for n_cfg, cfg in enumerate(configs):
        selecionados_ids = set(sinais.index[mascara_filtro(sinais, cfg)])
        candidatos = trades_pre[trades_pre["sinal_id"].isin(selecionados_ids)].copy()
        trades = []
        proxima_liberada = pd.Timestamp.min
        for _, trade in candidatos.iterrows():
            if trade["datahora_sinal"] < proxima_liberada:
                continue
            trade = trade.to_dict()
            trade["config_id"] = n_cfg
            proxima_liberada = trade["datahora_saida"]
            trades.append(trade)
        trades = pd.DataFrame(trades)
        if trades.empty:
            continue
        fim = trades["datahora_entrada"].max()
        m_all = metricas(trades)
        m365 = metricas(trades, fim - pd.Timedelta(days=365))
        m90 = metricas(trades, fim - pd.Timedelta(days=90))
        m30 = metricas(trades, fim - pd.Timedelta(days=30))
        if m365[0] < 40:
            continue
        linha = {
            "config_id": n_cfg,
            "nome_tokens": cfg["nome_tokens"],
            "tokens": " ; ".join(sorted(cfg["tokens"])),
            "adx_min": cfg["adx_min"],
            "dmi_gap_min": cfg["dmi_gap_min"],
            "ema_gap_min": cfg["ema_gap_min"],
            "usar_rsi": cfg["usar_rsi"],
            "usar_ema200": cfg["usar_ema200"],
            "usar_vwap": cfg["usar_vwap"],
        }
        for prefix, m in [("all", m_all), ("d365", m365), ("d90", m90), ("d30", m30)]:
            linha[f"{prefix}_trades"] = m[0]
            linha[f"{prefix}_winrate"] = m[1]
            linha[f"{prefix}_pontos"] = m[2]
            linha[f"{prefix}_dd"] = m[3]
            linha[f"{prefix}_pf"] = m[4]
        linhas.append(linha)
        if m365[1] >= 80 and m90[2] > 0 and m30[2] > 0:
            trades_top.append(trades)

    ranking = pd.DataFrame(linhas)
    ranking["score"] = (
        ranking["d365_pontos"] / 1000
        + ranking["d365_winrate"] / 10
        + ranking["d90_winrate"] / 20
        + ranking["d30_winrate"] / 20
        + ranking["d365_pf"]
        + ranking["d365_dd"] / 1000
    )
    ranking = ranking.sort_values(
        ["d365_winrate", "d90_pontos", "d30_pontos", "d365_pontos"],
        ascending=[False, False, False, False],
    )

    top_trades = pd.concat(trades_top, ignore_index=True) if trades_top else pd.DataFrame()
    ranking.to_csv(ARQ_RANKING, index=False)
    top_trades.to_csv(ARQ_TRADES, index=False)
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        ranking.to_excel(writer, sheet_name="ranking", index=False)
        top_trades.to_excel(writer, sheet_name="trades_top", index=False)

    print("Top 20 por acerto 365d:")
    cols = [
        "config_id",
        "nome_tokens",
        "d365_trades",
        "d365_winrate",
        "d365_pontos",
        "d365_dd",
        "d365_pf",
        "d90_trades",
        "d90_winrate",
        "d90_pontos",
        "d30_trades",
        "d30_winrate",
        "d30_pontos",
        "adx_min",
        "dmi_gap_min",
        "ema_gap_min",
        "usar_rsi",
        "usar_ema200",
        "usar_vwap",
    ]
    print(ranking[cols].head(20).to_string(index=False))
    print("Arquivos:")
    print(ARQ_RANKING)
    print(ARQ_TRADES)
    print(ARQ_XLSX)


if __name__ == "__main__":
    main()
