export async function fetchProdutos() {
    const res = await fetch('/api/produtos');
    if (!res.ok) throw new Error('Erro ao carregar lista de produtos.');
    return res.json();
}

export async function salvarProduto(id, payload) {
    const res = await fetch(id ? `/api/produtos/${id}` : '/api/produtos', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Erro ao salvar produto no servidor.');
}

export async function excluirProduto(id) {
    const res = await fetch(`/api/produtos/${id}`, { method: 'DELETE' });
    return res.ok;
}
