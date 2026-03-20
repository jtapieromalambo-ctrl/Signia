from django.shortcuts import render
from .models import video
import whisper
import os
import unicodedata
import uuid
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["PATH"] += os.pathsep + os.path.join(BASE_DIR, "ffmpeg")

# Carpeta temporal dedicada para guardar los audios antes de procesarlos
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)  # la crea automáticamente si no existe

# Carga el modelo de Whisper una sola vez al iniciar el servidor
# Modelos: tiny, base, small, medium, large (más grande = más preciso pero más lento)
model = whisper.load_model("base")

def pagina_base(request):
    return render(request, 'base.html')

def limpiar_texto(texto):
    # Convierte a minúsculas
    texto = texto.lower()
    # Quita tildes y caracteres especiales (á→a, é→e, etc.)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    # Quita puntuación y espacios extras
    texto = texto.strip().strip('.,!¿?¡')
    return texto

def buscar_video(request):
    resultados = []
    video_base = None

    # Siempre busca el video "base" para mostrarlo en bucle cuando no hay búsqueda
    try:
        video_base = video.objects.get(nombre__iexact='base')
    except video.DoesNotExist:
        video_base = None
    print("=============================")
    print("video_base:", video_base)
    print("=============================")
    if request.method == 'POST':
        palabras_texto = None

        # --- CASO 1: El usuario habló con el micrófono ---
        if 'audio' in request.FILES:
            audio = request.FILES['audio']

            # Nombre único por petición para evitar conflictos entre peticiones simultáneas
            nombre_archivo = f'temp_audio_{uuid.uuid4().hex}.webm'
            ruta = os.path.join(TEMP_DIR, nombre_archivo)  # guarda en carpeta temp/

            with open(ruta, 'wb') as f:
                f.write(audio.read())

            tamanio = os.path.getsize(ruta)
            print("✅ Tamaño:", tamanio, "bytes")

            if tamanio > 1000:
                try:
                    # Whisper convierte el audio a texto en español
                    resultado_whisper = model.transcribe(ruta, language='es')
                    palabras_texto = resultado_whisper["text"]
                    print("🎤 Whisper escuchó:", palabras_texto)
                except Exception as e:
                    print("❌ Error Whisper:", e)

            # Espera a que Whisper libere el archivo antes de eliminarlo
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
            # Toma solo la primera frase para evitar repeticiones de Whisper
            # Ej: "buenos dias. buenos dias" → "buenos dias"
            frase_limpia = frase_limpia.split('.')[0].strip()
            print("🎤 Texto limpio:", frase_limpia)

            palabras = frase_limpia.split()
            i = 0

            # Ventana deslizante: intenta combinaciones de mayor a menor longitud
            # Ejemplo con "buenos dias buenas tardes":
            # → intenta "buenos dias buenas tardes" → no existe
            # → intenta "buenos dias buenas"        → no existe
            # → intenta "buenos dias"               → ✅ encontrado, avanza 2
            # → intenta "buenas tardes"             → ✅ encontrado, avanza 2
            while i < len(palabras):
                encontrado = False

                # Intenta desde la frase más larga hasta 1 sola palabra
                for longitud in range(len(palabras) - i, 0, -1):
                    fragmento = ' '.join(p.strip('.,!¿?¡;:')for p in palabras[i:i+longitud])
                    print(f"🔍 Intentando: '{fragmento}'")
                    try:
                        v = video.objects.get(nombre__iexact=fragmento)
                        resultados.append(v)
                        print(f"✅ Encontrado: '{fragmento}'")
                        i += longitud  # avanza tantas palabras como tenga la frase encontrada
                        encontrado = True
                        break
                    except video.DoesNotExist:
                        continue

                if not encontrado:
                    # Ninguna combinación encontró video, salta esa palabra
                    print(f"❌ Sin video para: '{palabras[i]}'")
                    i += 1

    # Envía al template el video base, los resultados y las URLs para JavaScript
    return render(request, 'traduccion/traductor.html', {
        'resultados': resultados,
        'video_base': video_base,
        'urls_videos': [v.video.url for v in resultados],
    })