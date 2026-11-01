// static/js/modules/pedidos/pedidos_api.js

export async function fetchPedidos() {
    try {
        const res = await fetch("/api/pedidos");
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar pedidos:", e);
        return [];
    }
}

export async function fetchClientes() {
    try {
        const res = await fetch("/api/clientes");
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar clientes:", e);
        return [];
    }
}

export async function fetchProdutos() {
    try {
        const res = await fetch("/api/produtos");
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar produtos:", e);
        return [];
    }
}

export async function fetchAtendentes() {
    try {
        const res = await fetch("/api/usuarios");
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar atendentes:", e);
        return [];
    }
}

export async function fetchAtendentesDetalhes() {
    try {
        const res = await fetch("/api/usuarios/detalhes");
        return res.ok ? await res.json() : [];
    } catch (e) {
        return [];
    }
}

export async function salvarAtendenteAPI(nome, senha) {
    try {
        const res = await fetch("/api/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nome, senha })
        });
        return await res.json();
    } catch (e) {
        return { sucesso: false, detail: "Erro de conexão." };
    }
}

export async function removerAtendenteAPI(id) {
    try {
        const res = await fetch(`/api/usuarios/${id}`, { method: "DELETE" });
        return res.ok;
    } catch (e) {
        return false;
    }
}

export async function fetchConfiguracoes() {
    try {
        const res = await fetch("/api/configuracoes");
        return res.ok ? await res.json() : {};
    } catch (e) {
        return {};
    }
}

export async function salvarConfiguracoesAPI(payload) {
    try {
        const res = await fetch("/api/configuracoes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        return await res.json();
    } catch (e) {
        return { sucesso: false };
    }
}

export async function fetchImagensPedido(id) {
    try {
        const res = await fetch(`/api/pedidos/${id}/imagens`);
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar imagens do pedido:", e);
        return [];
    }
}

export async function fetchItensPedido(id) {
    try {
        const res = await fetch(`/api/pedidos/${id}/itens`);
        return res.ok ? await res.json() : [];
    } catch (e) {
        console.error("Erro ao carregar itens do pedido:", e);
        return [];
    }
}

export async function deletePedidoAPI(id) {
    try {
        const res = await fetch(`/api/pedidos/${id}`, { method: "DELETE" });
        return res.ok;
    } catch (err) {
        console.error("Erro ao excluir pedido:", err);
        return false;
    }
}

export async function postPedidoAPI(formData) {
    try {
        const res = await fetch("/api/pedidos", { method: "POST", body: formData });
        return await res.json();
    } catch (err) {
        console.error("Erro ao salvar pedido:", err);
        return { sucesso: false, erro: "Erro de conexão com o servidor local." };
    }
}
