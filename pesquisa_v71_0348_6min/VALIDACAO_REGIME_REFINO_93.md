# Validacao Regime Refino 93

Pesquisa separada. Nao altera o V7.1 oficial.

## Como testar no TradingView

- Simbolo: `MNQ1!`
- Timeframe: `2m`
- Modo: Backtesting Profundo
- Pine: `V71_PESQUISA_REGIME_REFINO_93_TV_2MIN.pine`
- Perfil recomendado primeiro: `02 Equilibrado 139 94pct`

## Resumo local

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 01_refino_157_93 | all | 370 | 81.35% | 7127.5 | -1064.0 | 1.88 |
| 01_refino_157_93 | 2024 | 146 | 69.86% | 3.0 | -1064.0 | 1.00 |
| 01_refino_157_93 | 2025 | 178 | 88.20% | 5471.5 | -250.0 | 3.23 |
| 01_refino_157_93 | 2026 | 46 | 91.30% | 1653.0 | -183.5 | 4.53 |
| 01_refino_157_93 | 365d | 157 | 92.99% | 6086.0 | -234.0 | 5.73 |
| 01_refino_157_93 | 90d | 26 | 92.31% | 978.0 | -133.0 | 5.18 |
| 01_refino_157_93 | 30d | 9 | 100.00% | 454.5 | 0.0 | 999.00 |
| 02_equilibrado_139_94 | all | 327 | 83.18% | 7301.0 | -697.0 | 2.13 |
| 02_equilibrado_139_94 | 2024 | 127 | 71.65% | 383.5 | -697.0 | 1.09 |
| 02_equilibrado_139_94 | 2025 | 155 | 90.32% | 5315.0 | -234.0 | 4.03 |
| 02_equilibrado_139_94 | 2026 | 45 | 91.11% | 1602.5 | -183.5 | 4.42 |
| 02_equilibrado_139_94 | 365d | 139 | 94.24% | 5679.5 | -183.5 | 7.07 |
| 02_equilibrado_139_94 | 90d | 27 | 92.59% | 1028.5 | -117.0 | 5.40 |
| 02_equilibrado_139_94 | 30d | 8 | 100.00% | 404.0 | 0.0 | 999.00 |
| 03_frequente_191_89 | all | 453 | 79.69% | 7466.5 | -1348.5 | 1.69 |
| 03_frequente_191_89 | 2024 | 175 | 70.29% | 127.5 | -1348.5 | 1.02 |
| 03_frequente_191_89 | 2025 | 216 | 85.19% | 5548.0 | -468.0 | 2.48 |
| 03_frequente_191_89 | 2026 | 62 | 87.10% | 1791.0 | -234.0 | 2.91 |
| 03_frequente_191_89 | 365d | 191 | 89.01% | 6128.0 | -468.0 | 3.49 |
| 03_frequente_191_89 | 90d | 40 | 85.00% | 1015.0 | -234.0 | 2.45 |
| 03_frequente_191_89 | 30d | 13 | 84.62% | 321.5 | -117.0 | 2.37 |

## Conferencia das entradas

O arquivo local `validacao_regime_refino_93_trades.csv` contem as entradas esperadas.
Use as colunas `perfil`, `modulo`, `datahora_sinal`, `datahora_entrada`, `direcao`, `resultado` e `pontos` para comparar com o export do TradingView.

A diferenca mais comum entre Python e TradingView costuma vir de:

- dados historicos diferentes;
- fuso/horario do candle;
- modo de execucao da ordem no TradingView;
- arredondamento de tick;
- divergencia no VWAP/ADX/DMI.

## Primeiras entradas por perfil

### 01_refino_157_93

| Sinal | Entrada | Modulo | Direcao | Resultado | Pontos |
|---|---|---|---|---|---:|
| 2024-03-15 10:30:00 | 2024-03-15 10:32:00 | DMI3_1030_SELL | SELL | TAKE | 50.5 |
| 2024-03-18 03:48:00 | 2024-03-18 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 10:30:00 | 2024-03-18 10:32:00 | DMI3_1030_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 20:52:00 | 2024-03-18 20:54:00 | REG_2052_SELL_A | SELL | TAKE | 50.5 |
| 2024-03-20 20:52:00 | 2024-03-20 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-21 03:48:00 | 2024-03-21 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-22 03:46:00 | 2024-03-22 03:48:00 | REG_0346_SELL | SELL | TAKE | 50.5 |
| 2024-03-24 20:52:00 | 2024-03-24 20:54:00 | REG_2052_BUY | BUY | STOP | -117.0 |
| 2024-03-25 20:52:00 | 2024-03-25 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-26 10:30:00 | 2024-03-26 10:32:00 | REG_1030_SELL | SELL | TAKE | 50.5 |
| 2024-03-26 20:52:00 | 2024-03-26 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-27 20:52:00 | 2024-03-27 20:54:00 | REG_2052_SELL_A | SELL | STOP | -117.0 |

### 02_equilibrado_139_94

| Sinal | Entrada | Modulo | Direcao | Resultado | Pontos |
|---|---|---|---|---|---:|
| 2024-03-18 03:48:00 | 2024-03-18 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 10:30:00 | 2024-03-18 10:32:00 | DMI3_1030_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 20:52:00 | 2024-03-18 20:54:00 | REG_2052_SELL_A | SELL | TAKE | 50.5 |
| 2024-03-20 20:52:00 | 2024-03-20 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-21 03:48:00 | 2024-03-21 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-22 03:46:00 | 2024-03-22 03:48:00 | REG_0346_SELL | SELL | TAKE | 50.5 |
| 2024-03-24 20:52:00 | 2024-03-24 20:54:00 | REG_2052_BUY | BUY | STOP | -117.0 |
| 2024-03-25 20:52:00 | 2024-03-25 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-26 20:52:00 | 2024-03-26 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-27 20:52:00 | 2024-03-27 20:54:00 | REG_2052_SELL_A | SELL | STOP | -117.0 |
| 2024-04-02 03:48:00 | 2024-04-02 03:50:00 | DMI3_0348_BUY | BUY | STOP | -117.0 |
| 2024-04-04 10:30:00 | 2024-04-04 10:32:00 | REG_1030_BUY | BUY | STOP | -117.0 |

### 03_frequente_191_89

| Sinal | Entrada | Modulo | Direcao | Resultado | Pontos |
|---|---|---|---|---|---:|
| 2024-03-15 10:30:00 | 2024-03-15 10:32:00 | DMI3_1030_SELL | SELL | TAKE | 50.5 |
| 2024-03-18 03:48:00 | 2024-03-18 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 10:30:00 | 2024-03-18 10:32:00 | DMI3_1030_BUY | BUY | TAKE | 50.5 |
| 2024-03-18 20:52:00 | 2024-03-18 20:54:00 | REG_2052_SELL_A | SELL | TAKE | 50.5 |
| 2024-03-20 20:52:00 | 2024-03-20 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-21 03:48:00 | 2024-03-21 03:50:00 | REG_0348_BUY | BUY | TAKE | 50.5 |
| 2024-03-22 03:46:00 | 2024-03-22 03:48:00 | REG_0346_SELL | SELL | TAKE | 50.5 |
| 2024-03-24 20:52:00 | 2024-03-24 20:54:00 | REG_2052_BUY | BUY | STOP | -117.0 |
| 2024-03-25 20:52:00 | 2024-03-25 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-26 10:30:00 | 2024-03-26 10:32:00 | REG_1030_SELL | SELL | TAKE | 50.5 |
| 2024-03-26 20:52:00 | 2024-03-26 20:54:00 | REG_2052_BUY | BUY | TAKE | 50.5 |
| 2024-03-27 20:52:00 | 2024-03-27 20:54:00 | REG_2052_SELL_A | SELL | STOP | -117.0 |

