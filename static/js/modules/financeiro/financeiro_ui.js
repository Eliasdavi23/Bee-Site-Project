// ==========================================
// INTERFACE E RENDERIZAÇÃO (FINANCEIRO)
// ==========================================

export function formatarMoeda(valor) {
    return `R$ ${(parseFloat(valor) || 0).toFixed(2)}`;
}

export function renderizarResumo(dados) {
    if (!dados) return;
    const entradas = dados.entradas_detalhadas || {};
    
    document.getElementById('fin-pix').innerText = formatarMoeda(entradas.PIX);
    document.getElementById('fin-credito').innerText = formatarMoeda(entradas.CREDITO);
    document.getElementById('fin-debito').innerText = formatarMoeda(entradas.DEBITO);
    document.getElementById('fin-dinheiro').innerText = formatarMoeda(entradas.DINHEIRO);
    document.getElementById('fin-link').innerText = formatarMoeda(entradas.LINK);

    document.getElementById('fin-total-recebido').innerText = formatarMoeda(dados.total_recebido_mes);
    document.getElementById('fin-a-receber').innerText = formatarMoeda(dados.total_a_receber_clientes);
    document.getElementById('fin-contas-pendentes').innerText = formatarMoeda(dados.contas_a_pagar_pendentes);
}

export function renderizarContasPagar(contas) {
    const tbody = document.getElementById('tabela-contas-pagar');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!contas || contas.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">Nenhuma conta cadastrada.</td></tr>`;
        return;
    }

    contas.forEach(c => {
        const isPago = c.status === 'PAGO';
        const badge = isPago 
            ? `<span class="px-2 py-1 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full text-xs font-bold">PAGO</span>`
            : `<span class="px-2 py-1 bg-rose-950 text-rose-400 border border-rose-800 rounded-full text-xs font-bold">PENDENTE</span>`;

        tbody.innerHTML += `
            <tr class="hover:bg-slate-800/50 transition">
                <td class="p-3 font-medium text-slate-200">${c.descricao} <br><span class="text-xs text-slate-500">${c.categoria || ''}${c.recorrente ? ' · Mensal' : ''}</span></td>
                <td class="p-3 text-slate-400">${c.data_vencimento}</td>
                <td class="p-3 font-bold text-slate-100">${formatarMoeda(c.valor)}</td>
                <td class="p-3 text-center">${badge}</td>
                <td class="p-3 text-right space-x-1">
                    ${!isPago ? `<button onclick="quitarConta(${c.id})" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs rounded-lg transition cursor-pointer">Quitar</button>` : ''}
                    <button onclick="excluirConta(${c.id})" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-lg transition cursor-pointer">Apagar</button>
                </td>
            </tr>
        `;
    });
}

export function renderizarClientesDevedores(devedores) {
    const tbody = document.getElementById('tabela-clientes-devedores');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!devedores || devedores.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-slate-500">Nenhum cliente inadimplente! 🎉</td></tr>`;
        return;
    }

    devedores.forEach(d => {
        tbody.innerHTML += `
            <tr class="hover:bg-slate-800/50 transition">
                <td class="p-3 font-bold text-slate-300">#${d.pedido_id}</td>
                <td class="p-3 font-medium text-slate-200">${d.cliente_nome || 'Cliente sem nome'}</td>
                <td class="p-3 text-slate-400">${formatarMoeda(d.valor_total)}</td>
                <td class="p-3 font-bold text-rose-400">${formatarMoeda(d.valor_pendente)}</td>
            </tr>
        `;
    });
}

export function abrirModalNovaConta() {
    const modal = document.getElementById('modal-conta');
    if (modal) modal.classList.replace('hidden', 'flex');
}

export function fecharModalNovaConta() {
    const modal = document.getElementById('modal-conta');
    if (modal) modal.classList.replace('flex', 'hidden');
}

export function limparFormularioConta() {
    const form = document.getElementById('form-conta');
    if (form) form.reset();
}
