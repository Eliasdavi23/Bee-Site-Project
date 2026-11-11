import * as api from './modules/imprimir/imprimir_api.js?v=2026i';
import * as ui from './modules/imprimir/imprimir_ui.js?v=2026i';

// Mapeamento declarativo dos campos do formulário rápido da empresa
const CAMPOS_EMPRESA = [
    { id: 'imp-cfg-nome', key: 'nome_empresa', default: 'BEE GRÁFICA & COMUNICAÇÃO VISUAL' },
    { id: 'imp-cfg-doc', key: 'documento_empresa', default: '' },
    { id: 'imp-cfg-tel', key: 'telefone_empresa', default: '' },
    { id: 'imp-cfg-email', key: 'email_empresa', default: '' },
    { id: 'imp-cfg-end', key: 'endereco_empresa', default: '' },
    { id: 'imp-cfg-cidade', key: 'cidade_empresa', default: '' },
    { id: 'imp-cfg-estado', key: 'estado_empresa', default: '' }
];

let documentoCarregado = false;
let modeloAtual = 'cupom';
let tipoDocumentoAtual = 'pedido';
let todosOsDocumentos = [];
let configuracoesAtuais = {};

document.addEventListener('DOMContentLoaded', inicializarImpressao);

function preencherInputsEditorEmpresa(cfg = {}) {
    CAMPOS_EMPRESA.forEach(({ id, key, default: defVal }) => {
        const el = document.getElementById(id);
        if (el) el.value = cfg[key] || defVal;
    });
}

function coletarDadosEditorEmpresa() {
    const payload = {
        ...configuracoesAtuais,
        subtitulo_empresa: configuracoesAtuais.subtitulo_empresa || 'Soluções Gráficas & Impressão Digital',
        modelo_impressao_padrao: configuracoesAtuais.modelo_impressao_padrao || 'cupom',
        obs_padrao_impressao: configuracoesAtuais.obs_padrao_impressao || 'Obrigado pela preferência!'
    };
    CAMPOS_EMPRESA.forEach(({ id, key, default: defVal }) => {
        const el = document.getElementById(id);
        payload[key] = (el?.value || '').trim() || defVal;
    });
    return payload;
}

async function carregarConfiguracoesIniciais() {
    try {
        const res = await fetch('/api/configuracoes');
        if (res.ok) {
            configuracoesAtuais = await res.json();
            preencherInputsEditorEmpresa(configuracoesAtuais);
            ui.aplicarDadosEmpresa(configuracoesAtuais, tipoDocumentoAtual === 'orcamento');
        }
    } catch (e) {
        console.warn('Erro ao carregar configurações da empresa:', e);
    }
}

async function inicializarImpressao() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    tipoDocumentoAtual = params.get('tipo') === 'orcamento' ? 'orcamento' : 'pedido';

    if (!id) {
        await carregarConfiguracoesIniciais();
        await mostrarSeletorDocumentos();
        return;
    }

    try {
        const resultado = await api.buscarDocumento(id, tipoDocumentoAtual, configuracoesAtuais);
        if (!resultado) {
            await carregarConfiguracoesIniciais();
            await mostrarSeletorDocumentos();
            return;
        }

        configuracoesAtuais = resultado.configuracoes || configuracoesAtuais;
        preencherInputsEditorEmpresa(configuracoesAtuais);

        const isOrcamento = tipoDocumentoAtual === 'orcamento' || resultado.documento.tipo === 'ORCAMENTO';
        modeloAtual = isOrcamento ? 'orcamento' : 'cupom';

        ui.preencherDocumento(resultado.documento, resultado.itens, tipoDocumentoAtual, configuracoesAtuais);
        documentoCarregado = true;
        ui.alternarModelo(modeloAtual);
    } catch (error) {
        console.error('Erro ao carregar documento para impressão:', error);
        await carregarConfiguracoesIniciais();
        await mostrarSeletorDocumentos();
    }
}

async function mostrarSeletorDocumentos() {
    try {
        todosOsDocumentos = await api.buscarTodosDocumentos();
    } catch (error) {
        console.warn('Não foi possível carregar catálogo de documentos:', error);
    }
    ui.renderizarSeletorDocumentos(todosOsDocumentos);
}

function mostrarSeletorManual() {
    const box = document.getElementById('seletor-documentos-box');
    if (box && !box.classList.contains('hidden')) {
        box.classList.add('hidden');
        return;
    }
    mostrarSeletorDocumentos();
}

function toggleEditorEmpresaImpressao() {
    const box = document.getElementById('box-editar-empresa-impressao');
    if (box) {
        box.classList.toggle('hidden');
    }
}

async function salvarDadosEmpresaRapido(event) {
    event?.preventDefault();
    const payload = coletarDadosEditorEmpresa();

    try {
        const res = await fetch('/api/configuracoes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            configuracoesAtuais = data.configuracoes || payload;
            ui.aplicarDadosEmpresa(configuracoesAtuais, tipoDocumentoAtual === 'orcamento');
            document.getElementById('box-editar-empresa-impressao')?.classList.add('hidden');
            BeeHUD.success('Dados da empresa salvos com sucesso!');
        } else {
            BeeHUD.error('Erro ao salvar dados da empresa.');
        }
    } catch (e) {
        BeeHUD.error('Erro de conexão ao salvar dados da empresa.');
    }
}

function filtrarListaDocumentos() {
    const termo = (document.getElementById('filtro-documentos')?.value || '').toLowerCase().trim();
    if (!termo) {
        ui.renderizarListaDocumentos(todosOsDocumentos);
        return;
    }
    const filtrados = todosOsDocumentos.filter(doc =>
        [doc.id, doc.cliente_nome, doc.tipo].some(valor =>
            String(valor || '').toLowerCase().includes(termo)
        )
    );
    ui.renderizarListaDocumentos(filtrados);
}

function alternarModelo(tipo) {
    modeloAtual = tipo;
    ui.alternarModelo(tipo);
}

function validarEImprimir() {
    if (!documentoCarregado) {
        BeeHUD.warning('Selecione um pedido ou orçamento primeiro antes de acionar a impressão.');
        mostrarSeletorDocumentos();
        return;
    }
    document.getElementById('seletor-documentos-box')?.classList.add('hidden');
    document.getElementById('box-editar-empresa-impressao')?.classList.add('hidden');
    window.print();
}

// Exportações globais para eventos de clique no template
window.filtrarListaDocumentos = filtrarListaDocumentos;
window.alternarModelo = alternarModelo;
window.validarEImprimir = validarEImprimir;
window.mostrarSeletorManual = mostrarSeletorManual;
window.toggleEditorEmpresaImpressao = toggleEditorEmpresaImpressao;
window.salvarDadosEmpresaRapido = salvarDadosEmpresaRapido;
