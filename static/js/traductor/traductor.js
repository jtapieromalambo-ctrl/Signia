// ─── REFERENCIAS AL DOM ───────────────────────────────────────────────
const videoBase = document.getElementById('videoBase');

// ─── ESTADO DEL REPRODUCTOR MULTI-VIDEO ────────────────────────────────
let videosCola   = []; // Elementos <video> de la cola actual
let indiceActual = 0;

// Inicializa los listeners de finalización para los videos existentes
function _inicializarVideos() {
    videosCola = Array.from(document.querySelectorAll('.video-item'));
    
    // Configurar cada video en la cola
    videosCola.forEach((videoEl, index) => {
        // Remover listeners anteriores para evitar duplicados
        videoEl.onended = null;
        videoEl.onended = () => reproducirSiguiente();
        
        // Precargar activamente
        videoEl.load();
    });
}

// ─── FUNCIÓN PRINCIPAL: reproducirSiguiente() ─────────────────────────
function reproducirSiguiente() {
    if (indiceActual < videosCola.length) {
        const elNuevo     = videosCola[indiceActual];
        const elViejo     = (indiceActual === 0) ? null : videosCola[indiceActual - 1];
        const esElPrimero = (indiceActual === 0);

        // Mostrar nuevo elemento
        elNuevo.style.display = 'block';

        elNuevo.play()
            .then(() => {
                // CORTE INSTANTÁNEO: Ocultar el viejo al instante
                if (elViejo) {
                    elViejo.pause();
                    elViejo.style.display = 'none';
                }

                if (esElPrimero && videoBase) {
                    videoBase.pause();
                    videoBase.style.display = 'none';
                }
                
                // Mover índice al siguiente
                indiceActual++;
            })
            .catch(() => {
                // Fallback para reproducir si hay bloqueos del navegador
                if (elViejo) {
                    elViejo.pause();
                    elViejo.style.display = 'none';
                }
                if (esElPrimero && videoBase) {
                    videoBase.pause();
                    videoBase.style.display = 'none';
                }
                indiceActual++;
                setTimeout(() => elNuevo.play().catch(() => {}), 10);
            });

    } else {
        // ─── COLA TERMINADA: vuelve al video base con corte directo ──────
        // Detener y ocultar el último video reproducido
        if (videosCola.length > 0) {
            const ultimoVideo = videosCola[videosCola.length - 1];
            ultimoVideo.pause();
            ultimoVideo.style.display = 'none';
        }

        indiceActual = 0;

        if (videoBase) {
            videoBase.style.display = 'block';
            videoBase.play().catch(() => {});
        }
    }
}

// Inicializar videos de la carga inicial
_inicializarVideos();
if (videosCola.length > 0) {
    reproducirSiguiente();
}


// ─── HELPER: Actualizar UI desde respuesta AJAX ───────────────────────
function _actualizarUi(doc) {
    // 1. Strip LSC permanente (tokens en orden LSC)
    const resViejo = document.getElementById('lsc-resultado');
    const resNuevo = doc.getElementById('lsc-resultado');
    if (resViejo && resNuevo) {
        resViejo.innerHTML = resNuevo.innerHTML;
        resViejo.className = resNuevo.className;
    }

    // 2. Label con indicador de modelo IA
    const labelViejo = document.getElementById('labelPalabra');
    const labelNuevo = doc.getElementById('labelPalabra');
    if (labelViejo && labelNuevo) labelViejo.innerHTML = labelNuevo.innerHTML;

    // 3. Toast LSC flotante (metadatos, notas, señas faltantes)
    const toastViejo = document.getElementById('lscToast');
    if (toastViejo) toastViejo.remove();

    const toastNuevo = doc.getElementById('lscToast');
    if (toastNuevo) {
        document.body.appendChild(toastNuevo);
        _arrancarToast(toastNuevo, 7000);
    }
}

function _arrancarToast(toast, duracion) {
    toast.style.setProperty('--lsc-duration', (duracion / 1000) + 's');
    function dismiss() {
        toast.classList.add('lsc-panel--hiding');
        toast.addEventListener('animationend', () => toast.remove(), { once: true });
    }
    const timer = setTimeout(dismiss, duracion);
    const closeBtn = toast.querySelector('#lscClose');
    if (closeBtn) closeBtn.addEventListener('click', () => { clearTimeout(timer); dismiss(); });
}

// ─── HELPER: Parsear y aplicar nueva cola de videos ───────────────────
function _actualizarVideos(doc) {
    // Remover videos dinámicos viejos del DOM
    const contenedor = document.getElementById('contenedorVideo');
    if (contenedor) {
        // Eliminar todos los videos viejos excepto el videoBase
        contenedor.querySelectorAll('.video-item').forEach(el => el.remove());
        
        // Agregar los nuevos elementos de video desde el documento parseado
        doc.querySelectorAll('.video-item').forEach(el => {
            contenedor.appendChild(el.cloneNode(true));
        });
    }

    // Re-inicializar e iniciar reproducción
    indiceActual = 0;
    _inicializarVideos();

    if (videosCola.length > 0) {
        reproducirSiguiente();
    } else {
        mostrarNoEncontrado();
    }
}


// ─── MICRÓFONO ────────────────────────────────────────────────────────
const btnMic      = document.getElementById('btnMic');
const formulario  = document.getElementById('formulario');
const inputPalabra = document.getElementById('palabra');

let grabando   = false;
let procesando = false;

// ── Desbloquear autoplay en iOS Safari en el primer gesto táctil ─────
// iOS bloquea play() en cadenas async. El primer touchstart desbloquea
// los elementos de video y permite que play() funcione sin gesto directo.
document.addEventListener('touchstart', function _unlockIos() {
    if (videoBase) videoBase.play().catch(() => {});
    videoA.load();
    videoB.load();
    document.removeEventListener('touchstart', _unlockIos);
}, { once: true, passive: true });

// ── Verificar soporte de Web Speech API ───────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognition) {
    console.warn('Web Speech API no disponible — usando MediaRecorder como fallback.');
    iniciarModoMediaRecorder();
} else {
    iniciarModoSpeechRecognition();
}

// ─── MODO 1: Web Speech API (continuo, tiempo real) ───────────────────
function iniciarModoSpeechRecognition() {

    const recognition = new SpeechRecognition();
    recognition.lang           = 'es-CO';
    recognition.continuous     = true;
    recognition.interimResults = true;

    let transcripcionInterim = '';

    recognition.onresult = (event) => {
        let finalDelTurno = '';
        transcripcionInterim = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const texto = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalDelTurno += texto + ' ';
            } else {
                transcripcionInterim += texto;
            }
        }

        if (inputPalabra) {
            inputPalabra.value = transcripcionInterim || finalDelTurno.trim();
        }

        if (finalDelTurno.trim().length > 0) {
            enviarTextoAlBackend(finalDelTurno.trim());
        }
    };

    recognition.onerror = (event) => {
        if (event.error !== 'no-speech') {
            console.error('Error de reconocimiento:', event.error);
            mostrarNoEncontrado();
        }
    };

    recognition.onend = () => {
        if (grabando) {
            try { recognition.start(); } catch(e) {}
        } else {
            btnMic.innerHTML = iconoMic + ' Hablar';
            btnMic.classList.remove('btn-mic--activo');
        }
    };

    btnMic.addEventListener('click', () => {
        if (!grabando) {
            recognition.start();
            grabando = true;
            btnMic.innerHTML = iconoDetener + ' Escuchando\u2026';
            btnMic.classList.add('btn-mic--activo');
        } else {
            grabando = false;
            recognition.stop();
            btnMic.innerHTML = iconoMic + ' Hablar';
            btnMic.classList.remove('btn-mic--activo');
            if (inputPalabra) inputPalabra.value = '';
        }
    });
}

// ─── ENVIAR TEXTO AL BACKEND ──────────────────────────────────────────
function enviarTextoAlBackend(texto) {
    if (procesando) return;
    procesando = true;

    if (typeof GroseriasModal !== 'undefined' && GroseriasModal.verificarTexto(texto)) {
        const detectada = GroseriasModal.obtenerPalabraDetectada(texto);
        GroseriasModal.mostrar(detectada, 'texto');
        procesando = false;
        return;
    }

    const formData = new FormData(formulario);
    formData.set('palabra', texto);

    fetch(window.location.href, { method: 'POST', body: formData })
        .then(res => res.text())
        .then(html => {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            _actualizarUi(doc);
            _actualizarVideos(doc);
            procesando = false;
        })
        .catch(() => {
            procesando = false;
            mostrarNoEncontrado();
        });
}

// ─── ICONOS SVG ───────────────────────────────────────────────────────
const iconoMic = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 19v3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <rect x="9" y="2" width="6" height="13" rx="3"/>
</svg>`;

const iconoDetener = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round">
    <rect x="6" y="6" width="12" height="12" rx="2"/>
</svg>`;

// ─── MODO 2: Fallback con MediaRecorder (sin Web Speech API) ─────────
function iniciarModoMediaRecorder() {
    let mediaRecorder;
    let chunks = [];

    btnMic.addEventListener('click', async () => {
        if (procesando) return;

        if (!grabando) {
            chunks = [];
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
                procesando = true;

                const blob     = new Blob(chunks, { type: mediaRecorder.mimeType });
                const formData = new FormData(formulario);
                formData.append('audio', blob, 'audio.webm');

                btnMic.textContent = 'Procesando...';
                btnMic.disabled    = true;

                fetch(window.location.href, { method: 'POST', body: formData })
                    .then(res => res.text())
                    .then(html => {
                        const doc = new DOMParser().parseFromString(html, 'text/html');
                        _actualizarUi(doc);
                        _actualizarVideos(doc);
                        btnMic.innerHTML = iconoMic + ' Hablar';
                        btnMic.disabled  = false;
                        procesando       = false;
                    })
                    .catch(() => {
                        btnMic.innerHTML = iconoMic + ' Hablar';
                        btnMic.disabled  = false;
                        procesando       = false;
                        mostrarNoEncontrado();
                    });
            };

            mediaRecorder.start(100);
            grabando = true;
            btnMic.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/></svg> Detener`;

        } else {
            mediaRecorder.stop();
            grabando = false;
            btnMic.innerHTML = iconoMic + ' Hablar';
        }
    });
}

// ─── NOTIFICACIÓN "NO ENCONTRADO" ────────────────────────────────────
const notificacion = document.getElementById('notificacionNoEncontrado');

function mostrarNoEncontrado() {
    notificacion.style.display   = 'flex';
    notificacion.style.animation = 'none';
    notificacion.offsetHeight; // Fuerza reflow
    notificacion.style.animation = 'slideDown 0.3s ease';
    setTimeout(() => {
        notificacion.style.animation = 'slideUp 0.3s ease';
        notificacion.addEventListener('animationend', () => {
            notificacion.style.display = 'none';
        }, { once: true });
    }, 2700);
}

// ── Integración groserías ─────────────────────────────────────────────
GroseriasModal.onLimpiar(() => {
    if (inputPalabra) inputPalabra.value = '';
});

document.getElementById('formulario').addEventListener('submit', function(e) {
    e.preventDefault();
    const texto = inputPalabra?.value || '';
    if (GroseriasModal.verificarTexto(texto)) {
        const detectada = GroseriasModal.obtenerPalabraDetectada(texto);
        GroseriasModal.mostrar(detectada, 'texto');
    } else if (texto.trim().length > 0) {
        enviarTextoAlBackend(texto);
    }
});