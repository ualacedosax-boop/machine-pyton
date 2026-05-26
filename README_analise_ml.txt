ARQUIVOS GERADOS

1) analise_entradas_ml.py
   Script pronto para:
   - ler candles OHLCV
   - calcular dezenas de indicadores
   - casar as entradas BUY/SELL com os candles
   - gerar ranking estatístico
   - rodar RandomForest exploratório

2) entradas_exemplo.csv
   Sua lista de entradas já formatada para o script.

COMO USAR

python analise_entradas_ml.py --ohlc "SEU_ARQUIVO_OHLC.csv" --entradas "entradas_exemplo.csv" --saida "./saida"

ARQUIVO OHLC ESPERADO

Colunas mínimas:
datetime,open,high,low,close,volume

ou:
date,time,open,high,low,close,volume

EXEMPLO:
2025-10-28 10:30:00,....
2025-10-28 10:45:00,....

SAÍDAS CRIADAS PELO SCRIPT

01_entradas_casadas.csv
02_ranking_indicadores.csv
03_dataset_completo_indicadores.csv
04_importancias_ml.csv
05_matriz_confusao.csv
06_metricas_ml.json
07_resumo.txt

OBSERVAÇÃO

Sem OHLC real não dá para medir o comportamento exato dos indicadores.
O script foi feito para você rodar assim que tiver o CSV exportado do TradingView, NinjaTrader, Profit ou MT5.