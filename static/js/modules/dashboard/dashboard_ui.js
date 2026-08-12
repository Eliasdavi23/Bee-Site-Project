export function formatarMoeda(valor) {
    return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// 1. Renderiza os Cards de KPIs no Topo
export function renderizarKPIs(kpis) {
    if (!kpis) return;
    document.getElementById("dash-faturamento").innerText = formatarMoeda(kpis.faturamento_total);
    document.getElementById("dash-total-pedidos").innerText = kpis.total_pedidos || 0;
    document.getElementById("dash-ticket-medio").innerText = formatarMoeda(kpis.ticket_medio);
    document.getElementById("dash-em-producao").innerText = kpis.em_producao || 0;
    document.getElementById("dash-a-receber").innerText = formatarMoeda(kpis.saldo_pendente);
}

// 2. Renderiza as Barras de Progresso de Pagamento
export function renderizarPagamentos(pagamentos, totalFaturamento) {
    const container = document.getElementById("container-pagamentos-progresso");
    if (!container) return;

    container.innerHTML = "";
    if (!pagamentos) return;

    const chaves = Object.keys(pagamentos);
    if (chaves.length === 0) {
        container.innerHTML = `<p class="text-sm text-slate-500 italic">Nenhum registro no período.</p>`;
        return;
    }

    chaves.forEach(forma => {
        const valor = pagamentos[forma];
        const percentual = totalFaturamento > 0 ? ((valor / totalFaturamento) * 100).toFixed(1) : 0;

        container.innerHTML += `
            <div>
                <div class="flex justify-between text-xs font-bold mb-1">
                    <span class="text-slate-300 uppercase">${forma}</span>
                    <span class="text-amber-400">${formatarMoeda(valor)} (${percentual}%)</span>
                </div>
                <div class="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                    <div class="bg-amber-400 h-full rounded-full transition-all duration-500" style="width: ${percentual}%"></div>
                </div>
            </div>
        `;
    });
}

// 3. Renderiza Ranking de Atendentes
export function renderizarTopAtendentes(atendentes) {
    const container = document.getElementById("list-top-atendentes");
    if (!container) return;

    container.innerHTML = "";

    if (!atendentes || atendentes.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-500 italic">Nenhum atendimento registrado.</p>`;
        return;
    }

    atendentes.forEach((at, index) => {
        container.innerHTML += `
            <div class="flex justify-between items-center text-xs bg-slate-950/50 p-2.5 rounded-xl border border-slate-800">
                <div class="flex items-center gap-2">
                    <span class="font-black text-amber-400">#${index + 1}</span>
                    <span class="font-bold text-slate-200">${at.usuario_nome || 'Sistema'}</span>
                </div>
                <div class="text-right">
                    <span class="font-extrabold text-emerald-400 block">${formatarMoeda(at.total_vendas)}</span>
                    <span class="text-[10px] text-slate-500">${at.qtd_pedidos} pedido(s)</span>
                </div>
            </div>
        `;
    });
}

// 4. Renderiza Ranking de Produtos
export function renderizarTopProdutos(produtos) {
    const container = document.getElementById("list-top-produtos");
    if (!container) return;

    container.innerHTML = "";

    if (!produtos || produtos.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-500 italic">Nenhum produto vendido.</p>`;
        return;
    }

    produtos.forEach((prod, index) => {
        container.innerHTML += `
            <div class="flex justify-between items-center text-xs bg-slate-950/50 p-2.5 rounded-xl border border-slate-800">
                <div class="flex items-center gap-2">
                    <span class="font-black text-slate-400">#${index + 1}</span>
                    <span class="font-medium text-slate-300 truncate max-w-[130px]">${prod.nome_produto}</span>
                </div>
                <span class="font-bold text-amber-400 bg-amber-950/40 border border-amber-800/50 px-2 py-0.5 rounded-lg">
                    ${prod.qtd_total} un
                </span>
            </div>
        `;
    });
}

// 5. Tabela de Últimos Pedidos
export function renderizarUltimosPedidos(pedidos) {
    const tbody = document.getElementById("tabela-dash-pedidos");
    if (!tbody) return;

    tbody.innerHTML = "";

    if (!pedidos || pedidos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-slate-500 italic">Nenhum pedido encontrado.</td></tr>`;
        return;
    }

    pedidos.forEach(p => {
        tbody.innerHTML += `
            <tr class="hover:bg-slate-850 transition">
                <td class="p-3 font-bold text-amber-400">#${p.id}</td>
                <td class="p-3 text-slate-200 truncate max-w-[120px]">${p.cliente_nome}</td>
                <td class="p-3 font-bold text-emerald-400">${formatarMoeda(p.valor_total)}</td>
                <td class="p-3 text-center">${getBadgeStatus(p.status_producao)}</td>
            </tr>
        `;
    });
}

// 6. Resumo de Status da Produção
export function renderizarStatusProducao(statusMap, totalPedidos) {
    const container = document.getElementById("container-status-producao");
    if (!container) return;

    container.innerHTML = "";
    if (!statusMap) return;

    const legenda = {
        "PENDENTE": { label: "Pendente", cor: "bg-amber-500", textCor: "text-amber-400" },
        "EM PRODUCAO": { label: "Em Produção", cor: "bg-blue-500", textCor: "text-blue-400" },
        "AGUARDANDO RETIRADA": { label: "Aguardando Retirada", cor: "bg-purple-500", textCor: "text-purple-400" },
        "ESPERANDO INSTALACAO": { label: "Esperando Instalação", cor: "bg-cyan-500", textCor: "text-cyan-400" },
        "FINALIZADO": { label: "Finalizado", cor: "bg-emerald-500", textCor: "text-emerald-400" }
    };

    Object.keys(legenda).forEach(key => {
        const item = legenda[key];
        const qtd = statusMap[key] || 0;
        const pct = totalPedidos > 0 ? ((qtd / totalPedidos) * 100).toFixed(1) : 0;

        container.innerHTML += `
            <div class="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                <div class="flex justify-between items-center text-xs mb-1.5">
                    <span class="font-bold ${item.textCor}">${item.label}</span>
                    <span class="font-extrabold text-slate-200">${qtd} <span class="text-slate-500 text-[10px]">(${pct}%)</span></span>
                </div>
                <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                    <div class="${item.cor} h-full transition-all duration-500" style="width: ${pct}%"></div>
                </div>
            </div>
        `;
    });
}

// Helper para Badges da Tabela
export function getBadgeStatus(status) {
    switch (status) {
        case "PENDENTE":
            return `<span class="bg-amber-950/60 text-amber-400 border border-amber-800/60 text-[10px] font-bold px-2 py-0.5 rounded-md">PENDENTE</span>`;
        case "EM PRODUCAO":
            return `<span class="bg-blue-950/60 text-blue-400 border border-blue-800/60 text-[10px] font-bold px-2 py-0.5 rounded-md">EM PRODUÇÃO</span>`;
        case "AGUARDANDO RETIRADA":
            return `<span class="bg-purple-950/60 text-purple-400 border border-purple-800/60 text-[10px] font-bold px-2 py-0.5 rounded-md">RETIRADA</span>`;        case "ESPERANDO INSTALACAO":
            return `<span class="bg-cyan-950/60 text-cyan-400 border border-cyan-800/60 text-[10px] font-bold px-2 py-0.5 rounded-md">ESPERANDO INSTALAÇÃO</span>`;        case "FINALIZADO":
            return `<span class="bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 text-[10px] font-bold px-2 py-0.5 rounded-md">FINALIZADO</span>`;
        default:
            return `<span class="bg-slate-800 text-slate-400 text-[10px] font-bold px-2 py-0.5 rounded-md">${status || 'N/A'}</span>`;
    }
}