// ==========================================================
// INTERFACE VISUAL E GERAÇÃO DE HTML (ATENDIMENTO WHATSAPP)
// ==========================================================

let _assinaturaListaAnterior = "";
let _assinaturaMensagensAnterior = "";

export function escaparHtml(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export function tocarSomNovaMensagem() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1174.66, ctx.currentTime + 0.09);
        gain.gain.setValueAtTime(0.06, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.16);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.17);
    } catch (_) {
        // Ignora bloqueio de áudio automático do navegador
    }
}

export function renderizarStatusTopo(st) {
    const elProv = document.getElementById("wa-status-provedor");
    const elIA = document.getElementById("wa-status-ia");
    const btnQr = document.getElementById("btn-wa-conectar-qr");
    const btnEnviarPrincipal = document.getElementById("btn-wa-enviar-resposta");

    const bridgeConectado = Boolean(st?.bridge?.conectado);

    if (elProv) {
        const mapa = {
            bridge: "Tempo Real Conectado (QR Code)",
            link: "Modo WhatsApp Web / wa.me",
            evolution: "Evolution API Conectada",
            cloud: "WhatsApp Cloud API Oficial",
        };
        elProv.textContent = mapa[st.provedor] || `Modo: ${st.provedor}`;
        elProv.className = st.envio_automatico_ativo
            ? "px-3 py-1.5 rounded-xl text-xs font-bold bg-yellow-400/10 border border-yellow-400/30 text-yellow-400"
            : "px-3 py-1.5 rounded-xl text-xs font-bold bg-black border border-zinc-800 text-zinc-300";
    }

    if (btnQr) {
        btnQr.textContent = bridgeConectado ? "WhatsApp Conectado (QR)" : "Conectar WhatsApp (QR Code)";
        btnQr.className = bridgeConectado
            ? "bg-zinc-800 hover:bg-zinc-700 text-yellow-400 border border-yellow-400/40 font-black px-3.5 py-2 rounded-xl text-xs transition cursor-pointer shadow"
            : "bg-yellow-400 hover:bg-yellow-300 text-black font-bold shadow-lg shadow-yellow-500/20 px-3.5 py-2 rounded-xl text-xs transition cursor-pointer shadow-lg";
    }

    if (btnEnviarPrincipal) {
        btnEnviarPrincipal.textContent = st.envio_automatico_ativo ? "Enviar Direto" : "WhatsApp Web";
        btnEnviarPrincipal.title = st.envio_automatico_ativo
            ? "Envia a mensagem imediatamente dentro do próprio sistema em tempo real"
            : "Abre direto no WhatsApp Web com o texto preenchido";
    }

    if (elIA) {
        elIA.textContent = st.ia_ativa ? `IA Ativa (${st.modelo_ia})` : "Modo Modelo Rápido (Sem chave IA)";
        elIA.className = st.ia_ativa
            ? "px-3 py-1.5 rounded-xl text-xs font-bold bg-yellow-400/10 border border-yellow-400/30 text-yellow-400"
            : "px-3 py-1.5 rounded-xl text-xs font-bold bg-black border border-zinc-800 text-zinc-300";
    }

    if (st.usuario_gestor) {
        document.getElementById("wa-painel-gestor")?.classList.remove("hidden");
        const chkAviso = document.getElementById("chk-wa-aviso-status");
        const chkAuto = document.getElementById("chk-wa-auto-resposta");
        if (chkAviso) chkAviso.checked = Boolean(st.aviso_status);
        if (chkAuto) chkAuto.checked = Boolean(st.auto_resposta);
    }
}

export function renderizarModalBridge(st) {
    const badge = document.getElementById("bridge-qr-status-badge");
    const boxQr = document.getElementById("bridge-qr-container");
    const imgQr = document.getElementById("bridge-qr-img");
    const boxConectado = document.getElementById("bridge-conectado-info");
    const boxNodeAusente = document.getElementById("bridge-node-ausente");
    const txtErro = document.getElementById("bridge-qr-erro");
    const btnDesconectar = document.getElementById("btn-bridge-desconectar");

    if (!badge) return;

    boxQr?.classList.add("hidden");
    boxConectado?.classList.add("hidden");
    boxNodeAusente?.classList.add("hidden");
    btnDesconectar?.classList.add("hidden");

    if (st.ultimo_erro && txtErro) {
        txtErro.textContent = st.ultimo_erro;
        txtErro.classList.remove("hidden");
    } else if (txtErro) {
        txtErro.classList.add("hidden");
    }

    if (st.conectado) {
        badge.textContent = "Conectado em Tempo Real!";
        badge.className = "px-3 py-1 rounded-full text-xs font-black bg-yellow-400/20 text-yellow-300 border border-yellow-400/40";
        boxConectado?.classList.remove("hidden");
        btnDesconectar?.classList.remove("hidden");
        const elNum = document.getElementById("bridge-conectado-numero");
        if (elNum) elNum.textContent = st.nome ? `${st.nome} (${st.numero})` : st.numero || "Aparelho pareado";
        return;
    }

    if (!st.node_instalado || st.status === "node_ausente") {
        badge.textContent = "Node.js necessário neste PC";
        badge.className = "px-3 py-1 rounded-full text-xs font-black bg-zinc-800 text-yellow-400 border border-zinc-700";
        boxNodeAusente?.classList.remove("hidden");
        return;
    }

    if (st.status === "instalando_dependencias") {
        badge.textContent = "Preparando ponte de tempo real (1ª vez, aguarde ~20s)...";
        badge.className = "px-3 py-1 rounded-full text-xs font-black bg-zinc-800 text-zinc-300 border border-zinc-700";
        return;
    }

    if (st.qr_data_url) {
        badge.textContent = "Aponte a câmera do WhatsApp para o QR Code abaixo";
        badge.className = "px-3 py-1 rounded-full text-xs font-black bg-zinc-800 text-yellow-400 border border-zinc-700";
        if (imgQr) imgQr.src = st.qr_data_url;
        boxQr?.classList.remove("hidden");
        return;
    }

    badge.textContent = "Gerando QR Code do WhatsApp...";
    badge.className = "px-3 py-1 rounded-full text-xs font-black bg-zinc-800 text-zinc-300 border border-zinc-700";
}

export function renderizarSelectClientesManual(clientes) {
    const sel = document.getElementById("manual-wa-cliente-id");
    if (!sel) return;
    sel.innerHTML =
        `<option value="">-- Escolher da lista ou digitar abaixo --</option>` +
        clientes
            .map(c => `<option value="${c.id}">${escaparHtml(c.nome)} (${escaparHtml(c.telefone || "sem telefone")})</option>`)
            .join("");
}

export function renderizarListaConversas(conversas, conversaAtivaId = null, totalPendentes = 0) {
    const totalNaoLidas = conversas.reduce((acc, c) => acc + (Number(c.nao_lidas) || 0), 0);
    const badge = document.getElementById("wa-contador-pendentes");
    if (badge) {
        badge.textContent = `${totalPendentes} aguardando humano`;
    }

    const badgeNaoLidas = document.getElementById("wa-contador-nao-lidas");
    const numNaoLidas = document.getElementById("wa-contador-nao-lidas-num");
    if (badgeNaoLidas && numNaoLidas) {
        numNaoLidas.textContent = totalNaoLidas > 99 ? "99+" : `+${totalNaoLidas}`;
        if (totalNaoLidas > 0) {
            badgeNaoLidas.classList.remove("hidden");
            badgeNaoLidas.classList.add("inline-flex");
        } else {
            badgeNaoLidas.classList.add("hidden");
            badgeNaoLidas.classList.remove("inline-flex");
        }
    }

    const box = document.getElementById("wa-lista-conversas");
    if (!box) return;

    const assinatura = JSON.stringify(
        conversas.map(c => [c.id, c.id === conversaAtivaId, c.nao_lidas, c.precisa_atendente, c.ultima_mensagem, c.nome_exibicao])
    );
    if (assinatura === _assinaturaListaAnterior) {
        return;
    }
    _assinaturaListaAnterior = assinatura;

    if (!conversas.length) {
        box.innerHTML = `
            <div class="p-6 text-center text-xs text-zinc-500 space-y-3">
                <p>Nenhuma conversa registrada ainda.</p>
                <button type="button" onclick="abrirModalWhatsApp({})" class="bg-yellow-400 hover:bg-yellow-300 text-black shadow-lg shadow-yellow-500/20 font-bold px-3 py-2 rounded-xl text-xs transition cursor-pointer">
                    Criar Primeira Mensagem
                </button>
            </div>
        `;
        return;
    }

    box.innerHTML = conversas
        .map(c => {
            const qtdNaoLidas = Number(c.nao_lidas) || 0;
            const temNaoLidas = qtdNaoLidas > 0;
            const textoBadge = qtdNaoLidas > 99 ? "99+" : `+${qtdNaoLidas}`;
            const selecionada = c.id === conversaAtivaId
                ? "bg-zinc-800/90 border-l-4 border-l-yellow-400 shadow-inner"
                : temNaoLidas
                    ? "bg-yellow-400/10 border-l-4 border-l-yellow-400 hover:bg-yellow-400/15"
                    : "hover:bg-zinc-800/40 border-l-4 border-l-transparent";

            const alertaHumano = c.precisa_atendente
                ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-yellow-400 text-black">Atendente</span>`
                : "";

            const naoLidasBadge = temNaoLidas
                ? `<span class="inline-flex items-center gap-1.5 shrink-0" title="${qtdNaoLidas} mensagem(ns) sem resposta">
                        <span class="relative flex h-2.5 w-2.5 shrink-0">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-400"></span>
                        </span>
                        <span class="inline-flex items-center justify-center min-w-[24px] px-2 py-0.5 rounded-full text-[11px] font-black bg-yellow-400 text-black shadow-sm leading-tight select-none">
                            ${textoBadge}
                        </span>
                    </span>`
                : "";

            const nomeLimpo = (c.nome_exibicao || "Contato").trim();
            const partes = nomeLimpo.split(" ").filter(Boolean);
            const iniciais = partes.length >= 2
                ? (partes[0][0] + partes[1][0]).toUpperCase()
                : nomeLimpo.slice(0, 2).toUpperCase();

            return `
                <button type="button" onclick="selecionarConversa(${c.id})" class="w-full text-left p-2.5 px-3 transition flex items-start gap-2.5 cursor-pointer border-b border-zinc-800/40 hover:bg-zinc-800/40 ${selecionada}">
                    <div class="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center font-bold text-xs ${temNaoLidas ? 'text-yellow-400 bg-zinc-800 border-yellow-400/40' : 'text-zinc-300'} shrink-0 shadow-inner mt-0.5">
                        ${iniciais}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-center gap-1.5 mb-0.5">
                            <span class="font-bold text-xs ${c.id === conversaAtivaId ? 'text-yellow-400' : 'text-zinc-100'} truncate">${escaparHtml(c.nome_exibicao)}</span>
                            <div class="flex items-center gap-1 shrink-0">
                                ${alertaHumano}
                                ${naoLidasBadge}
                            </div>
                        </div>
                        <div class="flex justify-between items-center gap-1">
                            <span class="text-[11px] text-zinc-400 truncate">${escaparHtml(c.telefone_exibicao)}</span>
                            <span onclick="event.stopPropagation(); alternarNaoLidaConversa(${c.id}, ${temNaoLidas ? 0 : 1})" class="text-[10px] font-medium text-zinc-500 hover:text-yellow-400 transition cursor-pointer" title="${temNaoLidas ? 'Marcar como lida' : 'Marcar como não lida (+1)'}">
                                ${temNaoLidas ? 'lida' : 'nao lida'}
                            </span>
                        </div>
                        <div class="text-[11px] ${temNaoLidas ? "text-yellow-400 font-semibold" : "text-zinc-400"} truncate mt-0.5">${escaparHtml(c.ultima_mensagem || "Sem mensagens")}</div>
                    </div>
                </button>
            `;
        })
        .join("");
}

export function renderizarCabecalhoConversa(c, resumoCliente, preservarTexto = false) {
    document.getElementById("wa-chat-nome").textContent = c.nome_exibicao;
    document.getElementById("wa-chat-telefone").textContent = c.telefone_exibicao;

    const acoes = document.getElementById("wa-chat-acoes");
    acoes?.classList.remove("hidden");
    acoes?.classList.add("flex");

    const linkDireto = document.getElementById("link-wa-direto");
    if (linkDireto) linkDireto.href = c.link_web || c.link_direto || "https://web.whatsapp.com";

    const btnAuto = document.getElementById("btn-wa-toggle-auto");
    if (btnAuto) {
        btnAuto.textContent = c.modo_auto ? "Robo: ON" : "Manual";
        btnAuto.className = c.modo_auto
            ? "px-2.5 py-1.5 rounded-lg text-[11px] font-bold border border-emerald-500/40 bg-emerald-950/60 text-yellow-400 cursor-pointer"
            : "px-2.5 py-1.5 rounded-lg text-[11px] font-bold border border-zinc-700 bg-zinc-800 text-zinc-400 cursor-pointer";
    }

    const btnAnteriores = document.getElementById("btn-wa-carregar-anteriores");
    if (btnAnteriores) btnAnteriores.disabled = false;
    document.getElementById("btn-wa-sugerir-ia").disabled = false;
    const btnResumo = document.getElementById("btn-wa-resumo-pedido");
    if (btnResumo) btnResumo.disabled = false;
    const btnGerar = document.getElementById("btn-wa-gerar-pedido");
    if (btnGerar) btnGerar.disabled = false;
    const btnComprovante = document.getElementById("btn-wa-comprovante");
    if (btnComprovante) btnComprovante.disabled = false;
    document.getElementById("wa-input-resposta").disabled = false;
    document.getElementById("btn-wa-enviar-resposta").disabled = false;
    const btnWame = document.getElementById("btn-wa-enviar-wame");
    if (btnWame) btnWame.disabled = false;

    if (!preservarTexto) {
        document.getElementById("wa-feedback-envio").textContent = "";
    }

    const ctx = document.getElementById("wa-contexto-cliente");
    if (ctx) ctx.textContent = resumoCliente || "";
}

export function renderizarMensagens(mensagens, conversaId = 0) {
    const box = document.getElementById("wa-chat-mensagens");
    if (!box) return false;

    const ultima = mensagens.length ? mensagens[mensagens.length - 1] : null;
    const assinatura = `${conversaId}:${mensagens.length}:${ultima ? `${ultima.id}-${ultima.status}` : "vazio"}`;
    if (assinatura === _assinaturaMensagensAnterior) {
        return false;
    }

    const mudouConversa = !_assinaturaMensagensAnterior.startsWith(`${conversaId}:`);
    const chegouNovaEntrada = !mudouConversa && ultima && ultima.direcao === "ENTRADA";
    _assinaturaMensagensAnterior = assinatura;

    if (!mensagens.length) {
        box.innerHTML = `
            <div class="p-6 text-center text-xs text-zinc-500 space-y-2">
                <p>Nenhuma mensagem nesta conversa ainda.</p>
                <button type="button" onclick="carregarMensagensAnteriores()" class="px-3 py-1.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 text-[11px] font-bold transition cursor-pointer">
                    Buscar historico anterior no WhatsApp
                </button>
            </div>
        `;
        return false;
    }

    const bannerAnteriores = `
        <div class="text-center py-1">
            <button type="button" onclick="carregarMensagensAnteriores()" class="px-3 py-1 rounded-full bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-700 text-[11px] font-semibold transition cursor-pointer shadow-sm">
                Carregar historico anterior
            </button>
        </div>
    `;

    box.innerHTML = bannerAnteriores + mensagens
        .map(m => {
            const entrada = m.direcao === "ENTRADA";
            const alinhamento = entrada ? "items-start" : "items-end";
            const ehIa = m.autor === "IA";
            const balao = entrada
                ? "bg-slate-800/95 border border-slate-700/60 text-zinc-100 rounded-2xl rounded-tl-xs shadow-sm"
                : ehIa
                    ? "bg-slate-800/90 border-l-4 border-l-amber-400 border border-slate-700/60 text-zinc-100 rounded-2xl shadow-sm"
                    : "bg-emerald-600/90 text-white rounded-2xl rounded-tr-xs shadow-md";
            const autorRotulo = entrada
                ? "Cliente"
                : ehIa
                    ? "Assistente IA"
                    : (m.usuario && m.usuario !== "Atendente" ? m.usuario : "Atendente");
            const statusIcone = !entrada ? (m.status === "ENVIADA" ? " [enviada]" : m.status === "LINK" ? " [link]" : "") : "";

            let textoExibicao = m.texto || "";
            let htmlMidia = "";

            const tipoMidia = (m.midia_tipo || "").toLowerCase();
            const urlMidia = m.midia_url || "";
            const urlLower = urlMidia.toLowerCase();

            // Detecta tipo da mídia
            const ehAudio =
                tipoMidia === "audio" ||
                urlLower.endsWith(".ogg") ||
                urlLower.endsWith(".mp3") ||
                urlLower.endsWith(".m4a") ||
                urlLower.endsWith(".wav") ||
                textoExibicao.startsWith("\uD83C\uDFA4") ||
                textoExibicao.startsWith("\uD83C\uDFB5");

            const ehDocumento =
                tipoMidia === "documento" ||
                urlLower.endsWith(".pdf") ||
                urlLower.endsWith(".cdr") ||
                urlLower.endsWith(".ai") ||
                urlLower.endsWith(".psd") ||
                urlLower.endsWith(".docx") ||
                urlLower.endsWith(".xlsx") ||
                urlLower.endsWith(".zip") ||
                textoExibicao.startsWith("\uD83D\uDCC4");

            const ehImagem =
                !ehAudio &&
                !ehDocumento &&
                (tipoMidia === "imagem" ||
                    urlLower.endsWith(".jpg") ||
                    urlLower.endsWith(".jpeg") ||
                    urlLower.endsWith(".png") ||
                    urlLower.endsWith(".webp") ||
                    urlLower.endsWith(".gif") ||
                    textoExibicao.startsWith("\uD83D\uDCF7"));

            if (ehAudio) {
                if (urlMidia) {
                    htmlMidia = `
                        <div class="mb-2 p-2.5 rounded-xl bg-black/90 border border-emerald-500/40 flex flex-col gap-2 min-w-[260px] max-w-[330px] shadow-sm">
                            <div class="flex items-center justify-between text-[11px] text-slate-200">
                                <span class="flex items-center gap-1.5 font-bold text-yellow-400">
                                    Mensagem de Voz / Audio
                                </span>
                                <a href="${escaparHtml(urlMidia)}" download="audio_${m.id}.ogg" class="text-[10px] text-indigo-300 hover:text-indigo-200 underline font-semibold flex items-center gap-0.5">
                                    Baixar
                                </a>
                            </div>
                            <audio controls preload="metadata" class="w-full h-9 rounded" src="${escaparHtml(urlMidia)}"></audio>
                        </div>
                    `;
                } else {
                    htmlMidia = `
                        <div class="mb-2 p-2.5 rounded-xl bg-black/90 border border-amber-500/40 flex flex-col gap-2 min-w-[260px] max-w-[330px] shadow-sm">
                            <div class="flex items-center gap-2 text-[11px] text-slate-200">
                                
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-amber-300">Mensagem de Voz / Áudio</div>
                                    <div class="text-[10px] text-zinc-400">Áudio do WhatsApp</div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 pt-1 border-t border-slate-800">
                                <button id="btn-carregar-midia-${m.id}" type="button" onclick="carregarMidiaMensagem(${m.id}, 'audio')" class="flex-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-yellow-400 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow transition cursor-pointer">
                                    Ouvir / Carregar
                                </button>
                                <a href="https://web.whatsapp.com" target="_blank" rel="noopener noreferrer" class="px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-300 text-[11px] font-semibold transition" title="Abrir no WhatsApp Web">
                                    Web
                                </a>
                            </div>
                        </div>
                    `;
                }
                if (textoExibicao.startsWith("\uD83C\uDFA4") || textoExibicao.startsWith("\uD83C\uDFB5")) {
                    textoExibicao = "";
                }
            } else if (ehDocumento) {
                let nomeArq = "documento.pdf";
                const matchNome = textoExibicao.match(/\[(?:Arquivo|Arquivo recebido):\s*([^\]]+)\]/);
                if (matchNome) {
                    nomeArq = matchNome[1].trim();
                    textoExibicao = textoExibicao.replace(/\uD83D\uDCC4\s*\[(?:Arquivo|Arquivo recebido):\s*[^\]]+\]\s*/, "").trim();
                } else if (urlMidia) {
                    nomeArq = urlMidia.split("/").pop() || "documento.pdf";
                }

                if (urlMidia) {
                    htmlMidia = `
                        <div class="mb-2 p-2.5 rounded-xl bg-black/90 border border-slate-700/80 flex items-center gap-3 min-w-[240px] max-w-sm shadow-sm">
                            <div class="w-10 h-10 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs text-yellow-400 font-bold shrink-0">DOC</div>
                            <div class="flex-1 min-w-0">
                                <div class="font-bold text-xs text-zinc-100 truncate" title="${escaparHtml(nomeArq)}">
                                    ${escaparHtml(nomeArq)}
                                </div>
                                <div class="text-[10px] text-zinc-400 mt-0.5">Documento WhatsApp</div>
                            </div>
                            <div class="flex items-center gap-1.5 shrink-0">
                                <a href="${escaparHtml(urlMidia)}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1.5 rounded-lg bg-yellow-400 hover:bg-yellow-300 text-black text-[11px] font-bold shadow transition flex items-center gap-1 shadow">
                                    Ver
                                </a>
                                <a href="${escaparHtml(urlMidia)}" download="${escaparHtml(nomeArq)}" class="px-2 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] font-bold transition" title="Baixar arquivo">
                                    Baixar
                                </a>
                            </div>
                        </div>
                    `;
                } else {
                    htmlMidia = `
                        <div class="mb-2 p-2.5 rounded-xl bg-black/90 border border-amber-500/40 flex flex-col gap-2 min-w-[250px] max-w-sm shadow-sm">
                            <div class="flex items-center gap-2.5">
                                <div class="w-9 h-9 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs text-yellow-400 font-bold shrink-0">DOC</div>
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-xs text-amber-300 truncate" title="${escaparHtml(nomeArq)}">
                                        ${escaparHtml(nomeArq)}
                                    </div>
                                    <div class="text-[10px] text-zinc-400">Documento no WhatsApp</div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 pt-1 border-t border-slate-800">
                                <button id="btn-carregar-midia-${m.id}" type="button" onclick="carregarMidiaMensagem(${m.id}, 'documento')" class="flex-1 px-2.5 py-1.5 rounded-lg bg-yellow-400 hover:bg-yellow-300 text-black font-bold shadow-lg shadow-yellow-500/20 text-xs flex items-center justify-center gap-1.5 shadow transition cursor-pointer">
                                    Carregar Arquivo
                                </button>
                                <a href="https://web.whatsapp.com" target="_blank" rel="noopener noreferrer" class="px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-300 text-[11px] font-semibold transition" title="Abrir no WhatsApp Web">
                                    Web
                                </a>
                            </div>
                        </div>
                    `;
                }
            } else if (ehImagem) {
                if (urlMidia) {
                    htmlMidia = `
                        <div class="mb-2 overflow-hidden rounded-xl border border-white/10 max-w-[280px] sm:max-w-xs cursor-pointer group relative bg-black/30 shadow-md" onclick="abrirModalImagemWa('${escaparHtml(urlMidia)}')">
                            <img src="${escaparHtml(urlMidia)}" alt="Imagem WhatsApp" class="w-full max-h-72 object-cover rounded-xl transition duration-200 group-hover:opacity-90 group-hover:scale-[1.01]" loading="lazy">
                            <div class="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition flex items-center justify-center text-white text-[11px] font-bold gap-1 rounded-xl">
                                Clique para ampliar
                            </div>
                        </div>
                    `;
                    if (textoExibicao.startsWith("\uD83D\uDCF7 [Imagem]")) {
                        textoExibicao = textoExibicao.replace(/^(?:\uD83D\uDCF7|\uD83D\uDCF7)\s*\[Imagem\]\s*/, "").trim();
                    } else if (textoExibicao === "\uD83D\uDCF7 [Imagem recebida]") {
                        textoExibicao = "";
                    }
                } else {
                    const legendaFoto = textoExibicao.replace(/^(?:\uD83D\uDCF7|\uD83D\uDCF7)\s*\[(?:Imagem|Imagem recebida)\]\s*/, "").trim();
                    htmlMidia = `
                        <div class="mb-2 p-2.5 rounded-xl bg-black/90 border border-amber-500/40 flex flex-col gap-2 min-w-[240px] max-w-xs shadow-sm">
                            <div class="flex items-center gap-2 text-[11px] text-slate-200">
                                <div class="w-9 h-9 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs text-yellow-400 font-bold shrink-0">IMG</div>
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-amber-300">Foto / Imagem</div>
                                    <div class="text-[10px] text-zinc-400">Recebida no WhatsApp</div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 pt-1 border-t border-slate-800">
                                <button id="btn-carregar-midia-${m.id}" type="button" onclick="carregarMidiaMensagem(${m.id}, 'imagem')" class="flex-1 px-2.5 py-1.5 rounded-lg bg-yellow-400 hover:bg-yellow-300 text-black font-bold shadow-lg shadow-yellow-500/20 text-xs flex items-center justify-center gap-1.5 shadow transition cursor-pointer">
                                    Carregar Foto
                                </button>
                                <a href="https://web.whatsapp.com" target="_blank" rel="noopener noreferrer" class="px-2 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-zinc-300 text-[11px] font-semibold transition" title="Abrir no WhatsApp Web">
                                    Web
                                </a>
                            </div>
                        </div>
                    `;
                    textoExibicao = legendaFoto;
                }
            }

            const htmlTexto = textoExibicao
                ? `<div class="leading-relaxed whitespace-pre-wrap">${escaparHtml(textoExibicao)}</div>`
                : "";

            return `
                <div class="flex flex-col ${alinhamento}">
                    <div class="max-w-[85%] px-3.5 py-2.5 text-xs ${balao}">
                        ${htmlMidia}
                        ${htmlTexto}
                    </div>
                    <span class="text-[10px] text-zinc-500 mt-1 px-1">${escaparHtml(autorRotulo)} • ${escaparHtml(m.criada_em || "")}${statusIcone}</span>
                </div>
            `;
        })
        .join("");
    box.scrollTop = box.scrollHeight;

    if (chegouNovaEntrada) {
        tocarSomNovaMensagem();
    }
    return chegouNovaEntrada;
}
