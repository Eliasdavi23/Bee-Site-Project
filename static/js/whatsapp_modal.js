/**
 * Modal global de envio rápido de WhatsApp + IA (usado em Pedidos, Orçamentos, Clientes e na aba WhatsApp).
 * 100% Localhost — sem dependências externas e sem bloqueio de pop-up.
 */
(function () {
    let estadoModal = {
        tipo: "status_pedido",
        pedido_id: null,
        cliente_id: null,
        telefone: "",
        linkAtual: "",
        linkWebAtual: "",
        telefoneValido: false,
        clientes: [],
        pedidos: [],
    };

    function extrairErro(dados, padrao = "Não foi possível concluir a operação.") {
        if (!dados) return padrao;
        if (typeof dados.detail === "string") return dados.detail;
        if (Array.isArray(dados.detail) && dados.detail.length > 0) {
            return dados.detail.map(item => item.msg || JSON.stringify(item)).join("; ");
        }
        return dados.erro || dados.mensagem || padrao;
    }

    function garantirModalNoDOM() {
        if (document.getElementById("bee-wa-modal")) return;

        const wrapper = document.createElement("div");
        wrapper.id = "bee-wa-modal";
        wrapper.className = "fixed inset-0 bg-black/80 backdrop-blur-sm hidden items-center justify-center z-[9998] p-4 no-print print:hidden";
        wrapper.innerHTML = `
            <div class="bg-zinc-900 border border-zinc-800 w-full max-w-xl rounded-2xl shadow-2xl p-6 space-y-4 text-zinc-100 max-h-[92vh] overflow-y-auto">
                <div class="flex justify-between items-center border-b border-zinc-800 pb-3">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-xl bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center text-yellow-400 shrink-0">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                    </div>
                        <div>
                            <h3 class="text-lg font-black text-yellow-400">Criar / Enviar Mensagem WhatsApp</h3>
                            <p id="bee-wa-destinatario" class="text-xs text-zinc-400">Selecione o cliente ou digite o número abaixo</p>
                        </div>
                    </div>
                    <button type="button" id="bee-wa-fechar" class="text-zinc-400 hover:text-white text-xl font-bold px-2 cursor-pointer">✕</button>
                </div>

                <!-- Seletores de Cliente e Pedido (visíveis quando aberto pela aba WhatsApp) -->
                <div id="bee-wa-seletores-bloco" class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-[11px] font-bold text-zinc-400 uppercase mb-1">Cliente Cadastrado</label>
                        <select id="bee-wa-sel-cliente" class="w-full bg-black border border-zinc-800 text-zinc-100 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent">
                            <option value="">-- Escolher cliente (ou digitar nº) --</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-zinc-400 uppercase mb-1">Pedido / Orçamento (opcional)</label>
                        <select id="bee-wa-sel-pedido" class="w-full bg-black border border-zinc-800 text-zinc-100 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent">
                            <option value="">-- Nenhum (mensagem livre) --</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-[11px] font-bold text-zinc-400 uppercase mb-1">WhatsApp do Cliente (com DDD) *</label>
                        <input type="text" id="bee-wa-telefone" placeholder="Ex.: (11) 98888-7777" class="w-full bg-black border border-zinc-800 text-zinc-100 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent">
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-zinc-400 uppercase mb-1">Tipo de Mensagem</label>
                        <select id="bee-wa-tipo" class="w-full bg-black border border-zinc-800 text-zinc-100 text-xs rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent">
                            <option value="status_pedido">Status do Pedido</option>
                            <option value="cobranca">Lembrete de Pagamento</option>
                            <option value="orcamento">Envio de Orçamento</option>
                            <option value="saudacao">Saudação / Mensagem Livre</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-zinc-400 uppercase mb-1">Instrução extra para a IA (opcional)</label>
                    <div class="flex gap-1.5">
                        <input type="text" id="bee-wa-instrucao" maxlength="250" placeholder="Ex.: avisar que fechamos às 18h" class="flex-1 bg-black border border-zinc-800 text-zinc-100 text-xs rounded-xl px-3 py-2 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent">
                        <button type="button" id="bee-wa-gerar-ia" class="bg-yellow-400 hover:bg-yellow-300 text-black font-black text-xs px-3.5 py-2 rounded-xl transition cursor-pointer whitespace-nowrap" title="Gerar/reescrever com IA">
                            Escrever com IA
                        </button>
                    </div>
                </div>

                <div>
                    <div class="flex justify-between items-center mb-1">
                        <label class="text-[11px] font-bold text-zinc-400 uppercase">Mensagem (pode editar antes de enviar)</label>
                        <span id="bee-wa-origem-badge" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-zinc-300">Modelo pronto</span>
                    </div>
                    <textarea id="bee-wa-texto" rows="6" maxlength="1500" class="w-full bg-black border border-zinc-800 text-zinc-100 text-sm rounded-xl p-3 outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent leading-relaxed"></textarea>
                </div>

                <div id="bee-wa-alerta" class="hidden text-xs rounded-xl p-3 border"></div>

                <div class="flex flex-wrap justify-between items-center gap-2 pt-2 border-t border-zinc-800">
                    <button type="button" id="bee-wa-cancelar" class="px-4 py-2 rounded-xl border border-zinc-800 text-zinc-300 text-xs font-bold hover:bg-slate-800 transition cursor-pointer">Cancelar</button>
                    <div class="flex flex-wrap gap-2">
                        <button type="button" id="bee-wa-enviar-app" class="px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-yellow-400 border border-zinc-700 text-xs font-bold transition cursor-pointer" title="Abre link wa.me (App ou Celular)">
                            Abrir wa.me
                        </button>
                        <button type="button" id="bee-wa-enviar-web" class="px-5 py-2.5 rounded-xl bg-yellow-400 hover:bg-yellow-300 text-black shadow-lg shadow-yellow-500/20 text-xs font-black transition cursor-pointer shadow-lg" title="Abre direto no WhatsApp Web do navegador">
                            Enviar no WhatsApp Web
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(wrapper);

        document.getElementById("bee-wa-fechar").addEventListener("click", fecharModalWhatsApp);
        document.getElementById("bee-wa-cancelar").addEventListener("click", fecharModalWhatsApp);

        document.getElementById("bee-wa-sel-cliente").addEventListener("change", (e) => {
            const cid = e.target.value ? Number(e.target.value) : null;
            estadoModal.cliente_id = cid;
            const cli = estadoModal.clientes.find(c => c.id === cid);
            if (cli) {
                document.getElementById("bee-wa-telefone").value = cli.telefone || "";
            }
            preencherSelectPedidosModal(cid);
            carregarRascunho(false);
        });

        document.getElementById("bee-wa-sel-pedido").addEventListener("change", (e) => {
            const pid = e.target.value ? Number(e.target.value) : null;
            estadoModal.pedido_id = pid;
            const ped = estadoModal.pedidos.find(p => p.id === pid);
            if (ped) {
                estadoModal.cliente_id = ped.cliente_id || estadoModal.cliente_id;
                const selCli = document.getElementById("bee-wa-sel-cliente");
                if (selCli && ped.cliente_id) selCli.value = String(ped.cliente_id);
                if (ped.cliente_telefone) {
                    document.getElementById("bee-wa-telefone").value = ped.cliente_telefone;
                }
                estadoModal.tipo = ped.tipo === "ORCAMENTO" ? "orcamento" : "status_pedido";
                document.getElementById("bee-wa-tipo").value = estadoModal.tipo;
            } else {
                estadoModal.tipo = "saudacao";
                document.getElementById("bee-wa-tipo").value = "saudacao";
            }
            carregarRascunho(false);
        });

        document.getElementById("bee-wa-tipo").addEventListener("change", (e) => {
            estadoModal.tipo = e.target.value;
            carregarRascunho(false);
        });
        document.getElementById("bee-wa-gerar-ia").addEventListener("click", () => carregarRascunho(true));
        document.getElementById("bee-wa-enviar-web").addEventListener("click", () => confirmarEnvioModal("web"));
        document.getElementById("bee-wa-enviar-app").addEventListener("click", () => confirmarEnvioModal("wame"));
    }

    async function carregarDestinatariosModal() {
        try {
            const resp = await fetch("/api/whatsapp/destinatarios");
            if (!resp.ok) return;
            const dados = await resp.json();
            estadoModal.clientes = dados.clientes || [];
            estadoModal.pedidos = dados.pedidos || [];

            const selCli = document.getElementById("bee-wa-sel-cliente");
            if (selCli) {
                selCli.innerHTML = `<option value="">-- Escolher cliente (ou digitar nº) --</option>` +
                    estadoModal.clientes.map(c =>
                        `<option value="${c.id}">${c.nome} (${c.telefone || "sem telefone"})</option>`
                    ).join("");
                if (estadoModal.cliente_id) selCli.value = String(estadoModal.cliente_id);
            }
            preencherSelectPedidosModal(estadoModal.cliente_id);
        } catch (e) {
            console.error("Erro ao carregar destinatários:", e);
        }
    }

    function preencherSelectPedidosModal(clienteIdFiltro = null) {
        const selPed = document.getElementById("bee-wa-sel-pedido");
        if (!selPed) return;
        const lista = clienteIdFiltro
            ? estadoModal.pedidos.filter(p => p.cliente_id === clienteIdFiltro)
            : estadoModal.pedidos;

        selPed.innerHTML = `<option value="">-- Nenhum (mensagem livre / saudação) --</option>` +
            lista.map(p => {
                const rotulo = p.tipo === "ORCAMENTO" ? `Orçamento #${p.id}` : `Pedido #${p.id} (${p.status_producao})`;
                return `<option value="${p.id}">${rotulo} - ${p.cliente_nome}</option>`;
            }).join("");
        if (estadoModal.pedido_id) selPed.value = String(estadoModal.pedido_id);
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
        const inpTel = document.getElementById("bee-wa-telefone");
        const instrucao = document.getElementById("bee-wa-instrucao")?.value || "";

        mostrarAlerta("");
        if (!estadoModal.pedido_id && estadoModal.tipo !== "saudacao") {
            estadoModal.tipo = "saudacao";
            const selTipo = document.getElementById("bee-wa-tipo");
            if (selTipo) selTipo.value = "saudacao";
        }

        if (btnIA) btnIA.disabled = true;

        try {
            const resp = await fetch("/api/whatsapp/rascunho", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tipo: estadoModal.tipo,
                    pedido_id: estadoModal.pedido_id,
                    cliente_id: estadoModal.cliente_id,
                    telefone: inpTel?.value || "",
                    usar_ia: Boolean(usarIA),
                    instrucao_extra: instrucao,
                }),
            });
            const dados = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                throw new Error(extrairErro(dados, "Não foi possível preparar a mensagem."));
            }
            estadoModal.cliente_id = dados.cliente_id || estadoModal.cliente_id;
            estadoModal.linkAtual = dados.link || "";
            estadoModal.linkWebAtual = dados.link_web || dados.link || "";
            estadoModal.telefoneValido = Boolean(dados.telefone_valido);

            if (txt) txt.value = dados.texto || "";
            if (inpTel && !inpTel.value && dados.telefone_bruto) {
                inpTel.value = dados.telefone_bruto;
            }
            if (dest) {
                dest.textContent = `${dados.cliente_nome || "Contato"} • ${dados.telefone_exibicao || "Informe o WhatsApp abaixo"}`;
            }
            if (badge) {
                badge.textContent = dados.origem === "ia" ? "Escrito pela IA" : "Modelo rápido";
                badge.className = dados.origem === "ia"
                    ? "text-[10px] font-bold px-2 py-0.5 rounded-full bg-yellow-400/20 text-yellow-300 border border-yellow-400/30"
                    : "text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-zinc-300";
            }
            if (!estadoModal.telefoneValido) {
                mostrarAlerta("Digite um número de WhatsApp válido com DDD no campo acima (ex.: 11 98888-7777) para enviar.", true);
            }
        } catch (err) {
            mostrarAlerta(err.message || "Erro ao gerar rascunho.", true);
        } finally {
            if (btnIA) btnIA.disabled = false;
        }
    }

    async function confirmarEnvioModal(modoAbertura = "web") {
        const texto = (document.getElementById("bee-wa-texto")?.value || "").trim();
        const telefoneDigitado = (document.getElementById("bee-wa-telefone")?.value || "").trim();
        const btnWeb = document.getElementById("bee-wa-enviar-web");
        const btnApp = document.getElementById("bee-wa-enviar-app");

        if (!texto) {
            mostrarAlerta("Digite uma mensagem antes de enviar.", true);
            return;
        }

        const envioDiretoAtivo = Boolean(window.beeWhatsAppEnvioAutomatico) && modoAbertura !== "wame";
        // Abre a aba sincronamente apenas quando não estiver em envio direto por QR Code
        const novaAba = envioDiretoAtivo ? null : window.open("about:blank", "_blank");

        if (btnWeb) btnWeb.disabled = true;
        if (btnApp) btnApp.disabled = true;

        try {
            const resp = await fetch("/api/whatsapp/enviar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    texto: texto,
                    pedido_id: estadoModal.pedido_id,
                    cliente_id: estadoModal.cliente_id,
                    telefone: telefoneDigitado,
                    assumir_conversa: false,
                }),
            });
            const dados = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                if (novaAba) novaAba.close();
                throw new Error(extrairErro(dados, "Falha ao enviar mensagem."));
            }

            if (typeof window.carregarConversas === "function") {
                window.carregarConversas(true);
            }

            if (dados.enviado) {
                if (novaAba) novaAba.close();
                mostrarAlerta("Mensagem enviada automaticamente pelo servidor!", false);
                setTimeout(fecharModalWhatsApp, 900);
            } else {
                const urlDestino = modoAbertura === "web" ? (dados.link_web || dados.link) : (dados.link || dados.link_web);
                if (novaAba && urlDestino) {
                    novaAba.location.href = urlDestino;
                } else if (urlDestino) {
                    window.location.href = urlDestino;
                }
                fecharModalWhatsApp();
            }
        } catch (err) {
            mostrarAlerta(err.message || "Erro ao enviar.", true);
        } finally {
            if (btnWeb) btnWeb.disabled = false;
            if (btnApp) btnApp.disabled = false;
        }
    }

    async function abrirModalWhatsApp(opcoes = {}) {
        garantirModalNoDOM();
        estadoModal.pedido_id = opcoes.pedido_id ? Number(opcoes.pedido_id) : null;
        estadoModal.cliente_id = opcoes.cliente_id ? Number(opcoes.cliente_id) : null;
        estadoModal.tipo = opcoes.tipo || (estadoModal.pedido_id ? "status_pedido" : "saudacao");
        estadoModal.linkAtual = "";
        estadoModal.linkWebAtual = "";
        estadoModal.telefoneValido = false;

        const selTipo = document.getElementById("bee-wa-tipo");
        if (selTipo) selTipo.value = estadoModal.tipo;
        const inpInst = document.getElementById("bee-wa-instrucao");
        if (inpInst) inpInst.value = "";
        const inpTel = document.getElementById("bee-wa-telefone");
        if (inpTel) inpTel.value = opcoes.telefone || "";

        const modal = document.getElementById("bee-wa-modal");
        modal.classList.remove("hidden");
        modal.classList.add("flex");

        await carregarDestinatariosModal();
        try {
            const stResp = await fetch("/api/whatsapp/status");
            if (stResp.ok) {
                const stDados = await stResp.json();
                window.beeWhatsAppEnvioAutomatico = Boolean(stDados.envio_automatico_ativo);
                const btnWeb = document.getElementById("bee-wa-enviar-web");
                if (btnWeb) {
                    btnWeb.textContent = stDados.envio_automatico_ativo
                        ? "Enviar Direto no Sistema"
                        : "Enviar no WhatsApp Web";
                }
            }
        } catch (_) {}
        await carregarRascunho(false);
    }

    function fecharModalWhatsApp() {
        const modal = document.getElementById("bee-wa-modal");
        if (!modal) return;
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }

    async function oferecerAvisoStatusWhatsApp(notificacao) {
        if (!notificacao || notificacao.enviado) return;
        const url = notificacao.link_web || notificacao.link;
        if (url) {
            const confirmar = await BeeHUD.confirm({
                titulo: "Aviso de Pedido",
                mensagem: `O status do pedido mudou para "${notificacao.novo_status}".\n\nDeseja abrir o WhatsApp Web de ${notificacao.cliente_nome || "cliente"} com o aviso pronto?`,
                confirmTexto: "Abrir WhatsApp Web",
                tipo: "question"
            });
            if (confirmar) {
                window.open(url, "_blank", "noopener,noreferrer");
            }
        }
    }

    window.abrirModalWhatsApp = abrirModalWhatsApp;
    window.fecharModalWhatsApp = fecharModalWhatsApp;
    window.oferecerAvisoStatusWhatsApp = oferecerAvisoStatusWhatsApp;
})();
