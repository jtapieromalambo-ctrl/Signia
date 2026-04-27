from django.shortcuts import render
from .models import video
from faster_whisper import WhisperModel
from historial.models import EntradaHistorial
from lsc_grammar import convertir_a_lsc, tokens_para_busqueda   # ← NUEVA CAPA LSC
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
    """Limpieza básica: minúsculas, sin tildes, sin puntuación extrema."""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.strip().strip('.,!¿?¡')
    return texto


def _obtener_vocabulario_bd() -> list[str]:
    """
    Retorna todos los nombres de videos disponibles en la BD.
    Se usa para que la IA detecte faltantes con precisión.
    Se cachea en memoria por sesión del proceso (se recarga si la BD cambia).
    """
    try:
        return list(video.objects.values_list('nombre', flat=True))
    except Exception:
        return []


def _buscar_video_en_bd(fragmento: str):
    """
    Busca un video en la BD por nombre exacto (case-insensitive).
    Retorna el objeto video o None.
    """
    try:
        return video.objects.get(nombre__iexact=fragmento)
    except video.DoesNotExist:
        return None
    except Exception:
        return None


def _buscar_token_con_fallbacks(token: str, estrategia_faltantes: dict):
    """
    Intenta encontrar un video para un token LSC, aplicando estrategias de fallback:
      1. Búsqueda exacta del token
      2. Si tiene estrategia "synonym:ALTERNATIVA", busca la alternativa
      3. Si no existe, retorna (None, estrategia_aplicada)

    Returns:
        (video_obj | None, info_dict)
        info_dict: {"found": bool, "strategy": str, "original": str, "used": str}
    """
    token_upper = token.upper()
    # Expresiones multipalabra llegan con guion bajo (CON_GUSTO → "con gusto" en BD)
    token_para_bd = token_upper.replace("_", " ")
    info = {"found": False, "strategy": "none", "original": token_upper, "used": token_para_bd}

    # 1. Búsqueda directa (con espacios si era expresión multipalabra)
    v = _buscar_video_en_bd(token_para_bd)
    if v:
        info["found"] = True
        return v, info

    # 2. Aplicar estrategia definida por la IA
    estrategia = estrategia_faltantes.get(token_upper, "spell")

    if estrategia.startswith("synonym:"):
        alternativa = estrategia.split(":", 1)[1].strip()
        v = _buscar_video_en_bd(alternativa)
        if v:
            info.update({"found": True, "strategy": "synonym", "used": alternativa})
            return v, info

    # 3. No se encontró
    info["strategy"] = "spell" if estrategia == "spell" else "record"
    return None, info


def buscar_video(request):
    resultados = []
    tokens_lsc = []         # Secuencia de tokens LSC ordenados
    info_tokens = []        # Info detallada por token (encontrado, faltante, etc.)
    faltantes = []          # Palabras sin video en BD
    aviso_lsc = None        # Mensaje si la IA usó fallback
    lsc_metadata = {}       # Tipo de oración, expresión facial, etc.
    video_base = None

    try:
        video_base = video.objects.get(nombre__iexact='base')
    except video.DoesNotExist:
        video_base = None

    if request.method == 'POST':
        palabras_texto = None

        # ── CASO 1: Audio del micrófono ──────────────────────────────────────
        if 'audio' in request.FILES:
            audio_file = request.FILES['audio']
            nombre_archivo = f'temp_audio_{uuid.uuid4().hex}.webm'
            ruta = os.path.join(TEMP_DIR, nombre_archivo)

            with open(ruta, 'wb') as f:
                f.write(audio_file.read())

            tamanio = os.path.getsize(ruta)
            print("✅ Tamaño audio:", tamanio, "bytes")

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

        # ── CASO 2: Texto escrito ─────────────────────────────────────────────
        else:
            palabras_texto = request.POST.get('palabra')
            print("⌨️ Texto escrito:", palabras_texto)

        # ── PROCESAMIENTO CON CAPA GRAMATICAL LSC ────────────────────────────
        if palabras_texto and palabras_texto.strip():
            # Limpieza básica (solo para logging; la IA recibe el texto original)
            texto_para_ia = palabras_texto.strip().split('.')[0].strip()
            print("📝 Texto para IA LSC:", texto_para_ia)

            # Obtener vocabulario disponible en BD para detección de faltantes
            vocabulario_bd = _obtener_vocabulario_bd()

            # ── Llamada a la IA gramatical LSC ───────────────────────────────
            resultado_lsc = convertir_a_lsc(texto_para_ia, vocabulario_bd)

            # Guardar metadata (tipo de oración, expresión facial, etc.)
            lsc_metadata = {
                "sentence_type":    resultado_lsc.get("sentence_type", "declarative"),
                "facial_expression": resultado_lsc.get("facial_expression", "neutral"),
                "notes":            resultado_lsc.get("notes", ""),
            }

            # Aviso si la IA no estaba disponible (usó fallback)
            if resultado_lsc.get("error"):
                aviso_lsc = resultado_lsc["error"]
                print("⚠️ LSC fallback:", aviso_lsc)

            # ── Extraer tokens LSC para buscar en BD ─────────────────────────
            tokens_lsc = tokens_para_busqueda(resultado_lsc)
            estrategia_faltantes = resultado_lsc.get("estrategia_faltantes", {})

            print("🤟 Tokens LSC:", tokens_lsc)

            # ── Búsqueda de videos por token ──────────────────────────────────
            # La IA ya reordenó los tokens en el orden LSC correcto.
            # Aquí intentamos búsqueda multi-token (frases compuestas) + single token.
            i = 0
            while i < len(tokens_lsc):
                encontrado = False

                # Intento de frases compuestas (máx 3 tokens contiguos)
                for longitud in range(min(3, len(tokens_lsc) - i), 0, -1):
                    fragmento = ' '.join(tokens_lsc[i:i + longitud])
                    v, info = _buscar_token_con_fallbacks(fragmento, estrategia_faltantes)

                    if v:
                        resultados.append(v)
                        info_tokens.append({**info, "tokens_usados": tokens_lsc[i:i + longitud]})
                        print(f"✅ Video encontrado: '{fragmento}' → '{info['used']}'")
                        i += longitud
                        encontrado = True
                        break

                if not encontrado:
                    token_faltante = tokens_lsc[i]
                    faltantes.append(token_faltante)
                    info_tokens.append({
                        "found":         False,
                        "strategy":      estrategia_faltantes.get(token_faltante, "spell"),
                        "original":      token_faltante,
                        "used":          token_faltante,
                        "tokens_usados": [token_faltante],
                    })
                    print(f"❌ Sin video para token LSC: '{token_faltante}'")
                    i += 1

            # ── Guardar en historial ───────────────────────────────────────────
            if resultados and request.user.is_authenticated:
                EntradaHistorial.objects.create(
                    usuario=request.user,
                    tipo='traduccion',
                    contenido=palabras_texto.strip(),
                )

    return render(request, 'traduccion/traductor.html', {
        # ── Variables originales (compatibilidad con template existente) ──
        'resultados':   resultados,
        'video_base':   video_base,
        'urls_videos':  [v.video.url for v in resultados],

        # ── Nuevas variables LSC ──────────────────────────────────────────
        'tokens_lsc':       tokens_lsc,        # Lista de strings con el orden LSC
        'info_tokens':      info_tokens,        # Detalles por token (encontrado, estrategia)
        'faltantes':        faltantes,          # Tokens sin video en BD
        'lsc_metadata':     lsc_metadata,       # Tipo de oración, expresión facial
        'aviso_lsc':        aviso_lsc,          # Mensaje de aviso si IA usó fallback
    })