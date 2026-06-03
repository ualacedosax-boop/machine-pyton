from itertools import combinations
from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import TAKE, STOP, preparar_candles
from simular_compilado_vencedoras import max_drawdown, profit_factor


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RANKING = SAIDA_DIR / "busca_calendario_dow_horario_230_250_ranking.csv"
ARQ_TOKENS = SAIDA_DIR / "busca_calendario_dow_horario_230_250_tokens.csv"
ARQ_TRADES = SAIDA_DIR / "busca_calendario_dow_horario_230_250_trades_top.csv"
ARQ_MD = SAIDA_DIR / "BUSCA_CALENDARIO_DOW_HORARIO_230_250.md"

DOWS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
JANELAS = [("02:00", "06:00"), ("09:30", "11:00"), ("20:00", "21:30")]
TOP_TOKENS_POR_DOW = 10
BEAM_SIZE = 20
MAX_BARRAS_SAIDA = 720


def dentro_janelas(hhmm):
    return any(inicio <= hhmm <= fim for inicio, fim in JANELAS)


def metricas(trades, inicio=None, fim=None):
    base = trades
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {"trades": 0, "dias": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0}
    pontos = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
        "winrate": float((pontos > 0).mean() * 100),
        "pontos": float(pontos.sum()),
        "dd": max_drawdown(pontos),
        "pf": profit_factor(pontos),
    }


def add_metricas(row, trades):
    for periodo, inicio, fim in [
        ("all", None, None),
        ("2024", "2024-01-01", "2025-01-01"),
        ("2025", "2025-01-01", "2026-01-01"),
        ("2026", "2026-01-01", "2027-01-01"),
    ]:
        m = metricas(trades, inicio, fim)
        for chave, valor in m.items():
            row[f"{chave}_{periodo}"] = valor
    if not trades.empty:
        fim = trades["datahora_entrada"].max()
        for periodo, dias in [("365", 365), ("90", 90), ("30", 30)]:
            m = metricas(trades, fim - pd.Timedelta(days=dias))
            for chave, valor in m.items():
                row[f"{chave}_{periodo}"] = valor
    else:
        for periodo in ["365", "90", "30"]:
            m = metricas(trades)
            for chave, valor in m.items():
                row[f"{chave}_{periodo}"] = valor
    return row


def score_token(row):
    penal_ano = (
        max(0.0, -row["pontos_2024"]) * 2.0
        + max(0.0, -row["pontos_2025"]) * 2.0
        + max(0.0, -row["pontos_2026"]) * 2.0
    )
    return (
        row["pontos_365"]
        + row["winrate_365"] * 35
        + min(row["pf_365"], 5.0) * 180
        - abs(row["dd_365"]) * 0.6
        - penal_ano
    )


def score_combo(row):
    dist = 0 if 230 <= row["trades_365"] <= 250 else min(abs(row["trades_365"] - 230), abs(row["trades_365"] - 250))
    penal_freq = dist * 130
    penal_win = max(0.0, 82.0 - row["winrate_365"]) * 720
    penal_ano = (
        max(0.0, -row["pontos_2024"]) * 4.0
        + max(0.0, -row["pontos_2025"]) * 4.0
        + max(0.0, -row["pontos_2026"]) * 4.0
    )
    penal_dd = abs(row["dd_365"]) * 0.8
    return (
        row["pontos_365"]
        + row["pontos_all"] * 0.22
        + min(row["pf_365"], 5.0) * 260
        + row["winrate_365"] * 45
        - penal_freq
        - penal_win
        - penal_ano
        - penal_dd
    )


def simular_arrays(candles, idx_sinal, direcao):
    idx_entrada = idx_sinal + 1
    opens = candles["_open_arr"]
    highs = candles["_high_arr"]
    lows = candles["_low_arr"]
    datas = candles["_data_arr"]
    if idx_entrada >= len(opens):
        return None
    entrada = float(opens[idx_entrada])
    if direcao == "BUY":
        preco_take = entrada + TAKE
        preco_stop = entrada - STOP
    else:
        preco_take = entrada - TAKE
        preco_stop = entrada + STOP

    fim = min(len(opens), idx_entrada + MAX_BARRAS_SAIDA)
    trecho_high = highs[idx_entrada:fim]
    trecho_low = lows[idx_entrada:fim]
    if direcao == "BUY":
        stop_hits = (trecho_low <= preco_stop).nonzero()[0]
        take_hits = (trecho_high >= preco_take).nonzero()[0]
    else:
        stop_hits = (trecho_high >= preco_stop).nonzero()[0]
        take_hits = (trecho_low <= preco_take).nonzero()[0]

    primeiro_stop = int(stop_hits[0]) if len(stop_hits) else 10**9
    primeiro_take = int(take_hits[0]) if len(take_hits) else 10**9
    if primeiro_stop == primeiro_take == 10**9:
        return None
    if primeiro_stop <= primeiro_take:
        j = idx_entrada + primeiro_stop
        return datas[idx_entrada], datas[j], -STOP, "STOP"
    j = idx_entrada + primeiro_take
    return datas[idx_entrada], datas[j], TAKE, "TAKE"


def filtrar_operacao_aberta(trades):
    if trades.empty:
        return trades
    linhas = []
    proxima_liberada = pd.Timestamp.min
    for row in trades.sort_values(["idx", "token"]).itertuples(index=False):
        if row.datahora_sinal < proxima_liberada:
            continue
        proxima_liberada = row.datahora_saida
        linhas.append(row._asdict())
    return pd.DataFrame(linhas)


def precomputar_trades_por_token(candles):
    df = candles.copy()
    df["hhmm"] = df["DataHora_SP"].dt.strftime("%H:%M")
    df["dow"] = df["DataHora_SP"].dt.day_name()
    df = df[df["dow"].isin(DOWS) & df["hhmm"].map(dentro_janelas)].copy()
    shared = {
        "_open_arr": candles["open"].to_numpy(),
        "_high_arr": candles["high"].to_numpy(),
        "_low_arr": candles["low"].to_numpy(),
        "_data_arr": candles["DataHora_SP"].to_numpy(),
    }
    linhas_por_token = {}
    total = 0
    for row in df[["DataHora_SP", "hhmm", "dow"]].itertuples():
        idx = int(row.Index)
        for direcao in ["BUY", "SELL"]:
            token = f"{row.dow}|{row.hhmm}|{direcao}"
            sim = simular_arrays(shared, idx, direcao)
            if sim is None:
                continue
            data_entrada, data_saida, pontos, resultado = sim
            linhas_por_token.setdefault(token, []).append(
                {
                    "idx": idx,
                    "token": token,
                    "dow": row.dow,
                    "hhmm": row.hhmm,
                    "direcao": direcao,
                    "datahora_sinal": row.DataHora_SP,
                    "datahora_entrada": pd.Timestamp(data_entrada),
                    "datahora_saida": pd.Timestamp(data_saida),
                    "pontos": float(pontos),
                    "resultado": resultado,
                }
            )
            total += 1
    colunas = [
        "idx",
        "token",
        "dow",
        "hhmm",
        "direcao",
        "datahora_sinal",
        "datahora_entrada",
        "datahora_saida",
        "pontos",
        "resultado",
    ]
    trades_por_token = {
        token: pd.DataFrame(linhas, columns=colunas)
        for token, linhas in linhas_por_token.items()
    }
    for dow in DOWS:
        for hhmm in sorted(df.loc[df["dow"].eq(dow), "hhmm"].unique()):
            for direcao in ["BUY", "SELL"]:
                token = f"{dow}|{hhmm}|{direcao}"
                trades_por_token.setdefault(
                    token,
                    pd.DataFrame(columns=colunas),
                )
    print("Trades precomputados:", total, flush=True)
    return trades_por_token


def avaliar_tokens(nome, tokens_combo, trades_por_token):
    frames = [trades_por_token[token] for token in tokens_combo if not trades_por_token[token].empty]
    trades = filtrar_operacao_aberta(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame()
    row = {"cenario": nome}
    add_metricas(row, trades)
    row["score"] = score_combo(row)
    return row, trades


def ranquear_tokens(trades_por_token):
    linhas = []
    for token, trades_brutos in trades_por_token.items():
        trades = filtrar_operacao_aberta(trades_brutos)
        row = {"token": token, "dow": token.split("|")[0], "hhmm": token.split("|")[1], "direcao": token.split("|")[2]}
        add_metricas(row, trades)
        row["score_token"] = score_token(row)
        linhas.append(row)
    tokens = pd.DataFrame(linhas)
    tokens = tokens[
        (tokens["trades_365"] >= 25)
        & (tokens["pontos_all"] > -600)
        & (tokens["pontos_365"] > -250)
    ].sort_values(["dow", "score_token"], ascending=[True, False])
    return tokens


def buscar_combos(trades_por_token, tokens):
    candidatos = {}
    for dow in DOWS:
        top = tokens[tokens["dow"].eq(dow)].head(TOP_TOKENS_POR_DOW)
        candidatos[dow] = top["token"].tolist()

    linhas = []
    melhor_trades = pd.DataFrame()
    melhor_score = -10**18

    for tamanho in [5]:
        for dows in combinations(DOWS, tamanho):
            beam = [tuple()]
            for dow in dows:
                prox = []
                for tokens_combo in beam:
                    for token in candidatos.get(dow, []):
                        novo_tokens = tokens_combo + (token,)
                        row, trades = avaliar_tokens(" + ".join(novo_tokens), novo_tokens, trades_por_token)
                        row["qtd_dows"] = len(novo_tokens)
                        row["tokens"] = " + ".join(novo_tokens)
                        prox.append((row["score"], novo_tokens, row, trades))
                prox.sort(key=lambda x: x[0], reverse=True)
                beam = [tokens_combo for _, tokens_combo, _, _ in prox[:BEAM_SIZE]]
                for score, tokens_combo, row, trades in prox[: max(50, BEAM_SIZE // 3)]:
                    linhas.append(row)
                    if score > melhor_score:
                        melhor_score = score
                        melhor_trades = trades.assign(cenario=row["tokens"]) if not trades.empty else trades

    ranking = pd.DataFrame(linhas).drop_duplicates("tokens").sort_values(
        ["score", "winrate_365", "pontos_365"],
        ascending=False,
    )
    return ranking, melhor_trades


def tabela_md(df, colunas, limite=20):
    if df.empty:
        return ["Nenhum cenario encontrado."]
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join(["---"] * len(colunas)) + " |",
    ]
    for row in df[colunas].head(limite).itertuples(index=False):
        valores = []
        for valor in row:
            if isinstance(valor, float):
                valores.append(f"{valor:.2f}")
            else:
                valores.append(str(valor))
        linhas.append("| " + " | ".join(valores) + " |")
    return linhas


def escrever_markdown(tokens, ranking):
    cols = [
        "tokens",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
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
    faixa = ranking[ranking["trades_365"].between(220, 260)].sort_values(
        ["winrate_365", "pontos_365"],
        ascending=False,
    )
    alvo_80 = faixa[(faixa["winrate_365"] >= 80) & (faixa["pontos_365"] > 0)]
    alvo_85 = faixa[(faixa["winrate_365"] >= 85) & (faixa["pontos_365"] > 0)]
    linhas = [
        "# Busca Calendario DOW Horario 230-250",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Familia testada: combinacoes de dia da semana + horario + direcao nas janelas 02:00-06:00, 09:30-11:00 e 20:00-21:30.",
        "A estrategia escolhe horarios fixos por dia da semana e simula take 50.5 / stop 117.",
        "",
        "## Top combinacoes por score",
        "",
    ]
    linhas.extend(tabela_md(ranking, cols, 20))
    linhas.extend(["", "## Melhores na faixa 220-260 trades", ""])
    linhas.extend(tabela_md(faixa, cols, 20))
    linhas.extend(["", "## Faixa 220-260 com 80%+", ""])
    linhas.extend(tabela_md(alvo_80, cols, 20))
    linhas.extend(["", "## Faixa 220-260 com 85%+", ""])
    linhas.extend(tabela_md(alvo_85, cols, 20))
    linhas.extend(
        [
            "",
            "## Leitura",
            "",
            f"- Tokens individuais considerados depois dos filtros: {len(tokens)}.",
            "- Se a faixa 85%+ ficar vazia, calendario puro por dia/horario tambem nao sustentou a meta.",
            "- Se aparecer candidato, ele ainda precisa ser convertido para Pine e validado no TradingView com Backtesting Profundo.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    candles = preparar_candles()
    trades_por_token = precomputar_trades_por_token(candles)
    print("Tokens brutos:", len(trades_por_token), flush=True)
    tokens = ranquear_tokens(trades_por_token)
    print("Tokens apos filtro:", len(tokens), flush=True)
    print(tokens.head(30).to_string(index=False), flush=True)

    ranking, trades_top = buscar_combos(trades_por_token, tokens)
    cols = [
        "tokens",
        "trades_365",
        "winrate_365",
        "pontos_365",
        "dd_365",
        "pf_365",
        "trades_2024",
        "winrate_2024",
        "pontos_2024",
        "trades_2025",
        "winrate_2025",
        "pontos_2025",
        "trades_2026",
        "winrate_2026",
        "pontos_2026",
        "score",
    ]
    print("\nTop calendario DOW/horario:")
    print(ranking[cols].head(30).to_string(index=False, max_colwidth=160), flush=True)
    faixa = ranking[ranking["trades_365"].between(220, 260)].sort_values(["winrate_365", "pontos_365"], ascending=False)
    print("\nMelhores 220-260 trades:")
    if faixa.empty:
        print("Nenhum na faixa.", flush=True)
    else:
        print(faixa[cols].head(20).to_string(index=False, max_colwidth=160), flush=True)

    tokens.to_csv(ARQ_TOKENS, index=False)
    ranking.to_csv(ARQ_RANKING, index=False)
    trades_top.to_csv(ARQ_TRADES, index=False)
    escrever_markdown(tokens, ranking)
    print("\nArquivos:")
    print(ARQ_TOKENS)
    print(ARQ_RANKING)
    print(ARQ_TRADES)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
