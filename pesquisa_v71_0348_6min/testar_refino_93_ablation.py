from itertools import combinations
from pathlib import Path

import pandas as pd

from buscar_regime_dia_230_250 import simular_lista
from simular_compilado_vencedoras import max_drawdown, profit_factor
from validar_regime_refino_93 import (
    PERFIS,
    enriquecer_candles,
    sinais_dmi_por_modulo,
    sinais_regime_por_modulo,
)


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_RESUMO = SAIDA_DIR / "ablation_regime_refino_93_resumo.csv"
ARQ_MD = SAIDA_DIR / "ABLACAO_REGIME_REFINO_93.md"


def metricas(trades, inicio=None, fim=None):
    base = trades
    if inicio is not None:
        base = base[base["datahora_entrada"] >= pd.Timestamp(inicio)]
    if fim is not None:
        base = base[base["datahora_entrada"] < pd.Timestamp(fim)]
    if base.empty:
        return {"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0, "dias": 0}
    pontos = base["pontos"].astype(float)
    return {
        "trades": int(len(base)),
        "winrate": float((pontos > 0).mean() * 100),
        "pontos": float(pontos.sum()),
        "dd": max_drawdown(pontos),
        "pf": profit_factor(pontos),
        "dias": int(base["datahora_entrada"].dt.date.nunique()),
    }


def avaliar(nome, modulos, candles, mapa_sinais, cache):
    sinais = []
    for modulo in modulos:
        sinais.extend(mapa_sinais[modulo])
    trades = simular_lista(candles, sinais, cache)
    row = {
        "cenario": nome,
        "qtd_modulos": len(modulos),
        "modulos": " + ".join(modulos),
    }
    periodos = {
        "all": (None, None),
        "2024": ("2024-01-01", "2025-01-01"),
        "2025": ("2025-01-01", "2026-01-01"),
        "2026": ("2026-01-01", "2027-01-01"),
    }
    for periodo, (inicio, fim) in periodos.items():
        for chave, valor in metricas(trades, inicio, fim).items():
            row[f"{chave}_{periodo}"] = valor
    if not trades.empty:
        fim = trades["datahora_entrada"].max()
        extras = {
            "365d": fim - pd.Timedelta(days=365),
            "90d": fim - pd.Timedelta(days=90),
            "30d": fim - pd.Timedelta(days=30),
        }
        for periodo, inicio in extras.items():
            for chave, valor in metricas(trades, inicio).items():
                row[f"{chave}_{periodo}"] = valor
    else:
        for periodo in ["365d", "90d", "30d"]:
            for chave, valor in metricas(trades).items():
                row[f"{chave}_{periodo}"] = valor
    row["score"] = score(row)
    return row


def score(row):
    penal_2024 = max(0.0, -row["pontos_2024"]) * 5 + max(0.0, 80.0 - row["winrate_2024"]) * 120
    penal_freq = max(0, 135 - row["trades_365d"]) * 35
    penal_dd = abs(row["dd_365d"]) * 0.8
    return (
        row["pontos_365d"]
        + row["pontos_all"] * 0.25
        + min(row["pf_365d"], 6.0) * 300
        + row["winrate_365d"] * 35
        - penal_2024
        - penal_freq
        - penal_dd
    )


def tabela_md(df, colunas, limite=20):
    if df.empty:
        return ["Nenhum cenario encontrado."]
    df = df.head(limite)
    linhas = [
        "| " + " | ".join(colunas) + " |",
        "| " + " | ".join(["---"] * len(colunas)) + " |",
    ]
    for row in df[colunas].itertuples(index=False):
        valores = []
        for valor in row:
            if isinstance(valor, float):
                valores.append(f"{valor:.2f}")
            else:
                valores.append(str(valor))
        linhas.append("| " + " | ".join(valores) + " |")
    return linhas


def escrever_markdown(resumo):
    cols = [
        "cenario",
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
    base = resumo[resumo["cenario"].str.startswith("perfil_")].copy()
    alta = resumo[
        (resumo["trades_365d"] >= 120)
        & (resumo["winrate_365d"] >= 88)
        & (resumo["pontos_2024"] > 0)
        & (resumo["pontos_2025"] > 0)
        & (resumo["pontos_2026"] > 0)
    ].sort_values(["score", "winrate_365d", "pontos_365d"], ascending=False)
    frequencia = resumo[
        (resumo["trades_365d"].between(220, 260))
        & (resumo["winrate_365d"] >= 80)
        & (resumo["pontos_2024"] > 0)
        & (resumo["pontos_2025"] > 0)
        & (resumo["pontos_2026"] > 0)
    ].sort_values(["winrate_365d", "pontos_365d"], ascending=False)
    alvo_85 = frequencia[frequencia["winrate_365d"] >= 85]

    linhas = [
        "# Ablacao Regime Refino 93",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Objetivo: testar cortes e combinacoes dos modulos atuais do Refino 93 para saber se existe melhora robusta antes de criar outro Pine.",
        "",
        "## Perfis atuais",
        "",
    ]
    linhas.extend(tabela_md(base.sort_values("cenario"), cols, 10))
    linhas.extend(
        [
            "",
            "## Melhores combinacoes com 365d >= 88% e anos positivos",
            "",
        ]
    )
    linhas.extend(tabela_md(alta, cols, 20))
    linhas.extend(
        [
            "",
            "## Busca por 220-260 trades e 365d >= 80%",
            "",
        ]
    )
    linhas.extend(tabela_md(frequencia, cols, 20))
    linhas.extend(
        [
            "",
            "## Busca por 220-260 trades e 365d >= 85%",
            "",
        ]
    )
    linhas.extend(tabela_md(alvo_85, cols, 20))
    linhas.extend(
        [
            "",
            "## Leitura",
            "",
            "- Se a tabela de 220-260 trades e 85% ficar vazia, os modulos atuais nao sustentam a meta de frequencia com acerto alto.",
            "- Nesse caso, a proxima linha deve procurar novos horarios/indicadores, nao apenas apertar os filtros atuais.",
            "- O candidato de maior confianca continua dependendo da confirmacao no TradingView, porque a equivalencia Python/TV ainda e a parte critica.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    candles = enriquecer_candles()
    mapa_sinais = {}
    mapa_sinais.update(sinais_dmi_por_modulo(candles))
    mapa_sinais.update(sinais_regime_por_modulo(candles))

    universo = sorted({modulo for modulos in PERFIS.values() for modulo in modulos})
    cache = {}
    linhas = []
    for perfil, modulos in PERFIS.items():
        linhas.append(avaliar(f"perfil_{perfil}", tuple(modulos), candles, mapa_sinais, cache))

    for tamanho in range(1, len(universo) + 1):
        for combo in combinations(universo, tamanho):
            linhas.append(avaliar("combo_" + "__".join(combo), combo, candles, mapa_sinais, cache))

    resumo = pd.DataFrame(linhas).drop_duplicates(subset=["modulos"]).sort_values(
        ["score", "winrate_365d", "pontos_365d"],
        ascending=False,
    )
    resumo.to_csv(ARQ_RESUMO, index=False)
    escrever_markdown(resumo)

    cols = [
        "cenario",
        "trades_365d",
        "winrate_365d",
        "pontos_365d",
        "dd_365d",
        "pf_365d",
        "trades_2024",
        "winrate_2024",
        "pontos_2024",
    ]
    print(resumo[cols].head(30).to_string(index=False))
    print("\nArquivos:")
    print(ARQ_RESUMO)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
