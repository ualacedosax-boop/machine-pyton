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
| `03 Pior ano melhor 230tr 86pct` | terca 03:12 `dmi_gap >= 2.7238`; quinta 04:30 `dmi_gap <= 12.7108` | Melhor pior-ano dentro da familia |
| `04 Robusto anual 222tr 85pct` | segunda 04:02 `ema_gap >= 2.6933`; quinta 04:30 `dmi_gap <= 22.1959` e `vwap_slope10 <= 1.9005` | Melhor equilibrio anual de frequencia alta; todos os anos 80%+ |
| `05 Alta acerto 147tr 89pct` | terca 03:12 `range_30 <= 16.75`; quarta 02:56 `ema_gap >= 3.3369`; quinta 04:30 `adx14 <= 20.3605` | Melhor acerto robusto multiano nesta familia |

## Metricas locais esperadas

| Perfil | Periodo | Trades | Winrate | Pontos | DD | PF |
|---|---|---:|---:|---:|---:|---:|
| 01 Max 365d | Ultimos 365d | 233 | 87.55% | 6909.0 | -316.5 | 3.04 |
| 01 Max 365d | Ultimos 90d | 63 | 84.13% | 1506.5 | -300.5 | 2.29 |
| 01 Max 365d | Ultimos 30d | 22 | 81.82% | 441.0 | -234.0 | 1.94 |
| 02 Recente forte | Ultimos 365d | 234 | 85.90% | 6289.5 | -316.5 | 2.63 |
| 02 Recente forte | Ultimos 90d | 56 | 89.29% | 1823.0 | -300.5 | 3.60 |
| 02 Recente forte | Ultimos 30d | 21 | 90.48% | 725.5 | -117.0 | 4.10 |
| 03 Pior ano melhor | Ultimos 365d | 230 | 86.09% | 6255.0 | -300.5 | 2.67 |
| 03 Pior ano melhor | Ultimos 90d | 56 | 85.71% | 1488.0 | -234.0 | 2.59 |
| 03 Pior ano melhor | Ultimos 30d | 20 | 85.00% | 507.5 | -234.0 | 2.45 |
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

## Observacoes

- O TradingView pode divergir por dados, contrato continuo, horario e regra de execucao.
- Resultado informado no TradingView para o perfil 01 ficou abaixo do local e reprova esse perfil como primeira escolha.
- Resultado informado no TradingView para o perfil 04 tambem ficou abaixo do local nos recortes 365d/90d; o 30d foi positivo, mas insuficiente para confirmar.
- O perfil 05 deve ser testado agora se o foco for acerto/DD, aceitando menor frequencia.
- O perfil 02 continua sendo o melhor teste para operabilidade recente.
- A auditoria anterior mostrou fragilidade na faixa 230-250; a busca multifaixa achou o perfil 04 com todos os anos 80%+, mas ainda e pesquisa, nao oficial.
- Nenhum perfil deve substituir o oficial sem aprovacao explicita.

## Resultado informado no TradingView

Print recebido em teste no `MNQ1!`, timeframe `2m`, Backtesting Profundo. O painel do Pine indicava `Perfil 01 MAX365`.

| Perfil | Periodo TV | Trades | Winrate | PnL TV | DD TV | PF TV | Leitura |
|---|---|---:|---:|---:|---:|---:|---|
| 01 Max 365d | Ultimos 365d | 240 | 81.25% | +9165.00 USD | 1105.00 USD | 1.87 | Reprovado vs expectativa local de 87.55% e PF 3.04 |
| 01 Max 365d | Ultimos 90d | 61 | 70.49% | +131.00 USD | 1105.00 USD | 1.031 | Muito fraco no recorte recente |
| 01 Max 365d | Ultimos 30d | 20 | 75.00% | +345.00 USD | 543.00 USD | 1.295 | Abaixo da meta |
| 04 Robusto anual | Ultimos 365d | 224 | 80.80% | +8219.00 USD | 1206.00 USD | 1.817 | Nao confirmou: local esperava 85.59% e PF 2.56 |
| 04 Robusto anual | Ultimos 90d | 57 | 73.68% | +732.00 USD | 1206.00 USD | 1.209 | Fraco no recorte recente |
| 04 Robusto anual | Ultimos 30d | 18 | 83.33% | +813.00 USD | 417.00 USD | 2.158 | Bom 30d, mas isolado |

Proximo teste recomendado no TradingView: perfil `05 Alta acerto 147tr 89pct`. Se tambem nao confirmar, parar essa familia e buscar outra logica.
