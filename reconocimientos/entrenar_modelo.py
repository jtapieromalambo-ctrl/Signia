# Librerías para manejo de rutas y sistema operativo
import sys
import os

# Agregar la raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Librería para manejo de arrays
import numpy as np

# Clasificador y herramientas de scikit-learn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

# Para guardar el modelo entrenado
import pickle

def entrenar():
    """
    Carga los datos extraídos, entrena un clasificador
    RandomForest y guarda el modelo en un archivo .pkl
    """

    # Rutas de los archivos de datos
    X_path = 'reconocimientos/datos/X.npy'
    y_path = 'reconocimientos/datos/y.npy'

    # Verificar que los archivos existen
    if not os.path.exists(X_path) or not os.path.exists(y_path):
        print("No se encontraron datos. Ejecuta primero extraer_landmarks.py")
        return

    # Cargar los datos de entrenamiento
    X = np.load(X_path, allow_pickle=True)
    y = np.load(y_path, allow_pickle=True)

    print(f"Datos cargados: {X.shape[0]} muestras, {X.shape[1]} características")
    print(f"Señas encontradas: {list(set(y))}")

    # Convertir etiquetas de texto a números (hola=0, gracias=1, etc.)
    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)

    # Dividir datos en entrenamiento (80%) y prueba (20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42
    )

    print(f"\nEntrenando modelo con {len(X_train)} muestras...")

    # Crear y entrenar el clasificador RandomForest
    # n_estimators=100: usa 100 árboles de decisión
    modelo = RandomForestClassifier(n_estimators=100, random_state=42)
    modelo.fit(X_train, y_train)

    # Evaluar el modelo con los datos de prueba
    y_pred = modelo.predict(X_test)
    print("\nResultados del modelo:")
    print(classification_report(y_test, y_pred, target_names=encoder.classes_))

    # Guardar el modelo y el encoder en archivos .pkl
    os.makedirs('reconocimientos/modelo', exist_ok=True)

    # model.pkl → el clasificador entrenado
    with open('reconocimientos/modelo/model.pkl', 'wb') as f:
        pickle.dump(modelo, f)

    # encoder.pkl → para convertir números de vuelta a nombres de señas
    with open('reconocimientos/modelo/encoder.pkl', 'wb') as f:
        pickle.dump(encoder, f)

    print("\nModelo guardado en reconocimientos/modelo/model.pkl")
    print("Encoder guardado en reconocimientos/modelo/encoder.pkl")

# Punto de entrada del script
if __name__ == '__main__':
    entrenar()