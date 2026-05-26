ITERATIVE ML SEARCH V2

Versão expandida com novos indicadores:
- ADX, +DI, -DI
- CCI
- ROC 3/5
- MACD histogram
- Williams %R
- Bollinger width e position
- slope da EMA 9 e 13
- breakout de máxima/mínima curta
- range position de 5 barras

USO
python nq_iterative_ml_search_v2.py --csv "CME_MINI_MNQ1!, 15.csv"

Mais agressivo:
python nq_iterative_ml_search_v2.py --csv "CME_MINI_MNQ1!, 15.csv" --target-precision 0.90 --max-rounds 150
