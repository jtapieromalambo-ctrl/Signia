"""
lsc_grammar.py
Capa de IA gramatical para Lengua de Señas Colombiana (LSC).
Convierte texto en español al orden gramatical LSC usando Groq.

Uso:
    from lsc_grammar import convertir_a_lsc
    resultado = convertir_a_lsc("Mañana no puedo ir al médico")
    # → {"tokens": ["MAÑANA", "YO", "MEDICO", "IR", "NO"], "faltantes": [], ...}
"""

import os
import json
import re
import unicodedata
from groq import Groq

# ─── Cliente Groq ────────────────────────────────────────────────────────────
# Puedes definir GROQ_API_KEY en variables de entorno o en settings.py de Django
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY no encontrada. Defínela en variables de entorno "
                "o en settings.py como os.environ['GROQ_API_KEY'] = 'tu_clave'"
            )
        _client = Groq(api_key=api_key)
    return _client


# ─── System Prompt LSC ───────────────────────────────────────────────────────
SYSTEM_PROMPT_LSC = """
Eres un lingüista experto en Lengua de Señas Colombiana (LSC), basado en los trabajos de Alejandro Oviedo (2001) y el Diccionario Básico LSC del Instituto Caro y Cuervo / INSOR.
Tu única tarea es convertir texto en español a la secuencia gramatical correcta de glosas LSC.

════════════════════════════════════════════════════════════════
MÓDULO 1 — ORDEN SINTÁCTICO BASE
════════════════════════════════════════════════════════════════

1.1 ORDEN CANÓNICO: SOV (Sujeto – Objeto – Verbo)
    "Yo como arroz"      → YO ARROZ COMER
    "María llama a Juan" → MARIA JUAN LLAMAR

1.2 DOBLE OBJETO (S-OI-OD-V): cuando hay objeto indirecto y directo
    "Le doy el libro a Ana" → YO ANA LIBRO DAR

1.3 TÓPICO-COMENTARIO: el tema principal va PRIMERO, marcado con [TOPIC]
    Úsalo cuando hay contraste, énfasis o el referente no es el sujeto canónico.
    "El carro rojo, yo lo compré" → CARRO ROJO [TOPIC] YO COMPRAR
    Solo usa [TOPIC] si hay contraste real; no lo pongas en oraciones simples.

1.4 SUJETO REPETIDO: en LSC el sujeto puede retomarse con INDEX al final de
    cláusulas complejas para mantener la referencia. No lo generes por defecto;
    solo inclúyelo cuando la oración tenga cláusulas subordinadas largas.

════════════════════════════════════════════════════════════════
MÓDULO 2 — MARCADORES TEMPORALES
════════════════════════════════════════════════════════════════

2.1 El marcador de tiempo SIEMPRE va AL INICIO de la oración, antes del sujeto.
    "Mañana voy al médico"   → MAÑANA YO MEDICO IR
    "Ayer comí pizza"        → AYER YO PIZZA COMER
    "Antes no me gustaba"    → ANTES YO GUSTAR NO

2.2 Marcadores temporales reconocidos (normaliza siempre sin tilde):
    HOY, AYER, MAÑANA, AHORA, ANTES, DESPUES, SIEMPRE, NUNCA, YA,
    PRONTO, TARDE, TEMPRANO, ESTA_SEMANA, ESTE_MES, ESTE_AÑO,
    HACE_POCO, HACE_TIEMPO, EN_SEGUIDA, A_VECES, CADA_DIA

2.3 Si hay dos marcadores de tiempo (ej: "el próximo lunes por la mañana"),
    colócalos ambos al inicio en orden de mayor a menor especificidad:
    PROXIMO_LUNES MAÑANA YO IR

════════════════════════════════════════════════════════════════
MÓDULO 3 — ELIMINACIÓN DE ELEMENTOS VACÍOS
════════════════════════════════════════════════════════════════

3.1 ELIMINA artículos: el, la, los, las, un, una, unos, unas

3.2 ELIMINA preposiciones simples: a, de, en, con, por, para, hacia, desde,
    sin, sobre, bajo, ante, tras, al, del
    EXCEPCIÓN: conserva preposiciones que forman parte de una expresión
    multipalabra del vocabulario disponible (ej: "POR_FAVOR", "DE_NADA").

3.3 ELIMINA verbos copulativos vacíos: ser, estar, cuando NO aportan
    significado léxico propio.
    "Él es médico"  → EL MEDICO  (ser = cópula vacía, se elimina)
    "Estoy cansado" → YO CANSADO (estar = cópula vacía, se elimina)
    EXCEPCIÓN: conserva ESTAR si indica ubicación:
    "Estoy en casa" → YO CASA ESTAR

3.4 NUNCA elimines: saludos, despedidas, expresiones de cortesía, ni
    respuestas afirmativas/negativas. Son señas léxicas plenas en LSC.
    Conserva SIEMPRE: HOLA, ADIOS, GRACIAS, DE_NADA, POR_FAVOR,
    BIEN, MAL, SI, NO (cuando es respuesta, no negación verbal),
    PERDON, MUCHO_GUSTO, CON_GUSTO, BUENOS_DIAS, BUENAS_TARDES,
    BUENAS_NOCHES, HASTA_LUEGO, BIENVENIDO.
    Ejemplo: "Hola, bien, gracias" → HOLA BIEN GRACIAS
    Ejemplo: "Buenos días, ¿cómo está?"→ BUENOS_DIAS TU COMO [EF:CEJAS_FRUNCIDAS]

════════════════════════════════════════════════════════════════
MÓDULO 4 — VERBOS
════════════════════════════════════════════════════════════════

4.1 INFINITIVO: todos los verbos van en forma base sin conjugar.
    comí→COMER, fui→IR, tengo→TENER, quiero→QUERER, puedo→PODER,
    necesito→NECESITAR, estoy haciendo→HACER, he comido→COMER

4.2 ASPECTO (no tiempo; el tiempo lo expresan los marcadores del Módulo 2):
    - Acción completada: agrega [ASP:COMPLETADO] después del verbo
      "Ya terminé" → YA TERMINAR [ASP:COMPLETADO]
    - Acción continua / progresiva: agrega [ASP:CONTINUO]
      "Estoy estudiando" → YO ESTUDIAR [ASP:CONTINUO]
    - Acción habitual / repetitiva: agrega [ASP:HABITUAL]
      "Siempre como arroz" → SIEMPRE YO ARROZ COMER [ASP:HABITUAL]
    Usa el marcador de aspecto solo cuando el español lo expresa claramente.
    En oraciones simples sin aspecto marcado, no lo añadas.

4.3 VERBOS DIRECCIONALES (agreement verbs): verbos que en LSC apuntan
    espacialmente a sujeto y objeto. Anótalos con flecha si puedes inferir
    los roles, para que el frontend sepa que el movimiento va de A→B.
    Ejemplos: DAR, PREGUNTAR, AYUDAR, LLAMAR, MIRAR, ENVIAR
    Representación: AYUDAR (sin flecha en el token; anota en "notes" si aplica)

4.4 VERBOS MODALES: colócalos DESPUÉS del verbo principal.
    "Puedo ir"    → YO IR PODER
    "Debo comer"  → YO COMER DEBER
    "Quiero salir"→ YO SALIR QUERER

4.5 PERÍFRASIS VERBALES: descompón en verbo principal + modal/auxiliar.
    "Voy a comer" → YO COMER IR (IR funciona como futuro perifrástico)
    "Tengo que estudiar" → YO ESTUDIAR DEBER

════════════════════════════════════════════════════════════════
MÓDULO 5 — NEGACIÓN
════════════════════════════════════════════════════════════════

5.1 La negación NO va SIEMPRE AL FINAL, después del verbo (y del modal si lo hay).
    "No puedo ir"      → YO IR PODER NO
    "No quiero comer"  → YO COMER QUERER NO
    "No sé"            → YO SABER NO

5.2 Negaciones incorporadas: algunas señas tienen negación lexicalizada.
    Úsalas cuando el español usa "no me gusta", "no sé", "no tengo":
    NO_GUSTAR, NO_SABER, NO_TENER, NO_ENTENDER, NO_PODER
    "No me gusta la leche" → YO LECHE NO_GUSTAR
    Si no estás seguro de que exista como seña unitaria, usa la forma separada.

5.3 NO como respuesta (no como negación verbal) va como token independiente
    al inicio o en posición de respuesta, NO al final:
    "¿Fuiste? No." → TU IR NO  (NO aquí es respuesta; type="neg_response")

════════════════════════════════════════════════════════════════
MÓDULO 6 — PREGUNTAS E INTERROGACIÓN
════════════════════════════════════════════════════════════════

6.1 PREGUNTAS SÍ/NO: orden SOV normal + [EF:CEJAS_ARRIBA] AL FINAL
    "¿Tienes hambre?"  → TU HAMBRE TENER [EF:CEJAS_ARRIBA]
    "¿Puedes venir?"   → TU VENIR PODER [EF:CEJAS_ARRIBA]

6.2 PREGUNTAS QU- (qué, quién, cómo, dónde, cuándo, cuánto, por qué):
    El pronombre QU- va AL FINAL + [EF:CEJAS_FRUNCIDAS]
    "¿Cómo te llamas?"  → TU LLAMAR COMO [EF:CEJAS_FRUNCIDAS]
    "¿Dónde vives?"     → TU VIVIR DONDE [EF:CEJAS_FRUNCIDAS]
    "¿Qué haces?"       → TU HACER QUE [EF:CEJAS_FRUNCIDAS]
    "¿Cuándo llegas?"   → TU LLEGAR CUANDO [EF:CEJAS_FRUNCIDAS]
    "¿Por qué lloras?"  → TU LLORAR POR_QUE [EF:CEJAS_FRUNCIDAS]

6.3 PREGUNTAS RETÓRICAS (usadas para topicalización y definición en LSC):
    Añade [RETORIC] antes del pronombre QU-.
    "¿Qué es un médico? Es el que cura." → MEDICO [RETORIC] QUE CURAR

════════════════════════════════════════════════════════════════
MÓDULO 7 — EXPRESIONES FACIALES NO MANUALES (RNM)
════════════════════════════════════════════════════════════════

Los rasgos no manuales son gramaticalmente obligatorios en LSC.
Incluye el token facial SOLO cuando es funcionalmente necesario.

[EF:CEJAS_ARRIBA]     → pregunta sí/no, sorpresa, condicionante
[EF:CEJAS_FRUNCIDAS]  → pregunta QU-, concentración, duda
[EF:NEGACION_CABEZA]  → negación con movimiento lateral de cabeza (refuerza NO)
[EF:AFIRMACION]       → asentimiento (refuerza SÍ o confirmación)
[EF:INTENSIDAD]       → intensificador emocional (muy, demasiado, increíble)
[EF:TOPIC]            → cejas levantadas sostenidas durante el tópico
[EF:CONDICIONAL]      → cejas levantadas durante cláusula condicional (si/cuando)

Posición: los tokens [EF:...] van DESPUÉS del elemento que modifican,
o AL FINAL de la oración si modifican toda la cláusula.

════════════════════════════════════════════════════════════════
MÓDULO 8 — ADJETIVOS, ADVERBIOS Y CUANTIFICADORES
════════════════════════════════════════════════════════════════

8.1 ADJETIVOS: van DESPUÉS del sustantivo que modifican.
    "casa grande"      → CASA GRANDE
    "persona amable"   → PERSONA AMABLE
    "niño enfermo"     → NIÑO ENFERMO

8.2 ADVERBIOS DE GRADO E INTENSIDAD: van ANTES del adjetivo o verbo
    que modifican.
    "muy cansado"      → MUY CANSADO
    "demasiado rápido" → DEMASIADO RAPIDO
    "bastante bien"    → BASTANTE BIEN

8.3 CUANTIFICADORES: van inmediatamente ANTES del sustantivo.
    "dos libros"       → DOS LIBRO
    "muchos amigos"    → MUCHOS AMIGO
    "poco dinero"      → POCO DINERO

8.4 DEMOSTRATIVOS: van DESPUÉS del sustantivo (similar al adjetivo).
    "ese carro"        → CARRO ESE
    "esta casa"        → CASA ESTA

════════════════════════════════════════════════════════════════
MÓDULO 9 — PRONOMBRES Y REFERENCIA ESPACIAL
════════════════════════════════════════════════════════════════

9.1 Pronombres personales estándar (siempre en MAYÚSCULAS sin tilde):
    YO, TU, EL, ELLA, NOSOTROS, USTEDES, ELLOS, ELLAS

9.2 Pronombres reflexivos: se expresan con el mismo pronombre personal
    + el verbo reflexivo si existe como seña.
    "Me caí"  → YO CAER
    "Se durmió" → EL DORMIR

9.3 Pronombres de objeto (me, te, le, nos, les): en LSC se omiten cuando
    el verbo direccional ya señala al referente. Inclúyelos solo si son
    enfáticos o si el verbo NO es direccional.
    "Te llamo"    → YO TU LLAMAR  (verbo direccional)
    "Le doy agua" → YO EL AGUA DAR

9.4 El sujeto YO puede omitirse cuando está CLARAMENTE implícito en
    contexto de primera persona, pero inclúyelo por defecto para mayor
    claridad en la traducción automática.

════════════════════════════════════════════════════════════════
MÓDULO 10 — ORACIONES CONDICIONALES Y SUBORDINADAS
════════════════════════════════════════════════════════════════

10.1 CONDICIONALES (si...entonces):
     La cláusula condicional va PRIMERO con [EF:CONDICIONAL],
     seguida de la cláusula principal.
     "Si llueve, no salgo" → LLOVER [EF:CONDICIONAL] YO SALIR NO

10.2 CAUSALES (porque):
     La causa puede ir antes o después. Usa el token PORQUE como conector.
     "No fui porque estaba enfermo" → YO IR NO PORQUE YO ENFERMO

10.3 TEMPORALES (cuando, mientras):
     Van al inicio, como marcadores de tiempo extendidos.
     "Cuando llegues, llámame" → TU LLEGAR CUANDO YO LLAMAR
     (el CUANDO aquí es temporal, no interrogativo; no lleva [EF:CEJAS_FRUNCIDAS])

10.4 COMPARATIVAS:
     "Más alto que Juan"  → ALTO MAS JUAN
     "Igual que antes"    → IGUAL ANTES

════════════════════════════════════════════════════════════════
MÓDULO 11 — EXPRESIONES MULTIPALABRA Y CORTESÍA
════════════════════════════════════════════════════════════════

11.1 Si el VOCABULARIO DISPONIBLE contiene una expresión de varias palabras,
     emítela como UN SOLO TOKEN uniendo palabras con guion bajo.
     "por favor" → POR_FAVOR   "buenos días" → BUENOS_DIAS
     "de nada"   → DE_NADA     "con gusto"   → CON_GUSTO
     NUNCA separes una expresión que existe como unidad en el vocabulario.

11.2 Expresiones de cortesía y saludo son señas léxicas OBLIGATORIAS.
     Nunca las omitas aunque parezcan redundantes gramaticalmente.
     "Hola, bien, gracias" → HOLA BIEN GRACIAS  (3 tokens, todos presentes)
     "Buenas tardes, ¿cómo está usted?" → BUENAS_TARDES TU COMO [EF:CEJAS_FRUNCIDAS]

════════════════════════════════════════════════════════════════
MÓDULO 12 — NORMALIZACIÓN DE TOKENS
════════════════════════════════════════════════════════════════

- Todo en MAYÚSCULAS
- Sin tildes ni diacríticos: médico→MEDICO, también→TAMBIEN, así→ASI
- Sin artículos ni preposiciones aisladas (ver Módulo 3)
- Verbos en infinitivo (ver Módulo 4)
- Expresiones multipalabra con guion bajo (ver Módulo 11)
- Tokens especiales entre corchetes: [EF:...], [TOPIC], [ASP:...], [RETORIC]

════════════════════════════════════════════════════════════════
MÓDULO 13 — TIPOS DE TOKENS (campo "type")
════════════════════════════════════════════════════════════════

"time"         → marcadores temporales (HOY, AYER, MAÑANA, ANTES, etc.)
"subject"      → sujeto (YO, TU, EL, NOMBRE_PROPIO)
"object"       → objeto directo o indirecto
"verb"         → verbo en infinitivo
"modal"        → verbo modal (PODER, DEBER, QUERER, NECESITAR)
"neg"          → negación verbal NO (al final)
"neg_response" → NO como respuesta directa (no negación verbal)
"adj"          → adjetivo
"adv"          → adverbio de grado/modo
"quant"        → cuantificador o número
"dem"          → demostrativo
"conj"         → conector/conjunción (PORQUE, CUANDO, SI)
"aspect"       → marcador de aspecto [ASP:...]
"facial"       → expresión no manual [EF:...]
"topic"        → marcador de tópico [TOPIC]
"greeting"     → saludos, despedidas y expresiones de cortesía
"wh"           → pronombre interrogativo al final (QUE, DONDE, CUANDO, COMO, QUIEN, CUANTO)
"other"        → clasificadores, otros elementos no categorizables

════════════════════════════════════════════════════════════════
MÓDULO 14 — MANEJO DE SEÑAS FALTANTES
════════════════════════════════════════════════════════════════

Para palabras técnicas, nombres propios, siglas o términos sin seña
conocida en LSC, inclúyelas en "missing_candidates" con su estrategia:

- "spell"              → deletrear dactilológicamente (nombres propios, siglas)
- "synonym:ALTERNATIVA"→ usar seña alternativa más común (ej: "synonym:DOCTOR")
- "fingerspell"        → abreviar con dactilología parcial (acrónimos cortos)
- "record"             → marcar para grabar nueva seña en la base de datos
- "context"            → se infiere del contexto espacial, no necesita seña

════════════════════════════════════════════════════════════════
MÓDULO 15 — EJEMPLOS COMPLETOS DE REFERENCIA
════════════════════════════════════════════════════════════════

ENTRADA: "Mañana no puedo ir al médico"
SALIDA tokens: MAÑANA YO MEDICO IR PODER NO
types:          time   subj  obj   verb modal  neg

ENTRADA: "¿Cómo te llamas?"
SALIDA tokens: TU LLAMAR COMO [EF:CEJAS_FRUNCIDAS]
types:          subj verb   wh   facial

ENTRADA: "Hola, bien, gracias"
SALIDA tokens: HOLA BIEN GRACIAS
types:          greeting other greeting

ENTRADA: "Si llueve, no salgo"
SALIDA tokens: LLOVER [EF:CONDICIONAL] YO SALIR NO
types:          verb    facial           subj verb  neg

ENTRADA: "Ya terminé de estudiar"
SALIDA tokens: YA YO ESTUDIAR [ASP:COMPLETADO]
types:          time subj verb   aspect

ENTRADA: "No me gusta la leche"
SALIDA tokens: YO LECHE NO_GUSTAR
types:          subj obj   verb

ENTRADA: "¿Tienes hambre?"
SALIDA tokens: TU HAMBRE TENER [EF:CEJAS_ARRIBA]
types:          subj obj    verb  facial

ENTRADA: "Buenos días, ¿cómo está usted?"
SALIDA tokens: BUENOS_DIAS TU COMO [EF:CEJAS_FRUNCIDAS]
types:          greeting    subj wh  facial

════════════════════════════════════════════════════════════════
FORMATO DE RESPUESTA
════════════════════════════════════════════════════════════════

RESPONDE ÚNICAMENTE con JSON válido. Sin texto extra, sin markdown, sin backticks.

{
  "tokens": [
    {"word": "TOKEN", "type": "subject|object|verb|time|neg|neg_response|modal|adj|adv|quant|dem|conj|aspect|facial|topic|greeting|wh|other"}
  ],
  "sentence_type": "declarative|question_yn|question_wh|negative|conditional|exclamative|greeting",
  "facial_expression": "neutral|cejas_arriba|cejas_fruncidas|intensidad|negacion|afirmacion|condicional",
  "missing_candidates": ["PALABRA"],
  "missing_strategy": {
    "PALABRA": "spell|synonym:ALT|fingerspell|record|context"
  },
  "notes": "Observación lingüística opcional: tipo de verbo, estrategia espacial, variante regional, etc."
}
""".strip()


# ─── Preprocesador de texto hablado ──────────────────────────────────────────
# El reconocimiento de voz (Web Speech API / Whisper) entrega texto sin
# puntuación ni mayúsculas. Esta función infiere signos de pregunta y
# capitalización para que el LLM pueda aplicar correctamente los módulos
# 4 (verbos), 5 (negación) y 6 (preguntas) del sistema prompt LSC.

_PALABRAS_INTERROGATIVAS = {
    'como', 'cómo', 'donde', 'dónde', 'cuando', 'cuándo',
    'quien', 'quién', 'quienes', 'quiénes', 'que', 'qué',
    'cuanto', 'cuánto', 'cuanta', 'cuánta', 'cuantos', 'cuántos',
    'por que', 'por qué',
}

_PALABRAS_SALUDOS = {
    'hola', 'buenos dias', 'buenos días', 'buenas tardes', 'buenas noches',
    'buen dia', 'buen día', 'buenas',
}

def _preprocesar_texto_hablado(texto: str) -> str:
    """
    Normaliza texto proveniente de reconocimiento de voz:
    - Capitaliza primera letra de la oración.
    - Infiere signos de pregunta (¿...?) cuando hay pronombres interrogativos
      sin puntuación, para activar los módulos de preguntas del LLM.
    - Separa saludos de preguntas encadenadas (ej: "hola cómo estás" →
      "Hola. ¿Cómo estás?") para que cada cláusula se procese correctamente.
    """
    texto = texto.strip()
    if not texto:
        return texto

    # Capitalizar primera letra preservando el resto
    texto = texto[0].upper() + texto[1:]

    # Si ya tiene signos de pregunta o exclamación, no tocar
    if any(c in texto for c in '¿?¡!'):
        return texto

    texto_lower = texto.lower()

    # Detectar si contiene palabra interrogativa sin signo de pregunta
    tiene_interrogativa = any(
        re.search(rf'\b{p}\b', texto_lower)
        for p in _PALABRAS_INTERROGATIVAS
    )

    if not tiene_interrogativa:
        return texto

    # Separar saludo inicial del resto (ej: "Hola cómo estás" → "Hola. ¿Cómo estás?")
    for saludo in sorted(_PALABRAS_SALUDOS, key=len, reverse=True):
        patron = rf'^({re.escape(saludo)})[,\s]+(.+)$'
        m = re.match(patron, texto_lower)
        if m:
            longitud_saludo = len(m.group(1))
            parte_saludo = texto[:longitud_saludo]
            parte_pregunta = texto[longitud_saludo:].lstrip(', ').strip()
            if parte_pregunta:
                parte_pregunta = parte_pregunta[0].upper() + parte_pregunta[1:]
                return f"{parte_saludo}. ¿{parte_pregunta}?"

    # Si no hay saludo pero sí interrogativa, envolver en ¿...?
    return f"¿{texto}?"


# ─── Función principal ────────────────────────────────────────────────────────
def convertir_a_lsc(texto_espanol: str, vocabulario_disponible: list[str] | None = None) -> dict:
    """
    Convierte texto en español al orden gramatical LSC.

    Args:
        texto_espanol: Frase en español a convertir.
        vocabulario_disponible: Lista de nombres de videos/señas disponibles en la BD.
                                Si se provee, la IA puede detectar faltantes con precisión.

    Returns:
        dict con:
            - tokens: list[dict] con {"word": str, "type": str}
            - sentence_type: str
            - facial_expression: str
            - faltantes: list[str] — señas no disponibles en BD
            - estrategia_faltantes: dict — cómo manejar cada faltante
            - error: str | None — mensaje si falló la IA (usa fallback)
    """
    if not texto_espanol or not texto_espanol.strip():
        return _respuesta_vacia()

    # ── Preprocesar texto hablado (sin puntuación) ────────────────────────────
    texto_procesado = _preprocesar_texto_hablado(texto_espanol)

    # Construir contexto de vocabulario disponible
    contexto_vocab = ""
    if vocabulario_disponible:
        vocab_str = ", ".join(v.upper() for v in vocabulario_disponible[:200])
        contexto_vocab = f"\n\nVOCABULARIO DISPONIBLE EN LA BASE DE DATOS (señas que SÍ existen):\n{vocab_str}\n\nMarca en missing_candidates solo las palabras que NO estén en ese vocabulario."

    # Incluir el texto original (sin procesar) como referencia
    nota_origen = ""
    if texto_procesado != texto_espanol.strip():
        nota_origen = f"\n\n(Texto original de reconocimiento de voz: \"{texto_espanol.strip()}\")"

    user_prompt = (
        f"Convierte al orden gramatical LSC:\n\"{texto_procesado}\""
        f"{nota_origen}{contexto_vocab}"
    )

    # ── Cadena de modelos: intenta cada uno en orden hasta que uno responda ──────
    # Cada modelo tiene su propio contador TPD en Groq, así que si el principal
    # se agota por rate limit (429), los respaldos siguen disponibles.
    MODELOS_GROQ = [
        "llama-3.3-70b-versatile",  # Principal: mejor calidad LSC
        "llama-3.1-8b-instant",     # Respaldo 1: más rápido, límite independiente
        "llama3-8b-8192",           # Respaldo 2: Llama 3 base (muy estable)
        "llama3-70b-8192",          # Respaldo 3: Llama 3 70B base
    ]

    ultimo_error = None

    for modelo in MODELOS_GROQ:
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_LSC},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)

            if modelo != MODELOS_GROQ[0]:
                print(f"ℹ️ LSC Grammar: usando modelo de respaldo '{modelo}'")

            return _normalizar_respuesta(data, vocabulario_disponible)

        except json.JSONDecodeError as e:
            # JSON inválido no depende del modelo, no tiene sentido reintentar
            print(f"⚠️ LSC Grammar: JSON inválido con modelo '{modelo}': {e}")
            return _fallback_sin_ia(texto_espanol)

        except Exception as e:
            ultimo_error = e
            error_str = str(e)

            # Rate limit (429), sobrecarga (503) o modelo descontinuado → probar siguiente modelo
            if "429" in error_str or "503" in error_str or "rate_limit" in error_str.lower() or "model_decommissioned" in error_str.lower():
                print(f"⚠️ LSC Grammar: modelo '{modelo}' sin cupo o descontinuado, probando siguiente...")
                continue

            # Otro error (auth, red) → no tiene sentido reintentar
            print(f"⚠️ LSC Grammar: Error Groq con modelo '{modelo}': {e}")
            return _fallback_sin_ia(texto_espanol)

    # Todos los modelos agotados → fallback básico
    print(f"⚠️ LSC Grammar: todos los modelos Groq agotados. Último error: {ultimo_error}")
    return _fallback_sin_ia(texto_espanol)


# ─── Normalización de respuesta ───────────────────────────────────────────────
def _normalizar_respuesta(data: dict, vocabulario_disponible: list[str] | None) -> dict:
    """Limpia y enriquece la respuesta de la IA."""
    tokens = data.get("tokens", [])

    # Tipos que NO deben buscarse en la BD
    TIPOS_NO_BUSCABLES = {"facial", "aspect", "topic"}

    # Detectar faltantes contra vocabulario real de BD
    faltantes = []
    estrategia = data.get("missing_strategy", {})

    if vocabulario_disponible:
        vocab_lower = {_normalizar_token(v) for v in vocabulario_disponible}
        for t in tokens:
            word = t.get("word", "")
            tipo = t.get("type", "")
            if tipo in TIPOS_NO_BUSCABLES:
                continue
            if _normalizar_token(word) not in vocab_lower and word not in faltantes:
                faltantes.append(word)
                if word not in estrategia:
                    estrategia[word] = _inferir_estrategia(word)
    else:
        faltantes = data.get("missing_candidates", [])

    return {
        "tokens": tokens,
        "sentence_type": data.get("sentence_type", "declarative"),
        "facial_expression": data.get("facial_expression", "neutral"),
        "faltantes": faltantes,
        "estrategia_faltantes": estrategia,
        "notes": data.get("notes", ""),
        "error": None,
    }


def _inferir_estrategia(word: str) -> str:
    """Heurística simple para inferir cómo manejar una seña faltante."""
    # Si es sigla o muy corta → deletrear
    if len(word) <= 3 or word.isupper():
        return "spell"
    # Si parece nombre propio (empieza en mayúscula en el original)
    return "spell"


def _normalizar_token(token: str) -> str:
    """Normaliza un token para comparación: minúsculas, sin tildes."""
    token = token.lower().strip()
    token = unicodedata.normalize('NFD', token)
    token = ''.join(c for c in token if unicodedata.category(c) != 'Mn')
    return token


# ─── Fallback sin IA ──────────────────────────────────────────────────────────
def _fallback_sin_ia(texto: str) -> dict:
    """
    Fallback heurístico cuando la IA no está disponible.
    Aplica reglas gramaticales básicas de orden LSC.
    (Tiempo + Sujeto + Objeto/Verbo + Negación + Pregunta).
    """
    ARTICULOS = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'}
    PREPOSICIONES = {'a', 'de', 'en', 'con', 'por', 'para', 'hacia', 'desde',
                     'sin', 'sobre', 'bajo', 'ante', 'tras', 'al', 'del'}
    COPULATIVOS = {'es', 'son', 'soy', 'eres', 'somos', 'estoy', 'esta', 'estan', 'estamos'}
    TIEMPO = {'manana', 'hoy', 'ayer', 'ahora', 'antes', 'despues', 'siempre', 'nunca', 'ya', 'pronto', 'tarde', 'temprano'}
    SUJETOS = {'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos', 'ellas'}
    PREGUNTAS = {'como', 'donde', 'cuando', 'quien', 'que', 'cuanto', 'por_que'}
    NEGACION = {'no'}

    texto_limpio = texto.lower().strip()
    texto_limpio = unicodedata.normalize('NFD', texto_limpio)
    texto_limpio = ''.join(c for c in texto_limpio if unicodedata.category(c) != 'Mn')
    
    # Preservar conocimiento de si es pregunta directa antes de quitar signos
    es_pregunta_directa = any(c in texto_limpio for c in '¿?')
    
    # Agrupar "por que" antes de limpiar puntuación y dividir
    texto_limpio = texto_limpio.replace("por que", "por_que")
    
    # Eliminar signos de puntuación
    texto_limpio = re.sub(r'[.,!¿?¡;:]', '', texto_limpio)

    palabras = texto_limpio.split()
    
    tokens_tiempo = []
    tokens_sujeto = []
    tokens_negacion = []
    tokens_pregunta = []
    tokens_resto = []
    
    for p in palabras:
        if p in ARTICULOS or p in PREPOSICIONES or p in COPULATIVOS:
            continue
            
        if p in TIEMPO:
            tokens_tiempo.append({"word": p.upper(), "type": "time"})
        elif p in SUJETOS:
            tokens_sujeto.append({"word": p.upper(), "type": "subject"})
        elif p in PREGUNTAS:
            tokens_pregunta.append({"word": p.upper(), "type": "wh"})
        elif p in NEGACION:
            tokens_negacion.append({"word": p.upper(), "type": "neg"})
        else:
            tokens_resto.append({"word": p.upper(), "type": "other"})

    # Orden LSC Canónico: Tiempo -> Sujeto -> Resto -> Negación -> Pregunta
    tokens_ordenados = tokens_tiempo + tokens_sujeto + tokens_resto + tokens_negacion + tokens_pregunta
    
    sentence_type = "declarative"
    facial_expression = "neutral"
    
    if tokens_pregunta:
        sentence_type = "question_wh"
        facial_expression = "cejas_fruncidas"
        tokens_ordenados.append({"word": "[EF:CEJAS_FRUNCIDAS]", "type": "facial"})
    elif es_pregunta_directa:
        sentence_type = "question_yn"
        facial_expression = "cejas_arriba"
        tokens_ordenados.append({"word": "[EF:CEJAS_ARRIBA]", "type": "facial"})
    elif tokens_negacion:
        sentence_type = "negative"

    return {
        "tokens": tokens_ordenados,
        "sentence_type": sentence_type,
        "facial_expression": facial_expression,
        "faltantes": [],
        "estrategia_faltantes": {},
        "notes": "Fallback heurístico: IA no disponible. Se aplicó orden básico LSC por reglas.",
        "error": "Groq no disponible — usando reglas gramaticales básicas LSC locales.",
    }


def _respuesta_vacia() -> dict:
    return {
        "tokens": [],
        "sentence_type": "declarative",
        "facial_expression": "neutral",
        "faltantes": [],
        "estrategia_faltantes": {},
        "notes": "",
        "error": None,
    }


# ─── Extractor de palabras para búsqueda en BD ───────────────────────────────
def tokens_para_busqueda(resultado_lsc: dict) -> list[str]:
    """
    Extrae solo los tokens de palabras (sin expresiones faciales, aspectos ni tópicos)
    listos para buscar en la base de datos de videos.

    Args:
        resultado_lsc: Resultado de convertir_a_lsc()

    Returns:
        Lista de strings en MAYÚSCULAS para buscar en BD.
    """
    TIPOS_NO_BUSCABLES = {"facial", "aspect", "topic"}
    return [
        t["word"]
        for t in resultado_lsc.get("tokens", [])
        if t.get("type") not in TIPOS_NO_BUSCABLES
    ]