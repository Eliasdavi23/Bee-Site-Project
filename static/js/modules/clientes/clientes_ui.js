export function renderizarTabela(dados) {
    const tbody = document.getElementById('tabela-clientes-body');
    const count = document.getElementById('total-clientes-count');
    if (count) count.textContent = dados.length;
    if (!tbody) return;

    if (!dados.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="p-6 text-center text-slate-500">Nenhum cliente cadastrado.</td></tr>';
        return;
    }

    tbody.innerHTML = dados.map(c => {
        const json = JSON.stringify(c).replace(/"/g, '&quot;');
        return `<tr class="hover:bg-slate-900/50 transition"><td class="p-4 font-bold text-amber-400">#${c.id}</td><td class="p-4 font-bold text-slate-100">${c.nome}</td><td class="p-4 text-slate-400">${c.cpf_cnpj || c.documento || '-'}</td><td class="p-4 text-slate-300">${c.telefone || '-'}</td><td class="p-4 text-slate-400">${c.email || '-'}</td><td class="p-4 text-center"><div class="flex items-center justify-center gap-2"><button type="button" onclick='editarCliente(${json})' class="p-2 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded-lg text-xs font-bold transition cursor-pointer">Editar</button><button type="button" onclick="excluirCliente(${c.id})" class="p-2 bg-slate-800 hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold transition cursor-pointer">Excluir</button></div></td></tr>`;
    }).join('');
}

export function abrirModalCliente() {
    document.getElementById('form-cliente')?.reset();
    document.getElementById('cliente-id').value = '';
    document.getElementById('modal-cliente-titulo').textContent = 'Novo Cliente';
    alternarModal(true);
}

export function fecharModalCliente() { alternarModal(false); }

export function preencherModalCliente(c) {
    document.getElementById('cliente-id').value = c.id;
    document.getElementById('cliente-nome').value = c.nome || '';
    document.getElementById('cliente-doc').value = c.cpf_cnpj || c.documento || '';
    document.getElementById('cliente-telefone').value = c.telefone || '';
    document.getElementById('cliente-email').value = c.email || '';
    document.getElementById('cliente-endereco').value = c.endereco || '';
    document.getElementById('modal-cliente-titulo').textContent = 'Editar Cliente';
    alternarModal(true);
}

function alternarModal(aberto) {
    const modal = document.getElementById('modal-cliente');
    if (!modal) return;
    modal.classList.toggle('hidden', !aberto);
    modal.classList.toggle('flex', aberto);
}
