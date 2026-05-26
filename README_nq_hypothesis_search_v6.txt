VERSAO V6

Esta versao e focada especificamente em buscar as entradas do video.
Ela reduz a busca ampla e concentra nos parametros que sobreviveram aos testes:

- pivot_left 2 ou 3
- pivot_right 1
- entrada no candle de confirmacao ou no proximo candle
- BUY e SELL com regras separadas
- RSI 7 ou 10
- body ratio separado por lado
- wick opcional
- gap separado por lado
- filtro EMA curto opcional
- distancia da EMA opcional
- distancia do pivot por ATR opcional
- extremo local opcional

USO
python nq_hypothesis_search_v6.py --csv "CME_MINI_MNQ1!, 15.csv"

Mais busca:
python nq_hypothesis_search_v6.py --csv "CME_MINI_MNQ1!, 15.csv" --max-tests 25000
