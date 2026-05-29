from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
PESQUISA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"

ARQ_CANDIDATOS = PESQUISA_DIR / "01_candidatos_6min_0230_0600.csv.gz"
ARQ_ML = PESQUISA_DIR / "03_resultado_ml_walkforward.csv"
ARQ_SAIDA_XLSX = PESQUISA_DIR / "validacao_top_candidatos_mensal.xlsx"
ARQ_SAIDA_CSV = PESQUISA_DIR / "validacao_top_candidatos_resumo.csv"
ARQ_TRADES = PESQUISA_DIR / "validacao_top_candidatos_trades.csv"


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


def resumir(trades, nome, extra=None):
    extra = extra or {}
    if trades.empty:
        row = {
            "nome": nome,
            "trades": 0,
            "takes": 0,
            "stops": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "media_pontos": 0.0,
            "dias_operados": 0,
        }
        row.update(extra)
        return row

    pontos = trades["pontos"].astype(float)
    row = {
        "nome": nome,
        "trades": int(len(trades)),
        "takes": int((trades["resultado"] == "TAKE").sum()),
        "stops": int((trades["resultado"] == "STOP").sum()),
        "winrate": float((trades["resultado"] == "TAKE").mean() * 100.0),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "dias_operados": int(pd.to_datetime(trades["DataHora_SP"]).dt.date.nunique()),
    }
    row.update(extra)
    return row


def carregar_candidatos():
    if not ARQ_CANDIDATOS.exists():
        raise FileNotFoundError(f"Nao encontrei {ARQ_CANDIDATOS}. Rode pesquisar_operacional_0348_6min.py primeiro.")

    df = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
    df["DataHora_SP"] = pd.to_datetime(df["DataHora_SP"], errors="coerce")
    df["DataHora_saida"] = pd.to_datetime(df["DataHora_saida"], errors="coerce")
    df = df.dropna(subset=["DataHora_SP"]).copy()
    df["ano"] = df["DataHora_SP"].dt.year
    df["mes"] = df["DataHora_SP"].dt.to_period("M").astype(str)
    df["data"] = df["DataHora_SP"].dt.date
    return df


def selecionar_regra_0406_reversao(candidatos):
    trades = candidatos[
        (candidatos["setup"] == "V71_OFICIAL_505_117")
        & (candidatos["hhmm"] == "04:06")
        & (candidatos["direcao_reversao_20"].isin(["BUY", "SELL"]))
        & (candidatos["Direcao"] == candidatos["direcao_reversao_20"])
    ].copy()

    trades["modelo_origem"] = "REGRA_0406_REVERSAO_505_117"
    trades["nome_candidato"] = "04:06 reversao 50.5/117"
    return trades.sort_values("DataHora_SP").reset_index(drop=True)


def modelos_ml():
    from sklearn.impute import SimpleImputer
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", MLPClassifier(hidden_layer_sizes=(32, 16), alpha=0.01, max_iter=500, random_state=42)),
    ])


def colunas_features(df):
    out = df.copy()
    excluir = {
        "DataHora_SP", "DataHora_saida", "Data", "data", "mes", "hhmm",
        "resultado", "pontos", "target_win", "Direcao", "setup",
        "preco_saida", "modelo_origem", "nome_candidato", "eh_0348",
    }
    out["dir_buy"] = (out["Direcao"] == "BUY").astype(int)
    out["dir_sell"] = (out["Direcao"] == "SELL").astype(int)
    cols = [c for c in out.columns if c not in excluir and pd.api.types.is_numeric_dtype(out[c])]
    return out, cols


def selecionar_ml_139ticks_mlp(candidatos, threshold=0.55):
    base = candidatos[candidatos["setup"] == "TS_139TICKS_SIMETRICO"].copy()
    base, feats = colunas_features(base)

    folds = [
        {
            "nome_fold": "treina_2024_testa_2025",
            "anos_treino": [2024],
            "ano_teste": 2025,
        },
        {
            "nome_fold": "treina_2024_2025_testa_2026",
            "anos_treino": [2024, 2025],
            "ano_teste": 2026,
        },
    ]

    escolhidos = []
    for fold in folds:
        treino = base[base["ano"].isin(fold["anos_treino"])].dropna(subset=["target_win"]).copy()
        teste = base[base["ano"] == fold["ano_teste"]].dropna(subset=["target_win"]).copy()

        if len(treino) < 100 or len(teste) < 20 or treino["target_win"].nunique() < 2:
            continue

        modelo = modelos_ml()
        modelo.fit(treino[feats], treino["target_win"].astype(int))
        teste["prob_win_ml"] = modelo.predict_proba(teste[feats])[:, 1]
        teste = (
            teste[teste["prob_win_ml"] >= threshold]
            .sort_values(["data", "prob_win_ml"], ascending=[True, False])
            .groupby("data", as_index=False)
            .head(1)
            .sort_values("DataHora_SP")
        )
        teste["modelo_origem"] = f"MLP_139TICKS_TH_{threshold}"
        teste["nome_candidato"] = f"MLP 139 ticks threshold {threshold}"
        teste["fold"] = fold["nome_fold"]
        escolhidos.append(teste)

    if not escolhidos:
        return pd.DataFrame()

    return pd.concat(escolhidos, ignore_index=True).sort_values("DataHora_SP").reset_index(drop=True)


def resumo_por_periodo(trades):
    linhas = []
    for nome, g_nome in trades.groupby("nome_candidato"):
        linhas.append(resumir(g_nome, nome, {"periodo": "TOTAL"}))

        for ano, g_ano in g_nome.groupby("ano"):
            linhas.append(resumir(g_ano, nome, {"periodo": str(int(ano)), "ano": int(ano)}))

        for mes, g_mes in g_nome.groupby("mes"):
            linhas.append(resumir(g_mes, nome, {"periodo": mes, "ano": int(str(mes)[:4]), "mes": mes}))

    return pd.DataFrame(linhas)


def resumo_meses_negativos(resumo):
    mensal = resumo[resumo["periodo"].astype(str).str.match(r"^\d{4}-\d{2}$", na=False)].copy()
    if mensal.empty:
        return pd.DataFrame()

    linhas = []
    for nome, g in mensal.groupby("nome"):
        linhas.append({
            "nome": nome,
            "meses_total": int(len(g)),
            "meses_positivos": int((g["pontos"] > 0).sum()),
            "meses_negativos": int((g["pontos"] < 0).sum()),
            "pior_mes": float(g["pontos"].min()),
            "melhor_mes": float(g["pontos"].max()),
            "media_mensal": float(g["pontos"].mean()),
            "mediana_mensal": float(g["pontos"].median()),
        })
    return pd.DataFrame(linhas).sort_values(["meses_negativos", "media_mensal"], ascending=[True, False])


def main():
    print("=====================================================")
    print("VALIDACAO MENSAL - TOP CANDIDATOS PESQUISA V7.1")
    print("Nao altera o robo oficial.")
    print("=====================================================")

    candidatos = carregar_candidatos()
    print("Candidatos carregados:", len(candidatos))

    regra = selecionar_regra_0406_reversao(candidatos)
    print("Trades regra 04:06:", len(regra))

    ml = selecionar_ml_139ticks_mlp(candidatos, threshold=0.55)
    print("Trades ML MLP 139 ticks:", len(ml))

    trades = pd.concat([regra, ml], ignore_index=True).sort_values("DataHora_SP")
    resumo = resumo_por_periodo(trades)
    meses = resumo_meses_negativos(resumo)

    trades.to_csv(ARQ_TRADES, index=False)
    resumo.to_csv(ARQ_SAIDA_CSV, index=False)

    with pd.ExcelWriter(ARQ_SAIDA_XLSX, engine="openpyxl") as writer:
        resumo.to_excel(writer, sheet_name="resumo_periodos", index=False)
        meses.to_excel(writer, sheet_name="qualidade_mensal", index=False)
        trades.to_excel(writer, sheet_name="trades", index=False)

    print("\nRESUMO TOTAL")
    totais = resumo[resumo["periodo"] == "TOTAL"].copy()
    print(totais[["nome", "trades", "winrate", "pontos", "max_drawdown", "profit_factor"]].to_string(index=False))

    print("\nQUALIDADE MENSAL")
    print(meses.to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_SAIDA_XLSX)
    print(ARQ_SAIDA_CSV)
    print(ARQ_TRADES)


if __name__ == "__main__":
    main()
