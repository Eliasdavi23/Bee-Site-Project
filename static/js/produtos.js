let listaProdutos = [];

document.addEventListener("DOMContentLoaded", () => {
    carregarProdutos();
});

async function carregarProdutos() {
    try {
        const res = await fetch("/api/produtos");
        if (!res.ok) throw new Error("Erro ao carregar lista de produtos.");

        listaProdutos = await res.json();
        renderizarTabelaProdutos(listaProdutos);
    } catch (e) {
        console.error("Erro ao carregar produtos:", e);
    }
}

function renderizarTabelaProdutos(dados) {
    const tbody = document.getElementById("tabela-produtos-body");
    const count = document.getElementById("total-produtos-count");

    if (count) count.textContent = dados.length;
    tbody.innerHTML = "";

    if (!dados || dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="p-6 text-center text-slate-500">Nenhum produto cadastrado.</td>
            </tr>
        `;
        return;
    }

    dados.forEach(p => {
        const preco = (p.preco_venda || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

        tbody.innerHTML += `
            <tr class="hover:bg-slate-900/50 transition border-b border-slate-800/60">
                <td class="p-4 font-bold text-amber-400">#${p.id}</td>
                <td class="p-4 font-bold text-slate-100">${p.nome}</td>
                <td class="p-4 text-emerald-400 font-bold">${preco}</td>
                <td class="p-4 text-slate-300 font-medium">${p.quantidade || 0} un</td>
                <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <button onclick='editarProduto(${JSON.stringify(p)})' class="p-2 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-lg text-xs font-bold transition cursor-pointer">✏️ Editar</button>
                        <button onclick="excluirProduto(${p.id})" class="p-2 bg-slate-800 hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold transition cursor-pointer">🗑️ Excluir</button>
                    </div>
                </td>
            </tr>
        `;
    });
}

function filtrarProdutos() {
    const termo = document.getElementById("input-busca-produto").value.toLowerCase();
    const filtrados = listaProdutos.filter(p => p.nome.toLowerCase().includes(termo));
    renderizarTabelaProdutos(filtrados);
}

function abrirModalProduto() {
    document.getElementById("form-produto").reset();
    document.getElementById("produto-id").value = "";
    document.getElementById("modal-produto-titulo").textContent = "Novo Produto";

    const modal = document.getElementById("modal-produto");
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

function fecharModalProduto() {
    const modal = document.getElementById("modal-produto");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
}

function editarProduto(p) {
    document.getElementById("produto-id").value = p.id;
    document.getElementById("produto-nome").value = p.nome;
    document.getElementById("produto-preco").value = p.preco_venda || 0;
    document.getElementById("produto-quantidade").value = p.quantidade || 0;

    document.getElementById("modal-produto-titulo").textContent = "Editar Produto";

    const modal = document.getElementById("modal-produto");
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

async function salvarProduto(e) {
    e.preventDefault();
    const id = document.getElementById("produto-id").value;

    const payload = {
        nome: document.getElementById("produto-nome").value,
        preco_venda: parseFloat(document.getElementById("produto-preco").value),
        quantidade: parseInt(document.getElementById("produto-quantidade").value) || 0
    };

    const url = id ? `/api/produtos/${id}` : "/api/produtos";
    const method = id ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            fecharModalProduto();
            carregarProdutos();
        } else {
            alert("Erro ao salvar produto no servidor.");
        }
    } catch (err) {
        console.error("Erro ao salvar produto:", err);
    }
}

async function excluirProduto(id) {
    if (!confirm("Tem certeza que deseja excluir este produto?")) return;

    try {
        const res = await fetch(`/api/produtos/${id}`, { method: "DELETE" });
        if (res.ok) {
            carregarProdutos();
        } else {
            alert("Erro ao excluir produto.");
        }
    } catch (err) {
        console.error("Erro ao excluir produto:", err);
    }
}