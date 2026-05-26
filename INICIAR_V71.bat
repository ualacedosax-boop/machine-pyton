@echo off
title INICIAR V7.1 - BlackArrow
color 0A
cls

echo ============================================================
echo   V7.1 BLACKARROW - INICIALIZACAO AUTOMATICA
echo ============================================================
echo.

set BASE=C:\Users\ualac\Documents\2025\Mercado\machine-pyton

:: ============================================================
:: [1/6] Abre a planilha Excel e inicia a macro de exportacao
::       Chama um .ps1 separado em processo oculto para nao travar o bat.
:: ============================================================
echo [1/6] Abrindo planilha BlackArrow e iniciando macro...
start "" powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%BASE%\abrir_excel_macro_v71.ps1"
echo       Aguardando planilha carregar (15 segundos)...
timeout /t 15 /nobreak >NUL
echo       Pronto.

:: ============================================================
:: [2/6] Verifica se o BlackArrow esta rodando
:: ============================================================
echo.
echo [2/6] Verificando BlackArrow...
tasklist /FI "IMAGENAME eq BlackArrow.exe" 2>NUL | find /I "BlackArrow.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo       AVISO: BlackArrow.exe nao encontrado no sistema.
    echo       Se o BlackArrow for parte do Excel/RTD, ignore este aviso.
) else (
    echo       BlackArrow rodando. OK
)

:: ============================================================
:: [3/6] Verifica se o CSV do BlackArrow esta sendo atualizado
:: ============================================================
echo.
echo [3/6] Verificando CSV do BlackArrow...
python "%BASE%\checar_csv_v71.py"
if %ERRORLEVEL% NEQ 0 (
    echo       AVISO: CSV pode estar desatualizado ou ausente.
    echo       Verifique se a macro IniciarExportacaoBlackArrow iniciou.
    echo       Pressione qualquer tecla para continuar mesmo assim...
    pause >NUL
) else (
    echo       CSV OK.
)

:: ============================================================
:: [4/6] Acessa a pasta do projeto
:: ============================================================
echo.
echo [4/6] Acessando pasta do projeto...
cd /d "%BASE%"
if %ERRORLEVEL% NEQ 0 (
    echo       ERRO: Pasta nao encontrada: %BASE%
    pause
    exit /b 1
)
echo       OK.

:: ============================================================
:: [5/6] Inicia o Robo V7.1
:: ============================================================
echo.
echo [5/6] Iniciando Robo V7.1...
start "ROBO V7.1" cmd /k "cd /d %BASE% && call .venv\Scripts\activate.bat && python sinal_v71_blackarrow_tempo_real_log_inteligente.py"
timeout /t 5 /nobreak >NUL
echo       Robo iniciado.

:: ============================================================
:: [6/6] Inicia o Monitor
:: ============================================================
echo.
echo [6/6] Iniciando Monitor...
start "MONITOR V7.1" powershell -ExecutionPolicy Bypass -NoExit -File "%BASE%\monitor_alarme_v71_oficial_completo.ps1"
echo       Monitor iniciado.

echo.
echo ============================================================
echo   TUDO INICIADO
echo ============================================================
echo   Planilha : blackarrow_rtd.xlsm (macro rodando em background)
echo   Robo     : janela "ROBO V7.1"
echo   Monitor  : janela "MONITOR V7.1"
echo   Take     : 50,5 pts   Stop: 117 pts   Max: 3 trades/dia
echo   Janela   : 02:00 - 06:00 (bloqueio 04:30-04:45)
echo ============================================================
echo.
pause
