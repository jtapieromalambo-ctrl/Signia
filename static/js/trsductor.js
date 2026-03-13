/* ============================================================
   ARCHIVO: static/js/traduccion/traductor.js
   Lógica del traductor de señas:
   - Encender/apagar cámara
   - Simular detección de señas
   - Mostrar texto traducido
   - Reproducir audio con síntesis de voz
   ============================================================ */


/* ──────────────────────────────────────
   VARIABLES DE ESTADO
   Guardan la información actual de la app
────────────────────────────────────────*/

let stream       = null;   // guarda el objeto de la cámara (MediaStream)
let detecting    = false;  // true cuando la cámara está activa y detectando
let timer        = null;   // referencia al setTimeout de detección
let currentText  = '';     // texto acumulado de todas las señas detectadas
let speechRate   = 1;      // velocidad de la voz (0.5 = lento, 2 = rápido)
let speechPitch  = 1;      // tono de la voz (0.5 = grave, 2 = agudo)
let frameCount   = 0;      // contador de "frames" para calcular fps
let fpsTime      = performance.now(); // tiempo base para calcular fps


/* ──────────────────────────────────────
   DATASET DE SEÑAS
   Cada objeto tiene:
   - sign: la letra de la seña
   - word: la palabra que representa
   Aquí iría el resultado de tu modelo de IA.
   Por ahora se elige una al azar para simular.
────────────────────────────────────────*/
const SIGNS = [
  { sign: 'A', word: 'Hola'          },
  { sign: 'B', word: 'Buenos días'   },
  { sign: 'C', word: 'Gracias'       },
  { sign: 'D', word: 'Por favor'     },
  { sign: 'E', word: 'Sí'            },
  { sign: 'F', word: 'No'            },
  { sign: 'G', word: 'Necesito ayuda'},
  { sign: 'H', word: 'Agua'          },
  { sign: 'I', word: 'Amor'          },
  { sign: 'J', word: 'Mi casa'       },
  { sign: 'K', word: 'Familia'       },
  { sign: 'L', word: 'Estoy bien'    },
  { sign: 'M', word: 'Me duele'      },
  { sign: 'N', word: 'Quiero comer'  },
  { sign: 'O', word: 'Buenas noches' },
  { sign: 'P', word: 'Adiós'         },
  { sign: 'Q', word: 'Perdón'        },
  { sign: 'R', word: 'Entendido'     },
];

/* Función auxiliar: número entero aleatorio entre a y b */
const rnd = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;


/* ══════════════════════════════════════
   CÁMARA
══════════════════════════════════════ */

/* Activa la cámara del dispositivo */
async function startCam() {
  try {
    // Pide permiso al navegador para usar la cámara frontal
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
      audio: false   // no necesitamos audio de la cámara
    });

    // Conecta el stream al elemento <video> del HTML
    document.getElementById('video').srcObject = stream;

    // Oculta la pantalla "sin cámara"
    document.getElementById('noCam').style.display = 'none';

    // Actualiza los botones
    document.getElementById('btnStart').disabled = true;
    document.getElementById('btnStop').disabled  = false;

    // Cambia el indicador de estado a verde
    setStatus('on', 'Activo');

    // Inicia el bucle de detección
    startDetecting();

  } catch (error) {
    // Si el usuario rechaza el permiso o hay error
    setStatus('', 'Error de cámara');
    alert('No se pudo acceder a la cámara. Verifica los permisos del navegador.');
  }
}

/* Apaga la cámara y limpia todo */
function stopCam() {
  // Detiene cada pista de video
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }

  // Desconecta el video
  document.getElementById('video').srcObject = null;

  // Muestra la pantalla "sin cámara"
  document.getElementById('noCam').style.display = 'flex';

  // Restaura los botones
  document.getElementById('btnStart').disabled = false;
  document.getElementById('btnStop').disabled  = true;

  // Para la detección y limpia los efectos visuales
  stopDetecting();
  document.getElementById('detOverlay').classList.remove('show');
  document.getElementById('scanLine').classList.remove('on');
  document.getElementById('fpsBadge').textContent = '— fps';

  setStatus('', 'Sin cámara');
}


/* ══════════════════════════════════════
   BUCLE DE DETECCIÓN
   Simula que el modelo de IA detecta señas
   cada cierto tiempo aleatorio.
══════════════════════════════════════ */

function startDetecting() {
  detecting = true;

  // Activa la línea de escaneo animada
  document.getElementById('scanLine').classList.add('on');

  // Programa la primera detección
  scheduleNext();

  // Actualiza el contador de FPS cada segundo
  setInterval(() => {
    const now = performance.now();
    const fps = Math.round(frameCount * 1000 / (now - fpsTime));
    document.getElementById('fpsBadge').textContent = fps + ' fps';
    frameCount = 0;
    fpsTime    = now;
  }, 1000);
}

function stopDetecting() {
  detecting = false;
  clearTimeout(timer);
  document.getElementById('scanLine').classList.remove('on');
}

/* Programa la próxima detección entre 2.2 y 3.8 segundos */
function scheduleNext() {
  if (!detecting) return;
  timer = setTimeout(() => {
    runDetection();
    scheduleNext();   // vuelve a programar la siguiente
  }, rnd(2200, 3800));
}

/* Ejecuta una detección: elige una seña al azar y la procesa */
function runDetection() {
  frameCount++;  // cuenta para el FPS

  // Elige una seña aleatoria del dataset
  const detected   = SIGNS[Math.floor(Math.random() * SIGNS.length)];
  const confidence = rnd(76, 98);  // confianza simulada entre 76% y 98%

  // Muestra estado "analizando" (amarillo)
  setStatus('busy', 'Analizando...');

  // Actualiza el overlay sobre el video
  document.getElementById('detLetter').textContent = detected.sign;
  document.getElementById('detWord').textContent   = detected.word;
  document.getElementById('detConf').textContent   = confidence + '%';
  document.getElementById('detOverlay').classList.add('show');

  // Actualiza la barra de confianza
  document.getElementById('confFill').style.width = confidence + '%';
  document.getElementById('confPct').textContent  = confidence + '%';

  // Después de 600ms confirma la detección y actualiza la traducción
  setTimeout(() => {
    setStatus('on', 'Activo');
    addTranslation(detected.word, detected.sign, confidence);
  }, 600);
}


/* ══════════════════════════════════════
   TRADUCCIÓN
   Agrega la nueva palabra al texto y
   actualiza todos los elementos del panel.
══════════════════════════════════════ */

function addTranslation(word, sign, confidence) {
  // Añade la palabra al texto acumulado
  currentText += (currentText ? ' ' : '') + word;

  // Reconstruye el texto en el panel, con la última palabra en azul
  const textEl = document.getElementById('transText');
  textEl.innerHTML = '';

  const words = currentText.split(' ');
  words.forEach((w, i) => {
    const span = document.createElement('span');
    // Si es la última palabra, le agrega la clase de resaltado
    span.className   = (i === words.length - 1) ? 'word--new' : '';
    span.textContent = (i > 0 ? ' ' : '') + w;
    textEl.appendChild(span);
  });

  // Agrega un chip clicable con la palabra
  addChip(word);

  // Agrega la entrada al historial
  addHistory(word, sign, confidence);

  // Reproduce la palabra en voz alta
  speak(word);
}

/* Crea una pastilla (chip) clicable para la palabra detectada */
function addChip(word) {
  const container = document.getElementById('chips');

  // Quita el resaltado "fresh" de los chips anteriores
  container.querySelectorAll('.chip--fresh').forEach(c => c.classList.remove('chip--fresh'));

  const chip = document.createElement('div');
  chip.className   = 'chip chip--fresh';
  chip.textContent = word;
  chip.title       = 'Reproducir: ' + word;
  chip.onclick     = () => speak(word);
  container.appendChild(chip);

  // Limita a 18 chips máximo (borra el más antiguo)
  while (container.children.length > 18) {
    container.removeChild(container.firstChild);
  }
}

/* Agrega una fila al historial */
function addHistory(word, sign, confidence) {
  const list = document.getElementById('histList');

  // Si existe el mensaje "vacío", lo elimina
  const empty = list.querySelector('.history__empty');
  if (empty) empty.remove();

  // Crea la fila del historial
  const item = document.createElement('div');
  item.className = 'history__item';
  item.innerHTML = `
    <div class="history__letter">${sign}</div>
    <div class="history__info">
      <div class="history__word">${word}</div>
      <div class="history__bar">
        <div class="history__bar-fill" style="width: ${confidence}%"></div>
      </div>
      <div class="history__meta">
        ${new Date().toLocaleTimeString('es-CO')} · ${confidence}% confianza
      </div>
    </div>
    <button class="history__speak" onclick="speak('${word}')" title="Reproducir">🔊</button>
  `;

  // Inserta al principio (más reciente arriba)
  list.insertBefore(item, list.firstChild);

  // Limita a 25 entradas
  while (list.children.length > 25) {
    list.removeChild(list.lastChild);
  }
}


/* ══════════════════════════════════════
   SÍNTESIS DE VOZ
   Usa la API nativa del navegador para
   leer el texto en voz alta en español.
══════════════════════════════════════ */

function speak(text) {
  // Si el navegador no soporta síntesis de voz, no hace nada
  if (!window.speechSynthesis) return;

  // Cancela cualquier reproducción anterior
  window.speechSynthesis.cancel();

  // Crea el objeto de reproducción
  const utterance       = new SpeechSynthesisUtterance(text);
  utterance.lang        = 'es-CO';         // español colombiano
  utterance.rate        = speechRate;       // velocidad del slider
  utterance.pitch       = speechPitch;      // tono del slider

  // Al empezar a hablar: activa animaciones
  utterance.onstart = () => {
    document.querySelectorAll('.wave__bar').forEach(b => b.classList.add('on'));
    document.getElementById('waveSpeak').classList.add('talking');
    document.getElementById('mainSpeak').classList.add('talking');
    document.getElementById('audioLbl').textContent = '▶ ' + text;
  };

  // Al terminar: desactiva animaciones
  utterance.onend = () => {
    document.querySelectorAll('.wave__bar').forEach(b => b.classList.remove('on'));
    document.getElementById('waveSpeak').classList.remove('talking');
    document.getElementById('mainSpeak').classList.remove('talking');
    document.getElementById('audioLbl').textContent = 'síntesis de voz lista';
  };

  // Ejecuta la reproducción
  window.speechSynthesis.speak(utterance);
}

/* Lee todo el texto acumulado de una vez */
function speakAll() {
  if (currentText) speak(currentText);
}


/* ══════════════════════════════════════
   UTILIDADES
══════════════════════════════════════ */

/* Borra el texto traducido y los chips */
function clearAll() {
  currentText = '';

  document.getElementById('transText').innerHTML =
    '<span class="trans-display__placeholder">esperando señas...</span>';

  document.getElementById('chips').innerHTML = '';

  document.getElementById('confFill').style.width = '0%';
  document.getElementById('confPct').textContent  = '0%';

  document.getElementById('detOverlay').classList.remove('show');

  window.speechSynthesis?.cancel();
}

/* Borra el historial */
function clearHistory() {
  document.getElementById('histList').innerHTML =
    '<div class="history__empty">Las señas detectadas<br>aparecerán aquí</div>';
}

/* Actualiza el indicador de estado (puntito + texto) */
function setStatus(type, text) {
  const dot = document.getElementById('statusDot');
  // Limpia clases anteriores y agrega la nueva si existe
  dot.className = 'status-pill__dot' + (type ? ' ' + type : '');
  document.getElementById('statusText').textContent = text;
}