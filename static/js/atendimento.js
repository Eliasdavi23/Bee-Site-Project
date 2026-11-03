/**
 * Painel de Atendimento WhatsApp + IA.
 */
let estadoAtendimento = {
    conversaAtual: null,
    conversas: [],
    statusModulo: null,
};

document.addEventListener("DOMContentLoaded", () => {
    carregarStatusModulo();
    carregarConversas();
    setInterval(() => {
        carregarConversas(true);
        if (estadoAtendimento.conversaAtual) {
            selecionarConversa(estadoAtendimento.conversaAtual.id, true);
        }
    }, 10000);
});

function escaparHtml(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function carregarStatusModulo() {
    try {
        const resp = await fetch("/api/whatsapp/status");
        if (!resp.ok) return;
        const st = await resp.json();
        estadoAtendimento.statusModulo = st;

        const elProv = document.getElementById("wa-status-provedor");
        const elIA = document.getElementById("wa-status-ia");
        if (elProv) {
            const mapa = {
                link: "🔗 Modo Híbrido (Clique wa.me)",
                evolution: "🤖 Evolution API Conectada",
                cloud: "☁️ WhatsApp Cloud API Oficial",
            };
            elProv.textContent = mapa[st.provedor] || `Modo: ${st.provedor}`;
        }
        if (elIA) {
            elIA.textContent = st.ia_ativa ? `✨ IA Ativa (${st.modelo_ia})` : "⚡ Modo Modelo Rápido (Sem chave IA)";
            elIA.className = st.ia_ativa
                ? "px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-950/70 border border-emerald-500/30 text-emerald-300"
                : "px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 border border-slate-700 text-slate-300";
        }

        if (st.usuario_gestor) {
            document.getElementById("wa-painel-gestor")?.classList.remove("hidden");
            const chkAviso = document.getElementById("chk-wa-aviso-status");
            const chkAuto = document.getElementById("chk-wa-auto-resposta");
            if (chkAviso) chkAviso.checked = Boolean(st.aviso_status);
            if (chkAuto) chkAuto.checked = Boolean(st.auto_resposta);
        }
    } catch (e) {
        console.error("Erro ao consultar status do WhatsApp:", e);
    }
}

async function salvarConfigWhatsApp() {
    const chkAviso = document.getElementById("chk-wa-aviso-status");
    const chkAuto = document.getElementById("chk-wa-auto-resposta");
    try {
        await fetch("/api/whatsapp/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                aviso_status: Boolean(chkAviso?.checked),
                auto_resposta: Boolean(chkAuto?.checked),
            }),
        });
        await carregarStatusModulo();
    } catch (e) {
        console.error("Erro ao salvar configurações:", e);
    }
}

async function carregarConversas(silencioso = false) {
    const busca = document.getElementById("wa-busca-conversa")?.value || "";
    try {
        const resp = await fetch(`/api/whatsapp/conversas?busca=${encodeURIComponent(busca)}`);
        if (!resp.ok) return;
        const dados = await resp.json();
        estadoAtendimento.conversas = dados.conversas || [];

        const badge = document.getElementById("wa-contador-pendentes");
        if (badge) {
            badge.textContent = `${dados.total_precisa_atendente || 0} aguardando humano`;
        }
        renderizarListaConversas(estadoAtendimento.conversas);
    } catch (e) {
        if (!silencioso) console.error("Erro ao listar conversas:", e);
    }
}

function renderizarListaConversas(conversas) {
    const box = document.getElementById("wa-lista-conversas");
    if (!box) return;

    if (!conversas.length) {
        box.innerHTML = `
            <div class="p-6 text-center text-xs text-slate-500 space-y-2">
                <p>Nenhuma conversa registrada ainda.</p>
                <p class="text-[11px] text-slate-400">Envie uma mensagem por Pedidos/Orçamentos/Clientes ou clique em "Colar Mensagem de Cliente".</p>
            </div>
        `;
        return;
    }

    const ativaId = estadoAtendimento.conversaAtual?.id;
    box.innerHTML = conversas.map(c => {
        const selecionada = c.id === ativaId ? "bg-slate-800/80 border-l-4 border-l-emerald-400" : "hover:bg-slate-800/40";
        const alertaHumano = c.precisa_atendente
            ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-slate-950">Atendente</span>`
            : "";
        const naoLidas = c.nao_lidas > 0
            ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500 text-slate-950">${c.nao_lidas}</span>`
            : "";

        return `
            <button type="button" onclick="selecionarConversa(${c.id})" class="w-full text-left p-3.5 transition flex flex-col gap-1 cursor-pointer ${selecionada}">
                <div class="flex justify-between items-center gap-2">
                    <span class="font-bold text-xs text-slate-100 truncate">${escaparHtml(c.nome_exibicao)}</span>
                    <div class="flex items-center gap-1">${alertaHumano}${naoLidas}</div>
                </div>
                <div class="text-[11px] text-slate-400">${escaparHtml(c.telefone_exibicao)}</div>
                <div class="text-xs text-slate-300 truncate mt-0.5">${escaparHtml(c.ultima_mensagem || "Sem mensagens")}</div>
            </button>
        `;
    }).join("");
}

async function selecionarConversa(conversaId, preservarTexto = false) {
    try {
        const resp = await fetch(`/api/whatsapp/conversas/${conversaId}`);
        if (!resp.ok) return;
        const dados = await resp.json();
        const c = dados.conversa;
        estadoAtendimento.conversaAtual = c;

        document.getElementById("wa-chat-nome").textContent = c.nome_exibicao;
        document.getElementById("wa-chat-telefone").textContent = c.telefone_exibicao;

        const acoes = document.getElementById("wa-chat-acoes");
        acoes?.classList.remove("hidden");
        acoes?.classList.add("flex");

        const linkDireto = document.getElementById("link-wa-direto");
        if (linkDireto) linkDireto.href = c.link_direto || "#";

        const btnAuto = document.getElementById("btn-wa-toggle-auto");
        if (btnAuto) {
            btnAuto.textContent = c.modo_auto ? "🤖 Robô: ON" : "👤 Manual";
            btnAuto.className = c.modo_auto
                ? "px-2.5 py-1.5 rounded-lg text-[11px] font-bold border border-emerald-500/40 bg-emerald-950/60 text-emerald-300 cursor-pointer"
                : "px-2.5 py-1.5 rounded-lg text-[11px] font-bold border border-amber-500/40 bg-amber-950/60 text-amber-300 cursor-pointer";
        }

        document.getElementById("btn-wa-sugerir-ia").disabled = false;
        document.getElementById("wa-input-resposta").disabled = false;
        document.getElementById("btn-wa-enviar-resposta").disabled = false;
        if (!preservarTexto) {
            document.getElementById("wa-feedback-envio").textContent = "";
        }

        const ctx = document.getElementById("wa-contexto-cliente");
        if (ctx) ctx.textContent = dados.resumo_cliente || "";

        renderizarMensagens(dados.mensagens || []);
        renderizarListaConversas(estadoAtendimento.conversas);
    } catch (e) {
        console.error("Erro ao abrir conversa:", e);
    }
}

function renderizarMensagens(mensagens) {
    const box = document.getElementById("wa-chat-mensagens");
    if (!box) return;
    if (!mensagens.length) {
        box.innerHTML = `<div class="p-6 text-center text-xs text-slate-500">Nenhuma mensagem nesta conversa.</div>`;
        return;
    }

    box.innerHTML = mensagens.map(m => {
        const entrada = m.direcao === "ENTRADA";
        const alinhamento = entrada ? "items-start" : "items-end";
        const balao = entrada
            ? "bg-slate-800 border border-slate-700 text-slate-100 rounded-2xl rounded-bl-sm"
            : "bg-emerald-900/70 border border-emerald-500/30 text-slate-100 rounded-2xl rounded-br-sm";
        const autorRotulo = entrada ? "Cliente" : (m.autor === "IA" ? "🤖 Assistente IA" : `👤 ${m.usuario || m.autor}`);

        return `
            <div class="flex flex-col ${alinhamento}">
                <div class="max-w-[85%] px-3.5 py-2.5 text-xs leading-relaxed whitespace-pre-wrap ${balao}">${escaparHtml(m.texto)}</div>
                <span class="text-[10px] text-slate-500 mt-1 px-1">${escaparHtml(autorRotulo)} • ${escaparHtml(m.criada_em || "")}</span>
            </div>
        `;
    }).join("");
    box.scrollTop = box.scrollHeight;
}

async function pedirSugestaoIA() {
    if (!estadoAtendimento.conversaAtual) return;
    const btn = document.getElementById("btn-wa-sugerir-ia");
    const campo = document.getElementById("wa-input-resposta");
    const feedback = document.getElementById("wa-feedback-envio");

    btn.disabled = true;
    feedback.textContent = "Consultando pedidos e gerando resposta...";

    try {
        const resp = await fetch(`/api/whatsapp/conversas/${estadoAtendimento.conversaAtual.id}/sugerir`, {
            method: "POST",
        });
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(dados.detail || "Falha ao gerar sugestão.");
        campo.value = dados.texto || "";
        feedback.textContent = dados.origem === "ia" ? "✨ Sugestão gerada pela IA" : (dados.aviso || "⚡ Modelo padrão carregado");
        campo.focus();
    } catch (e) {
        feedback.textContent = e.message || "Erro ao sugerir resposta.";
    } finally {
        btn.disabled = false;
    }
}

async function enviarRespostaPainel() {
    if (!estadoAtendimento.conversaAtual) return;
    const campo = document.getElementById("wa-input-resposta");
    const btn = document.getElementById("btn-wa-enviar-resposta");
    const feedback = document.getElementById("wa-feedback-envio");
    const texto = (campo.value || "").trim();
    if (!texto) return;

    btn.disabled = true;
    try {
        const resp = await fetch("/api/whatsapp/enviar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversa_id: estadoAtendimento.conversaAtual.id,
                texto: texto,
                assumir_conversa: true,
            }),
        });
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(dados.detail || "Erro ao enviar mensagem.");

        campo.value = "";
        if (dados.enviado) {
            feedback.textContent = "Enviada automaticamente! ✅";
        } else if (dados.link) {
            feedback.textContent = "Abrindo WhatsApp para envio...";
            window.open(dados.link, "_blank", "noopener,noreferrer");
        }
        await selecionarConversa(estadoAtendimento.conversaAtual.id, true);
        await carregarConversas(true);
    } catch (e) {
        feedback.textContent = e.message || "Erro ao enviar.";
    } finally {
        btn.disabled = false;
    }
}

async function alternarModoAutoConversa() {
    const c = estadoAtendimento.conversaAtual;
    if (!c) return;
    const novo = !Boolean(c.modo_auto);
    await fetch(`/api/whatsapp/conversas/${c.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modo_auto: novo, precisa_atendente: false }),
    });
    await selecionarConversa(c.id, true);
    await carregarConversas(true);
}

function abrirModalNovaMensagemCliente() {
    const modal = document.getElementById("modal-nova-msg-cliente");
    modal?.classList.remove("hidden");
    modal?.classList.add("flex");
}

function fecharModalNovaMensagemCliente() {
    const modal = document.getElementById("modal-nova-msg-cliente");
    modal?.classList.add("hidden");
    modal?.classList.remove("flex");
}

async function registrarMensagemManual(event) {
    event.preventDefault();
    const telefone = document.getElementById("manual-wa-telefone")?.value || "";
    const nome = document.getElementById("manual-wa-nome")?.value || "";
    const texto = document.getElementById("manual-wa-texto")?.value || "";
    const btn = document.getElementById("btn-salvar-manual-wa");

    if (btn) btn.disabled = true;
    try {
        const resp = await fetch("/api/whatsapp/conversas/manual", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ telefone, nome_contato: nome, texto }),
        });
        const dados = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(dados.detail || "Verifique o telefone informado.");

        fecharModalNovaMensagemCliente();
        document.getElementById("manual-wa-texto").value = "";
        await carregarConversas();
        await selecionarConversa(dados.conversa_id);
        if (dados.sugestao?.texto) {
            document.getElementById("wa-input-resposta").value = dados.sugestao.texto;
            document.getElementById("wa-feedback-envio").textContent =
                dados.sugestao.origem === "ia" ? "✨ Resposta sugerida pela IA pronta!" : "⚡ Resposta padrão carregada";
        }
    } catch (e) {
        alert(e.message || "Erro ao registrar mensagem.");
    } finally {
        if (btn) btn.disabled = false;
    }
}

window.abrirModalNovaMensagemCliente = abrirModalNovaMensagemCliente;
window.fecharModalNovaMensagemCliente = fecharModalNovaMensagemCliente;
window.registrarMensagemManual = registrarMensagemManual;
window.selecionarConversa = selecionarConversa;
window.pedirSugestaoIA = pedirSugestaoIA;
window.enviarRespostaPainel = enviarRespostaPainel;
window.alternarModoAutoConversa = alternarModoAutoConversa;
window.salvarConfigWhatsApp = salvarConfigWhatsApp;
window.carregarConversas = carregarConversas;
