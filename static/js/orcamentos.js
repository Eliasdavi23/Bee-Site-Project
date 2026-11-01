// ==========================================
// IMPORTAÇÕES
// ==========================================
import * as api from './modules/orcamentos/orcamentos_api.js';
import * as ui from './modules/orcamentos/orcamentos_ui.js';

let estado = {
    orcamentos: [],
    clientes: [],
    produtos: [],
    usuarios: []
};

let orcamentoEditandoId = null;

document.addEventListener("DOMContentLoaded", async () => {
    await carregarDadosIniciais();
    configurarEventos();
});

async function carregarDadosIniciais() {
    try {
        [estado.orcamentos, estado.clientes, estado.produtos, estado.usuarios] = await Promise.all([
            api.fetchOrcamentos(),
            api.fetchClientes(),
            api.fetchProdutos(),
            api.fetchUsuarios()
        ]);

        ui.renderizarTabela(estado.orcamentos);
        ui.preencherSelectClientes(document.getElementById("orc-cliente"), estado.clientes);
        ui.preencherSelectUsuarios(document.getElementById("orc-usuario"), estado.usuarios);
    } catch (error) {
        console.error("Erro ao carregar dados:", error);
    }
}

function alternarAbaOrcamentos(aba) {
    const abas = {
        historico: {
            btn: document.getElementById("tab-orc-historico"),
            panel: document.getElementById("painel-orc-historico")
        },
        novo: {
            btn: document.getElementById("tab-orc-novo"),
            panel: document.getElementById("modal-orcamento")
        }
    };

    Object.entries(abas).forEach(([chave, el]) => {
        const ativo = chave === aba;
        if (el.btn) el.btn.classList.toggle("active", ativo);
        if (el.panel) {
            el.panel.classList.toggle("active", ativo);
            el.panel.classList.toggle("hidden", !ativo);
        }
    });
}

window.alternarAbaOrcamentos = alternarAbaOrcamentos;

function configurarEventos() {
    const inputBusca = document.getElementById("filtro-orcamentos");
    if (inputBusca) {
        inputBusca.addEventListener("input", filtrarOrcamentos);
    }

    const inputClienteBusca = document.getElementById("orc-cliente-busca");
    if (inputClienteBusca) {
        inputClienteBusca.addEventListener("input", filtrarOpcaoClienteOrcamento);
        inputClienteBusca.addEventListener("focus", filtrarOpcaoClienteOrcamento);
        inputClienteBusca.addEventListener("keydown", (event) => {
            const suggestions = document.getElementById("orc-cliente-suggestions");
            const buttons = suggestions?.querySelectorAll('button[data-id]') || [];
            const total = buttons.length;
            let indiceAtual = Number(suggestions?.dataset.activeIndex || -1);

            if (event.key === "ArrowDown") {
                event.preventDefault();
                if (total === 0) return;
                indiceAtual = indiceAtual < total - 1 ? indiceAtual + 1 : 0;
                destacarOpcaoCliente(indiceAtual);
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                if (total === 0) return;
                indiceAtual = indiceAtual > 0 ? indiceAtual - 1 : total - 1;
                destacarOpcaoCliente(indiceAtual);
            } else if (event.key === "Enter") {
                event.preventDefault();
                const buttonSelecionado = buttons[indiceAtual] || buttons[0];
                if (buttonSelecionado) {
                    buttonSelecionado.click();
                }
            } else if (event.key === "Escape") {
                esconderSugestoesCliente();
            }
        });
    }

    document.addEventListener("click", (event) => {
        const suggestions = document.getElementById("orc-cliente-suggestions");
        const input = document.getElementById("orc-cliente-busca");
        const clicouDentroCliente = (suggestions && event.target.closest("#orc-cliente-suggestions")) || (input && event.target === input);
        if (!clicouDentroCliente) {
            esconderSugestoesCliente();
        }

        const clicouDentroProduto = event.target.closest('.prod-busca') || event.target.closest('.prod-suggestions');
        if (!clicouDentroProduto) {
            document.querySelectorAll('.prod-suggestions').forEach(s => {
                s.innerHTML = "";
                s.classList.add("hidden");
            });
        }
    });
}

function esconderSugestoesCliente() {
    const suggestions = document.getElementById("orc-cliente-suggestions");
    if (!suggestions) return;
    suggestions.innerHTML = "";
    suggestions.classList.add("hidden");
    suggestions.dataset.activeIndex = "-1";
}

function destacarOpcaoCliente(index) {
    const suggestions = document.getElementById("orc-cliente-suggestions");
    if (!suggestions) return;
    const buttons = suggestions.querySelectorAll('button[data-id]');
    suggestions.dataset.activeIndex = String(index);

    buttons.forEach((btn, idx) => {
        btn.classList.toggle("bg-slate-800", idx === index);
        btn.classList.toggle("text-amber-400", idx === index);
        btn.classList.toggle("text-slate-200", idx !== index);
    });
}

function selecionarClienteSugestao(button, input, hiddenInput, suggestions) {
    if (!button || !input || !hiddenInput || !suggestions) return;

    input.value = button.dataset.nome || "";
    hiddenInput.value = button.dataset.id || "";
    esconderSugestoesCliente();
}

function filtrarOpcaoClienteOrcamento() {
    const input = document.getElementById("orc-cliente-busca");
    const hiddenInput = document.getElementById("orc-cliente");
    const suggestions = document.getElementById("orc-cliente-suggestions");
    if (!input || !hiddenInput || !suggestions) return;

    const termo = input.value.toLowerCase().trim();

    const listaBase = !termo
        ? estado.clientes.slice(0, 8)
        : estado.clientes.filter(cliente => {
            const nome = (cliente.nome || "").toLowerCase();
            const telefone = (cliente.telefone || "").toLowerCase();
            return nome.includes(termo) || telefone.includes(termo);
        }).slice(0, 8);

    if (!termo) hiddenInput.value = "";

    if (listaBase.length === 0) {
        suggestions.innerHTML = '<div class="px-3 py-2 text-sm text-slate-400">Nenhum cliente encontrado</div>';
        suggestions.classList.remove("hidden");
        suggestions.dataset.activeIndex = "-1";
        return;
    }

    suggestions.innerHTML = listaBase.map((cliente, index) => `
        <button type="button" class="w-full text-left px-3 py-2 text-sm transition ${index === 0 ? 'bg-slate-800 text-amber-400' : 'text-slate-200 hover:bg-slate-800'}" data-id="${cliente.id}" data-nome="${cliente.nome}">
            <span class="font-medium">${cliente.nome}</span>
            ${cliente.telefone ? `<span class="text-slate-400"> • ${cliente.telefone}</span>` : ""}
        </button>
    `).join("");
    suggestions.classList.remove("hidden");
    suggestions.dataset.activeIndex = "0";

    suggestions.querySelectorAll('button[data-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            selecionarClienteSugestao(btn, input, hiddenInput, suggestions);
        });
    });
}

function esconderSugestoesProduto(suggestions) {
    if (!suggestions) return;
    suggestions.innerHTML = "";
    suggestions.classList.add("hidden");
}

function destacarOpcaoProduto(suggestions, index) {
    if (!suggestions) return;
    const buttons = suggestions.querySelectorAll('button[data-id]');
    suggestions.dataset.activeIndex = String(index);

    buttons.forEach((btn, idx) => {
        btn.classList.toggle("bg-slate-800", idx === index);
        btn.classList.toggle("text-amber-400", idx === index);
        btn.classList.toggle("text-slate-200", idx !== index);
    });
}

function selecionarProdutoSugestao(button, inputEl, hiddenInput, select, suggestions, container) {
    if (!button || !inputEl) return;

    const produtoId = button.dataset.id || "";
    const produtoNome = button.dataset.nome || "";
    const produtoPreco = parseFloat(button.dataset.preco || 0);

    inputEl.value = produtoNome;
    inputEl.dataset.id = produtoId;

    if (hiddenInput) hiddenInput.value = produtoId;
    if (select) {
        select.value = produtoId;
        select.dispatchEvent(new Event('change'));
    }

    if (suggestions) esconderSugestoesProduto(suggestions);

    const row = inputEl.closest('.linha-orc-item') || inputEl.closest('div.bg-slate-900') || container?.closest('div');
    const precoInput = row?.querySelector('.prod-preco');
    if (precoInput) {
        precoInput.value = Number(produtoPreco).toFixed(2);
        window.calcularTotalOrcamento();
    }
}

function filtrarOpcaoProdutoOrcamento(inputEl) {
    if (!inputEl) return;

    const termo = inputEl.value.toLowerCase().trim();
    const container = inputEl.closest('div.w-full');
    const select = container?.querySelector('.prod-select');
    const hiddenInput = container?.querySelector('.prod-id');
    const suggestions = container?.querySelector('.prod-suggestions');

    if (!suggestions) return;

    if (hiddenInput) hiddenInput.value = "";
    if (select) select.value = "";
    inputEl.dataset.id = "";

    const filtrados = !termo
        ? estado.produtos.slice(0, 8)
        : estado.produtos.filter(produto => {
            const nome = (produto.nome || "").toLowerCase();
            const preco = String(produto.preco_venda ?? produto.preco ?? "").toLowerCase();
            return nome.includes(termo) || preco.includes(termo);
        }).slice(0, 8);

    if (filtrados.length === 0) {
        suggestions.innerHTML = '<div class="px-3 py-2 text-sm text-slate-400">Nenhum produto encontrado</div>';
        suggestions.classList.remove("hidden");
        return;
    }

    suggestions.innerHTML = filtrados.map((produto, index) => {
        const precoVal = Number(produto.preco_venda ?? produto.preco ?? 0);
        return `
            <button type="button" class="w-full text-left px-3 py-2 text-sm transition ${index === 0 ? 'bg-slate-800 text-amber-400' : 'text-slate-200 hover:bg-slate-800'}" data-id="${produto.id}" data-nome="${produto.nome}" data-preco="${precoVal}">
                <span class="font-medium">${produto.nome}</span>
                <span class="text-emerald-400 font-bold"> • R$ ${precoVal.toFixed(2)}</span>
            </button>
        `;
    }).join("");
    suggestions.classList.remove("hidden");
    suggestions.dataset.activeIndex = "0";

    suggestions.querySelectorAll('button[data-id]').forEach(btn => {
        btn.addEventListener('click', () => {
            selecionarProdutoSugestao(btn, inputEl, hiddenInput, select, suggestions, container);
        });
    });
}

window.filtrarOpcaoProdutoOrcamento = filtrarOpcaoProdutoOrcamento;

// ==========================================
// REGRAS DE NEGÓCIO
// ==========================================

function filtrarOrcamentos() {
    const input = document.getElementById("filtro-orcamentos");
    if (!input) return;

    const termo = input.value.toLowerCase().trim();
    const filtrados = estado.orcamentos.filter(o => {
        const idStr = String(o.id).toLowerCase();
        const clienteStr = (o.cliente_nome || "").toLowerCase();
        const itensStr = Array.isArray(o.itens)
            ? o.itens.map(i => `${i.nome_produto || ""} ${i.observacao || ""}`).join(" ").toLowerCase()
            : "";
        return idStr.includes(termo) || clienteStr.includes(termo) || itensStr.includes(termo);
    });

    ui.renderizarTabela(filtrados);
}

async function salvarOrcamento() {
    const usuarioAtendente = document.getElementById("orc-usuario")?.value || "Sistema";
    const clienteId = document.getElementById("orc-cliente")?.value;

    if (!clienteId) {
        alert("Selecione um cliente para o orçamento.");
        document.getElementById("orc-cliente-busca")?.focus();
        return;
    }

    const linhas = document.querySelectorAll("#container-produtos-orc > div");
    if (linhas.length === 0) {
        alert("Adicione pelo menos um produto.");
        return;
    }

    const itens = [];
    linhas.forEach(row => {
        const prodBusca = row.querySelector('.prod-busca');
        const prodId = row.querySelector('.prod-id')?.value ||
            row.querySelector('.prod-select')?.value ||
            prodBusca?.dataset?.id ||
            prodBusca?.getAttribute('data-id');

        const qtd = Math.max(1, parseFloat(row.querySelector('.prod-qtd')?.value) || 1);
        const preco = Math.max(0, parseFloat(row.querySelector('.prod-preco')?.value) || 0);
        const obs = (row.querySelector('.prod-obs')?.value || "").trim();

        if (prodId && prodId !== "") {
            itens.push({
                produto_id: parseInt(prodId, 10),
                quantidade: qtd,
                preco_unitario: preco,
                observacao: obs
            });
        }
    });

    if (itens.length === 0) {
        alert("Selecione os produtos na lista de sugestões corretamente.");
        return;
    }

    const payload = {
        dados: {
            cliente_id: parseInt(clienteId, 10),
            usuario: usuarioAtendente,
            atendente: usuarioAtendente,
            status_producao: 'ORCAMENTO',
            desconto: Math.max(0, parseFloat(document.getElementById("orc-desconto")?.value) || 0),
            observacao: document.getElementById("orc-observacao")?.value || "",
            itens: itens
        }
    };

    try {
        const respostaAPI = orcamentoEditandoId
            ? await api.putOrcamentoAPI(orcamentoEditandoId, payload)
            : await api.postOrcamentoAPI(payload);

        const { ok, resultado } = respostaAPI;

        if (ok) {
            window.fecharModalOrcamento();
            estado.orcamentos = await api.fetchOrcamentos();
            ui.renderizarTabela(estado.orcamentos);
        } else {
            let mensagemErro = "Verifique os dados.";
            if (resultado && resultado.detail) {
                mensagemErro = typeof resultado.detail === 'string'
                    ? resultado.detail
                    : JSON.stringify(resultado.detail);
            }
            alert("Erro ao salvar:\n" + mensagemErro);
        }
    } catch (e) {
        console.error("Erro:", e);
        alert("Erro de conexão com o servidor.");
    }
}

async function converterParaVenda(orcamentoId) {
    if (!confirm(`Deseja aprovar o orçamento #${orcamentoId} e convertê-lo em Venda Oficial?`)) {
        return;
    }

    try {
        const { ok, resultado } = await api.converterVendaAPI(orcamentoId);
        if (ok) {
            estado.orcamentos = await api.fetchOrcamentos();
            ui.renderizarTabela(estado.orcamentos);
        } else {
            alert("Erro ao converter: " + (resultado?.detail || "Verifique os dados."));
        }
    } catch (error) {
        console.error("Erro:", error);
        alert("Erro de conexão com o servidor.");
    }
}

async function excluirOrcamento(orcamentoId) {
    if (!confirm(`Deseja realmente excluir o orçamento #${orcamentoId}?`)) return;
    if (await api.deleteOrcamentoAPI(orcamentoId)) {
        estado.orcamentos = await api.fetchOrcamentos();
        ui.renderizarTabela(estado.orcamentos);
    } else {
        alert("Erro ao excluir orçamento.");
    }
}

window.salvarOrcamento = salvarOrcamento;
window.converterParaVenda = converterParaVenda;
window.excluirOrcamento = excluirOrcamento;
window.filtrarOrcamentos = filtrarOrcamentos;
window.filtrarOpcaoClienteOrcamento = filtrarOpcaoClienteOrcamento;
window.filtrarOpcaoProdutoOrcamento = filtrarOpcaoProdutoOrcamento;
window.esconderSugestoesProduto = esconderSugestoesProduto;
window.destacarOpcaoProduto = destacarOpcaoProduto;

window.abrirModalOrcamento = () => {
    orcamentoEditandoId = null;

    const tituloModal = document.getElementById("modal-orcamento-titulo");
    const btnSalvar = document.getElementById("btn-salvar-orcamento");
    const lblAba = document.getElementById("lbl-aba-novo-orcamento");

    if (tituloModal) tituloModal.textContent = "Cadastrar Novo Orçamento";
    if (btnSalvar) btnSalvar.textContent = "💾 Salvar Orçamento";
    if (lblAba) lblAba.textContent = "Novo Orçamento";

    const container = document.getElementById("container-produtos-orc");
    if (container) container.innerHTML = "";

    const descInput = document.getElementById("orc-desconto");
    if (descInput) descInput.value = "0.00";

    const obsInput = document.getElementById("orc-observacao");
    if (obsInput) obsInput.value = "";

    const cliInput = document.getElementById("orc-cliente");
    if (cliInput) cliInput.value = "";

    const cliBusca = document.getElementById("orc-cliente-busca");
    if (cliBusca) cliBusca.value = "";

    esconderSugestoesCliente();

    const selUsuario = document.getElementById("orc-usuario");
    if (selUsuario) selUsuario.value = "Sistema";

    window.adicionarLinhaProdutoOrcamento();
    window.calcularTotalOrcamento();
    alternarAbaOrcamentos("novo");
};

window.abrirModalEdicaoOrcamento = async (orcamentoId) => {
    try {
        const resp = await fetch(`/api/orcamentos/${orcamentoId}`);
        if (!resp.ok) throw new Error("Não foi possível carregar os dados do orçamento.");

        const orcamento = await resp.json();
        orcamentoEditandoId = orcamento.id;

        const tituloModal = document.getElementById("modal-orcamento-titulo");
        const btnSalvar = document.getElementById("btn-salvar-orcamento");
        const lblAba = document.getElementById("lbl-aba-novo-orcamento");

        if (tituloModal) tituloModal.textContent = `Editar Orçamento #${orcamento.id}`;
        if (btnSalvar) btnSalvar.textContent = `💾 Salvar Alterações (#${orcamento.id})`;
        if (lblAba) lblAba.textContent = `Editando #${orcamento.id}`;

        const cliInput = document.getElementById("orc-cliente");
        const cliBusca = document.getElementById("orc-cliente-busca");
        if (cliInput) cliInput.value = orcamento.cliente_id || "";
        if (cliBusca) {
            const clienteSelecionado = estado.clientes.find(c => String(c.id) === String(orcamento.cliente_id));
            cliBusca.value = clienteSelecionado?.nome || orcamento.cliente_nome || "";
        }

        const descInput = document.getElementById("orc-desconto");
        if (descInput) descInput.value = Number(orcamento.desconto || 0).toFixed(2);

        const obsInput = document.getElementById("orc-observacao");
        if (obsInput) obsInput.value = orcamento.observacao || "";

        const selUsuario = document.getElementById("orc-usuario");
        if (selUsuario) selUsuario.value = orcamento.usuario_nome || "Sistema";

        const container = document.getElementById("container-produtos-orc");
        if (container) {
            container.innerHTML = "";

            if (orcamento.itens && orcamento.itens.length > 0) {
                orcamento.itens.forEach(item => {
                    const novaLinha = ui.construirLinhaProduto(estado.produtos, item.observacao || "");
                    container.appendChild(novaLinha);

                    const selectProd = novaLinha.querySelector('.prod-select');
                    const inputBuscaProd = novaLinha.querySelector('.prod-busca');
                    const hiddenInputProd = novaLinha.querySelector('.prod-id');
                    const inputQtd = novaLinha.querySelector('.prod-qtd');
                    const inputPreco = novaLinha.querySelector('.prod-preco');
                    const produtoSelecionado = estado.produtos.find(p => String(p.id) === String(item.produto_id));

                    if (selectProd) {
                        selectProd.value = item.produto_id;
                    }
                    if (inputBuscaProd) {
                        inputBuscaProd.value = produtoSelecionado?.nome || item.nome_produto || "";
                        inputBuscaProd.dataset.id = item.produto_id || "";
                    }
                    if (hiddenInputProd) hiddenInputProd.value = item.produto_id || "";
                    if (inputQtd) inputQtd.value = item.quantidade;
                    if (inputPreco) inputPreco.value = parseFloat(item.preco_unitario || 0).toFixed(2);
                });
            } else {
                window.adicionarLinhaProdutoOrcamento();
            }
        }

        window.calcularTotalOrcamento();
        alternarAbaOrcamentos("novo");
    } catch (e) {
        console.error(e);
        alert("Erro ao carregar orçamento para edição.");
    }
};

window.fecharModalOrcamento = () => {
    orcamentoEditandoId = null;
    const lblAba = document.getElementById("lbl-aba-novo-orcamento");
    if (lblAba) lblAba.textContent = "Novo Orçamento";
    alternarAbaOrcamentos("historico");
};

window.adicionarLinhaProdutoOrcamento = () => {
    const container = document.getElementById("container-produtos-orc");
    if (!container) return;

    const novaLinha = ui.construirLinhaProduto(estado.produtos);
    container.appendChild(novaLinha);
};

window.atualizarPrecoUnitario = (selectEl) => {
    const row = selectEl.closest('.linha-orc-item') || selectEl.closest('div.bg-slate-900');
    if (!row) return;

    const selectedOption = selectEl.options[selectEl.selectedIndex];
    const preco = selectedOption?.getAttribute('data-preco') || 0;
    const inputPreco = row.querySelector('.prod-preco');
    if (inputPreco) {
        inputPreco.value = parseFloat(preco).toFixed(2);
    }
    window.calcularTotalOrcamento();
};

window.calcularTotalOrcamento = () => {
    let subtotal = 0;
    const linhas = document.querySelectorAll("#container-produtos-orc > div");

    linhas.forEach(row => {
        const qtd = Math.max(0, parseFloat(row.querySelector('.prod-qtd')?.value) || 0);
        const preco = Math.max(0, parseFloat(row.querySelector('.prod-preco')?.value) || 0);
        subtotal += (qtd * preco);
    });

    const desconto = Math.max(0, parseFloat(document.getElementById("orc-desconto")?.value) || 0);
    const totalGeral = Math.max(0, subtotal - desconto);

    const lbl = document.getElementById("lbl-total-orc");
    if (lbl) {
        lbl.textContent = ui.formatarMoeda(totalGeral);
    }
};
