import * as api from './modules/dashboard/dashboard_api.js';
import * as ui from './modules/dashboard/dashboard_ui.js';

document.addEventListener("DOMContentLoaded", () => {
    atualizarDashboard();
});

function toggleDataInputDashboard() {
    const select = document.getElementById("dash-filtro-periodo");
    const input = document.getElementById("dash-data-especifica");
    if (!select || !input) return;

    input.classList.toggle("hidden", select.value !== "dia_especifico");
}

async function atualizarDashboard() {
    const filtroSelect = document.getElementById("dash-filtro-periodo");
    const periodo = filtroSelect ? filtroSelect.value : "mes_atual";
    const inputData = document.getElementById("dash-data-especifica");
    const dataEspecifica = inputData && !inputData.classList.contains("hidden") ? inputData.value : null;

    const data = await api.fetchEstatisticasDashboard(periodo, dataEspecifica);
    if (!data) return;

    // 1. Atualizar KPIs Superiores
    if (data.kpis) {
        ui.renderizarKPIs(data.kpis);
    }

    // 2. Renderizar Formas de Pagamento
    if (data.formas_pagamento && data.kpis) {
        ui.renderizarPagamentos(data.formas_pagamento, data.kpis.faturamento_total);
    }

    // 3. Renderizar Rankings
    ui.renderizarTopAtendentes(data.top_atendentes);
    ui.renderizarTopProdutos(data.top_produtos);

    // 4. Renderizar Tabelas e Status
    ui.renderizarUltimosPedidos(data.ultimos_pedidos);
    if (data.status_producao && data.kpis) {
        ui.renderizarStatusProducao(data.status_producao, data.kpis.total_pedidos);
    }
}

// Exposição para o HTML 

window.atualizarDashboard = atualizarDashboard;
window.toggleDataInputDashboard = toggleDataInputDashboard;