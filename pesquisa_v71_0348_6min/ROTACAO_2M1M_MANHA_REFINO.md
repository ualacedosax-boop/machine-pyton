# Rotacao 2M/1M Manha Refino

Pesquisa separada. Nao altera o V7.1 oficial.

Objetivo: continuar a busca depois que o combo `20:54 SELL + 10:30 SELL` reprovou no TradingView e o bloco de noite ficou positivo apenas no recente, mas fraco no anual.

## Metodo

- Timeframe alvo no TradingView: `MNQ1!`, `2m`, Backtesting Profundo.
- Janela operacional: manha em torno de `10:30`.
- Rotacao: treina dois meses e testa o terceiro.
- Exemplo do criterio: treina janeiro/fevereiro e testa marco; treina abril/maio e testa junho.
- Filtro de selecao: pelo menos 5 folds de teste positivos, recortes locais 90d e 30d positivos.
- Take/stop: `50.5` / `117`.

## Arquivo Pine

`V71_ROTACAO_2M1M_MANHA_REFINO_TV_2MIN.pine`

## Perfis

| Ordem | Perfil | Regra | OOS trades | OOS winrate | OOS pontos | 365d trades | 365d winrate | 365d pontos | 90d | 30d |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | `03 EMA200 ROC10 71tr` | `10:30 SELL`, `distEma200 <= 27.5907`, `roc10 <= -12.2250` | 29 | 86.21% | +794.5 | 71 | 84.51% | +1743.0 | 12tr, 91.67%, +438.5 | 5tr, 80.00%, +85.0 |
| 2 | `02 VWAP PosRange 83tr` | `10:30 SELL`, `distVwap <= 9.7502`, `posRange20 <= 0.5400` | 40 | 85.00% | +1015.0 | 83 | 83.13% | +1846.5 | 13tr, 92.31%, +489.0 | 5tr, 80.00%, +85.0 |
| 3 | `01 Macd PosRange 106tr` | `10:30 SELL`, `macdHist <= 0.8812`, `posRange20 <= 0.5400` | 58 | 79.31% | +919.0 | 106 | 80.19% | +1835.5 | 25tr, 80.00%, +425.0 | 7tr, 85.71%, +186.0 |
| 4 | `04 VWAP Macd 61tr` | `10:30 SELL`, `distVwap <= 9.7502`, `macdHist <= -0.2755` | 33 | 84.85% | +829.0 | 61 | 81.97% | +1238.0 | 9tr, 88.89%, +287.0 | 4tr, 75.00%, +34.5 |

## Leitura

- O perfil `03` ficou como padrao do Pine por ser o mais conservador: menos trades, OOS acima de 86%, 365d perto de 85%, 90d forte e 30d positivo.
- O perfil `02` e o segundo teste: mais trades que o `03` e recortes 90d/30d locais fortes.
- O perfil `01` serve para medir frequencia; nao e o primeiro porque o acerto local anual caiu para perto de 80%.
- O perfil `04` e diagnostico secundario, pois o 30d local tem poucos trades.

## Decisao esperada no TradingView

- Se `03` ou `02` confirmar acerto alto, lucro positivo e DD controlado no TV, manter a manha e procurar uma nova regra de noite para combinar depois.
- Se os quatro perfis cairem no TV, a proxima busca deve usar export/lista de trades do proprio TradingView para alinhar a diferenca entre motor local e Pine.
- Nenhum perfil deve substituir o V7.1 oficial sem validacao explicita.
