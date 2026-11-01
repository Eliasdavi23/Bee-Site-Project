from tests.test_periodo_filters import test_filtro_por_dia_especifico, test_filtro_por_mes_atual
from tests.test_full_system import (
    test_regra_de_ouro_100_porcento_localhost,
    test_schema_banco_possui_observacao_por_item,
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item,
)

if __name__ == "__main__":
    test_filtro_por_dia_especifico()
    test_filtro_por_mes_atual()
    test_regra_de_ouro_100_porcento_localhost()
    test_schema_banco_possui_observacao_por_item()
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item()
    print("Todos os testes passaram com sucesso (0 erros)!")
