# Relatorio de pesquisa V7.1 para TradingView

Este relatorio consolida os candidatos de pesquisa criados para MNQ no TradingView.

Importante: nenhum candidato abaixo altera o robo V7.1 oficial. Todos sao pesquisa.

## Criterio atual

O objetivo e encontrar uma configuracao com:

- acerto alto, idealmente acima de 85%;
- lucro positivo;
- drawdown baixo;
- frequencia razoavel;
- replicacao no TradingView;
- menor sinal possivel de overfitting.

## Ranking pratico

| Prioridade | Candidato | Timeframe | Arquivo Pine | Trades | Winrate | Pontos | DD | PF | Leitura |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Calendario DOW 230-85 | 2m | `V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine` | 233 | 87.55% nos ultimos 365d | 6909.0 | -316.5 | 3.04 | Melhor candidato de alta frequencia; precisa confirmar no TradingView |
| 2 | Regime refino 93 - perfil equilibrado | 2m | `V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine` | 139 | 94.24% nos ultimos 365d | 5679.5 | -183.5 | 7.07 | Melhor acerto/DD, mas com frequencia menor |
| 3 | 04:06 reversao multiano | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` | 122 | 86.07% | 3313.5 | -183.5 | 2.67 | Melhor robustez multiano simples |
| 4 | Regime 191/89 multiano | 2m | `V71_PESQUISA_REGIME_191_89_MULTIANO_TV_2MIN.pine` | 191 | 89.01% nos ultimos 365d | 6128.0 | -468.0 | 3.49 | Frequencia maior, mas 2024 ficou fraco |
| 5 | 04:06 reversao sem filtro | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` perfil 01 | 373 | 80.16% | 6441.5 | -550.5 | 1.74 | Frequencia alta e anos positivos, mas abaixo do alvo de acerto |
| 6 | Calendario top tokens | 2m | `V71_PESQUISA_TV_CALENDARIO_TOP_TOKENS_3H.pine` | 54 a 160 | 80% a 87% | variavel | variavel | variavel | Bom para estudar blocos de horario, nao final |

## Candidato novo: Calendario DOW 230-85

Arquivo:

`V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- perfil 01: `01 Max 365d 233tr 87pct`
- perfil 02: `02 Recente forte 234tr 85pct`

Horarios/direcoes:

- segunda 04:02 BUY
- terca 03:12 SELL
- quarta 02:56 BUY
- quinta 04:30 SELL
- sexta 09:30 BUY

Filtros por perfil:

- perfil 01: quarta 02:56 com `dmi_gap >= 3.5237` e quinta 04:30 com `ema200_slope10 <= 4.7472`
- perfil 02: segunda 04:02 com `vwap_slope10 <= 4.6748` e terca 03:12 com `dist_vwap <= 22.2546`

Metricas locais:

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 01 Max 365d | Ultimos 365d | 233 | 87.55% | 6909.0 | -316.5 | 3.04 |
| 01 Max 365d | Ultimos 90d | 63 | 84.13% | 1506.5 | -300.5 | 2.29 |
| 01 Max 365d | Ultimos 30d | 22 | 81.82% | 441.0 | -234.0 | 1.94 |
| 01 Max 365d | 2024 | 185 | 75.68% | 1805.0 | n/d | n/d |
| 01 Max 365d | 2025 | 230 | 83.04% | 5082.5 | n/d | n/d |
| 01 Max 365d | 2026 | 92 | 85.87% | 2468.5 | n/d | n/d |
| 02 Recente forte | Ultimos 365d | 234 | 85.90% | 6289.5 | -316.5 | 2.63 |
| 02 Recente forte | Ultimos 90d | 56 | 89.29% | 1823.0 | -300.5 | 3.60 |
| 02 Recente forte | Ultimos 30d | 21 | 90.48% | 725.5 | -117.0 | 4.10 |
| 02 Recente forte | 2024 | 191 | 74.87% | 1605.5 | n/d | n/d |
| 02 Recente forte | 2025 | 233 | 81.12% | 4396.5 | n/d | n/d |
| 02 Recente forte | 2026 | 88 | 87.50% | 2601.5 | n/d | n/d |

Arquivo de conferencia local:

`pesquisa_v71_0348_6min/REFINO_CALENDARIO_DOW_230_85.md`

Ponto forte:

- e o primeiro candidato que bate a faixa desejada de 230 a 250 trades e passa de 85% nos ultimos 365 dias.
- lucro, DD e PF locais ficaram melhores que os candidatos frequentes anteriores.
- o perfil 02 preserva 85%+ no anual e melhora bastante os recortes de 90 e 30 dias.

Ponto fraco:

- os anos completos 2024 e 2025 ficam abaixo de 85%, embora positivos.
- por usar calendario por dia da semana, precisa ser confirmado no TradingView antes de qualquer decisao operacional.
- ainda nao deve substituir o oficial.

## Candidato novo: Regime refino 93

Arquivo:

`V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- perfil recomendado: `02 Equilibrado 139 94pct`

Metricas locais:

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 01 Refino 157 | 365d | 157 | 92.99% | 6086.0 | -234.0 | 5.73 |
| 01 Refino 157 | 2024 | 146 | 69.86% | 3.0 | -1064.0 | 1.00 |
| 02 Equilibrado 139 | 365d | 139 | 94.24% | 5679.5 | -183.5 | 7.07 |
| 02 Equilibrado 139 | 2024 | 127 | 71.65% | 383.5 | -697.0 | 1.09 |
| 02 Equilibrado 139 | 2025 | 155 | 90.32% | 5315.0 | -234.0 | 4.03 |
| 02 Equilibrado 139 | 2026 | 45 | 91.11% | 1602.5 | -183.5 | 4.42 |
| 03 Frequente 191 | 365d | 191 | 89.01% | 6128.0 | -468.0 | 3.49 |

Arquivo de conferencia local:

`pesquisa_v71_0348_6min/VALIDACAO_REGIME_REFINO_93.md`

Esse arquivo mostra as primeiras entradas esperadas por perfil. O CSV local ignorado pelo Git, `validacao_regime_refino_93_trades.csv`, contem a lista completa de entradas para comparar com o export do TradingView.

Auditorias complementares:

- `pesquisa_v71_0348_6min/AUDITORIA_REGIME_REFINO_93_FRAGILIDADE.md`
- `pesquisa_v71_0348_6min/ABLACAO_REGIME_REFINO_93.md`

A ablacao testou todas as combinacoes dos modulos atuais do Refino 93. Dentro dessa familia, nao apareceu nenhum cenario com 220 a 260 trades nos ultimos 365 dias e winrate acima de 80%; portanto, para buscar 230 a 250 trades com 85%+, a proxima etapa precisa procurar novos horarios/indicadores em vez de apenas apertar os filtros atuais.

Ponto forte:

- o perfil equilibrado tem a melhor relacao atual entre acerto, DD e PF nos ultimos 365 dias.
- ele melhora a fragilidade do perfil 157 em 2024.

Ponto fraco:

- ainda nao chega em 230 a 250 trades por ano.
- a validacao precisa ser confirmada no TradingView, porque pequenas diferencas de dado/execucao podem mudar os numeros.
- a meta de 230 a 250 trades com 85%+ nao apareceu em nenhuma combinacao dos modulos atuais.

## Candidato 2: 04:06 reversao multiano

Arquivo:

`V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `6m`
- modo: Backtesting Profundo
- perfil recomendado: `02 Multiano 86pct`

Metricas locais do perfil recomendado:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Total 2024-2026 | 122 | 86.07% | 3313.5 | -183.5 | 2.67 |
| 2024 | 36 | 86.11% | 980.5 | -133.0 | 2.68 |
| 2025 | 65 | 84.62% | 1607.5 | -183.5 | 2.37 |
| 2026 | 21 | 90.48% | 725.5 | -183.5 | 4.10 |

Ponto forte:

- e o candidato com melhor equilibrio entre acerto alto e robustez por ano.

Ponto fraco:

- frequencia menor que a meta de 230 a 250 trades por ano.

## Candidato 3: Regime 191/89 multiano

Arquivo:

`V71_PESQUISA_REGIME_191_89_MULTIANO_TV_2MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo

Metricas locais:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Total 2024-2026 | 453 | 79.69% | 7466.5 | -1348.5 | 1.69 |
| 2024 | 175 | 70.29% | 127.5 | -1348.5 | 1.02 |
| 2025 | 216 | 85.19% | 5548.0 | -468.0 | 2.48 |
| 2026 | 62 | 87.10% | 1791.0 | -234.0 | 2.91 |
| Ultimos 365d | 191 | 89.01% | 6128.0 | -468.0 | 3.49 |

Ponto forte:

- melhor candidato nos ultimos 365 dias, com frequencia maior.

Ponto fraco:

- 2024 quase empatou, com DD alto. Nao deve ser promovido sem validacao no TradingView.

## Candidato 4: 04:06 reversao sem filtro

Mesmo arquivo do candidato 1, perfil:

`01 Sem filtro 80pct`

Metricas locais:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Total 2024-2026 | 373 | 80.16% | 6441.5 | -550.5 | 1.74 |
| 2024 | 123 | 80.49% | 2191.5 | -316.5 | 1.78 |
| 2025 | 183 | 79.78% | 3044.0 | -550.5 | 1.70 |
| 2026 | 67 | 80.60% | 1206.0 | -300.5 | 1.79 |

Ponto forte:

- frequencia e estabilidade por ano melhores.

Ponto fraco:

- nao chega no alvo de 85% de acerto.

## Conclusao provisoria

Melhor candidato de alta frequencia para teste serio agora:

`V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine`.

Melhor candidato de alta acertividade/DD:

`V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine`, perfil `02 Equilibrado 139 94pct`.

Melhor candidato simples por robustez multiano:

`V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine`, perfil `02 Multiano 86pct`.

Melhor candidato para tentar mais frequencia:

`V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine`.

Regra pratica:

- se o TradingView confirmar o Calendario DOW 230-85 perto de 233 trades e 87%, ele vira a melhor linha de pesquisa de frequencia;
- se o TradingView confirmar o 04:06 multiano perto de 86%, ele vira a linha mais segura de pesquisa;
- se o TradingView confirmar o regime 191/89 nos ultimos 365 dias, ele vira candidato de alta performance, mas ainda precisa controle de risco por causa de 2024;
- nenhum candidato deve substituir o oficial sem aprovacao explicita.

## Proximo teste recomendado no TradingView

1. Testar `V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine` em `MNQ1!`, `2m`.
2. Conferir se 365 dias fica proximo de 233 trades, 87.55%, +6909 pontos, DD -316.5 e PF 3.04.
3. Conferir 90 dias e 30 dias no TradingView.
4. Testar `V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine` em `MNQ1!`, `2m`, perfil `02 Equilibrado 139 94pct`.
5. Testar `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` em `MNQ1!`, `6m`, perfil `02 Multiano 86pct`.
6. Comparar as metricas locais acima com o relatorio do TradingView.
