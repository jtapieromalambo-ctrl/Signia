

    // ─── REFERENCIAS AL DOM ───────────────────────────────────────────
    const videoBase = document.getElementById('videoBase');
    const videoA    = document.getElementById('videoA');
    const videoB    = document.getElementById('videoB');

    // ─── DOUBLE BUFFERING ─────────────────────────────────────────────
    let activo       = videoA;
    let siguiente    = videoB;
    let indiceActual = 0;

    // ─── FUNCIÓN PRINCIPAL: reproducirSiguiente() ─────────────────────
    function reproducirSiguiente() {

        if (indiceActual < colaVideos.length) {

            siguiente.src = colaVideos[indiceActual];
            siguiente.load();

            siguiente.oncanplay = () => {

                // Oculta el video base solo cuando el primer video ya está listo
                if (indiceActual === 0 && videoBase) {
                    videoBase.style.display = 'none';
                }

                activo.style.display = 'none';
                activo.pause();

                siguiente.style.display = 'block';
                siguiente.play().catch(() => {
                    setTimeout(() => siguiente.play().catch(() => {}), 300);
                });

                // Swap de roles entre buffers
                [activo, siguiente] = [siguiente, activo];
                indiceActual++;

                // Precarga el próximo video en segundo plano
                if (indiceActual < colaVideos.length) {
                    siguiente.src = colaVideos[indiceActual];
                    siguiente.load();
                }
            };

        } else {
            // ─── COLA TERMINADA: vuelve al video base ─────────────────
            indiceActual = 0;
            activo.style.display = 'none';
            activo.pause();

            if (videoBase) {
                videoBase.style.display = 'block';
                videoBase.play().catch(() => {});
            }
        }
    }

    // ─── EVENTOS "ENDED" ──────────────────────────────────────────────
    videoA.addEventListener('ended', reproducirSiguiente);
    videoB.addEventListener('ended', reproducirSiguiente);

    // Arranca si Django ya envió videos (búsqueda por texto)
    if (colaVideos.length > 0) reproducirSiguiente();


    // ─── MICRÓFONO ────────────────────────────────────────────────────
    const btnMic     = document.getElementById('btnMic');
    const formulario = document.getElementById('formulario');
    let mediaRecorder;
    let grabando   = false;
    let chunks     = [];
    let procesando = false;

    btnMic.addEventListener('click', async () => {

        if (procesando) return;

        if (!grabando) {
            // ── INICIO DE GRABACIÓN ───────────────────────────────────
            chunks = [];

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = () => {
    procesando = true;

    const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
    const formData = new FormData(formulario);
    formData.append('audio', blob, 'audio.webm');

    btnMic.textContent = '⏳ Procesando...';
    btnMic.disabled = true;

    fetch(window.location.href, { method: 'POST', body: formData })
    .then(res => res.text())
    .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

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
            indiceActual = 0;
            colaVideos.length = 0;
            nuevasColas.forEach(url => colaVideos.push(url));

            activo.pause();
            activo.style.display  = 'none';
            activo.oncanplay      = null;
            siguiente.oncanplay   = null;

            activo    = videoA;
            siguiente = videoB;

            reproducirSiguiente();
        } else {
            mostrarNoEncontrado();
        }

        btnMic.textContent = '🎤 Hablar';
        btnMic.disabled    = false;
        procesando         = false;
    })
    .catch(() => {
        btnMic.textContent = '🎤 Hablar';
        btnMic.disabled    = false;
        procesando         = false;
        mostrarNoEncontrado();
    });
};

            mediaRecorder.start(100);
            grabando = true;
            btnMic.textContent = '⏹ Detener';

        } else {
            // ── DETENER GRABACIÓN ─────────────────────────────────────
            mediaRecorder.stop();
            grabando = false;
            btnMic.textContent = '🎤 Hablar';
        }
    });
    // ─── NOTIFICACION "NO ENCONTRADO" ──────────────────────────────────────────
const notificacion = document.getElementById('notificacionNoEncontrado');

function mostrarNoEncontrado() {
    notificacion.style.display = 'flex';
    notificacion.style.animation = 'none';
    // Fuerza reflow para reiniciar la animación
    notificacion.offsetHeight;
    notificacion.style.animation = 'slideDown 0.3s ease';
     setTimeout(() => {
        notificacion.style.animation = 'slideUp 0.3s ease';
        notificacion.addEventListener('animationend', () => {
            notificacion.style.display = 'none';
        }, { once: true }); 
    }, 2700);
}