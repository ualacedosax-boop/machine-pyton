# machine-pyton — Robô de Trading ML para MNQ

Robô de leitura de sinal em tempo real baseado em Machine Learning para o contrato **MNQ (Micro Nasdaq Futures)**.

Versão oficial atual: **V7.1** — operável, com ajustes em andamento.

---

## Como funciona

O robô lê os dados do **BlackArrow** exportados pelo Excel via macro RTD, converte em candles de 2 minutos, calcula features e passa por três camadas de modelos ML antes de gerar um sinal.

```
Excel / BlackArrow
       ↓  (macro ExportarBlackArrowCSV)
blackarrow_rtd.csv
       ↓
blackarrow_ticks.csv  →  blackarrow_candles_2min.csv
       ↓
Features do candle atual
       ↓
Score V3 + Modelo V7 Oficial + Filtro V5.3
       ↓
ultimo_sinal_v71_blackarrow.json  +  sinal.txt
       ↓
Monitor visual e sonoro (PowerShell)
```

O robô **não envia ordens diretamente**. Ele gera arquivos de sinal que o operador lê ou que uma ponte de execução consome.

---

## Configuração operacional (V7.1)

| Parâmetro | Valor |
|---|---|
| Take profit | 50,5 pontos |
| Stop loss | 117,0 pontos |
| Prob mínima V5.1 | 0,59 |
| Prob mínima V5.5 | 0,425 |
| Score BUY mínimo | 0,74 |
| Score SELL mínimo | 0,50 |
| Janela operacional | 02:00 – 06:00 (horário SP) |
| Bloqueio | 04:30 – 04:45 |
| Máx. trades/dia | 3 |
| Parar após loss | sim |

---

## Modelos utilizados

| Modelo | Arquivo |
|---|---|
| Score V3 | `saida_ml_entradas_video_v3/modelo_v3_score.joblib` |
| V7 Oficial | `OPERACIONAL_V7_OFICIAL/modelos_final_v7_oficial.joblib` |
| Filtro V5.3 | `saida_v5_3_validacao_2025_teste_2026/modelo_final_v5_3.joblib` |

---

## Como rodar

**1. Instalar dependências**
```bash
pip install -r requirements.txt
```

**2. Iniciar o robô**
```
RODAR_ROBO_V71_OFICIAL.bat
```

**3. Iniciar o monitor** (em outra janela)
```
RODAR_MONITOR_V71_OFICIAL.bat
```

O monitor exibe os scores em tempo real e emite alarme sonoro com voz do Windows ao detectar BUY ou SELL.

---

## Sinais gerados

| Sinal | Significado |
|---|---|
| `buy` | Entrada de compra aprovada por todos os filtros |
| `sell` | Entrada de venda aprovada por todos os filtros |
| `none` | Robô funcionando, nenhuma entrada aprovada no momento |

O estado completo está em `ultimo_sinal_v71_blackarrow.json`. Campos mais importantes:

- `sinal` — buy / sell / none
- `motivo` — razão do none ou do sinal
- `score_BUY` / `score_SELL`
- `prob_v5_3`
- `horario_operacional_valido`
- `candles_disponiveis` (precisa ser > 220)

---

## Pré-requisito: macro Excel BlackArrow

O robô depende de a macro `IniciarExportacaoBlackArrowCSV` estar rodando no Excel para exportar `blackarrow_rtd.csv` continuamente.

**Para instalar a macro:**
1. Abra o Excel com o BlackArrow ativo
2. Pressione `ALT + F11`
3. Importe o arquivo `MACRO_EXCEL_BLACKARROW/Modulo_BlackArrow_RTD_V71.bas`
4. Execute a macro `IniciarExportacaoBlackArrowV71`

**Colunas esperadas no CSV exportado:**
```
Ativo, Data, Hora, Último, Abertura, Máximo, Mínimo, Negócios
```

---

## Erros conhecidos (em resolução)

| Erro | Causa | Correção |
|---|---|---|
| `KeyError: DataHora_SP` | CSV de ticks sem cabeçalho | `python forcar_cabecalho_ticks_v71.py` |
| Candle travado em data futura | Sessão noturna com data errada | `python corrigir_sessao_noturna_v71.py` + `python cortar_futuro_candles_v71.py` |
| `candles_insuficientes` | Menos de ~220 candles disponíveis | Deixar o BlackArrow rodar mais tempo ou carregar histórico |

---

## Estrutura principal

```
machine-pyton/
├── sinal_v71_blackarrow_tempo_real_log_inteligente.py  # robô principal
├── RODAR_ROBO_V71_OFICIAL.bat                          # atalho para rodar
├── RODAR_MONITOR_V71_OFICIAL.bat                       # atalho do monitor
├── PACOTE_V71_OFICIAL_REPLICACAO_*/                    # pacote de replicação completo
├── OPERACIONAL_V7_OFICIAL/                             # modelos V7
├── saida_v5_3_validacao_2025_teste_2026/               # modelo filtro V5.3
├── saida_ml_entradas_video_v3/                         # modelo score V3
└── requirements.txt
```

---

## Dependências principais

- Python 3.x
- scikit-learn 1.8
- pandas 3.0
- numpy 2.2
- joblib 1.5
- matplotlib 3.10
