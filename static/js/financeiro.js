import * as api from './modules/financeiro/financeiro_api.js';
import * as ui from './modules/financeiro/financeiro_ui.js';

// INICIALIZAÇÃO E EVENTOS

document.addEventListener('DOMContentLoaded', carregarFinanceiro);

function toggleDataInputFinanceiro() {
    const select = document.getElementById("fin-filtro-periodo");
    const input = document.getElementById("fin-data-especifica");
    if (!select || !input) return;

    input.classList.toggle("hidden", select.value !== "dia_especifico");
}

async function carregarFinanceiro() {
    try {
        const filtroSelect = document.getElementById("fin-filtro-periodo");
        const periodo = filtroSelect ? filtroSelect.value : "mes_atual";
        const inputData = document.getElementById("fin-data-especifica");
        const dataEspecifica = inputData && !inputData.classList.contains("hidden") ? inputData.value : null;

        const dados = await api.fetchResumoFinanceiro(periodo, dataEspecifica);
        ui.renderizarResumo(dados);

        await Promise.all([
            carregarContasPagar(),
            carregarClientesDevedores(periodo, dataEspecifica)
        ]);

    } catch (e) {
        console.error("Erro ao carregar dados do financeiro:", e);
    }
}

async function carregarContasPagar() {
    try {
        const dataEspecifica = document.getElementById('fin-data-contas')?.value || null;
        const contas = await api.fetchContasPagar(dataEspecifica);
        ui.renderizarContasPagar(contas);
    } catch (e) {
        console.error("Erro ao carregar contas a pagar:", e);
    }
}

async function carregarClientesDevedores(periodo = "mes_atual", dataEspecifica = null) {
    try {
        const devedores = await api.fetchClientesDevedores(periodo, dataEspecifica);
        ui.renderizarClientesDevedores(devedores);
    } catch (e) {
        console.error("Erro ao carregar clientes devedores:", e);
    }
}

async function salvarContaPagar(e) {
    if (e) e.preventDefault();

    const payload = {
        descricao: document.getElementById('cp-descricao')?.value,
        valor: parseFloat(document.getElementById('cp-valor')?.value) || 0,
        data_vencimento: document.getElementById('cp-vencimento')?.value,
        categoria: document.getElementById('cp-categoria')?.value,
        recorrente: document.getElementById('cp-recorrente')?.checked || false
    };

    const ok = await api.postContaPagar(payload);
    if (ok) {
        ui.fecharModalNovaConta();
        ui.limparFormularioConta();
        await carregarFinanceiro();
    } else {
        alert("Erro ao salvar a conta.");
    }
}

async function quitarConta(id) {
    if (confirm("Marcar esta conta como PAGA?")) {
        const ok = await api.quitarContaAPI(id);
        if (ok) {
            await carregarFinanceiro();
        } else {
            alert("Erro ao quitar conta.");
        }
    }
}

async function excluirConta(id) {
    if (confirm("Deseja apagar este registro de conta?")) {
        const ok = await api.deleteContaAPI(id);
        if (ok) {
            await carregarFinanceiro();
        } else {
            alert("Erro ao excluir conta.");
        }
    }
}

// ==========================================
// EXPOSIÇÃO GLOBAL (PONTE PARA O HTML)
// ==========================================
window.carregarFinanceiro = carregarFinanceiro;
window.carregarContasPagar = carregarContasPagar;
window.limparFiltroContasPagar = () => {
    const input = document.getElementById('fin-data-contas');
    if (input) input.value = '';
    carregarContasPagar();
};
window.toggleDataInputFinanceiro = toggleDataInputFinanceiro;
window.abrirModalNovaConta = ui.abrirModalNovaConta;
window.fecharModalNovaConta = ui.fecharModalNovaConta;
window.salvarContaPagar = salvarContaPagar;
window.quitarConta = quitarConta;
window.excluirConta = excluirConta;
