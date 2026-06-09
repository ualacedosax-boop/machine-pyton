param(
    [string]$Planilha = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.xlsm",
    [string]$Csv = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv",
    [int]$IntervaloMs = 1000
)

$ErrorActionPreference = "Stop"
$LogFile = Join-Path (Split-Path -Parent $Csv) "log_exportador_excel_v71.txt"
$MutexName = "Local\V71BlackArrowExcelExporter"
$mutex = New-Object System.Threading.Mutex($false, $MutexName)

function Write-Log([string]$Mensagem) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp  $Mensagem" | Out-File -LiteralPath $LogFile -Append -Encoding utf8
}

function ConvertTo-CsvField([object]$Valor) {
    $texto = if ($null -eq $Valor) { "" } else { [string]$Valor }
    '"' + $texto.Replace('"', '""') + '"'
}

$app = $null
$wb = $null
$ws = $null

function Disconnect-Excel {
    if ($null -ne $ws) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws)
        $script:ws = $null
    }
    if ($null -ne $wb) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb)
        $script:wb = $null
    }
    if ($null -ne $app) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
        $script:app = $null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

function Connect-Excel {
    Disconnect-Excel

    # BindToMoniker conecta somente ao arquivo exato que ja esta aberto.
    # Diferente de GetActiveObject, nao captura outra instancia do Excel.
    $script:wb = [System.Runtime.InteropServices.Marshal]::BindToMoniker($Planilha)
    $script:app = $script:wb.Application
    $script:ws = $script:wb.Worksheets.Item(1)

    $aberto = [System.IO.Path]::GetFullPath([string]$script:wb.FullName)
    $esperado = [System.IO.Path]::GetFullPath($Planilha)
    if (-not $aberto.Equals($esperado, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Workbook incorreto conectado: $aberto"
    }

    Write-Log "Conectado ao Excel HWND=$($script:app.Hwnd), workbook=$aberto, aba=$($script:ws.Name)"
}

function Read-ExcelRow {
    if ($null -eq $ws) {
        Connect-Excel
    }

    $cabecalhos = New-Object System.Collections.Generic.List[string]
    $valores = New-Object System.Collections.Generic.List[string]

    for ($coluna = 1; $coluna -le 10; $coluna++) {
        $cabecalhos.Add((ConvertTo-CsvField $ws.Cells.Item(1, $coluna).Text))
        $valores.Add((ConvertTo-CsvField $ws.Cells.Item(2, $coluna).Text))
    }

    if ([string]::IsNullOrWhiteSpace([string]$ws.Cells.Item(2, 1).Text) -or
        [string]::IsNullOrWhiteSpace([string]$ws.Cells.Item(2, 2).Text) -or
        [string]::IsNullOrWhiteSpace([string]$ws.Cells.Item(2, 3).Text) -or
        [string]::IsNullOrWhiteSpace([string]$ws.Cells.Item(2, 4).Text)) {
        throw "Linha RTD incompleta nas colunas Asset/Data/Hora/Ultimo"
    }

    ($cabecalhos -join ';') + "`r`n" + ($valores -join ';') + "`r`n"
}

function Write-CsvAtomic([string]$Conteudo) {
    $pasta = Split-Path -Parent $Csv
    $temporario = Join-Path $pasta ("blackarrow_rtd.{0}.tmp" -f $PID)
    $backup = Join-Path $pasta ("blackarrow_rtd.{0}.bak" -f $PID)
    $encoding = [System.Text.Encoding]::GetEncoding(1252)

    [System.IO.File]::WriteAllText($temporario, $Conteudo, $encoding)
    if (Test-Path -LiteralPath $Csv) {
        [System.IO.File]::Replace($temporario, $Csv, $backup, $true)
        Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
    } else {
        [System.IO.File]::Move($temporario, $Csv)
    }
}

if (-not $mutex.WaitOne(0, $false)) {
    Write-Log "Outra instancia do exportador ja esta ativa. Encerrando duplicata."
    exit 0
}

Write-Log "=== EXPORTADOR EXTERNO V7.1 INICIADO ==="
$ultimoConteudo = $null
$errosConsecutivos = 0

try {
    while ($true) {
        try {
            $conteudo = Read-ExcelRow

            # Se o RTD congelar, nao renova artificialmente o timestamp do CSV.
            # Assim o monitor continua detectando dado realmente desatualizado.
            if ($conteudo -ne $ultimoConteudo) {
                Write-CsvAtomic $conteudo
                $ultimoConteudo = $conteudo
            }

            if ($errosConsecutivos -gt 0) {
                Write-Log "Exportacao recuperada."
            }
            $errosConsecutivos = 0
            Start-Sleep -Milliseconds $IntervaloMs
        } catch {
            $errosConsecutivos++
            Write-Log "Falha $errosConsecutivos`: $($_.Exception.Message). Reconectando..."
            Disconnect-Excel

            # Aguarda o Excel estar rodando antes de chamar BindToMoniker.
            # BindToMoniker em um arquivo .xlsm RELANCA o Excel automaticamente
            # via COM se o processo nao estiver ativo — causando reabertura indesejada
            # quando o usuario fecha a planilha manualmente.
            $tentativasEspera = 0
            while (-not (Get-Process "EXCEL" -ErrorAction SilentlyContinue)) {
                $tentativasEspera++
                if ($tentativasEspera -eq 1) {
                    Write-Log "Excel nao esta rodando. Aguardando reabrir antes de reconectar..."
                }
                Start-Sleep -Seconds 5
            }

            Start-Sleep -Seconds 3
        }
    }
} finally {
    Disconnect-Excel
    $mutex.ReleaseMutex()
    $mutex.Dispose()
    Write-Log "Exportador externo encerrado."
}
