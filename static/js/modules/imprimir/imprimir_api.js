export async function buscarDocumento(id, tipo) {
    const rotaBase = tipo === 'orcamento' ? '/api/orcamentos' : '/api/pedidos';
    const [listaResponse, cfgResponse] = await Promise.all([
        fetch(rotaBase),
        fetch('/api/configuracoes')
    ]);
    if (!listaResponse.ok) throw new Error('Erro ao carregar lista de documentos.');

    const lista = await listaResponse.json();
    let documento = lista.find(item => String(item.id) === String(id));

    // Caso o ID tenha sido buscado como pedido mas seja orçamento (ou vice-versa), faz fallback automático
    if (!documento) {
        const rotaAlternativa = tipo === 'orcamento' ? '/api/pedidos' : '/api/orcamentos';
        const altRes = await fetch(rotaAlternativa);
        if (altRes.ok) {
            const altLista = await altRes.json();
            documento = altLista.find(item => String(item.id) === String(id));
        }
    }

    if (!documento) return null;

    const rotaItens = documento.tipo === 'ORCAMENTO' ? `/api/orcamentos/${id}/itens` : `/api/pedidos/${id}/itens`;
    const itensResponse = await fetch(rotaItens);
    const itens = itensResponse.ok ? await itensResponse.json() : (documento.itens || []);
    const configuracoes = cfgResponse.ok ? await cfgResponse.json() : {};

    return { documento, itens, configuracoes };
}

export async function buscarTodosDocumentos() {
    const [pedidosResponse, orcamentosResponse] = await Promise.all([
        fetch('/api/pedidos'),
        fetch('/api/orcamentos')
    ]);
    return [
        ...(pedidosResponse.ok ? await pedidosResponse.json() : []),
        ...(orcamentosResponse.ok ? await orcamentosResponse.json() : [])
    ];
}
