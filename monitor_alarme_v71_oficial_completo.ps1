# monitor_alarme_v7_oficial_completo.ps1
# Monitor completo V7.1.1 OFICIAL:
# - Le ultimo_sinal_v71_blackarrow.json gerado pelo robo V7.1
# - Mostra Prob V5.1, Prob V5.5, Gap, BUY, SELL, checklist e melhores scores
# - Monitora entrada real no CSV
# - Toca alarme diferente com voz para COMPRA e VENDA

# ============================================================
# CAMINHOS
# ============================================================

$basePath = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton"

$jsonPath1 = Join-Path $basePath "ultimo_sinal_v71_blackarrow.json"
$jsonPath2 = Join-Path $basePath "operacional_v71_oficial\ultimo_sinal_v71_blackarrow.json"

$csvPath = Join-Path $basePath "operacional_v71_oficial\log_sinal_v71_blackarrow.csv"
$csvAprendizadoPath = Join-Path $basePath "operacional_v71_oficial\aprendizado_v71\eventos\eventos_v7_inteligente.csv"
$resultadosAprendizadoPath = Join-Path $basePath "operacional_v71_oficial\aprendizado_v71\resultados\resultados_v7_inteligente.csv"

# Usa o JSON que existir
if (Test-Path $jsonPath1) {
    $jsonPath = $jsonPath1
}
elseif (Test-Path $jsonPath2) {
    $jsonPath = $jsonPath2
}
else {
    $jsonPath = $jsonPath2
}

# ============================================================
# LIMITES OFICIAIS DA V7.1
# ============================================================

$minProbV51 = 0.590
$minProbV55 = 0.425
$minBuy     = 0.74
$minSell    = 0.50
$minGap     = -999.0   # V7.1 oficial nao usa corte minimo de gap; exibe apenas diagnostico

# ============================================================
# VOZ DO WINDOWS
# ============================================================

try {
    Add-Type -AssemblyName System.Speech
    $voz = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $voz.Volume = 100
    $voz.Rate = 2
}
catch {
    $voz = $null
}

# ============================================================
# VARIAVEIS DE CONTROLE
# ============================================================

$ultimoSinalProcessadoCSV = ""
$ultimoAlarmeEntradaId = ""

$melhorBuy = -999
$melhorSell = -999
$melhorV51 = -999
$melhorV55 = -999
$melhorGap = -999

$melhorBuyHora = ""
$melhorSellHora = ""
$melhorV51Hora = ""
$melhorV55Hora = ""
$melhorGapHora = ""

$melhorBuyPreco = ""
$melhorSellPreco = ""
$melhorV51Preco = ""
$melhorV55Preco = ""
$melhorGapPreco = ""

# ============================================================
# FUNCOES
# ============================================================

function To-Double {
    param ($valor)

    if ($null -eq $valor) {
        return 0.0
    }

    $txt = "$valor".Trim()
    if ($txt -eq "") { return 0.0 }

    # Remove separador de milhar brasileiro quando existir formato 29.520,00
    if ($txt.Contains(",")) {
        $txt = $txt.Replace(".", "")
        $txt = $txt.Replace(",", ".")
    }
    else {
        $txt = $txt.Replace(",", "")
    }

    try {
        return [double]::Parse($txt, [System.Globalization.CultureInfo]::InvariantCulture)
    }
    catch {
        return 0.0
    }
}

function Format-Num {
    param (
        $valor,
        $casas = 6
    )

    try {
        $v = To-Double $valor
        return $v.ToString("N$casas")
    }
    catch {
        return "$valor"
    }
}

function Barra-Progresso {
    param (
        [double]$valor,
        [double]$minimo
    )

    $tamanho = 24

    if ($minimo -le 0) {
        $perc = 0
    }
    else {
        $perc = $valor / $minimo
    }

    if ($perc -lt 0) { $perc = 0 }
    if ($perc -gt 1) { $perc = 1 }

    $cheio = [int]($perc * $tamanho)
    $vazio = $tamanho - $cheio

    $barra = ("#" * $cheio) + ("-" * $vazio)
    $percentual = "{0:N1}%" -f ($perc * 100)

    return "[$barra] $percentual"
}

function Faltando {
    param (
        [double]$valor,
        [double]$minimo
    )

    $falta = $minimo - $valor

    if ($falta -le 0) {
        return "0,000000"
    }

    return $falta.ToString("N6")
}

function Get-Prop {
    param (
        $obj,
        [string[]]$nomes
    )

    foreach ($nome in $nomes) {
        if ($null -ne $obj.PSObject.Properties[$nome]) {
            return $obj.$nome
        }
    }

    return $null
}

function Read-LastCsvRowSafe {
    param ($path)

    if (!(Test-Path $path)) {
        return $null
    }

    try {
        $dadosCsv = Import-Csv $path
        if ($dadosCsv.Count -le 0) {
            return $null
        }
        return ($dadosCsv | Select-Object -Last 1)
    }
    catch {
        return $null
    }
}

function Count-CsvRowsSafe {
    param ($path)

    if (!(Test-Path $path)) {
        return 0
    }

    try {
        $dadosCsv = Import-Csv $path
        return $dadosCsv.Count
    }
    catch {
        return 0
    }
}

function Tocar-AlarmeCompra {
    param ($voz)

    Write-Host ""
    Write-Host "ALERTA: COMPRA DETECTADA - BUY" -ForegroundColor Green

    for ($i = 0; $i -lt 3; $i++) {
        [console]::beep(1400, 150)
        Start-Sleep -Milliseconds 50
        [console]::beep(1800, 150)

        if ($null -ne $voz) {
            $voz.Speak("Compra detectada")
        }

        Start-Sleep -Milliseconds 250
    }
}

function Tocar-AlarmeVenda {
    param ($voz)

    Write-Host ""
    Write-Host "ALERTA: VENDA DETECTADA - SELL" -ForegroundColor Red

    for ($i = 0; $i -lt 3; $i++) {
        [console]::beep(700, 250)
        Start-Sleep -Milliseconds 80
        [console]::beep(500, 250)

        if ($null -ne $voz) {
            $voz.Speak("Venda detectada")
        }

        Start-Sleep -Milliseconds 250
    }
}

function Verificar-Alarme-CSV {
    param (
        $csvPath,
        $voz
    )

    $ultimoCsv = Read-LastCsvRowSafe $csvPath
    if ($null -eq $ultimoCsv) {
        return
    }

    $datahoraCsv = $ultimoCsv.datahora_execucao
    $sinalCsv    = $ultimoCsv.sinal
    $motivoCsv   = $ultimoCsv.motivo
    $precoCsv    = $ultimoCsv.preco_close
    $probCsv     = Get-Prop $ultimoCsv @("prob_v51", "prob_win_v4", "prob_v4")
    $direcaoCsv  = $ultimoCsv.Direcao
    $eventIdCsv  = Get-Prop $ultimoCsv @("event_id", "id_evento", "id")

    if ([string]::IsNullOrWhiteSpace("$eventIdCsv")) {
        $idCsv = "$datahoraCsv|$sinalCsv|$precoCsv|$direcaoCsv"
    }
    else {
        $idCsv = "$eventIdCsv"
    }

    if ($script:ultimoSinalProcessadoCSV -eq "") {
        $script:ultimoSinalProcessadoCSV = $idCsv
        return
    }

    if ($idCsv -ne $script:ultimoSinalProcessadoCSV) {
        $script:ultimoSinalProcessadoCSV = $idCsv

        if (($motivoCsv -eq "sinal_valido") -and ($idCsv -ne $script:ultimoAlarmeEntradaId) -and ($sinalCsv -eq "buy")) {
            $script:ultimoAlarmeEntradaId = $idCsv
            Clear-Host
            Write-Host "===============================================" -ForegroundColor Green
            Write-Host " ENTRADA REAL DETECTADA NO CSV - COMPRA" -ForegroundColor Green
            Write-Host "===============================================" -ForegroundColor Green
            Write-Host "Data/Hora     : $datahoraCsv"
            Write-Host "Sinal         : $sinalCsv"
            Write-Host "Motivo        : $motivoCsv"
            Write-Host "Preco         : $precoCsv"
            Write-Host "Prob V5.1     : $probCsv"
            Write-Host "Direcao       : $direcaoCsv"
            Tocar-AlarmeCompra $voz
            Start-Sleep -Seconds 2
        }
        elseif (($motivoCsv -eq "sinal_valido") -and ($idCsv -ne $script:ultimoAlarmeEntradaId) -and ($sinalCsv -eq "sell")) {
            $script:ultimoAlarmeEntradaId = $idCsv
            Clear-Host
            Write-Host "===============================================" -ForegroundColor Red
            Write-Host " ENTRADA REAL DETECTADA NO CSV - VENDA" -ForegroundColor Red
            Write-Host "===============================================" -ForegroundColor Red
            Write-Host "Data/Hora     : $datahoraCsv"
            Write-Host "Sinal         : $sinalCsv"
            Write-Host "Motivo        : $motivoCsv"
            Write-Host "Preco         : $precoCsv"
            Write-Host "Prob V5.1     : $probCsv"
            Write-Host "Direcao       : $direcaoCsv"
            Tocar-AlarmeVenda $voz
            Start-Sleep -Seconds 2
        }
    }
}

function Mostrar-LinhaScore {
    param(
        [string]$nome,
        [double]$valor,
        [double]$minimo,
        [double]$melhor
    )

    $passou = $valor -ge $minimo

    Write-Host ("{0,-13}: {1} / min {2} | melhor {3}" -f $nome, (Format-Num $valor 6), (Format-Num $minimo 3), (Format-Num $melhor 6))
    Write-Host ("              {0}" -f (Barra-Progresso $valor $minimo))

    if ($passou) {
        Write-Host ("              Falta: {0} | PASSOU" -f (Faltando $valor $minimo)) -ForegroundColor Green
    }
    else {
        Write-Host ("              Falta: {0} | NAO PASSOU" -f (Faltando $valor $minimo)) -ForegroundColor Red
    }

    Write-Host ""
}

# ============================================================
# LOOP PRINCIPAL
# ============================================================

while ($true) {

    Verificar-Alarme-CSV $csvPath $voz

    Clear-Host

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "MONITOR V7.1.1 OFICIAL BLACKARROW - JSON + ALARME + LOG INTELIGENTE" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Atualizacao : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Fonte JSON  : $jsonPath"
    Write-Host "Fonte CSV   : $csvPath"
    Write-Host "Eventos V7.1  : $csvAprendizadoPath"
    Write-Host "Resultados  : $resultadosAprendizadoPath"
    Write-Host ""

    if (!(Test-Path $jsonPath)) {
        Write-Host "ERRO: JSON nao encontrado." -ForegroundColor Red
        Write-Host "Verifique se existe um destes arquivos:"
        Write-Host $jsonPath1
        Write-Host $jsonPath2
        Write-Host ""
        Write-Host "O alarme do CSV continua tentando monitorar entradas reais."
        Start-Sleep -Seconds 2
        continue
    }

    try {
        $jsonRaw = Get-Content $jsonPath -Raw
        $json = $jsonRaw | ConvertFrom-Json
    }
    catch {
        Write-Host "ERRO: nao foi possivel ler o JSON." -ForegroundColor Red
        Write-Host $_.Exception.Message
        Start-Sleep -Seconds 2
        continue
    }

    # ============================================================
    # CAMPOS PRINCIPAIS
    # ============================================================

    $versao  = Get-Prop $json @("versao_robo", "modelo_operacional", "versao", "Versao")
    $sinal   = Get-Prop $json @("sinal", "signal", "Sinal")
    $motivo  = Get-Prop $json @("motivo", "reason", "Motivo")
    $eventId = Get-Prop $json @("event_id", "id_evento", "id")
    $exec    = Get-Prop $json @("datahora_execucao", "execucao", "execution_time", "Execucao")
    $candle  = Get-Prop $json @("datahora_ultimo_candle_sp", "candle", "ultimo_candle", "Candle")
    $data    = Get-Prop $json @("data", "date", "Data")
    $preco   = Get-Prop $json @("preco_close", "preco", "price", "Preco")
    $take    = Get-Prop $json @("preco_take", "take", "PrecoTake")
    $stop    = Get-Prop $json @("preco_stop", "stop", "PrecoStop")
    $direcao = Get-Prop $json @("Direcao", "direcao", "direction", "DirecaoPrevista")
    $candles = Get-Prop $json @("candles_disponiveis", "candles", "Candles", "qtd_candles")
    $modoSeguro = Get-Prop $json @("modo_seguro_sem_ordem", "modo_seguro", "MODO_SEGURO")

    $dentroHora = Get-Prop $json @("dentro_horario_v7", "dentro_horario_v4", "dentro_hora", "dentroHorario", "dentro_horario", "DentroHora")
    $horarioValido = Get-Prop $json @("horario_operacional_valido", "horario_valido")
    $bloqueio0430 = Get-Prop $json @("bloqueio_0430_0444", "bloqueio_0430")

    if ([string]::IsNullOrWhiteSpace("$eventId")) {
        $eventId = "$candle|$sinal|$preco|$direcao"
    }

    if (($motivo -eq "sinal_valido") -and ($eventId -ne $script:ultimoAlarmeEntradaId)) {
        if ($sinal -eq "buy") {
            $script:ultimoAlarmeEntradaId = $eventId
            Tocar-AlarmeCompra $voz
        }
        elseif ($sinal -eq "sell") {
            $script:ultimoAlarmeEntradaId = $eventId
            Tocar-AlarmeVenda $voz
        }
    }

    # ============================================================
    # SCORES / PROBABILIDADES
    # ============================================================

    $probV51Raw = Get-Prop $json @("prob_v51", "prob_win_v4", "prob_v4", "probabilidade")
    $probV55Raw = Get-Prop $json @("prob_v55", "prob_v5_5", "prob_filtro_v55")
    $gapRaw     = Get-Prop $json @("gap_v51_v55", "gap", "prob_gap")

    $buyScoreRaw  = Get-Prop $json @("score_BUY", "BUY", "buy", "score_BU", "score_buy", "buy_score")
    $sellScoreRaw = Get-Prop $json @("score_SELL", "SELL", "sell", "score_SE", "score_sell", "sell_score")
    $noneScoreRaw = Get-Prop $json @("score_NONE", "NONE", "none", "score_none")
    $scoreDiffRaw = Get-Prop $json @("score_diff", "diferenca_score")

    $probV51d = To-Double $probV51Raw
    $probV55d = To-Double $probV55Raw
    $gapD     = To-Double $gapRaw
    $buyD     = To-Double $buyScoreRaw
    $sellD    = To-Double $sellScoreRaw
    $noneD    = To-Double $noneScoreRaw
    $scoreDiffD = To-Double $scoreDiffRaw

    # ============================================================
    # MELHORES DESDE QUE ABRIU
    # ============================================================

    if ($probV51d -gt $melhorV51) {
        $melhorV51 = $probV51d
        $melhorV51Hora = $candle
        $melhorV51Preco = $preco
    }

    if ($probV55d -gt $melhorV55) {
        $melhorV55 = $probV55d
        $melhorV55Hora = $candle
        $melhorV55Preco = $preco
    }

    if ($gapD -gt $melhorGap) {
        $melhorGap = $gapD
        $melhorGapHora = $candle
        $melhorGapPreco = $preco
    }

    if ($buyD -gt $melhorBuy) {
        $melhorBuy = $buyD
        $melhorBuyHora = $candle
        $melhorBuyPreco = $preco
    }

    if ($sellD -gt $melhorSell) {
        $melhorSell = $sellD
        $melhorSellHora = $candle
        $melhorSellPreco = $preco
    }

    # ============================================================
    # CHECKS
    # ============================================================

    $passouV51 = $probV51d -ge $minProbV51
    $passouV55 = $probV55d -ge $minProbV55
    $passouBuy = $buyD -ge $minBuy
    $passouSell = $sellD -ge $minSell
    $direcaoBuy = "$direcao" -eq "BUY"
    $direcaoSell = "$direcao" -eq "SELL"

    $regraBuy = $passouV51 -and $passouV55 -and $passouBuy -and $direcaoBuy
    $regraSell = $passouV51 -and $passouV55 -and $passouSell -and $direcaoSell

    # ============================================================
    # LOG INTELIGENTE
    # ============================================================

    $qtdEventos = Count-CsvRowsSafe $csvAprendizadoPath
    $qtdResultados = Count-CsvRowsSafe $resultadosAprendizadoPath
    $ultimoResultado = Read-LastCsvRowSafe $resultadosAprendizadoPath

    # ============================================================
    # TELA
    # ============================================================

    Write-Host "STATUS ATUAL" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"
    Write-Host ("Versao      : {0}" -f $versao)
    Write-Host ("Sinal       : {0}" -f $sinal)
    Write-Host ("Motivo      : {0}" -f $motivo)
    Write-Host ("Execucao    : {0}" -f $exec)
    Write-Host ("Candle      : {0}" -f $candle)
    Write-Host ("Data        : {0}" -f $data)
    Write-Host ("Preco       : {0}" -f $preco)
    Write-Host ("Take        : {0}" -f $take)
    Write-Host ("Stop        : {0}" -f $stop)
    Write-Host ("Direcao     : {0}" -f $direcao)
    Write-Host ("Modo seguro : {0}" -f $modoSeguro)
    Write-Host ("Candles     : {0}" -f $candles)
    Write-Host ("Dentro hora : {0}" -f $dentroHora)
    Write-Host ("Horario ok  : {0}" -f $horarioValido)
    Write-Host ("Bloq 04:30  : {0}" -f $bloqueio0430)
    Write-Host ""

    Write-Host "PROBABILIDADES V7.1" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"
    Mostrar-LinhaScore "Prob V5.1" $probV51d $minProbV51 $melhorV51
    Mostrar-LinhaScore "Prob V5.5" $probV55d $minProbV55 $melhorV55
    Write-Host ("Gap V51-V55  : {0} | melhor {1}" -f (Format-Num $gapD 6), (Format-Num $melhorGap 6))
    Write-Host ""

    Write-Host "DIRECAO V3 / SCORES" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"
    Write-Host ("NONE        : {0}" -f (Format-Num $noneD 6))
    Mostrar-LinhaScore "BUY" $buyD $minBuy $melhorBuy
    Mostrar-LinhaScore "SELL" $sellD $minSell $melhorSell
    Write-Host ("Score diff  : {0}" -f (Format-Num $scoreDiffD 6))
    Write-Host ""

    Write-Host "MELHORES DESDE QUE ABRIU O MONITOR" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"
    Write-Host ("Melhor V5.1 : {0} | {1} | Preco {2}" -f (Format-Num $melhorV51 6), $melhorV51Hora, $melhorV51Preco)
    Write-Host ("Melhor V5.5 : {0} | {1} | Preco {2}" -f (Format-Num $melhorV55 6), $melhorV55Hora, $melhorV55Preco)
    Write-Host ("Melhor Gap  : {0} | {1} | Preco {2}" -f (Format-Num $melhorGap 6), $melhorGapHora, $melhorGapPreco)
    Write-Host ("Melhor BUY  : {0} | {1} | Preco {2}" -f (Format-Num $melhorBuy 6), $melhorBuyHora, $melhorBuyPreco)
    Write-Host ("Melhor SELL : {0} | {1} | Preco {2}" -f (Format-Num $melhorSell 6), $melhorSellHora, $melhorSellPreco)
    Write-Host ""

    Write-Host "CHECKLIST V7.1" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"

    if ($passouV51) {
        Write-Host ("Prob V5.1 >= {0} : PASSOU" -f (Format-Num $minProbV51 3)) -ForegroundColor Green
    }
    else {
        Write-Host ("Prob V5.1 >= {0} : NAO PASSOU" -f (Format-Num $minProbV51 3)) -ForegroundColor Red
    }

    if ($passouV55) {
        Write-Host ("Prob V5.5 >= {0} : PASSOU" -f (Format-Num $minProbV55 3)) -ForegroundColor Green
    }
    else {
        Write-Host ("Prob V5.5 >= {0} : NAO PASSOU" -f (Format-Num $minProbV55 3)) -ForegroundColor Red
    }

    if ($passouBuy) {
        Write-Host ("BUY       >= {0} : PASSOU" -f (Format-Num $minBuy 2)) -ForegroundColor Green
    }
    else {
        Write-Host ("BUY       >= {0} : NAO PASSOU" -f (Format-Num $minBuy 2)) -ForegroundColor Red
    }

    if ($passouSell) {
        Write-Host ("SELL      >= {0} : PASSOU" -f (Format-Num $minSell 2)) -ForegroundColor Green
    }
    else {
        Write-Host ("SELL      >= {0} : NAO PASSOU" -f (Format-Num $minSell 2)) -ForegroundColor Red
    }

    if ($direcaoBuy) {
        Write-Host "Direcao BUY       : PASSOU" -ForegroundColor Green
    }
    else {
        Write-Host "Direcao BUY       : NAO PASSOU" -ForegroundColor Red
    }

    if ($direcaoSell) {
        Write-Host "Direcao SELL      : PASSOU" -ForegroundColor Green
    }
    else {
        Write-Host "Direcao SELL      : NAO PASSOU" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host ("Regra BUY : V5.1 >= {0} + V5.5 >= {1} + BUY >= {2} + Direcao BUY + horario/gestao" -f (Format-Num $minProbV51 3), (Format-Num $minProbV55 3), (Format-Num $minBuy 2))
    Write-Host ("Regra SELL: V5.1 >= {0} + V5.5 >= {1} + SELL >= {2} + Direcao SELL + horario/gestao" -f (Format-Num $minProbV51 3), (Format-Num $minProbV55 3), (Format-Num $minSell 2))
    Write-Host ""

    Write-Host "LOG INTELIGENTE" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"
    Write-Host ("Eventos registrados   : {0}" -f $qtdEventos)
    Write-Host ("Resultados fechados   : {0}" -f $qtdResultados)

    if ($null -ne $ultimoResultado) {
        $res = Get-Prop $ultimoResultado @("resultado", "resultado_futuro", "tipo_resultado")
        $pontos = Get-Prop $ultimoResultado @("pontos_resultado", "pontos", "resultado_pontos")
        $dtres = Get-Prop $ultimoResultado @("datahora_resultado", "datahora_fechamento", "datahora_execucao")
        Write-Host ("Ultimo resultado      : {0} | pontos {1} | {2}" -f $res, $pontos, $dtres)
    }
    else {
        Write-Host "Ultimo resultado      : nenhum ainda"
    }

    Write-Host ""

    if ($regraBuy) {
        Write-Host "CHECK PRINCIPAL: BUY PASSOU NAS PROBABILIDADES E DIRECAO. Aguardando horario/gestao/sinal oficial." -ForegroundColor Green
    }
    elseif ($regraSell) {
        Write-Host "CHECK PRINCIPAL: SELL PASSOU NAS PROBABILIDADES E DIRECAO. Aguardando horario/gestao/sinal oficial." -ForegroundColor Red
    }
    else {
        Write-Host "CHECK PRINCIPAL: ainda sem setup completo V7.1." -ForegroundColor Yellow
    }

    if ($sinal -eq "buy") {
        Write-Host "ALARME: sinal oficial de COMPRA no JSON. Entrada real sera confirmada pelo CSV." -ForegroundColor Green
    }
    elseif ($sinal -eq "sell") {
        Write-Host "ALARME: sinal oficial de VENDA no JSON. Entrada real sera confirmada pelo CSV." -ForegroundColor Red
    }
    else {
        Write-Host "ALARME: monitorando... sem sinal oficial." -ForegroundColor Yellow
    }

    Write-Host "Para parar: CTRL + C" -ForegroundColor DarkGray

    Start-Sleep -Seconds 2
}
