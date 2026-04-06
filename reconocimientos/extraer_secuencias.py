import sys
import os
import urllib.request
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Signia.settings')

import cv2
import mediapipe as mp
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from mediapipe.tasks.python import BaseOptions
import django
django.setup()

from reconocimientos.models import VideoSeña

MODELO_PATH     = 'reconocimientos/datos/hand_landmarker.task'
FRAMES_OBJETIVO = 30


def descargar_modelo():
    os.makedirs('reconocimientos/datos', exist_ok=True)
    if not os.path.exists(MODELO_PATH):
        print("Descargando modelo MediaPipe...")
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
            MODELO_PATH
        )
        print("Modelo descargado.")


def extraer_secuencia_video(video_path):
    """
    Extrae landmarks frame por frame.
    Captura hasta 2 manos por frame (126 valores por frame).
    Si solo hay 1 mano, rellena la segunda con ceros.
    """
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODELO_PATH),
        running_mode=RunningMode.IMAGE,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_tracking_confidence=0.3
    )

    cap       = cv2.VideoCapture(video_path)
    secuencia = []

    with HandLandmarker.create_from_options(options) as detector:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            resultado = detector.detect(mp_image)

            if resultado.hand_landmarks:
                frame_data = []

                for punto in resultado.hand_landmarks[0]:
                    frame_data.extend([punto.x, punto.y, punto.z])

                if len(resultado.hand_landmarks) > 1:
                    for punto in resultado.hand_landmarks[1]:
                        frame_data.extend([punto.x, punto.y, punto.z])
                else:
                    frame_data.extend([0.0] * 63)

                secuencia.append(frame_data)

    cap.release()
    return secuencia


def normalizar_secuencia(secuencia, n_frames=FRAMES_OBJETIVO):
    """
    Normaliza una secuencia a exactamente n_frames usando interpolación.
    Devuelve un array de shape (n_frames, 126) — NO aplanado todavía.
    """
    secuencia     = np.array(secuencia)
    frames_reales = len(secuencia)

    if frames_reales == 0:
        return None

    if frames_reales == n_frames:
        return secuencia

    indices_origen  = np.linspace(0, frames_reales - 1, frames_reales)
    indices_destino = np.linspace(0, frames_reales - 1, n_frames)

    secuencia_norm = np.zeros((n_frames, secuencia.shape[1]))
    for i in range(secuencia.shape[1]):
        secuencia_norm[:, i] = np.interp(indices_destino, indices_origen, secuencia[:, i])

    return secuencia_norm


def construir_features(secuencia_norm):
    """
    Construye el vector final combinando posición + movimiento.

    - Posiciones absolutas (n_frames * 126)         → captura la forma de la mano
    - Deltas entre frames consecutivos ((n-1) * 126) → captura la velocidad del movimiento
    - Magnitud del movimiento por frame (n-1)        → captura cuánto se mueve la mano

    Gracias a los deltas y la magnitud, una mano quieta tendrá
    deltas ≈ 0 y magnitud ≈ 0, por lo que el modelo aprenderá
    a distinguirla de una seña con movimiento real.
    """
    posiciones = secuencia_norm.flatten()
    deltas     = np.diff(secuencia_norm, axis=0)        # (n_frames-1, 126)
    magnitud   = np.linalg.norm(deltas, axis=1)         # (n_frames-1,)

    return np.concatenate([posiciones, deltas.flatten(), magnitud])


def aumentar_secuencia(secuencia_array):
    """
    Genera variaciones artificiales para aumentar el dataset.
    """
    variaciones = [secuencia_array]

    # Variación 1: ruido gaussiano pequeño (temblor natural)
    ruido = secuencia_array + np.random.normal(0, 0.008, secuencia_array.shape)
    variaciones.append(ruido)

    # Variación 2: escala (distancia a la cámara)
    factor = np.random.uniform(0.93, 1.07)
    variaciones.append(secuencia_array * factor)

    # Variación 3: velocidad diferente
    n_alt    = np.random.randint(20, 45)
    idx_orig = np.linspace(0, len(secuencia_array) - 1, len(secuencia_array))
    idx_alt  = np.linspace(0, len(secuencia_array) - 1, n_alt)
    sec_alt  = np.zeros((n_alt, secuencia_array.shape[1]))
    for i in range(secuencia_array.shape[1]):
        sec_alt[:, i] = np.interp(idx_alt, idx_orig, secuencia_array[:, i])
    variaciones.append(sec_alt)

    return variaciones


def procesar_todos_los_videos():
    descargar_modelo()

    videos = list(VideoSeña.objects.all())
    total  = len(videos)

    if total == 0:
        print("No hay videos en la base de datos.")
        return

    print(f"Procesando {total} videos como secuencias...")

    datos     = []
    etiquetas = []

    for video in videos:
        print(f"  → {video.label}: {video.video.path}")
        secuencia = extraer_secuencia_video(video.video.path)

        if len(secuencia) < 5:
            print(f"     Muy pocos frames ({len(secuencia)}) — omitiendo")
            continue

        variaciones = aumentar_secuencia(np.array(secuencia))
        agregadas   = 0

        for variacion in variaciones:
            norm = normalizar_secuencia(variacion.tolist())
            if norm is not None:
                features = construir_features(norm)
                datos.append(features)
                etiquetas.append(video.label)
                agregadas += 1

        print(f"     {len(secuencia)} frames → {agregadas} variaciones generadas")

    if datos:
        os.makedirs('reconocimientos/datos', exist_ok=True)
        np.save('reconocimientos/datos/X_seq.npy', np.array(datos))
        np.save('reconocimientos/datos/y_seq.npy', np.array(etiquetas))
        n_features = np.array(datos).shape[1]
        print(f"\nDatos guardados: {len(datos)} secuencias de {len(set(etiquetas))} señas")
        print(f"Cada secuencia tiene {n_features} características (posición + movimiento)")
    else:
        print("No se pudieron extraer secuencias.")


if __name__ == '__main__':
    procesar_todos_los_videos()