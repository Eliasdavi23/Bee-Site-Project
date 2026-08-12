// static/js/pedidos_ui.js

export function formatarMoeda(valor) {
    return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function preencherSelectAtendentes(atendentes) {
    const selectUsuario = document.getElementById("ped-usuario");
    if (!selectUsuario) return;

    let htmlOptions = `<option value="Sistema">Sistema</option>`;
    atendentes.forEach(nome => {
        if (nome && nome !== "Sistema") htmlOptions += `<option value="${nome}">${nome}</option>`;
    });
    selectUsuario.innerHTML = htmlOptions;
}

export function renderizarTabela(pedidos) {
    const tbody = document.getElementById("tabela-pedidos");
    const count = document.getElementById("total-pedidos-count");
    if (count) count.textContent = pedidos.length;
    if (!tbody) return;

    if (pedidos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-500">Nenhum pedido encontrado.</td></tr>`;
        return;
    }

    tbody.innerHTML = pedidos.map(p => {
        const total = formatarMoeda(p.valor_total);
        const pago = formatarMoeda(p.valor_pago);
        return `
            <tr class="hover:bg-slate-900/50 transition border-b border-slate-800/60">
                <td class="p-4 font-bold text-amber-400">#${p.id}</td>
                <td class="p-4 font-bold text-slate-100">${p.cliente_nome || 'Cliente Removido'}</td>
                <td class="p-4 text-slate-400">${p.usuario_nome || 'Sistema'}</td>
                <td class="p-4 font-bold text-emerald-400">${total}</td>
                <td class="p-4 text-center">
                    <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-slate-800 text-amber-400 border border-amber-400/20">${p.status_producao}</span>
                </td>
                <td class="p-4 text-center text-slate-300 font-medium">${pago} / ${total}</td>
                <td class="p-4 text-center text-xs text-slate-400">${p.data || '-'}</td>
                <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <button onclick="editarPedido(${p.id})" class="p-2 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-lg text-xs font-bold transition cursor-pointer">✏️ Editar</button>
                        <button onclick="excluirPedido(${p.id})" class="p-2 bg-slate-800 hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold transition cursor-pointer">🗑️ Excluir</button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

export function renderizarDropdown(idDropdown, itens, onclickCallback, isProduto = false) {
    const dropdown = document.getElementById(idDropdown);
    if (!dropdown) return;

    if (itens.length === 0) {
        dropdown.innerHTML = `<div class="p-3 text-xs text-slate-500 text-center">Nenhum item encontrado</div>`;
    } else {
        dropdown.innerHTML = itens.map(item => {
            if (isProduto) {
                return `<div class="p-2 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer flex justify-between items-center border-b border-slate-900" onclick="${onclickCallback}(${item.id})">
                            <span>${item.nome}</span> <span class="text-emerald-400 font-bold">R$ ${item.preco_venda.toFixed(2)}</span>
                        </div>`;
            } else {
                return `<div class="p-3 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer border-b border-slate-900" onclick="${onclickCallback}(${item.id})">
                            ${item.nome}
                        </div>`;
            }
        }).join("");
    }
    dropdown.classList.remove("hidden");
}

export function construirLinhaProduto(idUnico, produto = null, precoInicial = 0, qtdInicial = 1) {
    const nome = produto ? produto.nome : "";
    const pId = produto ? produto.id : "";
    
    return `
        <div class="flex flex-col md:flex-row gap-2 items-center bg-slate-900 p-2.5 rounded-xl border border-slate-800 linha-prod-item" id="linha-${idUnico}">
            <div class="flex-1 w-full relative">
                <input type="text" id="input-busca-prod-${idUnico}" value="${nome}" placeholder="🔍 Digite para buscar produto..." autocomplete="off" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-amber-400" oninput="filtrarProdutoUI('${idUnico}')" onfocus="mostrarProdutoUI('${idUnico}')">
                <input type="hidden" id="select-prod-${idUnico}" class="sel-produto" value="${pId}">
                <div id="dropdown-prod-${idUnico}" class="hidden absolute left-0 right-0 top-full mt-1 bg-slate-950 border border-slate-700 rounded-lg shadow-xl max-h-48 overflow-y-auto z-50"></div>
            </div>
            <div class="w-full md:w-24">
                <input type="number" min="1" value="${qtdInicial}" oninput="calcularTotalGlobal()" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm text-center inp-qtd" placeholder="Qtd">
            </div>
            <div class="w-full md:w-28">
                <input type="number" step="0.01" value="${precoInicial.toFixed(2)}" oninput="calcularTotalGlobal()" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm text-right inp-preco" placeholder="R$ Unit">
            </div>
            <button type="button" onclick="removerLinhaProduto('${idUnico}')" class="p-2 text-rose-400 hover:text-rose-300 font-bold cursor-pointer">✕</button>
        </div>
    `;
}