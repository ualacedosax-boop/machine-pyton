from pathlib import Path
from datetime import datetime
import shutil
import zipfile

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

# Usa o pacote mais recente criado
pacotes = sorted(
    [p for p in BASE.glob("PACOTE_V71_OFICIAL_REPLICACAO_*") if p.is_dir()],
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

if not pacotes:
    raise RuntimeError("Não encontrei pasta PACOTE_V71_OFICIAL_REPLICACAO_*")

PACOTE = pacotes[0]
ZIP_FINAL = BASE / f"{PACOTE.name}.zip"

print("Pacote encontrado:", PACOTE)
print("ZIP correspondente:", ZIP_FINAL)

PASTA_MACRO = PACOTE / "MACRO_EXCEL_BLACKARROW"
PASTA_MACRO.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. CRIAR ARQUIVO .BAS COM A MACRO VBA
# ============================================================

macro_vba = r'''
Attribute VB_Name = "Modulo_BlackArrow_RTD_V71"
Option Explicit

' ============================================================
' MACRO BLACKARROW -> CSV -> V7.1
' ============================================================
'
' Esta macro exporta os dados RTD do Excel/BlackArrow para:
'
' C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv
'
' O robô V7.1 lê esse CSV em tempo real.
'
' Colunas esperadas:
'
' A: Ativo
' B: Data
' C: Hora
' D: Último
' E: Abertura
' F: Máximo
' G: Mínimo
' H: Negócios
'
' Linha 1: cabeçalho
' Linha 2: valores do BlackArrow/RTD
'
' Macros principais:
'
' ExportarBlackArrowCSV           -> exporta uma vez
' IniciarExportacaoBlackArrowV71  -> exporta automaticamente a cada 1 segundo
' PararExportacaoBlackArrowV71    -> para a exportação automática
'
' ============================================================

Public ProximaExecucao As Date
Public ExportacaoAtiva As Boolean

Public Const CAMINHO_CSV_V71 As String = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv"

Sub ExportarBlackArrowCSV()

    On Error GoTo TrataErro

    Dim ws As Worksheet
    Dim fso As Object
    Dim arquivo As Object
    Dim caminho As String

    Dim ativo As String
    Dim dataValor As String
    Dim horaValor As String
    Dim ultimo As String
    Dim abertura As String
    Dim maximo As String
    Dim minimo As String
    Dim negocios As String

    Set ws = ActiveSheet
    caminho = CAMINHO_CSV_V71

    ' Garante cabeçalho na planilha, se estiver vazio
    If Trim(CStr(ws.Range("A1").Value)) = "" Then ws.Range("A1").Value = "Ativo"
    If Trim(CStr(ws.Range("B1").Value)) = "" Then ws.Range("B1").Value = "Data"
    If Trim(CStr(ws.Range("C1").Value)) = "" Then ws.Range("C1").Value = "Hora"
    If Trim(CStr(ws.Range("D1").Value)) = "" Then ws.Range("D1").Value = "Último"
    If Trim(CStr(ws.Range("E1").Value)) = "" Then ws.Range("E1").Value = "Abertura"
    If Trim(CStr(ws.Range("F1").Value)) = "" Then ws.Range("F1").Value = "Máximo"
    If Trim(CStr(ws.Range("G1").Value)) = "" Then ws.Range("G1").Value = "Mínimo"
    If Trim(CStr(ws.Range("H1").Value)) = "" Then ws.Range("H1").Value = "Negócios"

    ativo = LimparCSV(ws.Range("A2").Text)
    dataValor = LimparCSV(ws.Range("B2").Text)
    horaValor = LimparCSV(ws.Range("C2").Text)
    ultimo = LimparCSV(ws.Range("D2").Text)
    abertura = LimparCSV(ws.Range("E2").Text)
    maximo = LimparCSV(ws.Range("F2").Text)
    minimo = LimparCSV(ws.Range("G2").Text)
    negocios = LimparCSV(ws.Range("H2").Text)

    Set fso = CreateObject("Scripting.FileSystemObject")
    Set arquivo = fso.CreateTextFile(caminho, True, False)

    arquivo.WriteLine "Ativo;Data;Hora;Último;Abertura;Máximo;Mínimo;Negócios"
    arquivo.WriteLine ativo & ";" & dataValor & ";" & horaValor & ";" & ultimo & ";" & abertura & ";" & maximo & ";" & minimo & ";" & negocios

    arquivo.Close

    Exit Sub

TrataErro:
    On Error Resume Next
    If Not arquivo Is Nothing Then arquivo.Close
    Debug.Print "Erro ExportarBlackArrowCSV: " & Err.Description

End Sub

Function LimparCSV(ByVal valor As String) As String

    valor = CStr(valor)
    valor = Replace(valor, ";", ",")
    valor = Replace(valor, vbCr, "")
    valor = Replace(valor, vbLf, "")
    valor = Trim(valor)

    LimparCSV = valor

End Function

Sub IniciarExportacaoBlackArrowV71()

    ExportacaoAtiva = True
    ExportarBlackArrowCSV
    AgendarProximaExportacao

    MsgBox "Exportação BlackArrow -> V7.1 iniciada." & vbCrLf & _
           "Arquivo gerado em:" & vbCrLf & CAMINHO_CSV_V71, vbInformation

End Sub

Sub AgendarProximaExportacao()

    If ExportacaoAtiva = False Then Exit Sub

    ProximaExecucao = Now + TimeSerial(0, 0, 1)

    Application.OnTime _
        EarliestTime:=ProximaExecucao, _
        Procedure:="AgendarExportarBlackArrowCSV", _
        Schedule:=True

End Sub

Sub AgendarExportarBlackArrowCSV()

    If ExportacaoAtiva = False Then Exit Sub

    ExportarBlackArrowCSV
    AgendarProximaExportacao

End Sub

Sub PararExportacaoBlackArrowV71()

    On Error Resume Next

    ExportacaoAtiva = False

    Application.OnTime _
        EarliestTime:=ProximaExecucao, _
        Procedure:="AgendarExportarBlackArrowCSV", _
        Schedule:=False

    MsgBox "Exportação BlackArrow -> V7.1 parada.", vbInformation

End Sub
'''

(PASTA_MACRO / "Modulo_BlackArrow_RTD_V71.bas").write_text(macro_vba, encoding="utf-8")

# ============================================================
# 2. CRIAR INSTRUÇÕES DA MACRO
# ============================================================

instrucoes = r'''
# MACRO EXCEL BLACKARROW PARA O V7.1

Esta pasta contém a macro VBA que exporta os dados do BlackArrow/Excel para o arquivo:

C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv

O robô V7.1 lê esse arquivo em tempo real.

## 1. Arquivo da macro

Modulo_BlackArrow_RTD_V71.bas

## 2. Como importar a macro no Excel

1. Abra a planilha do BlackArrow/RTD no Excel.

2. Pressione:

ALT + F11

3. No editor VBA, vá em:

Arquivo > Importar arquivo

4. Selecione:

Modulo_BlackArrow_RTD_V71.bas

5. Salve a planilha como:

Pasta de trabalho habilitada para macro do Excel (*.xlsm)

## 3. Estrutura da planilha

A macro espera os dados na planilha ativa:

Linha 1: cabeçalhos

A1: Ativo
B1: Data
C1: Hora
D1: Último
E1: Abertura
F1: Máximo
G1: Mínimo
H1: Negócios

Linha 2: valores RTD do BlackArrow

A2: símbolo, exemplo MNQM6
B2: data
C2: hora
D2: último preço
E2: abertura
F2: máxima
G2: mínima
H2: negócios

## 4. Macros disponíveis

### ExportarBlackArrowCSV

Exporta uma vez para blackarrow_rtd.csv.

### IniciarExportacaoBlackArrowV71

Inicia exportação automática a cada 1 segundo.

### PararExportacaoBlackArrowV71

Para a exportação automática.

## 5. Como rodar

No Excel:

1. Pressione ALT + F8.
2. Selecione:

IniciarExportacaoBlackArrowV71

3. Clique em Executar.

Depois abra o robô:

RODAR_ROBO_V71_OFICIAL.bat

## 6. Como testar

Depois de iniciar a macro, confira se o arquivo abaixo está atualizando:

C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv

Ele deve ter uma estrutura parecida com:

Ativo;Data;Hora;Último;Abertura;Máximo;Mínimo;Negócios
MNQM6;26/05/2026;03:24:00;29826;...

## 7. Observação importante

Se o projeto for instalado em outra pasta, altere dentro da macro a linha:

Public Const CAMINHO_CSV_V71 As String = "C:\Users\ualac\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv"

para o novo caminho correto.
'''

(PASTA_MACRO / "INSTRUCOES_MACRO_EXCEL.md").write_text(instrucoes, encoding="utf-8")

# ============================================================
# 3. TENTAR COPIAR PLANILHAS XLSM/XLSX RELACIONADAS AO BLACKARROW
# ============================================================

planilhas = []
for padrao in ["*blackarrow*.xls*", "*BlackArrow*.xls*", "*RTD*.xls*", "*rtd*.xls*"]:
    planilhas.extend(BASE.glob(padrao))

planilhas_unicas = []
vistos = set()

for p in planilhas:
    if p.is_file() and p.name not in vistos:
        vistos.add(p.name)
        planilhas_unicas.append(p)

if planilhas_unicas:
    pasta_planilhas = PASTA_MACRO / "PLANILHAS_ENCONTRADAS"
    pasta_planilhas.mkdir(exist_ok=True)

    for p in planilhas_unicas:
        print("Copiando planilha encontrada:", p.name)
        shutil.copy2(p, pasta_planilhas / p.name)
else:
    print("Nenhuma planilha Excel BlackArrow/RTD encontrada automaticamente.")

# ============================================================
# 4. ATUALIZAR README PRINCIPAL
# ============================================================

readme = PACOTE / "README_V71_OFICIAL.md"

texto_extra = r'''

## 10. Macro Excel BlackArrow

O pacote contém a pasta:

MACRO_EXCEL_BLACKARROW

Dentro dela existem:

Modulo_BlackArrow_RTD_V71.bas
INSTRUCOES_MACRO_EXCEL.md

Essa macro é responsável por exportar os dados do Excel/BlackArrow para:

blackarrow_rtd.csv

Sem essa macro, o robô não recebe os dados em tempo real.

Fluxo:

Excel/BlackArrow
↓
Macro ExportarBlackArrowCSV
↓
blackarrow_rtd.csv
↓
Robô V7.1

Para instalar, abra o Excel, pressione ALT + F11 e importe o arquivo:

MACRO_EXCEL_BLACKARROW/Modulo_BlackArrow_RTD_V71.bas

Depois rode a macro:

IniciarExportacaoBlackArrowV71
'''

if readme.exists():
    atual = readme.read_text(encoding="utf-8", errors="ignore")
    if "## 10. Macro Excel BlackArrow" not in atual:
        readme.write_text(atual + texto_extra, encoding="utf-8")

# ============================================================
# 5. ATUALIZAR MANIFESTO
# ============================================================

manifesto = PACOTE / "MANIFESTO_ARQUIVOS.csv"

with manifesto.open("w", encoding="utf-8") as f:
    f.write("arquivo,tamanho_bytes,modificado\n")
    for item in PACOTE.rglob("*"):
        if item.is_file():
            stat = item.stat()
            rel = item.relative_to(PACOTE)
            f.write(f'"{rel}",{stat.st_size},"{datetime.fromtimestamp(stat.st_mtime)}"\n')

# ============================================================
# 6. RECRIAR ZIP
# ============================================================

if ZIP_FINAL.exists():
    ZIP_FINAL.unlink()

with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED) as z:
    for item in PACOTE.rglob("*"):
        if item.is_file():
            z.write(item, item.relative_to(PACOTE))

print()
print("=" * 80)
print("MACRO ADICIONADA AO PACOTE COM SUCESSO")
print("=" * 80)
print("Pasta macro:", PASTA_MACRO)
print("ZIP atualizado:", ZIP_FINAL)
print()
print("Arquivos adicionados:")
print("- MACRO_EXCEL_BLACKARROW/Modulo_BlackArrow_RTD_V71.bas")
print("- MACRO_EXCEL_BLACKARROW/INSTRUCOES_MACRO_EXCEL.md")
print()
