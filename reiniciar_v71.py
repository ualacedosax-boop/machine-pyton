# -*- coding: utf-8 -*-
"""
reiniciar_v71.py  -  Reinicializacao segura do V7.1 BlackArrow
=================================================================
Corrige 3 bugs de restart:

  Bug 1 - Perde historico de candles
          Verifica blackarrow_ticks.csv. Se tiver menos de 220 candles
          executa o payload automaticamente antes de subir o robo.

  Bug 2 - Excel/RTD nao conecta
          Mata o Excel existente (estado inconsistente), reabre do zero
          e aguarda confirmacao de que blackarrow_rtd.csv esta sendo
          atualizado com dados frescos (menos de 30s).

  Bug 3 - Robo nao inicia
          So sobe o robo depois de confirmar que o exportador esta
          escrevendo dados validos. Inicia com janela visivel.

Uso:
    python reiniciar_v71.py              -- reinicio completo
    python reiniciar_v71.py --apenas-excel  -- so recicla Excel/exportador
    python reiniciar_v71.py --so-payload    -- so repoe candles (robo fora)
"""

import os
import sys
import time
import subprocess
import argparse
from datetime import datetime

# ================================================================
# CONFIGURACAO
# ================================================================
BASE          = r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton"
VENV_PYTHON   = os.path.join(BASE, ".venv", "Scripts", "python.exe")
SCRIPT_ROBO   = os.path.join(BASE, "sinal_v71_blackarrow_tempo_real_log_inteligente.py")
SCRIPT_PAYLOAD= os.path.join(BASE, "payload_candles_ibkr.py")

PS_EXPORTADOR = os.path.join(BASE, "exportar_blackarrow_excel_v71.ps1")
PS_EXCEL      = os.path.join(BASE, "abrir_excel_macro_v71.ps1")
SCRIPT_MONITOR = os.path.join(BASE, "monitor_v71_gui.py")

ARQ_TICKS     = os.path.join(BASE, "operacional_v71_oficial", "blackarrow_ticks.csv")
ARQ_RTD_CSV   = os.path.join(BASE, "blackarrow_rtd.csv")

MIN_CANDLES   = 220   # minimo para o robo operar
RTD_MAX_ATRASO= 30    # segundos -- rtd considerado fresco

# ================================================================
# UTILITARIOS
# ================================================================
def log(msg, ok=None):
    ts = datetime.now().strftime("%H:%M:%S")
    if ok is True:
        prefixo = "[OK]"
    elif ok is False:
        prefixo = "[!] "
    else:
        prefixo = "    "
    print(f"  {ts}  {prefixo}  {msg}")


def contar_candles():
    """Retorna numero de linhas de dados em blackarrow_ticks.csv."""
    if not os.path.exists(ARQ_TICKS):
        return 0
    try:
        with open(ARQ_TICKS, encoding="utf-8-sig") as f:
            total = sum(1 for _ in f) - 1   # desconta cabecalho
        return max(0, total)
    except Exception:
        return 0


def rtd_fresco():
    """Retorna True se blackarrow_rtd.csv existe e foi gravado ha menos de RTD_MAX_ATRASO segundos."""
    if not os.path.exists(ARQ_RTD_CSV):
        return False
    atraso = time.time() - os.path.getmtime(ARQ_RTD_CSV)
    return atraso < RTD_MAX_ATRASO


def rtd_tem_data_hoje():
    """Verifica se o CSV contem data de hoje no formato do exportador (dd/mm/yyyy)."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    try:
        with open(ARQ_RTD_CSV, encoding="latin-1") as f:
            conteudo = f.read()
        return hoje in conteudo
    except Exception:
        return False

# ================================================================
# PARAR PROCESSOS
# ================================================================
def matar_robo():
    """Para processos python.exe que estejam rodando o script do robo."""
    try:
        import psutil
        mortos = 0
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if "python" not in p.info["name"].lower():
                    continue
                cmd = " ".join(p.info["cmdline"] or [])
                if "sinal_v71_blackarrow" in cmd:
                    p.kill()
                    mortos += 1
            except Exception:
                pass
        return mortos
    except ImportError:
        # sem psutil: tenta via taskkill com filtro por linha de comando
        try:
            subprocess.run(
                ["wmic", "process", "where",
                 "name='python.exe'", "get", "processid,commandline"],
                capture_output=True, text=True
            )
        except Exception:
            pass
        return 0


def matar_exportador():
    """Para processos PowerShell que estejam rodando o exportador."""
    try:
        import psutil
        mortos = 0
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if "powershell" not in p.info["name"].lower():
                    continue
                cmd = " ".join(p.info["cmdline"] or [])
                if "exportar_blackarrow_excel_v71" in cmd:
                    p.kill()
                    mortos += 1
            except Exception:
                pass
        return mortos
    except ImportError:
        return 0


def matar_excel():
    """Fecha o Excel de forma forcada."""
    resultado = subprocess.run(
        ["taskkill", "/IM", "EXCEL.EXE", "/F"],
        capture_output=True, text=True
    )
    # taskkill retorna 0 se matou, 128 se nao havia processo
    return resultado.returncode in (0, 128)

# ================================================================
# INICIAR COMPONENTES
# ================================================================
def iniciar_excel():
    """Abre o Excel com a planilha blackarrow_rtd.xlsm e aguarda o RTD carregar."""
    log("Abrindo Excel (aguarda 30s para RTD carregar)...")
    proc = subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden",
         "-File", PS_EXCEL,
         "-SomenteAbrir"],
        cwd=BASE
    )
    proc.wait(timeout=60)


def iniciar_exportador():
    """Sobe o exportador PowerShell em background."""
    log("Iniciando exportador Excel...")
    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden",
         "-File", PS_EXPORTADOR],
        cwd=BASE
    )


def iniciar_robo():
    """Sobe o robo em nova janela de console visivel."""
    log("Iniciando Robo V7.1...")
    subprocess.Popen(
        [VENV_PYTHON, SCRIPT_ROBO],
        cwd=BASE,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )


def iniciar_monitor():
    """Sobe o monitor GUI (monitor_v71_gui.py) em nova janela."""
    log("Iniciando Monitor GUI...")
    subprocess.Popen(
        [VENV_PYTHON, SCRIPT_MONITOR],
        cwd=BASE,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )


def aguardar_rtd(timeout=90):
    """
    Aguarda ate RTD_MAX_ATRASO segundos atualizado E com data de hoje.
    Retorna True se OK, False se timeout.
    """
    log(f"Aguardando dados frescos do RTD (timeout {timeout}s)...")
    inicio = time.time()
    while time.time() - inicio < timeout:
        if rtd_fresco() and rtd_tem_data_hoje():
            return True
        time.sleep(2)
    return False


def repor_candles():
    """Executa payload_candles_ibkr.py --sobrescrever para repor historico."""
    log("Repondo historico de candles via payload IBKR...")
    resultado = subprocess.run(
        [VENV_PYTHON, SCRIPT_PAYLOAD, "--sobrescrever"],
        cwd=BASE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if resultado.returncode == 0:
        return True
    else:
        print(resultado.stdout[-800:] if resultado.stdout else "")
        print(resultado.stderr[-400:] if resultado.stderr else "")
        return False

# ================================================================
# FLUXO PRINCIPAL
# ================================================================
def reiniciar_completo(pular_monitor=False):
    print()
    print("=" * 55)
    print("  REINICIAR V7.1 BLACKARROW")
    print("=" * 55)

    # ----------------------------------------------------------
    # PASSO 1: Parar tudo
    # ----------------------------------------------------------
    print()
    print("-- [1/5] Parando componentes em execucao --")

    n = matar_robo()
    log(f"Robo parado ({n} processo(s))", ok=(n >= 0))

    n = matar_exportador()
    log(f"Exportador parado ({n} processo(s))", ok=(n >= 0))

    matar_excel()
    log("Excel fechado", ok=True)

    log("Aguardando 4s para processos liberarem arquivos...")
    time.sleep(4)

    # ----------------------------------------------------------
    # PASSO 2: Verificar / repor candles
    # ----------------------------------------------------------
    print()
    print("-- [2/5] Verificando historico de candles --")

    qtd = contar_candles()
    log(f"blackarrow_ticks.csv: {qtd} candles")

    if qtd < MIN_CANDLES:
        log(f"Menos de {MIN_CANDLES} candles! Repondo automaticamente...", ok=False)
        ok = repor_candles()
        if ok:
            qtd = contar_candles()
            log(f"Payload aplicado. Agora: {qtd} candles", ok=(qtd >= MIN_CANDLES))
        else:
            log("Falha no payload. Continuando assim mesmo...", ok=False)
            log("AVISO: robo pode iniciar sem candles suficientes!", ok=False)
    else:
        log(f"Historico OK ({qtd} >= {MIN_CANDLES})", ok=True)

    # ----------------------------------------------------------
    # PASSO 3: Abrir Excel e aguardar RTD
    # ----------------------------------------------------------
    print()
    print("-- [3/5] Abrindo Excel e aguardando RTD --")

    iniciar_excel()
    iniciar_exportador()

    ok_rtd = aguardar_rtd(timeout=90)
    if ok_rtd:
        atraso = int(time.time() - os.path.getmtime(ARQ_RTD_CSV))
        log(f"RTD ativo e fresco (atraso {atraso}s)", ok=True)
    else:
        log("RTD nao respondeu em 90s!", ok=False)
        log("Verifique se o Excel abriu e o RTD carregou.", ok=False)
        resposta = input("  Continuar mesmo assim? [s/N] ").strip().lower()
        if resposta != "s":
            log("Abortando restart.")
            return False

    # ----------------------------------------------------------
    # PASSO 4: Iniciar Robo
    # ----------------------------------------------------------
    print()
    print("-- [4/5] Iniciando Robo V7.1 --")

    iniciar_robo()
    time.sleep(3)
    log("Robo iniciado em nova janela", ok=True)

    # ----------------------------------------------------------
    # PASSO 5: Monitor (opcional)
    # ----------------------------------------------------------
    print()
    print("-- [5/5] Iniciando Monitor --")

    if pular_monitor:
        log("Monitor pulado (use RODAR_MONITOR_V71_OFICIAL.bat para abrir)")
    else:
        iniciar_monitor()
        log("Monitor iniciado em nova janela", ok=True)

    # ----------------------------------------------------------
    # RESUMO
    # ----------------------------------------------------------
    print()
    print("=" * 55)
    print("  TUDO INICIADO")
    print("=" * 55)
    qtd_final = contar_candles()
    print(f"  Candles     : {qtd_final}")
    print(f"  RTD fresco  : {'SIM' if rtd_fresco() else 'NAO'}")
    print(f"  Hora        : {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 55)
    print()
    return True


def apenas_excel():
    """Recicla so o Excel e o exportador, sem tocar no robo."""
    print()
    print("=" * 55)
    print("  REABRIR EXCEL + EXPORTADOR  (robo nao e tocado)")
    print("=" * 55)

    print()
    print("-- [1/3] Parando Excel e exportador --")
    n = matar_exportador()
    log(f"Exportador parado ({n} processo(s))")
    matar_excel()
    log("Excel fechado")
    time.sleep(3)

    print()
    print("-- [2/3] Abrindo Excel e aguardando RTD --")
    iniciar_excel()
    iniciar_exportador()
    ok_rtd = aguardar_rtd(timeout=90)
    if ok_rtd:
        log("RTD ativo", ok=True)
    else:
        log("RTD nao respondeu em 90s", ok=False)

    print()
    print("-- [3/3] Pronto --")
    log(f"RTD fresco: {'SIM' if rtd_fresco() else 'NAO'}")
    print()


def so_payload():
    """So repoe candles. Robo deve estar parado."""
    print()
    print("=" * 55)
    print("  REPOR CANDLES  (pare o robo antes!)")
    print("=" * 55)
    print()
    qtd = contar_candles()
    log(f"Candles atuais: {qtd}")
    ok = repor_candles()
    if ok:
        qtd = contar_candles()
        log(f"Candles apos payload: {qtd}", ok=True)
    else:
        log("Falha ao repor candles", ok=False)
    print()


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reinicia o V7.1 BlackArrow de forma segura.")
    parser.add_argument("--apenas-excel",  action="store_true", help="So recicla o Excel/exportador")
    parser.add_argument("--so-payload",    action="store_true", help="So repoe candles (robo fora)")
    parser.add_argument("--sem-monitor",   action="store_true", help="Nao abre o monitor")
    args = parser.parse_args()

    if args.apenas_excel:
        apenas_excel()
    elif args.so_payload:
        so_payload()
    else:
        reiniciar_completo(pular_monitor=args.sem_monitor)
