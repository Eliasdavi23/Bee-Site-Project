import * as api from './modules/imprimir/imprimir_api.js';
import * as ui from './modules/imprimir/imprimir_ui.js';

let documentoCarregado = false;
let modeloAtual = 'orcamento';
let tipoDocumentoAtual = 'pedido';
let todosOsDocumentos = [];

document.addEventListener('DOMContentLoaded', inicializarImpressao);

async function inicializarImpressao() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    tipoDocumentoAtual = params.get('tipo') === 'orcamento' ? 'orcamento' : 'pedido';
    if (!id) return mostrarSeletorDocumentos();
    try {
        const resultado = await api.buscarDocumento(id, tipoDocumentoAtual);
        if (!resultado) {
            alert('Documento não encontrado no servidor!');
            window.location.href = '/imprimir';
            return;
        }
        ui.preencherDocumento(resultado.documento, resultado.itens, tipoDocumentoAtual);
        documentoCarregado = true;
        ui.alternarModelo(modeloAtual);
    } catch (error) {
        console.error('Erro ao carregar documento para impressão:', error);
        alert('Erro ao carregar os dados do documento.');
    }
}

async function mostrarSeletorDocumentos() {
    try { todosOsDocumentos = await api.buscarTodosDocumentos(); }
    catch (error) { console.warn('Não foi possível carregar documentos:', error); }
    ui.renderizarSeletorDocumentos(todosOsDocumentos);
}

function filtrarListaDocumentos() {
    const termo = document.getElementById('filtro-documentos')?.value.toLowerCase().trim() || '';
    ui.renderizarListaDocumentos(todosOsDocumentos.filter(doc =>
        [doc.id, doc.cliente_nome, doc.tipo].some(valor => String(valor || '').toLowerCase().includes(termo))
    ));
}

function alternarModelo(tipo) { modeloAtual = tipo; ui.alternarModelo(tipo); }
function validarEImprimir() {
    if (!documentoCarregado) return alert('Aguarde o carregamento completo do documento antes de imprimir!');
    setTimeout(() => window.print(), 400);
}

window.filtrarListaDocumentos = filtrarListaDocumentos;
window.alternarModelo = alternarModelo;
window.validarEImprimir = validarEImprimir;
