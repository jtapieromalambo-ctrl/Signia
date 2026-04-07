import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
import pickle


def entrenar():
    X_path = 'reconocimientos/datos/X_seq.npy'
    y_path = 'reconocimientos/datos/y_seq.npy'

    if not os.path.exists(X_path) or not os.path.exists(y_path):
        print("No se encontraron datos. Ejecuta primero extraer_secuencias.py")
        return

    X = np.load(X_path, allow_pickle=True)
    y = np.load(y_path, allow_pickle=True)

    print(f"Datos cargados: {X.shape[0]} secuencias, {X.shape[1]} características")
    print(f"Señas: {list(set(y))}")

    encoder   = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    # Más estimadores y sin límite de profundidad para aprovechar
    # los nuevos features de movimiento
    modelo = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    if len(X) >= 6:
        cv_folds = min(5, len(X) // len(set(y)))
        cv_folds = max(cv_folds, 2)
        scores   = cross_val_score(modelo, X, y_encoded, cv=cv_folds)
        print(f"\nPrecisión con validación cruzada ({cv_folds} folds): "
              f"{scores.mean()*100:.1f}% ± {scores.std()*100:.1f}%")

    print("\nEntrenando modelo final con todas las secuencias...")
    modelo.fit(X, y_encoded)

    os.makedirs('reconocimientos/modelo', exist_ok=True)

    with open('reconocimientos/modelo/model_seq.pkl', 'wb') as f:
        pickle.dump(modelo, f)

    with open('reconocimientos/modelo/encoder_seq.pkl', 'wb') as f:
        pickle.dump(encoder, f)

    print("Modelo guardado en reconocimientos/modelo/model_seq.pkl")
    print("Encoder guardado en reconocimientos/modelo/encoder_seq.pkl")


if __name__ == '__main__':
    entrenar()