// ==========================================
// API DE ORÇAMENTOS
// ==========================================

export async function fetchOrcamentos() {
    try {
        const response = await fetch('/api/orcamentos');
        if (!response.ok) throw new Error("Erro ao buscar orçamentos.");
        return await response.json();
    } catch (error) {
        console.error("Erro:", error);
        return [];
    }
}

export async function fetchClientes() {
    try {
        const res = await fetch('/api/clientes');
        return res.ok ? await res.json() : [];
    } catch (error) {
        console.error("Erro ao buscar clientes:", error);
        return [];
    }
}

export async function fetchProdutos() {
    try {
        const res = await fetch('/api/produtos');
        return res.ok ? await res.json() : [];
    } catch (error) {
        console.error("Erro ao buscar produtos:", error);
        return [];
    }
}

export async function fetchUsuarios() {
    try {
        const res = await fetch('/api/usuarios');
        return res.ok ? await res.json() : [];
    } catch (error) {
        console.error("Erro ao buscar usuários:", error);
        return [];
    }
}

export async function postOrcamentoAPI(payload) {
    const response = await fetch('/api/orcamentos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const resultado = await response.json();
    return { ok: response.ok, resultado };
}

export async function putOrcamentoAPI(orcamentoId, payload) {
    try {
        const response = await fetch(`/api/orcamentos/${orcamentoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resultado = await response.json();
        return { ok: response.ok, resultado };
    } catch (error) {
        console.error("Erro ao atualizar orçamento:", error);
        return { ok: false, resultado: { detail: error.message } };
    }
}

export async function converterVendaAPI(orcamentoId) {
    const response = await fetch(`/api/orcamentos/${orcamentoId}/converter-venda`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const resultado = await response.json();
    return { ok: response.ok, resultado };
}

export async function deleteOrcamentoAPI(orcamentoId) {
    try {
        const response = await fetch(`/api/orcamentos/${orcamentoId}`, {
            method: 'DELETE'
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}
