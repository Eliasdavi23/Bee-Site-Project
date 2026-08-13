export async function buscarDocumento(id, tipo) {
    const rotaBase = tipo === 'orcamento' ? '/api/orcamentos' : '/api/pedidos';
    const listaResponse = await fetch(rotaBase);
    if (!listaResponse.ok) throw new Error('Erro ao carregar lista de documentos.');
    const documento = (await listaResponse.json()).find(item => String(item.id) === String(id));
    if (!documento) return null;

    const itensResponse = await fetch(`${rotaBase}/${id}/itens`);
    const itens = itensResponse.ok ? await itensResponse.json() : [];
    let imagens = [];
    if (tipo !== 'orcamento') {
        const imagensResponse = await fetch(`/api/pedidos/${id}/imagens`);
        imagens = imagensResponse.ok ? await imagensResponse.json() : [];
    }
    return { documento, itens, imagens };
}

export async function buscarTodosDocumentos() {
    const [pedidosResponse, orcamentosResponse] = await Promise.all([fetch('/api/pedidos'), fetch('/api/orcamentos')]);
    return [
        ...(pedidosResponse.ok ? await pedidosResponse.json() : []),
        ...(orcamentosResponse.ok ? await orcamentosResponse.json() : [])
    ];
}
