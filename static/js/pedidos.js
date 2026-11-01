// IMPORTAÇÕES (API e Interface Visual)
import * as api from './modules/pedidos/pedidos_api.js';
import * as ui from './modules/pedidos/pedidos_ui.js';

// ESTADO GLOBAL DA TELA
let estado = {
    pedidos: [],
    clientes: [],
    produtos: [],
    atendentes: [],
    atendentesDetalhes: [],
    configuracoes: {},
    imagensExistentes: []
};

document.addEventListener("DOMContentLoaded", carregarDadosIniciais);

async function carregarDadosIniciais() {
    [estado.pedidos, estado.clientes, estado.produtos, estado.atendentes, estado.configuracoes] = await Promise.all([
        api.fetchPedidos(),
        api.fetchClientes(),
        api.fetchProdutos(),
        api.fetchAtendentes(),
        api.fetchConfiguracoes()
    ]);

    ui.preencherSelectAtendentes(estado.atendentes);
    preencherFormularioConfiguracoes(estado.configuracoes);
    filtrarPedidos();
    configurarEventosGerais();
}

function configurarEventosGerais() {
    document.addEventListener("click", (e) => {
        if (!e.target.closest('.relative')) {
            document.querySelectorAll('[id^="dropdown-"]').forEach(d => d.classList.add("hidden"));
        }
    });

    document.getElementById("campo-busca")?.addEventListener("input", filtrarPedidos);
    document.getElementById("filtro-status-producao")?.addEventListener("change", filtrarPedidos);
    document.getElementById("ped-pagamento")?.addEventListener("change", atualizarValorPagoPorStatus);

    document.addEventListener("change", (e) => {
        if (e.target && e.target.id === "ped-imagens-input") {
            window.renderizarGaleriaImagens();
        }
    });
}

// =========================================================================
// SISTEMA DE ABAS DINÂMICAS E RESPONSIVAS (Histórico / Novo Pedido / Config)
// =========================================================================
function alternarAbaPedidos(aba) {
    const abas = {
        historico: {
            btn: document.getElementById("tab-btn-historico"),
            panel: document.getElementById("painel-aba-historico")
        },
        novo: {
            btn: document.getElementById("tab-btn-novo"),
            panel: document.getElementById("modal-pedido")
        },
        config: {
            btn: document.getElementById("tab-btn-config"),
            panel: document.getElementById("painel-aba-config")
        }
    };

    Object.entries(abas).forEach(([chave, elem]) => {
        const ativo = chave === aba;
        if (elem.btn) {
            elem.btn.classList.toggle("active", ativo);
            elem.btn.setAttribute("aria-selected", ativo ? "true" : "false");
        }
        if (elem.panel) {
            elem.panel.classList.toggle("active", ativo);
            elem.panel.classList.toggle("hidden", !ativo);
        }
    });

    if (aba === "config") {
        carregarPainelConfiguracoes();
    }
}

window.alternarAbaPedidos = alternarAbaPedidos;

function sincronizarSubAbasStatus(statusSelecionado) {
    const botoes = document.querySelectorAll("#subtabs-status-producao .bee-subtab-btn");
    botoes.forEach(btn => {
        btn.classList.toggle("active", (btn.dataset.status || "") === (statusSelecionado || ""));
    });
}

function filtrarPorStatusRapido(status) {
    const select = document.getElementById("filtro-status-producao");
    if (select) select.value = status;
    sincronizarSubAbasStatus(status);
    filtrarPedidos();
}

window.sincronizarSubAbasStatus = sincronizarSubAbasStatus;
window.filtrarPorStatusRapido = filtrarPorStatusRapido;

function obterTotalAtual() {
    let subtotal = 0;
    document.querySelectorAll(".linha-prod-item").forEach(l => {
        const qtd = Math.max(0, parseFloat(l.querySelector(".inp-qtd")?.value) || 0);
        const preco = Math.max(0, parseFloat(l.querySelector(".inp-preco")?.value) || 0);
        const subItem = qtd * preco;
        subtotal += subItem;

        const lblSub = l.querySelector(".lbl-subtotal-item");
        if (lblSub) {
            lblSub.textContent = ui.formatarMoeda(subItem);
        }
    });

    const desconto = Math.max(0, parseFloat(document.getElementById("ped-desconto")?.value) || 0);
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
    } else if (status === "PENDENTE") {
        input.value = "0.00";
    }
}

function filtrarPedidos() {
    const termo = document.getElementById("campo-busca")?.value.toLowerCase().trim() || "";
    const statusFiltro = document.getElementById("filtro-status-producao")?.value.toUpperCase().trim() || "";

    const filtrados = estado.pedidos.filter(p => {
        const itensTexto = Array.isArray(p.itens)
            ? p.itens.map(i => `${i.nome_produto || ""} ${i.observacao || ""}`).join(" ").toLowerCase()
            : "";

        const bateuTexto = !termo ||
            String(p.id).includes(termo) ||
            (p.cliente_nome?.toLowerCase().includes(termo)) ||
            (p.usuario_nome?.toLowerCase().includes(termo)) ||
            (p.observacao?.toLowerCase().includes(termo)) ||
            itensTexto.includes(termo);

        const stProd = String(p.status_producao || "").toUpperCase()
            .replace("EM PRODUÇÃO", "EM PRODUCAO")
            .replace("ESPERANDO INSTALAÇÃO", "ESPERANDO INSTALACAO");

        const bateuStatus = !statusFiltro || stProd === statusFiltro;

        return bateuTexto && bateuStatus;
    });

    ui.renderizarTabela(filtrados);
}

window.filtrarPedidos = filtrarPedidos;

// =========================================================================
// LÓGICA DE NEGÓCIO (CRUD de Pedidos com Observações por Item)
// =========================================================================
async function salvarPedido(irParaImpressao = false) {
    const clienteId = document.getElementById("ped-cliente")?.value;
    if (!clienteId) {
        alert("Por favor, selecione um cliente válido na lista.");
        document.getElementById("input-busca-cliente")?.focus();
        return;
    }

    const produtos = [];
    document.querySelectorAll(".linha-prod-item").forEach(l => {
        const prodId = l.querySelector(".sel-produto")?.value;
        const nomeInput = (l.querySelector(".inp-nome-prod")?.value || l.querySelector("input[type='text']")?.value || "").trim();
        const obsItem = (l.querySelector(".inp-obs-item")?.value || "").trim();
        const qtd = Math.max(1, parseInt(l.querySelector(".inp-qtd")?.value, 10) || 1);
        const preco = Math.max(0, parseFloat(l.querySelector(".inp-preco")?.value) || 0);

        if (prodId || nomeInput) {
            produtos.push({
                produto_id: prodId ? parseInt(prodId, 10) : null,
                nome_produto: nomeInput || "Produto",
                quantidade: qtd,
                preco_unitario: preco,
                observacao: obsItem
            });
        }
    });

    if (produtos.length === 0) {
        alert("Adicione pelo menos um produto ao pedido.");
        return;
    }

    const payload = {
        id: document.getElementById("ped-id").value || null,
        cliente_id: parseInt(clienteId, 10),
        usuario_nome: document.getElementById("ped-usuario").value || "Sistema",
        valor_total: window.calcularTotalGlobal(),
        desconto: Math.max(0, parseFloat(document.getElementById("ped-desconto").value) || 0),
        status_producao: document.getElementById("ped-producao").value,
        status_pagamento: document.getElementById("ped-pagamento").value,
        forma_pagamento: document.getElementById("ped-forma-pagamento").value,
        valor_pago: Math.max(0, parseFloat(document.getElementById("ped-vpago").value) || 0),
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

    if (resultado && resultado.sucesso) {
        estado.pedidos = await api.fetchPedidos();
        filtrarPedidos();
        if (irParaImpressao && resultado.id) {
            window.location.href = `/imprimir?id=${resultado.id}`;
            return;
        }
        window.fecharModalPedido();
    } else {
        alert("Erro ao salvar pedido: " + (resultado?.erro || "Verifique os dados informados."));
    }
}

async function editarPedido(id) {
    const pedido = estado.pedidos.find(p => p.id === id);
    if (!pedido) return;

    document.getElementById("ped-id").value = pedido.id;
    window.configurarBuscaCliente(pedido.cliente_id);
    document.getElementById("ped-usuario").value = pedido.usuario_nome || "Sistema";
    document.getElementById("ped-desconto").value = Number(pedido.desconto || 0).toFixed(2);
    document.getElementById("ped-producao").value = pedido.status_producao || "PENDENTE";
    document.getElementById("ped-pagamento").value = pedido.status_pagamento || "PENDENTE";
    document.getElementById("ped-forma-pagamento").value = pedido.forma_pagamento || "";
    document.getElementById("ped-vpago").value = Number(pedido.valor_pago || 0).toFixed(2);
    document.getElementById("ped-observacao").value = pedido.observacao || "";
    document.getElementById("modal-titulo").textContent = `Editar Pedido #${pedido.id}`;

    const lblAba = document.getElementById("lbl-aba-novo-pedido");
    if (lblAba) lblAba.textContent = `Editando #${pedido.id}`;

    // Imagens
    estado.imagensExistentes = await api.fetchImagensPedido(pedido.id);
    const inputImg = document.getElementById("ped-imagens-input");
    if (inputImg) inputImg.value = "";
    window.renderizarGaleriaImagens();

    // Produtos + Observações individuais
    const itens = await api.fetchItensPedido(pedido.id);
    const container = document.getElementById("container-produtos");
    container.innerHTML = "";

    if (itens.length > 0) {
        itens.forEach(item => window.adicionarLinhaProduto(item));
    } else {
        window.adicionarLinhaProduto();
    }

    alternarAbaPedidos("novo");
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

// =========================================================================
// CONFIGURAÇÕES DA GRÁFICA E EQUIPE
// =========================================================================
function preencherFormularioConfiguracoes(cfg) {
    if (!cfg) return;
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) el.value = val;
    };
    setVal("cfg-nome-empresa", cfg.nome_empresa || "SISTEMA GRÁFICA");
    setVal("cfg-documento-empresa", cfg.documento_empresa || "");
    setVal("cfg-telefone-empresa", cfg.telefone_empresa || "");
    setVal("cfg-endereco-empresa", cfg.endereco_empresa || "");
    setVal("cfg-modelo-impressao", cfg.modelo_impressao_padrao || "os");
    setVal("cfg-obs-padrao", cfg.obs_padrao_impressao || "Obrigado pela preferência!");
}

async function carregarPainelConfiguracoes() {
    const [cfg, detalhes] = await Promise.all([
        api.fetchConfiguracoes(),
        api.fetchAtendentesDetalhes()
    ]);
    estado.configuracoes = cfg;
    estado.atendentesDetalhes = detalhes;
    preencherFormularioConfiguracoes(cfg);
    renderizarListaAtendentesConfig(detalhes);
}

function renderizarListaAtendentesConfig(lista) {
    const container = document.getElementById("lista-atendentes-config");
    if (!container) return;
    if (!lista || lista.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-500">Nenhum atendente cadastrado.</p>`;
        return;
    }
    container.innerHTML = lista.map(u => `
        <div class="flex items-center justify-between bg-slate-950 border border-slate-800 px-3.5 py-2.5 rounded-xl text-xs">
            <span class="font-bold text-slate-200">👤 ${u.nome}</span>
            <button type="button" onclick="removerAtendenteConfig(${u.id})" class="text-rose-400 hover:text-rose-300 font-bold cursor-pointer">Remover</button>
        </div>
    `).join("");
}

window.salvarConfiguracoesEmpresa = async (event) => {
    event?.preventDefault();
    const payload = {
        nome_empresa: document.getElementById("cfg-nome-empresa")?.value || "SISTEMA GRÁFICA",
        subtitulo_empresa: "Gestão Interna & Produção Gráfica",
        documento_empresa: document.getElementById("cfg-documento-empresa")?.value || "",
        telefone_empresa: document.getElementById("cfg-telefone-empresa")?.value || "",
        endereco_empresa: document.getElementById("cfg-endereco-empresa")?.value || "",
        modelo_impressao_padrao: document.getElementById("cfg-modelo-impressao")?.value || "os",
        obs_padrao_impressao: document.getElementById("cfg-obs-padrao")?.value || ""
    };
    const resp = await api.salvarConfiguracoesAPI(payload);
    if (resp && resp.sucesso) {
        alert("Configurações da gráfica salvas com sucesso!");
    } else {
        alert("Erro ao salvar configurações.");
    }
};

window.salvarNovoAtendenteConfig = async (event) => {
    event?.preventDefault();
    const nome = document.getElementById("novo-atendente-nome")?.value.trim();
    const senha = document.getElementById("novo-atendente-senha")?.value.trim();
    if (!nome || !senha) return;

    const resp = await api.salvarAtendenteAPI(nome, senha);
    if (resp && resp.sucesso) {
        document.getElementById("novo-atendente-nome").value = "";
        document.getElementById("novo-atendente-senha").value = "";
        estado.atendentes = await api.fetchAtendentes();
        ui.preencherSelectAtendentes(estado.atendentes);
        await carregarPainelConfiguracoes();
    } else {
        alert("Erro ao salvar atendente.");
    }
};

window.removerAtendenteConfig = async (id) => {
    if (!confirm("Deseja remover este atendente?")) return;
    if (await api.removerAtendenteAPI(id)) {
        estado.atendentes = await api.fetchAtendentes();
        ui.preencherSelectAtendentes(estado.atendentes);
        await carregarPainelConfiguracoes();
    }
};

// =========================================================================
// EXPOSIÇÃO GLOBAL PARA O HTML
// =========================================================================
window.editarPedido = editarPedido;
window.excluirPedido = excluirPedido;
window.salvarPedido = salvarPedido;

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
    const lblAba = document.getElementById("lbl-aba-novo-pedido");
    if (lblAba) lblAba.textContent = "Novo Pedido";

    window.adicionarLinhaProduto();
    alternarAbaPedidos("novo");
};

window.fecharModalPedido = () => {
    const lblAba = document.getElementById("lbl-aba-novo-pedido");
    if (lblAba) lblAba.textContent = "Novo Pedido";
    alternarAbaPedidos("historico");
};

window.calcularTotalGlobal = () => {
    const total = obterTotalAtual();
    const lbl = document.getElementById("lbl-total");
    if (lbl) lbl.textContent = ui.formatarMoeda(total);

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
    const prodObj = item ? estado.produtos.find(p => String(p.id) === String(item.produto_id)) : null;
    const preco = item ? Number(item.preco_unitario || 0) : (prodObj ? Number(prodObj.preco_venda || 0) : 0);
    const qtd = item ? Number(item.quantidade || 1) : 1;
    const obs = item ? (item.observacao || "") : "";
    const nomeCustom = item ? (item.nome_produto || "") : "";

    const htmlLinha = ui.construirLinhaProduto(idUnico, prodObj, preco, qtd, obs, nomeCustom);
    document.getElementById("container-produtos").insertAdjacentHTML('beforeend', htmlLinha);
    window.calcularTotalGlobal();
};

window.removerLinhaProduto = (idUnico) => {
    document.getElementById(`linha-${idUnico}`)?.remove();
    window.calcularTotalGlobal();
};

window.filtrarProdutoUI = (idUnico) => {
    const termo = (document.getElementById(`input-busca-prod-${idUnico}`)?.value || "").toLowerCase();
    const filtrados = estado.produtos.filter(p => (p.nome || "").toLowerCase().includes(termo));

    ui.renderizarDropdown(`dropdown-prod-${idUnico}`, filtrados, `window.selecionarProduto_${idUnico}`, true);

    window[`selecionarProduto_${idUnico}`] = (idProd) => {
        const prod = estado.produtos.find(p => p.id === idProd);
        if (!prod) return;
        document.getElementById(`input-busca-prod-${idUnico}`).value = prod.nome;
        document.getElementById(`select-prod-${idUnico}`).value = prod.id;

        const linha = document.getElementById(`linha-${idUnico}`);
        if (linha) {
            linha.querySelector(".inp-preco").value = Number(prod.preco_venda || 0).toFixed(2);
        }

        document.getElementById(`dropdown-prod-${idUnico}`)?.classList.add("hidden");
        window.calcularTotalGlobal();
    };
};

window.mostrarProdutoUI = (idUnico) => window.filtrarProdutoUI(idUnico);

window.configurarBuscaCliente = (clienteIdSelecionado = "") => {
    const pedClienteEl = document.getElementById("ped-cliente");
    if (!pedClienteEl) return;
    const containerCliente = pedClienteEl.closest("div.relative")?.parentElement || pedClienteEl.parentElement;
    const clienteObj = estado.clientes.find(c => String(c.id) === String(clienteIdSelecionado));
    const nomeClienteInicial = clienteObj ? clienteObj.nome : "";

    containerCliente.innerHTML = `
        <label class="block text-xs font-bold text-slate-400 uppercase mb-1.5">Cliente * (Digite para buscar)</label>
        <div class="relative">
            <input type="text" id="input-busca-cliente" value="${nomeClienteInicial.replace(/"/g, '&quot;')}" placeholder="🔍 Digite o nome do cliente..." autocomplete="off" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-4 py-2.5 outline-none focus:border-amber-400 text-sm" oninput="window.filtrarDropdownClientes()" onfocus="window.mostrarDropdownClientes()">
            <input type="hidden" id="ped-cliente" value="${clienteIdSelecionado}">
            <div id="dropdown-cliente" class="hidden absolute left-0 right-0 top-full mt-1 bg-slate-950 border border-slate-700 rounded-xl shadow-xl max-h-48 overflow-y-auto z-50"></div>
        </div>
    `;
};

window.mostrarDropdownClientes = () => ui.renderizarDropdown("dropdown-cliente", estado.clientes, "window.selecionarCliente");

window.filtrarDropdownClientes = () => {
    const input = document.getElementById("input-busca-cliente");
    const termo = (input?.value || "").toLowerCase();
    if (!termo) {
        document.getElementById("ped-cliente").value = "";
    }
    const filtrados = estado.clientes.filter(c =>
        (c.nome || "").toLowerCase().includes(termo) ||
        (c.telefone || "").toLowerCase().includes(termo)
    );
    ui.renderizarDropdown("dropdown-cliente", filtrados, "window.selecionarCliente");
};

window.selecionarCliente = (id) => {
    const c = estado.clientes.find(cliente => cliente.id === id);
    if (!c) return;
    document.getElementById("input-busca-cliente").value = c.nome;
    document.getElementById("ped-cliente").value = c.id;
    document.getElementById("dropdown-cliente")?.classList.add("hidden");
};

window.renderizarGaleriaImagens = () => {
    const container = document.getElementById("container-galeria-imagens");
    if (!container) return;
    container.innerHTML = "";

    estado.imagensExistentes.forEach((imgUrl, index) => {
        container.innerHTML += `
            <div class="relative w-20 h-20 bg-slate-900 border border-slate-700 rounded-xl overflow-hidden group">
                <img src="${imgUrl}" class="w-full h-full object-cover">
                <button type="button" onclick="window.removerImagemExistente(${index})" class="absolute top-1 right-1 bg-rose-600 hover:bg-rose-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shadow cursor-pointer">✕</button>
            </div>
        `;
    });

    const inputFiles = document.getElementById("ped-imagens-input");
    if (inputFiles && inputFiles.files) {
        Array.from(inputFiles.files).forEach((file) => {
            const reader = new FileReader();
            reader.onload = function (e) {
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
