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

Resultado no export TV com stop original 117:
- 105 trades
- 81,90% de acerto
- +5367,0 USD
- Max DD -551,5 USD
- Profit factor 2,776
- 2 meses negativos
- Menor quartil de validacao: 74,07% de acerto e +984,0 USD

Resultado estimado por excursao com stop 110:
- 105 trades
- 81,90% de acerto
- +5521,0 USD
- Max DD -509,5 USD
- Profit factor 2,925
- 2 meses negativos
- Menor quartil de validacao: 74,07% de acerto e +1012,0 USD

Leitura: stop 110 melhorou PnL, DD e PF sem reduzir o acerto no teste por excursao. Precisa confirmar no TradingView.

## Candidato mais robusto por score

Modo: `79pct_129trades`

Regras:
- BUY 03:48 somente segunda e terca.
- BUY 20:58 somente domingo, terca e quarta.
- Mesmo take/stop: 50,5 / 117 pontos.

Resultado no export TV com stop original 117:
- 129 trades
- 79,84% de acerto
- +5726,5 USD
- Max DD -735,0 USD
- Profit factor 2,317
- 1 mes negativo
- Menor quartil de validacao: 69,70% de acerto e +709,5 USD

Resultado estimado por excursao com stop 110:
- 129 trades
- 79,84% de acerto
- +5950,5 USD
- Max DD -679,0 USD
- Profit factor 2,443
- 1 mes negativo
- Menor quartil de validacao: 69,70% de acerto e +765,5 USD

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

## Novo candidato com 3 horarios e 30/90 dias positivos

Arquivo Pine: `V71_PESQUISA_TV_3H_80PCT_ROBUSTO_FIXO.pine`

Regras:
- BUY 03:48 somente segunda e terca.
- BUY 10:30 somente segunda.
- SELL 10:30 somente sexta.
- BUY 20:58 somente domingo e quarta.
- Take/stop: 50,5 / 117 pontos.

Resultado no export TV:
- 160 trades
- 80,63% de acerto
- +6878,0 USD
- Max DD -816,5 USD
- Profit factor 2,136
- 90 dias: 41 trades, 87,80%, +2466,0 USD
- 30 dias: 10 trades, 80,00%, +340,0 USD

Leitura: e o melhor equilibrio encontrado ate agora com os 3 horarios ativos e validacao recente positiva. Ainda precisa ser confirmado no TradingView antes de qualquer promocao para oficial.

Observacao apos teste visual no TV:
- O Pine `V71_PESQUISA_TV_ALTA_ACERTIVIDADE_CALENDARIO.pine` ficou bom em 365/90 dias, mas negativo nos ultimos 30 dias no print do TradingView.
- Portanto ele nao deve ser considerado pronto para operar.
- O proximo candidato para validar no TV e `V71_PESQUISA_TV_3H_80PCT_ROBUSTO_FIXO.pine`.
- Depois de exportar a Lista de negociacoes desse Pine, rodar `pesquisa_v71_0348_6min/auditar_export_tv_3h_robusto.py` para conferir 365/90/30 dias com o resultado real do TradingView.

## Candidato novo por regime DMI em candles IBKR

Arquivo Pine: `V71_PESQUISA_TV_3H_DMI3_ROBUSTO_FIXO.pine`

Regras:
- Mesmas regras do candidato 3H robusto.
- Filtro adicional: `abs(DI+ - DI-) >= 3`.

Resultado em simulacao local com candles IBKR 2min, entrada no candle seguinte e stop primeiro:
- 365 dias: 131 trades, 83,97%, +3098,0 pontos, DD -484,0, PF 2,261.
- 90 dias: 31 trades, 80,65%, +560,5 pontos.
- 30 dias: 11 trades, 81,82%, +220,5 pontos.

Leitura: melhor equilibrio local entre frequencia e robustez recente. Precisa confirmacao no TradingView, pois o TV pode recalcular preenchimentos e quantidade de trades.

## Variante alta acertividade DMI10

Arquivo Pine: `V71_PESQUISA_TV_3H_DMI10_ALTA_ACERTIVIDADE.pine`

Regras:
- Mesmas regras do candidato 3H robusto.
- Filtro adicional: `ADX >= 25` e `abs(DI+ - DI-) >= 10`.

Resultado em simulacao local com candles IBKR 2min:
- 365 dias: 45 trades, 91,11%, +1602,5 pontos, DD -183,5, PF 4,424.
- 90 dias: 11 trades, 81,82%, +220,5 pontos.
- 30 dias: 5 trades, 80,00%, +85,0 pontos.

Leitura: e a versao mais defensiva. A vantagem e acerto/DD; a desvantagem e baixa frequencia.

## Variante DMI3 com take 45,5

Arquivo Pine: `V71_PESQUISA_TV_3H_DMI3_TAKE45_ROBUSTO.pine`

Regras:
- Mesmas regras do candidato DMI3.
- Take reduzido de 50,5 para 45,5 pontos.
- Stop mantido em 117 pontos.

Resultado em re-simulacao local com candles IBKR 2min:
- 365 dias: 132 trades, 86,36%, +3081,0 pontos, DD -331,5, PF 2,463.
- 90 dias: 31 trades, 87,10%, +760,5 pontos.
- 30 dias: 11 trades, 90,91%, +338,0 pontos.

Leitura: melhorou acerto, DD e resultado recente em relacao ao DMI3 original, sem reduzir frequencia. E o principal candidato novo para validacao no TradingView.

## Compilado de estrategias vencedoras

Arquivo Pine: `V71_PESQUISA_COMPILADO_VENCEDORAS_MAX_ENTRADAS.pine`

Objetivo:
- Unir os blocos positivos em um unico Pine de pesquisa no grafico de 2 minutos.
- Aumentar o numero de entradas.
- Evitar duplicidade no mesmo candle e manter `pyramiding=0`.

Modulos:
- DMI3: 03:48, 10:30 e 20:58, com take 50,5 por padrao.
- EMA/ADX extra: 03:50 e 20:54.
- EMA/ADX alternativo 20:52 fica como opcional desligado.

Observacao:
- Como e uma uniao de estrategias, precisa validacao no TradingView em 365/90/30 dias. Unir estrategias aumenta frequencia, mas pode reduzir acerto se algum modulo piorar o conjunto.

Resultado local em candles IBKR 2min:
- DMI3 Take45 sozinho: 132 trades, 86,36%, +3081,0 pontos, DD -331,5, PF 2,463.
- EMA/ADX extra sozinho: 139 trades, 75,54%, +1324,5 pontos, DD -827,5, PF 1,333.
- Compilado DMI3 + EMA/ADX: 230 trades, 81,30%, +3947,5 pontos, DD -632,0, PF 1,785.
- Compilado com 20:52 ligado: 234 trades, 80,77%, +3814,5 pontos, DD -632,0, PF 1,725.

Leitura:
- O compilado aumenta bastante a frequencia e melhora pontos totais contra DMI3 sozinho.
- O 20:52 piorou 90 dias e pontos totais, por isso fica desligado por padrao.
- Para operar com maior acerto, DMI3 Take45 sozinho continua melhor.
- Para operar com maior frequencia, testar o compilado sem 20:52.

Auditoria do TradingView:
- Depois de exportar a Lista de negociacoes do Pine compilado, rodar `pesquisa_v71_0348_6min/auditar_export_tv_compilado_vencedoras.py`.
- O auditor separa resultado por modulo, horario, 365/90/30 dias.

Correcao apos teste no TV:
- A primeira versao do compilado nao gerou entradas no TradingView.
- Foi removida a trava manual `flat`; agora o controle fica por `pyramiding=0`, igual aos Piness que ja geraram entradas.
- O take DMI3 padrao voltou para 50,5, pois essa versao ja foi validada no TV com 140 trades e 82,14% em 365 dias.
