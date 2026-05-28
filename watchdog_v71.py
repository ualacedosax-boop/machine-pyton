# -*- coding: utf-8 -*-
"""
WATCHDOG V7.1 - Monitor de saude do sistema
Verifica a cada 30 segundos se:
  1. O blackarrow_rtd.csv esta sendo atualizado
  2. O robo esta gerando sinais (ultimo_sinal_v71_blackarrow.json)
  3. Os candles estao frescos

Se detectar problema, emite alarme sonoro e mostra aviso na tela.

USO: python watchdog_v71.py
     (rodar em janela separada apos iniciar o robo)
"""

import os
import json
import time
import datetime
import sys

# ----------------------------------------------------------------
# CONFIGURACOES - ajuste se necessario
# ----------------------------------------------------------------
BASE = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"
CSV_RTD       = os.path.join(BASE, "blackarrow_rtd.csv")
JSON_SINAL    = os.path.join(BASE, "operacional_v71_oficial", "ultimo_sinal_v71_blackarrow.json")
CANDLES_CSV   = os.path.join(BASE, "operacional_v71_oficial", "blackarrow_candles_2min.csv")

INTERVALO_VERIFICACAO   = 30   # segundos entre cada checagem
MAX_IDADE_CSV_SEGUNDOS  = 120  # se o CSV nao atualizar em 2 min = alerta
MAX_IDADE_JSON_SEGUNDOS = 300  # se o JSON nao atualizar em 5 min = alerta

HORA_INICIO = 2   # 02:00
HORA_FIM    = 6   # 06:00

# ----------------------------------------------------------------
# FUNCOES
# ----------------------------------------------------------------

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def alarme(vezes=3):
    """Emite beep sonoro"""
    for _ in range(vezes):
        print('\a', end='', flush=True)
        time.sleep(0.3)

def idade_arquivo(caminho):
    """Retorna quantos segundos atras o arquivo foi modificado"""
    if not os.path.exists(caminho):
        return None
    mod = os.path.getmtime(caminho)
    return time.time() - mod

def ler_json_sinal():
    """Le e retorna o ultimo sinal JSON"""
    try:
        with open(JSON_SINAL, encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def dentro_janela_operacional():
    """Verifica se estamos no horario operacional"""
    agora = datetime.datetime.now()
    h = agora.hour + agora.minute / 60
    return HORA_INICIO <= h <= HORA_FIM

def status_linha(ok, texto):
    icone = "  [OK]  " if ok else " [WARN] "
    return icone + texto

def verificar_sistema():
    """Faz todas as verificacoes e retorna lista de status e lista de alertas"""
    status = []
    alertas = []
    agora = datetime.datetime.now().strftime("%H:%M:%S")

    # --- CSV RTD ---
    idade_csv = idade_arquivo(CSV_RTD)
    if idade_csv is None:
        status.append(status_linha(False, "blackarrow_rtd.csv NAO ENCONTRADO"))
        alertas.append("CSV do BlackArrow nao existe! Verifique a macro do Excel.")
    elif dentro_janela_operacional() and idade_csv > MAX_IDADE_CSV_SEGUNDOS:
        status.append(status_linha(False, f"blackarrow_rtd.csv TRAVADO ({int(idade_csv)}s sem atualizar)"))
        alertas.append(f"CSV parou de atualizar ha {int(idade_csv)} segundos! Verifique a macro do BlackArrow.")
    else:
        status.append(status_linha(True, f"blackarrow_rtd.csv OK (atualizado ha {int(idade_csv or 0)}s)"))

    # --- JSON sinal ---
    idade_json = idade_arquivo(JSON_SINAL)
    sinal_dados = ler_json_sinal()

    if idade_json is None:
        status.append(status_linha(False, "ultimo_sinal_v71_blackarrow.json NAO ENCONTRADO"))
        alertas.append("Robo nao gerou sinal ainda. Verifique se esta rodando.")
    elif dentro_janela_operacional() and idade_json > MAX_IDADE_JSON_SEGUNDOS:
        status.append(status_linha(False, f"JSON do sinal DESATUALIZADO ({int(idade_json)}s)"))
        alertas.append(f"Robo parou de gerar sinais ha {int(idade_json)}s! Verifique a janela do robo.")
    else:
        status.append(status_linha(True, f"JSON sinal OK (atualizado ha {int(idade_json or 0)}s)"))

    # --- Conteudo do sinal ---
    if sinal_dados:
        sinal       = sinal_dados.get('sinal', 'N/A')
        candles     = sinal_dados.get('candles_disponiveis', 0)
        horario_ok  = sinal_dados.get('horario_operacional_valido', False)
        janela_ok   = sinal_dados.get('dentro_janela_v71_oficial', False)
        datahora    = sinal_dados.get('datahora_ultimo_candle_sp', 'N/A')

        status.append(status_linha(True,  f"Ultimo sinal: {sinal.upper()}"))
        status.append(status_linha(candles >= 220, f"Candles disponiveis: {candles} (min 220)"))
        status.append(status_linha(horario_ok, f"Horario operacional: {'SIM' if horario_ok else 'NAO'}"))
        status.append(status_linha(janela_ok,  f"Dentro da janela V7.1: {'SIM' if janela_ok else 'NAO'}"))
        status.append(status_linha(True,  f"Ultimo candle: {datahora}"))

        if candles < 220:
            alertas.append(f"Candles insuficientes: {candles}. Aguarde o BlackArrow carregar mais historico.")

        # --- ALERTA DE SINAL DE ENTRADA ---
        if sinal in ('buy', 'sell'):
            idade_json_s = idade_json or 999
            if idade_json_s < 180:  # sinal novo (menos de 3 min)
                status.append("")
                status.append(f"  *** SINAL ATIVO: {sinal.upper()} ***")
                status.append(f"  *** EXECUTE A ORDEM AGORA!   ***")
                return status, alertas, sinal.upper()

    # --- Candles CSV ---
    idade_candles = idade_arquivo(CANDLES_CSV)
    if idade_candles is not None:
        status.append(status_linha(
            idade_candles < 300,
            f"Candles CSV (atualizado ha {int(idade_candles)}s)"
        ))

    return status, alertas, None

# ----------------------------------------------------------------
# LOOP PRINCIPAL
# ----------------------------------------------------------------

def main():
    print("WATCHDOG V7.1 iniciado.")
    print(f"Verificando a cada {INTERVALO_VERIFICACAO} segundos...")
    print("Pressione CTRL+C para parar.\n")
    time.sleep(2)

    ultimo_sinal_alertado = None

    while True:
        try:
            limpar_tela()
            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            na_janela = dentro_janela_operacional()

            print("=" * 60)
            print("  WATCHDOG V7.1 BLACKARROW")
            print(f"  {agora}")
            print(f"  Janela operacional (02:00-06:00): {'ATIVA' if na_janela else 'FORA'}")
            print("=" * 60)
            print()

            status_list, alertas, sinal_ativo = verificar_sistema()

            for linha in status_list:
                print(linha)

            if alertas:
                print()
                print("-" * 60)
                print("  ALERTAS:")
                for a in alertas:
                    print(f"  >> {a}")
                print("-" * 60)
                alarme(2)

            if sinal_ativo and sinal_ativo != ultimo_sinal_alertado:
                print()
                print("!" * 60)
                print(f"  SINAL: {sinal_ativo} - EXECUTE A ORDEM!")
                print(f"  Stop: 117 pts | Take: 50.5 pts | 1 micro MNQ")
                print("!" * 60)
                alarme(5)
                ultimo_sinal_alertado = sinal_ativo
            elif not sinal_ativo:
                ultimo_sinal_alertado = None

            print()
            print(f"  Proxima verificacao em {INTERVALO_VERIFICACAO}s... (CTRL+C para sair)")

            time.sleep(INTERVALO_VERIFICACAO)

        except KeyboardInterrupt:
            print("\nWatchdog encerrado.")
            sys.exit(0)
        except Exception as e:
            print(f"\nErro no watchdog: {e}")
            time.sleep(INTERVALO_VERIFICACAO)

if __name__ == "__main__":
    main()
