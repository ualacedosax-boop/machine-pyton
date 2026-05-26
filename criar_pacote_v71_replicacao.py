from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys
import os
import zipfile

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")
DATA = datetime.now().strftime("%Y%m%d_%H%M%S")

NOME_PACOTE = f"PACOTE_V71_OFICIAL_REPLICACAO_{DATA}"
DESTINO = BASE / NOME_PACOTE
ZIP_FINAL = BASE / f"{NOME_PACOTE}.zip"

DESTINO.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("CRIANDO PACOTE V7.1 OFICIAL")
print("=" * 80)
print("Pasta destino:", DESTINO)
print("ZIP final    :", ZIP_FINAL)
print()

# ============================================================
# 1. PASTAS PRINCIPAIS
# ============================================================

pastas = [
    "operacional_v71_oficial",
    "OPERACIONAL_V7_OFICIAL",
    "saida_v5_3_validacao_2025_teste_2026",
    "saida_ml_entradas_video_v3",
]

for pasta in pastas:
    origem = BASE / pasta
    alvo = DESTINO / pasta

    if origem.exists():
        print(f"Copiando pasta: {pasta}")
        if alvo.exists():
            shutil.rmtree(alvo)
        shutil.copytree(origem, alvo)
    else:
        print(f"ATENÇÃO: pasta não encontrada: {pasta}")

# ============================================================
# 2. ARQUIVOS PRINCIPAIS
# ============================================================

arquivos = [
    "sinal_v71_blackarrow_tempo_real_log_inteligente.py",
    "RODAR_ROBO_V71_OFICIAL.bat",
    "RODAR_MONITOR_V71_OFICIAL.bat",
    "monitor_v71_oficial.ps1",
    "blackarrow_rtd.csv",
    "forcar_cabecalho_ticks_v71.py",
    "forcar_cabecalho_candles_v71.py",
    "corrigir_sessao_noturna_v71.py",
    "cortar_futuro_candles_v71.py",
    "patch_corrigir_leitura_candles_v71.py",
]

for arq in arquivos:
    origem = BASE / arq
    if origem.exists():
        print(f"Copiando arquivo: {arq}")
        shutil.copy2(origem, DESTINO / arq)
    else:
        print(f"ATENÇÃO: arquivo não encontrado: {arq}")

# ============================================================
# 3. REQUIREMENTS
# ============================================================

print("Gerando requirements.txt...")

req_path = DESTINO / "requirements.txt"

try:
    r = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        check=False
    )
    if r.stdout.strip():
        req_path.write_text(r.stdout, encoding="utf-8")
    else:
        req_path.write_text(
            "pandas\nnumpy\nscikit-learn\njoblib\nopenpyxl\n",
            encoding="utf-8"
        )
except Exception:
    req_path.write_text(
        "pandas\nnumpy\nscikit-learn\njoblib\nopenpyxl\n",
        encoding="utf-8"
    )

# ============================================================
# 4. README DETALHADO
# ============================================================

readme = r"""
# PACOTE V7.1 OFICIAL - BLACKARROW TEMPO REAL

Este pacote contém os arquivos necessários para replicar o robô V7.1 Oficial em outro computador.

## 1. O que é o V7.1

O V7.1 é um robô de leitura em tempo real do BlackArrow que transforma os dados exportados por RTD/CSV em candles de 2 minutos, calcula features, roda modelos de machine learning e gera um sinal operacional.

Ele não envia ordem diretamente por padrão. Ele gera arquivos de sinal para serem lidos pelo monitor ou por uma ponte de execução.

## 2. Fluxo de funcionamento

Fluxo principal:

BlackArrow/Excel
↓
blackarrow_rtd.csv
↓
operacional_v71_oficial/blackarrow_ticks.csv
↓
operacional_v71_oficial/blackarrow_candles_2min.csv
↓
features do candle
↓
Modelo V7 + filtro V5.3
↓
ultimo_sinal_v71_blackarrow.json + sinal.txt
↓
monitor visual/sonoro

## 3. Modelos usados

Modelo V3:

saida_ml_entradas_video_v3/modelo_v3_score.joblib

Modelo V7 Oficial:

OPERACIONAL_V7_OFICIAL/modelos_final_v7_oficial.joblib

Filtro V5.3:

saida_v5_3_validacao_2025_teste_2026/modelo_final_v5_3.joblib

## 4. Configuração operacional

Configuração usada no V7.1:

take = 50.5 pontos
stop = 117.0 pontos
prob_v51_min = 0.59
prob_v55_min = 0.425
score_buy_min = 0.74
score_sell_min = 0.50
hora_inicio = 02:00
hora_fim = 06:00
bloqueio = 04:30 até 04:45
max_trades_dia = 3
parar_apos_loss = true

## 5. Sinais possíveis

O campo principal é:

sinal

Valores possíveis:

buy
sell
none

Quando aparecer `none`, o robô está funcionando, mas não encontrou entrada aprovada.

Exemplo normal sem entrada:

sinal: none
motivo: score_buy_sell_nao_passou

Exemplo de entrada:

sinal: buy

ou:

sinal: sell

## 6. Arquivos principais

sinal_v71_blackarrow_tempo_real_log_inteligente.py

Arquivo principal do robô.

RODAR_ROBO_V71_OFICIAL.bat

Arquivo para iniciar o robô.

RODAR_MONITOR_V71_OFICIAL.bat

Arquivo para iniciar o monitor.

operacional_v71_oficial

Pasta operacional. Contém ticks, candles, sinal, JSON, logs e aprendizado.

OPERACIONAL_V7_OFICIAL

Pasta com modelos oficiais do V7.

saida_v5_3_validacao_2025_teste_2026

Pasta com o modelo filtro V5.3.

saida_ml_entradas_video_v3

Pasta com o modelo V3.

## 7. Arquivo JSON principal

O robô grava o estado atual em:

operacional_v71_oficial/ultimo_sinal_v71_blackarrow.json

Campos importantes:

sinal
motivo
datahora_ultimo_candle_sp
horario_operacional_valido
dentro_janela_v71_oficial
candles_disponiveis
features_v3_faltando
features_v3_validas
score_BUY
score_SELL
prob_v5_3

Funcionando corretamente:

horario_operacional_valido = true
dentro_janela_v71_oficial = true
candles_disponiveis maior que 220

## 8. Erros comuns

### ERRO: DataHora_SP

Causa provável:

O arquivo blackarrow_ticks.csv ou blackarrow_candles_2min.csv está sem cabeçalho.

Correção:

python forcar_cabecalho_ticks_v71.py

Se o problema for nos candles:

python forcar_cabecalho_candles_v71.py

### Candle travado em data futura

Exemplo:

2026-05-27 01:58

Causa:

Mistura de sessão noturna com data errada.

Correção:

python corrigir_sessao_noturna_v71.py
python cortar_futuro_candles_v71.py

### Candles insuficientes

O robô precisa de aproximadamente 220 candles para calcular as features.

Se aparecer candles_insuficientes, deixe o BlackArrow rodando mais tempo ou carregue histórico suficiente.

## 9. Observação importante

Este pacote replica o robô, mas o novo computador precisa ter o BlackArrow/Excel exportando o arquivo:

blackarrow_rtd.csv

na pasta raiz do projeto.

Colunas esperadas:

Ativo
Data
Hora
Último
Abertura
Máximo
Mínimo
Negócios
"""

(DESTINO / "README_V71_OFICIAL.md").write_text(readme, encoding="utf-8")

# ============================================================
# 5. INSTALAÇÃO PASSO A PASSO
# ============================================================

instalacao = r"""
# INSTALAÇÃO DO V7.1 EM OUTRA MÁQUINA

## 1. Instalar Python

Instale Python 3.11, 3.12 ou 3.13.

Durante a instalação, marque:

Add Python to PATH

Depois teste no PowerShell:

python --version

## 2. Copiar o pacote

Copie a pasta do pacote para:

C:\Users\SEU_USUARIO\Documents\2025\Mercado\machine-pyton

Se usar outro caminho, será necessário editar os caminhos nos arquivos .bat e no arquivo Python principal.

## 3. Criar ambiente virtual

No PowerShell:

cd "C:\Users\SEU_USUARIO\Documents\2025\Mercado\machine-pyton"

python -m venv .venv

Ativar:

.\.venv\Scripts\Activate.ps1

Se der erro de permissão:

Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Depois tente ativar novamente.

## 4. Instalar dependências

Com o ambiente virtual ativo:

pip install --upgrade pip

pip install -r requirements.txt

Se o requirements falhar, instalar manualmente os principais:

pip install pandas numpy scikit-learn joblib openpyxl

## 5. Configurar BlackArrow/Excel

O BlackArrow ou Excel precisa gerar o arquivo:

blackarrow_rtd.csv

na pasta raiz do projeto:

C:\Users\SEU_USUARIO\Documents\2025\Mercado\machine-pyton\blackarrow_rtd.csv

Esse arquivo precisa atualizar em tempo real com:

Ativo
Data
Hora
Último
Abertura
Máximo
Mínimo
Negócios

## 6. Rodar o robô

No PowerShell:

cd "C:\Users\SEU_USUARIO\Documents\2025\Mercado\machine-pyton"

.\RODAR_ROBO_V71_OFICIAL.bat

## 7. Verificar se está funcionando

Em outra janela do PowerShell:

cd "C:\Users\SEU_USUARIO\Documents\2025\Mercado\machine-pyton"

Get-Content ".\operacional_v71_oficial\ultimo_sinal_v71_blackarrow.json"

Verificar:

horario_operacional_valido
dentro_janela_v71_oficial
candles_disponiveis
sinal
motivo

## 8. Rodar o monitor

Depois que o robô estiver sem erro:

.\RODAR_MONITOR_V71_OFICIAL.bat

## 9. Como parar

Na janela do robô ou monitor:

CTRL + C

Se perguntar:

Deseja finalizar o arquivo em lotes (S/N)?

Digite:

S

## 10. Primeiro teste recomendado

Antes de operar real, deixar o robô rodando em modo observação e conferir:

1. O JSON atualiza.
2. O candle atual acompanha o horário real.
3. O sinal permanece none quando não há entrada.
4. Quando aparecer buy ou sell, o monitor alerta corretamente.
5. O arquivo log_sinal_v71_blackarrow.csv registra os sinais.

## 11. Correções úteis

Se der erro DataHora_SP:

python forcar_cabecalho_ticks_v71.py

Se candle ficar em data futura:

python corrigir_sessao_noturna_v71.py
python cortar_futuro_candles_v71.py

Se o robô não encontrar modelos, conferir se existem as pastas:

OPERACIONAL_V7_OFICIAL
saida_v5_3_validacao_2025_teste_2026
saida_ml_entradas_video_v3
"""

(DESTINO / "INSTALACAO_PASSO_A_PASSO.md").write_text(instalacao, encoding="utf-8")

# ============================================================
# 6. MANIFESTO
# ============================================================

manifesto = DESTINO / "MANIFESTO_ARQUIVOS.csv"

with manifesto.open("w", encoding="utf-8") as f:
    f.write("arquivo,tamanho_bytes,modificado\n")
    for item in DESTINO.rglob("*"):
        if item.is_file():
            stat = item.stat()
            rel = item.relative_to(DESTINO)
            f.write(f'"{rel}",{stat.st_size},"{datetime.fromtimestamp(stat.st_mtime)}"\n')

# ============================================================
# 7. ZIP
# ============================================================

if ZIP_FINAL.exists():
    ZIP_FINAL.unlink()

print()
print("Compactando ZIP...")

with zipfile.ZipFile(ZIP_FINAL, "w", zipfile.ZIP_DEFLATED) as z:
    for item in DESTINO.rglob("*"):
        if item.is_file():
            z.write(item, item.relative_to(DESTINO))

print()
print("=" * 80)
print("PACOTE CRIADO COM SUCESSO")
print("=" * 80)
print("Pasta:", DESTINO)
print("ZIP  :", ZIP_FINAL)
print()
print("Documentação criada:")
print("- README_V71_OFICIAL.md")
print("- INSTALACAO_PASSO_A_PASSO.md")
print("- MANIFESTO_ARQUIVOS.csv")
print()
