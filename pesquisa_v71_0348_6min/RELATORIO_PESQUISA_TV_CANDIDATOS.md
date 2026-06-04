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
- regra anti-vazamento: 2026 nao pode participar de quantis, score, folds, escolha de filtros ou treino; 2026 fica apenas como teste/holdout.

## Ranking pratico

| Prioridade | Candidato | Timeframe | Arquivo Pine | Trades | Winrate | Pontos | DD | PF | Leitura |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| 0 | Confluencia 7 indicadores 21:02 | 2m | `V71_CONFLUENCIA_7INDICADORES_ROTACAO_TV_2MIN.pine` | perfil 01: 53 TV; perfil 02: 53 TV | perfil 02 TV: 71.70% anual; 76.92% 90d; 100.00% 30d | perfil 02 TV: +328 USD anual; +308 USD 90d; +505 USD 30d | -777 USD TV anual | 1.093 TV anual | Perfis 01 e 02 reprovaram no anual; seguir para perfil 03 |
| 1 | Rotacao 2024-2025 Holdout2026 | 2m | `V71_ROTACAO_2024_2025_HOLDOUT2026_TV_2MIN.pine` | 197/92/146/114/104 TV | melhor: 80.20% anual perfil 01; 87.50% 30d perfil 04 | melhor anual +6596.50 USD perfil 01; perfil 05 -886.00 USD | melhor DD anual -747.00 USD perfil 02; perfil 05 -1773.00 USD | melhor PF anual 1.705 perfil 01; perfil 05 0.889 | Bateria 01-05 encerrada: nenhum perfil promove; 04 fica so como melhor recente |
| 2 | Rotacao 2M/1M Manha Refino | 2m | `V71_ROTACAO_2M1M_MANHA_REFINO_TV_2MIN.pine` | 61 a 106 local | 81.97% a 84.51% local nos ultimos 365d | +1238 a +1846.5 pts local | n/d | n/d | Exploratorio; supersedido porque foi criado antes da regra 2026 somente holdout |
| 3 | Rotacao 2M/1M Noite+Manha | 2m | `V71_ROTACAO_2M1M_NOITE_MANHA_TV_2MIN.pine` | 195 TV combo | 73.33% TV nos ultimos 365d | +2275 USD TV | -2750 USD TV | 1.187 TV | Combo reprovado no TV; noite isolada positiva recente, fraca no anual |
| 4 | Diagnostico TVSafe por blocos | 2m | `V71_DIAGNOSTICO_TVSAFE_BLOCOS_REWRITE_2MIN.pine` | diagnostico | n/d | n/d | n/d | n/d | Caminho secundario: isolar se a perda recente vem da quarta 02:56, sexta 09:30 ou da combinacao |
| 5 | Rewrite TVSafe indicadores 95 | 2m | `V71_REWRITE_TVSAFE_INDICADORES_95_TV_2MIN.pine` | 46 TV perfil 05 | 86.96% TV nos ultimos 365d | +2636 USD TV | -827.50 USD TV | 2.877 TV | Operavel, mas perfis 01/04/05 reprovaram no 90d/30d |
| 6 | Destrava TV minimo smoke/horarios | 2m | `V71_DESTRAVA_TV_MINIMO_SMOKE_HORARIOS.pine` | 3547 TV smoke | 47.90% TV | -389 USD TV | -1661.50 USD TV | 0.983 TV | Confirmou que o TV executa; e diagnostico, nao estrategia |
| 7 | Destrava TV 3H escada operavel | 2m | `V71_DESTRAVA_TV_3H_ESCADA_OPERAVEL.pine` | diagnostico | n/d | n/d | n/d | n/d | Travou; provavelmente complexo demais para diagnostico inicial |
| 8 | DMI3 Take45 robusto | 2m | `V71_PESQUISA_TV_3H_DMI3_TAKE45_ROBUSTO.pine` | 132 | 86.36% local nos ultimos 365d | 3081.0 | -331.5 | 2.463 | Travou no teste direto; precisa passar por diagnostico minimo antes |
| 9 | Regime refino 93 - perfil equilibrado | 2m | `V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine` | 139 | 94.24% local nos ultimos 365d | 5679.5 | -183.5 | 7.07 | Reprovado por operabilidade: tambem travou no TradingView |
| 10 | Regime 191/89 multiano | 2m | `V71_PESQUISA_REGIME_191_89_TV_LIMPO.pine` | 191 | 89.01% local nos ultimos 365d | 6128.0 | -468.0 | 3.49 | Reprovado por operabilidade: smoke minimo funciona, mas versoes Regime travaram no TV |
| 11 | 04:06 reversao multiano | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` | 122 | 86.07% local | 3313.5 | -183.5 | 2.67 | Melhor robustez multiano simples, mas ainda sem confirmacao TV recente |
| 12 | Calendario DOW alta acerto - perfil 05 | 2m | `V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine` | 152 TV | 81.58% TV nos ultimos 365d | +5972 USD TV | -1168 USD TV | 1.911 TV | Nao confirmou acerto alto no TV |
| 13 | Calendario DOW robusto anual - perfil 04 | 2m | `V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine` | 224 TV | 80.80% TV nos ultimos 365d | +8219 USD TV | -1206 USD TV | 1.817 TV | Nao confirmou acerto alto no TV; 90d fraco |
| 14 | Calendario DOW 230-85 - perfil 01 | 2m | `V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine` | 240 TV | 81.25% TV nos ultimos 365d | +9165 USD TV | -1105 USD TV | 1.87 TV | Reprovado no TradingView apesar do local forte |
| 15 | 04:06 reversao sem filtro | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` perfil 01 | 373 | 80.16% local | 6441.5 | -550.5 | 1.74 | Frequencia alta e anos positivos, mas abaixo do alvo de acerto |
| 16 | Calendario top tokens | 2m | `V71_PESQUISA_TV_CALENDARIO_TOP_TOKENS_3H.pine` | 54 a 160 | 80% a 87% local | variavel | variavel | variavel | Bom para estudar blocos de horario, nao final |

## Candidato novo: Confluencia 7 indicadores - rotacao 2024-2025

Arquivo:

`V71_CONFLUENCIA_7INDICADORES_ROTACAO_TV_2MIN.pine`

Metodo:

- cada regra usa exatamente 7 votos de indicadores;
- o sinal exige pelo menos 5 votos alinhados com BUY/SELL;
- busca focada em noite em torno de `20:54/21:00` e manha em torno de `10:30/11:54`;
- rotacao mensal dentro de 2024-2025: treina dois meses e testa o terceiro;
- 2026 nao entrou em quantis, score, folds ou escolha de parametros; foi calculado somente depois como holdout cego.

Melhor bloco encontrado:

| Perfil | Regra | Folds 2M/1M | Modelo 2024-2025 | Holdout 2026 | 90d | 30d | Leitura |
|---|---|---:|---|---|---|---|---|
| 01 Noite 2102 SELL | `21:02 SELL`, 5 de 7 votos, `ADX >= 20`, `DMI gap >= 4` | 16/20 | 75tr, 85.33%, +1945.0 pts | 20tr, 85.00%, +507.5 pts | 14tr, 85.71%, +372.0 pts | 5tr, 100.00%, +252.5 pts | Testado no TV e reprovado |
| 02 Noite 2102 SELL | variante com DMI/ROC10/candle | 15/20 | 84tr, 85.71%, +2232.0 pts | 20tr, 85.00%, +507.5 pts | 14tr, 85.71%, +372.0 pts | 5tr, 100.00%, +252.5 pts | Testado no TV: 30d forte, anual reprovado |
| 03 Noite 2102 SELL | variante com DMI/MACD/candle | 15/20 | 76tr, 86.84%, +2163.0 pts | 20tr, 85.00%, +507.5 pts | 14tr, 85.71%, +372.0 pts | 5tr, 100.00%, +252.5 pts | Terceiro teste |
| 05 Manha 1152 BUY | diagnostico de manha | 16/20 | 98tr, 83.67%, +2269.0 pts | 15tr, 73.33%, +87.5 pts | 12tr, 66.67%, -64.0 pts | 2tr, 100.00%, +101.0 pts | Nao promover; diagnostico |

Decisao:

- nao promover o perfil `01 Noite 2102 SELL 75tr 85pct`;
- nao promover o perfil `02 Noite 2102 SELL 84tr 86pct`;
- o Pine foi atualizado para abrir por padrao no perfil `03 Noite 2102 SELL 76tr 87pct`;
- testar o perfil `03` para ver se a variante replica melhor;
- nao promover o combo ainda: no local ele ficou forte em 2024-2025, mas caiu para 77.78% no holdout 2026 e 74.07% nos 90d;
- manter o V7.1 oficial sem alteracao.

Teste TradingView do perfil `01 Noite 2102 SELL 75tr 85pct`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 53 | 69.81% | -7.00 USD | -848.00 USD | 0.998 | Reprovado: anual praticamente neutro e acerto muito abaixo do local |
| Ultimos 90d | 14 | 71.43% | +74.00 USD | -619.00 USD | 1.079 | Fraco; sem vantagem suficiente |
| Ultimos 30d | 6 | 83.33% | +271.00 USD | -321.00 USD | 2.158 | Recente positivo, mas poucos trades e ainda abaixo do alvo anual |

Teste TradingView do perfil `02 Noite 2102 SELL 84tr 86pct`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 53 | 71.70% | +328.00 USD | -777.00 USD | 1.093 | Reprovado: anual positivo, mas acerto/PF fracos |
| Ultimos 90d | 13 | 76.92% | +308.00 USD | -426.50 USD | 1.439 | Melhor que o perfil 01, mas ainda abaixo do alvo |
| Ultimos 30d | 5 | 100.00% | +505.00 USD | -87.00 USD | n/d | Excelente recente, mas pouca amostra |

## Candidato novo: Rotacao 2024-2025 Holdout2026

Arquivo:

`V71_ROTACAO_2024_2025_HOLDOUT2026_TV_2MIN.pine`

Metodo:

- filtros e thresholds criados somente com 2024-2025;
- folds 2M/1M apenas em 2024-2025;
- 2026 nao entra em quantis, score, folds nem escolha de parametros;
- 2026 e usado so como teste cego/holdout;
- take `50.5`, stop `117`.

Perfis do Pine:

| Perfil | Regra | OOS 2024-2025 | Modelo 2024-2025 | Holdout 2026 | 90d | 30d |
|---|---|---|---|---|---|---|
| 01 Combo 21 BUY + 1154 SELL | `21:00 BUY` + `11:54 SELL` | 79tr, 86.08%, +2147.0 | 378tr, 75.93%, +3846.5 | 71tr, 80.28%, +1240.5 | 50tr, 78.00%, +682.5 | 18tr, 77.78%, +239.0 |
| 02 Noite 21 BUY | `21:00 BUY`, `emaTrend >= -2.9964`, `roc5 <= -0.5000` | 40tr, 85.00%, +1015.0 | 175tr, 76.57%, +1970.0 | 30tr, 80.00%, +510.0 | 22tr, 81.82%, +441.0 | 10tr, 100.00%, +505.0 |
| 03 Manha 1030 SELL | `10:30 SELL`, `distEma200 <= 24.0847`, `posRange20 <= 0.8233` | 68tr, 76.47%, +754.0 | 259tr, 72.97%, +1354.5 | 38tr, 81.58%, +746.5 | 26tr, 80.77%, +475.5 | 9tr, 55.56%, -215.5 |
| 04 Manha 1154 SELL | `11:54 SELL`, `distVwap <= 6.9961`, `emaTrend <= 8.3737` | 49tr, 83.67%, +1134.5 | 214tr, 74.30%, +1594.5 | 41tr, 80.49%, +730.5 | 28tr, 75.00%, +241.5 | 8tr, 50.00%, -266.0 |
| 05 Noite 2058 SELL | `20:58 SELL`, `roc10 <= -3.2500` | 36tr, 77.78%, +478.0 | 160tr, 74.38%, +1212.5 | 46tr, 78.26%, +648.0 | 30tr, 80.00%, +510.0 | 9tr, 100.00%, +454.5 |

Leitura:

- o perfil `01 Combo` foi o primeiro teste porque foi escolhido sem ver 2026 e ainda ficou positivo no holdout.
- o perfil `02 Noite 21 BUY` e a melhor peca individual recente: 30d local com 10/10 e +505.0 pontos, mas precisa confirmar no TV.
- o perfil `03 Manha 1030 SELL` confirmou bem em 2026/90d, mas caiu no 30d; testar so depois do combo/noite.
- o perfil `04 Manha 1154 SELL` confirma o bloco da manha no holdout, mas tambem enfraquece no 30d.
- o perfil `05 Noite 2058 SELL` e diagnostico de noite alternativa, com 2026/90d/30d positivos.
- nenhum desses perfis ainda deve substituir o oficial; o proximo filtro real e TradingView.

Teste TradingView do perfil `01 Combo 21 BUY + 1154 SELL`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 197 | 80.20% | +6596.50 USD | -804.50 USD | 1.705 | Positivo e DD aceitavel, mas abaixo da meta de acerto |
| Ultimos 90d | 40 | 75.00% | +690.00 USD | -692.00 USD | 1.295 | Positivo, mas acerto/PF fracos |
| Ultimos 30d | 13 | 76.92% | +308.00 USD | -527.00 USD | 1.439 | Positivo, mas ainda abaixo de 85% |

Decisao:

- nao promover o perfil `01` ainda;
- manter como referencia positiva porque foi operavel e lucrativo nos tres recortes;
- proximo teste realizado: `02 Noite 21 BUY`.

Teste TradingView do perfil `02 Noite 21 BUY`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 92 | 77.17% | +2257.00 USD | -747.00 USD | 1.459 | Positivo, mas bem abaixo da meta de 85% |
| Ultimos 90d | 14 | 71.43% | +74.00 USD | -527.00 USD | 1.079 | Quase neutro; sem vantagem clara |
| Ultimos 30d | 5 | 60.00% | -165.00 USD | -495.00 USD | 0.647 | Reprovado no recente |

Decisao:

- nao promover o perfil `02`;
- o 365d e positivo, mas o 30d negativo invalida como candidato operacional;
- proximo teste: `03 Manha 1030 SELL`.

Teste TradingView do perfil `03 Manha 1030 SELL`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 146 | 72.60% | +1346.00 USD | -1966.50 USD | 1.144 | Positivo, mas DD alto e acerto baixo |
| Ultimos 90d | 32 | 59.38% | -1123.00 USD | -1917.50 USD | 0.631 | Reprovado |
| Ultimos 30d | 11 | 54.55% | -564.00 USD | -1055.50 USD | 0.518 | Reprovado |

Decisao:

- nao promover o perfil `03`;
- o 90d e o 30d negativos encerram esse bloco de manha 10:30;
- proximo teste: `04 Manha 1154 SELL`.

Teste TradingView do perfil `04 Manha 1154 SELL`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 114 | 77.19% | +2497.50 USD | -871.00 USD | 1.391 | Positivo, mas abaixo da meta de acerto |
| Ultimos 90d | 26 | 76.92% | +616.00 USD | -559.00 USD | 1.439 | Positivo, mas acerto ainda baixo |
| Ultimos 30d | 8 | 87.50% | +473.00 USD | -284.00 USD | 3.021 | Recente forte, mas poucos trades |

Decisao:

- nao promover o perfil `04` ainda;
- manter como melhor recente desta bateria, por ter 30d acima de 85% com PF bom;
- anual e 90d ainda ficam abaixo da meta, entao precisa de mais filtro ou combinacao;
- proximo teste: `05 Noite 2058 SELL`.

Teste TradingView do perfil `05 Noite 2058 SELL`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 104 | 67.31% | -886.00 USD | -1773.00 USD | 0.889 | Reprovado no anual |
| Ultimos 90d | 27 | 66.67% | -288.00 USD | -818.50 USD | 0.863 | Reprovado |
| Ultimos 30d | 9 | 66.67% | -96.00 USD | -520.50 USD | 0.863 | Reprovado |

Decisao:

- nao promover o perfil `05`;
- a bateria `01-05` fica encerrada sem candidato operacional;
- manter o perfil `04 Manha 1154 SELL` apenas como referencia de melhor 30d, nao como aprovacao;
- proxima etapa: nova busca com a mesma regra anti-vazamento, usando 2024-2025 para selecao e 2026 apenas como holdout.

## Candidato novo: Rotacao 2M/1M Noite e Manha

Arquivo:

`V71_ROTACAO_2M1M_NOITE_MANHA_TV_2MIN.pine`

Metodo:

- busca separada por horario de noite em torno de `20:54/21:00`;
- busca separada por horario de manha em torno de `10:30/11:54`;
- rotacao trimestral: treina 2 meses e testa o terceiro;
- depois combina o melhor bloco de noite com o melhor bloco de manha.

Perfis do Pine:

- `01 Noite 20:54 SELL`: `dist_ema200 <= 49.5526` e `prev_roc5 <= -3.2500`;
- `02 Manha 10:30 SELL`: `dist_vwap <= 9.7502` e `pos_range20 <= 0.8351`;
- `03 Combo Noite+Manha`: junta os dois blocos.

Metricas locais do combo:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Rotacao OOS 2M/1M | 98 | 87.76% | 2939.0 | -367.0 | 3.09 |
| Ultimos 365d | 176 | 81.25% | 3360.5 | -500.0 | 1.87 |
| Ultimos 90d | 43 | 86.05% | 1166.5 | -500.0 | 2.66 |
| Ultimos 30d | 14 | 78.57% | 204.5 | -183.5 | 1.58 |

Teste TradingView do perfil `03 Combo Noite+Manha`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 195 | 73.33% | +2275 USD | -2750 USD | 1.187 | Operavel, mas abaixo do alvo |
| Ultimos 90d | 51 | 64.71% | -879 USD | -2366 USD | 0.791 | Reprovado |
| Ultimos 30d | 22 | 68.18% | -123 USD | -1270 USD | 0.925 | Reprovado |

Teste TradingView do perfil `01 Noite 20:54 SELL`:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 80 | 73.75% | +1045 USD | -1462 USD | 1.213 | Anual fraco; nao promover |
| Ultimos 90d | 20 | 75.00% | +345 USD | -706 USD | 1.295 | Positivo, mas acerto baixo |
| Ultimos 30d | 10 | 80.00% | +340 USD | -472 USD | 1.726 | Recente bom para diagnostico |

Leitura:

- o teste fora da amostra por rotacao ficou forte: 7 de 8 folds positivos e sem fold de teste negativo quando o treino passava.
- o 365d local ainda fica abaixo de 85%, entao nao e candidato final; e candidato para validacao TV.
- o 30d local ficou positivo, diferente dos perfis 04/05 do rewrite TVSafe que ficaram negativos.
- o combo foi testado no TradingView e reprovou no 90d/30d.
- o TV executou mais trades que o local porque a base local da busca terminava em `2026-05-20`, enquanto o TV testou ate `2026-06-03`; ainda assim, o resultado deve ser tratado como reprova.
- o perfil `01 Noite 20:54 SELL` foi positivo no 30d/90d, mas reprovou no 365d por acerto baixo e DD alto.
- proximo passo: testar `02 Manha 10:30 SELL` separado para decidir se a manha tambem esta contaminada.

## Candidato exploratorio: Rotacao 2M/1M Manha Refino

Arquivo:

`V71_ROTACAO_2M1M_MANHA_REFINO_TV_2MIN.pine`

Metodo:

- pesquisa separada, sem mexer no V7.1 oficial;
- status atual: supersedido pela regra anti-vazamento que deixa 2026 somente como holdout;
- mantem o alvo da sugestao do usuario: operacoes na parte da manha em torno de `10:30`;
- usa rotacao 2M/1M: treina dois meses e testa o terceiro;
- pega apenas candidatos com pelo menos 5 folds de teste positivos e recortes locais 90d/30d positivos;
- usa take `50.5` e stop `117`.

Perfis do Pine:

| Perfil | Regra | OOS trades | OOS winrate | OOS pontos | 365d trades | 365d winrate | 365d pontos | 90d | 30d |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 03 EMA200 ROC10 71tr | `10:30 SELL`, `distEma200 <= 27.5907`, `roc10 <= -12.2250` | 29 | 86.21% | +794.5 | 71 | 84.51% | +1743.0 | 12tr, 91.67%, +438.5 | 5tr, 80.00%, +85.0 |
| 02 VWAP PosRange 83tr | `10:30 SELL`, `distVwap <= 9.7502`, `posRange20 <= 0.5400` | 40 | 85.00% | +1015.0 | 83 | 83.13% | +1846.5 | 13tr, 92.31%, +489.0 | 5tr, 80.00%, +85.0 |
| 01 Macd PosRange 106tr | `10:30 SELL`, `macdHist <= 0.8812`, `posRange20 <= 0.5400` | 58 | 79.31% | +919.0 | 106 | 80.19% | +1835.5 | 25tr, 80.00%, +425.0 | 7tr, 85.71%, +186.0 |
| 04 VWAP Macd 61tr | `10:30 SELL`, `distVwap <= 9.7502`, `macdHist <= -0.2755` | 33 | 84.85% | +829.0 | 61 | 81.97% | +1238.0 | 9tr, 88.89%, +287.0 | 4tr, 75.00%, +34.5 |

Ordem de teste recomendada:

1. `03 EMA200 ROC10 71tr`: padrao do Pine; menor frequencia, mas melhor equilibrio entre OOS, 365d, 90d e 30d.
2. `02 VWAP PosRange 83tr`: segunda melhor opcao, com OOS e recortes recentes fortes.
3. `01 Macd PosRange 106tr`: mais trades, mas acerto local anual mais baixo.
4. `04 VWAP Macd 61tr`: diagnostico secundario; 30d local tem poucos trades.

Leitura:

- este arquivo nao tenta juntar noite e manha; ele testa se a manha sozinha ainda tem vantagem quando refinada.
- a base local termina em `2026-05-20`, entao o TradingView ate `2026-06-03` pode mudar bastante o resultado.
- se os perfis 03 ou 02 confirmarem no TV, a proxima etapa e procurar uma noite nova para combinar depois.
- se os quatro cairem no TV, a busca deve passar a usar export/lista de trades do proprio TradingView.

## Candidato novo: Calendario DOW 230-85

Arquivo:

`V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- perfil 01: `01 Max 365d 233tr 87pct`
- perfil 02: `02 Recente forte 234tr 85pct`
- perfil 03: `03 Pior ano melhor 230tr 86pct`
- perfil 04: `04 Robusto anual 222tr 85pct`
- perfil 05: `05 Alta acerto 147tr 89pct`

Horarios/direcoes:

- segunda 04:02 BUY
- terca 03:12 SELL
- quarta 02:56 BUY
- quinta 04:30 SELL
- sexta 09:30 BUY

Filtros por perfil:

- perfil 01: quarta 02:56 com `dmi_gap >= 3.5237` e quinta 04:30 com `ema200_slope10 <= 4.7472`
- perfil 02: segunda 04:02 com `vwap_slope10 <= 4.6748` e terca 03:12 com `dist_vwap <= 22.2546`
- perfil 03: terca 03:12 com `dmi_gap >= 2.7238` e quinta 04:30 com `dmi_gap <= 12.7108`
- perfil 04: segunda 04:02 com `ema_gap >= 2.6933` e quinta 04:30 com `dmi_gap <= 22.1959` + `vwap_slope10 <= 1.9005`
- perfil 05: terca 03:12 com `range_30 <= 16.75`, quarta 02:56 com `ema_gap >= 3.3369` e quinta 04:30 com `adx14 <= 20.3605`

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
| 03 Pior ano melhor | Ultimos 365d | 230 | 86.09% | 6255.0 | -300.5 | 2.67 |
| 03 Pior ano melhor | Ultimos 90d | 56 | 85.71% | 1488.0 | -234.0 | 2.59 |
| 03 Pior ano melhor | Ultimos 30d | 20 | 85.00% | 507.5 | -234.0 | 2.45 |
| 03 Pior ano melhor | 2024 | 165 | 77.58% | 2135.0 | n/d | n/d |
| 03 Pior ano melhor | 2025 | 226 | 81.42% | 4378.0 | n/d | n/d |
| 03 Pior ano melhor | 2026 | 89 | 85.39% | 2317.0 | n/d | n/d |
| 04 Robusto anual | Ultimos 365d | 222 | 85.59% | 5851.0 | -351.0 | 2.56 |
| 04 Robusto anual | Ultimos 90d | 58 | 84.48% | 1421.5 | -351.0 | 2.35 |
| 04 Robusto anual | Ultimos 30d | 20 | 85.00% | 507.5 | -117.0 | 2.45 |
| 04 Robusto anual | 2024 | 160 | 80.00% | 2720.0 | -433.5 | 1.73 |
| 04 Robusto anual | 2025 | 220 | 81.36% | 4242.5 | -516.0 | 1.88 |
| 04 Robusto anual | 2026 | 88 | 85.23% | 2266.5 | -351.0 | 2.49 |
| 05 Alta acerto | Ultimos 365d | 147 | 89.80% | 4911.0 | -183.5 | 3.80 |
| 05 Alta acerto | Ultimos 90d | 39 | 87.18% | 1132.0 | -183.5 | 2.94 |
| 05 Alta acerto | Ultimos 30d | 14 | 85.71% | 372.0 | -117.0 | 2.59 |
| 05 Alta acerto | 2024 | 115 | 81.74% | 2290.0 | -481.5 | 1.93 |
| 05 Alta acerto | 2025 | 146 | 84.25% | 3520.5 | -433.5 | 2.31 |
| 05 Alta acerto | 2026 | 59 | 89.83% | 1974.5 | -183.5 | 3.81 |

Arquivo de conferencia local:

`pesquisa_v71_0348_6min/REFINO_CALENDARIO_DOW_230_85.md`

Auditoria de robustez:

`pesquisa_v71_0348_6min/AUDITORIA_CALENDARIO_DOW_230_85_ROTACAO.md`

Busca multifaixa nova:

`pesquisa_v71_0348_6min/BUSCA_CALENDARIO_DOW_ROBUSTO_MULTIFAIXA.md`

Ponto forte:

- o perfil 01 e o primeiro candidato que bate a faixa desejada de 230 a 250 trades e passa de 85% nos ultimos 365 dias.
- o perfil 04 fica perto da faixa, com 222 trades, 85%+ nos ultimos 365 dias e todos os anos 80%+.
- o perfil 02 preserva 85%+ no anual e melhora bastante os recortes de 90 e 30 dias.
- o perfil 05 sobe para 89.80% nos ultimos 365 dias com DD/PF melhores, mas aceita menor frequencia.

Ponto fraco:

- os anos completos 2024 e 2025 ficam abaixo de 85%, embora positivos.
- a auditoria encontrou 1.863 candidatos na faixa 230-250 trades e 85%+ em 365d, mas nenhum manteve todos os anos acima de 80%; a solucao multifaixa achou robustez anual abrindo mao de pelo menos 8 trades na faixa.
- o perfil 01 foi testado no TradingView e caiu para 81.25% nos ultimos 365 dias, PF 1.87, 90d com 70.49% e PF 1.031; portanto nao deve ser priorizado.
- o perfil 04 foi testado no TradingView e caiu para 80.80% nos ultimos 365 dias, PF 1.817, 90d com 73.68% e PF 1.209; portanto nao confirmou a meta, apesar do 30d positivo.
- o perfil 05 foi testado no TradingView e caiu para 81.58% nos ultimos 365 dias, PF 1.911, 90d com 79.49% e PF 1.673; portanto a familia Calendario DOW atual deve ser abandonada.
- a busca pos-DOW voltou ao Regime 191/89 como melhor candidato pronto; ele usa entrada no candle seguinte, mas ainda carrega fragilidade em 2024.
- o Regime 191/89 travou no TradingView mesmo na versao limpa; como o smoke minimo funciona, o problema esta na implementacao/operabilidade desse Pine, entao ele nao deve ser priorizado.
- o Regime Refino 93 tambem travou no TradingView; portanto a proxima validacao deve priorizar arquivos Pine mais simples e ja proximos de uma base que gerou entradas no TV.
- o DMI3 Take45 tambem travou no teste direto; portanto a proxima etapa e diagnostica, com uma escada que comeca forcando entrada e depois adiciona horarios, scores e DMI.
- por usar calendario por dia da semana, precisa ser confirmado no TradingView antes de qualquer decisao operacional.
- ainda nao deve substituir o oficial.

## Diagnostico operacional: Destrava TV 3H escada

Arquivo:

`V71_DESTRAVA_TV_3H_ESCADA_OPERAVEL.pine`

Status:

- travou no TradingView mesmo com modo `00 Forcar smoke`.
- como esse arquivo ainda calcula indicadores e DMI, a proxima tentativa deve ser um arquivo minimo, sem indicadores.

## Diagnostico minimo: Smoke e horarios puros

Arquivo:

`V71_DESTRAVA_TV_MINIMO_SMOKE_HORARIOS.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- comecar no modo `00 Smoke puro`

Escada minima:

1. `00 Smoke puro`: replica a ideia do smoke que ja funcionou, com entrada a cada 50 barras e fechamento no candle seguinte.
2. `01 Horarios 3H puro`: testa apenas os horarios/dias 03:48, 10:30 e 20:58, sem qualquer indicador.
3. `02 Calendario DOW puro`: testa apenas os horarios/dias do calendario que ja gerou trades no TradingView.

Leitura:

- se `00` travar, o problema nao e filtro: e execucao/configuracao do script no TV.
- se `00` funcionar e `01` travar, o problema esta na forma como o TV esta enxergando os horarios 3H.
- se `01` e `02` funcionarem, voltar a adicionar filtros um por um em um Pine novo.

## Candidato novo: Rewrite TVSafe indicadores 95

Arquivo:

`V71_REWRITE_TVSAFE_INDICADORES_95_TV_2MIN.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- perfil recomendado agora: `05 Ultra 52tr 100pct`

Indicadores usados:

- corpo do candle;
- MACD histograma;
- EMA 17 menos EMA 34;
- ROC 5;
- ROC 10;
- range de 30 minutos;
- distancia do VWAP apenas no perfil `03`.

Regras do perfil 01:

- segunda 10:30 BUY se `body <= 12.3750`;
- domingo 20:58 BUY se `macd_hist >= 1.0513`;
- quarta 02:56 BUY se `ema17 - ema34 >= 0.9902`;
- quinta 04:30 SELL se `ema17 - ema34 <= 3.3899`;
- sexta 09:30 BUY se `roc5 <= -9.5000`.

Metricas locais do perfil 01:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Ultimos 365d | 122 | 95.08% | 5156.0 | -133.0 | 8.34 |
| Ultimos 90d | 41 | 95.12% | 1735.5 | -117.0 | 8.42 |
| Ultimos 30d | 19 | 89.47% | 624.5 | -117.0 | 3.67 |
| 2024 | 87 | 71.26% | 206.0 | -582.5 | 1.07 |
| 2025 | 121 | 87.60% | 3598.0 | -234.0 | 3.05 |
| 2026 | 56 | 94.64% | 2325.5 | -117.0 | 7.63 |

Teste TradingView do perfil 01:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 112 | 84.82% | +5617 USD | -835 USD | 2.412 | Operavel, mas abaixo do alvo de 85% |
| Ultimos 90d | 28 | 78.57% | +818 USD | -835 USD | 1.583 | Recente fraco |
| Ultimos 30d | 10 | 60.00% | -330 USD | -835 USD | 0.647 | Reprovado |

Teste TradingView do perfil 04:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 71 | 87.32% | +4156 USD | -521 USD | 2.973 | Anual bom, mas abaixo do esperado local |
| Ultimos 90d | 17 | 76.47% | +377 USD | -468 USD | 1.403 | Recente fraco |
| Ultimos 30d | 6 | 66.67% | -64 USD | -468 USD | 0.863 | Reprovado |

Teste TradingView do perfil 05:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 46 | 86.96% | +2636 USD | -827.50 USD | 2.877 | Anual aceitavel, mas menor frequencia |
| Ultimos 90d | 15 | 73.33% | +175 USD | -795.50 USD | 1.187 | Recente fraco |
| Ultimos 30d | 6 | 66.67% | -64 USD | -468 USD | 0.863 | Reprovado; mesmo 30d do perfil 04 |

Perfis novos adicionados ao mesmo Pine:

- `04 Recente 68tr 97pct`: segunda 03:48 BUY se `range30 <= 41.0625`, quarta 02:56 BUY se `ema17 - ema34 >= 0.9902`, sexta 09:30 BUY se `roc5 <= -9.5000`.
- `05 Ultra 52tr 100pct`: segunda 10:30 BUY se `roc10 >= 24.5000`, quarta 02:56 BUY se `ema17 - ema34 >= 0.9902`, sexta 09:30 BUY se `roc5 <= -9.5000`.

Metricas locais dos perfis novos:

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 04 Recente | Ultimos 365d | 68 | 97.06% | 3099.0 | -117.0 | 14.24 |
| 04 Recente | Ultimos 90d | 19 | 100.00% | 959.5 | 0.0 | 999 |
| 04 Recente | Ultimos 30d | 9 | 100.00% | 454.5 | 0.0 | 999 |
| 05 Ultra | Ultimos 365d | 52 | 100.00% | 2626.0 | 0.0 | 999 |
| 05 Ultra | Ultimos 90d | 19 | 100.00% | 959.5 | 0.0 | 999 |
| 05 Ultra | Ultimos 30d | 10 | 100.00% | 505.0 | 0.0 | 999 |

Ponto forte:

- e o primeiro rewrite apos o smoke minimo que combina acerto alto recente, DD baixo e indicadores simples no Pine.
- confirmou operabilidade no TradingView; a falha agora e qualidade do filtro, nao travamento.

Ponto fraco:

- 2024 completo ainda e fraco; por isso e candidato de pesquisa/validacao TV, nao substituto do oficial.
- o perfil 01 caiu no TV para 84.82% em 365d, 78.57% em 90d e 60.00% em 30d; portanto nao deve ser promovido.
- o perfil 04 caiu no TV para 87.32% em 365d, 76.47% em 90d e 66.67% em 30d; portanto tambem nao deve ser promovido.
- o perfil 05 caiu no TV para 86.96% em 365d, 73.33% em 90d e 66.67% em 30d; portanto a familia nao deve ser promovida.
- os perfis 04 e 05 repetiram exatamente o mesmo 30d, indicando que a perda recente vem dos blocos compartilhados `qua0256` e/ou `sex0930`.

## Diagnostico por blocos do rewrite TVSafe

Arquivo:

`V71_DIAGNOSTICO_TVSAFE_BLOCOS_REWRITE_2MIN.pine`

Objetivo:

- isolar no TradingView qual bloco esta contaminando o 30d dos perfis 04/05;
- manter o Pine simples e operavel;
- evitar nova busca cega antes de saber se o problema e quarta 02:56, sexta 09:30 ou a combinacao.

Ordem recomendada de teste:

1. `05 Qua+Sex compartilhado`: deve reproduzir a base ruim do 30d dos perfis 04/05.
2. `03 Qua 02:56 ema`: se perder, a quarta esta contaminando.
3. `04 Sex 09:30 roc5`: se perder, a sexta esta contaminando.
4. `02 Seg 10:30 roc10`: mede o bloco exclusivo do perfil 05.
5. `01 Seg 03:48 range30`: mede o bloco exclusivo do perfil 04.

Leitura:

- se apenas um bloco estiver ruim, reescrever removendo esse bloco.
- se `03` e `04` estiverem ruins, abandonar essa familia e usar export/lista de trades do TV para uma nova busca.
- se os blocos isolados forem bons mas a combinacao for ruim, o problema e concorrencia/ordem de trades no Backtesting Profundo.

## Candidato operacional: DMI3 Take45 robusto

Arquivo:

`V71_PESQUISA_TV_3H_DMI3_TAKE45_ROBUSTO.pine`

Teste no TradingView:

- simbolo: `MNQ1!`
- timeframe: `2m`
- modo: Backtesting Profundo
- parametros padrao: take `45.5`, stop `117`, DMI gap minimo `3.0`

Metricas locais:

| Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---:|---:|---:|---:|---:|
| Ultimos 365d | 132 | 86.36% | 3081.0 | -331.5 | 2.463 |
| Ultimos 90d | 31 | 87.10% | 760.5 | n/d | n/d |
| Ultimos 30d | 11 | 90.91% | 338.0 | n/d | n/d |

Ponto forte:

- e mais simples que os Regimes e usa a mesma base 3 horarios/DMI que ja gerou entradas no TradingView em validacoes anteriores.
- sacrifica parte do lucro/acerto teorico dos Regimes para ganhar operabilidade no TV.

Ponto fraco:

- ainda precisa confirmacao direta no TradingView; se cair para perto de 82%, fica como pesquisa positiva, mas nao como candidato de alta acertividade.

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

Melhor candidato para teste serio agora:

Nenhum perfil da bateria `V71_ROTACAO_2024_2025_HOLDOUT2026_TV_2MIN.pine` foi aprovado para promocao.

Melhor candidato de alta acertividade/DD:

Nenhum confirmado no TradingView recente; o perfil `04 Manha 1154 SELL` foi o melhor no 30d, mas anual/90d ainda nao passaram de 85%.

Melhor candidato simples por robustez multiano:

`V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine`, perfil `02 Multiano 86pct`.

Melhor candidato para tentar mais frequencia/pontuacao, mas com ressalva:

Nenhum candidato de maior frequencia esta confirmado no TradingView neste momento.

Regra pratica:

- os perfis 04/05 antigos do Calendario DOW foram testados no TradingView e nao confirmaram; so voltar neles se houver ajuste de regra/dados;
- o perfil 01 do Calendario DOW ja foi testado no TradingView e nao confirmou; so voltar nele se houver ajuste de regra/dados;
- o perfil 01 do Rewrite TVSafe operou no TradingView, mas reprovou no 30d; manter apenas como diagnostico de operabilidade;
- o perfil 04 do Rewrite TVSafe tambem operou, mas reprovou no 90d e 30d;
- o perfil 05 do Rewrite TVSafe tambem operou, mas reprovou no 90d e 30d;
- a busca por rotacao 2M/1M achou um combo novo `20:54 SELL + 10:30 SELL`, mas o perfil `03 Combo` reprovou no TV;
- o perfil `01 Noite 20:54 SELL` da rotacao ficou positivo no recente, mas nao passou no anual;
- a partir de agora, toda busca deve treinar/selecionar apenas em 2024-2025 e deixar 2026 como holdout;
- o arquivo `V71_ROTACAO_2M1M_MANHA_REFINO_TV_2MIN.pine` fica apenas como historico exploratorio, pois foi criado antes da regra 2026 somente holdout;
- o perfil `01 Combo 21 BUY + 1154 SELL` do holdout 2026 foi positivo no TradingView, mas ficou abaixo de 85% nos 365/90/30 dias;
- o perfil `02 Noite 21 BUY` tambem foi positivo no anual, mas reprovou no 30d;
- o perfil `03 Manha 1030 SELL` reprovou no TradingView, com 90d e 30d negativos;
- o perfil `04 Manha 1154 SELL` foi o melhor recente desta bateria, com 87.50% no 30d, mas ainda nao confirmou no anual/90d;
- o perfil `05 Noite 2058 SELL` reprovou nos 365d/90d/30d;
- a bateria `V71_ROTACAO_2024_2025_HOLDOUT2026_TV_2MIN.pine` nao deve ser promovida;
- a proxima busca deve manter a regra: 2024-2025 para selecao, 2026 somente holdout;
- o Regime 191/89 deve ficar pausado: o smoke minimo funciona, mas as versoes com logica de regime travaram no TradingView;
- o Regime Refino 93 tambem deve ficar pausado: travou no TradingView;
- o DMI3 Take45 tambem deve ficar pausado no teste direto: travou no TradingView;
- o minimo `V71_DESTRAVA_TV_MINIMO_SMOKE_HORARIOS.pine` confirmou que o TV executa, mas e diagnostico e ficou perto de 48% no smoke;
- testar os blocos separados da rotacao antes de abandonar a familia;
- se o TradingView confirmar o 04:06 multiano perto de 86%, ele vira a linha mais segura de pesquisa;
- nenhum candidato deve substituir o oficial sem aprovacao explicita.

## Proximo teste recomendado no TradingView

1. Nao promover a familia Calendario DOW atual: perfis 01, 04 e 05 ficaram abaixo de 85% no TradingView.
2. Pausar o Regime 191/89: smoke minimo funciona, mas as versoes com logica travaram no TradingView.
3. Pausar o Regime Refino 93: tambem travou no TradingView.
4. Pausar o DMI3 Take45 direto: tambem travou no TradingView.
5. Usar o resultado do `V71_DESTRAVA_TV_MINIMO_SMOKE_HORARIOS.pine` apenas como prova de execucao; o modo smoke ficou perto de 48% e nao e estrategia.
6. O perfil `03 Combo Noite+Manha` da rotacao reprovou no TradingView.
7. O perfil `01 Noite 20:54 SELL` ficou positivo no 30d/90d, mas reprovou no 365d.
8. Perfil `01 Combo 21 BUY + 1154 SELL` ja testado: positivo, mas abaixo da meta de acerto.
9. Perfil `02 Noite 21 BUY` ja testado: positivo no anual, mas reprovado no 30d.
10. Perfil `03 Manha 1030 SELL` ja testado: reprovado no 90d/30d.
11. Perfil `04 Manha 1154 SELL` ja testado: melhor recente, mas anual/90d abaixo da meta.
12. Perfil `05 Noite 2058 SELL` ja testado: reprovado nos 365d/90d/30d.
13. Encerrar a bateria `01-05`: nenhum perfil promove.
14. Proxima etapa: nova busca anti-vazamento, com 2024-2025 para selecao e 2026 apenas como holdout.
15. Manter o V7.1 oficial sem alteracao.
