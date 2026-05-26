import joblib
from pathlib import Path

BASE = Path(r"C:\Users\ualac\Documents\2025\Mercado\machine-pyton")

modelo = joblib.load(BASE / "OPERACIONAL_V5_1_CAMPEA" / "modelo_v5_1_campea.joblib")
features = joblib.load(BASE / "OPERACIONAL_V5_1_CAMPEA" / "features_v5_1_campea.joblib")

print("Tipo modelo:", type(modelo))
print("Tipo features:", type(features))
print("Qtd features:", len(features))

if isinstance(modelo, dict):
    print("Chaves modelo:", list(modelo.keys()))
    for k, v in modelo.items():
        print(k, type(v))
else:
    print("Modelo unico:", type(modelo))

print("Primeiras 30 features:")
print(features[:30])
