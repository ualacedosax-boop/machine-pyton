@echo off
title REINICIAR V7.1 - BlackArrow
color 0B
cls

echo.
echo  ============================================================
echo   REINICIAR V7.1 BLACKARROW
echo   Para o robo, verifica candles, reabre Excel, sobe tudo
echo  ============================================================
echo.
echo  Opcoes de uso:
echo    [ENTER]       -- Reinicio completo (recomendado)
echo    1             -- So reabrir Excel/exportador (robo continua)
echo    2             -- So repor candles (robo deve estar parado)
echo.

set /p OPCAO="  Escolha [ENTER/1/2]: "

set BASE=C:\Users\ualac\Documents\2025\Mercado\machine-pyton

if "%OPCAO%"=="1" (
    echo.
    echo  Reabrindo apenas Excel e exportador...
    "%BASE%\.venv\Scripts\python.exe" "%BASE%\reiniciar_v71.py" --apenas-excel
    goto FIM
)

if "%OPCAO%"=="2" (
    echo.
    echo  Repondo candles via payload IBKR...
    "%BASE%\.venv\Scripts\python.exe" "%BASE%\reiniciar_v71.py" --so-payload
    goto FIM
)

:: Reinicio completo (padrao)
"%BASE%\.venv\Scripts\python.exe" "%BASE%\reiniciar_v71.py"

:FIM
echo.
pause
