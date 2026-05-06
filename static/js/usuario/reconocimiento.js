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

// Variables para ventana deslizante (sliding window)
let ultimaSenaDetectada = '';
let cooldownActivo = 0;
let procesando = false;
let framesAcumuladosDesdePred = 0;

const FRAMES_SIN_MANO_MAX = 8;
const MIN_FRAMES_SEÑA     = 15;
const MAX_BUFFER_SIZE     = 50; // Ventana de ~2.5s (permite señas largas)
const INTERVALO_PRED      = 18; // Predecir cada ~0.9s
const COOLDOWN_FRAMES     = 24; // Esperar ~1.2s después de una detección
const INTERVALO_MS        = 50;
const JPEG_QUALITY        = 0.4;
const UMBRAL_CONFIANZA    = 60; // Confianza mínima para de corrido

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
            video: { 
                width: { ideal: 320 }, 
                height: { ideal: 240 }, 
                frameRate: { ideal: 30 },
                facingMode: "user"
            }
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

    // Evitar que el video de móviles (portrait) se achate (squash) al dibujarlo en 320x240
    // Calculamos un recorte (crop) tipo object-fit: cover para mantener la proporción
    const cw = canvas.width;  // 320
    const ch = canvas.height; // 240
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    const scale = Math.max(cw / vw, ch / vh);
    const sw = vw * scale;
    const sh = vh * scale;
    const dx = (cw - sw) / 2;
    const dy = (ch - sh) / 2;
    
    // Limpiar canvas y dibujar el video centrado sin deformarlo
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(video, 0, 0, vw, vh, dx, dy, sw, sh);

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
        
        // Ventana deslizante: agregamos el frame y quitamos el más viejo si excede el máximo
        secuenciaFrames.push(canvas.toDataURL('image/jpeg', JPEG_QUALITY));
        if (secuenciaFrames.length > MAX_BUFFER_SIZE) {
            secuenciaFrames.shift();
        }
        
        badgeSeña.textContent   = 'Capturando...';
        estadoTexto.textContent = 'Traduciendo de corrido...';

        // Manejo de cooldown para no repetir la misma seña muy rápido
        if (cooldownActivo > 0) {
            cooldownActivo--;
        } else {
            framesAcumuladosDesdePred++;
            // Predecir periódicamente si tenemos suficientes frames
            if (framesAcumuladosDesdePred >= INTERVALO_PRED && secuenciaFrames.length >= MIN_FRAMES_SEÑA && !procesando) {
                framesAcumuladosDesdePred = 0;
                procesarSecuencia([...secuenciaFrames]); // Usamos copia del array
            }
        }
    } else {
        if (grabando) {
            framesSinMano++;
            if (framesSinMano >= FRAMES_SIN_MANO_MAX) {
                // Hacer una última predicción si bajó la mano y quedó algo sin evaluar
                if (secuenciaFrames.length >= MIN_FRAMES_SEÑA && !procesando && framesAcumuladosDesdePred > 0) {
                    procesarSecuencia([...secuenciaFrames]);
                }
                
                // Reset de la ventana deslizante al bajar la mano
                grabando = false;
                secuenciaFrames = [];
                framesSinMano   = 0;
                framesAcumuladosDesdePred = 0;
                cooldownActivo = 0;
                ultimaSenaDetectada = ''; // Permite repetir la misma seña si vuelve a subir la mano
                
                estadoTexto.textContent = 'Manos bajas — puedes continuar cuando quieras';
                badgeSeña.textContent   = 'Esperando mano...';
            }
        } else {
            badgeSeña.textContent   = 'Esperando mano...';
            estadoTexto.textContent = 'Listo — muestra tu mano para firmar';
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
    
    // Resetear variables
    secuenciaFrames = []; 
    grabando = false; 
    framesSinMano = 0;
    ultimaSenaDetectada = '';
    cooldownActivo = 0;
    procesando = false;
    framesAcumuladosDesdePred = 0;
    
    speechSynthesis.cancel();
}

// ── Predicción ───────────────────────────────────────────────────────
async function procesarSecuencia(frames) {
    if (procesando) return;
    procesando = true;

    try {
        // Al enviar 24 frames en lugar de 12, el servidor tiene el doble de información 
        // temporal para que su "interpolación" coincida mejor con los 30 frames del entrenamiento.
        const framesAEnviar = submuestrear(frames, 24);

        const response = await fetch('/reconocimientos/predecir/', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ frames: framesAEnviar }),
        });
        const data = await response.json();
        console.log('[DEBUG] predecir continuo:', data);

        const sena = data.seña || '';

        // Modal de groserías
        if (sena && typeof GroseriasModal !== 'undefined' && GroseriasModal.verificarSena(sena)) {
            GroseriasModal.mostrar(sena, 'sena');
            procesando = false;
            return;
        }

        if (sena && data.confianza >= UMBRAL_CONFIANZA) {
            // Solo agregar si es una seña diferente a la última detectada en esta ráfaga
            if (sena !== ultimaSenaDetectada) {
                ultimaSenaDetectada = sena;
                cooldownActivo = COOLDOWN_FRAMES; // Evitar detecciones espurias durante la transición
                
                señaActual.textContent     = sena.toUpperCase();
                confianzaTexto.textContent = 'Confianza: ' + data.confianza + '%';
                
                if (modoVoz) {
                    hablar(sena);
                } else {
                    textoAcumulado += (textoAcumulado ? ' ' : '') + sena;
                    resultado.classList.add('activo');
                    resultado.innerHTML = '<div id="historial">' + textoAcumulado + '</div>';
                }
            }
        }
        // Nota: Si no se reconoce nada o es la misma seña, simplemente se ignora y el loop continúa.
        // No borramos la seña anterior de la interfaz para no parpadear visualmente.
    } catch (err) {
        console.error('[DEBUG] Error:', err);
    } finally {
        procesando = false;
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
    framesSinMano   = 0;
    ultimaSenaDetectada = '';
    cooldownActivo = 0;
    procesando = false;
    framesAcumuladosDesdePred = 0;
    
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