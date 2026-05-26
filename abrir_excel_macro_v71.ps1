param(
    [string]$Planilha = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.xlsm",
    [string]$Macro    = "IniciarExportacaoBlackArrowV71"
)

$LogFile = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\log_abrir_excel.txt"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

Log "=== INICIANDO abrir_excel_macro_v71.ps1 ==="

# Se Excel ja estiver rodando, usa a instancia existente; senao cria nova.
try {
    $xl = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    Log "Excel ja estava rodando - usando instancia existente"
} catch {
    $xl = New-Object -ComObject Excel.Application
    # msoAutomationSecurityLow = 1: deve ser definido ANTES de abrir o workbook
    $xl.AutomationSecurity = 1
    Log "Nova instancia Excel criada"
}

$xl.Visible       = $true
$xl.DisplayAlerts = $false

# Abre o workbook apenas se ainda nao estiver aberto
$NomeArquivo = [System.IO.Path]::GetFileName($Planilha)
$wb = $xl.Workbooks | Where-Object { $_.Name -eq $NomeArquivo }

if ($wb) {
    Log "Planilha ja estava aberta - aguardando 5s"
    Start-Sleep -Seconds 5
} else {
    $xl.AutomationSecurity = 1
    Log "Abrindo planilha..."
    $wb = $xl.Workbooks.Open($Planilha)
    Log "Aguardando 25 segundos para RTD carregar..."
    Start-Sleep -Seconds 25
}

# 3 tentativas com 10s de espera entre elas (para o erro 0x800AC472 - Excel ocupado)
$MacroCompleto = "'$NomeArquivo'!$Macro"
$sucesso = $false

for ($i = 1; $i -le 3; $i++) {
    try {
        Log "Tentativa $i - Executando: $MacroCompleto"
        $xl.Run($MacroCompleto)
        Log "Macro iniciada com sucesso na tentativa $i."
        $sucesso = $true
        break
    } catch {
        Log "Tentativa $i falhou: $_"
        if ($i -lt 3) {
            Log "Aguardando 10s antes da proxima tentativa..."
            Start-Sleep -Seconds 10
        }
    }
}

if (-not $sucesso) {
    Log "FALHA: macro nao iniciou apos 3 tentativas."
    Log "Abra a planilha manualmente e rode $Macro via ALT+F8."
}
