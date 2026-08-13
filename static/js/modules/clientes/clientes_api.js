export async function fetchClientes() {
    const res = await fetch('/api/clientes');
    if (!res.ok) throw new Error('Erro ao carregar clientes.');
    return res.json();
}

export async function salvarCliente(id, payload) {
    const res = await fetch(id ? `/api/clientes/${id}` : '/api/clientes', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.erro || 'Erro ao salvar cliente.');
    return data;
}

export async function excluirCliente(id) {
    const res = await fetch(`/api/clientes/${id}`, { method: 'DELETE' });
    return res.ok;
}
