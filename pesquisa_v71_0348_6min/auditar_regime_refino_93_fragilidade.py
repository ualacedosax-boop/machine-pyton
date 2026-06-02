from pathlib import Path

import pandas as pd

from simular_compilado_vencedoras import max_drawdown, profit_factor
from validar_regime_refino_93 import avaliar_perfil, enriquecer_candles, PERFIS, sinais_dmi_por_modulo, sinais_regime_por_modulo


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
ARQ_MD = SAIDA_DIR / "AUDITORIA_REGIME_REFINO_93_FRAGILIDADE.md"


def metricas(grupo):
    if grupo.empty:
        return pd.Series({"trades": 0, "winrate": 0.0, "pontos": 0.0, "dd": 0.0, "pf": 0.0})
    pontos = grupo["pontos"].astype(float)
    return pd.Series(
        {
            "trades": int(len(grupo)),
            "winrate": float((pontos > 0).mean() * 100),
            "pontos": float(pontos.sum()),
            "dd": max_drawdown(pontos),
            "pf": profit_factor(pontos),
        }
    )


def tabela_markdown(df, colunas, n=None):
    if n is not None:
        df = df.head(n)
    if df.empty:
        return ["Sem registros."]
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


def montar_trades():
    candles = enriquecer_candles()
    mapa_sinais = {}
    mapa_sinais.update(sinais_dmi_por_modulo(candles))
    mapa_sinais.update(sinais_regime_por_modulo(candles))

    frames = []
    for perfil, modulos in PERFIS.items():
        _, trades = avaliar_perfil(candles, mapa_sinais, perfil, modulos)
        frames.append(trades)
    trades = pd.concat(frames, ignore_index=True)
    trades["ano"] = trades["datahora_entrada"].dt.year
    trades["mes"] = trades["datahora_entrada"].dt.to_period("M").astype(str)
    trades["dow"] = trades["datahora_entrada"].dt.day_name()
    return trades


def gerar_markdown(trades):
    linhas = [
        "# Auditoria de Fragilidade - Regime Refino 93",
        "",
        "Pesquisa separada. Nao altera o V7.1 oficial.",
        "",
        "Objetivo: entender onde o candidato `V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine` fica mais fragil antes de apertar filtros.",
        "",
    ]

    for perfil in sorted(trades["perfil"].unique()):
        base = trades[trades["perfil"].eq(perfil)].copy()
        linhas.extend([f"## {perfil}", ""])

        por_ano = (
            base.groupby("ano", sort=True)
            .apply(metricas)
            .reset_index()
            .sort_values("ano")
        )
        linhas.extend(["### Por ano", ""])
        linhas.extend(tabela_markdown(por_ano, ["ano", "trades", "winrate", "pontos", "dd", "pf"]))
        linhas.append("")

        por_modulo = (
            base.groupby("modulo", sort=True)
            .apply(metricas)
            .reset_index()
            .sort_values("pontos")
        )
        linhas.extend(["### Modulos mais frageis", ""])
        linhas.extend(tabela_markdown(por_modulo, ["modulo", "trades", "winrate", "pontos", "dd", "pf"], 8))
        linhas.append("")
        linhas.extend(["### Modulos mais fortes", ""])
        linhas.extend(tabela_markdown(por_modulo.sort_values("pontos", ascending=False), ["modulo", "trades", "winrate", "pontos", "dd", "pf"], 8))
        linhas.append("")

        por_mes = (
            base.groupby("mes", sort=True)
            .apply(metricas)
            .reset_index()
            .sort_values("pontos")
        )
        linhas.extend(["### Piores meses", ""])
        linhas.extend(tabela_markdown(por_mes, ["mes", "trades", "winrate", "pontos", "dd", "pf"], 10))
        linhas.append("")

    foco = trades[trades["perfil"].eq("02_equilibrado_139_94")].copy()
    foco_2024 = foco[foco["ano"].eq(2024)]
    por_modulo_2024 = (
        foco_2024.groupby("modulo", sort=True)
        .apply(metricas)
        .reset_index()
        .sort_values("pontos")
    )
    linhas.extend(
        [
            "## Leitura do perfil recomendado",
            "",
            "Perfil recomendado atual: `02_equilibrado_139_94`.",
            "",
            "A melhora dos ultimos 365 dias e forte, mas 2024 ainda mostra que o setup nao deve ser promovido para oficial sem confirmacao no TradingView.",
            "O ponto bom e que 2024 ficou positivo; o ponto ruim e que o acerto de 2024 ainda esta perto de 71%, abaixo do alvo.",
            "",
            "### Fragilidade 2024 por modulo no perfil recomendado",
            "",
        ]
    )
    linhas.extend(tabela_markdown(por_modulo_2024, ["modulo", "trades", "winrate", "pontos", "dd", "pf"]))
    linhas.extend(
        [
            "",
            "Conclusao provisoria:",
            "",
            "- `02_equilibrado_139_94` e o melhor candidato atual para testar no TradingView.",
            "- O proximo refino deve mirar a melhora de 2024 sem perder a curva recente de 365 dias.",
            "- Se o TradingView divergir muito das primeiras entradas esperadas, a prioridade passa a ser equivalencia de dados/execucao antes de qualquer novo filtro.",
            "",
        ]
    )
    ARQ_MD.write_text("\n".join(linhas), encoding="utf-8")


def main():
    trades = montar_trades()
    gerar_markdown(trades)
    print(ARQ_MD)


if __name__ == "__main__":
    main()
