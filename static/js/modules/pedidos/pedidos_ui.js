// static/js/modules/pedidos/pedidos_ui.js

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

export function preencherSelectAtendentes(atendentes) {
    const selectUsuario = document.getElementById("ped-usuario");
    if (!selectUsuario) return;

    let htmlOptions = `<option value="Sistema">Sistema</option>`;
    atendentes.forEach(item => {
        const nome = typeof item === "object" ? item.nome : item;
        if (nome && nome !== "Sistema") {
            htmlOptions += `<option value="${escaparHtml(nome)}">${escaparHtml(nome)}</option>`;
        }
    });
    selectUsuario.innerHTML = htmlOptions;
}

function badgeStatusProducao(status) {
    const st = String(status || "PENDENTE").toUpperCase();
    const map = {
        "PENDENTE": "bg-amber-950/70 text-amber-400 border-amber-500/30",
        "EM PRODUCAO": "bg-blue-950/70 text-blue-400 border-blue-500/30",
        "EM PRODUÇÃO": "bg-blue-950/70 text-blue-400 border-blue-500/30",
        "AGUARDANDO RETIRADA": "bg-purple-950/70 text-purple-400 border-purple-500/30",
        "ESPERANDO INSTALACAO": "bg-cyan-950/70 text-cyan-400 border-cyan-500/30",
        "ESPERANDO INSTALAÇÃO": "bg-cyan-950/70 text-cyan-400 border-cyan-500/30",
        "FINALIZADO": "bg-emerald-950/70 text-emerald-400 border-emerald-500/30"
    };
    const cls = map[st] || "bg-slate-800 text-slate-300 border-slate-700";
    return `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold border ${cls}">${escaparHtml(st)}</span>`;
}

export function renderizarTabela(pedidos) {
    const tbody = document.getElementById("tabela-pedidos");
    const count = document.getElementById("total-pedidos-count");
    if (count) count.textContent = pedidos.length;
    if (!tbody) return;

    if (pedidos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-500">Nenhum pedido encontrado para os filtros selecionados.</td></tr>`;
        return;
    }

    tbody.innerHTML = pedidos.map(p => {
        const total = formatarMoeda(p.valor_total);
        const pago = formatarMoeda(p.valor_pago);
        const itens = Array.isArray(p.itens) ? p.itens : [];

        const htmlItens = itens.length > 0
            ? itens.map(it => {
                const obs = (it.observacao || "").trim();
                return `
                    <div class="text-xs leading-tight py-0.5">
                        <span class="font-bold text-amber-400">${it.quantidade}x</span>
                        <span class="text-slate-200 font-medium">${escaparHtml(it.nome_produto)}</span>
                        ${obs ? `<div class="text-[11px] text-amber-300/90 bg-amber-950/40 border border-amber-500/20 rounded px-1.5 py-0.5 mt-0.5 inline-block">📝 ${escaparHtml(obs)}</div>` : ""}
                    </div>
                `;
            }).join("")
            : `<span class="text-xs text-slate-500 italic">Sem itens detalhados</span>`;

        const obsGeral = (p.observacao || "").trim();
        const stPag = String(p.status_pagamento || "PENDENTE").toUpperCase();
        const corPag = stPag === "PAGO" ? "text-emerald-400" : (stPag === "PARCIAL" ? "text-amber-400" : "text-rose-400");

        return `
            <tr class="hover:bg-slate-900/70 transition border-b border-slate-800/60 align-top">
                <td class="p-4 font-black text-amber-400">#${p.id}</td>
                <td class="p-4">
                    <div class="font-bold text-slate-100">${escaparHtml(p.cliente_nome || 'Cliente Removido')}</div>
                    <div class="text-xs text-slate-400 mt-0.5">👤 Atendente: <span class="text-slate-300 font-semibold">${escaparHtml(p.usuario_nome || 'Sistema')}</span></div>
                </td>
                <td class="p-4 max-w-xs space-y-1">
                    ${htmlItens}
                    ${obsGeral ? `<div class="text-[11px] text-slate-400 border-t border-slate-800 pt-1 mt-1">📌 Obs. Pedido: ${escaparHtml(obsGeral)}</div>` : ""}
                </td>
                <td class="p-4 font-black text-emerald-400 whitespace-nowrap">${total}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    ${badgeStatusProducao(p.status_producao)}
                </td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="text-xs font-extrabold ${corPag}">${escaparHtml(stPag)} ${p.forma_pagamento ? `(${escaparHtml(p.forma_pagamento)})` : ''}</div>
                    <div class="text-xs text-slate-300 font-medium mt-0.5">${pago} / ${total}</div>
                </td>
                <td class="p-4 text-center text-xs text-slate-400 whitespace-nowrap">${escaparHtml(p.data || '-')}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="flex items-center justify-center gap-1.5">
                        <a href="/imprimir?id=${p.id}" class="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-bold transition cursor-pointer" title="Imprimir Pedido">🖨️ Imprimir</a>
                        <button type="button" onclick="editarPedido(${p.id})" class="p-2 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-lg text-xs font-bold transition cursor-pointer" title="Editar Pedido">✏️ Editar</button>
                        <button type="button" onclick="excluirPedido(${p.id})" class="p-2 bg-slate-800 hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold transition cursor-pointer" title="Excluir Pedido">🗑️</button>
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
                const preco = Number(item.preco_venda ?? item.preco ?? 0).toFixed(2);
                return `<div class="p-2.5 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer flex justify-between items-center border-b border-slate-900" onclick="${onclickCallback}(${item.id})">
                            <span class="font-medium">${escaparHtml(item.nome)}</span>
                            <span class="text-emerald-400 font-bold">R$ ${preco}</span>
                        </div>`;
            } else {
                return `<div class="p-2.5 hover:bg-slate-800 text-xs text-slate-200 cursor-pointer border-b border-slate-900" onclick="${onclickCallback}(${item.id})">
                            <span class="font-medium">${escaparHtml(item.nome)}</span>
                            ${item.telefone ? `<span class="text-slate-400 ml-1">• ${escaparHtml(item.telefone)}</span>` : ""}
                        </div>`;
            }
        }).join("");
    }
    dropdown.classList.remove("hidden");
}

export function construirLinhaProduto(idUnico, produto = null, precoInicial = 0, qtdInicial = 1, obsInicial = "", nomeCustomizado = "") {
    const nome = produto ? produto.nome : (nomeCustomizado || "");
    const pId = produto ? produto.id : "";
    const precoNum = Number(precoInicial) || 0;
    const qtdNum = Number(qtdInicial) || 1;
    const subtotalInicial = formatarMoeda(precoNum * qtdNum);

    return `
        <div class="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-2.5 linha-prod-item transition hover:border-slate-700" id="linha-${idUnico}">
            <div class="flex flex-col md:flex-row gap-2.5 items-center">
                <div class="flex-1 w-full relative">
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Produto / Serviço</label>
                    <input type="text" id="input-busca-prod-${idUnico}" value="${escaparHtml(nome)}" placeholder="🔍 Digite para buscar produto..." autocomplete="off" class="inp-nome-prod w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-amber-400" oninput="filtrarProdutoUI('${idUnico}')" onfocus="mostrarProdutoUI('${idUnico}')">
                    <input type="hidden" id="select-prod-${idUnico}" class="sel-produto" value="${pId}">
                    <div id="dropdown-prod-${idUnico}" class="hidden absolute left-0 right-0 top-full mt-1 bg-slate-950 border border-slate-700 rounded-lg shadow-xl max-h-48 overflow-y-auto z-50"></div>
                </div>
                <div class="w-full md:w-24">
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Quantidade</label>
                    <input type="number" min="1" value="${qtdNum}" oninput="calcularTotalGlobal()" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm text-center inp-qtd focus:outline-none focus:border-amber-400" placeholder="Qtd">
                </div>
                <div class="w-full md:w-32">
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Valor Unit. (R$)</label>
                    <input type="number" step="0.01" min="0" value="${precoNum.toFixed(2)}" oninput="calcularTotalGlobal()" class="w-full bg-slate-950 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm text-right inp-preco focus:outline-none focus:border-amber-400" placeholder="R$ Unit">
                </div>
                <div class="w-full md:w-28 text-right">
                    <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Subtotal</label>
                    <div class="py-2 px-2 text-sm font-black text-emerald-400 lbl-subtotal-item">${subtotalInicial}</div>
                </div>
                <div class="pt-4">
                    <button type="button" onclick="removerLinhaProduto('${idUnico}')" class="p-2 bg-slate-950 hover:bg-rose-950 text-rose-400 border border-slate-800 rounded-lg font-bold cursor-pointer transition" title="Remover item">✕</button>
                </div>
            </div>

            <!-- Campo de Observação Individual do Item -->
            <div class="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-slate-800/80">
                <label for="obs-item-${idUnico}" class="text-[11px] font-bold text-amber-400 uppercase whitespace-nowrap flex items-center gap-1">
                    📝 Observações deste Item:
                </label>
                <input
                    type="text"
                    id="obs-item-${idUnico}"
                    value="${escaparHtml(obsInicial)}"
                    placeholder="Ex: Acabamento fosco, furar no canto, papel couché 300g, laminação brilho..."
                    class="inp-obs-item flex-1 w-full bg-slate-950 border border-slate-700/80 text-slate-100 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-amber-400 transition"
                >
            </div>
        </div>
    `;
}
