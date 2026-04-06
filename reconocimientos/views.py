import os
import pickle
import threading
import base64
import json
import numpy as np

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import cv2
import mediapipe as mp
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
from mediapipe.tasks.python import BaseOptions

from reconocimientos.models import VideoSeña
from traduccion.models import video as VideoTraductor

# ── Rutas ─────────────────────────────────────────────────────────────
MODELO_PATH     = 'reconocimientos/modelo/model_seq.pkl'
ENCODER_PATH    = 'reconocimientos/modelo/encoder_seq.pkl'
LANDMARKER_PATH = 'reconocimientos/datos/hand_landmarker.task'

FRAMES_OBJETIVO = 30

# ── Cargar modelo y encoder ───────────────────────────────────────────
with open(MODELO_PATH, 'rb') as f:
    modelo = pickle.load(f)

with open(ENCODER_PATH, 'rb') as f:
    encoder = pickle.load(f)

# ── Configurar detector MediaPipe ─────────────────────────────────────
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=LANDMARKER_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.3,
    min_tracking_confidence=0.3
)
detector = HandLandmarker.create_from_options(options)


# ══════════════════════════════════════════════════════════════════════
#  RECONOCIMIENTO — vistas originales
# ══════════════════════════════════════════════════════════════════════

def normalizar_secuencia(secuencia, n_frames=FRAMES_OBJETIVO):
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
    posiciones = secuencia_norm.flatten()
    deltas     = np.diff(secuencia_norm, axis=0)
    magnitud   = np.linalg.norm(deltas, axis=1)
    return np.concatenate([posiciones, deltas.flatten(), magnitud])


def camara(request):
    return render(request, 'usuarios/reconocimiento.html')


@csrf_exempt
def predecir(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        body       = json.loads(request.body)
        frames_b64 = body.get('frames', [])

        if not frames_b64:
            return JsonResponse({'seña': '', 'confianza': 0})

        secuencia = []
        for frame_data in frames_b64:
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]

            img_bytes = base64.b64decode(frame_data)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame     = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            resultado = detector.detect(mp_image)

            if resultado.hand_landmarks:
                puntos = []
                for mano in resultado.hand_landmarks[:2]:
                    for punto in mano:
                        puntos.extend([punto.x, punto.y, punto.z])
                if len(resultado.hand_landmarks) == 1:
                    puntos.extend([0.0] * 63)
                secuencia.append(puntos)
        print(f'[RECONOCIMIENTO]) Frames con mano detectada: {len(secuencia)}/{len(frames_b64)} recibidos')


        if len(secuencia) < 5:

            print('[RECONOCIMIENTO] ❌ No hay sufuciente movimiento de manos (< 5 frames validos)')
            return JsonResponse({'seña': '', 'confianza': 0})

        secuencia_norm = normalizar_secuencia(secuencia)
        if secuencia_norm is None:

            print('[RECONOCIMIENTO] ❌ No hay sufuciente movimiento de manos (< 5 frames validos)')
            return JsonResponse({'seña': '', 'confianza': 0})

        features       = construir_features(secuencia_norm)
        X              = np.array([features])
        prediccion     = modelo.predict(X)
        probabilidades = modelo.predict_proba(X)

        seña      = encoder.inverse_transform(prediccion)[0]
        confianza = round(float(np.max(probabilidades)) * 100, 1)

        #top 3 candidatos
        clases = encoder.classes_
        top3 = sorted(zip(clases, probabilidades[0]), key=lambda x: x[1], reverse=True)[:3]
        top3_str = '|' .join(f'{c}:{round(p*100,1)}%' for c, p in top3) 


        print(f'[RECONOCIMIENTO] ✅ Seña detectada: "{seña}" — confianza: {confianza}%')
        print(f'[RECONOCIMIENTO] 🔢 Top 3: {top3_str}')


        return JsonResponse({'seña': seña, 'confianza': confianza})

    except Exception as e:
        import traceback
        traceback.print_exc()  # esto imprime el error completo en la consola
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def detectar_mano(request):
    if request.method != 'POST':
        return JsonResponse({'hay_mano': False})

    try:
        data = request.POST.get('frame', '')
        if ',' in data:
            data = data.split(',')[1]

        img_bytes = base64.b64decode(data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame     = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            return JsonResponse({'hay_mano': False})

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        resultado = detector.detect(mp_image)

        return JsonResponse({'hay_mano': bool(resultado.hand_landmarks)})

    except Exception:
        return JsonResponse({'hay_mano': False})


# ══════════════════════════════════════════════════════════════════════
#  PANEL ADMIN — vista principal
# ══════════════════════════════════════════════════════════════════════

def admin_videos(request):
    context = {
        'videos_reconocimiento': VideoSeña.objects.all().order_by('-creado'),
        'videos_traductor':      VideoTraductor.objects.all().order_by('nombre'),
        'total_reconocimiento':  VideoSeña.objects.count(),
        'total_traductor':       VideoTraductor.objects.count(),
    }
    return render(request, 'usuarios/admin_video.html', context)


# ══════════════════════════════════════════════════════════════════════
#  PANEL ADMIN — reconocimiento (subir / eliminar)
# ══════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["POST"])
def reconocimiento_subir(request):
    label   = request.POST.get('label', '').strip()
    archivo = request.FILES.get('video')

    if not label or not archivo:
        return JsonResponse({'ok': False, 'error': 'Faltan datos'}, status=400)

    instancia = VideoSeña.objects.create(label=label, video=archivo)

    return JsonResponse({
        'ok': True,
        'video': {
            'id':     instancia.id,
            'label':  instancia.label,
            'creado': instancia.creado.strftime('%d/%m/%Y %H:%M'),
        }
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def reconocimiento_eliminar(request, video_id):
    try:
        instancia = VideoSeña.objects.get(pk=video_id)
        instancia.video.delete(save=False)
        instancia.delete()
        return JsonResponse({'ok': True})
    except VideoSeña.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrado'}, status=404)


# ══════════════════════════════════════════════════════════════════════
#  PANEL ADMIN — traductor (CRUD completo)
# ══════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["POST"])
def traductor_crear(request):
    nombre  = request.POST.get('nombre', '').strip()
    archivo = request.FILES.get('video')

    if not nombre or not archivo:
        return JsonResponse({'ok': False, 'error': 'Faltan datos'}, status=400)

    if VideoTraductor.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse({'ok': False, 'error': f'Ya existe una seña llamada "{nombre}"'}, status=400)

    instancia = VideoTraductor.objects.create(nombre=nombre, video=archivo)

    return JsonResponse({'ok': True, 'video': _serializar_traductor(instancia)})


@csrf_exempt
@require_http_methods(["PUT"])
def traductor_editar(request, video_id):
    try:
        instancia = VideoTraductor.objects.get(pk=video_id)
    except VideoTraductor.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrado'}, status=404)

    nombre  = request.POST.get('nombre', '').strip()
    archivo = request.FILES.get('video')

    if nombre:
        instancia.nombre = nombre
    if archivo:
        instancia.video.delete(save=False)
        instancia.video = archivo

    instancia.save()
    return JsonResponse({'ok': True, 'video': _serializar_traductor(instancia)})


@csrf_exempt
@require_http_methods(["DELETE"])
def traductor_eliminar(request, video_id):
    try:
        instancia = VideoTraductor.objects.get(pk=video_id)
        instancia.video.delete(save=False)
        instancia.delete()
        return JsonResponse({'ok': True})
    except VideoTraductor.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrado'}, status=404)


# ── Helper ────────────────────────────────────────────────────────────

def _serializar_traductor(instancia):
    return {
        'id':        instancia.id,
        'nombre':    instancia.nombre,
        'video_url': instancia.video.url,
    }


# ══════════════════════════════════════════════════════════════════════
#  PANEL ADMIN — entrenamiento
# ══════════════════════════════════════════════════════════════════════

_entrenando = False


@csrf_exempt
@require_http_methods(["POST"])
def entrenar_modelo(request):
    global _entrenando
    if _entrenando:
        return JsonResponse({'ok': False, 'error': 'Ya hay un entrenamiento en curso'})

    def tarea():
        global _entrenando, modelo, encoder
        _entrenando = True
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import LabelEncoder

            videos = VideoSeña.objects.all()
            if not videos.exists():
                return

            X_data, y_data = [], []

            for v in videos:
                ruta = v.video.path
                cap  = cv2.VideoCapture(ruta)
                secuencia = []

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                    resultado = detector.detect(mp_image)

                    if resultado.hand_landmarks:
                        puntos = []
                        for mano in resultado.hand_landmarks[:2]:
                            for punto in mano:
                                puntos.extend([punto.x, punto.y, punto.z])
                        if len(resultado.hand_landmarks) == 1:
                            puntos.extend([0.0] * 63)
                        secuencia.append(puntos)

                cap.release()

                if len(secuencia) < 5:
                    continue

                secuencia_norm = normalizar_secuencia(secuencia)
                if secuencia_norm is None:
                    continue

                features = construir_features(secuencia_norm)
                X_data.append(features)
                y_data.append(v.label)

            if len(X_data) < 2:
                return

            X = np.array(X_data)
            y = np.array(y_data)

            nuevo_encoder = LabelEncoder()
            y_enc = nuevo_encoder.fit_transform(y)

            nuevo_modelo = RandomForestClassifier(n_estimators=100, random_state=42)
            nuevo_modelo.fit(X, y_enc)

            os.makedirs(os.path.dirname(MODELO_PATH), exist_ok=True)
            with open(MODELO_PATH, 'wb') as f:
                pickle.dump(nuevo_modelo, f)
            with open(ENCODER_PATH, 'wb') as f:
                pickle.dump(nuevo_encoder, f)

            # Recargar en memoria sin reiniciar el servidor
            modelo  = nuevo_modelo
            encoder = nuevo_encoder

        except Exception as e:
            print(f'[entrenar] Error: {e}')
        finally:
            _entrenando = False

    threading.Thread(target=tarea, daemon=True).start()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(["GET"])
def estado_entrenamiento(request):
    return JsonResponse({'activo': _entrenando})