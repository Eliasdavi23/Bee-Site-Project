// static/js/modules/orcamentos/orcamentos_ui.js

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
                <td colspan="6" class="p-8 text-center text-zinc-500 text-sm">Nenhum orçamento cadastrado no momento.</td>
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
                        <span class="font-bold text-yellow-400">${it.quantidade}x</span>
                        <span class="text-zinc-200">${escaparHtml(it.nome_produto)}</span>
                        ${obs ? `<span class="ml-1 text-[11px] text-yellow-300 bg-yellow-950/40 border border-yellow-500/30 rounded px-1.5 py-0.5">${escaparHtml(obs)}</span>` : ""}
                    </div>
                `;
            }).join("")
            : `<span class="text-xs text-zinc-500 italic">Sem itens</span>`;

        return `
            <tr class="hover:bg-zinc-800/50 transition border-b border-zinc-800/80 align-top">
                <td class="p-4 font-black text-yellow-400">#${o.id}</td>
                <td class="p-4 text-xs text-zinc-400 whitespace-nowrap">${escaparHtml(o.data || '-')}</td>
                <td class="p-4">
                    <div class="text-white font-bold">${escaparHtml(o.cliente_nome || 'Cliente Balcão')}</div>
                    <div class="text-xs text-zinc-400">Atendente: <span class="text-zinc-300 font-semibold">${escaparHtml(o.usuario_nome || 'Sistema')}</span></div>
                </td>
                <td class="p-4 max-w-xs">${htmlItens}</td>
                <td class="p-4 text-emerald-400 font-black whitespace-nowrap">${total}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="flex flex-wrap items-center justify-center gap-1.5">
                        <button type="button" onclick="converterParaVenda(${o.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                            Aprovar e Vender
                        </button>
                        <a href="/api/orcamentos/${o.id}/pdf" target="_blank" class="bg-zinc-800 hover:bg-yellow-400 hover:text-black text-yellow-400 border border-yellow-400/30 font-bold px-3 py-1.5 rounded-lg text-xs transition cursor-pointer inline-flex items-center gap-1" title="Visualizar ou Baixar Proposta em PDF">
                            PDF
                        </a>
                        <button type="button" onclick="enviarOrcamentoPdfWhatsApp(${o.id})" class="bg-emerald-950/90 hover:bg-emerald-800 text-emerald-300 border border-emerald-500/40 font-bold px-3 py-1.5 rounded-lg text-xs transition cursor-pointer inline-flex items-center gap-1 shadow-sm" title="Disparar PDF do orçamento no WhatsApp do cliente">
                            PDF Whats
                        </button>
                        <button type="button" onclick="abrirModalEdicaoOrcamento(${o.id})" class="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/60 font-bold px-2.5 py-1.5 rounded-lg text-xs transition shadow cursor-pointer inline-flex items-center gap-1">
                            Editar
                        </button>
                        <a href="/imprimir?id=${o.id}&tipo=orcamento" class="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/60 font-bold px-2.5 py-1.5 rounded-lg text-xs transition inline-block">
                            Imprimir
                        </a>
                        <button type="button" onclick="excluirOrcamento(${o.id})" class="bg-zinc-800 hover:bg-rose-950 text-rose-400 border border-zinc-700/60 font-bold px-2.5 py-1.5 rounded-lg text-xs transition cursor-pointer" title="Excluir Orçamento">
                            Excluir
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
    div.className = "bg-zinc-900/90 p-4 rounded-xl border border-zinc-800 space-y-3 linha-orc-item transition hover:border-zinc-700";

    div.innerHTML = `
        <div class="flex flex-col sm:flex-row items-center gap-3">
            <div class="w-full sm:flex-[2] relative">
                <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Produto / Serviço</label>
                <input type="text" placeholder="Digite ou selecione um produto..." class="prod-busca w-full bg-black border border-zinc-800 text-white placeholder-zinc-500 rounded-lg pl-3 pr-8 py-2 text-xs outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" autocomplete="off">
                <span class="pointer-events-none absolute right-3 bottom-2 text-zinc-500">▾</span>
                <input type="hidden" class="prod-id" value="">
                <select class="prod-select hidden" onchange="atualizarPrecoUnitario(this)">
                    ${optionsProd}
                </select>
                <div class="prod-suggestions hidden absolute left-0 right-0 top-full mt-1 z-20 max-h-44 overflow-y-auto rounded-lg border border-zinc-800 bg-black shadow-xl"></div>
            </div>
            <div class="flex items-end gap-2 w-full sm:w-auto justify-end">
                <div>
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Qtd</label>
                    <input type="number" step="any" min="0.01" value="1" title="Quantidade" class="prod-qtd w-20 bg-black border border-zinc-800 text-white rounded-lg px-2 py-2 text-xs text-center outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" oninput="calcularTotalOrcamento()">
                </div>
                <div>
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Valor Unit. (R$)</label>
                    <input type="number" step="any" min="0" value="0.00" title="Preço Unitário" placeholder="0.00" class="prod-preco w-28 bg-black border border-zinc-800 text-white rounded-lg px-2 py-2 text-xs text-right outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" oninput="calcularTotalOrcamento()">
                </div>
                <button type="button" onclick="this.closest('.linha-orc-item').remove(); window.calcularTotalOrcamento();" class="p-2 bg-black hover:bg-rose-950 text-rose-400 border border-zinc-800 rounded-lg font-bold cursor-pointer transition">✕</button>
            </div>
        </div>
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-zinc-800">
            <label class="text-[11px] font-bold text-yellow-400 uppercase whitespace-nowrap">Observações deste Item:</label>
            <input type="text" value="${escaparHtml(obsInicial)}" placeholder="Ex: Acabamento fosco, furar no canto, medida específica..." class="prod-obs flex-1 w-full bg-black border border-zinc-800 text-white placeholder-zinc-500 rounded-lg px-3 py-1.5 text-xs outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition">
        </div>
    `;

    const buscaInput = div.querySelector('.prod-busca');
    if (buscaInput) {
        buscaInput.addEventListener('input', (event) => window.filtrarOpcaoProdutoOrcamento?.(event.currentTarget));
        buscaInput.addEventListener('focus', (event) => window.mostrarOpcoesProdutoOrcamento?.(event.currentTarget));
    }

    return div;
}
