UNSUPERVISED ENTRY PATTERNS

Este script usa clustering apenas nas entradas reais para descobrir familias de entrada.
Tambem cria dois scores:
- buy_exhaustion_score
- sell_exhaustion_score

USO
python nq_unsupervised_entry_patterns.py --csv "CME_MINI_MNQ1!, 15.csv"

Opcional
python nq_unsupervised_entry_patterns.py --csv "CME_MINI_MNQ1!, 15.csv" --clusters 4
