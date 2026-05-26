@echo off
title INICIAR V7.1 - BlackArrow
color 0A
cls

echo ============================================================
echo   V7.1 BLACKARROW - INICIALIZACAO AUTOMATICA
echo ============================================================
echo.

set BASE=C:\Users\ualac\Documents\2025\Mercado\machine-pyton

echo [1/5] Verificando BlackArrow...
tasklist /FI "IMAGENAME eq BlackArrow.exe" 2>NUL | find /I "BlackArrow.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo       BlackArrow NAO encontrado. Abra o BlackArrow manualmente.
    echo       Pressione qualquer tecla quando o BlackArrow estiver aberto...
    pause >NUL
) else (
    echo       BlackArrow ja esta rodando. OK
)

echo.
echo [2/5] Verificando CSV do BlackArrow...
python "%BASE%\checar_csv_v71.py"
if %ERRORLEVEL% NEQ 0 (
    echo       AVISO: CSV pode estar desatualizado!
    echo       Verifique se o BlackArrow esta exportando dados.
    echo       Pressione qualquer tecla para continuar mesmo assim...
    pause >NUL
) else (
    echo       CSV OK.
)

echo.
echo [3/5] Acessando pasta do projeto...
cd /d "%BASE%"
if %ERRORLEVEL% NEQ 0 (
    echo       ERRO: Pasta nao encontrada: %BASE%
    pause
    exit /b 1
)
echo       OK.

echo.
echo [4/5] Iniciando Robo V7.1...
start "ROBO V7.1" cmd /k "cd /d %BASE% && call .venv\Scripts\activate.bat && python sinal_v71_blackarrow_tempo_real_log_inteligente.py"
timeout /t 5 /nobreak >NUL
echo       Robo iniciado.

echo.
echo [5/5] Iniciando Monitor...
start "MONITOR V7.1" powershell -ExecutionPolicy Bypass -NoExit -File "%BASE%\monitor_alarme_v71_oficial_completo.ps1"
echo       Monitor iniciado.

echo.
echo ============================================================
echo   TUDO INICIADO
echo ============================================================
echo   Robo   : janela "ROBO V7.1"
echo   Monitor: janela "MONITOR V7.1"
echo   Stop: 90pts  Take: 50.5pts  Max: 3 trades/dia
echo   Janela: 02:00 - 06:00
echo ============================================================
echo.
pause
