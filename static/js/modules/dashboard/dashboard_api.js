export async function fetchEstatisticasDashboard(periodo = "mes_atual", dataEspecifica = null) {
    try {
        const params = new URLSearchParams({ periodo });
        if (dataEspecifica) {
            params.set('data', dataEspecifica);
        }
        const response = await fetch(`/api/dashboard/estatisticas?${params.toString()}`);
        if (!response.ok) throw new Error("Erro ao buscar dados do dashboard");
        return await response.json();
    } catch (error) {
        console.error("Erro na API do Dashboard:", error);
        return null;
    }
}