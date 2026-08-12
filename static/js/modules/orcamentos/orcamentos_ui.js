// ==========================================
// INTERFACE E GERAÇÃO DE HTML (ORÇAMENTOS)
// ==========================================

export function formatarMoeda(valor) {
    return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function renderizarTabela(orcamentos) {
    const tbody = document.getElementById("tabela-orcamentos");
    const contador = document.getElementById("total-orcamentos-count");
    if (!tbody) return;

    if (contador) contador.textContent = orcamentos.length;

    if (!orcamentos || orcamentos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="p-8 text-center text-slate-500 text-sm">Nenhum orçamento cadastrado no momento.</td>
            </tr>
        `;
        return;
    }

    let html = "";
    orcamentos.forEach(o => {
        const total = formatarMoeda(o.valor_total);
        html += `
            <tr class="hover:bg-slate-800/40 transition">
                <td class="p-4 font-bold text-amber-400">#${o.id}</td>
                <td class="p-4 text-slate-300">${o.data || '-'}</td>
                <td class="p-4 text-slate-200 font-medium">${o.cliente_nome || 'Cliente Balcão'}</td>
                <td class="p-4 text-emerald-400 font-bold">${total}</td>
                <td class="p-4 text-center space-x-2">
                    <button onclick="converterParaVenda(${o.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-xl text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                        🚀 Aprovar e Vender
                    </button>
                    <button onclick="abrirModalEdicaoOrcamento(${o.id})" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-3 py-1.5 rounded-xl text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                        ✏️ Editar
                    </button>
                    <a href="/imprimir?id=${o.id}&tipo=orcamento" class="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-3 py-1.5 rounded-xl text-xs transition inline-block">
                        🖨️ Imprimir
                    </a>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

export function preencherSelectClientes(selectEl, clientes) {
    if (!selectEl) return;
    let html = '<option value="">Selecione um cliente...</option>';
    clientes.forEach(c => {
        html += `<option value="${c.id}">${c.nome}</option>`;
    });
    selectEl.innerHTML = html;
}

export function preencherSelectUsuarios(selectEl, usuarios) {
    if (!selectEl) return;
    let htmlU = '<option value="">Selecione o atendente...</option>';
    usuarios.forEach(u => {
        const nomeUser = typeof u === 'object' ? (u.nome || u.usuario || u.username || JSON.stringify(u)) : u;
        htmlU += `<option value="${nomeUser}">${nomeUser}</option>`;
    });
    selectEl.innerHTML = htmlU;
    selectEl.value = "Sistema";
}

export function construirLinhaProduto(produtos) {
    let optionsProd = '<option value="">Selecione o produto...</option>';
    produtos.forEach(p => {
        optionsProd += `<option value="${p.id}" data-preco="${p.preco || 0}">${p.nome} - R$ ${(p.preco || 0).toFixed(2)}</option>`;
    });

    const div = document.createElement("div");
    div.className = "flex flex-col sm:flex-row items-center gap-2 bg-slate-900 p-3 rounded-xl border border-slate-800";

    div.innerHTML = `
        <div class="w-full sm:flex-[2] relative">
            <input type="text" placeholder="Selecione um produto" class="prod-busca w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl pl-3 pr-8 py-2 text-xs outline-none focus:border-amber-400" autocomplete="off">
            <span class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500">▾</span>
            <input type="hidden" class="prod-id" value="">
            <select class="prod-select hidden" onchange="atualizarPrecoUnitario(this)">
                ${optionsProd}
            </select>
            <div class="prod-suggestions hidden absolute left-0 right-0 top-full mt-1 z-20 max-h-40 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 shadow-lg"></div>
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
            <input type="number" min="1" value="1" title="Quantidade" class="prod-qtd w-16 bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-2 py-2 text-xs text-center outline-none focus:border-amber-400" oninput="calcularTotalOrcamento()">
            <input type="number" step="0.01" title="Preço Unitário" placeholder="Preço" class="prod-preco w-24 bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-2 py-2 text-xs text-center outline-none focus:border-amber-400" oninput="calcularTotalOrcamento()">
            <button type="button" onclick="this.closest('.bg-slate-900').remove(); window.calcularTotalOrcamento();" class="text-red-500 hover:text-red-400 font-bold px-2 py-1 cursor-pointer">✕</button>
        </div>
    `;

    const buscaInput = div.querySelector('.prod-busca');
    if (buscaInput) {
        buscaInput.addEventListener('input', (event) => window.filtrarOpcaoProdutoOrcamento?.(event.currentTarget));
        buscaInput.addEventListener('focus', (event) => window.filtrarOpcaoProdutoOrcamento?.(event.currentTarget));
        buscaInput.addEventListener('keydown', (event) => {
            const suggestions = buscaInput.closest('div.w-full')?.querySelector('.prod-suggestions');
            const buttons = suggestions?.querySelectorAll('button[data-id]') || [];
            const total = buttons.length;
            let indiceAtual = Number(suggestions?.dataset.activeIndex || -1);

            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (total === 0) return;
                indiceAtual = indiceAtual < total - 1 ? indiceAtual + 1 : 0;
                destacarOpcaoProduto(suggestions, indiceAtual);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (total === 0) return;
                indiceAtual = indiceAtual > 0 ? indiceAtual - 1 : total - 1;
                destacarOpcaoProduto(suggestions, indiceAtual);
            } else if (event.key === 'Enter') {
                event.preventDefault();
                const buttonSelecionado = buttons[indiceAtual] || buttons[0];
                if (buttonSelecionado) {
                    buttonSelecionado.click();
                }
            } else if (event.key === 'Escape') {
                event.preventDefault();
                esconderSugestoesProduto(suggestions);
            }
        });
    }

    return div;
}
