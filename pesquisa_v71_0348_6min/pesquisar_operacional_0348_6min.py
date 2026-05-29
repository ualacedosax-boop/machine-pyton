from pathlib import Path
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


BASE_DIR = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
SAIDA_DIR = BASE_DIR / "pesquisa_v71_0348_6min"
SAIDA_DIR.mkdir(parents=True, exist_ok=True)

ARQ_CANDIDATOS = SAIDA_DIR / "01_candidatos_6min_0230_0600.csv.gz"
ARQ_REGRAS = SAIDA_DIR / "02_resultado_regras_horario_indicadores.csv"
ARQ_ML = SAIDA_DIR / "03_resultado_ml_walkforward.csv"
ARQ_TRADES_MELHORES = SAIDA_DIR / "04_trades_melhores_modelos.csv"
ARQ_XLSX = SAIDA_DIR / "pesquisa_operacional_0348_6min.xlsx"

TIMEZONE_SP = "America/Sao_Paulo"
HORARIO_INICIO = "02:30"
HORARIO_FIM = "06:00"
HORARIO_REFERENCIA = "03:48"
MAX_CANDLES_FUTURO = 160

SETUPS_TAKE_STOP = [
    {"setup": "TS_139TICKS_SIMETRICO", "take": 34.75, "stop": 34.75},
    {"setup": "V71_OFICIAL_505_117", "take": 50.5, "stop": 117.0},
    {"setup": "V71_STOP90", "take": 50.5, "stop": 90.0},
]


def minutos_hhmm(hhmm):
    h, m = str(hhmm).split(":")
    return int(h) * 60 + int(m)


def max_drawdown(pontos):
    if len(pontos) == 0:
        return 0.0
    eq = np.cumsum(np.asarray(pontos, dtype=float))
    pico = np.maximum.accumulate(eq)
    dd = eq - pico
    return float(dd.min())


def profit_factor(pontos):
    pontos = pd.Series(pontos, dtype=float)
    ganhos = float(pontos[pontos > 0].sum())
    perdas = abs(float(pontos[pontos < 0].sum()))
    if perdas == 0:
        return 999.0 if ganhos > 0 else 0.0
    return ganhos / perdas


def resumir_trades(trades, nome, grupo_extra=None):
    if trades.empty:
        return {
            "nome": nome,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0.0,
            "pontos": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "media_pontos": 0.0,
        }

    wins = int((trades["resultado"] == "TAKE").sum())
    losses = int((trades["resultado"] == "STOP").sum())
    pontos = trades["pontos"].astype(float)
    row = {
        "nome": nome,
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "winrate": float(wins / len(trades) * 100.0),
        "pontos": float(pontos.sum()),
        "max_drawdown": max_drawdown(pontos),
        "profit_factor": profit_factor(pontos),
        "media_pontos": float(pontos.mean()),
        "dias_operados": int(pd.to_datetime(trades["DataHora_SP"]).dt.date.nunique()),
    }
    if grupo_extra:
        row.update(grupo_extra)
    return row


def normalizar_ohlcv(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if "DataHora_SP" in df.columns:
        dt = pd.to_datetime(df["DataHora_SP"], errors="coerce")
        if getattr(dt.dt, "tz", None) is not None:
            dt = dt.dt.tz_convert(TIMEZONE_SP).dt.tz_localize(None)
    elif "date" in df.columns:
        dt = pd.to_datetime(df["date"], errors="coerce", utc=True)
        dt = dt.dt.tz_convert(TIMEZONE_SP).dt.tz_localize(None)
    elif "DataHora" in df.columns:
        dt = pd.to_datetime(df["DataHora"], errors="coerce")
    else:
        raise RuntimeError("Nao encontrei coluna de data/hora.")

    df["DataHora_SP"] = dt
    df = df.dropna(subset=["DataHora_SP"]).sort_values("DataHora_SP")

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            if col == "volume":
                df[col] = 0.0
            else:
                raise RuntimeError(f"Coluna obrigatoria ausente: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])
    return df[["DataHora_SP", "open", "high", "low", "close", "volume"]].copy()


def carregar_dados():
    arquivos = [
        BASE_DIR / "dados_mnq_2024_ibkr" / "MNQ_2024_2MIN_IBKR_CONTINUO.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQH5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQM5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQU5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2025_ibkr" / "MNQZ5_1MIN_IBKR.csv",
        BASE_DIR / "dados_mnq_2026_ibkr" / "MNQ_2026_2MIN_IBKR_CONTINUO.csv",
    ]

    partes = []
    usados = []
    for arq in arquivos:
        if not arq.exists():
            continue
        df = pd.read_csv(arq, low_memory=False)
        partes.append(normalizar_ohlcv(df))
        usados.append(str(arq))

    if not partes:
        raise FileNotFoundError("Nenhum arquivo MNQ 2024/2025/2026 foi encontrado.")

    candles = pd.concat(partes, ignore_index=True)
    candles = candles.drop_duplicates(subset=["DataHora_SP"]).sort_values("DataHora_SP")
    candles = candles[(candles["DataHora_SP"].dt.year >= 2024) & (candles["DataHora_SP"].dt.year <= 2026)].copy()

    print("Arquivos usados:")
    for arq in usados:
        print(" -", arq)
    print("Candles base:", len(candles), candles["DataHora_SP"].min(), candles["DataHora_SP"].max())
    return candles


def resample_6min(candles):
    df = candles.set_index("DataHora_SP").sort_index()
    out = df.resample("6min", origin="start_day", label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index()
    out["Data"] = out["DataHora_SP"].dt.date
    out["hhmm"] = out["DataHora_SP"].dt.strftime("%H:%M")
    out["minuto_dia"] = out["DataHora_SP"].dt.hour * 60 + out["DataHora_SP"].dt.minute
    out["ano"] = out["DataHora_SP"].dt.year
    return out


def adicionar_features(df):
    out = df.copy()
    out["ret_1"] = out["close"].diff()
    out["ret_2"] = out["close"].diff(2)
    out["ret_3"] = out["close"].diff(3)
    out["ret_5"] = out["close"].diff(5)
    out["range"] = out["high"] - out["low"]
    out["body"] = out["close"] - out["open"]
    out["body_abs"] = out["body"].abs()
    out["upper_wick"] = out["high"] - out[["open", "close"]].max(axis=1)
    out["lower_wick"] = out[["open", "close"]].min(axis=1) - out["low"]

    for n in [3, 5, 10, 20, 40]:
        out[f"ema_{n}"] = out["close"].ewm(span=n, adjust=False).mean()
        out[f"slope_ema_{n}"] = out[f"ema_{n}"].diff()
        out[f"dist_ema_{n}"] = out["close"] - out[f"ema_{n}"]
        out[f"range_med_{n}"] = out["range"].rolling(n).mean()
        out[f"vol_med_{n}"] = out["volume"].rolling(n).mean()

    delta = out["close"].diff()
    ganho = delta.clip(lower=0).rolling(14).mean()
    perda = (-delta.clip(upper=0)).rolling(14).mean()
    rs = ganho / perda.replace(0, np.nan)
    out["rsi_14"] = 100 - (100 / (1 + rs))

    out["max_20"] = out["high"].rolling(20).max()
    out["min_20"] = out["low"].rolling(20).min()
    out["pos_range_20"] = (out["close"] - out["min_20"]) / (out["max_20"] - out["min_20"]).replace(0, np.nan)

    por_dia = out.groupby("Data", group_keys=False)
    out["open_dia"] = por_dia["open"].transform("first")
    out["max_dia_ate_agora"] = por_dia["high"].cummax()
    out["min_dia_ate_agora"] = por_dia["low"].cummin()
    out["dist_open_dia"] = out["close"] - out["open_dia"]
    out["dist_max_dia"] = out["close"] - out["max_dia_ate_agora"]
    out["dist_min_dia"] = out["close"] - out["min_dia_ate_agora"]

    out["direcao_tendencia"] = np.where(out["close"] >= out["ema_20"], "BUY", "SELL")
    out["direcao_reversao_20"] = np.where(out["pos_range_20"] <= 0.35, "BUY", np.where(out["pos_range_20"] >= 0.65, "SELL", "NONE"))
    out["direcao_candle"] = np.where(out["body"] >= 0, "BUY", "SELL")
    out["direcao_rompimento"] = np.where(out["close"] >= out["max_20"].shift(1), "BUY", np.where(out["close"] <= out["min_20"].shift(1), "SELL", "NONE"))
    return out


def simular_trade(base, idx, direcao, take, stop):
    entrada = float(base.at[idx, "close"])
    data_entrada = base.at[idx, "Data"]
    futuro = base.iloc[idx + 1: idx + 1 + MAX_CANDLES_FUTURO]
    futuro = futuro[futuro["Data"] == data_entrada]
    if futuro.empty:
        return None

    if direcao == "BUY":
        preco_take = entrada + take
        preco_stop = entrada - stop
        for row in futuro.itertuples():
            tocou_stop = float(row.low) <= preco_stop
            tocou_take = float(row.high) >= preco_take
            if tocou_stop:
                return "STOP", -stop, row.DataHora_SP, preco_stop
            if tocou_take:
                return "TAKE", take, row.DataHora_SP, preco_take

    if direcao == "SELL":
        preco_take = entrada - take
        preco_stop = entrada + stop
        for row in futuro.itertuples():
            tocou_stop = float(row.high) >= preco_stop
            tocou_take = float(row.low) <= preco_take
            if tocou_stop:
                return "STOP", -stop, row.DataHora_SP, preco_stop
            if tocou_take:
                return "TAKE", take, row.DataHora_SP, preco_take

    return None


def montar_candidatos(candles_6):
    inicio = minutos_hhmm(HORARIO_INICIO)
    fim = minutos_hhmm(HORARIO_FIM)
    base = candles_6.reset_index(drop=True).copy()
    idxs = base[(base["minuto_dia"] >= inicio) & (base["minuto_dia"] <= fim)].index.tolist()

    linhas = []
    for idx in idxs:
        row = base.loc[idx]
        for setup in SETUPS_TAKE_STOP:
            for direcao in ["BUY", "SELL"]:
                sim = simular_trade(base, idx, direcao, setup["take"], setup["stop"])
                if sim is None:
                    continue
                resultado, pontos, saida, preco_saida = sim
                r = row.to_dict()
                r.update({
                    "setup": setup["setup"],
                    "take": setup["take"],
                    "stop": setup["stop"],
                    "Direcao": direcao,
                    "resultado": resultado,
                    "pontos": float(pontos),
                    "DataHora_saida": saida,
                    "preco_saida": preco_saida,
                    "preco_entrada": float(row["close"]),
                    "target_win": 1 if resultado == "TAKE" else 0,
                    "eh_0348": str(row["hhmm"]) == HORARIO_REFERENCIA,
                })
                linhas.append(r)

    candidatos = pd.DataFrame(linhas)
    candidatos = candidatos.replace([np.inf, -np.inf], np.nan)
    return candidatos


def avaliar_regras(candidatos):
    linhas = []
    trades_melhores = []

    regras = {
        "fixo_por_direcao": None,
        "direcao_tendencia": "direcao_tendencia",
        "direcao_reversao_20": "direcao_reversao_20",
        "direcao_candle": "direcao_candle",
        "direcao_rompimento": "direcao_rompimento",
    }

    for setup, df_setup in candidatos.groupby("setup"):
        for hhmm, df_hora in df_setup.groupby("hhmm"):
            for nome_regra, col_regra in regras.items():
                if col_regra is None:
                    for direcao in ["BUY", "SELL"]:
                        trades = df_hora[df_hora["Direcao"] == direcao].copy()
                        row = resumir_trades(trades, f"{setup}_{hhmm}_{nome_regra}_{direcao}", {
                            "setup": setup,
                            "hhmm": hhmm,
                            "regra": nome_regra,
                            "Direcao": direcao,
                        })
                        linhas.append(row)
                else:
                    trades = df_hora[df_hora["Direcao"] == df_hora[col_regra]].copy()
                    trades = trades[trades[col_regra].isin(["BUY", "SELL"])].copy()
                    row = resumir_trades(trades, f"{setup}_{hhmm}_{nome_regra}", {
                        "setup": setup,
                        "hhmm": hhmm,
                        "regra": nome_regra,
                        "Direcao": "PELA_REGRA",
                    })
                    linhas.append(row)

    resumo = pd.DataFrame(linhas)
    resumo = resumo.sort_values(["pontos", "profit_factor", "winrate", "trades"], ascending=[False, False, False, False])

    for _, best in resumo.head(10).iterrows():
        g = candidatos[(candidatos["setup"] == best["setup"]) & (candidatos["hhmm"] == best["hhmm"])].copy()
        if best["regra"] == "fixo_por_direcao":
            g = g[g["Direcao"] == best["Direcao"]].copy()
        else:
            col = best["regra"]
            g = g[g["Direcao"] == g[col]].copy()
        g["modelo_origem"] = "REGRA"
        g["nome_resultado"] = best["nome"]
        trades_melhores.append(g)

    return resumo, pd.concat(trades_melhores, ignore_index=True) if trades_melhores else pd.DataFrame()


def modelos_ml():
    from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "LogisticRegression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]),
        "RandomForest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(
                n_estimators=500, max_depth=7, min_samples_leaf=8,
                class_weight="balanced_subsample", random_state=42, n_jobs=-1
            )),
        ]),
        "ExtraTrees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=500, max_depth=7, min_samples_leaf=8,
                class_weight="balanced", random_state=42, n_jobs=-1
            )),
        ]),
        "HistGradientBoosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingClassifier(max_iter=250, max_leaf_nodes=15, random_state=42)),
        ]),
        "RedeNeural_MLP": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", MLPClassifier(hidden_layer_sizes=(32, 16), alpha=0.01, max_iter=500, random_state=42)),
        ]),
    }


def colunas_features(candidatos):
    excluir = {
        "DataHora_SP", "Data", "hhmm", "DataHora_saida", "resultado", "pontos", "target_win",
        "Direcao", "setup", "preco_saida", "eh_0348",
    }
    cols = []
    for c in candidatos.columns:
        if c in excluir:
            continue
        if pd.api.types.is_numeric_dtype(candidatos[c]):
            cols.append(c)
    candidatos["dir_buy"] = (candidatos["Direcao"] == "BUY").astype(int)
    candidatos["dir_sell"] = (candidatos["Direcao"] == "SELL").astype(int)
    cols += ["dir_buy", "dir_sell"]
    return cols


def avaliar_ml(candidatos):
    try:
        modelos = modelos_ml()
    except Exception as e:
        print("ML indisponivel:", e)
        return pd.DataFrame(), pd.DataFrame()

    candidatos = candidatos.copy()
    feats = colunas_features(candidatos)
    thresholds = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    folds = [
        ("treina_2024_testa_2025", [2024], 2025),
        ("treina_2024_2025_testa_2026", [2024, 2025], 2026),
    ]

    linhas = []
    trades_melhores = []

    for setup, df_setup in candidatos.groupby("setup"):
        for nome_fold, anos_treino, ano_teste in folds:
            treino = df_setup[df_setup["ano"].isin(anos_treino)].dropna(subset=["target_win"]).copy()
            teste = df_setup[df_setup["ano"] == ano_teste].dropna(subset=["target_win"]).copy()

            if len(treino) < 100 or len(teste) < 20 or treino["target_win"].nunique() < 2:
                continue

            X_train = treino[feats]
            y_train = treino["target_win"].astype(int)
            X_test = teste[feats]

            for nome_modelo, modelo in modelos.items():
                try:
                    modelo.fit(X_train, y_train)
                    if hasattr(modelo, "predict_proba"):
                        prob = modelo.predict_proba(X_test)[:, 1]
                    else:
                        prob = modelo.decision_function(X_test)
                    pred = teste.copy()
                    pred["prob_win_ml"] = prob
                except Exception as e:
                    print(f"Falha ML {nome_modelo} {setup} {nome_fold}: {e}")
                    continue

                for threshold in thresholds:
                    escolhidos = (
                        pred[pred["prob_win_ml"] >= threshold]
                        .sort_values(["Data", "prob_win_ml"], ascending=[True, False])
                        .groupby("Data", as_index=False)
                        .head(1)
                        .sort_values("DataHora_SP")
                    )

                    row = resumir_trades(escolhidos, f"{setup}_{nome_fold}_{nome_modelo}_{threshold}", {
                        "setup": setup,
                        "fold": nome_fold,
                        "modelo": nome_modelo,
                        "threshold": threshold,
                        "feature_count": len(feats),
                        "ano_teste": ano_teste,
                    })
                    linhas.append(row)

    resumo = pd.DataFrame(linhas)
    if resumo.empty:
        return resumo, pd.DataFrame()

    resumo = resumo.sort_values(["pontos", "profit_factor", "winrate", "trades"], ascending=[False, False, False, False])

    # Reconstroi trades dos melhores modelos para auditoria.
    for _, row in resumo.head(10).iterrows():
        setup = row["setup"]
        nome_fold = row["fold"]
        threshold = row["threshold"]
        nome_modelo = row["modelo"]
        anos_treino = [2024] if nome_fold == "treina_2024_testa_2025" else [2024, 2025]
        ano_teste = int(row["ano_teste"])
        df_setup = candidatos[candidatos["setup"] == setup].copy()
        treino = df_setup[df_setup["ano"].isin(anos_treino)].copy()
        teste = df_setup[df_setup["ano"] == ano_teste].copy()
        modelo = modelos[nome_modelo]
        modelo.fit(treino[feats], treino["target_win"].astype(int))
        teste["prob_win_ml"] = modelo.predict_proba(teste[feats])[:, 1]
        escolhidos = (
            teste[teste["prob_win_ml"] >= threshold]
            .sort_values(["Data", "prob_win_ml"], ascending=[True, False])
            .groupby("Data", as_index=False)
            .head(1)
            .sort_values("DataHora_SP")
        )
        escolhidos["modelo_origem"] = "ML"
        escolhidos["nome_resultado"] = row["nome"]
        trades_melhores.append(escolhidos)

    return resumo, pd.concat(trades_melhores, ignore_index=True) if trades_melhores else pd.DataFrame()


def salvar_excel(regras, ml, trades):
    with pd.ExcelWriter(ARQ_XLSX, engine="openpyxl") as writer:
        regras.to_excel(writer, sheet_name="regras", index=False)
        ml.to_excel(writer, sheet_name="ml_walkforward", index=False)
        trades.to_excel(writer, sheet_name="trades_melhores", index=False)

        resumo = []
        if not regras.empty:
            r = regras.iloc[0].to_dict()
            r["tipo"] = "melhor_regra"
            resumo.append(r)
        if not ml.empty:
            r = ml.iloc[0].to_dict()
            r["tipo"] = "melhor_ml"
            resumo.append(r)
        pd.DataFrame(resumo).to_excel(writer, sheet_name="resumo_top", index=False)


def main():
    print("==========================================================")
    print("PESQUISA ISOLADA V7.1 - 03:48 / 6 MIN / ML")
    print("Nao altera o robo oficial.")
    print("==========================================================")

    if ARQ_CANDIDATOS.exists():
        print("Reaproveitando candidatos ja gerados:")
        print(ARQ_CANDIDATOS)
        candidatos = pd.read_csv(ARQ_CANDIDATOS, compression="gzip", low_memory=False)
        candidatos["DataHora_SP"] = pd.to_datetime(candidatos["DataHora_SP"], errors="coerce")
        candidatos["DataHora_saida"] = pd.to_datetime(candidatos["DataHora_saida"], errors="coerce")
        candidatos["Data"] = pd.to_datetime(candidatos["DataHora_SP"]).dt.date
    else:
        candles = carregar_dados()
        candles_6 = adicionar_features(resample_6min(candles))
        print("Candles 6min:", len(candles_6), candles_6["DataHora_SP"].min(), candles_6["DataHora_SP"].max())

        candidatos = montar_candidatos(candles_6)
        candidatos.to_csv(ARQ_CANDIDATOS, index=False, compression="gzip")

    print("Candidatos simulados:", len(candidatos))

    regras, trades_regras = avaliar_regras(candidatos)
    regras.to_csv(ARQ_REGRAS, index=False)

    ml, trades_ml = avaliar_ml(candidatos)
    ml.to_csv(ARQ_ML, index=False)

    trades = pd.concat([trades_regras, trades_ml], ignore_index=True) if not trades_regras.empty or not trades_ml.empty else pd.DataFrame()
    trades.to_csv(ARQ_TRADES_MELHORES, index=False)
    salvar_excel(regras, ml, trades)

    print("\nTOP 10 REGRAS")
    if not regras.empty:
        cols = ["setup", "hhmm", "regra", "Direcao", "trades", "winrate", "pontos", "max_drawdown", "profit_factor"]
        print(regras[cols].head(10).to_string(index=False))

    print("\nTOP 10 ML")
    if not ml.empty:
        cols = ["setup", "fold", "modelo", "threshold", "trades", "winrate", "pontos", "max_drawdown", "profit_factor"]
        print(ml[cols].head(10).to_string(index=False))

    print("\nArquivos gerados:")
    print(ARQ_CANDIDATOS)
    print(ARQ_REGRAS)
    print(ARQ_ML)
    print(ARQ_TRADES_MELHORES)
    print(ARQ_XLSX)


if __name__ == "__main__":
    main()
