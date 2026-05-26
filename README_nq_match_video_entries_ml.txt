ARQUIVOS ENTREGUES

1) nq_match_video_entries_ml.py
Script para ajustar parametros do indicador com base nos horarios do video.

2) README_nq_match_video_entries_ml.txt
Instrucoes de uso.

COMO USAR

No terminal, na pasta onde estiver o script e o CSV:

python nq_match_video_entries_ml.py --csv "CME_MINI_MNQ1!, 15.csv"

O script ja usa, por padrao, os horarios que voce mandou na conversa.

SAIDA

Ele cria a pasta:
saida_match_video_ml

Arquivos principais:
- report.txt
- best_params.json
- leaderboard.csv
- best_matches.csv
- candidate_signals.csv
- pivot_ml_dataset_scored.csv
- ml_filtered_signals.csv
- ml_matches.csv
- best_pine_params.txt

OBSERVACAO

Como sua lista de entradas nao e exaustiva, o script usa uma metrica soft:
- prioriza acertar os horarios marcados
- penaliza sinais extras de forma leve
