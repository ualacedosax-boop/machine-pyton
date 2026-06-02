from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import TAKE, STOP, preparar_candles, simular_lista
from simular_compilado_vencedoras import max_drawdown, profit_factor
from validar_regime_191_89_multiano import MODULOS


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RESUMO = SAIDA_DIR / "validacao_regime_refino_93_resumo.csv"
ARQ_TRADES = SAIDA_DIR / "validacao_regime_refino_93_trades.csv"


PERFIS = {
    "01_refino_157_93": [
        "DMI3_0348_BUY",
        "DMI3_1030_BUY",
        "DMI3_1030_SELL",
        "REG_0346_SELL",
        "REG_0348_BUY",
        "REG_1030_SELL",
        "REG_2052_BUY",
        "REG_2052_SELL_A",
        "REG_2052_SELL_B",
        "REG_2058_BUY",
    ],
    "02_equilibrado_139_94": [
        "DMI3_0348_BUY",
        "DMI3_1030_BUY",
        "REG_0346_SELL",
        "REG_0348_BUY",
        "REG_1030_BUY",
        "REG_2052_BUY",
        "REG_2052_SELL_A",
        "REG_2052_SELL_B",
        "REG_2058_BUY",
    ],
    "03_frequente_191_89": [
        "DMI3_0348_BUY",
        "DMI3_1030_BUY",
        "DMI3_1030_SELL",
        "DMI3_2058_BUY",
        "REG_0346_SELL",
        "REG_0348_BUY",
        "REG_1030_BUY",
        "REG_1030_SELL",
        "REG_2052_BUY",
        "REG_2052_SELL_A",
        "REG_2052_SELL_B",
        "REG_2058_BUY",
    ],
}


def enriquecer_candles():
    df = preparar_candles()
    df["dist_vwap"] = df["close"] - df["vwap"]
    return df


def sinais_dmi_por_modulo(candles):
    df = candles
    h = df["DataHora_SP"].dt.hour
    m = df["DataHora_SP"].dt.minute
    voto_macd = (df["macd"] >= df["macd_signal"]).map({True: 1, False: -1})
    voto_candle = (df["body"] >= 0).map({True: 1, False: -1})
    voto_prev_roc5_contra = (df["prev_roc5"] <= 0).map({True: 1, False: -1})
    voto_sma1734 = (df["sma17"] >= df["sma34"]).map({True: 1, False: -1})
    voto_roc10 = (df["roc10"] >= 0).map({True: 1, False: -1})
    voto_ema1734 = (df["ema17"] >= df["ema34"]).map({True: 1, False: -1})
    voto_roc5 = (df["roc5"] >= 0).map({True: 1, False: -1})
    voto_vwap = (df["close"] >= df["vwap"]).map({True: 1, False: -1})

    score0348 = voto_macd + voto_candle + voto_prev_roc5_contra
    score1030 = voto_sma1734 + voto_roc10 + voto_prev_roc5_contra
    score2058 = voto_ema1734 + voto_roc5 + voto_vwap
    ok = df["dmi_gap"] >= 3
    regras = [
        ("DMI3_0348_BUY", (h == 3) & (m == 48) & ok & (score0348 >= 0) & df["dow"].isin(["Monday", "Tuesday"]), "BUY"),
        ("DMI3_1030_BUY", (h == 10) & (m == 30) & ok & (score1030 >= 0) & df["dow"].eq("Monday"), "BUY"),
        ("DMI3_1030_SELL", (h == 10) & (m == 30) & ok & (score1030 < 0) & df["dow"].eq("Friday"), "SELL"),
        ("DMI3_2058_BUY", (h == 20) & (m == 58) & ok & (score2058 >= 0) & df["dow"].isin(["Sunday", "Wednesday"]), "BUY"),
    ]
    return {nome: [(idx, nome, direcao, TAKE, STOP) for idx in df.index[mask]] for nome, mask, direcao in regras}


def sinais_regime_por_modulo(candles):
    sinais = {}
    for nome, hhmm, direcao, filtro in MODULOS:
        mask = candles["hhmm"].eq(hhmm)
        if direcao == "BUY":
            mask &= (candles["ema17"] >= candles["ema34"]) & (candles["di_plus"] >= candles["di_minus"])
        else:
            mask &= (candles["ema17"] < candles["ema34"]) & (candles["di_minus"] > candles["di_plus"])
        mask &= filtro(candles)
        sinais[nome] = [(idx, nome, direcao, TAKE, STOP) for idx in candles.index[mask]]
    return sinais


def metricas(periodo, perfil, trades, inicio=None, fim=None):
    base = trades
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {
            "perfil": perfil,
            "periodo": periodo,
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "dd": 0.0,
            "pf": 0.0,
            "dias": 0,
        }
    pontos = base["pontos"].astype(float)
    return {
        "perfil": perfil,
        "periodo": periodo,
        "trades": int(len(base)),
        "winrate": float((pontos > 0).mean() * 100),
        "pontos": float(pontos.sum()),
        "dd": max_drawdown(pontos),
        "pf": profit_factor(pontos),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
    }


def avaliar_perfil(candles, mapa_sinais, perfil, modulos):
    sinais = []
    for modulo in modulos:
        sinais.extend(mapa_sinais[modulo])
    trades = simular_lista(candles, sinais, {})
    if not trades.empty:
        trades = trades.assign(perfil=perfil)
    resumo = [
        metricas("all", perfil, trades),
        metricas("2024", perfil, trades, "2024-01-01", "2025-01-01"),
        metricas("2025", perfil, trades, "2025-01-01", "2026-01-01"),
        metricas("2026", perfil, trades, "2026-01-01", "2027-01-01"),
    ]
    if not trades.empty:
        fim = trades["datahora_entrada"].max()
        resumo.extend(
            [
                metricas("365d", perfil, trades, fim - pd.Timedelta(days=365)),
                metricas("90d", perfil, trades, fim - pd.Timedelta(days=90)),
                metricas("30d", perfil, trades, fim - pd.Timedelta(days=30)),
            ]
        )
    return pd.DataFrame(resumo), trades


def main():
    candles = enriquecer_candles()
    mapa_sinais = {}
    mapa_sinais.update(sinais_dmi_por_modulo(candles))
    mapa_sinais.update(sinais_regime_por_modulo(candles))

    resumos = []
    trades = []
    for perfil, modulos in PERFIS.items():
        resumo, trades_perfil = avaliar_perfil(candles, mapa_sinais, perfil, modulos)
        resumos.append(resumo)
        trades.append(trades_perfil)

    resumo_final = pd.concat(resumos, ignore_index=True)
    trades_final = pd.concat(trades, ignore_index=True)
    print(resumo_final.to_string(index=False))
    resumo_final.to_csv(ARQ_RESUMO, index=False)
    trades_final.to_csv(ARQ_TRADES, index=False)
    print("\nArquivos:")
    print(ARQ_RESUMO)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
