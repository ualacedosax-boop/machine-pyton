# Rotacao 2M/1M Noite e Manha

Pesquisa separada. Nao altera o V7.1 oficial.

Metodo: blocos trimestrais. Treina os dois primeiros meses e testa o terceiro.

Folds usados:

- treina_2024-04_2024-05_testa_2024-06
- treina_2024-07_2024-08_testa_2024-09
- treina_2024-10_2024-11_testa_2024-12
- treina_2025-01_2025-02_testa_2025-03
- treina_2025-04_2025-05_testa_2025-06
- treina_2025-07_2025-08_testa_2025-09
- treina_2025-10_2025-11_testa_2025-12
- treina_2026-01_2026-02_testa_2026-03

## Top noite

| candidato | filtro | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | teste_dd | teste_pf | trades_365 | winrate_365 | pontos_365 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noite|20:54|SELL | dist_ema200 <= 49.5526 & prev_roc5 <= -3.2500 | 5 | 34 | 94.12 | 1382.00 | -117.00 | 6.91 | 78 | 83.33 | 1761.50 | 22 | 86.36 | 608.50 | 6 | 100.00 | 303.00 |
| noite|20:54|BUY | macd_hist <= 0.4640 & prev_roc5 >= -7.2500 | 5 | 41 | 92.68 | 1568.00 | -117.00 | 5.47 | 109 | 78.90 | 1652.00 | 22 | 81.82 | 441.00 | 14 | 92.86 | 539.50 |
| noite|20:54|BUY | adx14 <= 27.4867 & prev_roc5 >= -7.2500 | 6 | 67 | 83.58 | 1541.00 | -234.00 | 2.20 | 134 | 74.63 | 1072.00 | 32 | 78.12 | 443.50 | 11 | 72.73 | 53.00 |
| noite|20:54|BUY | macd_hist <= 1.1241 & prev_roc5 >= -7.2500 | 5 | 50 | 88.00 | 1520.00 | -250.00 | 3.17 | 148 | 77.70 | 1946.50 | 34 | 79.41 | 544.50 | 18 | 77.78 | 239.00 |
| noite|20:54|SELL | dmi_gap >= 9.0032 & rsi14 <= 46.4040 | 5 | 27 | 100.00 | 1363.50 | 0.00 | 999.00 | 58 | 72.41 | 249.00 | 16 | 81.25 | 305.50 | 6 | 83.33 | 135.50 |
| noite|20:56|SELL | macd_hist <= -0.0177 & roc10 <= -3.5000 | 6 | 34 | 91.18 | 1214.50 | -117.00 | 4.46 | 78 | 74.36 | 589.00 | 25 | 72.00 | 90.00 | 6 | 83.33 | 135.50 |
| noite|20:54|SELL | dmi_gap >= 9.0032 & ret_60 <= 2.2500 | 5 | 26 | 100.00 | 1313.00 | 0.00 | 999.00 | 61 | 72.13 | 233.00 | 15 | 80.00 | 255.00 | 6 | 83.33 | 135.50 |
| noite|20:54|BUY | ema_trend >= -0.9495 & prev_roc5 >= -7.2500 | 5 | 53 | 86.79 | 1504.00 | -183.50 | 2.84 | 131 | 77.10 | 1590.50 | 30 | 80.00 | 510.00 | 13 | 76.92 | 154.00 |
| noite|20:54|BUY | prev_roc5 >= -7.2500 & range_30 <= 32.0000 | 5 | 58 | 82.76 | 1254.00 | -234.00 | 2.07 | 134 | 77.61 | 1742.00 | 19 | 84.21 | 457.00 | 10 | 100.00 | 505.00 |
| noite|20:54|BUY | prev_roc5 >= -7.2500 & roc10 <= 5.0000 | 5 | 45 | 86.67 | 1267.50 | -234.00 | 2.81 | 104 | 78.85 | 1567.00 | 18 | 88.89 | 574.00 | 6 | 100.00 | 303.00 |
| noite|20:54|BUY | prev_roc5 >= -7.2500 & roc10 <= 0.2500 | 5 | 34 | 88.24 | 1047.00 | -133.00 | 3.24 | 76 | 82.89 | 1660.50 | 18 | 88.89 | 574.00 | 6 | 100.00 | 303.00 |
| noite|20:56|SELL | prev_roc5 <= 0.0000 & roc10 <= 0.5000 | 6 | 44 | 84.09 | 1049.50 | -133.00 | 2.28 | 92 | 71.74 | 291.00 | 25 | 76.00 | 257.50 | 9 | 88.89 | 287.00 |

## Top manha

| candidato | filtro | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | teste_dd | teste_pf | trades_365 | winrate_365 | pontos_365 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| manha|11:54|SELL | dist_ema200 <= 9.1919 & ema_trend <= 8.1862 | 7 | 60 | 83.33 | 1355.00 | -250.00 | 2.16 | 111 | 80.18 | 1920.50 | 28 | 71.43 | 74.00 | 9 | 44.44 | -383.00 |
| manha|11:54|SELL | ema_trend <= 8.1862 & rsi14 <= 50.1523 | 7 | 55 | 87.27 | 1605.00 | -234.00 | 2.96 | 110 | 76.36 | 1200.00 | 31 | 67.74 | -109.50 | 12 | 41.67 | -566.50 |
| manha|11:54|SELL | dist_ema200 <= 9.1919 & ret_60 <= 28.2500 | 6 | 55 | 85.45 | 1437.50 | -133.00 | 2.54 | 105 | 80.00 | 1785.00 | 27 | 74.07 | 191.00 | 8 | 50.00 | -266.00 |
| manha|10:30|SELL | dist_vwap <= 9.7502 & pos_range20 <= 0.8351 | 6 | 62 | 83.87 | 1456.00 | -300.50 | 2.24 | 105 | 80.00 | 1785.00 | 22 | 81.82 | 441.00 | 8 | 62.50 | -98.50 |
| manha|11:54|SELL | dist_vwap <= 9.7004 & ema_trend <= 1.6849 | 6 | 54 | 85.19 | 1387.00 | -133.00 | 2.48 | 104 | 78.85 | 1567.00 | 25 | 76.00 | 257.50 | 7 | 57.14 | -149.00 |
| manha|11:54|SELL | dist_ema200 <= 9.1919 & rsi14 <= 50.1523 | 6 | 44 | 88.64 | 1384.50 | -117.00 | 3.37 | 94 | 78.72 | 1397.00 | 25 | 72.00 | 90.00 | 7 | 42.86 | -316.50 |
| manha|10:30|SELL | dist_ema200 <= 27.5907 & macd_hist <= 0.8812 | 6 | 53 | 83.02 | 1169.00 | -300.50 | 2.11 | 96 | 82.29 | 2000.50 | 18 | 83.33 | 406.50 | 7 | 57.14 | -149.00 |
| manha|11:54|SELL | dist_vwap <= 9.7004 & ema_trend <= 8.1862 | 6 | 53 | 84.91 | 1336.50 | -234.00 | 2.43 | 112 | 78.57 | 1636.00 | 27 | 74.07 | 191.00 | 8 | 50.00 | -266.00 |
| manha|11:54|SELL | ema_trend <= 8.1862 & ret_60 <= 28.2500 | 7 | 77 | 79.22 | 1208.50 | -332.50 | 1.65 | 142 | 74.65 | 1141.00 | 43 | 67.44 | -173.50 | 16 | 50.00 | -532.00 |
| manha|10:30|SELL | dist_vwap <= 32.0772 & macd_hist <= 0.8812 | 6 | 50 | 82.00 | 1017.50 | -330.00 | 1.97 | 95 | 83.16 | 2117.50 | 16 | 87.50 | 473.00 | 6 | 66.67 | -32.00 |
| manha|11:54|SELL | dist_ema200 <= 9.1919 & pos_range20 <= 0.6775 | 6 | 48 | 87.50 | 1419.00 | -133.00 | 3.02 | 104 | 76.92 | 1232.00 | 28 | 71.43 | 74.00 | 8 | 37.50 | -433.50 |
| manha|11:54|SELL | dist_ema200 <= 9.1919 & pos_range20 <= 0.5313 | 5 | 37 | 94.59 | 1533.50 | -117.00 | 7.55 | 86 | 79.07 | 1328.00 | 22 | 68.18 | -61.50 | 6 | 33.33 | -367.00 |

## Top combinacoes noite + manha

| combo | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | teste_dd | teste_pf | trades_365 | winrate_365 | pontos_365 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noite|20:54|SELL [dist_ema200 <= 49.5526 & prev_roc5 <= -3.2500] + manha|10:30|SELL [dist_vwap <= 9.7502 & pos_range20 <= 0.8351] | 7 | 98 | 87.76 | 2939.00 | -367.00 | 3.09 | 176 | 81.25 | 3360.50 | 43 | 86.05 | 1166.50 | 14 | 78.57 | 204.50 |
| noite|20:54|SELL [dist_ema200 <= 49.5526 & prev_roc5 <= -3.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ret_60 <= 28.2500] | 7 | 89 | 88.76 | 2819.50 | -234.00 | 3.41 | 180 | 81.67 | 3562.50 | 48 | 81.25 | 916.50 | 14 | 71.43 | 37.00 |
| noite|20:54|SELL [dist_ema200 <= 49.5526 & prev_roc5 <= -3.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ema_trend <= 8.1862] | 7 | 94 | 87.23 | 2737.00 | -234.00 | 2.95 | 186 | 81.72 | 3698.00 | 49 | 79.59 | 799.50 | 15 | 66.67 | -80.00 |
| noite|20:54|SELL [dist_ema200 <= 49.5526 & prev_roc5 <= -3.2500] + manha|11:54|SELL [ema_trend <= 8.1862 & rsi14 <= 50.1523] | 7 | 88 | 89.77 | 2936.50 | -266.00 | 3.79 | 183 | 79.23 | 2876.50 | 51 | 76.47 | 565.50 | 18 | 61.11 | -263.50 |
| noite|20:54|BUY [macd_hist <= 1.1241 & prev_roc5 >= -7.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ema_trend <= 8.1862] | 6 | 120 | 85.83 | 3212.50 | -215.50 | 2.62 | 246 | 78.46 | 3545.50 | 60 | 76.67 | 685.00 | 20 | 60.00 | -330.00 |
| noite|20:54|BUY [adx14 <= 27.4867 & prev_roc5 >= -7.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ret_60 <= 28.2500] | 6 | 113 | 85.84 | 3026.50 | -250.00 | 2.62 | 233 | 78.11 | 3224.00 | 58 | 77.59 | 751.50 | 19 | 63.16 | -213.00 |
| noite|20:54|BUY [adx14 <= 27.4867 & prev_roc5 >= -7.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ema_trend <= 8.1862] | 6 | 117 | 85.47 | 3061.00 | -250.00 | 2.54 | 239 | 78.24 | 3359.50 | 59 | 76.27 | 634.50 | 20 | 60.00 | -330.00 |
| noite|20:56|SELL [macd_hist <= -0.0177 & roc10 <= -3.5000] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ret_60 <= 28.2500] | 7 | 94 | 86.17 | 2569.50 | -266.00 | 2.69 | 181 | 77.35 | 2273.00 | 51 | 72.55 | 230.50 | 14 | 64.29 | -130.50 |
| noite|20:54|BUY [adx14 <= 27.4867 & prev_roc5 >= -7.2500] + manha|11:54|SELL [ema_trend <= 8.1862 & rsi14 <= 50.1523] | 6 | 116 | 86.21 | 3178.00 | -250.00 | 2.70 | 238 | 76.47 | 2639.00 | 63 | 73.02 | 334.00 | 23 | 56.52 | -513.50 |
| noite|20:56|SELL [macd_hist <= -0.0177 & roc10 <= -3.5000] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ema_trend <= 8.1862] | 7 | 99 | 84.85 | 2487.00 | -300.50 | 2.42 | 187 | 77.54 | 2408.50 | 52 | 71.15 | 113.50 | 15 | 60.00 | -247.50 |
| noite|20:54|BUY [macd_hist <= 0.4640 & prev_roc5 >= -7.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ret_60 <= 28.2500] | 5 | 82 | 89.02 | 2633.50 | -133.00 | 3.50 | 208 | 79.81 | 3469.00 | 48 | 79.17 | 749.00 | 16 | 75.00 | 138.00 |
| noite|20:54|BUY [macd_hist <= 0.4640 & prev_roc5 >= -7.2500] + manha|11:54|SELL [dist_ema200 <= 9.1919 & ema_trend <= 8.1862] | 5 | 86 | 88.37 | 2668.00 | -133.00 | 3.28 | 214 | 79.91 | 3604.50 | 49 | 77.55 | 632.00 | 17 | 70.59 | 21.00 |

## Validacao TradingView

Arquivo testado:

`V71_ROTACAO_2M1M_NOITE_MANHA_TV_2MIN.pine`

Perfil testado:

`03 Combo Noite+Manha`

Resultado:

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Ultimos 365d | 195 | 73.33% | +2275 USD | -2750 USD | 1.187 | Operavel, mas abaixo do alvo |
| Ultimos 90d | 51 | 64.71% | -879 USD | -2366 USD | 0.791 | Reprovado |
| Ultimos 30d | 22 | 68.18% | -123 USD | -1270 USD | 0.925 | Reprovado |

Leitura:

- o combo nao deve ser promovido.
- o TradingView gerou mais trades que a simulacao local de 365d, em parte porque a base local terminava em `2026-05-20` e o teste do TV foi ate `2026-06-03`.
- a proxima validacao deve testar os blocos separados: `01 Noite 20:54 SELL` e `02 Manha 10:30 SELL`.
- se apenas um bloco confirmar, refazer a busca do bloco que caiu antes de tentar juntar novamente.

## Leitura

- Uma regra so e candidata se passar em meses de teste, nao apenas no periodo total.
- Se a combinacao for pior que os blocos separados, manter scripts separados e juntar apenas depois de validacao no TV.
- Proximo passo apos escolher candidatos: converter para Pine simples e validar no TradingView com Backtesting Profundo.
