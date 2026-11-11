// static/js/modules/produtos/produtos_ui.js

export function renderizarTabelaProdutos(dados) {
    const tbody = document.getElementById('tabela-produtos-body');
    const count = document.getElementById('total-produtos-count');
    if (count) count.textContent = dados.length;
    if (!tbody) return;

    if (!dados.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-zinc-500 text-sm">Nenhum produto cadastrado no estoque.</td></tr>';
        return;
    }

    tbody.innerHTML = dados.map(p => {
        const preco = Number(p.preco_venda || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        const json = JSON.stringify(p).replace(/"/g, '&quot;');
        return `
            <tr class="hover:bg-zinc-800/50 transition border-b border-zinc-800/80">
                <td class="p-4 font-black text-yellow-400">#${p.id}</td>
                <td class="p-4 font-bold text-white">${p.nome}</td>
                <td class="p-4 text-emerald-400 font-black">${preco}</td>
                <td class="p-4 text-zinc-300 font-medium">${p.quantidade || 0} un</td>
                <td class="p-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <button onclick='editarProduto(${json})' class="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-yellow-400 border border-zinc-700/60 rounded-lg text-xs font-bold transition cursor-pointer">Editar</button>
                        <button onclick="excluirProduto(${p.id})" class="px-3 py-1.5 bg-zinc-800 hover:bg-rose-950 text-rose-400 border border-zinc-700/60 rounded-lg text-xs font-bold transition cursor-pointer">Excluir</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

export function abrirModalProduto() {
    document.getElementById('form-produto').reset();
    document.getElementById('produto-id').value = '';
    document.getElementById('modal-produto-titulo').textContent = 'Novo Produto';
    alternarModal(true);
}

export function fecharModalProduto() { alternarModal(false); }

export function preencherModalProduto(produto) {
    document.getElementById('produto-id').value = produto.id;
    document.getElementById('produto-nome').value = produto.nome || '';
    document.getElementById('produto-preco').value = produto.preco_venda || 0;
    document.getElementById('produto-quantidade').value = produto.quantidade || 0;
    document.getElementById('modal-produto-titulo').textContent = 'Editar Produto';
    alternarModal(true);
}

function alternarModal(aberto) {
    const modal = document.getElementById('modal-produto');
    modal.classList.toggle('hidden', !aberto);
    modal.classList.toggle('flex', aberto);
}
