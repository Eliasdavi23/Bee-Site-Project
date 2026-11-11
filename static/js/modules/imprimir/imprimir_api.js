/**
 * Módulo de API para Central de Impressão (Bee-Site)
 * Busca direta otimizada (O(1)) de pedidos e orçamentos via endpoints indexados.
 */

export async function buscarDocumento(id, tipo, configuracoesExistentes = null) {
    if (!id) return null;

    const rotaPrincipal = tipo === 'orcamento' ? `/api/orcamentos/${id}` : `/api/pedidos/${id}`;
    const rotaFallback = tipo === 'orcamento' ? `/api/pedidos/${id}` : `/api/orcamentos/${id}`;

    // Busca o documento e as configurações da empresa em paralelo
    const promises = [
        fetch(rotaPrincipal),
        configuracoesExistentes ? Promise.resolve(null) : fetch('/api/configuracoes')
    ];

    let [docRes, cfgRes] = await Promise.all(promises);

    let doc = null;
    if (docRes && docRes.ok) {
        doc = await docRes.json();
    } else {
        // Fallback automático caso o ID pertença ao tipo oposto
        try {
            const altRes = await fetch(rotaFallback);
            if (altRes.ok) {
                doc = await altRes.json();
            }
        } catch (_) {}
    }

    if (!doc) return null;

    // Itens: Já inclusos pelo backend em obter_pedido / obter_orcamento
    let itens = doc.itens || [];
    if (!itens.length) {
        const rotaItens = doc.tipo === 'ORCAMENTO' ? `/api/orcamentos/${doc.id}/itens` : `/api/pedidos/${doc.id}/itens`;
        try {
            const itensRes = await fetch(rotaItens);
            if (itensRes.ok) itens = await itensRes.json();
        } catch (_) {}
    }

    let configuracoes = configuracoesExistentes;
    if (!configuracoes && cfgRes && cfgRes.ok) {
        try { configuracoes = await cfgRes.json(); } catch (_) {}
    }

    return {
        documento: doc,
        itens,
        configuracoes: configuracoes || {}
    };
}

export async function buscarTodosDocumentos() {
    try {
        const [pedidosRes, orcamentosRes] = await Promise.all([
            fetch('/api/pedidos'),
            fetch('/api/orcamentos')
        ]);
        const pedidos = pedidosRes.ok ? await pedidosRes.json() : [];
        const orcamentos = orcamentosRes.ok ? await orcamentosRes.json() : [];
        return [
            ...pedidos.map(p => ({ ...p, tipo: p.tipo || 'PEDIDO' })),
            ...orcamentos.map(o => ({ ...o, tipo: 'ORCAMENTO' }))
        ];
    } catch (e) {
        console.warn('Erro ao carregar catálogo de documentos:', e);
        return [];
    }
}
