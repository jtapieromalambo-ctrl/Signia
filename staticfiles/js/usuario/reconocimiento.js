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
let intervalo       = null;
let textoAcumulado  = '';
let modoVoz         = false;
let enviando        = false;
let grabando        = false;
let secuenciaFrames = [];
let framesSinMano   = 0;

// ── Parámetros optimizados ───────────────────────────────
const FRAMES_SIN_MANO_MAX = 8;   // era 15 → corta antes
const MIN_FRAMES_SEÑA     = 8;   // era 15 → procesa antes
const INTERVALO_MS        = 60;  // era 100ms → más rápido
const JPEG_QUALITY        = 0.4; // era 0.5 → menos peso = menos latencia de red

// ── Voz ──────────────────────────────────────────────────
let vozEspanol = null;

function cargarVoz() {
    const voces = speechSynthesis.getVoices();
    vozEspanol = voces.find(v => v.lang.startsWith('es') && !v.name.includes('Raul') && v.localService)
              || voces.find(v => v.lang.startsWith('es') && !v.name.includes('Raul'))
              || voces.find(v => v.lang.startsWith('es'))
              || null;
    console.log('[VOZ] Voz seleccionada:', vozEspanol?.name, '| local:', vozEspanol?.localService);
}
speechSynthesis.onvoiceschanged = cargarVoz;
cargarVoz();

// Keepalive para Chrome
setInterval(() => {
    if (speechSynthesis.speaking) {
        speechSynthesis.pause();
        speechSynthesis.resume();
    }
}, 5000);

// ── Voz sin delay ────────────────────────────────────────
// Se eliminó el setTimeout de 100ms — cancel() es síncrono suficiente
function hablar(texto) {
    speechSynthesis.cancel();
    const u  = new SpeechSynthesisUtterance(texto);
    u.rate   = 1.1;   // un poco más rápido para respuesta más ágil
    u.pitch  = 1.0;
    u.volume = 1.0;
    if (vozEspanol) {
        u.voice = vozEspanol;
        u.lang  = vozEspanol.lang;
    } else {
        u.lang = 'es';
    }
    u.onerror = (e) => console.error('[VOZ] Error:', e.error);
    u.onstart = ()  => console.log('[VOZ] Hablando:', texto);
    u.onend   = ()  => console.log('[VOZ] Terminó');
    speechSynthesis.speak(u);
}

// ── Toggle modo ──────────────────────────────────────────
function cambiarModo() {
    modoVoz = !modoVoz;
    pillToggle.classList.toggle('voz', modoVoz);
    if (modoVoz) {
        estadoTexto.textContent = 'Modo voz — las señas se leerán en voz alta';
        hablar('modo voz activado');
    } else {
        estadoTexto.textContent = 'Modo texto activado';
        speechSynthesis.cancel();
        hablar('modo texto activado');
    }
}

// ── Cámara ───────────────────────────────────────────────
async function iniciar() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width:  { ideal: 320 },  // fuerza resolución baja desde origen
                height: { ideal: 240 },
                frameRate: { ideal: 30 }
            }
        });
        video.srcObject = stream;
        video.style.display       = 'block';
        placeholder.style.display = 'none';
        badgeSeña.style.display   = 'block';
        activo   = true;
        enviando = false;
        estadoTexto.textContent = 'Listo — muestra tu mano y haz la seña';
        btnCamara.textContent   = 'Detener cámara';
        btnCamara.classList.add('rojo');
        btnCamara.onclick = detener;

        // Usar requestAnimationFrame en vez de setInterval para capturar
        // en sincronía con el render del video — menos frames perdidos
        programarCaptura();
    } catch (err) {
        estadoTexto.textContent = 'Error al acceder a la cámara: ' + err.message;
    }
}

// ── Captura con requestAnimationFrame + throttle ─────────
let ultimaCaptura = 0;

function programarCaptura() {
    if (!activo) return;
    requestAnimationFrame((timestamp) => {
        if (timestamp - ultimaCaptura >= INTERVALO_MS) {
            ultimaCaptura = timestamp;
            capturarFrame();
        }
        programarCaptura();
    });
}

function detener() {
    activo   = false;
    enviando = false;
    clearInterval(intervalo);
    if (video.srcObject) video.srcObject.getTracks().forEach(t => t.stop());
    video.style.display       = 'none';
    placeholder.style.display = 'flex';
    badgeSeña.style.display   = 'none';
    señaActual.textContent     = '--';
    confianzaTexto.textContent = 'Confianza: --';
    estadoTexto.textContent    = 'Cámara detenida';
    btnCamara.textContent      = 'Iniciar cámara';
    btnCamara.classList.remove('rojo');
    btnCamara.onclick  = iniciar;
    secuenciaFrames    = [];
    grabando           = false;
    framesSinMano      = 0;
    speechSynthesis.cancel();
}

async function capturarFrame() {
    if (!activo || enviando) return;
    enviando = true;
    ctx.drawImage(video, 0, 0, 320, 240);
    const frameBase64 = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
    try {
        const formData = new FormData();
        formData.append('frame', frameBase64);
        const response = await fetch('/reconocimientos/detectar_mano/', { method: 'POST', body: formData });
        const data     = await response.json();
        procesarDeteccion(data.hay_mano, frameBase64);
    } catch (err) {
        estadoTexto.textContent = 'Error de red: ' + err.message;
    } finally {
        enviando = false;
    }
}

function procesarDeteccion(hayMano, frameBase64) {
    if (hayMano) {
        grabando = true;
        framesSinMano = 0;
        secuenciaFrames.push(frameBase64);
        badgeSeña.textContent   = `Grabando... ${secuenciaFrames.length} frames`;
        estadoTexto.textContent = 'Grabando seña — mantén el movimiento';
    } else {
        if (grabando) {
            framesSinMano++;
            estadoTexto.textContent = 'Procesando...';
            if (framesSinMano >= FRAMES_SIN_MANO_MAX) {
                grabando = false;
                if (secuenciaFrames.length >= MIN_FRAMES_SEÑA) {
                    procesarSecuencia();
                } else {
                    estadoTexto.textContent = 'Seña muy corta — intenta de nuevo';
                }
                secuenciaFrames = [];
                framesSinMano   = 0;
            }
        } else {
            badgeSeña.textContent   = 'Esperando mano...';
            estadoTexto.textContent = 'Listo — muestra tu mano y haz la seña';
        }
    }
}

async function procesarSecuencia() {
    try {
        estadoTexto.textContent = `Analizando ${secuenciaFrames.length} frames...`;
        badgeSeña.textContent   = 'Analizando...';

        // Submuestreo: si hay muchos frames, tomar solo los necesarios
        // Esto reduce el payload sin perder información relevante
        const framesAEnviar = submuestrear(secuenciaFrames, 12);

        const response = await fetch('/reconocimientos/predecir/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frames: framesAEnviar })
        });
        const data = await response.json();
       // ✅ ASÍ DEBE QUEDAR
if (GroseriasModal.verificarSena(data.seña)) {
    GroseriasModal.mostrar(data.seña, "sena");
    return;
}

if (data.seña && data.confianza >= 70) {
            señaActual.textContent     = data.seña.toUpperCase();
            confianzaTexto.textContent = `Confianza: ${data.confianza}%`;
            estadoTexto.textContent    = `Seña detectada: ${data.seña}`;
            badgeSeña.textContent      = data.seña.toUpperCase();

            if (modoVoz) {
                hablar(data.seña); // sin delay ahora
            } else {
                textoAcumulado += (textoAcumulado ? ' ' : '') + data.seña;
                resultado.classList.add('activo');
                resultado.innerHTML = `<div id="historial">${textoAcumulado}</div>`;
            }
        } else {
            señaActual.textContent     = '--';
            confianzaTexto.textContent = 'Confianza: --';
            estadoTexto.textContent    = data.confianza
                ? `Confianza baja (${data.confianza}%) — intenta de nuevo`
                : 'No se reconoció la seña — intenta de nuevo';
            badgeSeña.textContent = 'Esperando mano...';
        }
    } catch (err) {
        estadoTexto.textContent = 'Error al procesar: ' + err.message;
    }
}

// Toma N frames distribuidos uniformemente de la secuencia
// Evita enviar 40+ frames cuando el modelo solo necesita ~12
function submuestrear(frames, max) {
    if (frames.length <= max) return frames;
    const resultado = [];
    const paso = frames.length / max;
    for (let i = 0; i < max; i++) {
        resultado.push(frames[Math.floor(i * paso)]);
    }
    return resultado;
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