/**
 * groserias.js — Signia
 * Detección de palabras y señas inapropiadas.
 * Usado por: traductor.html y reconocimiento.html
 *
 * API pública:
 *   GroseriasModal.verificarTexto(texto)   → true si es grosero
 *   GroseriasModal.verificarSena(sena)     → true si la seña está bloqueada
 *   GroseriasModal.mostrar(palabra, tipo)  → muestra el modal
 *   GroseriasModal.onLimpiar(callback)     → registra acción del botón "Limpiar"
 */

const GroseriasModal = (() => {

    // ─── Lista de palabras bloqueadas ───────────────────────────────────────
    // Agrega o quita palabras según las necesidades del proyecto.
    const PALABRAS_BLOQUEADAS = [
        // Groserías generales en español
        "mierda", "puta", "puto", "hijueputa", "hijueputa",
        "culo", "pendejo", "pendeja", "idiota", "estupido",
        "estupida", "cabron", "cabrona", "chinga", "chingada",
        "verga", "coño", "joder", "hostia", "gilipollas",
        "marica", "maricón", "maricon", "hdp", "hp",
        "carajo", "malparido", "malparida", "gonorrea",
        "guevon", "huevon", "mamada", "mamadas",
        // Insultos/discriminación
        "idiota", "imbécil", "imbecil", "retrasado", "retrasada",
        "mongolo", "subnormal",
    ];

    // ─── Señas bloqueadas (nombre exacto que devuelve el modelo) ────────────
    // Agrega las etiquetas de señas que consideres inapropiadas.
    const SENAS_BLOQUEADAS = [
        // Ejemplo: "insulto_1", "groseria_a"
        // Ajusta estos valores según las clases de tu RandomForestClassifier
    ];

    // ─── Normalizar texto (quitar tildes, minúsculas) ───────────────────────
    function normalizar(texto) {
        return texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9\s]/g, " ");
    }

    // ─── Verificar texto escrito / hablado ──────────────────────────────────
    function verificarTexto(texto) {
        if (!texto || texto.trim() === "") return false;
        const palabras = normalizar(texto).split(/\s+/);
        return palabras.some(p => PALABRAS_BLOQUEADAS.includes(p));
    }

    // Devuelve la primera palabra bloqueada encontrada (para mostrar en badge)
    function obtenerPalabraDetectada(texto) {
        const palabras = normalizar(texto).split(/\s+/);
        return palabras.find(p => PALABRAS_BLOQUEADAS.includes(p)) || "—";
    }

    // ─── Verificar seña reconocida ───────────────────────────────────────────
    function verificarSena(nombreSena) {
        if (!nombreSena) return false;
        return SENAS_BLOQUEADAS.includes(nombreSena.trim().toLowerCase());
    }

    // ─── Callback para el botón "Limpiar" ───────────────────────────────────
    let _callbackLimpiar = null;
    function onLimpiar(callback) {
        _callbackLimpiar = callback;
    }

    // ─── Mostrar modal ───────────────────────────────────────────────────────
    // @param detectado  string — palabra o nombre de seña detectada
    // @param tipo       "texto" | "sena"
    function mostrar(detectado, tipo = "texto") {
        const overlay  = document.getElementById("modalGroseria");
        const badge    = document.getElementById("modalGroseriaPalabra");
        const desc     = document.getElementById("modalGroseriaDesc");

        if (!overlay) {
            console.warn("[Signia] Modal de groserías no encontrado en el DOM.");
            return;
        }

        // Personalizar texto según el origen
        if (tipo === "sena") {
            desc.textContent =
                "Signia detectó una seña inapropiada. Este tipo de contenido no está permitido en la plataforma.";
            badge.textContent = detectado || "seña no permitida";
        } else {
            desc.textContent =
                "Signia detectó una palabra inapropiada. Este tipo de contenido no está permitido en la plataforma.";
            badge.textContent = detectado || "—";
        }

        overlay.classList.remove("mg-oculto");
    }

    // ─── Ocultar modal ───────────────────────────────────────────────────────
    function ocultar() {
        const overlay = document.getElementById("modalGroseria");
        if (overlay) overlay.classList.add("mg-oculto");
    }

    // ─── Inicializar eventos del modal ───────────────────────────────────────
    function init() {
        document.addEventListener("DOMContentLoaded", () => {
            const btnCerrar   = document.getElementById("btnCerrarModal");
            const btnEntendido = document.getElementById("btnEntendido");
            const btnLimpiar  = document.getElementById("btnLimpiar");
            const overlay     = document.getElementById("modalGroseria");

            if (!overlay) return;

            // Cerrar con X o "Entendido"
            [btnCerrar, btnEntendido].forEach(btn => {
                if (btn) btn.addEventListener("click", ocultar);
            });

            // Botón "Limpiar": ejecuta callback registrado + cierra modal
            if (btnLimpiar) {
                btnLimpiar.addEventListener("click", () => {
                    if (typeof _callbackLimpiar === "function") {
                        _callbackLimpiar();
                    }
                    ocultar();
                });
            }

            // Clic fuera del box → cerrar
            overlay.addEventListener("click", (e) => {
                if (e.target === overlay) ocultar();
            });

            // ESC → cerrar
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape") ocultar();
            });
        });
    }

    init();

    // ─── API pública ─────────────────────────────────────────────────────────
    return {
        verificarTexto,
        verificarSena,
        obtenerPalabraDetectada,
        mostrar,
        ocultar,
        onLimpiar,
    };

})();