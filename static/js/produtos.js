import * as api from './modules/produtos/produtos_api.js';
import * as ui from './modules/produtos/produtos_ui.js';

let listaProdutos = [];

function lerDecimal(valor, padrao = 0) {
    if (valor === null || valor === undefined || valor === "") return padrao;
    if (typeof valor === "number") return Number.isFinite(valor) ? valor : padrao;
    let texto = String(valor).trim().replace(/R\$\s?/gi, "").replace(/\s+/g, "");
    if (!texto) return padrao;
    if (texto.includes(",") && texto.includes(".")) {
        if (texto.lastIndexOf(",") > texto.lastIndexOf(".")) {
            texto = texto.replace(/\./g, "").replace(",", ".");
        } else {
            texto = texto.replace(/,/g, "");
        }
    } else if (texto.includes(",")) {
        texto = texto.replace(",", ".");
    }
    const num = parseFloat(texto);
    return Number.isFinite(num) ? num : padrao;
}

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
        preco_venda: Math.max(0, lerDecimal(document.getElementById('produto-preco').value, 0)),
        quantidade: Math.max(0, lerDecimal(document.getElementById('produto-quantidade').value, 0))
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
