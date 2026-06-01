# Pesquisa V7.1 03:48 6min

Linha de pesquisa isolada. Nao alterar o robo oficial ate existir resultado melhor,
validado fora da amostra, e aprovado manualmente.

## Objetivo

Buscar aumento de frequencia sem perder assertividade, inspirado em setup de 6 minutos
com entradas perto de 03:48.

## Primeira bateria

Script:

`pesquisar_operacional_0348_6min.py`

Testes:

- candles MNQ em 6 minutos;
- janela de candidatos entre 02:30 e 06:00;
- setups de take/stop:
  - 139 ticks simetrico, equivalente a 34.75 pontos;
  - V7.1 oficial 50.5/117;
  - V7.1 com stop 90;
- regras simples por horario e direcao;
- regras por tendencia, reversao, candle e rompimento;
- modelos ML:
  - LogisticRegression;
  - RandomForest;
  - ExtraTrees;
  - HistGradientBoosting;
  - Rede neural MLP.

## Criterio de seguranca

Nada desta pasta deve ser promovido para o operacional sem:

1. Resultado melhor que o V7.1 oficial.
2. Validacao fora da amostra.
3. Resumo por mes.
4. Aprovacao expressa antes de mexer no oficial.

## Candidato atual para TradingView

Arquivo Pine:

`V71_PESQUISA_REGIME_V3B_FALLBACK_2058_OPERAVEL.pine`

Status:

- Pesquisa separada.
- Oficial V7.1 nao alterado.
- Timeframe alvo: MNQ1!, 2 minutos.
- TP/SL: 50.5 / 117 pontos.
- Base: Regime V2 robusto.
- Fallback: somente as 20:58, para evitar decisao com informacao futura.

Perfis locais esperados:

| Perfil | Trades 365d | Winrate | Pontos | DD | PF | 30d |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Conservador 224 | 224 | 86.16% | 6119.5 | -367.0 | 2.69 | 19 trades, 89.47% |
| Frequente 230 | 230 | 85.22% | 5920.0 | -566.5 | 2.49 | 20 trades, 85.00% |

Observacao:

O perfil Conservador 224 e o primeiro candidato a validar no TradingView. O perfil Frequente 230 aumenta um pouco a frequencia, mas aceita drawdown maior.

## Validacao no TradingView

1. Abrir `MNQ1!` no timeframe de 2 minutos.
2. Colar o Pine `V71_PESQUISA_REGIME_V3B_FALLBACK_2058_OPERAVEL.pine`.
3. Testar primeiro o perfil `Conservador 224`.
4. Conferir 365, 90 e 30 dias.
5. Exportar a aba `Lista de negociacoes` do TradingView em CSV.
6. Rodar:

```powershell
python .\pesquisa_v71_0348_6min\auditar_export_tv_v3b_fallback_2058.py
```

O auditor compara o CSV do TradingView com os alvos locais e gera:

- `auditoria_export_tv_v3b_fallback_2058.xlsx`
- `auditoria_export_tv_v3b_fallback_2058_trades.csv`
- `auditoria_export_tv_v3b_fallback_2058_resumo.csv`

## Historico recente

- DMI3 robusto validado no TradingView: 140 trades, 82.14%, PF 1.985 em 365 dias.
- Compilado V3 validado no TradingView: 269 trades, 75.84%, PF 1.645 em 365 dias.
- V3B local busca o meio termo: perto de 224-230 trades, acima de 85%, com fallback operavel.
