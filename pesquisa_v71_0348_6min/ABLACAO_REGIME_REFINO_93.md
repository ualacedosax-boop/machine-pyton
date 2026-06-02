# Ablacao Regime Refino 93

Pesquisa separada. Nao altera o V7.1 oficial.

Objetivo: testar cortes e combinacoes dos modulos atuais do Refino 93 para saber se existe melhora robusta antes de criar outro Pine.

## Perfis atuais

| cenario | trades_365d | winrate_365d | pontos_365d | dd_365d | pf_365d | trades_2024 | winrate_2024 | pontos_2024 | trades_2025 | winrate_2025 | pontos_2025 | trades_2026 | winrate_2026 | pontos_2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perfil_01_refino_157_93 | 157 | 92.99 | 6086.00 | -234.00 | 5.73 | 146 | 69.86 | 3.00 | 178 | 88.20 | 5471.50 | 46 | 91.30 | 1653.00 |
| perfil_02_equilibrado_139_94 | 139 | 94.24 | 5679.50 | -183.50 | 7.07 | 127 | 71.65 | 383.50 | 155 | 90.32 | 5315.00 | 45 | 91.11 | 1602.50 |
| perfil_03_frequente_191_89 | 191 | 89.01 | 6128.00 | -468.00 | 3.49 | 175 | 70.29 | 127.50 | 216 | 85.19 | 5548.00 | 62 | 87.10 | 1791.00 |

## Melhores combinacoes com 365d >= 88% e anos positivos

| cenario | trades_365d | winrate_365d | pontos_365d | dd_365d | pf_365d | trades_2024 | winrate_2024 | pontos_2024 | trades_2025 | winrate_2025 | pontos_2025 | trades_2026 | winrate_2026 | pontos_2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| perfil_02_equilibrado_139_94 | 139 | 94.24 | 5679.50 | -183.50 | 7.07 | 127 | 71.65 | 383.50 | 155 | 90.32 | 5315.00 | 45 | 91.11 | 1602.50 |
| perfil_01_refino_157_93 | 157 | 92.99 | 6086.00 | -234.00 | 5.73 | 146 | 69.86 | 3.00 | 178 | 88.20 | 5471.50 | 46 | 91.30 | 1653.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2058_BUY | 142 | 94.37 | 5831.00 | -183.50 | 7.23 | 140 | 70.00 | 35.00 | 158 | 90.51 | 5466.50 | 45 | 91.11 | 1602.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 140 | 94.29 | 5730.00 | -183.50 | 7.12 | 133 | 70.68 | 184.00 | 160 | 90.62 | 5567.50 | 41 | 90.24 | 1400.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_1030_SELL__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 140 | 94.29 | 5730.00 | -183.50 | 7.12 | 133 | 69.92 | 16.50 | 160 | 90.62 | 5567.50 | 45 | 91.11 | 1602.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_2052_BUY__REG_2052_SELL_A__REG_2058_BUY | 133 | 93.98 | 5376.50 | -183.50 | 6.74 | 125 | 72.00 | 450.00 | 145 | 89.66 | 4810.00 | 44 | 90.91 | 1552.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__DMI3_1030_SELL__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2058_BUY | 151 | 92.72 | 5783.00 | -234.00 | 5.49 | 144 | 70.14 | 69.50 | 168 | 87.50 | 4966.50 | 45 | 91.11 | 1602.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 131 | 93.89 | 5275.50 | -183.50 | 6.64 | 118 | 72.88 | 599.00 | 147 | 89.80 | 4911.00 | 40 | 90.00 | 1350.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2058_BUY | 134 | 94.03 | 5427.00 | -183.50 | 6.80 | 131 | 70.99 | 250.50 | 150 | 90.00 | 5062.50 | 40 | 90.00 | 1350.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__DMI3_1030_SELL__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 149 | 92.62 | 5682.00 | -234.00 | 5.41 | 137 | 70.07 | 51.00 | 170 | 87.65 | 5067.50 | 45 | 91.11 | 1602.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_1030_SELL__REG_2052_SELL_A__REG_2058_BUY | 134 | 94.03 | 5427.00 | -183.50 | 6.80 | 131 | 70.23 | 83.00 | 150 | 90.00 | 5062.50 | 44 | 90.91 | 1552.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 132 | 93.94 | 5326.00 | -183.50 | 6.69 | 124 | 70.97 | 232.00 | 152 | 90.13 | 5163.50 | 40 | 90.00 | 1350.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 131 | 93.89 | 5275.50 | -183.50 | 6.64 | 116 | 71.55 | 330.50 | 147 | 89.80 | 4911.00 | 44 | 90.91 | 1552.00 |
| combo_DMI3_0348_BUY__DMI3_1030_SELL__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 142 | 92.96 | 5496.00 | -234.00 | 5.70 | 140 | 70.00 | 35.00 | 163 | 87.73 | 4881.50 | 44 | 93.18 | 1719.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0346_SELL__REG_1030_BUY__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 133 | 93.98 | 5376.50 | -183.50 | 6.74 | 118 | 70.34 | 96.50 | 145 | 89.66 | 4810.00 | 45 | 91.11 | 1602.50 |
| perfil_03_frequente_191_89 | 191 | 89.01 | 6128.00 | -468.00 | 3.49 | 175 | 70.29 | 127.50 | 216 | 85.19 | 5548.00 | 62 | 87.10 | 1791.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__DMI3_2058_BUY__REG_0346_SELL__REG_0348_BUY__REG_1030_BUY__REG_1030_SELL__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 174 | 89.66 | 5772.00 | -351.00 | 3.74 | 162 | 70.99 | 308.50 | 198 | 86.87 | 5644.00 | 57 | 85.96 | 1538.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__REG_0348_BUY__REG_1030_BUY__REG_2052_BUY__REG_2052_SELL_A__REG_2052_SELL_B__REG_2058_BUY | 131 | 93.89 | 5275.50 | -183.50 | 6.64 | 113 | 69.91 | 11.50 | 146 | 89.73 | 4860.50 | 39 | 89.74 | 1299.50 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__DMI3_1030_SELL__REG_0346_SELL__REG_0348_BUY__REG_2052_BUY__REG_2052_SELL_A__REG_2058_BUY | 145 | 92.41 | 5480.00 | -234.00 | 5.26 | 133 | 69.92 | 16.50 | 158 | 86.71 | 4461.50 | 44 | 90.91 | 1552.00 |
| combo_DMI3_0348_BUY__DMI3_1030_BUY__DMI3_1030_SELL__REG_0346_SELL__REG_0348_BUY__REG_1030_SELL__REG_2052_SELL_A__REG_2058_BUY | 143 | 92.31 | 5379.00 | -234.00 | 5.18 | 135 | 70.37 | 117.50 | 160 | 86.88 | 4562.50 | 44 | 90.91 | 1552.00 |

## Busca por 220-260 trades e 365d >= 80%

Nenhum cenario encontrado.

## Busca por 220-260 trades e 365d >= 85%

Nenhum cenario encontrado.

## Leitura

- Se a tabela de 220-260 trades e 85% ficar vazia, os modulos atuais nao sustentam a meta de frequencia com acerto alto.
- Nesse caso, a proxima linha deve procurar novos horarios/indicadores, nao apenas apertar os filtros atuais.
- O candidato de maior confianca continua dependendo da confirmacao no TradingView, porque a equivalencia Python/TV ainda e a parte critica.
