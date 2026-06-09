param(
    [string]$Planilha = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.xlsm",
    [string]$Macro    = "IniciarExportacaoBlackArrow",
    [switch]$SomenteAbrir
)

$LogFile = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\log_abrir_excel.txt"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

# Chama uma propriedade COM com retry automatico para RPC_E_CALL_REJECTED (0x80010001)
# O Excel rejeita chamadas enquanto esta ocupado inicializando — espera ate aceitar.
function Set-ComProp($obj, [string]$prop, $valor, [int]$tentativas = 10) {
    for ($i = 1; $i -le $tentativas; $i++) {
        try {
            $obj.$prop = $valor
            return
        } catch {
            $hr = $_.Exception.HResult
            if ($hr -eq [int]0x80010001 -or $hr -eq [int]0x800AC472) {
                # RPC_E_CALL_REJECTED ou VBA_E_IGNORE: Excel ocupado, tenta de novo
                Start-Sleep -Milliseconds 800
            } else {
                Log "Set-ComProp $prop falhou (nao recuperavel): $_"
                return
            }
        }
    }
    Log "Set-ComProp $prop: Excel nao aceitou apos $tentativas tentativas."
}

Log "=== INICIANDO abrir_excel_macro_v71.ps1 ==="

# Primeiro tenta conectar ao workbook exato. Isso evita usar uma instancia
# qualquer do Excel quando outras planilhas estiverem abertas.
$wb = $null
try {
    $wb = [System.Runtime.InteropServices.Marshal]::BindToMoniker($Planilha)
    $xl = $wb.Application
    Log "Planilha ja estava aberta - usando instancia exata HWND=$($xl.Hwnd)"
} catch {
    $xl = New-Object -ComObject Excel.Application
    Log "Nova instancia Excel criada — aguardando Excel inicializar..."
    # Aguarda o processo do Excel estar pronto antes de qualquer chamada COM
    Start-Sleep -Seconds 2
}

# AutomationSecurity = 1 (msoAutomationSecurityLow): desativa alertas de macro
# Deve ser definido ANTES de abrir o workbook para suprimir o dialogo de seguranca.
Set-ComProp $xl "AutomationSecurity" 1
Set-ComProp $xl "Visible"            $true
Set-ComProp $xl "DisplayAlerts"      $false

# Abre o workbook apenas se ainda nao estiver aberto
$NomeArquivo = [System.IO.Path]::GetFileName($Planilha)

if ($wb) {
    Log "Planilha ja estava aberta - aguardando 5s"
    Start-Sleep -Seconds 5
} else {
    Log "Abrindo planilha..."
    try {
        $wb = $xl.Workbooks.Open($Planilha)
        Log "Planilha aberta. Aguardando 25 segundos para RTD carregar..."
        Start-Sleep -Seconds 25
    } catch {
        Log "Erro ao abrir planilha: $_"
        exit 1
    }
}

if ($SomenteAbrir) {
    Log "Planilha pronta. Exportacao sera feita pelo processo externo V7.1."
    exit 0
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
