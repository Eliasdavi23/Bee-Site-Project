export function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function renderizarSeletorDocumentos(documentos) {
    const principal = document.querySelector('.min-h-screen');
    if (!principal) return;
    principal.innerHTML = `<div class="max-w-xl mx-auto bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl space-y-4 mt-10"><h2 class="text-xl font-bold text-amber-400">Nenhum documento informado</h2><p class="text-xs text-slate-400">Selecione um pedido ou orçamento abaixo para visualizar e imprimir.</p><div class="relative"><input type="text" id="filtro-documentos" placeholder="Busque por código ou cliente..." oninput="filtrarListaDocumentos()" autocomplete="off" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-4 py-2.5 outline-none focus:border-amber-400 text-xs font-medium"></div><div id="lista-documentos-container" class="space-y-2 max-h-80 overflow-y-auto pr-1"></div><div class="pt-2 flex gap-2"><a href="/pedidos" class="flex-1 text-center bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-2.5 rounded-xl text-xs transition">Voltar para Pedidos</a><a href="/orcamentos" class="flex-1 text-center bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-2.5 rounded-xl text-xs transition">Voltar para Orçamentos</a></div></div>`;
    renderizarListaDocumentos(documentos);
}

export function renderizarListaDocumentos(documentos) {
    const container = document.getElementById('lista-documentos-container');
    if (!container) return;
    if (!documentos.length) {
        container.innerHTML = '<p class="text-xs text-slate-500 text-center py-4">Nenhum documento encontrado.</p>';
        return;
    }
    container.innerHTML = documentos.map(doc => {
        const tipoOrcamento = doc.tipo === 'ORCAMENTO';
        return `<a href="/imprimir?id=${doc.id}&tipo=${tipoOrcamento ? 'orcamento' : 'pedido'}" class="block p-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl transition"><div class="flex justify-between items-center gap-2"><div><span class="font-bold text-amber-400">#${doc.id}</span><span class="ml-2 text-slate-200">${doc.cliente_nome || 'Cliente'}</span></div><div class="text-right"><span class="text-emerald-400 font-bold text-xs">${formatarMoeda(doc.valor_total)}</span><span class="block text-[10px] text-slate-500">${tipoOrcamento ? 'Orçamento' : 'Pedido'}</span></div></div></a>`;
    }).join('');
}

export function preencherDocumento(pedido, itens, tipoDocumento) {
    const preencherTexto = (id, valor) => { const el = document.getElementById(id); if (el) el.textContent = valor; };
    const preencherHtml = (id, valor) => { const el = document.getElementById(id); if (el) el.innerHTML = valor; };
    const subtotal = Number(pedido.valor_total || 0) + Number(pedido.desconto || 0);
    const pago = Number(pedido.valor_pago || 0);
    const restante = Math.max(0, Number(pedido.valor_total || 0) - pago);
    const linhas = itens.length ? itens.map(item => `<tr><td class="py-2 font-bold">${item.quantidade || 0}</td><td class="py-2">${item.nome_produto || item.produto_nome || 'Produto'}</td><td class="py-2 text-right">${formatarMoeda(item.preco_unitario)}</td><td class="py-2 text-right font-bold">${formatarMoeda((item.quantidade || 0) * (item.preco_unitario || 0))}</td></tr>`).join('') : "<tr><td colspan='4' class='py-3 text-slate-500'>Nenhum item informado.</td></tr>";
    const titulo = tipoDocumento === 'orcamento' ? 'ORÇAMENTO' : 'PEDIDO';
    const subtitulo = tipoDocumento === 'orcamento' ? 'Documento de proposta comercial' : 'Comprovante de venda';
    const cabecalho = document.querySelector('#layout-orcamento h2');
    const subcabecalho = document.querySelector('#layout-orcamento p.text-xs.text-slate-600');
    if (cabecalho) cabecalho.textContent = titulo;
    if (subcabecalho) subcabecalho.textContent = subtitulo;
    preencherTexto('lbl-id-topo', pedido.id);
    ['c', 'os', 'orc'].forEach(prefixo => {
        preencherTexto(`${prefixo}-id`, pedido.id);
        preencherTexto(`${prefixo}-data`, pedido.data || '-');
        preencherTexto(`${prefixo}-cliente`, pedido.cliente_nome || '');
        preencherTexto(`${prefixo}-documento`, pedido.cliente_documento || '');
        preencherTexto(`${prefixo}-telefone`, pedido.cliente_telefone || '');
        preencherTexto(`${prefixo}-email`, pedido.cliente_email || '');
        preencherTexto(`${prefixo}-endereco`, pedido.cliente_endereco || '');
        preencherTexto(`${prefixo}-atendente`, pedido.usuario_nome || pedido.atendente || 'Sistema');
        preencherTexto(`${prefixo}-formapag`, pedido.forma_pagamento || 'Não informada');
        preencherTexto(`${prefixo}-pagamento`, pedido.status_pagamento || '-');
        preencherTexto(`${prefixo}-subtotal`, formatarMoeda(subtotal));
        preencherTexto(`${prefixo}-desconto`, formatarMoeda(pedido.desconto));
        preencherTexto(`${prefixo}-valor-pago`, formatarMoeda(pago));
        preencherTexto(`${prefixo}-total`, formatarMoeda(restante));
        preencherHtml(`${prefixo}-itens`, linhas);
    });
    preencherTexto('c-producao', pedido.status_producao || '-');
    preencherTexto('os-obs', pedido.observacao || 'Nenhuma observação registrada.');
    preencherTexto('orc-obs', pedido.observacao || 'Nenhuma observação registrada.');
}

export function alternarModelo(tipo) {
    ['cupom', 'os', 'orcamento'].forEach(modelo => document.getElementById(`layout-${modelo}`)?.classList.toggle('ativo', modelo === tipo));
    ['cupom', 'os', 'orcamento'].forEach(modelo => {
        const botao = document.getElementById(`btn-${modelo}`);
        if (botao) botao.className = `px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${modelo === tipo ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-slate-300'}`;
    });
}
