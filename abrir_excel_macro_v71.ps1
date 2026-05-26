param(
    [string]$Planilha = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.xlsm",
    [string]$Macro    = "IniciarExportacaoBlackArrowCSV"
)

try {
    $xl = New-Object -ComObject Excel.Application
    $xl.Visible        = $true
    $xl.DisplayAlerts  = $false
    $wb = $xl.Workbooks.Open($Planilha)

    Write-Host "Planilha aberta. Aguardando 10 segundos para carregar..."
    Start-Sleep -Seconds 10

    Write-Host "Iniciando macro: $Macro"
    $xl.Run($Macro)
}
catch {
    Write-Host "ERRO ao abrir Excel ou iniciar macro: $_"
    Write-Host "Abra a planilha manualmente e rode a macro IniciarExportacaoBlackArrowCSV."
    Start-Sleep -Seconds 10
}
