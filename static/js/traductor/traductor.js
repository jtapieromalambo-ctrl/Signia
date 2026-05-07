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


    // ─── MICRÓFONO (reconocimiento continuo) ──────────────────────────
    const btnMic     = document.getElementById('btnMic');
    const formulario = document.getElementById('formulario');
    const inputPalabra = document.getElementById('palabra');

    let grabando   = false;
    let procesando = false;

    // ── Verificar soporte de Web Speech API ───────────────────────────
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        // Fallback al flujo antiguo con MediaRecorder si el navegador no soporta Web Speech API
        console.warn('Web Speech API no disponible, usando MediaRecorder como fallback.');
        iniciarModoMediaRecorder();
    } else {
        iniciarModoSpeechRecognition();
    }

    // ─── MODO 1: Web Speech API (continuo, tiempo real) ───────────────
    function iniciarModoSpeechRecognition() {

        const recognition = new SpeechRecognition();
        recognition.lang        = 'es-CO';   // Español colombiano
        recognition.continuous  = true;       // No se detiene entre pausas
        recognition.interimResults = true;    // Muestra texto parcial mientras habla

        let transcripcionInterim = '';

        // ── Actualiza el input con el texto parcial mientras habla ────
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

            // Muestra en el input lo que está diciendo en tiempo real
            if (inputPalabra) {
                inputPalabra.value = transcripcionInterim || finalDelTurno.trim();
            }

            // Cuando hay un fragmento final, lo envía al backend
            if (finalDelTurno.trim().length > 0) {
                enviarTextoAlBackend(finalDelTurno.trim());
            }
        };

        recognition.onerror = (event) => {
            // 'no-speech' es normal en pausas largas, no mostrar error
            if (event.error !== 'no-speech') {
                console.error('Error de reconocimiento:', event.error);
                mostrarNoEncontrado();
            }
        };

        recognition.onend = () => {
            // Si sigue en modo grabando, reinicia automáticamente
            // (el navegador puede terminar el recognition por inactividad)
            if (grabando) {
                try { recognition.start(); } catch(e) {}
            } else {
                btnMic.innerHTML = iconoMic + ' Hablar';
                btnMic.classList.remove('btn-mic--activo');
            }
        };

        btnMic.addEventListener('click', () => {
            if (!grabando) {
                // ── INICIAR ───────────────────────────────────────────
                recognition.start();
                grabando = true;
                btnMic.innerHTML = iconoDetener + ' Escuchando…';
                btnMic.classList.add('btn-mic--activo');
            } else {
                // ── DETENER ───────────────────────────────────────────
                grabando = false;
                recognition.stop();
                btnMic.innerHTML = iconoMic + ' Hablar';
                btnMic.classList.remove('btn-mic--activo');
                if (inputPalabra) inputPalabra.value = '';
            }
        });
    }

    // ─── ENVIAR TEXTO AL BACKEND ───────────────────────────────────────
    function enviarTextoAlBackend(texto) {

        if (procesando) return; // Evita llamadas solapadas
        procesando = true;

        // Verificar groserías antes de enviar
        if (typeof GroseriasModal !== 'undefined' && GroseriasModal.verificarTexto(texto)) {
            const detectada = GroseriasModal.obtenerPalabraDetectada(texto);
            GroseriasModal.mostrar(detectada, 'texto');
            procesando = false;
            return;
        }

        const formData = new FormData(formulario);
        formData.set('palabra', texto); // Sobrescribe con el texto reconocido

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

                // ── Refrescar toast LSC ───────────────────────────────
                const toastViejo = document.getElementById('lscToast');
                if (toastViejo) toastViejo.remove();

                const toastNuevo = doc.getElementById('lscToast');
                if (toastNuevo) {
                    document.body.appendChild(toastNuevo);
                    const DURATION_TOAST = 7000;
                    toastNuevo.style.setProperty('--lsc-duration', (DURATION_TOAST / 1000) + 's');
                    const closeBtn = toastNuevo.querySelector('#lscClose');
                    function dismissToast() {
                        toastNuevo.classList.add('lsc-panel--hiding');
                        toastNuevo.addEventListener('animationend', () => toastNuevo.remove(), { once: true });
                    }
                    let toastTimer = setTimeout(dismissToast, DURATION_TOAST);
                    if (closeBtn) {
                        closeBtn.addEventListener('click', () => { clearTimeout(toastTimer); dismissToast(); });
                    }
                }

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

                procesando = false;
            })
            .catch(() => {
                procesando = false;
                mostrarNoEncontrado();
            });
    }

    // ─── ICONOS SVG para el botón ──────────────────────────────────────
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

    // ─── MODO 2: Fallback con MediaRecorder (navegadores sin Web Speech API) ─
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

                    const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
                    const formData = new FormData(formulario);
                    formData.append('audio', blob, 'audio.webm');

                    btnMic.textContent = 'Procesando...';
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

                            const toastViejo = document.getElementById('lscToast');
                            if (toastViejo) toastViejo.remove();

                            const toastNuevo = doc.getElementById('lscToast');
                            if (toastNuevo) {
                                document.body.appendChild(toastNuevo);
                                const DURATION_TOAST = 7000;
                                toastNuevo.style.setProperty('--lsc-duration', (DURATION_TOAST / 1000) + 's');
                                const closeBtn = toastNuevo.querySelector('#lscClose');
                                function dismissToast() {
                                    toastNuevo.classList.add('lsc-panel--hiding');
                                    toastNuevo.addEventListener('animationend', () => toastNuevo.remove(), { once: true });
                                }
                                let toastTimer = setTimeout(dismissToast, DURATION_TOAST);
                                if (closeBtn) {
                                    closeBtn.addEventListener('click', () => { clearTimeout(toastTimer); dismissToast(); });
                                }
                            }

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
                btnMic.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-square" style="vertical-align: middle; margin-right: 4px;"><rect width="18" height="18" x="3" y="3" rx="2"/></svg> Detener`;

            } else {
                mediaRecorder.stop();
                grabando = false;
                btnMic.innerHTML = iconoMic + ' Hablar';
            }
        });
    }

    // ─── NOTIFICACIÓN "NO ENCONTRADO" ─────────────────────────────────
    const notificacion = document.getElementById('notificacionNoEncontrado');

    function mostrarNoEncontrado() {
        notificacion.style.display = 'flex';
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

    // ── Integración groserías ──────────────────────────────────────────
    GroseriasModal.onLimpiar(() => {
        if (inputPalabra) inputPalabra.value = '';
    });

    document.getElementById('formulario').addEventListener('submit', function(e) {
        const texto = inputPalabra?.value || '';
        if (GroseriasModal.verificarTexto(texto)) {
            e.preventDefault();
            const detectada = GroseriasModal.obtenerPalabraDetectada(texto);
            GroseriasModal.mostrar(detectada, 'texto');
        }
    });