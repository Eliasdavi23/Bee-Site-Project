/**
 * BeeHUD - Sistema Unificado de Feedback Visual, Toasts e Modais para Bee Gráfica
 * 
 * 100% Localhost, sem CDNs, sem dependências externas.
 * Fornece:
 * - Toasts animados de feedback rápido (sucesso, erro, aviso, info)
 * - Diálogos interativos de confirmação assíncronos (substitui o confirm nativo)
 * - Modais modernos de alerta (substitui o alert nativo)
 * - Indicadores visuais de carregamento e progresso
 * - Interceptação opcional de window.alert e window.confirm
 */

(function () {
    const ICONS = {
        success: `<svg class="w-5 h-5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        error: `<svg class="w-5 h-5 text-rose-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        warning: `<svg class="w-5 h-5 text-yellow-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
        info: `<svg class="w-5 h-5 text-sky-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        question: `<svg class="w-6 h-6 text-yellow-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        danger: `<svg class="w-6 h-6 text-rose-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>`,
    };

    let toastContainer = null;
    let loadingElement = null;

    function garantirContainerToasts() {
        if (toastContainer && document.body.contains(toastContainer)) return toastContainer;
        toastContainer = document.getElementById("bee-hud-toasts");
        if (!toastContainer) {
            toastContainer = document.createElement("div");
            toastContainer.id = "bee-hud-toasts";
            toastContainer.className = "fixed top-5 right-5 z-[10000] flex flex-col gap-2.5 pointer-events-none max-w-sm w-[calc(100vw-2.5rem)] no-print print:hidden";
            document.body.appendChild(toastContainer);
        }
        return toastContainer;
    }

    function escaparTexto(str) {
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    /**
     * Exibe um Toast na tela
     */
    function toast(opcoes = {}) {
        const {
            titulo = "",
            mensagem = "",
            tipo = "info", // "success" | "error" | "warning" | "info"
            duracao = 4500,
        } = typeof opcoes === "string" ? { mensagem: opcoes } : opcoes;

        const container = garantirContainerToasts();
        const card = document.createElement("div");
        card.className = "bee-hud-toast pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white shadow-2xl relative overflow-hidden transition-all duration-300 ease-out transform translate-x-full opacity-0";

        // Cor da borda lateral indicativa
        const bordaCores = {
            success: "border-l-4 border-l-emerald-500",
            error: "border-l-4 border-l-rose-500",
            warning: "border-l-4 border-l-yellow-400",
            info: "border-l-4 border-l-sky-400",
        };
        card.classList.add(...(bordaCores[tipo] || bordaCores.info).split(" "));

        const iconHtml = ICONS[tipo] || ICONS.info;
        const tituloHtml = titulo ? `<strong class="block text-xs font-black uppercase tracking-wider text-zinc-100 mb-0.5">${escaparTexto(titulo)}</strong>` : "";
        const mensagemHtml = `<p class="text-xs text-zinc-300 leading-relaxed break-words">${escaparTexto(mensagem).replace(/\n/g, "<br/>")}</p>`;

        card.innerHTML = `
            ${iconHtml}
            <div class="flex-1 min-w-0 pr-1">
                ${tituloHtml}
                ${mensagemHtml}
            </div>
            <button type="button" class="text-zinc-500 hover:text-zinc-200 text-sm font-bold leading-none p-1 transition cursor-pointer" title="Fechar">✕</button>
            <div class="bee-hud-toast-bar absolute bottom-0 left-0 h-[2px] bg-yellow-400/80 transition-all"></div>
        `;

        const btnFechar = card.querySelector("button");
        const bar = card.querySelector(".bee-hud-toast-bar");

        let timerId = null;
        let tempoRestante = duracao;
        let tempoInicio = Date.now();

        function fecharToast() {
            if (timerId) clearTimeout(timerId);
            card.classList.remove("translate-x-0", "opacity-100");
            card.classList.add("translate-x-full", "opacity-0");
            setTimeout(() => {
                if (card.parentNode) card.parentNode.removeChild(card);
            }, 300);
        }

        btnFechar.addEventListener("click", fecharToast);

        function iniciarTimer() {
            if (duracao <= 0) return;
            tempoInicio = Date.now();
            bar.style.transition = `width ${tempoRestante}ms linear`;
            bar.style.width = "0%";
            timerId = setTimeout(fecharToast, tempoRestante);
        }

        function pausarTimer() {
            if (timerId) {
                clearTimeout(timerId);
                timerId = null;
                const decorrido = Date.now() - tempoInicio;
                tempoRestante = Math.max(0, tempoRestante - decorrido);
                const pct = (tempoRestante / duracao) * 100;
                bar.style.transition = "none";
                bar.style.width = `${pct}%`;
            }
        }

        card.addEventListener("mouseenter", pausarTimer);
        card.addEventListener("mouseleave", () => {
            if (tempoRestante > 0) iniciarTimer();
        });

        bar.style.width = "100%";
        container.appendChild(card);

        // Força repaint para ativar animação de entrada
        requestAnimationFrame(() => {
            card.classList.remove("translate-x-full", "opacity-0");
            card.classList.add("translate-x-0", "opacity-100");
            iniciarTimer();
        });

        return { close: fecharToast };
    }

    /**
     * Diálogo moderno assíncrono de Confirmação (Promise<boolean>)
     */
    function confirmDialog(opcoes = {}) {
        return new Promise((resolve) => {
            const {
                titulo = "Confirmar Ação",
                mensagem = "Tem certeza que deseja prosseguir?",
                confirmTexto = "Confirmar",
                cancelarTexto = "Cancelar",
                tipo = "question", // "question" | "danger" | "warning"
            } = typeof opcoes === "string" ? { mensagem: opcoes } : opcoes;

            const backdrop = document.createElement("div");
            backdrop.className = "bee-hud-backdrop fixed inset-0 bg-black/80 backdrop-blur-sm z-[10020] flex items-center justify-center p-4 transition-opacity duration-200 opacity-0 no-print print:hidden";

            const btnConfirmClass = tipo === "danger"
                ? "bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30"
                : "bg-yellow-400 hover:bg-yellow-300 text-black shadow-lg shadow-yellow-500/20";

            const iconHtml = ICONS[tipo] || ICONS.question;

            backdrop.innerHTML = `
                <div class="bee-hud-dialog bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-6 max-w-md w-full space-y-4 text-white transform scale-95 opacity-0 transition-all duration-200 ease-out">
                    <div class="flex items-start gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-zinc-800 border border-zinc-700/60 flex items-center justify-center shrink-0">
                            ${iconHtml}
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 class="text-base font-black text-white tracking-wide">${escaparTexto(titulo)}</h3>
                            <p class="text-xs text-zinc-300 mt-1 leading-relaxed break-words">${escaparTexto(mensagem).replace(/\n/g, "<br/>")}</p>
                        </div>
                    </div>
                    <div class="flex justify-end items-center gap-2.5 pt-3 border-t border-zinc-800/80">
                        <button type="button" class="btn-cancel px-4 py-2 rounded-xl border border-zinc-800 text-zinc-300 hover:bg-zinc-800 text-xs font-bold transition cursor-pointer">
                            ${escaparTexto(cancelarTexto)}
                        </button>
                        <button type="button" class="btn-confirm px-5 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${btnConfirmClass}">
                            ${escaparTexto(confirmTexto)}
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(backdrop);
            const dialog = backdrop.querySelector(".bee-hud-dialog");
            const btnConfirm = backdrop.querySelector(".btn-confirm");
            const btnCancel = backdrop.querySelector(".btn-cancel");

            function fechar(resultado) {
                document.removeEventListener("keydown", onKeyDown);
                backdrop.classList.add("opacity-0");
                dialog.classList.remove("scale-100", "opacity-100");
                dialog.classList.add("scale-95", "opacity-0");
                setTimeout(() => {
                    if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                    resolve(resultado);
                }, 180);
            }

            function onKeyDown(e) {
                if (e.key === "Escape") {
                    e.preventDefault();
                    fechar(false);
                } else if (e.key === "Enter" && document.activeElement !== btnCancel) {
                    e.preventDefault();
                    fechar(true);
                }
            }

            btnConfirm.addEventListener("click", () => fechar(true));
            btnCancel.addEventListener("click", () => fechar(false));
            backdrop.addEventListener("click", (e) => {
                if (e.target === backdrop) fechar(false);
            });
            document.addEventListener("keydown", onKeyDown);

            requestAnimationFrame(() => {
                backdrop.classList.remove("opacity-0");
                backdrop.classList.add("opacity-100");
                dialog.classList.remove("scale-95", "opacity-0");
                dialog.classList.add("scale-100", "opacity-100");
                btnConfirm.focus();
            });
        });
    }

    /**
     * Modal moderno de Alerta informativo (Promise<void>)
     */
    function alertDialog(opcoes = {}) {
        return new Promise((resolve) => {
            const {
                titulo = "Aviso do Sistema",
                mensagem = "",
                tipo = "info", // "info" | "warning" | "error" | "success"
                botaoTexto = "Entendido",
            } = typeof opcoes === "string" ? { mensagem: opcoes } : opcoes;

            const backdrop = document.createElement("div");
            backdrop.className = "bee-hud-backdrop fixed inset-0 bg-black/80 backdrop-blur-sm z-[10020] flex items-center justify-center p-4 transition-opacity duration-200 opacity-0 no-print print:hidden";

            const iconHtml = ICONS[tipo] || ICONS.info;

            backdrop.innerHTML = `
                <div class="bee-hud-dialog bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-6 max-w-md w-full space-y-4 text-white transform scale-95 opacity-0 transition-all duration-200 ease-out">
                    <div class="flex items-start gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-zinc-800 border border-zinc-700/60 flex items-center justify-center shrink-0">
                            ${iconHtml}
                        </div>
                        <div class="flex-1 min-w-0">
                            <h3 class="text-base font-black text-white tracking-wide">${escaparTexto(titulo)}</h3>
                            <div class="text-xs text-zinc-300 mt-1 leading-relaxed break-words max-h-60 overflow-y-auto">${escaparTexto(mensagem).replace(/\n/g, "<br/>")}</div>
                        </div>
                    </div>
                    <div class="flex justify-end pt-3 border-t border-zinc-800/80">
                        <button type="button" class="btn-ok px-6 py-2 rounded-xl bg-yellow-400 hover:bg-yellow-300 text-black text-xs font-bold transition cursor-pointer shadow-lg shadow-yellow-500/20">
                            ${escaparTexto(botaoTexto)}
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(backdrop);
            const dialog = backdrop.querySelector(".bee-hud-dialog");
            const btnOk = backdrop.querySelector(".btn-ok");

            function fechar() {
                document.removeEventListener("keydown", onKeyDown);
                backdrop.classList.add("opacity-0");
                dialog.classList.remove("scale-100", "opacity-100");
                dialog.classList.add("scale-95", "opacity-0");
                setTimeout(() => {
                    if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                    resolve();
                }, 180);
            }

            function onKeyDown(e) {
                if (e.key === "Escape" || e.key === "Enter") {
                    e.preventDefault();
                    fechar();
                }
            }

            btnOk.addEventListener("click", fechar);
            backdrop.addEventListener("click", (e) => {
                if (e.target === backdrop) fechar();
            });
            document.addEventListener("keydown", onKeyDown);

            requestAnimationFrame(() => {
                backdrop.classList.remove("opacity-0");
                backdrop.classList.add("opacity-100");
                dialog.classList.remove("scale-95", "opacity-0");
                dialog.classList.add("scale-100", "opacity-100");
                btnOk.focus();
            });
        });
    }

    /**
     * Indicador visual de Carregamento Flutuante
     */
    function showLoading(mensagem = "Processando...") {
        if (!loadingElement) {
            loadingElement = document.createElement("div");
            loadingElement.id = "bee-hud-loading";
            loadingElement.className = "fixed bottom-5 left-5 z-[10030] bg-zinc-900 border border-yellow-400/50 rounded-full px-4 py-2.5 flex items-center gap-2.5 shadow-2xl text-white text-xs font-bold no-print print:hidden animate-pulse";
            loadingElement.innerHTML = `
                <svg class="animate-spin w-4 h-4 text-yellow-400 shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span id="bee-hud-loading-txt" class="tracking-wide">${escaparTexto(mensagem)}</span>
            `;
            document.body.appendChild(loadingElement);
        } else {
            const span = document.getElementById("bee-hud-loading-txt");
            if (span) span.textContent = mensagem;
            loadingElement.classList.remove("hidden");
        }

        return function fecharLoading() {
            if (loadingElement && loadingElement.parentNode) {
                loadingElement.classList.add("hidden");
            }
        };
    }

    function hideLoading() {
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.classList.add("hidden");
        }
    }

    // Objeto central do HUD
    const BeeHUD = {
        toast,
        confirm: confirmDialog,
        alert: alertDialog,
        loading: showLoading,
        hideLoading,

        success(msg, titulo = "Sucesso") {
            return toast({ tipo: "success", titulo, mensagem: msg });
        },
        error(msg, titulo = "Erro") {
            return toast({ tipo: "error", titulo, mensagem: msg });
        },
        warning(msg, titulo = "Atenção") {
            return toast({ tipo: "warning", titulo, mensagem: msg });
        },
        info(msg, titulo = "Informação") {
            return toast({ tipo: "info", titulo, mensagem: msg });
        },
    };

    window.BeeHUD = BeeHUD;

    // Sobrescreve alert e confirm do navegador para redirecionar ao BeeHUD de forma elegante
    window.alert = function (msg) {
        return alertDialog({ mensagem: String(msg || "") });
    };

    // Para confirm síncrono mantido por compatibilidade rápida
    const confirmOriginal = window.confirm;
    window.confirmOriginal = confirmOriginal;
})();
