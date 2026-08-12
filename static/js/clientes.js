let listaClientes = [];

document.addEventListener("DOMContentLoaded", () => {
    carregarClientes();
});

async function carregarClientes() {
    try {
        const res = await fetch("/api/clientes");
        if (res.ok) {
            listaClientes = await res.json();
            renderizarTabela(listaClientes);
        }
    } catch (e) {
        console.error("Erro ao carregar clientes:", e);
    }
}

function renderizarTabela(dados) {
    const tbody = document.getElementById("tabela-clientes-body");
    const count = document.getElementById("total-clientes-count");
    
    if (count) count.textContent = dados.length;
    if (!tbody) return;

    tbody.innerHTML = "";

    if (!dados || dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="p-6 text-center text-slate-500">Nenhum cliente cadastrado.</td>
            </tr>
        `;
        return;
    }

    dados.forEach(c => {
        const jsonStr = JSON.stringify(c).replace(/"/g, '&quot;');
        // Suporta tanto a chave 'documento' quanto 'cpf_cnpj' vinda do backend
        const docOuCpf = c.cpf_cnpj || c.documento || '-';

        tbody.innerHTML += `
            <tr class="hover:bg-slate-900/50 transition">
                <td class="p-4 font-bold text-amber-400">#${c.id}</td>
                <td class="p-4 font-bold text-slate-100">${c.nome}</td>
                <td class="p-4 text-slate-400">${docOuCpf}</td>
                <td class="p-4 text-slate-300">${c.telefone || '-'}</td>
                <td class="p-4 text-slate-400">${c.email || '-'}</td>
                <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <button type="button" onclick='editarCliente(${jsonStr})' class="p-2 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-lg text-xs font-bold transition cursor-pointer">✏️ Editar</button>
                        <button type="button" onclick="excluirCliente(${c.id})" class="p-2 bg-slate-800 hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold transition cursor-pointer">🗑️ Excluir</button>
                    </div>
                </td>
            </tr>
        `;
    });
}

function filtrarClientes() {
    const inputBusca = document.getElementById("input-busca-cliente");
    if (!inputBusca) return;
    const termo = inputBusca.value.toLowerCase();
    
    const filtrados = listaClientes.filter(c => 
        (c.nome && c.nome.toLowerCase().includes(termo)) || 
        (c.documento && c.documento.toLowerCase().includes(termo)) ||
        (c.cpf_cnpj && c.cpf_cnpj.toLowerCase().includes(termo)) ||
        (c.telefone && c.telefone.toLowerCase().includes(termo))
    );
    renderizarTabela(filtrados);
}

function abrirModalCliente() {
    const form = document.getElementById("form-cliente");
    if (form) form.reset();
    
    const inputId = document.getElementById("cliente-id");
    if (inputId) inputId.value = "";
    
    const titulo = document.getElementById("modal-cliente-titulo");
    if (titulo) titulo.textContent = "Novo Cliente";

    const modal = document.getElementById("modal-cliente");
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
    }
}

function fecharModalCliente() {
    const modal = document.getElementById("modal-cliente");
    if (modal) {
        modal.classList.add("hidden");
        modal.classList.remove("flex");
    }
}

function editarCliente(c) {
    document.getElementById("cliente-id").value = c.id;
    document.getElementById("cliente-nome").value = c.nome || "";
    document.getElementById("cliente-doc").value = c.cpf_cnpj || c.documento || "";
    document.getElementById("cliente-telefone").value = c.telefone || "";
    document.getElementById("cliente-email").value = c.email || "";
    document.getElementById("cliente-endereco").value = c.endereco || "";
    
    const titulo = document.getElementById("modal-cliente-titulo");
    if (titulo) titulo.textContent = "Editar Cliente";

    const modal = document.getElementById("modal-cliente");
    if (modal) {
        modal.classList.remove("hidden");
        modal.classList.add("flex");
    }
}

async function salvarCliente(event) {
    if (event) event.preventDefault();

    const id = document.getElementById("cliente-id").value;
    const nome = document.getElementById("cliente-nome").value.trim();
    const documento = document.getElementById("cliente-doc").value.trim();
    const telefone = document.getElementById("cliente-telefone").value.trim();
    const email = document.getElementById("cliente-email").value.trim();
    const endereco = document.getElementById("cliente-endereco").value.trim();

    if (!nome || !telefone) {
        alert("Preencha o Nome e o Telefone/WhatsApp do cliente.");
        return;
    }

    const payload = {
        nome: nome,
        documento: documento,
        telefone: telefone,
        email: email,
        endereco: endereco
    };

    const url = id ? `/api/clientes/${id}` : "/api/clientes";
    const method = id ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json().catch(() => ({}));

        if (res.ok && (data.sucesso || data.status === "ok")) {
            fecharModalCliente();
            await carregarClientes(); // Atualiza a tabela na mesma hora
        } else {
            alert("Erro ao salvar cliente: " + (data.erro || "Verifique os campos."));
        }
    } catch (err) {
        console.error("Erro na requisição:", err);
        alert("Ocorreu um erro de conexão ao salvar o cliente.");
    }
}

async function excluirCliente(id) {
    if (!confirm("Tem certeza que deseja excluir este cliente?")) return;

    try {
        const res = await fetch(`/api/clientes/${id}`, { method: "DELETE" });
        if (res.ok) {
            await carregarClientes();
        } else {
            alert("Erro ao excluir cliente.");
        }
    } catch (err) {
        console.error("Erro ao excluir cliente:", err);
    }
}