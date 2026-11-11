/**
 * Controlador principal do Painel de Atendimento WhatsApp + IA (Tempo Real).
 * Segue o padrão modular do projeto (atendimento_api.js + atendimento_ui.js).
 */
import * as api from "./modules/atendimento/atendimento_api.js?v=2026e";
import * as ui from "./modules/atendimento/atendimento_ui.js?v=2026e";

let estado = {
    conversaAtual: null,
    conversas: [],
    totalPendentes: 0,
    statusModulo: null,
    clientes: [],
    modalBridgeAberto: false,
    timerBridge: null,
    imagemSelecionada: null,
};

document.addEventListener("DOMContentLoaded", () => {
    api.postBridgeIniciar().catch(() => {});
    carregarStatusModulo();
    carregarConversas();
    carregarClientesParaSelectManual();

    // Atualização ultrarrápida em tempo real (a cada 1 segundo) sem piscar a tela
    setInterval(() => {
        carregarConversas(true);
        if (estado.conversaAtual) {
            selecionarConversa(estado.conversaAtual.id, true);
        }
    }, 1000);

    // Atualiza o status do topo (conexão QR / IA) a cada 6 segundos
    setInterval(carregarStatusModulo, 6000);

    // Atalho Enter para enviar rápido (Shift+Enter quebra linha)
    const campoResposta = document.getElementById("wa-input-resposta");
    campoResposta?.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            enviarRespostaPainel("web");
        }
    });
});

async function carregarClientesParaSelectManual() {
    try {
        const dados = await api.fetchDestinatarios();
        estado.clientes = dados.clientes || [];
        ui.renderizarSelectClientesManual(estado.clientes);
    } catch (e) {
        console.error("Erro ao carregar clientes:", e);
    }
}

function aoSelecionarClienteManual() {
    const sel = document.getElementById("manual-wa-cliente-id");
    const cid = sel?.value ? Number(sel.value) : null;
    const cli = estado.clientes.find(c => c.id === cid);
    if (cli) {
        document.getElementById("manual-wa-nome").value = cli.nome || "";
        document.getElementById("manual-wa-telefone").value = cli.telefone || "";
    }
}

async function carregarStatusModulo() {
    try {
        estado.statusModulo = await api.fetchStatusModulo();
        window.beeWhatsAppEnvioAutomatico = Boolean(estado.statusModulo?.envio_automatico_ativo);
        ui.renderizarStatusTopo(estado.statusModulo);
    } catch (e) {
        console.error("Erro ao consultar status do WhatsApp:", e);
    }
}

async function salvarConfigWhatsApp() {
    const chkAviso = document.getElementById("chk-wa-aviso-status");
    const chkAuto = document.getElementById("chk-wa-auto-resposta");
    try {
        await api.postConfigWhatsApp({
            aviso_status: Boolean(chkAviso?.checked),
            auto_resposta: Boolean(chkAuto?.checked),
        });
        await carregarStatusModulo();
    } catch (e) {
        console.error("Erro ao salvar configurações:", e);
    }
}

async function carregarConversas(silencioso = false) {
    const busca = document.getElementById("wa-busca-conversa")?.value || "";
    try {
        const dados = await api.fetchConversas(busca);
        estado.conversas = dados.conversas || [];
        estado.totalPendentes = dados.total_precisa_atendente || 0;
        if (estado.conversaAtual) {
            const ativa = estado.conversas.find(c => c.id === estado.conversaAtual.id);
            if (ativa && !ativa._marcadaNaoLidaManualmente) {
                ativa.nao_lidas = 0;
            }
        }
        ui.renderizarListaConversas(estado.conversas, estado.conversaAtual?.id, estado.totalPendentes);
    } catch (e) {
        if (!silencioso) console.error("Erro ao listar conversas:", e);
    }
}

async function selecionarConversa(conversaId, preservarTexto = false) {
    try {
        const convNaLista = estado.conversas.find(c => c.id === conversaId);
        if (convNaLista) {
            convNaLista.nao_lidas = 0;
            convNaLista._marcadaNaoLidaManualmente = false;
        }
        ui.renderizarListaConversas(estado.conversas, conversaId, estado.totalPendentes);

        const dados = await api.fetchConversaDetalhe(conversaId, !preservarTexto);
        estado.conversaAtual = dados.conversa;
        ui.renderizarCabecalhoConversa(dados.conversa, dados.resumo_cliente, preservarTexto);
        ui.renderizarMensagens(dados.mensagens || [], dados.conversa.id);
        ui.renderizarListaConversas(estado.conversas, estado.conversaAtual.id, estado.totalPendentes);
    } catch (e) {
        console.error("Erro ao abrir conversa:", e);
    }
}

function deselecionarConversa() {
    estado.conversaAtual = null;
    document.getElementById("wa-chat-nome").textContent = "Selecione uma conversa";
    document.getElementById("wa-chat-telefone").textContent = "Ou clique em 'Criar Mensagem' no topo";
    const acoes = document.getElementById("wa-chat-acoes");
    acoes?.classList.add("hidden");
    acoes?.classList.remove("flex");

    const msgsBox = document.getElementById("wa-chat-mensagens");
    if (msgsBox) {
        msgsBox.innerHTML = `
            <div class="p-8 text-center text-xs text-slate-500 space-y-3">
                <p>Nenhuma conversa selecionada.</p>
                <button type="button" onclick="abrirModalWhatsApp({})" class="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black px-4 py-2 rounded-xl text-xs transition cursor-pointer">
                    Criar Nova Mensagem para Cliente
                </button>
            </div>
        `;
    }

    const btnAnteriores = document.getElementById("btn-wa-carregar-anteriores");
    if (btnAnteriores) btnAnteriores.disabled = true;
    const btnSugerir = document.getElementById("btn-wa-sugerir-ia");
    if (btnSugerir) btnSugerir.disabled = true;
    const btnResumo = document.getElementById("btn-wa-resumo-pedido");
    if (btnResumo) btnResumo.disabled = true;
    const btnGerar = document.getElementById("btn-wa-gerar-pedido");
    if (btnGerar) btnGerar.disabled = true;
    const btnComprovante = document.getElementById("btn-wa-comprovante");
    if (btnComprovante) btnComprovante.disabled = true;
    const inp = document.getElementById("wa-input-resposta");
    if (inp) {
        inp.value = "";
        inp.disabled = true;
    }
    const btnEnviar = document.getElementById("btn-wa-enviar-resposta");
    if (btnEnviar) btnEnviar.disabled = true;
    const btnWame = document.getElementById("btn-wa-enviar-wame");
    if (btnWame) btnWame.disabled = true;
    const ctx = document.getElementById("wa-contexto-cliente");
    if (ctx) ctx.textContent = "";

    ui.renderizarListaConversas(estado.conversas, null, estado.totalPendentes);
}

async function alternarNaoLidaConversa(conversaId, novoStatusNaoLidas) {
    const conv = estado.conversas.find(c => c.id === conversaId);
    if (conv) {
        conv.nao_lidas = novoStatusNaoLidas;
        conv._marcadaNaoLidaManualmente = novoStatusNaoLidas > 0;
    }

    if (estado.conversaAtual && estado.conversaAtual.id === conversaId && novoStatusNaoLidas > 0) {
        deselecionarConversa();
    } else {
        ui.renderizarListaConversas(estado.conversas, estado.conversaAtual?.id, estado.totalPendentes);
    }

    try {
        if (novoStatusNaoLidas > 0) {
            await api.postMarcarConversaNaoLida(conversaId);
        } else {
            await api.postMarcarConversaLida(conversaId);
        }
    } catch (e) {
        console.error("Erro ao alterar status não lida:", e);
    }
}

async function marcarConversaNaoLidaAtual() {
    if (!estado.conversaAtual) return;
    const cid = estado.conversaAtual.id;
    await alternarNaoLidaConversa(cid, 1);
}

async function marcarTodasConversasComoLidas() {
    const btn = document.getElementById("btn-marcar-todas-lidas");
    const totalNaoLidas = estado.conversas.reduce((acc, c) => acc + (Number(c.nao_lidas) || 0), 0);

    // 1. Atualização otimista imediata na interface
    estado.conversas.forEach(c => {
        c.nao_lidas = 0;
        c._marcadaNaoLidaManualmente = false;
    });
    ui.renderizarListaConversas(estado.conversas, estado.conversaAtual?.id, estado.totalPendentes);

    // Zera contadores visuais e pings
    const badgeNaoLidas = document.getElementById("wa-contador-nao-lidas");
    if (badgeNaoLidas) {
        badgeNaoLidas.classList.add("hidden");
        badgeNaoLidas.classList.remove("inline-flex");
    }
    const sideCont = document.getElementById("nav-wa-ping-container");
    const topCont = document.getElementById("top-wa-ping-container");
    if (sideCont) {
        sideCont.classList.add("hidden");
        sideCont.classList.remove("inline-flex");
    }
    if (topCont) {
        topCont.classList.add("hidden");
        topCont.classList.remove("inline-flex");
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="hidden sm:inline">Todas lidas!</span>`;
    }

    try {
        await api.postMarcarTodasLidas();
    } catch (e) {
        console.error("Erro ao marcar todas as conversas como lidas:", e);
        await carregarConversas(true);
    } finally {
        setTimeout(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<span class="hidden sm:inline">Ler todas</span>`;
            }
        }, 2000);
    }
}

async function pedirSugestaoIA() {
    if (!estado.conversaAtual) return;
    const btn = document.getElementById("btn-wa-sugerir-ia");
    const campo = document.getElementById("wa-input-resposta");
    const feedback = document.getElementById("wa-feedback-envio");

    btn.disabled = true;
    feedback.textContent = "Consultando pedidos e gerando resposta...";

    try {
        const dados = await api.postSugerirRespostaIA(estado.conversaAtual.id);
        campo.value = dados.texto || "";
        feedback.textContent =
            dados.origem === "ia" ? "Sugestão gerada pela IA" : dados.aviso || "Sugestão pronta";
        campo.focus();
    } catch (e) {
        feedback.textContent = e.message || "Erro ao sugerir resposta.";
    } finally {
        btn.disabled = false;
    }
}

async function gerarPedidoComIA() {
    if (!estado.conversaAtual) return;
    const btn = document.getElementById("btn-wa-gerar-pedido");
    const feedback = document.getElementById("wa-feedback-envio");
    const atendenteEl = document.getElementById("wa-atendente-logado");
    const atendente = (atendenteEl && atendenteEl.textContent) ? atendenteEl.textContent.trim() : "";

    if (btn) btn.disabled = true;
    if (feedback) feedback.textContent = "Analisando conversa e gerando pedido com IA...";

    try {
        const dados = await api.postGerarPedidoIA(estado.conversaAtual.id, atendente);
        if (dados.aguardando_nome) {
            if (feedback) {
                feedback.textContent = "Pergunta enviada ao cliente no WhatsApp: 'Em qual nome podemos gerar o pedido?'";
            }
            BeeHUD.alert({
                titulo: "Aguardando Nome do Cliente",
                mensagem: "Cliente ainda sem nome informado.\n\nA IA acabou de enviar a mensagem no WhatsApp:\n\"Em qual nome podemos gerar o pedido?\"\n\nAssim que o cliente responder com o nome, o sistema cadastrará o cliente e criará o pedido automaticamente!",
                tipo: "info"
            });
        } else if (dados.pedido_id) {
            const atendenteMsg = dados.atendente ? ` (Atendente: ${dados.atendente})` : "";
            if (feedback) {
                feedback.textContent = `Pedido #${dados.pedido_id} criado com sucesso para ${dados.cliente_nome}${atendenteMsg}!`;
            }
            const boxResumo = document.getElementById("wa-box-resumo-pedido");
            const txtResumo = document.getElementById("wa-texto-resumo-pedido");
            const obsTexto = dados.observacao ? `\nObs: ${dados.observacao}` : "";
            const itemTexto = dados.item_principal || dados.descricao_pedido || "Item";
            const qtdTexto = dados.quantidade || 1;
            if (boxResumo && txtResumo) {
                txtResumo.textContent = `Pedido #${dados.pedido_id} (${dados.cliente_nome})${atendenteMsg}\nItem: ${itemTexto}\nQtd: ${qtdTexto}${obsTexto}\nValor Total: R$ ${Number(dados.valor_total || 0).toFixed(2)} (Aguardando 50% de entrada)`;
                boxResumo.classList.remove("hidden");
            }
            BeeHUD.alert({
                titulo: "Pedido Criado com Sucesso",
                mensagem: `Pedido #${dados.pedido_id} criado com sucesso para ${dados.cliente_nome}${atendenteMsg}!\n\n` +
                    `Item: ${itemTexto}\n` +
                    `Quantidade: ${qtdTexto}` +
                    obsTexto + `\n` +
                    `Valor Total: R$ ${Number(dados.valor_total || 0).toFixed(2)}\n\n` +
                    "Mensagem de confirmação enviada ao cliente no WhatsApp solicitando o comprovante de 50% de entrada.",
                tipo: "success"
            });
        }
        await selecionarConversa(estado.conversaAtual.id, true);
    } catch (e) {
        if (feedback) feedback.textContent = e.message || "Erro ao gerar pedido com IA.";
        BeeHUD.error(e.message || "Erro ao gerar pedido com IA.");
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function gerarResumoDescricaoPedidoIA() {
    if (!estado.conversaAtual) return;
    const btn = document.getElementById("btn-wa-resumo-pedido");
    const boxResumo = document.getElementById("wa-box-resumo-pedido");
    const txtResumo = document.getElementById("wa-texto-resumo-pedido");
    const feedback = document.getElementById("wa-feedback-envio");

    if (btn) btn.disabled = true;
    if (feedback) feedback.textContent = "Analisando conversa e verificando pagamento do pedido...";

    try {
        const dados = await api.postGerarResumoPedidoIA(estado.conversaAtual.id);
        if (boxResumo && txtResumo) {
            txtResumo.textContent = dados.descricao_pedido || "";
            boxResumo.classList.remove("hidden");
        }
        if (feedback) {
            feedback.textContent = `Descrição gerada e salva no Pedido #${dados.pedido_id}!`;
        }
        await selecionarConversa(estado.conversaAtual.id, true);
    } catch (e) {
        if (feedback) feedback.textContent = e.message || "Pagamento ainda não efetuado.";
        BeeHUD.warning(e.message || "A descrição do pedido só é liberada após o pedido e o pagamento serem efetuados.");
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function enviarComprovanteParaAnaliseIA(event) {
    const file = event?.target?.files?.[0];
    if (!estado.conversaAtual) return;
    const feedback = document.getElementById("wa-feedback-envio");
    if (feedback) feedback.textContent = "Analisando imagem de comprovante com IA...";

    const formData = new FormData();
    if (file) {
        formData.append("arquivo", file);
    }
    formData.append("legenda", "[Imagem de comprovante enviada para análise]");

    try {
        const dados = await api.postAnalisarComprovanteIA(estado.conversaAtual.id, formData);
        const percTxt = dados.percentual === 50 ? "50% PAGO" : "100% PAGO";
        if (feedback) {
            feedback.textContent = `Pedido #${dados.pedido_id} atualizado para ${percTxt}! Mensagem de confirmação enviada ao cliente!`;
        }
        const boxResumo = document.getElementById("wa-box-resumo-pedido");
        const txtResumo = document.getElementById("wa-texto-resumo-pedido");
        if (boxResumo && txtResumo) {
            txtResumo.textContent = `Pagamento ${percTxt} confirmado no Pedido #${dados.pedido_id}!\nValor pago: R$ ${Number(dados.valor_pago || 0).toFixed(2)} de R$ ${Number(dados.valor_total || 0).toFixed(2)}`;
            boxResumo.classList.remove("hidden");
        }
        BeeHUD.alert({
            titulo: "Comprovante Validado",
            mensagem: `Comprovante validado com sucesso!\n\nPedido #${dados.pedido_id} atualizado para ${percTxt} na aba Pedidos.\nMensagem automática de confirmação enviada ao cliente no WhatsApp!`,
            tipo: "success"
        });
        await selecionarConversa(estado.conversaAtual.id, true);
    } catch (e) {
        if (feedback) feedback.textContent = e.message || "Não foi possível validar o comprovante.";
        BeeHUD.error(e.message || "Erro ao analisar comprovante.");
    } finally {
        if (event?.target) event.target.value = "";
    }
}

function aoSelecionarImagemChat(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;

    if (file.size > 25 * 1024 * 1024) {
        BeeHUD.warning("O arquivo excede o tamanho máximo permitido de 25MB.");
        return;
    }

    estado.imagemSelecionada = file;

    const barra = document.getElementById("wa-preview-imagem-barra");
    const thumb = document.getElementById("wa-preview-img-thumb");
    const docIcon = document.getElementById("wa-preview-doc-icon");
    const nome = document.getElementById("wa-preview-img-nome");
    const desc = document.getElementById("wa-preview-tipo-desc");

    if (file.type.startsWith("image/")) {
        if (thumb) {
            thumb.classList.remove("hidden");
            const reader = new FileReader();
            reader.onload = (e) => {
                thumb.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
        docIcon?.classList.add("hidden");
        docIcon?.classList.remove("flex");
        if (desc) desc.textContent = "Imagem pronta para enviar (digite legenda abaixo se desejar)";
    } else {
        thumb?.classList.add("hidden");
        if (docIcon) {
            docIcon.innerHTML = file.type.startsWith("audio/") ? "Audio" : "Doc";
            docIcon.classList.remove("hidden");
            docIcon.classList.add("flex");
        }
        if (desc) desc.textContent = "Documento pronto para enviar (digite legenda abaixo se desejar)";
    }

    if (nome) nome.textContent = file.name;
    barra?.classList.remove("hidden");
    barra?.classList.add("flex");

    const campoResposta = document.getElementById("wa-input-resposta");
    campoResposta?.focus();
}

function cancelarImagemSelecionada() {
    estado.imagemSelecionada = null;
    const inp = document.getElementById("wa-input-imagem-chat");
    if (inp) inp.value = "";
    const barra = document.getElementById("wa-preview-imagem-barra");
    barra?.classList.add("hidden");
    barra?.classList.remove("flex");
}

function abrirModalImagemWa(url) {
    const modal = document.getElementById("modal-wa-imagem");
    const img = document.getElementById("wa-modal-img-src");
    const link = document.getElementById("wa-modal-img-link");
    if (img) img.src = url;
    if (link) link.href = url;
    modal?.classList.remove("hidden");
    modal?.classList.add("flex");
}

function fecharModalImagemWa(e) {
    if (e && e.target !== e.currentTarget && e.target.tagName !== "BUTTON") return;
    const modal = document.getElementById("modal-wa-imagem");
    modal?.classList.add("hidden");
    modal?.classList.remove("flex");
}

async function enviarRespostaPainel(modoAbertura = "web") {
    if (!estado.conversaAtual) return;
    const campo = document.getElementById("wa-input-resposta");
    const btn = document.getElementById("btn-wa-enviar-resposta");
    const btnWame = document.getElementById("btn-wa-enviar-wame");
    const feedback = document.getElementById("wa-feedback-envio");
    const texto = (campo.value || "").trim();

    // Se houver um arquivo/imagem selecionado para envio
    if (estado.imagemSelecionada) {
        const formData = new FormData();
        formData.append("arquivo", estado.imagemSelecionada);
        formData.append("imagem", estado.imagemSelecionada); // compatibilidade
        formData.append("legenda", texto);

        btn.disabled = true;
        if (btnWame) btnWame.disabled = true;
        if (feedback) feedback.textContent = "Enviando arquivo pelo WhatsApp...";

        try {
            await api.postEnviarArquivo(estado.conversaAtual.id, formData);
            campo.value = "";
            cancelarImagemSelecionada();
            if (feedback) feedback.textContent = "Arquivo enviado com sucesso!";
            await selecionarConversa(estado.conversaAtual.id, true);
            await carregarConversas(true);
        } catch (e) {
            if (feedback) feedback.textContent = e.message || "Erro ao enviar arquivo.";
            BeeHUD.error(e.message || "Erro ao enviar arquivo.");
        } finally {
            btn.disabled = false;
            if (btnWame) btnWame.disabled = false;
        }
        return;
    }

    if (!texto) {
        feedback.textContent = "Digite uma mensagem antes de enviar.";
        return;
    }

    const envioDiretoAtivo = Boolean(estado.statusModulo?.envio_automatico_ativo) && modoAbertura !== "wame";
    // Só abre nova aba se NÃO estiver conectado em tempo real (ou se o operador clicou explicitamente em wa.me)
    const novaAba = envioDiretoAtivo ? null : window.open("about:blank", "_blank");
    btn.disabled = true;
    if (btnWame) btnWame.disabled = true;

    try {
        const dados = await api.postEnviarMensagem({
            conversa_id: estado.conversaAtual.id,
            texto: texto,
            assumir_conversa: true,
        });

        campo.value = "";
        if (dados.enviado && modoAbertura !== "wame") {
            if (novaAba) novaAba.close();
            feedback.textContent = "Enviada em tempo real!";
        } else {
            const urlDestino = modoAbertura === "web" ? dados.link_web || dados.link : dados.link || dados.link_web;
            feedback.textContent = "WhatsApp aberto em nova aba!";
            if (novaAba && urlDestino) {
                novaAba.location.href = urlDestino;
            } else if (urlDestino) {
                window.open(urlDestino, "_blank", "noopener,noreferrer");
            }
        }
        await selecionarConversa(estado.conversaAtual.id, true);
        await carregarConversas(true);
    } catch (e) {
        if (novaAba) novaAba.close();
        feedback.textContent = e.message || "Erro ao enviar.";
    } finally {
        btn.disabled = false;
        if (btnWame) btnWame.disabled = false;
    }
}

async function alternarModoAutoConversa() {
    const c = estado.conversaAtual;
    if (!c) return;
    await api.patchConversa(c.id, { modo_auto: !Boolean(c.modo_auto), precisa_atendente: false });
    await selecionarConversa(c.id, true);
    await carregarConversas(true);
}

// ==========================================================
// MODAL DE CONEXÃO QR CODE EM TEMPO REAL
// ==========================================================
async function abrirModalBridgeQR() {
    estado.modalBridgeAberto = true;
    const modal = document.getElementById("modal-bridge-qr");
    modal?.classList.remove("hidden");
    modal?.classList.add("flex");

    try {
        const st = await api.postBridgeIniciar();
        ui.renderizarModalBridge(st);
    } catch (e) {
        console.error("Erro ao iniciar ponte:", e);
    }

    if (estado.timerBridge) clearInterval(estado.timerBridge);
    estado.timerBridge = setInterval(atualizarStatusBridgeModal, 2000);
}

function fecharModalBridgeQR() {
    estado.modalBridgeAberto = false;
    if (estado.timerBridge) {
        clearInterval(estado.timerBridge);
        estado.timerBridge = null;
    }
    const modal = document.getElementById("modal-bridge-qr");
    modal?.classList.add("hidden");
    modal?.classList.remove("flex");
    carregarStatusModulo();
}

async function atualizarStatusBridgeModal() {
    if (!estado.modalBridgeAberto) return;
    try {
        const st = await api.fetchBridgeStatus();
        ui.renderizarModalBridge(st);
        if (st.conectado) {
            carregarStatusModulo();
        }
    } catch (e) {
        console.error("Erro ao consultar QR Code:", e);
    }
}

async function desconectarBridgeAparelho() {
    const ok = await BeeHUD.confirm({
        titulo: "Desconectar WhatsApp",
        mensagem: "Deseja desconectar o WhatsApp atual e gerar um novo QR Code?",
        confirmTexto: "Sim, desconectar",
        tipo: "warning"
    });
    if (!ok) return;
    try {
        const st = await api.postBridgeDesconectar();
        ui.renderizarModalBridge(st);
        BeeHUD.success("WhatsApp desconectado com sucesso.");
        await carregarStatusModulo();
    } catch (e) {
        console.error("Erro ao desconectar aparelho:", e);
        BeeHUD.error("Erro ao desconectar aparelho.");
    }
}

function abrirModalNovaMensagemCliente() {
    carregarClientesParaSelectManual();
    document.getElementById("manual-wa-erro")?.classList.add("hidden");
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
    const clienteIdVal = document.getElementById("manual-wa-cliente-id")?.value;
    const telefone = document.getElementById("manual-wa-telefone")?.value || "";
    const nome = document.getElementById("manual-wa-nome")?.value || "";
    const texto = document.getElementById("manual-wa-texto")?.value || "";
    const btn = document.getElementById("btn-salvar-manual-wa");
    const erroBox = document.getElementById("manual-wa-erro");

    erroBox?.classList.add("hidden");
    if (btn) btn.disabled = true;

    try {
        const dados = await api.postMensagemManual({
            cliente_id: clienteIdVal ? Number(clienteIdVal) : null,
            telefone: telefone,
            nome_contato: nome,
            texto: texto,
        });

        fecharModalNovaMensagemCliente();
        document.getElementById("manual-wa-texto").value = "";
        await carregarConversas();
        await selecionarConversa(dados.conversa_id);
        if (dados.sugestao?.texto) {
            document.getElementById("wa-input-resposta").value = dados.sugestao.texto;
            document.getElementById("wa-feedback-envio").textContent =
                dados.sugestao.origem === "ia"
                    ? "Resposta sugerida pela IA pronta para enviar!"
                    : "Resposta padrão pronta para enviar!";
        }
    } catch (e) {
        if (erroBox) {
            erroBox.textContent = e.message || "Erro ao registrar mensagem.";
            erroBox.classList.remove("hidden");
        } else {
            BeeHUD.error(e.message || "Erro ao registrar mensagem.");
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function carregarMidiaMensagem(mensagemId, tipo = "midia") {
    const btn = document.getElementById(`btn-carregar-midia-${mensagemId}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="inline-block w-3.5 h-3.5 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></span> Carregando...`;
    }
    try {
        const dados = await api.postCarregarMidiaMensagem(mensagemId);
        if (dados.sucesso && dados.midia_url) {
            if (estado.conversaAtual) {
                await selecionarConversa(estado.conversaAtual.id, true);
            }
        } else {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `Tentar novamente`;
            }
            if (dados.link_web) {
                const abrir = await BeeHUD.confirm({
                    titulo: "Mídia Externa",
                    mensagem: `${dados.mensagem || "Mídia não encontrada no cache local."}\n\nDeseja abrir a conversa no WhatsApp Web para ouvir/baixar diretamente?`,
                    confirmTexto: "Abrir WhatsApp Web",
                    tipo: "question"
                });
                if (abrir) window.open(dados.link_web, "_blank");
            } else {
                BeeHUD.warning(dados.mensagem || "Não foi possível carregar a mídia.");
            }
        }
    } catch (e) {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `Tentar novamente`;
        }
        BeeHUD.error(e.message || "Erro ao carregar mídia.");
    }
}

async function carregarMensagensAnteriores() {
    if (!estado.conversaAtual) return;
    const btn = document.getElementById("btn-wa-carregar-anteriores");
    const feedback = document.getElementById("wa-feedback-envio");

    if (btn) btn.disabled = true;
    if (feedback) feedback.textContent = "Buscando mensagens anteriores no WhatsApp...";

    try {
        const resp = await api.postCarregarMensagensAnteriores(estado.conversaAtual.id);
        if (feedback) {
            feedback.textContent = resp.mensagem || "Histórico solicitado ao WhatsApp!";
        }
        setTimeout(async () => {
            if (estado.conversaAtual) {
                await selecionarConversa(estado.conversaAtual.id, true);
            }
        }, 1500);
    } catch (e) {
        if (feedback) feedback.textContent = e.message || "Erro ao buscar histórico.";
    } finally {
        if (btn) btn.disabled = false;
    }
}

window.carregarMensagensAnteriores = carregarMensagensAnteriores;
window.carregarMidiaMensagem = carregarMidiaMensagem;
window.aoSelecionarImagemChat = aoSelecionarImagemChat;
window.cancelarImagemSelecionada = cancelarImagemSelecionada;
window.abrirModalImagemWa = abrirModalImagemWa;
window.fecharModalImagemWa = fecharModalImagemWa;
window.abrirModalNovaMensagemCliente = abrirModalNovaMensagemCliente;
window.fecharModalNovaMensagemCliente = fecharModalNovaMensagemCliente;
window.registrarMensagemManual = registrarMensagemManual;
window.aoSelecionarClienteManual = aoSelecionarClienteManual;
window.selecionarConversa = selecionarConversa;
window.pedirSugestaoIA = pedirSugestaoIA;
window.gerarPedidoComIA = gerarPedidoComIA;
window.gerarResumoDescricaoPedidoIA = gerarResumoDescricaoPedidoIA;
window.enviarComprovanteParaAnaliseIA = enviarComprovanteParaAnaliseIA;
window.enviarRespostaPainel = enviarRespostaPainel;
window.alternarModoAutoConversa = alternarModoAutoConversa;
window.salvarConfigWhatsApp = salvarConfigWhatsApp;
window.carregarConversas = carregarConversas;
window.abrirModalBridgeQR = abrirModalBridgeQR;
window.fecharModalBridgeQR = fecharModalBridgeQR;
window.desconectarBridgeAparelho = desconectarBridgeAparelho;
window.atualizarStatusBridgeModal = atualizarStatusBridgeModal;
window.marcarConversaNaoLidaAtual = marcarConversaNaoLidaAtual;
window.marcarTodasConversasComoLidas = marcarTodasConversasComoLidas;
window.alternarNaoLidaConversa = alternarNaoLidaConversa;
window.deselecionarConversa = deselecionarConversa;
