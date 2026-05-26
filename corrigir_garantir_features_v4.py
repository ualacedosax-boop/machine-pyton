import os
import re
from datetime import datetime


BASE_DIR = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"
ARQUIVO = os.path.join(BASE_DIR, "sinal_v4_blackarrow_tempo_real.py")


NOVA_FUNCAO = r'''def garantir_features_esperadas(base, features_esperadas):
    """
    Garante que todas as features esperadas existam e que cada uma seja 1-dimensional.
    Corrige erro:
    Data must be 1-dimensional, got ndarray of shape (..., 2)
    """

    # Remove qualquer coluna duplicada antes de criar features faltantes.
    base = base.loc[:, ~base.columns.duplicated()].copy()

    aliases = {
        "hora_sp": "Hora_SP_Decimal",
        "dia_semana_sp": "dia_semana",
        "mes_sp": "mes",
        "sin_hora_sp": "sin_hora",
        "cos_hora_sp": "cos_hora",
    }

    def pegar_coluna_1d(df, nome):
        """
        Retorna sempre uma Series 1D.
        Se por algum motivo vier DataFrame com colunas duplicadas, pega a primeira.
        """
        if nome not in df.columns:
            return None

        valor = df[nome]

        if isinstance(valor, pd.DataFrame):
            valor = valor.iloc[:, 0]

        return pd.Series(valor, index=df.index)

    novas = {}

    # Remove duplicidade também da lista de features esperadas.
    features_unicas = []
    vistas = set()

    for f in features_esperadas:
        if f not in vistas:
            features_unicas.append(f)
            vistas.add(f)

    for feature in features_unicas:
        if feature in base.columns:
            continue

        valor_final = None

        if feature.startswith("prev_"):
            sem_prev = feature[5:]

            col = pegar_coluna_1d(base, sem_prev)

            if col is not None:
                valor_final = col.shift(1)

            elif sem_prev in aliases:
                alias = aliases[sem_prev]
                col_alias = pegar_coluna_1d(base, alias)

                if col_alias is not None:
                    valor_final = col_alias.shift(1)

        else:
            if feature in aliases:
                alias = aliases[feature]
                col_alias = pegar_coluna_1d(base, alias)

                if col_alias is not None:
                    valor_final = col_alias

        if valor_final is None:
            valor_final = pd.Series(np.nan, index=base.index)

        # Garantia final: nunca deixar entrar 2D no dicionário.
        if isinstance(valor_final, pd.DataFrame):
            valor_final = valor_final.iloc[:, 0]

        valor_final = pd.Series(valor_final, index=base.index)

        novas[feature] = valor_final

    if novas:
        novas_df = pd.DataFrame(novas, index=base.index)
        novas_df = novas_df.loc[:, ~novas_df.columns.duplicated()].copy()

        base = pd.concat([base, novas_df], axis=1)
        base = base.loc[:, ~base.columns.duplicated()].copy()

    return base.copy()


'''


def main():
    if not os.path.exists(ARQUIVO):
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO}")

    with open(ARQUIVO, "r", encoding="utf-8") as f:
        codigo = f.read()

    backup = ARQUIVO.replace(
        ".py",
        f"_backup_antes_corrigir_garantir_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    )

    with open(backup, "w", encoding="utf-8") as f:
        f.write(codigo)

    print("Backup criado:")
    print(backup)

    padrao = r"def garantir_features_esperadas\(base, features_esperadas\):.*?\n\ndef preparar_features_tempo_real"

    novo_codigo, qtd = re.subn(
        padrao,
        NOVA_FUNCAO + "\ndef preparar_features_tempo_real",
        codigo,
        flags=re.DOTALL
    )

    if qtd == 0:
        raise RuntimeError("Não consegui localizar a função garantir_features_esperadas para substituir.")

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        f.write(novo_codigo)

    print("Função garantir_features_esperadas substituída com sucesso.")
    print("Arquivo corrigido:")
    print(ARQUIVO)


if __name__ == "__main__":
    main()