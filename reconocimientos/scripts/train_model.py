import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from reconocimientos.models import VideoSeña


def load_dataset(landmarks_dir):
    """
    Carga todos los .npy disponibles y sus etiquetas desde la BD.
    Retorna X (features) e y (labels).
    """
    X = []
    y = []

    videos = VideoSeña.objects.filter(procesado=True)

    for video in videos:
        npy_path = os.path.join(landmarks_dir, f"{video.id}.npy")

        if not os.path.exists(npy_path):
            print(f"[SKIP] No existe .npy para {video.id}")
            continue

        landmarks = np.load(npy_path)  # shape: (30, 42, 3)
        features = landmarks.flatten()  # shape: (3780,)
        X.append(features)
        y.append(video.label)

    return np.array(X), np.array(y)


def train_and_save(landmarks_dir, model_output_path):
    """
    Entrena un RandomForestClassifier y guarda el modelo como .pkl
    Retorna un dict con métricas del entrenamiento.
    """
    X, y = load_dataset(landmarks_dir)

    if len(X) == 0:
        raise ValueError("No hay datos para entrenar. Procesa los videos primero.")

    if len(set(y)) < 2:
        raise ValueError("Se necesitan al menos 2 clases distintas para entrenar.")

    # Split entrenamiento / validación
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Modelo
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # Métricas
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    clases = list(clf.classes_)

    # Guardar modelo
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    with open(model_output_path, 'wb') as f:
        pickle.dump(clf, f)

    print(f"[OK] Modelo guardado en {model_output_path}")
    print(f"     Accuracy: {accuracy:.2%} | Clases: {clases}")

    return {
        "accuracy": accuracy,
        "clases": clases,
        "total_muestras": len(X),
        "entrenamiento": len(X_train),
        "validacion": len(X_test),
        "model_path": model_output_path,
    }