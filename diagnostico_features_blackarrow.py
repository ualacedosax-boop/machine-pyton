import os
import joblib
import pandas as pd
import numpy as np


BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

PASTA_V3 = os.path.join(BASE_DIR, "saida_ml_entradas_video_v3")
PASTA_OPERACIONAL = os.path.join(BASE_DIR, "operacional_v4")

ARQUIVO_FEATURES_V3 = os.path.join(PASTA_V3, "features_v3_score.joblib")
ARQUIVO_IMPORTANCIA_V3 = os.path.join(PASTA_V3, "04_v3_importancia_features.csv")

ARQUIVO_CANDLES = os.path.join(PASTA_OPERACIONAL, "blackarrow_candles_2min.csv")
ARQUIVO_FEATURES_TEMPO_REAL = os.path.join(PASTA_OPERACIONAL, "features_blackarrow_tempo_real.csv")
ARQUIVO_LOG = os.path.join(PASTA_OPERACIONAL, "log_sinal_v4_blackarrow.csv")

ARQUIVO_SAIDA_DIAGNOSTICO = os.path.join(PASTA_OPERACIONAL, "diagnostico_features_blackarrow.csv")


def carregar_csv(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    return pd.read_csv(caminho)


def main():
    print("=====================================================")
    print("DIAGNÓSTICO FEATURES BLACKARROW")
    print("=====================================================")

    features_v3 = joblib.load(ARQUIVO_FEATURES_V3)
    print("Features esperadas pelo V3:", len(features_v3))

    candles = carregar_csv(ARQUIVO_CANDLES)
    features_rt = carregar_csv(ARQUIVO_FEATURES_TEMPO_REAL)
    log = carregar_csv(ARQUIVO_LOG)

    print("\nCandles BlackArrow:", len(candles))
    print("Features tempo real:", len(features_rt))
    print("Log:", len(log))

    print("\nÚltimos 5 candles:")
    print(candles.tail(5).to_string())

    ultima = features_rt.iloc[-1]

    faltando = []
    nan_cols = []
    validas = []

    for col in features_v3:
        if col not in features_rt.columns:
            faltando.append(col)
        else:
            val = ultima[col]
            if pd.isna(val):
                nan_cols.append(col)
            else:
                validas.append(col)

    print("\n=====================================================")
    print("RESUMO DAS FEATURES V3 NO ÚLTIMO CANDLE")
    print("=====================================================")
    print("Features esperadas:", len(features_v3))
    print("Features faltando:", len(faltando))
    print("Features com NaN:", len(nan_cols))
    print("Features válidas:", len(validas))

    pct_validas = len(validas) / len(features_v3) * 100
    print(f"% válidas: {pct_validas:.2f}%")

    print("\nPrimeiras 50 features faltando:")
    print(faltando[:50])

    print("\nPrimeiras 50 features com NaN:")
    print(nan_cols[:50])

    # Importância das features
    if os.path.exists(ARQUIVO_IMPORTANCIA_V3):
        imp = pd.read_csv(ARQUIVO_IMPORTANCIA_V3)

        col_feature = None
        col_importancia = None

        for c in imp.columns:
            if c.lower().strip() in ["feature", "features", "coluna"]:
                col_feature = c
            if c.lower().strip() in ["importancia", "importance"]:
                col_importancia = c

        if col_feature is not None:
            print("\n=====================================================")
            print("TOP 50 FEATURES IMPORTANTES E VALORES NO ÚLTIMO CANDLE")
            print("=====================================================")

            if col_importancia is not None:
                imp = imp.sort_values(col_importancia, ascending=False)

            registros = []

            for _, row in imp.head(100).iterrows():
                feature = row[col_feature]

                if feature in features_rt.columns:
                    valor = ultima[feature]
                    status = "OK" if not pd.isna(valor) else "NaN"
                else:
                    valor = np.nan
                    status = "FALTANDO"

                importancia = row[col_importancia] if col_importancia is not None else np.nan

                registros.append({
                    "feature": feature,
                    "importancia": importancia,
                    "valor_ultimo_candle": valor,
                    "status": status,
                })

            diag = pd.DataFrame(registros)
            print(diag.head(50).to_string(index=False))

            diag.to_csv(ARQUIVO_SAIDA_DIAGNOSTICO, index=False, encoding="utf-8-sig")
            print("\nDiagnóstico salvo em:")
            print(ARQUIVO_SAIDA_DIAGNOSTICO)

    print("\n=====================================================")
    print("ÚLTIMOS 20 REGISTROS DO LOG")
    print("=====================================================")

    cols = [
        "datahora_execucao",
        "sinal",
        "motivo",
        "datahora_ultimo_candle_sp",
        "preco_close",
        "prob_win_v4",
        "Direcao",
        "score_BUY",
        "score_SELL",
        "score_NONE",
        "candles_disponiveis",
    ]

    cols_existentes = [c for c in cols if c in log.columns]

    print(log[cols_existentes].tail(20).to_string(index=False))

    print("\nFINALIZADO.")


if __name__ == "__main__":
    main()