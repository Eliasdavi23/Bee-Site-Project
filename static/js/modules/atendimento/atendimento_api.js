// ==========================================================
// CAMADA DE COMUNICAÇÃO HTTP (ATENDIMENTO WHATSAPP & IA)
// ==========================================================

export function extrairMensagemErro(dados, padrao = "Não foi possível concluir a ação.") {
    if (!dados) return padrao;
    if (typeof dados.detail === "string") return dados.detail;
    if (Array.isArray(dados.detail) && dados.detail.length > 0) {
        return dados.detail.map(item => item.msg || JSON.stringify(item)).join("; ");
    }
    return dados.erro || dados.mensagem || padrao;
}

async function requisitarJson(url, opcoes = {}, msgErroPadrao = "Falha na requisição.") {
    const resp = await fetch(url, opcoes);
    const dados = await resp.json().catch(() => ({}));
    if (!resp.ok) {
        throw new Error(extrairMensagemErro(dados, msgErroPadrao));
    }
    return dados;
}

export async function fetchStatusModulo() {
    return requisitarJson("/api/whatsapp/status");
}

export async function fetchBridgeStatus() {
    return requisitarJson("/api/whatsapp/bridge/status");
}

export async function postBridgeIniciar() {
    return requisitarJson("/api/whatsapp/bridge/iniciar", { method: "POST" });
}

export async function postBridgeDesconectar() {
    return requisitarJson("/api/whatsapp/bridge/desconectar", { method: "POST" });
}

export async function fetchDestinatarios() {
    return requisitarJson("/api/whatsapp/destinatarios");
}

export async function postConfigWhatsApp(payload) {
    return requisitarJson("/api/whatsapp/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function fetchConversas(busca = "") {
    return requisitarJson(`/api/whatsapp/conversas?busca=${encodeURIComponent(busca)}`);
}

export async function fetchConversaDetalhe(conversaId, marcarLida = true) {
    return requisitarJson(`/api/whatsapp/conversas/${conversaId}?marcar_lida=${marcarLida ? "true" : "false"}`);
}

export async function postMarcarConversaNaoLida(conversaId) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/marcar-nao-lida`,
        { method: "POST" },
        "Não foi possível marcar a conversa como não lida."
    );
}

export async function postMarcarConversaLida(conversaId) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/marcar-lida`,
        { method: "POST" },
        "Não foi possível marcar a conversa como lida."
    );
}

export async function postMarcarTodasLidas() {
    return requisitarJson(
        "/api/whatsapp/conversas/marcar-todas-lidas",
        { method: "POST" },
        "Não foi possível marcar todas as conversas como lidas."
    );
}

export async function patchConversa(conversaId, payload) {
    return requisitarJson(`/api/whatsapp/conversas/${conversaId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function postSugerirRespostaIA(conversaId) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/sugerir`,
        { method: "POST" },
        "Falha ao gerar sugestão com IA."
    );
}

export async function postGerarPedidoIA(conversaId, atendente = "") {
    const opcoes = { method: "POST" };
    if (atendente) {
        opcoes.headers = { "Content-Type": "application/json" };
        opcoes.body = JSON.stringify({ atendente });
    }
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/gerar-pedido`,
        opcoes,
        "Não foi possível gerar o pedido com IA."
    );
}

export async function postGerarResumoPedidoIA(conversaId) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/resumo-pedido`,
        { method: "POST" },
        "A descrição do pedido pela IA só é liberada após o pedido e o pagamento serem efetuados."
    );
}

export async function postAnalisarComprovanteIA(conversaId, formData) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/comprovante`,
        { method: "POST", body: formData },
        "Não foi possível validar o comprovante de pagamento."
    );
}

export async function postEnviarMensagem(payload) {
    return requisitarJson(
        "/api/whatsapp/enviar",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        },
        "Erro ao enviar mensagem."
    );
}

export async function postEnviarImagem(conversaId, formData) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/enviar-imagem`,
        {
            method: "POST",
            body: formData,
        },
        "Erro ao enviar imagem pelo WhatsApp."
    );
}

export async function postEnviarArquivo(conversaId, formData) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/enviar-arquivo`,
        {
            method: "POST",
            body: formData,
        },
        "Erro ao enviar arquivo pelo WhatsApp."
    );
}

export async function postCarregarMidiaMensagem(mensagemId) {
    return requisitarJson(
        `/api/whatsapp/mensagens/${mensagemId}/carregar-midia`,
        { method: "POST" },
        "Não foi possível carregar a mídia desta mensagem."
    );
}

export async function postCarregarMensagensAnteriores(conversaId) {
    return requisitarJson(
        `/api/whatsapp/conversas/${conversaId}/carregar-anteriores`,
        { method: "POST" },
        "Não foi possível solicitar mensagens anteriores ao WhatsApp."
    );
}

export async function postMensagemManual(payload) {
    return requisitarJson(
        "/api/whatsapp/conversas/manual",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        },
        "Informe um telefone válido com DDD (ex.: 11 98888-7777)."
    );
}
