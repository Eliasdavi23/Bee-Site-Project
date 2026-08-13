import * as api from './modules/clientes/clientes_api.js';
import * as ui from './modules/clientes/clientes_ui.js';

let listaClientes = [];

document.addEventListener('DOMContentLoaded', carregarClientes);

async function carregarClientes() {
    try {
        listaClientes = await api.fetchClientes();
        ui.renderizarTabela(listaClientes);
    } catch (error) {
        console.error('Erro ao carregar clientes:', error);
    }
}

function filtrarClientes() {
    const termo = document.getElementById('input-busca-cliente')?.value.toLowerCase() || '';
    const filtrados = listaClientes.filter(c =>
        [c.nome, c.documento, c.cpf_cnpj, c.telefone]
            .some(valor => String(valor || '').toLowerCase().includes(termo))
    );
    ui.renderizarTabela(filtrados);
}

function abrirModalCliente() { ui.abrirModalCliente(); }
function fecharModalCliente() { ui.fecharModalCliente(); }
function editarCliente(cliente) { ui.preencherModalCliente(cliente); }

async function salvarCliente(event) {
    event?.preventDefault();
    const id = document.getElementById('cliente-id').value;
    const payload = {
        nome: document.getElementById('cliente-nome').value.trim(),
        documento: document.getElementById('cliente-doc').value.trim(),
        telefone: document.getElementById('cliente-telefone').value.trim(),
        email: document.getElementById('cliente-email').value.trim(),
        endereco: document.getElementById('cliente-endereco').value.trim()
    };

    if (!payload.nome || !payload.telefone) {
        alert('Preencha o Nome e o Telefone/WhatsApp do cliente.');
        return;
    }

    try {
        const resultado = await api.salvarCliente(id, payload);
        if (!resultado.sucesso && resultado.status !== 'ok') {
            throw new Error(resultado.erro || 'Verifique os campos.');
        }
        fecharModalCliente();
        await carregarClientes();
    } catch (error) {
        console.error('Erro ao salvar cliente:', error);
        alert(`Erro ao salvar cliente: ${error.message}`);
    }
}

async function excluirCliente(id) {
    if (!confirm('Tem certeza que deseja excluir este cliente?')) return;
    try {
        if (await api.excluirCliente(id)) await carregarClientes();
        else alert('Erro ao excluir cliente.');
    } catch (error) {
        console.error('Erro ao excluir cliente:', error);
    }
}

window.filtrarClientes = filtrarClientes;
window.abrirModalCliente = abrirModalCliente;
window.fecharModalCliente = fecharModalCliente;
window.editarCliente = editarCliente;
window.salvarCliente = salvarCliente;
window.excluirCliente = excluirCliente;
