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
