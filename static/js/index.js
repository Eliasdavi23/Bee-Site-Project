import * as api from './api.js';
import { setListaProdutos, adicionarLinhaProduto } from './produtos.js'; 

let listaPedidosGeral = [];

function parseDataBrOuIso(dataStr) {
    if (!dataStr || dataStr === '-') return new Date(0);
    if (dataStr.includes('-')) return new Date(dataStr.replace(' ', 'T'));

    const partes = dataStr.split(',');
    const dataPartes = partes[0].trim().split('/');
    if (dataPartes.length === 3) {
        const [dia, mes, ano] = dataPartes;
        const horaStr = partes[1] ? partes[1].trim() : '00:00:00';
        return new Date(`${ano}-${mes.padStart(2, '0')}-${dia.padStart(2, '0')}T${horaStr}`);
    }
    return new Date(dataStr);
}

function renderizarTabelaPedidos(pedidos) {
    const tbody = document.getElementById('tabela-pedidos');
    tbody.innerHTML = '';

    if (!pedidos || pedidos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="py-6 text-center text-gray-400">Nenhum pedido encontrado.</td></tr>`;
        return;
    }

    pedidos.forEach(p => {
        const vTotal = parseFloat(p.valor_total || 0);
        const vPago = parseFloat(p.valor_pago || 0);
        
        let badgePagamento = 'bg-red-100 text-red-800';
        if (p.status_pagamento === 'PAGO') badgePagamento = 'bg-emerald-100 text-emerald-800';
        else if (p.status_pagamento === 'PARCIAL') badgePagamento = 'bg-yellow-100 text-yellow-800';

        tbody.innerHTML += `
            <tr class="hover:bg-gray-50 transition border-b border-gray-100">
                <td class="py-4 px-6 font-bold text-gray-700">#${p.id}</td>
                <td class="py-4 px-6 font-medium text-gray-900">${p.cliente_nome || p.cliente_id || 'Cliente'}</td>
                <td class="py-4 px-6 font-semibold text-teal-700">${p.usuario_nome || 'Sistema'}</td>
                <td class="py-4 px-6 font-bold text-slate-800">R$ ${vTotal.toFixed(2)}</td>
                <td class="py-4 px-6 text-center">
                    <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">${p.status_producao}</span>
                </td>
                <td class="py-4 px-6 text-center">
                    <span class="px-3 py-1 rounded-full text-xs font-bold ${badgePagamento}">${p.status_pagamento}</span>
                    <div class="text-xs text-gray-500 mt-1 font-semibold">
                        R$ ${vPago.toFixed(2)} / <span class="text-gray-400">R$ ${vTotal.toFixed(2)}</span>
                    </div>
                </td>
                <td class="py-4 px-6 text-center text-gray-500">${p.data || '-'}</td>
                <td class="py-4 px-6 text-center space-x-1">
                    <button data-id="${p.id}" class="btn-imprimir bg-gray-700 hover:bg-gray-800 text-white font-bold text-xs px-2.5 py-1.5 rounded-lg shadow-sm">Imprimir</button>
                    <button data-id="${p.id}" class="btn-editar bg-blue-500 hover:bg-blue-600 text-white font-bold text-xs px-2.5 py-1.5 rounded-lg shadow-sm">Editar</button>
                    <button data-id="${p.id}" class="btn-excluir bg-red-500 hover:bg-red-600 text-white font-bold text-xs px-2.5 py-1.5 rounded-lg shadow-sm">Apagar</button>
                </td>
            </tr>
        `;
    });

    // Eventos dos botões da tabela (Garante o redirecionamento correto para a impressão)
    tbody.querySelectorAll('.btn-imprimir').forEach(btn => {
        btn.addEventListener('click', () => {
            const pedidoId = btn.dataset.id;
            window.location.href = `/imprimir?id=${pedidoId}`;
        });
    });

    tbody.querySelectorAll('.btn-editar').forEach(btn => {
        btn.addEventListener('click', () => editarPedido(parseInt(btn.dataset.id)));
    });

    tbody.querySelectorAll('.btn-excluir').forEach(btn => {
        btn.addEventListener('click', () => excluirPedido(parseInt(btn.dataset.id)));
    });
}

function calcularTotalGeral() {
    let subtotal = 0;
    document.querySelectorAll('.linha-produto').forEach(l => {
        const qtd = parseFloat(l.querySelector('.item-prod-qtd').value || 0);
        const vunit = parseFloat(l.querySelector('.item-prod-vunit').value || 0);
        subtotal += (qtd * vunit);
    });

    const desconto = parseFloat(document.getElementById('ped-desconto').value || 0);
    const totalComDesconto = Math.max(0, subtotal - desconto);

    document.getElementById('lbl-total').innerText = `R$ ${totalComDesconto.toFixed(2)}`;

    if (document.getElementById('ped-pagamento').value === 'PAGO') {
        document.getElementById('ped-vpago').value = totalComDesconto.toFixed(2);
    }

    return totalComDesconto;
}

async function carregarCombos() {
    const usuarios = await api.fetchUsuarios();
    document.getElementById('ped-usuario').innerHTML = '<option value="">Selecione o perfil...</option>' + 
        usuarios.map(u => `<option value="${u.nome}">${u.nome}</option>`).join('');

    const clientes = await api.fetchClientes();
    document.getElementById('ped-cliente').innerHTML = '<option value="">Selecione um cliente...</option>' + 
        clientes.map(c => `<option value="${c.id}">${c.nome}</option>`).join('');

    const produtos = await api.fetchProdutos();
    setListaProdutos(produtos);
}

async function carregarPedidos() {
    listaPedidosGeral = await api.fetchPedidos();
    if (listaPedidosGeral.length > 0) {
        listaPedidosGeral.sort((a, b) => parseDataBrOuIso(b.data) - parseDataBrOuIso(a.data));
    }
    filtrarPedidos();
}

function filtrarPedidos() {
    const termo = document.getElementById('campo-busca').value.toLowerCase().trim();
    if (!termo) return renderizarTabelaPedidos(listaPedidosGeral);

    const filtrados = listaPedidosGeral.filter(p => 
        String(p.id).includes(termo) || 
        String(p.cliente_nome || '').toLowerCase().includes(termo) || 
        String(p.usuario_nome || '').toLowerCase().includes(termo)
    );
    renderizarTabelaPedidos(filtrados);
}

async function abrirModalPedido() {
    await carregarCombos();
    document.getElementById('modal-titulo').innerText = "Cadastrar Novo Pedido";
    document.getElementById('ped-id').value = "";
    document.getElementById('ped-usuario').value = "";
    document.getElementById('container-produtos').innerHTML = "";
    document.getElementById('ped-desconto').value = "0.00";
    document.getElementById('ped-vpago').value = "0.00";
    document.getElementById('ped-pagamento').value = "PENDENTE";
    document.getElementById('ped-forma-pagamento').value = "";
    document.getElementById('ped-producao').value = "PENDENTE";
    
    const elObs = document.getElementById('ped-observacao') || document.getElementById('observacao');
    if (elObs) elObs.value = "";

    adicionarLinhaProduto("", 1, 0, calcularTotalGeral);
    document.getElementById('modal-pedido').classList.replace('hidden', 'flex');
}

async function editarPedido(id) {
    const pedido = listaPedidosGeral.find(p => p.id === id);
    if (!pedido) return;

    await carregarCombos();
    document.getElementById('modal-titulo').innerText = `Editar Pedido #${pedido.id}`;
    document.getElementById('ped-id').value = pedido.id;
    document.getElementById('ped-usuario').value = pedido.usuario_nome || "";
    document.getElementById('ped-cliente').value = pedido.cliente_id || "";
    document.getElementById('container-produtos').innerHTML = "";

    try {
        const itens = await api.fetchItensPedido(pedido.id);
        if (itens && itens.length > 0) {
            itens.forEach(item => adicionarLinhaProduto(item.produto_id, item.quantidade, item.preco_unitario, calcularTotalGeral));
        } else {
            adicionarLinhaProduto("", 1, 0, calcularTotalGeral);
        }
    } catch (e) {
        adicionarLinhaProduto("", 1, 0, calcularTotalGeral);
    }

    document.getElementById('ped-desconto').value = parseFloat(pedido.desconto || 0).toFixed(2);
    document.getElementById('ped-producao').value = pedido.status_producao || "PENDENTE";
    document.getElementById('ped-pagamento').value = pedido.status_pagamento || "PENDENTE";
    document.getElementById('ped-forma-pagamento').value = pedido.forma_pagamento || "";
    document.getElementById('ped-vpago').value = parseFloat(pedido.valor_pago || 0).toFixed(2);

    const elObs = document.getElementById('ped-observacao') || document.getElementById('observacao');
    if (elObs) elObs.value = pedido.observacao || "";

    calcularTotalGeral();
    document.getElementById('modal-pedido').classList.replace('hidden', 'flex');
}

async function salvarPedido() {
    const usuarioNome = document.getElementById('ped-usuario').value;
    const clienteId = document.getElementById('ped-cliente').value;

    if (!usuarioNome || !clienteId) {
        alert("Preencha o Atendente e o Cliente!");
        return;
    }

    const produtos = [];
    document.querySelectorAll('.linha-produto').forEach(l => {
        const prodId = l.querySelector('.item-prod-id').value;
        if (prodId) {
            produtos.push({
                produto_id: parseInt(prodId),
                nome_produto: l.querySelector('.item-prod-search').value,
                quantidade: parseInt(l.querySelector('.item-prod-qtd').value || 1),
                preco_unitario: parseFloat(l.querySelector('.item-prod-vunit').value || 0)
            });
        }
    });

    if (produtos.length === 0) {
        alert("Adicione pelo menos um produto ao pedido.");
        return;
    }

    const elObs = document.getElementById('ped-observacao') || document.getElementById('observacao');
    const observacaoTexto = elObs ? elObs.value : "";

    const payload = {
        id: document.getElementById('ped-id').value ? parseInt(document.getElementById('ped-id').value) : null,
        cliente_id: parseInt(clienteId),
        usuario_nome: usuarioNome,
        valor_total: calcularTotalGeral(),
        desconto: parseFloat(document.getElementById('ped-desconto').value || 0),
        valor_pago: parseFloat(document.getElementById('ped-vpago').value || 0),
        status_producao: document.getElementById('ped-producao').value,
        status_pagamento: document.getElementById('ped-pagamento').value,
        forma_pagamento: document.getElementById('ped-forma-pagamento').value,
        observacao: observacaoTexto,
        produtos
    };

    await api.salvarPedidoAPI(payload);
    fecharModal();
    carregarPedidos();
}

async function excluirPedido(id) {
    if (confirm(`Tem certeza que deseja apagar a venda #${id}?`)) {
        await api.excluirPedidoAPI(id);
        carregarPedidos();
    }
}

function fecharModal() {
    document.getElementById('modal-pedido').classList.replace('flex', 'hidden');
}

// Inicialização de Eventos Globais
document.addEventListener('DOMContentLoaded', () => {
    carregarPedidos();

    document.getElementById('campo-busca').addEventListener('input', filtrarPedidos);
    document.getElementById('ped-desconto').addEventListener('input', calcularTotalGeral);
    document.getElementById('ped-pagamento').addEventListener('change', (e) => {
        if (e.target.value === 'PAGO') document.getElementById('ped-vpago').value = calcularTotalGeral().toFixed(2);
    });

    window.abrirModalPedido = abrirModalPedido;
    window.fecharModalPedido = fecharModal;
    window.salvarPedido = salvarPedido;
    window.adicionarLinhaProduto = () => adicionarLinhaProduto("", 1, 0, calcularTotalGeral);
});