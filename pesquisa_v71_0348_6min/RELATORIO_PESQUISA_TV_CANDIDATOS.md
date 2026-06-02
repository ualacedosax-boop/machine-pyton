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
| 1 | 04:06 reversao multiano | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` | 122 | 86.07% | 3313.5 | -183.5 | 2.67 | Melhor robustez multiano com acerto alto |
| 2 | Regime 191/89 multiano | 2m | `V71_PESQUISA_REGIME_191_89_MULTIANO_TV_2MIN.pine` | 191 | 89.01% nos ultimos 365d | 6128.0 | -468.0 | 3.49 | Melhor 365d, mas 2024 ficou fraco |
| 3 | 04:06 reversao sem filtro | 6m | `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` perfil 01 | 373 | 80.16% | 6441.5 | -550.5 | 1.74 | Frequencia alta e anos positivos, mas abaixo do alvo de acerto |
| 4 | Calendario top tokens | 2m | `V71_PESQUISA_TV_CALENDARIO_TOP_TOKENS_3H.pine` | 54 a 160 | 80% a 87% | variavel | variavel | variavel | Bom para estudar blocos de horario, nao final |

## Candidato 1: 04:06 reversao multiano

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

## Candidato 2: Regime 191/89 multiano

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

## Candidato 3: 04:06 reversao sem filtro

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

`V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine`, perfil `02 Multiano 86pct`.

Melhor candidato para tentar mais frequencia:

`V71_PESQUISA_REGIME_191_89_MULTIANO_TV_2MIN.pine`.

Regra pratica:

- se o TradingView confirmar o 04:06 multiano perto de 86%, ele vira a linha mais segura de pesquisa;
- se o TradingView confirmar o regime 191/89 nos ultimos 365 dias, ele vira candidato de alta performance, mas ainda precisa controle de risco por causa de 2024;
- nenhum candidato deve substituir o oficial sem aprovacao explicita.

## Proximo teste recomendado no TradingView

1. Testar `V71_PESQUISA_0406_REVERSAO_MULTIANO_TV_6MIN.pine` em `MNQ1!`, `6m`, perfil `02 Multiano 86pct`.
2. Conferir 365 dias, 90 dias e 30 dias.
3. Testar `V71_PESQUISA_REGIME_191_89_MULTIANO_TV_2MIN.pine` em `MNQ1!`, `2m`.
4. Comparar com as metricas locais acima.

