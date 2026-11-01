import * as api from './modules/imprimir/imprimir_api.js?v=2026c';
import * as ui from './modules/imprimir/imprimir_ui.js?v=2026c';

let documentoCarregado = false;
let modeloAtual = 'cupom';
let tipoDocumentoAtual = 'pedido';
let todosOsDocumentos = [];
let configuracoesAtuais = {};

document.addEventListener('DOMContentLoaded', inicializarImpressao);

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

function preencherInputsEditorEmpresa(cfg = {}) {
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val || '';
    };
    setVal('imp-cfg-nome', cfg.nome_empresa || 'BEE GRÁFICA & COMUNICAÇÃO VISUAL');
    setVal('imp-cfg-doc', cfg.documento_empresa || '');
    setVal('imp-cfg-tel', cfg.telefone_empresa || '');
    setVal('imp-cfg-email', cfg.email_empresa || '');
    setVal('imp-cfg-end', cfg.endereco_empresa || '');
}

async function inicializarImpressao() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    tipoDocumentoAtual = params.get('tipo') === 'orcamento' ? 'orcamento' : 'pedido';

    await carregarConfiguracoesIniciais();

    if (!id) {
        await mostrarSeletorDocumentos();
        return;
    }

    try {
        const resultado = await api.buscarDocumento(id, tipoDocumentoAtual);
        if (!resultado) {
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
        await mostrarSeletorDocumentos();
    }
}

async function mostrarSeletorDocumentos() {
    try {
        todosOsDocumentos = await api.buscarTodosDocumentos();
    } catch (error) {
        console.warn('Não foi possível carregar documentos:', error);
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
    const payload = {
        nome_empresa: document.getElementById('imp-cfg-nome')?.value || 'BEE GRÁFICA & COMUNICAÇÃO VISUAL',
        subtitulo_empresa: configuracoesAtuais.subtitulo_empresa || 'Soluções Gráficas & Impressão Digital',
        documento_empresa: document.getElementById('imp-cfg-doc')?.value || '',
        telefone_empresa: document.getElementById('imp-cfg-tel')?.value || '',
        email_empresa: document.getElementById('imp-cfg-email')?.value || '',
        endereco_empresa: document.getElementById('imp-cfg-end')?.value || '',
        modelo_impressao_padrao: configuracoesAtuais.modelo_impressao_padrao || 'cupom',
        obs_padrao_impressao: configuracoesAtuais.obs_padrao_impressao || 'Obrigado pela preferência!'
    };

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
        } else {
            alert('Erro ao salvar dados da empresa.');
        }
    } catch (e) {
        alert('Erro de conexão ao salvar dados da empresa.');
    }
}

function filtrarListaDocumentos() {
    const termo = document.getElementById('filtro-documentos')?.value.toLowerCase().trim() || '';
    ui.renderizarListaDocumentos(todosOsDocumentos.filter(doc =>
        [doc.id, doc.cliente_nome, doc.tipo].some(valor => String(valor || '').toLowerCase().includes(termo))
    ));
}

function alternarModelo(tipo) {
    modeloAtual = tipo;
    ui.alternarModelo(tipo);
}

function validarEImprimir() {
    if (!documentoCarregado) {
        alert('Selecione um pedido ou orçamento primeiro antes de acionar a impressão.');
        mostrarSeletorDocumentos();
        return;
    }
    document.getElementById('seletor-documentos-box')?.classList.add('hidden');
    document.getElementById('box-editar-empresa-impressao')?.classList.add('hidden');
    window.print();
}

window.filtrarListaDocumentos = filtrarListaDocumentos;
window.alternarModelo = alternarModelo;
window.validarEImprimir = validarEImprimir;
window.mostrarSeletorManual = mostrarSeletorManual;
window.toggleEditorEmpresaImpressao = toggleEditorEmpresaImpressao;
window.salvarDadosEmpresaRapido = salvarDadosEmpresaRapido;
