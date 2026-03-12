from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
import cv2
import mediapipe as mp
import numpy as np

# ── MediaPipe setup ──────────────────────────────────────
mp_hands    = mp.solutions.hands
mp_drawing  = mp.solutions.drawing_utils
hands       = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# ── Diccionario básico de señas (puedes expandirlo) ──────
# Mapea cantidad de dedos extendidos a una palabra
SEÑAS = {
    0: "Puño cerrado",
    1: "Uno / Sí",
    2: "Dos / Paz",
    3: "Tres",
    4: "Cuatro",
    5: "Mano abierta / Hola",
}

def contar_dedos(hand_landmarks):
    """Cuenta cuántos dedos están extendidos."""
    dedos = []
    tips = [
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP,
    ]
    pip = [
        mp_hands.HandLandmark.THUMB_IP,
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP,
    ]
    for tip, p in zip(tips, pip):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[p].y:
            dedos.append(1)
        else:
            dedos.append(0)
    return sum(dedos)


def generar_frames():
    """Generador de frames para el streaming de video."""
    cap = cv2.VideoCapture(0)

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        texto = "Sin señas detectadas"

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(37, 99, 235), thickness=2, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(96, 165, 250), thickness=2),
                )
                dedos = contar_dedos(hand_landmarks)
                texto = SEÑAS.get(dedos, "Seña no reconocida")

        # Caja de texto con resultado
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), (30, 30, 30), -1)
        cv2.putText(
            frame, texto,
            (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
            (255, 255, 255), 2, cv2.LINE_AA
        )

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


# ── Vistas ───────────────────────────────────────────────

@login_required
def reconocimiento(request):
    """Vista principal del módulo de reconocimiento."""
    return render(request, 'reconocimientos/reconocimiento.html')


def video_feed(request):
    """Endpoint que sirve el stream de video con detección."""
    return StreamingHttpResponse(
        generar_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )