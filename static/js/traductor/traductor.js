// ─── REFERENCIAS AL DOM ───────────────────────────────────────────────
const videoBase = document.getElementById('videoBase');
const videoA    = document.getElementById('videoA');
const videoB    = document.getElementById('videoB');

// ─── DOUBLE BUFFERING ─────────────────────────────────────────────────
let activo       = videoA;
let siguiente    = videoB;
let indiceActual = 0;

// ─── CROSS-FADE: mostrar elNuevo sobre elViejo sin parpadeo ──────────
// Funciona en escritorio y móvil (iOS Safari + Android Chrome).
// Muestra el nuevo video (opacity 0 → 1) y desvanece el viejo (1 → 0)
// en el mismo frame de pintura, eliminando el flash negro entre videos.
function _mostrarVideo(elNuevo, elViejo, esElPrimero) {
    // Preparar nuevo: invisible pero en el DOM para que el browser lo pinte
    elNuevo.style.opacity = '0';
    elNuevo.style.display = 'block';

    elNuevo.play()
        .then(() => {
            requestAnimationFrame(() => {
                // Fade in del nuevo
                elNuevo.style.transition = 'opacity 0.2s ease';
                elNuevo.style.opacity    = '1';

                // Pausar y fade out del viejo simultáneamente
                elViejo.pause();
                elViejo.style.transition = 'opacity 0.2s ease';
                elViejo.style.opacity    = '0';

                if (esElPrimero && videoBase) {
                    videoBase.style.transition = 'opacity 0.2s ease';
                    videoBase.style.opacity    = '0';
                }

                // Limpiar después de la transición
                setTimeout(() => {
                    elViejo.style.display    = 'none';
                    elViejo.style.transition = '';
                    elViejo.style.opacity    = '';

                    if (esElPrimero && videoBase) {
                        videoBase.style.display    = 'none';
                        videoBase.style.transition = '';
                        videoBase.style.opacity    = '';
                    }

                    elNuevo.style.transition = '';
                }, 220);
            });
        })
        .catch(() => {
            // Móvil: play() bloqueado (sin gesto de usuario) — mostrar de todas formas
            elNuevo.style.opacity = '1';
            elViejo.pause();
            elViejo.style.display = 'none';
            if (esElPrimero && videoBase) videoBase.style.display = 'none';
            // Reintentar en 400ms (iOS suele aceptar tras breve pausa)
            setTimeout(() => elNuevo.play().catch(() => {}), 400);
        });
}

// ─── FUNCIÓN PRINCIPAL: reproducirSiguiente() ─────────────────────────
function reproducirSiguiente() {

    if (indiceActual < colaVideos.length) {
        const elNuevo     = siguiente;
        const elViejo     = activo;
        const esElPrimero = (indiceActual === 0);
        const url         = colaVideos[indiceActual];

        elNuevo.oncanplay = () => {
            elNuevo.oncanplay = null; // evitar doble disparo

            // Swap de roles
            [activo, siguiente] = [elNuevo, elViejo];
            indiceActual++;

            // Cross-fade sin parpadeo
            _mostrarVideo(elNuevo, elViejo, esElPrimero);

            // Precarga el próximo DESPUÉS de que el viejo esté oculto
            // (evita cambiar src en un elemento aún visible durante fade-out)
            setTimeout(() => {
                if (indiceActual < colaVideos.length) {
                    siguiente.src = colaVideos[indiceActual];
                    siguiente.load();
                }
            }, 230);
        };

        elNuevo.src = url;
        elNuevo.load();

    } else {
        // ─── COLA TERMINADA: vuelve al video base con cross-fade ──────
        indiceActual = 0;
        const elViejo = activo;

        if (videoBase) {
            videoBase.style.opacity = '0';
            videoBase.style.display = 'block';
            videoBase.play().catch(() => {});

            requestAnimationFrame(() => {
                videoBase.style.transition = 'opacity 0.2s ease';
                videoBase.style.opacity    = '1';

                elViejo.pause();
                elViejo.style.transition = 'opacity 0.2s ease';
                elViejo.style.opacity    = '0';

                setTimeout(() => {
                    elViejo.style.display    = 'none';
                    elViejo.style.transition = '';
                    elViejo.style.opacity    = '';
                    videoBase.style.transition = '';
                }, 220);
            });
        } else {
            elViejo.pause();
            elViejo.style.display = 'none';
        }
    }
}

// ─── EVENTOS "ENDED" ──────────────────────────────────────────────────
videoA.addEventListener('ended', reproducirSiguiente);
videoB.addEventListener('ended', reproducirSiguiente);

// Arranca si Django ya envió videos (búsqueda por texto en carga inicial)
if (colaVideos.length > 0) reproducirSiguiente();


// ─── HELPER: Actualizar UI desde respuesta AJAX ───────────────────────
// Consolida 3 updates (lsc-resultado + label + toast) en un solo lugar,
// eliminando duplicación entre enviarTextoAlBackend y MediaRecorder.
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
    let nuevasColas = [];
    doc.querySelectorAll('script').forEach(script => {
        const match = script.textContent.match(/const colaVideos\s*=\s*\[([\s\S]*?)\];/);
        if (match) {
            const urlsTexto = match[1].trim();
            if (urlsTexto.length > 0) {
                nuevasColas = urlsTexto
                    .split(',')
                    .map(s => s.trim().replace(/['"]/g, ''))
                    .filter(s => s.length > 0);
            }
        }
    });

    if (nuevasColas.length > 0) {
        // Cancelar cargas/callbacks pendientes
        activo.oncanplay  = null;
        siguiente.oncanplay = null;
        activo.pause();

        indiceActual = 0;
        colaVideos.length = 0;
        nuevasColas.forEach(url => colaVideos.push(url));

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