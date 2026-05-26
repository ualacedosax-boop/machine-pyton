import os
import traceback
import pandas as pd

import sinal_v4_blackarrow_tempo_real as robo


def mostrar_duplicadas(df, nome):
    duplicadas = df.columns[df.columns.duplicated()].tolist()

    print("\n=====================================================")
    print(f"DIAGNOSTICO: {nome}")
    print("=====================================================")
    print("Linhas:", len(df))
    print("Colunas:", len(df.columns))
    print("Duplicadas:", len(duplicadas))

    if duplicadas:
        print("Primeiras duplicadas:")
        print(duplicadas[:50])
    else:
        print("Nenhuma coluna duplicada encontrada.")


def main():
    print("=====================================================")
    print("DIAGNOSTICO ERRO 1-DIMENSIONAL SINAL V4")
    print("=====================================================")

    print("\nCarregando config/modelos...")
    config_v4 = robo.carregar_config_v4()
    modelo_v3, features_v3, config_v3 = robo.carregar_modelo_v3()
    modelo_v4, features_v4 = robo.carregar_modelo_v4()

    print("\nLendo BlackArrow RTD...")
    tick = robo.ler_blackarrow_rtd()
    print(tick)

    print("\nAtualizando ticks...")
    ticks = robo.atualizar_ticks(tick)
    mostrar_duplicadas(ticks, "TICKS")

    print("\nMontando candles...")
    candles = robo.montar_candles_2min(ticks)
    mostrar_duplicadas(candles, "CANDLES 2 MIN")

    print("\nCandles disponíveis:", len(candles))
    print("Últimos candles:")
    print(candles.tail(5).to_string())

    print("\nTestando preparar_features_tempo_real...")
    try:
        df_feat = robo.preparar_features_tempo_real(candles, features_v3, features_v4)
        mostrar_duplicadas(df_feat, "FEATURES TEMPO REAL")

        print("\nFeatures geradas com sucesso.")
        print("Linhas:", len(df_feat))
        print("Colunas:", len(df_feat.columns))

        print("\nTestando preparar_X V3...")
        X_v3, ultima = robo.preparar_X(df_feat, features_v3)
        mostrar_duplicadas(X_v3, "X_V3")

        print("\nTestando calcular_score_v3...")
        score_v3 = robo.calcular_score_v3(modelo_v3, X_v3)
        print(score_v3)

        print("\nTestando montar_X_v4...")
        X_v4 = robo.montar_X_v4(df_feat, ultima, score_v3, features_v4)
        mostrar_duplicadas(X_v4, "X_V4")

        print("\nTestando prob V4...")
        prob = robo.calcular_prob_v4(modelo_v4, X_v4)
        print("prob_win_v4:", prob)

        print("\n=====================================================")
        print("DIAGNOSTICO FINALIZADO SEM ERRO")
        print("=====================================================")

    except Exception as e:
        print("\n=====================================================")
        print("ERRO ENCONTRADO")
        print("=====================================================")
        print("Erro:", e)
        print("\nTRACEBACK COMPLETO:")
        traceback.print_exc()


if __name__ == "__main__":
    main()