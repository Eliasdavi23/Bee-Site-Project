export function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function escaparHtml(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export function renderizarSeletorDocumentos(documentos) {
    const seletorBox = document.getElementById('seletor-documentos-box');
    if (seletorBox) {
        seletorBox.classList.remove('hidden');
    }
    renderizarListaDocumentos(documentos);
}

export function renderizarListaDocumentos(documentos) {
    const container = document.getElementById('lista-documentos-container');
    if (!container) return;
    if (!documentos || !documentos.length) {
        container.innerHTML = '<p class="text-xs text-slate-500 text-center py-4">Nenhum documento encontrado.</p>';
        return;
    }
    container.innerHTML = documentos.map(doc => {
        const tipoOrcamento = doc.tipo === 'ORCAMENTO';
        return `
            <a href="/imprimir?id=${doc.id}&tipo=${tipoOrcamento ? 'orcamento' : 'pedido'}" class="block p-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl transition">
                <div class="flex justify-between items-center gap-2">
                    <div>
                        <span class="font-black text-amber-400">#${doc.id}</span>
                        <span class="ml-2 font-bold text-slate-200">${escaparHtml(doc.cliente_nome || 'Cliente')}</span>
                        <span class="ml-2 text-xs text-slate-400">(${escaparHtml(doc.data || '-')})</span>
                    </div>
                    <div class="text-right">
                        <span class="text-emerald-400 font-black text-xs">${formatarMoeda(doc.valor_total)}</span>
                        <span class="block text-[10px] font-bold uppercase text-slate-400">${tipoOrcamento ? 'Orçamento' : 'Pedido de Venda'}</span>
                    </div>
                </div>
            </a>
        `;
    }).join('');
}

export function aplicarDadosEmpresa(configuracoes = {}, isOrcamento = false) {
    const preencherTexto = (id, valor) => {
        const el = document.getElementById(id);
        if (el) el.textContent = valor;
    };

    const nomeEmpresa = (configuracoes.nome_empresa || '').trim() || 'BEE GRÁFICA & COMUNICAÇÃO VISUAL';
    const docEmpresa = (configuracoes.documento_empresa || '').trim();
    const telEmpresa = (configuracoes.telefone_empresa || '').trim();
    const emailEmpresa = (configuracoes.email_empresa || '').trim();
    const endEmpresa = (configuracoes.endereco_empresa || '').trim();

    const linhaContato = [
        docEmpresa ? `CNPJ/CPF: ${docEmpresa}` : '',
        telEmpresa ? `Tel: ${telEmpresa}` : '',
        emailEmpresa,
        endEmpresa
    ].filter(Boolean).join(' • ');

    preencherTexto('c-empresa-nome', nomeEmpresa);
    preencherTexto('c-empresa-sub', isOrcamento ? 'Orçamento Comercial' : 'Comprovante de Pedido');

    // Bloco DADOS DA EMPRESA na Bobina Térmica (80mm) e nos modelos A4
    ['c', 'os', 'orc'].forEach(prefixo => {
        preencherTexto(`${prefixo}-emp-razao`, nomeEmpresa);
        preencherTexto(`${prefixo}-emp-documento`, docEmpresa || 'Não informado');
        preencherTexto(`${prefixo}-emp-telefone`, telEmpresa || 'Não informado');
        preencherTexto(`${prefixo}-emp-email`, emailEmpresa || 'Não informado');
        preencherTexto(`${prefixo}-emp-endereco`, endEmpresa || 'Não informado');
    });

    preencherTexto('os-empresa-contato', linhaContato);
    preencherTexto('orc-empresa-contato', linhaContato);

    if (configuracoes.obs_padrao_impressao) {
        preencherTexto('c-rodape-msg', configuracoes.obs_padrao_impressao);
    }

    preencherTexto('orc-titulo-doc', 'ORÇAMENTO');
    preencherTexto('orc-subtitulo-doc', 'Documento de proposta comercial');
}

export function preencherDocumento(pedido, itens, tipoDocumento, configuracoes = {}) {
    const preencherTexto = (id, valor) => {
        const el = document.getElementById(id);
        if (el) el.textContent = valor;
    };
    const preencherHtml = (id, valor) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = valor;
    };

    const valorTotalLiquido = Number(pedido.valor_total || 0);
    const desconto = Number(pedido.desconto || 0);
    const subtotal = valorTotalLiquido + desconto;
    const pago = Number(pedido.valor_pago || 0);
    const restante = Math.max(0, valorTotalLiquido - pago);

    // Linhas para tabelas A4 (Ordem de Serviço e Orçamento) com Observação individual por item
    const linhasTabelaA4 = itens && itens.length
        ? itens.map(item => {
            const qtd = Number(item.quantidade || 1);
            const unit = Number(item.preco_unitario || 0);
            const sub = qtd * unit;
            const nome = escaparHtml(item.nome_produto || item.produto_nome || 'Produto');
            const obs = (item.observacao || '').trim();
            return `
                <tr class="border-b border-black">
                    <td class="py-2 px-3 border-r border-black font-bold text-center align-top">${qtd}</td>
                    <td class="py-2 px-3 border-r border-black align-top">
                        <div class="font-bold text-black">${nome}</div>
                        ${obs ? `<div class="text-[11px] font-semibold text-black mt-0.5">📝 Obs. do Item: ${escaparHtml(obs)}</div>` : ''}
                    </td>
                    <td class="py-2 px-3 border-r border-black text-right align-top">${formatarMoeda(unit)}</td>
                    <td class="py-2 px-3 text-right font-bold align-top">${formatarMoeda(sub)}</td>
                </tr>
            `;
        }).join('')
        : "<tr><td colspan='4' class='py-3 px-3 text-center'>Nenhum item informado.</td></tr>";

    // Blocos para Cupom Térmico 80mm (#c-itens é uma <div>, nunca <tr>)
    const blocosCupom80mm = itens && itens.length
        ? itens.map(item => {
            const qtd = Number(item.quantidade || 1);
            const unit = Number(item.preco_unitario || 0);
            const sub = qtd * unit;
            const nome = escaparHtml(item.nome_produto || item.produto_nome || 'Produto');
            const obs = (item.observacao || '').trim();
            return `
                <div class="border-b border-dashed border-black pb-1">
                    <div class="flex justify-between">
                        <span>${qtd}x ${nome}</span>
                        <span>${formatarMoeda(sub)}</span>
                    </div>
                    <div class="text-[10px] font-normal">Unit: ${formatarMoeda(unit)}</div>
                    ${obs ? `<div class="text-[10px] font-bold mt-0.5">› Obs: ${escaparHtml(obs)}</div>` : ''}
                </div>
            `;
        }).join('')
        : "<div class='py-1'>Nenhum item informado.</div>";

    const isOrcamento = tipoDocumento === 'orcamento' || pedido.tipo === 'ORCAMENTO';
    aplicarDadosEmpresa(configuracoes, isOrcamento);

    preencherTexto('lbl-id-topo', pedido.id);

    ['c', 'os', 'orc'].forEach(prefixo => {
        preencherTexto(`${prefixo}-id`, pedido.id);
        preencherTexto(`${prefixo}-data`, pedido.data || '-');
        preencherTexto(`${prefixo}-cliente`, pedido.cliente_nome || 'Cliente Balcão');
        preencherTexto(`${prefixo}-documento`, pedido.cliente_documento || '-');
        preencherTexto(`${prefixo}-telefone`, pedido.cliente_telefone || '-');
        preencherTexto(`${prefixo}-email`, pedido.cliente_email || '-');
        preencherTexto(`${prefixo}-endereco`, pedido.cliente_endereco || '-');
        preencherTexto(`${prefixo}-atendente`, pedido.usuario_nome || pedido.atendente || 'Sistema');
        preencherTexto(`${prefixo}-formapag`, pedido.forma_pagamento || 'Não informada');
        preencherTexto(`${prefixo}-pagamento`, pedido.status_pagamento || '-');
        preencherTexto(`${prefixo}-subtotal`, formatarMoeda(subtotal));
        preencherTexto(`${prefixo}-desconto`, formatarMoeda(desconto));
        preencherTexto(`${prefixo}-total`, formatarMoeda(valorTotalLiquido));
        preencherTexto(`${prefixo}-valor-pago`, formatarMoeda(pago));
        preencherTexto(`${prefixo}-restante`, formatarMoeda(restante));
        preencherTexto(`${prefixo}-obs`, pedido.observacao || 'Nenhuma observação geral registrada.');
    });

    preencherHtml('c-itens', blocosCupom80mm);
    preencherHtml('os-itens', linhasTabelaA4);
    preencherHtml('orc-itens', linhasTabelaA4);

    preencherTexto('c-producao', pedido.status_producao || '-');
    preencherTexto('os-producao', pedido.status_producao || '-');
}

export function alternarModelo(tipo) {
    ['cupom', 'os', 'orcamento'].forEach(modelo => {
        document.getElementById(`layout-${modelo}`)?.classList.toggle('ativo', modelo === tipo);
        const botao = document.getElementById(`btn-${modelo}`);
        if (botao) {
            botao.classList.toggle('active', modelo === tipo);
        }
    });
}
