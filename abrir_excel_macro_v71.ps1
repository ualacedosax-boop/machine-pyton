param(
    [string]$Planilha = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.xlsm",
    [string]$Macro    = "IniciarExportacaoBlackArrowCSV"
)

$LogFile = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\log_abrir_excel.txt"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

Log "=== INICIANDO abrir_excel_macro_v71.ps1 ==="
Log "Planilha : $Planilha"
Log "Macro    : $Macro"

try {
    Log "Criando instancia Excel COM..."
    $xl = New-Object -ComObject Excel.Application
    $xl.Visible           = $true
    $xl.DisplayAlerts     = $false
    # msoAutomationSecurityLow = 1 -> permite macros sem prompt de seguranca.
    # Deve ser definido ANTES de abrir a pasta de trabalho.
    $xl.AutomationSecurity = 1

    Log "Abrindo planilha..."
    $wb = $xl.Workbooks.Open($Planilha)

    Log "Aguardando 20 segundos para RTD carregar..."
    Start-Sleep -Seconds 20

    # Nome completo evita ambiguidade quando ha varios workbooks abertos
    $NomeArquivo   = [System.IO.Path]::GetFileName($Planilha)
    $MacroCompleto = "'$NomeArquivo'!$Macro"
    Log "Executando: $MacroCompleto"
    $xl.Run($MacroCompleto)
    Log "Macro iniciada com sucesso."
}
catch {
    Log "ERRO: $_"
    Log "Abra a planilha manualmente e rode a macro $Macro via ALT+F8."
}
