import os
import time
import winsound
from datetime import datetime


# =====================================================
# CONFIGURAÇÕES
# =====================================================

ARQUIVO_SINAL = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton\operacional_v4\sinal.txt"

INTERVALO_SEGUNDOS = 1

# Alarme sonoro
FREQUENCIA_BUY = 1200
FREQUENCIA_SELL = 700
DURACAO_BEEP_MS = 500

REPETICOES_ALARME = 5


# =====================================================
# FUNÇÕES
# =====================================================

def ler_sinal():
    if not os.path.exists(ARQUIVO_SINAL):
        return "none"

    try:
        with open(ARQUIVO_SINAL, "r", encoding="utf-8") as f:
            sinal = f.read().strip().lower()

        if sinal not in ["buy", "sell", "none", "close"]:
            return "none"

        return sinal

    except Exception:
        return "none"


def tocar_alarme_buy():
    print("\n🚨🚨🚨 SINAL DE COMPRA - BUY 🚨🚨🚨")
    print("Horário:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for _ in range(REPETICOES_ALARME):
        winsound.Beep(FREQUENCIA_BUY, DURACAO_BEEP_MS)
        time.sleep(0.15)


def tocar_alarme_sell():
    print("\n🚨🚨🚨 SINAL DE VENDA - SELL 🚨🚨🚨")
    print("Horário:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for _ in range(REPETICOES_ALARME):
        winsound.Beep(FREQUENCIA_SELL, DURACAO_BEEP_MS)
        time.sleep(0.15)


def main():
    print("=====================================================")
    print("ALARME DE SINAL V4")
    print("=====================================================")
    print("Monitorando:")
    print(ARQUIVO_SINAL)
    print("\nAguardando BUY ou SELL...")
    print("Para parar: Ctrl + C")
    print("=====================================================")

    ultimo_sinal_alertado = None

    while True:
        sinal = ler_sinal()

        agora = datetime.now().strftime("%H:%M:%S")

        if sinal == "buy" and ultimo_sinal_alertado != "buy":
            tocar_alarme_buy()
            ultimo_sinal_alertado = "buy"

        elif sinal == "sell" and ultimo_sinal_alertado != "sell":
            tocar_alarme_sell()
            ultimo_sinal_alertado = "sell"

        elif sinal == "none":
            ultimo_sinal_alertado = None
            print(f"{agora} | sinal: none", end="\r")

        else:
            print(f"{agora} | sinal: {sinal}", end="\r")

        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()