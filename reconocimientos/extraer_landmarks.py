# Librerías para manejo de rutas y sistema operativo
import sys
import os
import urllib.request

# Agregar la raíz del proyecto al path para que Python encuentre los módulos de Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Indicarle a Django cuál es el archivo de configuración del proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Signia.settings')

# Librería para procesar video frame por frame
import cv2

# Librería de Google para detectar manos y extraer landmarks (nueva API 0.10.x)
import mediapipe as mp
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from mediapipe.tasks.python import BaseOptions

# Librería para manejo de arrays y guardado de datos
import numpy as np

# Inicializar Django para poder usar los modelos de la base de datos
import django
django.setup()

# Importar el modelo VideoSeña para leer los videos subidos en el admin
from reconocimientos.models import VideoSeña

# Ruta donde se guardará el modelo de MediaPipe descargado
MODELO_PATH = 'reconocimientos/datos/hand_landmarker.task'

def descargar_modelo():
    """
    Descarga el modelo de detección de manos de MediaPipe
    si aún no existe en la carpeta de datos.
    """
    # Crear la carpeta de datos si no existe
    os.makedirs('reconocimientos/datos', exist_ok=True)

    # Solo descargar si el modelo no existe
    if not os.path.exists(MODELO_PATH):
        print("Descargando modelo de MediaPipe (~25MB), espere...")
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
            MODELO_PATH
        )
        print("Modelo descargado correctamente.")


def extraer_landmarks_video(video_path):
    """
    Lee un video frame por frame y extrae las coordenadas
    de los 21 puntos clave (landmarks) de cada mano detectada.
    Retorna una lista con los datos de cada frame.
    """

    # Configurar el detector con la nueva API de MediaPipe 0.10.x
    options = HandLandmarkerOptions(
        # Ruta al modelo descargado
        base_options=BaseOptions(model_asset_path=MODELO_PATH),
        # Modo imagen: procesa cada frame de forma independiente
        running_mode=RunningMode.IMAGE,
        # Detectar hasta 2 manos simultáneamente
        num_hands=2,
        # Confianza mínima del 50% para detectar una mano
        min_hand_detection_confidence=0.5,
        # Confianza mínima del 50% para rastrear una mano entre frames
        min_tracking_confidence=0.5
    )

    # Abrir el video desde la ruta dada
    cap = cv2.VideoCapture(video_path)

    # Lista donde se guardarán los landmarks de cada frame
    landmarks_video = []

    # Crear el detector dentro de un bloque with para manejo automático de recursos
    with HandLandmarker.create_from_options(options) as detector:

        # Leer el video frame por frame hasta que se acabe
        while cap.isOpened():
            ret, frame = cap.read()

            # Si no hay más frames, salir del bucle
            if not ret:
                break

            # Convertir el frame de BGR (formato OpenCV) a RGB (formato MediaPipe)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convertir el frame al formato de imagen que requiere MediaPipe
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            # Procesar el frame con MediaPipe para detectar manos
            resultado = detector.detect(mp_image)

            # Si se detectaron manos en este frame
            if resultado.hand_landmarks:
                for hand_landmarks in resultado.hand_landmarks:

                    # Lista para guardar los datos de esta mano en este frame
                    frame_data = []

                    # Cada mano tiene 21 puntos (landmarks), cada uno con X, Y, Z
                    for punto in hand_landmarks:
                        frame_data.extend([punto.x, punto.y, punto.z])
                        # Resultado: 21 puntos × 3 coordenadas = 63 valores por mano

                    # Agregar los datos de esta mano a la lista del video
                    landmarks_video.append(frame_data)

    # Liberar el video de la memoria
    cap.release()

    return landmarks_video


def procesar_todos_los_videos():
    """
    Procesa todos los videos sin procesar del admin,
    extrae sus landmarks y los guarda como archivos .npy
    para usarlos en el entrenamiento del modelo.
    """

    # Descargar el modelo de MediaPipe si no existe
    descargar_modelo()

    # Obtener solo los videos que aún no han sido procesados
    videos = VideoSeña.objects.filter(procesado=False)
    total = videos.count()

    # Si no hay videos pendientes, terminar
    if total == 0:
        print("No hay videos pendientes por procesar.")
        return

    print(f"Procesando {total} videos...")

    # Listas donde se acumularán todos los datos y etiquetas
    datos = []      # Coordenadas de landmarks de cada frame
    etiquetas = []  # Nombre de la seña correspondiente a cada frame

    for video in videos:
        print(f"  → {video.label}: {video.video.path}")

        # Extraer landmarks de todos los frames del video
        landmarks = extraer_landmarks_video(video.video.path)

        if landmarks:
            # Agregar cada frame como una muestra de entrenamiento
            for frame_landmarks in landmarks:
                datos.append(frame_landmarks)
                etiquetas.append(video.label)  # La etiqueta es el nombre de la seña

            # Marcar el video como procesado en la base de datos
            video.procesado = True
            video.save()
            print(f"     {len(landmarks)} frames extraidos")
        else:
            print(f"     No se detectaron manos en este video")

    if datos:
        # Crear la carpeta de datos si no existe
        os.makedirs('reconocimientos/datos', exist_ok=True)

        # Guardar los datos de entrenamiento como archivos numpy
        # X.npy → matriz de landmarks (cada fila es un frame)
        # y.npy → vector de etiquetas (nombre de la seña por frame)
        np.save('reconocimientos/datos/X.npy', np.array(datos))
        np.save('reconocimientos/datos/y.npy', np.array(etiquetas))

        print(f"\nDatos guardados: {len(datos)} muestras de {len(set(etiquetas))} señas")
    else:
        print("No se pudieron extraer landmarks de ningún video.")


# Punto de entrada del script
if __name__ == '__main__':
    procesar_todos_los_videos()