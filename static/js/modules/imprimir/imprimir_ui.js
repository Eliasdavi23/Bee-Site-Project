/**
 * Módulo de Interface e Renderização da Central de Impressão (Bee-Site)
 * Arquitetura declarativa com zero duplicação e suporte extensível a novos modelos.
 */

// Registro declarativo dos modelos de impressão disponíveis
export const MODELOS_DISPONIVEIS = [
    { id: 'cupom', prefixo: 'c', nome: 'Bobina Térmica (80mm)' },
    { id: 'os', prefixo: 'os', nome: 'Ordem de Serviço (A4)' },
    { id: 'orcamento', prefixo: 'orc', nome: 'Orçamento (A4)' }
];

// Utilitários de Formatação
export function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function formatarStatusLegivel(status) {
    if (!status) return '-';
    const s = String(status).trim().toUpperCase().replace(/_/g, ' ');
    const mapaStatus = {
        'EM PRODUCAO': 'EM PRODUÇÃO',
        'EM PRODUÇÃO': 'EM PRODUÇÃO',
        'ORCAMENTO': 'ORÇAMENTO',
        'ORÇAMENTO': 'ORÇAMENTO',
        'AGUARDANDO APROVACAO': 'AGUARDANDO APROVAÇÃO',
        'AGUARDANDO APROVAÇÃO': 'AGUARDANDO APROVAÇÃO',
        'ESPERANDO INSTALACAO': 'ESPERANDO INSTALAÇÃO',
        'ESPERANDO INSTALAÇÃO': 'ESPERANDO INSTALAÇÃO',
        'CONCLUIDO': 'CONCLUÍDO',
        'CONCLUÍDO': 'CONCLUÍDO'
    };
    return mapaStatus[s] || s;
}

export function formatarStatusPagamento(status) {
    if (!status) return '-';
    return String(status).trim().toUpperCase();
}

export function escaparHtml(texto) {
    return String(texto || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Helpers DOM seguros
export function preencherTexto(id, valor) {
    const el = document.getElementById(id);
    if (el) el.textContent = valor !== null && valor !== undefined ? valor : '-';
}

export function preencherHtml(id, valor) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = valor !== null && valor !== undefined ? valor : '';
}

// Alternância de Modelos de Impressão (Bobina 80mm vs A4)
export function alternarModelo(tipo) {
    MODELOS_DISPONIVEIS.forEach(m => {
        document.getElementById(`layout-${m.id}`)?.classList.toggle('ativo', m.id === tipo);
        document.getElementById(`btn-${m.id}`)?.classList.toggle('active', m.id === tipo);
    });
}

// Renderização do Seletor de Documentos
export function renderizarSeletorDocumentos(documentos) {
    const seletorBox = document.getElementById('seletor-documentos-box');
    if (seletorBox) seletorBox.classList.remove('hidden');
    renderizarListaDocumentos(documentos);
}

export function renderizarListaDocumentos(documentos) {
    const container = document.getElementById('lista-documentos-container');
    if (!container) return;
    if (!documentos || !documentos.length) {
        container.innerHTML = '<p class="text-xs text-zinc-500 text-center py-4">Nenhum documento encontrado.</p>';
        return;
    }
    container.innerHTML = documentos.map(doc => {
        const tipoOrcamento = doc.tipo === 'ORCAMENTO';
        return `
            <a href="/imprimir?id=${doc.id}&tipo=${tipoOrcamento ? 'orcamento' : 'pedido'}" class="block p-3 bg-black hover:bg-zinc-800 border border-zinc-800 rounded-xl transition">
                <div class="flex justify-between items-center gap-2">
                    <div>
                        <span class="font-black text-yellow-400">#${doc.id}</span>
                        <span class="ml-2 font-bold text-zinc-100">${escaparHtml(doc.cliente_nome || 'Cliente Balcão')}</span>
                        <span class="ml-2 text-xs text-zinc-400">(${escaparHtml(doc.data || '-')})</span>
                    </div>
                    <div class="text-right">
                        <span class="text-emerald-400 font-black text-xs">${formatarMoeda(doc.valor_total)}</span>
                        <span class="block text-[10px] font-bold uppercase text-zinc-400">${tipoOrcamento ? 'Orçamento' : 'Pedido de Venda'}</span>
                    </div>
                </div>
            </a>
        `;
    }).join('');
}

// Normalização de Item para Renderização DRY
function normalizarItem(item) {
    const qtd = Number(item.quantidade || 1);
    const unit = Number(item.preco_unitario || 0);
    const sub = Number(item.subtotal) || (qtd * unit);
    const nome = escaparHtml(item.nome_produto || item.produto_nome || 'Produto');
    const obs = escaparHtml((item.observacao || '').trim());
    return { qtd, unit, sub, nome, obs };
}

export function renderizarItensTabelaA4(itens = []) {
    if (!itens || !itens.length) {
        return "<tr><td colspan='4' class='py-3 px-3 text-center font-normal'>Nenhum item informado.</td></tr>";
    }
    return itens.map(item => {
        const { qtd, unit, sub, nome, obs } = normalizarItem(item);
        return `
            <tr class="border-b border-black">
                <td class="py-2 px-3 border-r border-black font-bold text-center align-top">${qtd}</td>
                <td class="py-2 px-3 border-r border-black align-top">
                    <div class="font-bold text-black">${nome}</div>
                    ${obs ? `<div class="text-[11px] font-semibold text-black mt-0.5">Obs. do Item: ${obs}</div>` : ''}
                </td>
                <td class="py-2 px-3 border-r border-black text-right align-top">${formatarMoeda(unit)}</td>
                <td class="py-2 px-3 text-right font-bold align-top">${formatarMoeda(sub)}</td>
            </tr>
        `;
    }).join('');
}

export function renderizarItensCupom(itens = []) {
    if (!itens || !itens.length) {
        return "<div class='py-1 font-normal'>Nenhum item informado.</div>";
    }
    return itens.map(item => {
        const { qtd, unit, sub, nome, obs } = normalizarItem(item);
        return `
            <div class="border-b border-dashed border-black pb-1">
                <div class="flex justify-between">
                    <span>${qtd}x ${nome}</span>
                    <span>${formatarMoeda(sub)}</span>
                </div>
                <div class="text-[10px] font-normal">Unit: ${formatarMoeda(unit)}</div>
                ${obs ? `<div class="text-[10px] font-bold mt-0.5">› Obs: ${obs}</div>` : ''}
            </div>
        `;
    }).join('');
}

// Aplicação de Dados Institucionais da Empresa
export function aplicarDadosEmpresa(configuracoes = {}, isOrcamento = false) {
    const nomeEmpresa = (configuracoes.nome_empresa || '').trim() || 'BEE GRÁFICA & COMUNICAÇÃO VISUAL';
    const docEmpresa = (configuracoes.documento_empresa || '').trim();
    const telEmpresa = (configuracoes.telefone_empresa || '').trim();
    const emailEmpresa = (configuracoes.email_empresa || '').trim();
    const endEmpresa = (configuracoes.endereco_empresa || '').trim();
    const cidEmpresa = (configuracoes.cidade_empresa || '').trim();
    const ufEmpresa = (configuracoes.estado_empresa || '').trim().toUpperCase();

    const localidade = [cidEmpresa, ufEmpresa].filter(Boolean).join(' / ');

    const linhaContato = [
        localidade,
        docEmpresa ? `CNPJ/CPF: ${docEmpresa}` : '',
        telEmpresa ? `Tel: ${telEmpresa}` : '',
        emailEmpresa,
        endEmpresa
    ].filter(Boolean).join(' • ');

    preencherTexto('c-empresa-nome', nomeEmpresa);
    preencherTexto('c-empresa-sub', isOrcamento ? 'Orçamento Comercial' : 'Comprovante de Pedido');
    preencherTexto('os-empresa-contato', linhaContato);
    preencherTexto('orc-empresa-contato', linhaContato);

    MODELOS_DISPONIVEIS.forEach(m => {
        const p = m.prefixo;
        preencherTexto(`${p}-emp-razao`, nomeEmpresa);
        preencherTexto(`${p}-emp-documento`, docEmpresa || '-');
        preencherTexto(`${p}-emp-telefone`, telEmpresa || '-');
        preencherTexto(`${p}-emp-email`, emailEmpresa || '-');
        preencherTexto(`${p}-emp-endereco`, endEmpresa || '-');
        preencherTexto(`${p}-emp-cidade`, cidEmpresa || '-');
        preencherTexto(`${p}-emp-estado`, ufEmpresa || '-');
        preencherTexto(`${p}-emp-cidade-estado`, localidade || '-');
    });

    if (configuracoes.obs_padrao_impressao) {
        preencherTexto('c-rodape-msg', configuracoes.obs_padrao_impressao);
    }
    preencherTexto('orc-titulo-doc', 'ORÇAMENTO');
    preencherTexto('orc-subtitulo-doc', 'Documento de proposta comercial');
}

// Preenchimento Declarativo Completo do Documento
export function preencherDocumento(pedido, itens, tipoDocumento, configuracoes = {}) {
    const valorTotalLiquido = Number(pedido.valor_total || 0);
    const desconto = Number(pedido.desconto || 0);
    const subtotal = valorTotalLiquido + desconto;
    const pago = Number(pedido.valor_pago || 0);
    const restante = Math.max(0, valorTotalLiquido - pago);

    const isOrcamento = tipoDocumento === 'orcamento' || pedido.tipo === 'ORCAMENTO';
    aplicarDadosEmpresa(configuracoes, isOrcamento);

    preencherTexto('lbl-id-topo', pedido.id);

    const statusProducao = formatarStatusLegivel(pedido.status_producao);
    const statusPagto = formatarStatusPagamento(pedido.status_pagamento);

    // Mapeamento declarativo centralizado (Single Source of Truth)
    const mapaCampos = {
        'id': pedido.id,
        'data': pedido.data || '-',
        'cliente': pedido.cliente_nome || 'Cliente Balcão',
        'documento': pedido.cliente_documento || '-',
        'telefone': pedido.cliente_telefone || '-',
        'email': pedido.cliente_email || '-',
        'endereco': pedido.cliente_endereco || '-',
        'atendente': pedido.usuario_nome || pedido.atendente || 'Sistema',
        'formapag': pedido.forma_pagamento || 'Não informada',
        'pagamento': statusPagto,
        'producao': statusProducao,
        'subtotal': formatarMoeda(subtotal),
        'desconto': formatarMoeda(desconto),
        'total': formatarMoeda(valorTotalLiquido),
        'valor-pago': formatarMoeda(pago),
        'restante': formatarMoeda(restante),
        'obs': pedido.observacao || 'Nenhuma observação geral registrada.'
    };

    // Preenche todos os modelos registrados sem código duplicado
    MODELOS_DISPONIVEIS.forEach(m => {
        Object.entries(mapaCampos).forEach(([campo, valor]) => {
            preencherTexto(`${m.prefixo}-${campo}`, valor);
        });
    });

    // Injeção limpa de itens
    const linhasA4 = renderizarItensTabelaA4(itens);
    preencherHtml('c-itens', renderizarItensCupom(itens));
    preencherHtml('os-itens', linhasA4);
    preencherHtml('orc-itens', linhasA4);
}
