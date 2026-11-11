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
    const raw = String(status || "PENDENTE").trim().toUpperCase();
    const st = raw.replace(/_/g, " ").replace(/\s+/g, " ").replace("EM PRODUÇÃO", "EM PRODUCAO").replace("ESPERANDO INSTALAÇÃO", "ESPERANDO INSTALACAO");
    const map = {
        "PENDENTE": { cls: "bg-yellow-950/70 text-yellow-400 border-yellow-500/30", label: "PENDENTE" },
        "EM PRODUCAO": { cls: "bg-blue-950/70 text-blue-400 border-blue-500/30", label: "EM PRODUÇÃO" },
        "AGUARDANDO RETIRADA": { cls: "bg-purple-950/70 text-purple-400 border-purple-500/30", label: "AGUARDANDO RETIRADA" },
        "ESPERANDO INSTALACAO": { cls: "bg-cyan-950/70 text-cyan-400 border-cyan-500/30", label: "ESPERANDO INSTALAÇÃO" },
        "FINALIZADO": { cls: "bg-emerald-950/70 text-emerald-400 border-emerald-500/30", label: "FINALIZADO" },
        "CANCELADO": { cls: "bg-rose-950/70 text-rose-400 border-rose-500/30", label: "CANCELADO" },
        "ORCAMENTO": { cls: "bg-zinc-800 text-zinc-300 border-zinc-700", label: "ORÇAMENTO" }
    };
    const item = map[st] || { cls: "bg-zinc-800 text-zinc-300 border-zinc-700", label: raw.replace(/_/g, " ") };
    return `<span class="px-2.5 py-1 rounded-full text-[11px] font-bold border ${item.cls}">${escaparHtml(item.label)}</span>`;
}

export function renderizarTabela(pedidos) {
    const tbody = document.getElementById("tabela-pedidos");
    const count = document.getElementById("total-pedidos-count");
    if (count) count.textContent = pedidos.length;
    if (!tbody) return;

    if (pedidos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-zinc-500">Nenhum pedido encontrado para os filtros selecionados.</td></tr>`;
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
                        <span class="font-bold text-yellow-400">${it.quantidade}x</span>
                        <span class="text-zinc-200 font-medium">${escaparHtml(it.nome_produto)}</span>
                        ${obs ? `<div class="text-[11px] text-yellow-300 bg-yellow-950/40 border border-yellow-500/30 rounded px-1.5 py-0.5 mt-0.5 inline-block">${escaparHtml(obs)}</div>` : ""}
                    </div>
                `;
            }).join("")
            : `<span class="text-xs text-zinc-500 italic">Sem itens detalhados</span>`;

        const obsGeral = (p.observacao || "").trim();
        const stPag = String(p.status_pagamento || "PENDENTE").toUpperCase();
        const corPag = stPag === "PAGO" ? "text-emerald-400" : (stPag === "PARCIAL" ? "text-yellow-400" : "text-rose-400");

        return `
            <tr class="hover:bg-zinc-800/50 transition border-b border-zinc-800/80 align-top">
                <td class="p-4 font-black text-yellow-400">#${p.id}</td>
                <td class="p-4">
                    <div class="font-bold text-white">${escaparHtml(p.cliente_nome || 'Cliente Removido')}</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Atendente: <span class="text-zinc-300 font-semibold">${escaparHtml(p.usuario_nome || 'Sistema')}</span></div>
                </td>
                <td class="p-4 max-w-xs space-y-1">
                    ${htmlItens}
                    ${obsGeral ? `<div class="text-[11px] text-zinc-400 border-t border-zinc-800 pt-1 mt-1">Obs. Pedido: ${escaparHtml(obsGeral)}</div>` : ""}
                </td>
                <td class="p-4 font-black text-emerald-400 whitespace-nowrap">${total}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    ${badgeStatusProducao(p.status_producao)}
                </td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="text-xs font-extrabold ${corPag}">${escaparHtml(stPag)} ${p.forma_pagamento ? `(${escaparHtml(p.forma_pagamento)})` : ''}</div>
                    <div class="text-xs text-zinc-300 font-medium mt-0.5">${pago} / ${total}</div>
                </td>
                <td class="p-4 text-center text-xs text-zinc-400 whitespace-nowrap">${escaparHtml(p.data || '-')}</td>
                <td class="p-4 text-center whitespace-nowrap">
                    <div class="flex items-center justify-center gap-1.5">
                        <button type="button" onclick="abrirModalWhatsApp({tipo: 'status_pedido', pedido_id: ${p.id}})" class="px-2.5 py-1.5 bg-emerald-950/70 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-bold transition cursor-pointer" title="Enviar WhatsApp com IA">Whats</button>
                        <a href="/imprimir?id=${p.id}" class="px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700/60 rounded-lg text-xs font-bold transition cursor-pointer" title="Imprimir Pedido">Imprimir</a>
                        <button type="button" onclick="editarPedido(${p.id})" class="px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-yellow-400 border border-zinc-700/60 rounded-lg text-xs font-bold transition cursor-pointer" title="Editar Pedido">Editar</button>
                        <button type="button" onclick="excluirPedido(${p.id})" class="px-2.5 py-1.5 bg-zinc-800 hover:bg-rose-950 text-rose-400 border border-zinc-700/60 rounded-lg text-xs font-bold transition cursor-pointer" title="Excluir Pedido">Excluir</button>
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
        dropdown.innerHTML = `<div class="p-3 text-xs text-zinc-500 text-center">Nenhum item encontrado</div>`;
    } else {
        dropdown.innerHTML = itens.map(item => {
            if (isProduto) {
                const preco = Number(item.preco_venda ?? item.preco ?? 0).toFixed(2);
                return `<div class="p-2.5 hover:bg-zinc-800 text-xs text-zinc-200 cursor-pointer flex justify-between items-center border-b border-zinc-800" onclick="${onclickCallback}(${item.id})">
                            <span class="font-medium">${escaparHtml(item.nome)}</span>
                            <span class="text-emerald-400 font-bold">R$ ${preco}</span>
                        </div>`;
            } else {
                return `<div class="p-2.5 hover:bg-zinc-800 text-xs text-zinc-200 cursor-pointer border-b border-zinc-800" onclick="${onclickCallback}(${item.id})">
                            <span class="font-medium">${escaparHtml(item.nome)}</span>
                            ${item.telefone ? `<span class="text-zinc-400 ml-1">• ${escaparHtml(item.telefone)}</span>` : ""}
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
        <div class="bg-zinc-900/90 p-4 rounded-xl border border-zinc-800 space-y-3 linha-prod-item transition hover:border-zinc-700" id="linha-${idUnico}">
            <div class="flex flex-col md:flex-row gap-3 items-center">
                <div class="flex-1 w-full relative">
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Produto / Serviço</label>
                    <input type="text" id="input-busca-prod-${idUnico}" value="${escaparHtml(nome)}" placeholder="Digite para buscar produto..." autocomplete="off" class="inp-nome-prod w-full bg-black border border-zinc-800 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" oninput="filtrarProdutoUI('${idUnico}')" onfocus="mostrarProdutoUI('${idUnico}')">
                    <input type="hidden" id="select-prod-${idUnico}" class="sel-produto" value="${pId}">
                    <div id="dropdown-prod-${idUnico}" class="hidden absolute left-0 right-0 top-full mt-1 bg-black border border-zinc-800 rounded-lg shadow-xl max-h-48 overflow-y-auto z-50"></div>
                </div>
                <div class="w-full md:w-24">
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Quantidade</label>
                    <input type="number" step="any" min="0.01" value="${qtdNum}" oninput="calcularTotalGlobal()" class="w-full bg-black border border-zinc-800 text-white rounded-lg px-3 py-2 text-sm text-center inp-qtd focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" placeholder="Qtd">
                </div>
                <div class="w-full md:w-32">
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Valor Unit. (R$)</label>
                    <input type="number" step="any" min="0" value="${precoNum.toFixed(2)}" oninput="calcularTotalGlobal()" class="w-full bg-black border border-zinc-800 text-white rounded-lg px-3 py-2 text-sm text-right inp-preco focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent" placeholder="R$ Unit">
                </div>
                <div class="w-full md:w-28 text-right">
                    <label class="block text-[10px] font-bold text-zinc-400 uppercase mb-1">Subtotal</label>
                    <div class="py-2 px-2 text-sm font-black text-emerald-400 lbl-subtotal-item">${subtotalInicial}</div>
                </div>
                <div class="pt-4">
                    <button type="button" onclick="removerLinhaProduto('${idUnico}')" class="p-2 bg-black hover:bg-rose-950 text-rose-400 border border-zinc-800 rounded-lg font-bold cursor-pointer transition" title="Remover item">✕</button>
                </div>
            </div>

            <!-- Campo de Observação Individual do Item -->
            <div class="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-zinc-800">
                <label for="obs-item-${idUnico}" class="text-[11px] font-bold text-yellow-400 uppercase whitespace-nowrap flex items-center gap-1">
                    Observações deste Item:
                </label>
                <input
                    type="text"
                    id="obs-item-${idUnico}"
                    value="${escaparHtml(obsInicial)}"
                    placeholder="Ex: Acabamento fosco, furar no canto, papel couché 300g, laminação brilho..."
                    class="inp-obs-item flex-1 w-full bg-black border border-zinc-800 text-white placeholder-zinc-500 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition"
                >
            </div>
        </div>
    `;
}
