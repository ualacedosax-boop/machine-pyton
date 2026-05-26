ITERATIVE ML SEARCH

Este script faz uma busca iterativa supervisionada:
- cria features dos candles
- compara com as entradas reais do vídeo
- testa várias combinações de features, modelos e thresholds
- para cedo se atingir a precisão desejada

IMPORTANTE
Ele tenta atingir a meta, mas não pode garantir 90% de precisão real.
Com apenas ~32 entradas rotuladas, pode não haver informação suficiente.

USO
python nq_iterative_ml_search.py --csv "CME_MINI_MNQ1!, 15.csv"

Mais agressivo:
python nq_iterative_ml_search.py --csv "CME_MINI_MNQ1!, 15.csv" --target-precision 0.90 --max-rounds 120
