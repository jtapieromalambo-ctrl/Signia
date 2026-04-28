const video          = document.getElementById('video');
const canvas         = document.getElementById('canvas');
const ctx            = canvas.getContext('2d');
const btnCamara      = document.getElementById('btn-camara');
const placeholder    = document.getElementById('placeholder');
const badgeSeña      = document.getElementById('badge-seña');
const señaActual     = document.getElementById('seña-actual');
const confianzaTexto = document.getElementById('confianza-texto');
const estadoTexto    = document.getElementById('estado-texto');
const resultado      = document.getElementById('resultado');
const pillToggle     = document.getElementById('pill-toggle');
const pillThumb      = document.getElementById('pill-thumb');

let activo          = false;
let textoAcumulado  = '';
let modoVoz         = false;
let grabando        = false;
let secuenciaFrames = [];
let framesSinMano   = 0;
let handLandmarker  = null;
let mpListo         = false;

const FRAMES_SIN_MANO_MAX = 8;
const MIN_FRAMES_SEÑA     = 8;
const INTERVALO_MS        = 50;
const JPEG_QUALITY        = 0.4;

// ── MediaPipe — import dinámico desde ruta Django ────────────────────
async function iniciarMediaPipe() {
    try {
        estadoTexto.textContent = 'Cargando detector de manos...';

        const { FilesetResolver, HandLandmarker } = await import(window.MP_BUNDLE_PATH);

        const vision = await FilesetResolver.forVisionTasks(window.MP_WASM_PATH);

        handLandmarker = await HandLandmarker.createFromOptions(vision, {
            baseOptions: {
                modelAssetPath: window.MP_MODEL_PATH,
                delegate: 'GPU',
            },
            runningMode:                'VIDEO',
            numHands:                   2,
            minHandDetectionConfidence: 0.5,
            minHandPresenceConfidence:  0.5,
            minTrackingConfidence:      0.5,
        });

        mpListo = true;
        estadoTexto.textContent = 'Detector listo — presiona "Iniciar cámara"';
        console.log('[MediaPipe] OK — modelo local cargado');
    } catch (err) {
        console.error('[MediaPipe] Error:', err);
        mpListo = false;
        estadoTexto.textContent = 'Error al cargar detector: ' + err.message;
    }
}

iniciarMediaPipe();

// ── Voz ──────────────────────────────────────────────────────────────
let vozEspanol = null;
function cargarVoz() {
    const voces = speechSynthesis.getVoices();
    vozEspanol = voces.find(v => v.lang.startsWith('es') && !v.name.includes('Raul') && v.localService)
              || voces.find(v => v.lang.startsWith('es') && !v.name.includes('Raul'))
              || voces.find(v => v.lang.startsWith('es'))
              || null;
}
speechSynthesis.onvoiceschanged = cargarVoz;
cargarVoz();

setInterval(() => {
    if (speechSynthesis.speaking) { speechSynthesis.pause(); speechSynthesis.resume(); }
}, 5000);

function hablar(texto) {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.rate = 1.1; u.pitch = 1.0; u.volume = 1.0;
    if (vozEspanol) { u.voice = vozEspanol; u.lang = vozEspanol.lang; }
    else u.lang = 'es';
    speechSynthesis.speak(u);
}

// ── Toggle modo ──────────────────────────────────────────────────────
function cambiarModo() {
    modoVoz = !modoVoz;
    pillToggle.classList.toggle('voz', modoVoz);
    if (modoVoz) {
        estadoTexto.textContent = 'Modo voz activo';
        hablar('modo voz activado');
    } else {
        estadoTexto.textContent = 'Modo texto activo';
        speechSynthesis.cancel();
        hablar('modo texto activado');
    }
}

// ── Cámara ───────────────────────────────────────────────────────────
async function iniciar() {
    if (!mpListo) {
        estadoTexto.textContent = 'Cargando detector, espera...';
        await iniciarMediaPipe();
        if (!mpListo) return;
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 30 } }
        });
        video.srcObject = stream;

        // Esperar a que el video tenga dimensiones válidas antes de arrancar
        await new Promise(resolve => {
            if (video.readyState >= 2 && video.videoWidth > 0) {
                resolve();
            } else {
                video.onloadeddata     = resolve;
                video.onloadedmetadata = resolve; // fallback
            }
        });

        video.style.display       = 'block';
        placeholder.style.display = 'none';
        badgeSeña.style.display   = 'block';
        activo = true;
        estadoTexto.textContent = 'Listo — muestra tu mano y haz la seña';
        btnCamara.textContent   = 'Detener cámara';
        btnCamara.classList.add('rojo');
        btnCamara.onclick = detener;
        programarCaptura();
    } catch (err) {
        estadoTexto.textContent = 'Error cámara: ' + err.message;
    }
}

// ── Bucle rAF puro ────────────────────────────────────────────────────
let ultimaCaptura = 0;

function programarCaptura() {
    if (!activo) return;
    requestAnimationFrame((ts) => {
        if (ts - ultimaCaptura >= INTERVALO_MS) {
            ultimaCaptura = ts;
            tick(ts);
        }
        programarCaptura();
    });
}

function tick(timestamp) {
    if (!activo || !mpListo) return;

    // Guarda: video debe tener dimensiones válidas
    if (video.readyState < 2 || video.videoWidth === 0 || video.videoHeight === 0) return;

    ctx.drawImage(video, 0, 0, 320, 240);

    let hayMano = false;
    try {
        const result = handLandmarker.detectForVideo(video, timestamp);
        hayMano = result.landmarks && result.landmarks.length > 0;
    } catch (e) {
        return; // video aún no listo
    }

    if (hayMano) {
        grabando = true;
        framesSinMano = 0;
        secuenciaFrames.push(canvas.toDataURL('image/jpeg', JPEG_QUALITY));
        badgeSeña.textContent   = 'Grabando... ' + secuenciaFrames.length + ' frames';
        estadoTexto.textContent = 'Grabando seña — mantén el movimiento';
    } else {
        if (grabando) {
            framesSinMano++;
            if (framesSinMano >= FRAMES_SIN_MANO_MAX) {
                grabando = false;
                const frames = secuenciaFrames.slice();
                secuenciaFrames = [];
                framesSinMano   = 0;
                if (frames.length >= MIN_FRAMES_SEÑA) {
                    procesarSecuencia(frames);
                } else {
                    estadoTexto.textContent = 'Seña muy corta — intenta de nuevo';
                    badgeSeña.textContent   = 'Esperando mano...';
                }
            }
        } else {
            badgeSeña.textContent   = 'Esperando mano...';
            estadoTexto.textContent = 'Listo — muestra tu mano y haz la seña';
        }
    }
}

function detener() {
    activo = false;
    if (video.srcObject) video.srcObject.getTracks().forEach(t => t.stop());
    video.style.display       = 'none';
    placeholder.style.display = 'flex';
    badgeSeña.style.display   = 'none';
    señaActual.textContent     = '--';
    confianzaTexto.textContent = 'Confianza: --';
    estadoTexto.textContent    = 'Cámara detenida';
    btnCamara.textContent      = 'Iniciar cámara';
    btnCamara.classList.remove('rojo');
    btnCamara.onclick = iniciar;
    secuenciaFrames = []; grabando = false; framesSinMano = 0;
    speechSynthesis.cancel();
}

// ── Predicción ───────────────────────────────────────────────────────
async function procesarSecuencia(frames) {
    try {
        estadoTexto.textContent = 'Analizando ' + frames.length + ' frames...';
        badgeSeña.textContent   = 'Analizando...';
        const framesAEnviar = submuestrear(frames, 12);

        const response = await fetch('/reconocimientos/predecir/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ frames: framesAEnviar }),
        });
        const data = await response.json();
        console.log('[DEBUG] predecir:', data);

        const sena = data.seña || '';

        if (sena && typeof GroseriasModal !== 'undefined' && GroseriasModal.verificarSena(sena)) {
            GroseriasModal.mostrar(sena, 'sena');
            return;
        }

        if (sena && data.confianza >= 70) {
            señaActual.textContent     = sena.toUpperCase();
            confianzaTexto.textContent = 'Confianza: ' + data.confianza + '%';
            estadoTexto.textContent    = 'Seña detectada: ' + sena;
            badgeSeña.textContent      = sena.toUpperCase();
            if (modoVoz) {
                hablar(sena);
            } else {
                textoAcumulado += (textoAcumulado ? ' ' : '') + sena;
                resultado.classList.add('activo');
                resultado.innerHTML = '<div id="historial">' + textoAcumulado + '</div>';
            }
        } else {
            señaActual.textContent     = '--';
            confianzaTexto.textContent = 'Confianza: --';
            estadoTexto.textContent    = data.confianza
                ? 'Confianza baja (' + data.confianza + '%) — intenta de nuevo'
                : 'No se reconoció la seña — intenta de nuevo';
            badgeSeña.textContent = 'Esperando mano...';
        }
    } catch (err) {
        console.error('[DEBUG] Error:', err);
        estadoTexto.textContent = 'Error al procesar: ' + err.message;
    }
}

function submuestrear(frames, max) {
    if (frames.length <= max) return frames;
    const out = [], paso = frames.length / max;
    for (let i = 0; i < max; i++) out.push(frames[Math.floor(i * paso)]);
    return out;
}

function limpiarHistorial() {
    textoAcumulado  = '';
    secuenciaFrames = [];
    grabando        = false;
    resultado.classList.remove('activo');
    resultado.innerHTML = '<span style="color:var(--text-muted); font-style:italic;">El texto traducido aparecerá aquí...</span>';
    señaActual.textContent     = '--';
    confianzaTexto.textContent = 'Confianza: --';
    speechSynthesis.cancel();
}

// ── Exponer funciones globales (necesario con type="module") ─────────
window.iniciar          = iniciar;
window.detener          = detener;
window.cambiarModo      = cambiarModo;
window.limpiarHistorial = limpiarHistorial;