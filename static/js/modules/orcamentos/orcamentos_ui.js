// ==========================================
// INTERFACE E GERAÇÃO DE HTML (ORÇAMENTOS)
// ==========================================

export function formatarMoeda(valor) {
    return (Number(valor) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function escaparHtml(texto) {
    return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

export function renderizarTabela(orcamentos) {
    const tbody = document.getElementById("tabela-orcamentos");
    const contador = document.getElementById("total-orcamentos-count");
    if (!tbody) return;

    if (contador) contador.textContent = orcamentos.length;

    if (!orcamentos || orcamentos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="p-8 text-center text-slate-500 text-sm">Nenhum orçamento cadastrado no momento.</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = orcamentos.map(o => {
        const total = formatarMoeda(o.valor_total);
        const itens = Array.isArray(o.itens) ? o.itens : [];
        const htmlItens = itens.length > 0
            ? itens.map(it => {
                const obs = (it.observacao || "").trim();
                return `
                    <div class="text-xs py-0.5">
                        <span class="font-bold text-amber-400">${it.quantidade}x</span>
                        <span class="text-slate-200">${escaparHtml(it.nome_produto)}</span>
                        ${obs ? `<span class="ml-1 text-[11px] text-amber-300 bg-amber-950/40 border border-amber-500/20 rounded px-1.5 py-0.5">📝 ${escaparHtml(obs)}</span>` : ""}
                    </div>
                `;
            }).join("")
            : `<span class="text-xs text-slate-500 italic">Sem itens</span>`;

        return `
            <tr class="hover:bg-slate-800/40 transition align-top">
                <td class="p-4 font-black text-amber-400">#${o.id}</td>
                <td class="p-4 text-xs text-slate-400 whitespace-nowrap">${escaparHtml(o.data || '-')}</td>
                <td class="p-4">
                    <div class="text-slate-100 font-bold">${escaparHtml(o.cliente_nome || 'Cliente Balcão')}</div>
                    <div class="text-xs text-slate-400">👤 ${escaparHtml(o.usuario_nome || 'Sistema')}</div>
                </td>
                <td class="p-4 max-w-xs">${htmlItens}</td>
                <td class="p-4 text-emerald-400 font-black whitespace-nowrap">${total}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="flex flex-wrap items-center justify-center gap-1.5">
                        <button type="button" onclick="converterParaVenda(${o.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-xl text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                            🚀 Aprovar e Vender
                        </button>
                        <button type="button" onclick="abrirModalEdicaoOrcamento(${o.id})" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-3 py-1.5 rounded-xl text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                            ✏️ Editar
                        </button>
                        <a href="/imprimir?id=${o.id}&tipo=orcamento" class="bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold px-3 py-1.5 rounded-xl text-xs transition inline-block">
                            🖨️ Imprimir
                        </a>
                        <button type="button" onclick="excluirOrcamento(${o.id})" class="bg-slate-800 hover:bg-rose-950 text-rose-400 font-bold px-2.5 py-1.5 rounded-xl text-xs transition cursor-pointer" title="Excluir Orçamento">
                            🗑️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

export function preencherSelectClientes(selectEl, clientes) {
    if (!selectEl) return;
}

export function preencherSelectUsuarios(selectEl, usuarios) {
    if (!selectEl) return;
    let htmlU = '<option value="Sistema">Sistema</option>';
    usuarios.forEach(u => {
        const nomeUser = typeof u === 'object' ? (u.nome || u.usuario || u.username || '') : u;
        if (nomeUser && nomeUser !== "Sistema") {
            htmlU += `<option value="${escaparHtml(nomeUser)}">${escaparHtml(nomeUser)}</option>`;
        }
    });
    selectEl.innerHTML = htmlU;
    selectEl.value = "Sistema";
}

export function construirLinhaProduto(produtos, obsInicial = "") {
    let optionsProd = '<option value="">Selecione o produto...</option>';
    produtos.forEach(p => {
        const precoVal = Number(p.preco_venda ?? p.preco ?? 0);
        optionsProd += `<option value="${p.id}" data-preco="${precoVal}">${escaparHtml(p.nome)} - R$ ${precoVal.toFixed(2)}</option>`;
    });

    const div = document.createElement("div");
    div.className = "bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2.5 linha-orc-item";

    div.innerHTML = `
        <div class="flex flex-col sm:flex-row items-center gap-2.5">
            <div class="w-full sm:flex-[2] relative">
                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Produto / Serviço</label>
                <input type="text" placeholder="🔍 Digite ou selecione um produto..." class="prod-busca w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-xl pl-3 pr-8 py-2 text-xs outline-none focus:border-amber-400" autocomplete="off">
                <span class="pointer-events-none absolute right-3 bottom-2 text-slate-500">▾</span>
                <input type="hidden" class="prod-id" value="">
                <select class="prod-select hidden" onchange="atualizarPrecoUnitario(this)">
                    ${optionsProd}
                </select>
                <div class="prod-suggestions hidden absolute left-0 right-0 top-full mt-1 z-20 max-h-44 overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 shadow-xl"></div>
            </div>
            <div class="flex items-end gap-2 w-full sm:w-auto justify-end">
                <div>
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Qtd</label>
                    <input type="number" min="1" value="1" title="Quantidade" class="prod-qtd w-20 bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-2 py-2 text-xs text-center outline-none focus:border-amber-400" oninput="calcularTotalOrcamento()">
                </div>
                <div>
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Valor Unit. (R$)</label>
                    <input type="number" step="0.01" min="0" value="0.00" title="Preço Unitário" placeholder="0.00" class="prod-preco w-28 bg-slate-950 border border-slate-700 text-slate-100 rounded-xl px-2 py-2 text-xs text-right outline-none focus:border-amber-400" oninput="calcularTotalOrcamento()">
                </div>
                <button type="button" onclick="this.closest('.linha-orc-item').remove(); window.calcularTotalOrcamento();" class="p-2 bg-slate-950 hover:bg-rose-950 text-rose-400 border border-slate-800 rounded-lg font-bold cursor-pointer">✕</button>
            </div>
        </div>
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-slate-800/80">
            <label class="text-[11px] font-bold text-amber-400 uppercase whitespace-nowrap">📝 Observações deste Item:</label>
            <input type="text" value="${escaparHtml(obsInicial)}" placeholder="Ex: Acabamento fosco, furar no canto, medida específica..." class="prod-obs flex-1 w-full bg-slate-950 border border-slate-700/80 text-slate-100 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-400">
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
                window.destacarOpcaoProduto?.(suggestions, indiceAtual);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (total === 0) return;
                indiceAtual = indiceAtual > 0 ? indiceAtual - 1 : total - 1;
                window.destacarOpcaoProduto?.(suggestions, indiceAtual);
            } else if (event.key === 'Enter') {
                event.preventDefault();
                const buttonSelecionado = buttons[indiceAtual] || buttons[0];
                if (buttonSelecionado) {
                    buttonSelecionado.click();
                }
            } else if (event.key === 'Escape') {
                event.preventDefault();
                window.esconderSugestoesProduto?.(suggestions);
            }
        });
    }

    return div;
}
