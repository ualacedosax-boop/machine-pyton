ENTRY OBSERVATION ML

Este script observa o que estava acontecendo exatamente nos candles das entradas do video.

Ele extrai, para cada entrada:
- RSI 7, 10, 14
- K e D
- body ratio
- wick superior/inferior
- distancia para EMA 5, 9, 13 em ATR
- relacao entre medias
- candle verde/vermelho
- close > close[1] ou close < close[1]

USO
python nq_entry_observation_ml.py --csv "CME_MINI_MNQ1!, 15.csv"
