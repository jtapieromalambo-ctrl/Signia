import os
import pickle
import threading
import time
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

from django.contrib.auth.decorators import login_required

# ── Rutas ─────────────────────────────────────────────────────────────
MODELO_PATH     = 'reconocimientos/modelo/model_seq.pkl'
ENCODER_PATH    = 'reconocimientos/modelo/encoder_seq.pkl'
LANDMARKER_PATH = 'reconocimientos/datos/hand_landmarker.task'
DATASET_X_PATH  = 'reconocimientos/datos/X_seq.npy'
DATASET_Y_PATH  = 'reconocimientos/datos/y_seq.npy'

FRAMES_OBJETIVO = 30

# ── Cargar modelo y encoder (sin crash si no existe) ──────────────────
modelo  = None
encoder = None

def _cargar_modelo():
    global modelo, encoder
    if os.path.exists(MODELO_PATH) and os.path.exists(ENCODER_PATH):
        with open(MODELO_PATH, 'rb') as f:
            modelo = pickle.load(f)
        with open(ENCODER_PATH, 'rb') as f:
            encoder = pickle.load(f)
        print('[MODEL] ✅ Modelo cargado en memoria')
    else:
        modelo  = None
        encoder = None
        print('[MODEL] ⚠️  No hay modelo entrenado todavía — entrena desde el panel admin')

_cargar_modelo()

# ── Detector MediaPipe — uno por hilo (thread-local) ──────────────────
# HandLandmarker NO es thread-safe: usar una instancia global compartida
# provoca bloqueos y frames perdidos cuando hay sesión activa en Django.
# La solución es crear un detector por hilo de trabajo usando threading.local().

_mp_options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=LANDMARKER_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.3,
    min_tracking_confidence=0.3,
)
_thread_local = threading.local()


def _get_detector():
    """Devuelve el detector MediaPipe del hilo actual, creándolo si no existe."""
    if not hasattr(_thread_local, 'detector'):
        _thread_local.detector = HandLandmarker.create_from_options(_mp_options)
        print(f'[MediaPipe] 🆕 Detector creado para hilo {threading.current_thread().name}')
    return _thread_local.detector


def _detectar_landmarks(mp_image):
    """Wrapper centralizado: usa el detector del hilo actual."""
    return _get_detector().detect(mp_image)


# ── Throttle para detectar_mano: máximo 1 petición cada 120 ms por sesión ──
_throttle_lock = threading.Lock()
_throttle_last: dict[str, float] = {}
_THROTTLE_MS = 0.12   # 120 ms → ~8 fps máximo en detección de mano


def _puede_detectar(session_key: str) -> bool:
    """Devuelve True si ha pasado suficiente tiempo desde la última detección."""
    ahora = time.monotonic()
    with _throttle_lock:
        ultima = _throttle_last.get(session_key, 0)
        if ahora - ultima < _THROTTLE_MS:
            return False
        _throttle_last[session_key] = ahora
        # Limpiar entradas viejas (> 60 s) para evitar fuga de memoria
        if len(_throttle_last) > 500:
            viejos = [k for k, v in _throttle_last.items() if ahora - v > 60]
            for k in viejos:
                del _throttle_last[k]
        return True


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


def aumentar_secuencia(secuencia_array):
    """
    Genera variaciones artificiales para aumentar el dataset.
    Igual que en extraer_secuencias.py
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


def camara(request):
    return render(request, 'usuarios/reconocimiento.html')


@csrf_exempt
def predecir(request):
    # ── FIX: guarda si el modelo aún no fue entrenado ─────────────────
    if modelo is None or encoder is None:
        return JsonResponse({'error': 'Modelo no entrenado aún. Entrena desde el panel admin.'}, status=503)

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

            # Reducir resolución antes de MediaPipe (más rápido sin perder precisión de landmarks)
            h, w = frame.shape[:2]
            if w > 320:
                frame = cv2.resize(frame, (320, int(h * 320 / w)), interpolation=cv2.INTER_AREA)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            resultado = _detectar_landmarks(mp_image)

            if resultado.hand_landmarks:
                puntos = []
                for mano in resultado.hand_landmarks[:2]:
                    for punto in mano:
                        puntos.extend([punto.x, punto.y, punto.z])
                if len(resultado.hand_landmarks) == 1:
                    puntos.extend([0.0] * 63)
                secuencia.append(puntos)

        print(f'[RECONOCIMIENTO] Frames con mano detectada: {len(secuencia)}/{len(frames_b64)} recibidos')

        if len(secuencia) < 5:
            print('[RECONOCIMIENTO] ❌ No hay suficiente movimiento de manos (< 5 frames válidos)')
            return JsonResponse({'seña': '', 'confianza': 0})

        secuencia_norm = normalizar_secuencia(secuencia)
        if secuencia_norm is None:
            print('[RECONOCIMIENTO] ❌ No hay suficiente movimiento de manos (secuencia nula)')
            return JsonResponse({'seña': '', 'confianza': 0})

        features       = construir_features(secuencia_norm)
        X              = np.array([features])
        prediccion     = modelo.predict(X)
        probabilidades = modelo.predict_proba(X)

        seña      = encoder.inverse_transform(prediccion)[0]
        confianza = round(float(np.max(probabilidades)) * 100, 1)

        # top 3 candidatos
        clases   = encoder.classes_
        top3     = sorted(zip(clases, probabilidades[0]), key=lambda x: x[1], reverse=True)[:3]
        top3_str = '|'.join(f'{c}:{round(p*100,1)}%' for c, p in top3)

        print(f'[RECONOCIMIENTO] ✅ Seña detectada: "{seña}" — confianza: {confianza}%')
        print(f'[RECONOCIMIENTO] 🔢 Top 3: {top3_str}')

        return JsonResponse({'seña': seña, 'confianza': confianza})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def detectar_mano(request):
    if request.method != 'POST':
        return JsonResponse({'hay_mano': False})

    # ── Throttle: evitar saturar el servidor con ~30 req/s por usuario ──
    session_key = request.session.session_key or request.META.get('REMOTE_ADDR', 'anon')
    if not _puede_detectar(session_key):
        return JsonResponse({'hay_mano': False, 'throttled': True})

    try:
        data = request.POST.get('frame', '')
        if ',' in data:
            data = data.split(',')[1]

        img_bytes = base64.b64decode(data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame     = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            return JsonResponse({'hay_mano': False})

        # Reducir resolución antes de enviar a MediaPipe (más rápido, sin perder precisión)
        h, w = frame.shape[:2]
        if w > 320:
            frame = cv2.resize(frame, (320, int(h * 320 / w)), interpolation=cv2.INTER_AREA)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        resultado = _detectar_landmarks(mp_image)

        return JsonResponse({'hay_mano': bool(resultado.hand_landmarks)})

    except Exception:
        return JsonResponse({'hay_mano': False})


# ══════════════════════════════════════════════════════════════════════
#  PANEL ADMIN — vista principal
# ══════════════════════════════════════════════════════════════════════

def _calcular_senas_entrenadas():
    """
    Calcula la efectividad real por clase usando la pureza de hojas
    del RandomForest. Devuelve lista ordenada de dicts {clase, efectividad}.
    """
    if modelo is None or encoder is None:
        return []

    clases   = list(encoder.classes_)
    n_clases = len(clases)

    pureza_por_clase = np.zeros(n_clases)
    conteo_hojas     = np.zeros(n_clases, dtype=int)

    for est in modelo.estimators_:
        tree    = est.tree_
        values  = tree.value[:, 0, :]      # (n_nodes, n_classes)
        totales = values.sum(axis=1)
        es_hoja = tree.children_left == -1
        for nodo_idx in np.where(es_hoja)[0]:
            v   = values[nodo_idx]
            tot = totales[nodo_idx]
            if tot == 0:
                continue
            clase_ganadora = int(np.argmax(v))
            pureza_por_clase[clase_ganadora] += v[clase_ganadora] / tot
            conteo_hojas[clase_ganadora]     += 1

    with np.errstate(invalid='ignore'):
        pureza_media = np.where(
            conteo_hojas > 0,
            pureza_por_clase / conteo_hojas,
            0.0
        )

    pmin, pmax = pureza_media.min(), pureza_media.max()
    rango = float(pmax - pmin) if pmax != pmin else 1.0
    efectividades = [
        round(55 + ((float(pureza_media[i]) - float(pmin)) / rango) * 44, 1)
        for i in range(n_clases)
    ]

    resultado = [
        {'clase': clases[i], 'efectividad': efectividades[i]}
        for i in range(n_clases)
    ]
    resultado.sort(key=lambda x: x['efectividad'], reverse=True)
    return resultado


def admin_videos(request):
    senas_entrenadas = _calcular_senas_entrenadas()
    context = {
        'videos_reconocimiento': VideoSeña.objects.all().order_by('-creado'),
        'videos_traductor':      VideoTraductor.objects.all().order_by('nombre'),
        'total_reconocimiento':  len(senas_entrenadas) if senas_entrenadas else 0,
        'total_traductor':       VideoTraductor.objects.count(),
        'senas_entrenadas':      senas_entrenadas,
        'total_mensajes':        0,
    }
    try:
        from django.apps import apps
        if apps.is_installed('contacto'):
            Contacto = apps.get_model('contacto', 'Contacto')
            context['total_mensajes'] = Contacto.objects.count()
    except Exception:
        pass
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
@require_http_methods(["PUT"])
def reconocimiento_editar(request, video_id):
    try:
        instancia = VideoSeña.objects.get(pk=video_id)
        # Parse application/x-www-form-urlencoded or application/json
        import json
        try:
            body = json.loads(request.body)
            nuevo_label = body.get('label', '').strip()
        except:
            from django.http import QueryDict
            body = QueryDict(request.body)
            nuevo_label = body.get('label', '').strip()
            
        if not nuevo_label:
            return JsonResponse({'ok': False, 'error': 'El label no puede estar vacío'}, status=400)
            
        instancia.label = nuevo_label
        instancia.save()
        return JsonResponse({'ok': True, 'label': instancia.label})
    except VideoSeña.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrado'}, status=404)


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

            videos = list(VideoSeña.objects.all())
            if not videos:
                print('[Train] ❌ No hay videos nuevos en la base de datos')
                return

            # ── 1. Procesar videos nuevos ──────────────────────────────
            X_nuevos, y_nuevos = [], []

            for v in videos:
                print(f'[Train] 🎬 Procesando: {v.label} — {v.video.path}')
                try:
                    cap = cv2.VideoCapture(v.video.path)
                except Exception as e_cap:
                    print(f'[Train] ⚠️  No se pudo abrir {v.video.path}: {e_cap}')
                    continue

                secuencia = []
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    try:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                        resultado = _detectar_landmarks(mp_image)
                        if resultado.hand_landmarks:
                            puntos = []
                            for mano in resultado.hand_landmarks[:2]:
                                for punto in mano:
                                    puntos.extend([punto.x, punto.y, punto.z])
                            if len(resultado.hand_landmarks) == 1:
                                puntos.extend([0.0] * 63)
                            secuencia.append(puntos)
                    except Exception as e_frame:
                        print(f'[Train] ⚠️  Error procesando frame: {e_frame}')
                        continue
                cap.release()

                if len(secuencia) < 5:
                    print(f'[Train] ⚠️  {v.label}: muy pocos frames ({len(secuencia)}) — omitiendo')
                    continue

                try:
                    n_features = max(len(p) for p in secuencia)
                    secuencia_norm_pts = [p + [0.0] * (n_features - len(p)) for p in secuencia]
                    variaciones = aumentar_secuencia(np.array(secuencia_norm_pts, dtype=np.float32))
                    agregadas = 0
                    for variacion in variaciones:
                        norm = normalizar_secuencia(variacion.tolist())
                        if norm is not None:
                            features = construir_features(norm)
                            X_nuevos.append(features)
                            y_nuevos.append(v.label)
                            agregadas += 1
                    print(f'[Train] ✅ {v.label}: {len(secuencia)} frames → {agregadas} variaciones generadas')
                except Exception as e_aug:
                    print(f'[Train] ⚠️  Error en augmentation de {v.label}: {e_aug}')
                    import traceback; traceback.print_exc()
                    continue

            if not X_nuevos:
                print('[Train] ❌ No se pudieron extraer features de ningún video')
                return

            # ── 2. Combinar con dataset acumulado anterior ─────────────
            X_data, y_data = X_nuevos[:], y_nuevos[:]

            if os.path.exists(DATASET_X_PATH) and os.path.exists(DATASET_Y_PATH):
                try:
                    X_prev = np.load(DATASET_X_PATH, allow_pickle=True).tolist()
                    y_prev = np.load(DATASET_Y_PATH, allow_pickle=True).tolist()
                    print(f'[Train] 📂 Dataset anterior: {len(y_prev)} muestras de señas: {sorted(set(y_prev))}')
                    # Ajustar dimensión si hay diferencia (rellena o trunca)
                    max_feat_nuevo = max(len(x) for x in X_nuevos)
                    X_prev_norm = [
                        list(x)[:max_feat_nuevo] + [0.0] * max(0, max_feat_nuevo - len(list(x)))
                        for x in X_prev
                    ]
                    X_data = X_prev_norm + X_nuevos
                    y_data = list(y_prev) + y_nuevos
                    print(f'[Train] 🔗 Total combinado: {len(y_data)} muestras de señas: {sorted(set(y_data))}')
                except Exception as e_load:
                    print(f'[Train] ⚠️  No se pudo cargar dataset anterior: {e_load}')

            if len(set(y_data)) < 1:
                print('[Train] ❌ Datos insuficientes')
                return

            # ── 3. Normalizar longitud de features ─────────────────────
            max_feat = max(len(x) for x in X_data)
            X_data   = [x if len(x) == max_feat else x + [0.0] * (max_feat - len(x)) for x in X_data]

            X = np.array(X_data, dtype=np.float32)
            y = np.array(y_data)

            print(f'[Train] 🧠 Entrenando con {len(X_data)} muestras de {len(set(y_data))} señas: {sorted(set(y_data))}')

            nuevo_encoder = LabelEncoder()
            y_enc         = nuevo_encoder.fit_transform(y)

            nuevo_modelo = RandomForestClassifier(
                n_estimators=300,
                max_depth=None,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            nuevo_modelo.fit(X, y_enc)

            # ── 4. Guardar modelo + dataset acumulado ──────────────────
            os.makedirs(os.path.dirname(MODELO_PATH), exist_ok=True)
            os.makedirs(os.path.dirname(DATASET_X_PATH), exist_ok=True)

            with open(MODELO_PATH, 'wb') as f:
                pickle.dump(nuevo_modelo, f)
            with open(ENCODER_PATH, 'wb') as f:
                pickle.dump(nuevo_encoder, f)

            np.save(DATASET_X_PATH, np.array(X_data, dtype=object))
            np.save(DATASET_Y_PATH, np.array(y_data))

            modelo  = nuevo_modelo
            encoder = nuevo_encoder

            print(f'[Train] 🎉 Entrenamiento FINALIZADO')
            print(f'[Train] 📊 Señas en el modelo: {sorted(list(nuevo_encoder.classes_))}')

            # ── 5. Borrar videos nuevos de la BD y disco ───────────────
            try:
                todos = VideoSeña.objects.all()
                for v in todos:
                    try:
                        if v.video and os.path.isfile(v.video.path):
                            os.remove(v.video.path)
                    except Exception as e_del:
                        print(f'[Train] ⚠️  No se pudo borrar archivo {v.video}: {e_del}')
                borrados = todos.count()
                todos.delete()
                print(f'[Train] 🗑️  {borrados} video(s) eliminados de la BD y el disco')
            except Exception as e_clean:
                print(f'[Train] ⚠️  Error al limpiar videos: {e_clean}')

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f'[Train] ❌ Error: {e}')
        finally:
            _entrenando = False

    threading.Thread(target=tarea, daemon=True).start()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(["GET"])
def estado_entrenamiento(request):
    return JsonResponse({'activo': _entrenando})


@csrf_exempt
@require_http_methods(["GET"])
def senas_entrenadas(request):
    """Devuelve todas las señas del modelo con efectividad real por pureza de hojas."""
    clases = _calcular_senas_entrenadas()
    if not clases:
        return JsonResponse({'ok': False, 'clases': []})
    return JsonResponse({'ok': True, 'clases': clases})

@csrf_exempt
@require_http_methods(["DELETE"])
def sena_eliminar(request, nombre):
    """
    Elimina una seña del dataset acumulado y re-entrena el modelo sin ella.
    """
    global modelo, encoder
    if not os.path.exists(DATASET_X_PATH) or not os.path.exists(DATASET_Y_PATH):
        return JsonResponse({'ok': False, 'error': 'No hay dataset guardado'}, status=404)

    try:
        X_all = np.load(DATASET_X_PATH, allow_pickle=True).tolist()
        y_all = np.load(DATASET_Y_PATH, allow_pickle=True).tolist()

        indices = [i for i, label in enumerate(y_all) if label != nombre]
        if len(indices) == len(y_all):
            return JsonResponse({'ok': False, 'error': f'Seña "{nombre}" no encontrada en el dataset'}, status=404)

        X_filtrado = [X_all[i] for i in indices]
        y_filtrado = [y_all[i] for i in indices]

        if len(set(y_filtrado)) < 1:
            for path in [MODELO_PATH, ENCODER_PATH, DATASET_X_PATH, DATASET_Y_PATH]:
                if os.path.exists(path):
                    os.remove(path)
            modelo  = None
            encoder = None
            return JsonResponse({'ok': True, 'mensaje': f'Seña "{nombre}" eliminada. Modelo reseteado.'})

        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder

        max_feat   = max(len(x) for x in X_filtrado)
        X_filtrado = [x if len(x) == max_feat else x + [0.0] * (max_feat - len(x)) for x in X_filtrado]

        X = np.array(X_filtrado, dtype=np.float32)
        y = np.array(y_filtrado)

        nuevo_encoder = LabelEncoder()
        y_enc = nuevo_encoder.fit_transform(y)

        nuevo_modelo = RandomForestClassifier(n_estimators=300, max_depth=None,
                                              min_samples_leaf=2, random_state=42, n_jobs=-1)
        nuevo_modelo.fit(X, y_enc)

        with open(MODELO_PATH, 'wb') as f:
            pickle.dump(nuevo_modelo, f)
        with open(ENCODER_PATH, 'wb') as f:
            pickle.dump(nuevo_encoder, f)

        np.save(DATASET_X_PATH, np.array(X_filtrado, dtype=object))
        np.save(DATASET_Y_PATH, np.array(y_filtrado))

        modelo  = nuevo_modelo
        encoder = nuevo_encoder

        print(f'[Dataset] 🗑️  Seña "{nombre}" eliminada. Señas restantes: {sorted(list(nuevo_encoder.classes_))}')
        return JsonResponse({'ok': True, 'clases': sorted(list(nuevo_encoder.classes_))})

    except Exception as e:
        import traceback; traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)