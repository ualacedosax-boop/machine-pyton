# Validacao TV - Calendario DOW 230-85

Pesquisa separada. Nao altera o V7.1 oficial.

## Pine

`V71_PESQUISA_CALENDARIO_DOW_230_85_TV_2MIN.pine`

## Como testar

- Simbolo: `MNQ1!`
- Timeframe: `2m`
- Modo: Backtesting Profundo
- Take: `50.5`
- Stop: `117`
- Quantidade: `1`

## Perfis

| Perfil | Filtros | Uso esperado |
|---|---|---|
| `01 Max 365d 233tr 87pct` | quarta 02:56 `dmi_gap >= 3.5237`; quinta 04:30 `ema200_slope10 <= 4.7472` | Melhor pontuacao anual local |
| `02 Recente forte 234tr 85pct` | segunda 04:02 `vwap_slope10 <= 4.6748`; terca 03:12 `dist_vwap <= 22.2546` | Melhor 90d/30d local |

## Metricas locais esperadas

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 01 Max 365d | Ultimos 365d | 233 | 87.55% | 6909.0 | -316.5 | 3.04 |
| 01 Max 365d | Ultimos 90d | 63 | 84.13% | 1506.5 | -300.5 | 2.29 |
| 01 Max 365d | Ultimos 30d | 22 | 81.82% | 441.0 | -234.0 | 1.94 |
| 02 Recente forte | Ultimos 365d | 234 | 85.90% | 6289.5 | -316.5 | 2.63 |
| 02 Recente forte | Ultimos 90d | 56 | 89.29% | 1823.0 | -300.5 | 3.60 |
| 02 Recente forte | Ultimos 30d | 21 | 90.48% | 725.5 | -117.0 | 4.10 |

## Observacoes

- O TradingView pode divergir por dados, contrato continuo, horario e regra de execucao.
- Se o TV ficar perto dos numeros locais, o perfil 02 e o primeiro teste recomendado para operabilidade recente.
- Nenhum perfil deve substituir o oficial sem aprovacao explicita.
