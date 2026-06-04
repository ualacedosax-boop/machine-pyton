# Confluencia 7 indicadores - rotacao 2024-2025

Pesquisa separada. Nao altera o V7.1 oficial.

Metodo:

- cada candidato usa exatamente 7 votos de indicadores;
- o sinal exige 5, 6 ou 7 votos alinhados com BUY/SELL;
- horarios testados: noite em torno de 20:54-21:00 e manha em torno de 10:30/11:54;
- rotacao mensal 2M/1M dentro de 2024-2025: treina dois meses e testa o terceiro;
- 2026 fica fora de quantis, score, folds e escolha; aparece apenas como holdout cego.

Folds usados:

- treina_2024-03_2024-04_testa_2024-05
- treina_2024-04_2024-05_testa_2024-06
- treina_2024-05_2024-06_testa_2024-07
- treina_2024-06_2024-07_testa_2024-08
- treina_2024-07_2024-08_testa_2024-09
- treina_2024-08_2024-09_testa_2024-10
- treina_2024-09_2024-10_testa_2024-11
- treina_2024-10_2024-11_testa_2024-12
- treina_2024-11_2024-12_testa_2025-01
- treina_2024-12_2025-01_testa_2025-02
- treina_2025-01_2025-02_testa_2025-03
- treina_2025-02_2025-03_testa_2025-04
- treina_2025-03_2025-04_testa_2025-05
- treina_2025-04_2025-05_testa_2025-06
- treina_2025-05_2025-06_testa_2025-07
- treina_2025-06_2025-07_testa_2025-08
- treina_2025-07_2025-08_testa_2025-09
- treina_2025-08_2025-09_testa_2025-10
- treina_2025-09_2025-10_testa_2025-11
- treina_2025-10_2025-11_testa_2025-12

## Top noite

| id | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | trades_modelo | winrate_modelo | pontos_modelo | trades_2026 | winrate_2026 | pontos_2026 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+ema34_89+preco_ema200+roc5+bb_mid+candle+prev_candle | 16 | 61 | 85.25 | 1573.00 | 75 | 85.33 | 1945.00 | 20 | 85.00 | 507.50 | 14 | 85.71 | 372.00 | 5 | 100.00 | 252.50 |
| noite|20:52|SELL|v5|adx20|WEEK|ema34_89+macd+roc10+vwap+bb_mid+prev_candle+stoch50 | 16 | 70 | 84.29 | 1692.50 | 76 | 84.21 | 1828.00 | 15 | 80.00 | 255.00 | 11 | 72.73 | 53.00 | 5 | 100.00 | 252.50 |
| noite|21:02|SELL|v5|adx20|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle | 15 | 87 | 83.91 | 2048.50 | 106 | 83.02 | 2338.00 | 22 | 81.82 | 441.00 | 16 | 81.25 | 305.50 | 7 | 85.71 | 186.00 |
| noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle | 15 | 83 | 84.34 | 2014.00 | 102 | 83.33 | 2303.50 | 21 | 80.95 | 390.50 | 15 | 80.00 | 255.00 | 7 | 85.71 | 186.00 |
| noite|21:02|SELL|v5|adx20|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 | 15 | 90 | 83.33 | 2032.50 | 108 | 82.41 | 2271.50 | 23 | 82.61 | 491.50 | 17 | 82.35 | 356.00 | 7 | 85.71 | 186.00 |
| noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 | 15 | 86 | 83.72 | 1998.00 | 104 | 82.69 | 2237.00 | 22 | 81.82 | 441.00 | 16 | 81.25 | 305.50 | 7 | 85.71 | 186.00 |
| noite|21:02|SELL|v5|adx20|ALL|ema8_21+ema17_34+ema34_89+dmi+roc5+candle+prev_candle | 15 | 77 | 84.42 | 1878.50 | 100 | 81.00 | 1867.50 | 21 | 80.95 | 390.50 | 14 | 78.57 | 204.50 | 6 | 83.33 | 135.50 |
| noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+ema34_89+preco_ema200+dmi+roc5+roc10+candle | 15 | 69 | 85.51 | 1809.50 | 84 | 85.71 | 2232.00 | 20 | 85.00 | 507.50 | 14 | 85.71 | 372.00 | 5 | 100.00 | 252.50 |
| noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+ema34_89+preco_ema200+dmi+macd+roc5+candle | 15 | 61 | 86.89 | 1740.50 | 76 | 86.84 | 2163.00 | 20 | 85.00 | 507.50 | 14 | 85.71 | 372.00 | 5 | 100.00 | 252.50 |
| noite|21:02|SELL|v5|adx20|ALL|preco_ema200+dmi+rsi50+roc5+roc10+vwap+candle | 15 | 77 | 84.42 | 1878.50 | 94 | 82.98 | 2067.00 | 20 | 85.00 | 507.50 | 14 | 85.71 | 372.00 | 5 | 100.00 | 252.50 |
| noite|21:02|SELL|v6|adx20_dmi4|ALL|ema17_34+ema34_89+preco_ema200+dmi+roc5+bb_mid+prev_candle | 15 | 51 | 86.27 | 1403.00 | 62 | 87.10 | 1791.00 | 15 | 80.00 | 255.00 | 9 | 77.78 | 119.50 | 4 | 100.00 | 202.00 |
| noite|20:52|SELL|v5|adx20|WEEK|ema8_21+ema34_89+macd+roc10+bb_mid+candle+stoch50 | 15 | 77 | 84.42 | 1878.50 | 85 | 83.53 | 1947.50 | 21 | 85.71 | 558.00 | 14 | 78.57 | 204.50 | 6 | 100.00 | 303.00 |

## Top manha

| id | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | trades_modelo | winrate_modelo | pontos_modelo | trades_2026 | winrate_2026 | pontos_2026 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| manha|11:52|BUY|v5|adx20_dmi4|ALL|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 15 | 73.33 | 87.50 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v5|adx20_dmi4|WEEK|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 15 | 73.33 | 87.50 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v5|adx20_dmi4|ALL|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 16 | 75.00 | 138.00 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v5|adx20_dmi4|WEEK|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 16 | 75.00 | 138.00 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v5|adx20_dmi4|ALL|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 16 | 75.00 | 138.00 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v5|adx20_dmi4|WEEK|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 16 | 87 | 83.91 | 2048.50 | 98 | 83.67 | 2269.00 | 16 | 75.00 | 138.00 | 12 | 66.67 | -64.00 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v6|dmi4|ALL|ema17_34+macd+rsi50+roc5+vwap+bb_mid+candle | 16 | 99 | 82.83 | 2152.00 | 111 | 81.98 | 2255.50 | 21 | 66.67 | -112.00 | 16 | 68.75 | -29.50 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v6|dmi4|WEEK|ema17_34+macd+rsi50+roc5+vwap+bb_mid+candle | 16 | 99 | 82.83 | 2152.00 | 111 | 81.98 | 2255.50 | 21 | 66.67 | -112.00 | 16 | 68.75 | -29.50 | 2 | 100.00 | 101.00 |
| manha|11:52|BUY|v6|dmi4|ALL|ema8_21+ema17_34+rsi50+roc5+vwap+bb_mid+prev_candle | 16 | 109 | 81.65 | 2154.50 | 121 | 80.99 | 2258.00 | 26 | 69.23 | -27.00 | 17 | 70.59 | 21.00 | 3 | 100.00 | 151.50 |
| manha|11:52|BUY|v6|dmi4|WEEK|ema8_21+ema17_34+rsi50+roc5+vwap+bb_mid+prev_candle | 16 | 109 | 81.65 | 2154.50 | 121 | 80.99 | 2258.00 | 26 | 69.23 | -27.00 | 17 | 70.59 | 21.00 | 3 | 100.00 | 151.50 |
| manha|11:52|BUY|v6|dmi4|ALL|ema8_21+macd+rsi50+roc5+vwap+bb_mid+candle | 16 | 102 | 82.35 | 2136.00 | 114 | 81.58 | 2239.50 | 22 | 68.18 | -61.50 | 16 | 68.75 | -29.50 | 3 | 100.00 | 151.50 |
| manha|11:52|BUY|v6|dmi4|WEEK|ema8_21+macd+rsi50+roc5+vwap+bb_mid+candle | 16 | 102 | 82.35 | 2136.00 | 114 | 81.58 | 2239.50 | 22 | 68.18 | -61.50 | 16 | 68.75 | -29.50 | 3 | 100.00 | 151.50 |

## Top combos noite + manha

| id | folds_teste_ok | teste_trades | teste_winrate | teste_pontos | trades_modelo | winrate_modelo | pontos_modelo | trades_2026 | winrate_2026 | pontos_2026 | trades_90 | winrate_90 | pontos_90 | trades_30 | winrate_30 | pontos_30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|ALL|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 36 | 77.78 | 478.00 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|WEEK|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 36 | 77.78 | 478.00 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|ALL|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 37 | 78.38 | 528.50 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|WEEK|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 37 | 78.38 | 528.50 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|ALL|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 37 | 78.38 | 528.50 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+macd+roc5+roc10+prev_candle + manha|11:52|BUY|v5|adx20_dmi4|WEEK|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 18 | 188 | 83.51 | 4301.50 | 199 | 83.42 | 4522.00 | 37 | 78.38 | 528.50 | 27 | 74.07 | 191.00 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|ALL|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 37 | 78.38 | 528.50 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|WEEK|ema34_89+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 37 | 78.38 | 528.50 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|ALL|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 38 | 78.95 | 579.00 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|WEEK|preco_ema200+macd+roc5+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 38 | 78.95 | 579.00 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|ALL|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 38 | 78.95 | 579.00 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |
| COMBO::noite|21:02|SELL|v5|adx20_dmi4|ALL|ema17_34+preco_ema200+dmi+roc5+roc10+prev_candle+stoch50 + manha|11:52|BUY|v5|adx20_dmi4|WEEK|macd+roc5+vwap+bb_mid+candle+prev_candle+stoch50 | 18 | 191 | 83.25 | 4285.50 | 201 | 83.08 | 4455.50 | 38 | 78.95 | 579.00 | 28 | 75.00 | 241.50 | 9 | 88.89 | 287.00 |

## Leitura inicial

- Promover para TradingView somente candidatos que continuem fortes no holdout 2026 e nos recortes recentes.
- O score acima nao usa 2026; se 2026 estiver ruim, o candidato deve ser tratado como reprovado ou apenas diagnostico.
- Esta busca e a primeira bateria de confluencia. Apos teste no TV, registrar os resultados reais no relatorio principal.

## Teste TradingView - perfil 01

Perfil: `01 Noite 2102 SELL 75tr 85pct`.

| Periodo | Trades | Winrate | Resultado | DD | PF | Leitura |
|---|---:|---:|---:|---:|---:|---|
| Ultimos 365d | 53 | 69.81% | -7.00 USD | -848.00 USD | 0.998 | Reprovado no anual |
| Ultimos 90d | 14 | 71.43% | +74.00 USD | -619.00 USD | 1.079 | Fraco |
| Ultimos 30d | 6 | 83.33% | +271.00 USD | -321.00 USD | 2.158 | Recente positivo, mas poucos trades |

Decisao:

- nao promover o perfil `01`;
- testar em seguida o perfil `02 Noite 2102 SELL 84tr 86pct`;
- se o perfil `02` tambem nao confirmar, testar o perfil `03`.
