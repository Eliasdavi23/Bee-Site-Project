// ==========================================
// API DO FINANCEIRO
// ==========================================

export async function fetchResumoFinanceiro(periodo = 'mes_atual', dataEspecifica = null) {
    const params = new URLSearchParams({ periodo });
    if (dataEspecifica) {
        params.set('data', dataEspecifica);
    }
    const res = await fetch(`/api/financeiro/resumo?${params.toString()}`);
    if (!res.ok) throw new Error("Acesso negado ou erro ao carregar dados.");
    return await res.json();
}

export async function fetchContasPagar(dataEspecifica = null) {
    const params = new URLSearchParams();
    if (dataEspecifica) {
        params.set('data', dataEspecifica);
    }
    const sufixo = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`/api/financeiro/contas-pagar${sufixo}`);
    if (!res.ok) throw new Error("Erro ao carregar contas a pagar.");
    return await res.json();
}

export async function fetchClientesDevedores(periodo = 'mes_atual', dataEspecifica = null) {
    const params = new URLSearchParams({ periodo });
    if (dataEspecifica) {
        params.set('data', dataEspecifica);
    }
    const res = await fetch(`/api/financeiro/clientes-devedores?${params.toString()}`);
    if (!res.ok) throw new Error("Erro ao carregar clientes devedores.");
    return await res.json();
}

export async function postContaPagar(payload) {
    const res = await fetch('/api/financeiro/contas-pagar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return res.ok;
}

export async function quitarContaAPI(id) {
    const res = await fetch(`/api/financeiro/contas-pagar/${id}/quitar`, { method: 'PUT' });
    return res.ok;
}

export async function deleteContaAPI(id) {
    const res = await fetch(`/api/financeiro/contas-pagar/${id}`, { method: 'DELETE' });
    return res.ok;
}
