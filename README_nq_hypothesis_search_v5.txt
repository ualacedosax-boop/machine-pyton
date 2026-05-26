VERSAO V5

Esta versao testa hipoteses mais amplas sobre o sinal:
- pivots
- RSI com periodos diferentes para BUY e SELL
- virada do RSI
- Stoch separado por lado
- filtro EMA de tendencia
- distancia da EMA
- distancia do pivot por ATR
- wick opcional
- close acima/abaixo do candle anterior
- extremo local separado para BUY e SELL
- gaps separados

USO
python nq_hypothesis_search_v5.py --csv "CME_MINI_MNQ1!, 15.csv"

Mais busca:
python nq_hypothesis_search_v5.py --csv "CME_MINI_MNQ1!, 15.csv" --max-tests 25000
