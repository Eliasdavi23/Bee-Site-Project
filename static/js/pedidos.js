
// IMPORTAÇÕES (API e Interface Visual)
import * as api from './modules/pedidos/pedidos_api.js';
import * as ui from './modules/pedidos/pedidos_ui.js';

// ESTADO GLOBAL DA TELA
let estado = {
    pedidos: [],
    clientes: [],
    produtos: [],
    atendentes: [],
    imagensExistentes: []
};

// INICIALIZAÇÃO E EVENTOS GERAIS

document.addEventListener("DOMContentLoaded", carregarDadosIniciais);

async function carregarDadosIniciais() {
    // Carrega tudo do banco simultaneamente
    [estado.pedidos, estado.clientes, estado.produtos, estado.atendentes] = await Promise.all([
        api.fetchPedidos(), 
        api.fetchClientes(), 
        api.fetchProdutos(), 
        api.fetchAtendentes()
    ]);
    
    ui.preencherSelectAtendentes(estado.atendentes);
    filtrarPedidos();
    configurarEventosGerais();
}

function configurarEventosGerais() {
    // Fechar dropdowns ao clicar fora deles
    document.addEventListener("click", (e) => {
        if(!e.target.closest('.relative')) {
            document.querySelectorAll('[id^="dropdown-"]').forEach(d => d.classList.add("hidden"));
        }
    });

    // Filtros da tabela
    document.getElementById("campo-busca")?.addEventListener("input", filtrarPedidos);
    document.getElementById("filtro-status-producao")?.addEventListener("change", filtrarPedidos);
    document.getElementById("ped-pagamento")?.addEventListener("change", atualizarValorPagoPorStatus);

    // Listener para input de imagens
    
    document.addEventListener("change", (e) => {
        if (e.target && e.target.id === "ped-imagens-input") {
            window.renderizarGaleriaImagens();
        }
    });
}

function obterTotalAtual() {
    let subtotal = 0;
    document.querySelectorAll(".linha-prod-item").forEach(l => {
        const qtd = parseFloat(l.querySelector(".inp-qtd").value) || 0;
        const preco = parseFloat(l.querySelector(".inp-preco").value) || 0;
        subtotal += (qtd * preco);
    });

    const desconto = parseFloat(document.getElementById("ped-desconto").value) || 0;
    return Math.max(0, subtotal - desconto);
}

function atualizarValorPagoPorStatus() {
    const select = document.getElementById("ped-pagamento");
    const input = document.getElementById("ped-vpago");
    if (!select || !input) return;

    const status = (select.value || "").toUpperCase();
    const totalAtual = obterTotalAtual();

    if (status === "PAGO") {
        input.value = Number(totalAtual).toFixed(2);
    } else if (status === "PARCIAL") {
        input.value = "0.00";
    } else {
        input.value = "0.00";
    }
}

function filtrarPedidos() {
    const termo = document.getElementById("campo-busca")?.value.toLowerCase().trim() || "";
    const statusFiltro = document.getElementById("filtro-status-producao")?.value.toUpperCase().trim() || "";

    const filtrados = estado.pedidos.filter(p => {
        const bateuTexto = (p.id + "").includes(termo) || 
                           (p.cliente_nome?.toLowerCase().includes(termo)) || 
                           (p.usuario_nome?.toLowerCase().includes(termo));
        const bateuStatus = !statusFiltro || (p.status_producao || "").toUpperCase() === statusFiltro;
        
        return bateuTexto && bateuStatus;
    });

    ui.renderizarTabela(filtrados);
}

// LÓGICA DE NEGÓCIO (CRUD de Pedidos)

async function salvarPedido() {
    const clienteId = document.getElementById("ped-cliente")?.value;
    if (!clienteId) {
        alert("Por favor, selecione um cliente válido na lista.");
        return;
    }

    const produtos = [];
    document.querySelectorAll(".linha-prod-item").forEach(l => {
        const prodId = l.querySelector(".sel-produto").value;
        if (prodId) {
            produtos.push({
                produto_id: parseInt(prodId),
                nome_produto: l.querySelector("input[type='text']").value,
                quantidade: parseInt(l.querySelector(".inp-qtd").value) || 1,
                preco_unitario: parseFloat(l.querySelector(".inp-preco").value) || 0
            });
        }
    });

    if (produtos.length === 0) {
        alert("Adicione pelo menos um produto ao pedido.");
        return;
    }

    const payload = {
        id: document.getElementById("ped-id").value || null,
        cliente_id: parseInt(clienteId),
        usuario_nome: document.getElementById("ped-usuario").value || "Sistema",
        valor_total: window.calcularTotalGlobal(),
        desconto: parseFloat(document.getElementById("ped-desconto").value) || 0,
        status_producao: document.getElementById("ped-producao").value,
        status_pagamento: document.getElementById("ped-pagamento").value,
        forma_pagamento: document.getElementById("ped-forma-pagamento").value,
        valor_pago: parseFloat(document.getElementById("ped-vpago").value) || 0,
        observacao: document.getElementById("ped-observacao").value,
        produtos: produtos,
        imagens_mantidas: estado.imagensExistentes
    };

    const formData = new FormData();
    formData.append("dados", JSON.stringify(payload));
    
    const inputImagens = document.getElementById("ped-imagens-input");
    if (inputImagens?.files) {
        Array.from(inputImagens.files).forEach(file => formData.append("imagens", file));
    }

    const resultado = await api.postPedidoAPI(formData);
    
    if (resultado.sucesso) {
        window.fecharModalPedido();
        estado.pedidos = await api.fetchPedidos();
        filtrarPedidos();
    } else {
        alert("Erro ao salvar pedido: " + (resultado.erro || "Verifique os dados."));
    }
}

async function editarPedido(id) {
    const pedido = estado.pedidos.find(p => p.id === id);
    if (!pedido) return;

    // Preenche campos base
    document.getElementById("ped-id").value = pedido.id;
    window.configurarBuscaCliente(pedido.cliente_id);
    document.getElementById("ped-usuario").value = pedido.usuario_nome || "Sistema";
    document.getElementById("ped-desconto").value = (pedido.desconto || 0).toFixed(2);
    document.getElementById("ped-producao").value = pedido.status_producao;
    document.getElementById("ped-pagamento").value = pedido.status_pagamento;
    document.getElementById("ped-forma-pagamento").value = pedido.forma_pagamento || "";
    document.getElementById("ped-vpago").value = (pedido.valor_pago || 0).toFixed(2);
    document.getElementById("ped-observacao").value = pedido.observacao || "";
    document.getElementById("modal-titulo").textContent = `Editar Pedido #${pedido.id}`;

    // Imagens
    estado.imagensExistentes = await api.fetchImagensPedido(pedido.id);
    const inputImg = document.getElementById("ped-imagens-input");
    if (inputImg) inputImg.value = "";
    window.renderizarGaleriaImagens();

    // Produtos
    const itens = await api.fetchItensPedido(pedido.id);
    const container = document.getElementById("container-produtos");
    container.innerHTML = "";
    
    if (itens.length > 0) {
        itens.forEach(item => window.adicionarLinhaProduto(item));
    } else {
        window.adicionarLinhaProduto();
    }

    // Abre Modal
    const modal = document.getElementById("modal-pedido");
    modal.classList.remove("hidden");
    modal.classList.add("flex");
}

async function excluirPedido(id) {
    if (!confirm(`Tem certeza que deseja excluir o pedido #${id}?`)) return;
    
    const sucesso = await api.deletePedidoAPI(id);
    if (sucesso) {
        estado.pedidos = await api.fetchPedidos();
        filtrarPedidos();
    } else {
        alert("Erro ao excluir pedido.");
    }
}

// ⚠️ EXPOSIÇÃO PARA O HTML ⚠️

// 1. Ações Principais
window.editarPedido = editarPedido;
window.excluirPedido = excluirPedido;
window.salvarPedido = salvarPedido;

// 2. Modal
window.abrirModalPedido = () => {
    document.getElementById("ped-id").value = "";
    window.configurarBuscaCliente("");
    document.getElementById("ped-usuario").value = "Sistema";
    document.getElementById("ped-desconto").value = "0.00";
    document.getElementById("ped-producao").value = "PENDENTE";
    document.getElementById("ped-pagamento").value = "PENDENTE";
    document.getElementById("ped-forma-pagamento").value = "";
    document.getElementById("ped-vpago").value = "0.00";
    document.getElementById("ped-observacao").value = "";
    document.getElementById("container-produtos").innerHTML = "";
    
    estado.imagensExistentes = [];
    const inputImg = document.getElementById("ped-imagens-input");
    if (inputImg) inputImg.value = "";
    window.renderizarGaleriaImagens();

    document.getElementById("modal-titulo").textContent = "Cadastrar Novo Pedido";
    window.adicionarLinhaProduto();

    const modal = document.getElementById("modal-pedido");
    modal.classList.remove("hidden");
    modal.classList.add("flex");
};

window.fecharModalPedido = () => {
    const modal = document.getElementById("modal-pedido");
    modal.classList.add("hidden");
    modal.classList.remove("flex");
};

// 3. Calculos e Linhas de Produtos
window.calcularTotalGlobal = () => {
    const total = obterTotalAtual();
    document.getElementById("lbl-total").textContent = ui.formatarMoeda(total);

    const select = document.getElementById("ped-pagamento");
    const input = document.getElementById("ped-vpago");
    if (select && input && (select.value || "").toUpperCase() === "PAGO") {
        input.value = Number(total).toFixed(2);
    }

    return total;
};

window.calcularTotalGeral = window.calcularTotalGlobal;

window.adicionarLinhaProduto = (item = null) => {
    const idUnico = Date.now() + Math.random().toString(36).substring(2, 7);
    const prodObj = item ? estado.produtos.find(p => p.id == item.produto_id) : null;
    const preco = item ? item.preco_unitario : (prodObj ? prodObj.preco_venda : 0);
    const qtd = item ? item.quantidade : 1;
    
    const htmlLinha = ui.construirLinhaProduto(idUnico, prodObj, preco, qtd);
    document.getElementById("container-produtos").insertAdjacentHTML('beforeend', htmlLinha);
    window.calcularTotalGlobal();
};

window.removerLinhaProduto = (idUnico) => {
    document.getElementById(`linha-${idUnico}`)?.remove();
    window.calcularTotalGlobal();
};

// 4. Busca Inteligente: Produtos
window.filtrarProdutoUI = (idUnico) => {
    const termo = document.getElementById(`input-busca-prod-${idUnico}`).value.toLowerCase();
    const filtrados = estado.produtos.filter(p => p.nome.toLowerCase().includes(termo));
    
    ui.renderizarDropdown(`dropdown-prod-${idUnico}`, filtrados, `window.selecionarProduto_${idUnico}`, true);
    
    // Cria a função de seleção dinamicamente para a linha clicada
    window[`selecionarProduto_${idUnico}`] = (idProd) => {
        const prod = estado.produtos.find(p => p.id === idProd);
        document.getElementById(`input-busca-prod-${idUnico}`).value = prod.nome;
        document.getElementById(`select-prod-${idUnico}`).value = prod.id;
        
        const linha = document.getElementById(`linha-${idUnico}`);
        linha.querySelector(".inp-preco").value = prod.preco_venda.toFixed(2);
        
        document.getElementById(`dropdown-prod-${idUnico}`).classList.add("hidden");
        window.calcularTotalGlobal();
    };
};

window.mostrarProdutoUI = (idUnico) => window.filtrarProdutoUI(idUnico);

// 5. Busca Inteligente: Clientes
window.configurarBuscaCliente = (clienteIdSelecionado = "") => {
    const containerCliente = document.getElementById("ped-cliente").parentElement;
    const clienteObj = estado.clientes.find(c => String(c.id) === String(clienteIdSelecionado));
    const nomeClienteInicial = clienteObj ? clienteObj.nome : "";

    containerCliente.innerHTML = `
        <label class="block text-xs font-bold text-slate-400 uppercase mb-1">Cliente * (Digite para buscar)</label>
        <div class="relative">
            <input type="text" id="input-busca-cliente" value="${nomeClienteInicial}" placeholder="🔍 Digite o nome do cliente..." autocomplete="off" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-4 py-2.5 outline-none focus:border-amber-400 text-sm" oninput="window.filtrarDropdownClientes()" onfocus="window.mostrarDropdownClientes()">
            <input type="hidden" id="ped-cliente" value="${clienteIdSelecionado}">
            <div id="dropdown-cliente" class="hidden absolute left-0 right-0 top-full mt-1 bg-slate-950 border border-slate-700 rounded-xl shadow-xl max-h-48 overflow-y-auto z-50"></div>
        </div>
    `;
};

window.mostrarDropdownClientes = () => ui.renderizarDropdown("dropdown-cliente", estado.clientes, "window.selecionarCliente");

window.filtrarDropdownClientes = () => {
    const termo = document.getElementById("input-busca-cliente").value.toLowerCase();
    const filtrados = estado.clientes.filter(c => c.nome.toLowerCase().includes(termo));
    ui.renderizarDropdown("dropdown-cliente", filtrados, "window.selecionarCliente");
};

window.selecionarCliente = (id) => {
    const c = estado.clientes.find(cliente => cliente.id === id);
    document.getElementById("input-busca-cliente").value = c.nome;
    document.getElementById("ped-cliente").value = c.id;
    document.getElementById("dropdown-cliente").classList.add("hidden");
};

// 6. Galeria de Imagens
window.renderizarGaleriaImagens = () => {
    const container = document.getElementById("container-galeria-imagens");
    if (!container) return;
    container.innerHTML = "";

    // Imagens que já estão no servidor
    estado.imagensExistentes.forEach((imgUrl, index) => {
        container.innerHTML += `
            <div class="relative w-20 h-20 bg-slate-900 border border-slate-700 rounded-xl overflow-hidden group">
                <img src="${imgUrl}" class="w-full h-full object-cover">
                <button type="button" onclick="window.removerImagemExistente(${index})" class="absolute top-1 right-1 bg-rose-600 hover:bg-rose-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shadow cursor-pointer">✕</button>
            </div>
        `;
    });

    // Imagens novas anexadas no input
    const inputFiles = document.getElementById("ped-imagens-input");
    if (inputFiles && inputFiles.files) {
        Array.from(inputFiles.files).forEach((file) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                container.innerHTML += `
                    <div class="relative w-20 h-20 bg-slate-900 border border-amber-400/40 rounded-xl overflow-hidden group">
                        <img src="${e.target.result}" class="w-full h-full object-cover">
                        <span class="absolute bottom-0 inset-x-0 bg-amber-400/80 text-slate-950 text-[9px] font-bold text-center truncate px-1">Nova</span>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        });
    }
};

window.removerImagemExistente = (index) => {
    estado.imagensExistentes.splice(index, 1);
    window.renderizarGaleriaImagens();
};