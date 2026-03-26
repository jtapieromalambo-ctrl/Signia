from django.shortcuts import render
from .models import video
from faster_whisper import WhisperModel
from historial.models import EntradaHistorial  # ← NUEVO
import os
import unicodedata
import uuid
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] += os.pathsep + os.path.join(BASE_DIR, "ffmpeg")

TEMP_DIR = os.path.join(BASE_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

model = WhisperModel("base", device="cpu", compute_type="int8")


def pagina_base(request):
    return render(request, 'base.html')


def limpiar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.strip().strip('.,!¿?¡')
    return texto


def buscar_video(request):
    resultados = []
    video_base = None

    try:
        video_base = video.objects.get(nombre__iexact='base')
    except video.DoesNotExist:
        video_base = None

    if request.method == 'POST':
        palabras_texto = None

        # --- CASO 1: El usuario habló con el micrófono ---
        if 'audio' in request.FILES:
            audio_file = request.FILES['audio']
            nombre_archivo = f'temp_audio_{uuid.uuid4().hex}.webm'
            ruta = os.path.join(TEMP_DIR, nombre_archivo)

            with open(ruta, 'wb') as f:
                f.write(audio_file.read())

            tamanio = os.path.getsize(ruta)
            print("✅ Tamaño:", tamanio, "bytes")

            if tamanio > 1000:
                try:
                    segments, info = model.transcribe(ruta, language='es', beam_size=5)
                    palabras_texto = " ".join(segment.text for segment in segments)
                    print("🎤 Whisper escuchó:", palabras_texto)
                except Exception as e:
                    print("❌ Error Whisper:", e)

            time.sleep(0.5)
            try:
                if os.path.exists(ruta):
                    os.remove(ruta)
                    print("🗑️ Archivo eliminado")
            except Exception as e:
                print("⚠️ No se pudo eliminar:", e)

        # --- CASO 2: El usuario escribió en el campo de texto ---
        else:
            palabras_texto = request.POST.get('palabra')
            print("⌨️ Texto escrito:", palabras_texto)

        if palabras_texto:
            frase_limpia = limpiar_texto(palabras_texto)
            frase_limpia = frase_limpia.split('.')[0].strip()
            print("🎤 Texto limpio:", frase_limpia)

            palabras = frase_limpia.split()
            i = 0

            while i < len(palabras):
                encontrado = False

                for longitud in range(len(palabras) - i, 0, -1):
                    fragmento = ' '.join(p.strip('.,!¿?¡;:') for p in palabras[i:i+longitud])
                    print(f"🔍 Intentando: '{fragmento}'")
                    try:
                        v = video.objects.get(nombre__iexact=fragmento)
                        resultados.append(v)
                        print(f"✅ Encontrado: '{fragmento}'")
                        i += longitud
                        encontrado = True
                        break
                    except video.DoesNotExist:
                        continue

                if not encontrado:
                    print(f"❌ Sin video para: '{palabras[i]}'")
                    i += 1

            # ── GUARDAR EN HISTORIAL ───────────────────────────
            if resultados and request.user.is_authenticated:
                EntradaHistorial.objects.create(
                    usuario=request.user,
                    tipo='traduccion',
                    contenido=palabras_texto.strip(),
                )
            # ──────────────────────────────────────────────────

    return render(request, 'traduccion/traductor.html', {
        'resultados': resultados,
        'video_base': video_base,
        'urls_videos': [v.video.url for v in resultados],
    })