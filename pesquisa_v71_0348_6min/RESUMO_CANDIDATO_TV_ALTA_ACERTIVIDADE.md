# Candidato TV Alta Acertividade - Pesquisa

Base: export TradingView `V71_Pesquisa_3_Horarios_Fixos_Multi_Indicadores_CME_MINI_MNQ1!_2026-05-30.csv`.

Nao altera o V7.1 oficial.

## Melhor candidato acima de 80%

Modo: `81pct_105trades`

Regras:
- BUY 03:48 somente segunda e terca.
- BUY 20:58 somente domingo e terca.
- Mesmo take/stop: 50,5 / 117 pontos.
- Mesma direcao por votos do Pine de pesquisa.

Resultado no export TV:
- 105 trades
- 81,90% de acerto
- +5367,0 USD
- Max DD -551,5 USD
- Profit factor 2,776
- 2 meses negativos
- Menor quartil de validacao: 74,07% de acerto e +984,0 USD

## Candidato mais robusto por score

Modo: `79pct_129trades`

Regras:
- BUY 03:48 somente segunda e terca.
- BUY 20:58 somente domingo, terca e quarta.
- Mesmo take/stop: 50,5 / 117 pontos.

Resultado no export TV:
- 129 trades
- 79,84% de acerto
- +5726,5 USD
- Max DD -735,0 USD
- Profit factor 2,317
- 1 mes negativo
- Menor quartil de validacao: 69,70% de acerto e +709,5 USD

Leitura: fica um pouco abaixo de 80%, mas tem mais trades, maior lucro e apenas 1 mes negativo. Para meta estrita de acerto, usar `81pct_105trades`.

## Alternativas

`87pct_54trades`
- BUY 03:48 segunda.
- BUY 20:58 domingo.
- 54 trades, 87,04%, +3289,5 USD, DD -702,0, PF 3,257.

`84pct_78trades`
- BUY 03:48 segunda.
- BUY 20:58 domingo e terca.
- 78 trades, 84,62%, +4437,0 USD, DD -703,0, PF 3,224.

`79pct_129trades`
- BUY 03:48 segunda e terca.
- BUY 20:58 domingo, terca e quarta.
- 129 trades, 79,84%, +5726,5 USD, DD -735,0, PF 2,317.

## Observacao operacional

Para passar de 80% anual, foi necessario reduzir frequencia. A configuracao com todos os dias nao atingiu a meta.

Esta linha continua em pesquisa. Nao foi promovida a oficial.
