let pedidoCarregado = false;
let modeloAtual = 'orcamento';
let tipoDocumentoAtual = 'pedido';

document.addEventListener("DOMContentLoaded", async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const pedidoId = urlParams.get("id");
    const tipo = urlParams.get("tipo");
    tipoDocumentoAtual = (tipo === 'orcamento') ? 'orcamento' : 'pedido';

    if (!pedidoId) {
        mostrarMensagemSemDocumento();
        return;
    }

    await carregarPedidoParaImpressao(pedidoId, tipo);
});

function formatCurrency(value) {
    return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

async function carregarPedidoParaImpressao(pedidoId, tipo) {
    try {
        const rotaBase = (tipo === 'orcamento') ? '/api/orcamentos' : '/api/pedidos';

        const resPedido = await fetch(rotaBase);
        if (!resPedido.ok) throw new Error("Erro ao carregar lista de documentos");
        const pedidos = await resPedido.json();
        const pedido = pedidos.find(p => String(p.id) === String(pedidoId));

        if (!pedido) {
            alert("Documento não encontrado no servidor!");
            window.location.href = "/imprimir";
            return;
        }

        let itens = [];
        try {
            if (pedido.itens && Array.isArray(pedido.itens)) {
                itens = pedido.itens;
            } else {
                const resItens = await fetch(`${rotaBase}/${pedidoId}/itens`);
                if (resItens.ok) {
                    itens = await resItens.json();
                }
            }
        } catch (err) {
            console.warn("Aviso: Não foi possível carregar os itens específicos.");
        }

        let imagens = [];
        try {
            if (tipo !== 'orcamento') {
                const resImagens = await fetch(`/api/pedidos/${pedidoId}/imagens`);
                if (resImagens.ok) {
                    imagens = await resImagens.json();
                }
            }
        } catch (err) {
            console.warn("Aviso: Não foi possível carregar as imagens do pedido.");
        }

        preencherDadosImpressao(pedido, itens, imagens);
        pedidoCarregado = true;
        alternarModelo(modeloAtual);

    } catch (e) {
        console.error("Erro ao carregar dados para impressão:", e);
        alert("Erro ao carregar os dados do documento.");
    }
}

let todosOsDocumentosCache = [];

async function mostrarMensagemSemDocumento() {
    try {
        const [pedidosRes, orcamentosRes] = await Promise.all([
            fetch('/api/pedidos'),
            fetch('/api/orcamentos')
        ]);

        const pedidos = pedidosRes.ok ? await pedidosRes.json() : [];
        const orcamentos = orcamentosRes.ok ? await orcamentosRes.json() : [];

        todosOsDocumentosCache = [...pedidos, ...orcamentos];
    } catch (err) {
        console.warn('Não foi possível carregar os documentos para seleção:', err);
        todosOsDocumentosCache = [];
    }

    const conteudoPrincipal = document.querySelector(".min-h-screen");
    if (!conteudoPrincipal) return;

    conteudoPrincipal.innerHTML = `
        <div class="max-w-xl mx-auto bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl space-y-4 mt-10">
            <h2 class="text-xl font-bold text-amber-400">Nenhum documento informado</h2>
            <p class="text-xs text-slate-400">Selecione um pedido ou orçamento abaixo para visualizar e imprimir.</p>

            <div class="relative">
                <input type="text" id="filtro-documentos" placeholder="🔍 Busque por código ou cliente..." oninput="filtrarListaDocumentos()" autocomplete="off" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-4 py-2.5 outline-none focus:border-amber-400 text-xs font-medium">
            </div>

            <div id="lista-documentos-container" class="space-y-2 max-h-80 overflow-y-auto pr-1"></div>

            <div class="pt-2 flex gap-2">
                <a href="/pedidos" class="flex-1 text-center bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-2.5 rounded-xl text-xs transition">Voltar para Pedidos</a>
                <a href="/orcamentos" class="flex-1 text-center bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-2.5 rounded-xl text-xs transition">Voltar para Orçamentos</a>
            </div>
        </div>
    `;

    renderizarListaDocumentos(todosOsDocumentosCache);
}

function renderizarListaDocumentos(documentos) {
    const container = document.getElementById('lista-documentos-container');
    if (!container) return;

    if (!documentos || documentos.length === 0) {
        container.innerHTML = '<p class="text-xs text-slate-500 text-center py-4">Nenhum documento encontrado.</p>';
        return;
    }

    const html = documentos.map(doc => {
        const tipo = doc.tipo === 'ORCAMENTO' ? 'Orçamento' : 'Pedido';
        const tipoHref = doc.tipo === 'ORCAMENTO' ? 'orcamento' : 'pedido';
        const total = Number(doc.valor_total || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        return `
            <a href="/imprimir?id=${doc.id}&tipo=${tipoHref}" class="block p-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl transition">
                <div class="flex justify-between items-center gap-2">
                    <div>
                        <span class="font-bold text-amber-400">#${doc.id}</span>
                        <span class="ml-2 text-slate-200">${doc.cliente_nome || 'Cliente'}</span>
                    </div>
                    <div class="text-right">
                        <span class="text-emerald-400 font-bold text-xs">${total}</span>
                        <span class="block text-[10px] text-slate-500">${tipo}</span>
                    </div>
                </div>
            </a>
        `;
    }).join('');

    container.innerHTML = html;
}

function filtrarListaDocumentos() {
    const input = document.getElementById('filtro-documentos');
    if (!input) return;

    const termo = input.value.toLowerCase().trim();
    const filtrados = todosOsDocumentosCache.filter(doc => {
        const id = String(doc.id || '').toLowerCase();
        const cliente = String(doc.cliente_nome || '').toLowerCase();
        const tipo = String(doc.tipo || '').toLowerCase();
        return id.includes(termo) || cliente.includes(termo) || tipo.includes(termo);
    });

    renderizarListaDocumentos(filtrados);
}

function preencherDadosImpressao(p, itens, imagens = []) {
    const lblTopo = document.getElementById("lbl-id-topo");
    if (lblTopo) lblTopo.textContent = p.id;

    const subtotalCalc = (p.valor_total || 0) + (p.desconto || 0);
    const valorPago = Number(p.valor_pago || 0);
    const valorRestante = Math.max(0, Number(p.valor_total || 0) - valorPago);
    const tituloDocumento = tipoDocumentoAtual === 'orcamento' ? 'ORÇAMENTO' : 'PEDIDO';
    const subtituloDocumento = tipoDocumentoAtual === 'orcamento' ? 'Documento de proposta comercial' : 'Comprovante de venda';

    const preencherTexto = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    const preencherHtml = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = value;
    };

    const montarItens = (prefixo) => {
        if (!Array.isArray(itens)) return "";

        return itens.map(i => {
            const qtd = i.quantidade || 0;
            const preco = i.preco_unitario || 0;
            const totalItem = qtd * preco;
            const nomeProd = i.nome_produto || i.produto_nome || "Produto";

            return `
                <tr>
                    <td class="py-2 font-bold">${qtd}</td>
                    <td class="py-2">${nomeProd}</td>
                    <td class="py-2 text-right">${formatCurrency(preco)}</td>
                    <td class="py-2 text-right font-bold">${formatCurrency(totalItem)}</td>
                </tr>
            `;
        }).join("");
    };

    const headerOrcamento = document.querySelector('#layout-orcamento h2');
    if (headerOrcamento) headerOrcamento.textContent = tituloDocumento;

    const subHeaderOrcamento = document.querySelector('#layout-orcamento p.text-xs.text-slate-600');
    if (subHeaderOrcamento) subHeaderOrcamento.textContent = subtituloDocumento;

    preencherTexto("c-id", p.id);
    preencherTexto("c-data", p.data || "-");
    preencherTexto("c-cliente", p.cliente_nome || "Cliente");
    preencherTexto("c-atendente", p.usuario_nome || p.atendente || "Sistema");
    preencherTexto("c-producao", p.status_producao || "-");
    preencherTexto("c-pagamento", p.status_pagamento || "-");
    preencherTexto("c-formapag", p.forma_pagamento || "Não informada");
    preencherTexto("c-subtotal", formatCurrency(subtotalCalc));
    preencherTexto("c-desconto", formatCurrency(p.desconto || 0));
    preencherTexto("c-valor-pago", formatCurrency(valorPago));
    preencherTexto("c-total", formatCurrency(valorRestante));
    preencherHtml("c-itens", itens.length ? montarItens("c") : "<tr><td colspan='4' class='py-3 text-slate-500'>Nenhum item informado.</td></tr>");

    preencherTexto("os-id", p.id);
    preencherTexto("os-data", p.data || "-");
    preencherTexto("os-cliente", p.cliente_nome || "Cliente");
    preencherTexto("os-atendente", p.usuario_nome || p.atendente || "Sistema");
    preencherTexto("os-formapag", p.forma_pagamento || "Não informada");
    preencherTexto("os-pagamento", p.status_pagamento || "-");
    preencherTexto("os-obs", p.observacao || "Nenhuma observação registrada.");
    preencherHtml("os-itens", itens.length ? montarItens("os") : "<tr><td colspan='4' class='py-3 text-slate-500'>Nenhum item informado.</td></tr>");
    preencherTexto("os-subtotal", formatCurrency(subtotalCalc));
    preencherTexto("os-desconto", formatCurrency(p.desconto || 0));
    preencherTexto("os-valor-pago", formatCurrency(valorPago));
    preencherTexto("os-total", formatCurrency(valorRestante));

    preencherTexto("orc-id", p.id);
    preencherTexto("orc-data", p.data || "-");
    preencherTexto("orc-cliente", p.cliente_nome || "Cliente");
    preencherTexto("orc-atendente", p.usuario_nome || p.atendente || "Sistema");
    preencherTexto("orc-formapag", p.forma_pagamento || "Não informada");
    preencherTexto("orc-pagamento", p.status_pagamento || "-");
    preencherTexto("orc-obs", p.observacao || "Nenhuma observação registrada.");
    preencherHtml("orc-itens", itens.length ? montarItens("orc") : "<tr><td colspan='4' class='py-3 text-slate-500'>Nenhum item informado.</td></tr>");
    preencherTexto("orc-subtotal", formatCurrency(subtotalCalc));
    preencherTexto("orc-desconto", formatCurrency(p.desconto || 0));
    preencherTexto("orc-valor-pago", formatCurrency(valorPago));
    preencherTexto("orc-total", formatCurrency(valorRestante));
}

function alternarModelo(tipo) {
    modeloAtual = tipo;

    const modelos = ["cupom", "os", "orcamento"];
    modelos.forEach(modelo => {
        const el = document.getElementById(`layout-${modelo}`);
        if (el) {
            el.classList.toggle("ativo", modelo === tipo);
        }
    });

    const botoes = {
        cupom: document.getElementById("btn-cupom"),
        os: document.getElementById("btn-os"),
        orcamento: document.getElementById("btn-orcamento")
    };

    Object.entries(botoes).forEach(([key, button]) => {
        if (!button) return;
        button.className = `px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${key === tipo ? "bg-amber-400 text-slate-950" : "bg-slate-800 text-slate-300"}`;
    });
}

function validarEImprimir() {
    if (!pedidoCarregado) {
        alert("Aguarde o carregamento completo do documento antes de imprimir!");
        return;
    }

    setTimeout(() => {
        window.print();
    }, 400);
}