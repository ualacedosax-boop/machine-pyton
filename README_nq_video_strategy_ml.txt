ARQUIVOS ENTREGUES

1) nq_video_strategy_ml.py
Script em Python que:
- lê seu CSV do NQ/MNQ 15 minutos;
- cria indicadores e features;
- testa 5 versões de estratégia candidata;
- treina modelos de ML para filtrar sinais;
- compara versão bruta vs versão com ML;
- cruza frames do vídeo com janelas do preço por similaridade visual aproximada;
- salva relatórios em CSV/JSON/TXT.

COMO USAR NO SEU CASO

No terminal, dentro da pasta onde estiver o script:

python nq_video_strategy_ml.py --csv "CME_MINI_MNQ1!, 15.csv"

Se quiser cruzar com os frames que já estão no ambiente, adapte para os seus caminhos locais.
Exemplo:

python nq_video_strategy_ml.py ^
  --csv "CME_MINI_MNQ1!, 15.csv" ^
  --frames "frame_265.jpg" "frame_230.jpg" "frame_150.jpg" "f1_260.jpg"

SAÍDAS GERADAS
- strategy_summary.csv
- all_trades.csv
- ml_report.json
- frame_matches.json
- report.txt

INTERPRETAÇÃO
- strategy_summary.csv:
  mostra ranking das estratégias e das versões filtradas por ML.
- all_trades.csv:
  lista todas as operações simuladas.
- frame_matches.json:
  mostra quais trechos do histórico mais se parecem com cada frame.
- ml_report.json:
  mostra métricas AUC/accuracy/precision/recall dos modelos.

OBSERVAÇÃO IMPORTANTE
O cruzamento das imagens com o preço é uma aproximação visual.
Sem timestamp real do vídeo ou OCR confiável do eixo do gráfico, ele encontra
"trechos parecidos", não necessariamente o trecho exato.

PRÓXIMO PASSO RECOMENDADO
Rodar o script, ver qual estratégia ficou melhor e depois transformar a campeã em:
- Pine Script para TradingView, ou
- Python com otimização mais pesada, ou
- EA/robô para outra plataforma.
