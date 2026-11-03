/**
 * Modal global de envio rápido de WhatsApp + IA (usado em Pedidos, Orçamentos e Clientes).
 * 100% Localhost — sem dependências externas.
 */
(function () {
    let estadoModal = {
        tipo: "status_pedido",
        pedido_id: null,
        cliente_id: null,
        linkAtual: "",
        telefoneValido: false,
    };

    function garantirModalNoDOM() {
        if (document.getElementById("bee-wa-modal")) return;

        const wrapper = document.createElement("div");
        wrapper.id = "bee-wa-modal";
        wrapper.className = "fixed inset-0 bg-slate-950/80 backdrop-blur-sm hidden items-center justify-center z-[9998] p-4 no-print print:hidden";
        wrapper.innerHTML = `
            <div class="bg-slate-900 border border-slate-800 w-full max-w-xl rounded-2xl shadow-2xl p-6 space-y-4 text-slate-100">
                <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                    <div class="flex items-center gap-2.5">
                        <span class="text-2xl">💬</span>
                        <div>
                            <h3 class="text-lg font-black text-emerald-400">Enviar WhatsApp com IA</h3>
                            <p id="bee-wa-destinatario" class="text-xs text-slate-400">Carregando destinatário...</p>
                        </div>
                    </div>
                    <button type="button" id="bee-wa-fechar" class="text-slate-400 hover:text-white text-xl font-bold px-2 cursor-pointer">✕</button>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-[11px] font-bold text-slate-400 uppercase mb-1">Tipo de Mensagem</label>
                        <select id="bee-wa-tipo" class="w-full bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl px-3 py-2.5 outline-none focus:border-emerald-400">
                            <option value="status_pedido">📦 Status do Pedido</option>
                            <option value="cobranca">💰 Lembrete de Pagamento</option>
                            <option value="orcamento">📋 Envio de Orçamento</option>
                            <option value="saudacao">👋 Saudação / Mensagem Livre</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-slate-400 uppercase mb-1">Instrução extra para a IA (opcional)</label>
                        <div class="flex gap-1.5">
                            <input type="text" id="bee-wa-instrucao" maxlength="250" placeholder="Ex.: avisar que fechamos às 18h" class="flex-1 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl px-3 py-2 outline-none focus:border-amber-400">
                            <button type="button" id="bee-wa-gerar-ia" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black text-xs px-3 py-2 rounded-xl transition cursor-pointer whitespace-nowrap" title="Gerar/reescrever com IA">
                                ✨ IA
                            </button>
                        </div>
                    </div>
                </div>

                <div>
                    <div class="flex justify-between items-center mb-1">
                        <label class="text-[11px] font-bold text-slate-400 uppercase">Mensagem (pode editar antes de enviar)</label>
                        <span id="bee-wa-origem-badge" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">Modelo pronto</span>
                    </div>
                    <textarea id="bee-wa-texto" rows="7" maxlength="1500" class="w-full bg-slate-950 border border-slate-700 text-slate-100 text-sm rounded-xl p-3 outline-none focus:border-emerald-400 leading-relaxed"></textarea>
                </div>

                <div id="bee-wa-alerta" class="hidden text-xs rounded-xl p-3 border"></div>

                <div class="flex flex-wrap justify-between items-center gap-2 pt-2 border-t border-slate-800">
                    <a href="/atendimento" class="text-xs text-amber-400 hover:underline font-bold">Abrir Painel de Atendimento →</a>
                    <div class="flex gap-2">
                        <button type="button" id="bee-wa-cancelar" class="px-4 py-2 rounded-xl border border-slate-700 text-slate-300 text-xs font-bold hover:bg-slate-800 transition cursor-pointer">Cancelar</button>
                        <button type="button" id="bee-wa-enviar" class="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-black transition cursor-pointer shadow-lg">
                            📲 Enviar no WhatsApp
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(wrapper);

        document.getElementById("bee-wa-fechar").addEventListener("click", fecharModalWhatsApp);
        document.getElementById("bee-wa-cancelar").addEventListener("click", fecharModalWhatsApp);
        document.getElementById("bee-wa-tipo").addEventListener("change", (e) => {
            estadoModal.tipo = e.target.value;
            carregarRascunho(false);
        });
        document.getElementById("bee-wa-gerar-ia").addEventListener("click", () => carregarRascunho(true));
        document.getElementById("bee-wa-enviar").addEventListener("click", confirmarEnvioModal);
    }

    function mostrarAlerta(msg, erro = false) {
        const box = document.getElementById("bee-wa-alerta");
        if (!box) return;
        if (!msg) {
            box.classList.add("hidden");
            return;
        }
        box.textContent = msg;
        box.className = erro
            ? "text-xs rounded-xl p-3 border bg-rose-950/60 border-rose-500/40 text-rose-200"
            : "text-xs rounded-xl p-3 border bg-emerald-950/60 border-emerald-500/40 text-emerald-200";
    }

    async function carregarRascunho(usarIA = false) {
        const txt = document.getElementById("bee-wa-texto");
        const dest = document.getElementById("bee-wa-destinatario");
        const badge = document.getElementById("bee-wa-origem-badge");
        const btnIA = document.getElementById("bee-wa-gerar-ia");
        const instrucao = document.getElementById("bee-wa-instrucao")?.value || "";

        mostrarAlerta("");
        if (txt) txt.value = "Gerando mensagem...";
        if (btnIA) btnIA.disabled = true;

        try {
            const resp = await fetch("/api/whatsapp/rascunho", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tipo: estadoModal.tipo,
                    pedido_id: estadoModal.pedido_id,
                    cliente_id: estadoModal.cliente_id,
                    usar_ia: Boolean(usarIA),
                    instrucao_extra: instrucao,
                }),
            });
            const dados = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                throw new Error(dados.detail || "Não foi possível preparar a mensagem.");
            }
            estadoModal.cliente_id = dados.cliente_id || estadoModal.cliente_id;
            estadoModal.linkAtual = dados.link || "";
            estadoModal.telefoneValido = Boolean(dados.telefone_valido);

            if (txt) txt.value = dados.texto || "";
            if (dest) {
                dest.textContent = `${dados.cliente_nome || "Cliente"} • ${dados.telefone_exibicao || "Sem telefone"}`;
            }
            if (badge) {
                badge.textContent = dados.origem === "ia" ? "✨ Escrito pela IA" : "⚡ Modelo rápido";
                badge.className = dados.origem === "ia"
                    ? "text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30"
                    : "text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300";
            }
            if (!estadoModal.telefoneValido) {
                mostrarAlerta("Este cliente está sem WhatsApp válido no cadastro. Cadastre o telefone com DDD em Clientes.", true);
            }
        } catch (err) {
            if (txt) txt.value = "";
            mostrarAlerta(err.message || "Erro ao gerar rascunho.", true);
        } finally {
            if (btnIA) btnIA.disabled = false;
        }
    }

    async function confirmarEnvioModal() {
        const texto = (document.getElementById("bee-wa-texto")?.value || "").trim();
        const btn = document.getElementById("bee-wa-enviar");
        if (!texto) {
            mostrarAlerta("Digite uma mensagem antes de enviar.", true);
            return;
        }
        if (btn) btn.disabled = true;

        try {
            const resp = await fetch("/api/whatsapp/enviar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    texto: texto,
                    pedido_id: estadoModal.pedido_id,
                    cliente_id: estadoModal.cliente_id,
                    assumir_conversa: false,
                }),
            });
            const dados = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                throw new Error(dados.detail || "Falha ao enviar mensagem.");
            }

            if (dados.enviado) {
                mostrarAlerta("Mensagem enviada automaticamente pelo servidor! ✅", false);
                setTimeout(fecharModalWhatsApp, 900);
            } else if (dados.link) {
                window.open(dados.link, "_blank", "noopener,noreferrer");
                fecharModalWhatsApp();
            }
        } catch (err) {
            mostrarAlerta(err.message || "Erro ao enviar.", true);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function abrirModalWhatsApp(opcoes = {}) {
        garantirModalNoDOM();
        estadoModal = {
            tipo: opcoes.tipo || (opcoes.pedido_id ? "status_pedido" : "saudacao"),
            pedido_id: opcoes.pedido_id ? Number(opcoes.pedido_id) : null,
            cliente_id: opcoes.cliente_id ? Number(opcoes.cliente_id) : null,
            linkAtual: "",
            telefoneValido: false,
        };
        const selTipo = document.getElementById("bee-wa-tipo");
        if (selTipo) selTipo.value = estadoModal.tipo;
        const inpInst = document.getElementById("bee-wa-instrucao");
        if (inpInst) inpInst.value = "";

        const modal = document.getElementById("bee-wa-modal");
        modal.classList.remove("hidden");
        modal.classList.add("flex");
        carregarRascunho(false);
    }

    function fecharModalWhatsApp() {
        const modal = document.getElementById("bee-wa-modal");
        if (!modal) return;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }

    function oferecerAvisoStatusWhatsApp(notificacao) {
        if (!notificacao) return;
        if (notificacao.enviado) return; // Já saiu automático pelo servidor
        if (notificacao.link) {
            const confirmar = confirm(
                `O status do pedido mudou para "${notificacao.novo_status}".\n` +
                `Deseja abrir o WhatsApp de ${notificacao.cliente_nome || "cliente"} com o aviso pronto?`
            );
            if (confirmar) {
                window.open(notificacao.link, "_blank", "noopener,noreferrer");
            }
        }
    }

    window.abrirModalWhatsApp = abrirModalWhatsApp;
    window.fecharModalWhatsApp = fecharModalWhatsApp;
    window.oferecerAvisoStatusWhatsApp = oferecerAvisoStatusWhatsApp;
})();
