from pathlib import Path
from datetime import datetime
from itertools import combinations

import pandas as pd

from buscar_regime_dia_230_250 import TAKE, STOP, preparar_candles, sinais_dmi3, simular_lista
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
ARQ_RESUMO = SAIDA_DIR / f"auditoria_modulos_regime_robusto_resumo_{STAMP}.csv"
ARQ_TRADES = SAIDA_DIR / f"auditoria_modulos_regime_robusto_trades_{STAMP}.csv"


MODULOS = [
    ("REG_0346_SELL", "03:46", "SELL", lambda df: (df["dmi_gap"] >= 6) & (df["dist_vwap"] >= -7.26)),
    ("REG_0348_BUY", "03:48", "BUY", lambda df: (df["adx14"] >= 25) & (df["dmi_gap"] >= 3) & (df["ret_60"] <= 17.25)),
    ("REG_1030_BUY", "10:30", "BUY", lambda df: (df["adx14"] >= 30) & (df["ema200_slope10"] >= 5.67)),
    ("REG_1030_SELL", "10:30", "SELL", lambda df: (df["adx14"] >= 25) & (df["range_30"] <= 62.5)),
    ("REG_2052_BUY", "20:52", "BUY", lambda df: (df["adx14"] >= 25) & (df["range_30"] <= 18.44)),
    ("REG_2052_SELL_A", "20:52", "SELL", lambda df: (df["adx14"] >= 20) & (df["dmi_gap"] >= 10) & (df["ret_60"] >= -27.75)),
    ("REG_2052_SELL_B", "20:52", "SELL", lambda df: (df["adx14"] >= 30) & (df["ret_30"] >= -3.25)),
    ("REG_2058_BUY", "20:58", "BUY", lambda df: (df["dmi_gap"] >= 10) & (df["dmi_gap"] <= 13.35)),
]


def sinais_modulo(candles, modulo):
    nome, hhmm, direcao, filtro = modulo
    mask = candles["hhmm"].eq(hhmm)
    if direcao == "BUY":
        mask &= (candles["ema17"] >= candles["ema34"]) & (candles["di_plus"] >= candles["di_minus"])
    else:
        mask &= (candles["ema17"] < candles["ema34"]) & (candles["di_minus"] > candles["di_plus"])
    mask &= filtro(candles)
    return [(idx, nome, direcao, TAKE, STOP) for idx in candles.index[mask]]


def resumo_periodo(nome, trades, inicio=None, fim=None):
    base = trades
    if inicio:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {
            "cenario": nome,
            "trades": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "dd": 0.0,
            "pf": 0.0,
            "dias": 0,
        }
    p = base["pontos"].astype(float)
    return {
        "cenario": nome,
        "trades": int(len(base)),
        "winrate": float((p > 0).mean() * 100),
        "pontos": float(p.sum()),
        "dd": max_drawdown(p),
        "pf": profit_factor(p),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
    }


def resumo_cenario(nome, trades):
    linhas = [
        resumo_periodo(f"{nome}|all", trades),
        resumo_periodo(f"{nome}|2024", trades, "2024-01-01", "2025-01-01"),
        resumo_periodo(f"{nome}|2025", trades, "2025-01-01", "2026-01-01"),
        resumo_periodo(f"{nome}|2026", trades, "2026-01-01", "2027-01-01"),
    ]
    if not trades.empty:
        fim = trades["datahora_entrada"].max()
        linhas.append(resumo_periodo(f"{nome}|365d", trades, fim - pd.Timedelta(days=365)))
        linhas.append(resumo_periodo(f"{nome}|90d", trades, fim - pd.Timedelta(days=90)))
        linhas.append(resumo_periodo(f"{nome}|30d", trades, fim - pd.Timedelta(days=30)))
    return linhas


def main():
    candles = preparar_candles()
    cache = {}
    base = sinais_dmi3(candles)
    sinais_por_modulo = {modulo[0]: sinais_modulo(candles, modulo) for modulo in MODULOS}

    linhas = []
    todos_trades = []

    cenarios = {"BASE_DMI3": list(base)}
    cenarios["COMPLETO"] = list(base)
    for sinais in sinais_por_modulo.values():
        cenarios["COMPLETO"].extend(sinais)
    for nome, sinais in sinais_por_modulo.items():
        cenarios[f"SO_MODULO_{nome}"] = list(sinais)
        cenarios[f"SEM_{nome}"] = list(base)
        for outro_nome, outro_sinais in sinais_por_modulo.items():
            if outro_nome != nome:
                cenarios[f"SEM_{nome}"].extend(outro_sinais)

    nomes_modulos = list(sinais_por_modulo)
    for qtd_remover in [2, 3, 4]:
        for removidos in combinations(nomes_modulos, qtd_remover):
            nome_cenario = "SEM_COMBO_" + "__".join(removidos)
            cenarios[nome_cenario] = list(base)
            for outro_nome, outro_sinais in sinais_por_modulo.items():
                if outro_nome not in removidos:
                    cenarios[nome_cenario].extend(outro_sinais)

    for nome, sinais in cenarios.items():
        trades = simular_lista(candles, sinais, cache)
        if not trades.empty:
            trades = trades.assign(cenario=nome)
            todos_trades.append(trades)
        linhas.extend(resumo_cenario(nome, trades))

    resumo = pd.DataFrame(linhas)
    trades_all = pd.concat(todos_trades, ignore_index=True) if todos_trades else pd.DataFrame()
    print("Resumo principal:")
    principal = resumo[resumo["cenario"].str.endswith("|365d") | resumo["cenario"].str.endswith("|2024")]
    print(principal.sort_values(["cenario"]).to_string(index=False))
    print("\nRemocoes ordenadas por 2024:")
    rem = resumo[resumo["cenario"].str.startswith("SEM_") & resumo["cenario"].str.endswith("|2024")].copy()
    print(rem.sort_values("pontos", ascending=False).to_string(index=False))
    print("\nCombos com 365d >= 170 trades, 365d >= 85% e 2024 positivo:")
    wide = resumo.copy()
    wide[["base_cenario", "periodo"]] = wide["cenario"].str.rsplit("|", n=1, expand=True)
    tabela = wide.pivot(index="base_cenario", columns="periodo", values=["trades", "winrate", "pontos", "dd", "pf"])
    tabela.columns = [f"{a}_{b}" for a, b in tabela.columns]
    tabela = tabela.reset_index()
    filtro = tabela[
        (tabela["trades_365d"] >= 170)
        & (tabela["winrate_365d"] >= 85)
        & (tabela["pontos_2024"] > 0)
        & (tabela["pontos_2025"] > 0)
        & (tabela["pontos_2026"] > 0)
    ].sort_values(["pontos_2024", "pontos_365d"], ascending=False)
    cols = [
        "base_cenario",
        "trades_365d",
        "winrate_365d",
        "pontos_365d",
        "dd_365d",
        "pf_365d",
        "trades_2024",
        "winrate_2024",
        "pontos_2024",
        "trades_2025",
        "winrate_2025",
        "pontos_2025",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
    ]
    if not filtro.empty:
        print(filtro[cols].head(30).to_string(index=False))
    else:
        print("Nenhum combo passou no filtro.")
    try:
        resumo.to_csv(ARQ_RESUMO, index=False)
        trades_all.to_csv(ARQ_TRADES, index=False)
        print("\nArquivos:")
        print(ARQ_RESUMO)
        print(ARQ_TRADES)
    except PermissionError as exc:
        print("\nAVISO: nao consegui salvar CSV:", exc)


if __name__ == "__main__":
    main()
