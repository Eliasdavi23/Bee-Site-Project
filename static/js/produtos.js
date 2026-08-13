import * as api from './modules/produtos/produtos_api.js';
import * as ui from './modules/produtos/produtos_ui.js';

let listaProdutos = [];

document.addEventListener('DOMContentLoaded', carregarProdutos);

async function carregarProdutos() {
    try {
        listaProdutos = await api.fetchProdutos();
        ui.renderizarTabelaProdutos(listaProdutos);
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
    }
}

function filtrarProdutos() {
    const termo = document.getElementById('input-busca-produto')?.value.toLowerCase() || '';
    ui.renderizarTabelaProdutos(listaProdutos.filter(p => p.nome.toLowerCase().includes(termo)));
}

function abrirModalProduto() { ui.abrirModalProduto(); }
function fecharModalProduto() { ui.fecharModalProduto(); }
function editarProduto(produto) { ui.preencherModalProduto(produto); }

async function salvarProduto(event) {
    event.preventDefault();
    const id = document.getElementById('produto-id').value;
    const payload = {
        nome: document.getElementById('produto-nome').value,
        preco_venda: parseFloat(document.getElementById('produto-preco').value),
        quantidade: parseInt(document.getElementById('produto-quantidade').value, 10) || 0
    };
    try {
        await api.salvarProduto(id, payload);
        fecharModalProduto();
        await carregarProdutos();
    } catch (error) {
        console.error('Erro ao salvar produto:', error);
        alert(error.message);
    }
}

async function excluirProduto(id) {
    if (!confirm('Tem certeza que deseja excluir este produto?')) return;
    try {
        if (await api.excluirProduto(id)) await carregarProdutos();
        else alert('Erro ao excluir produto.');
    } catch (error) {
        console.error('Erro ao excluir produto:', error);
    }
}

window.filtrarProdutos = filtrarProdutos;
window.abrirModalProduto = abrirModalProduto;
window.fecharModalProduto = fecharModalProduto;
window.editarProduto = editarProduto;
window.salvarProduto = salvarProduto;
window.excluirProduto = excluirProduto;
