from tests.test_periodo_filters import test_filtro_por_dia_especifico, test_filtro_por_mes_atual
from tests.test_full_system import (
    test_regra_de_ouro_100_porcento_localhost,
    test_schema_banco_possui_observacao_por_item,
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item,
    test_pedidos_e_orcamentos_com_numeros_decimais,
    test_pilares_gemini_e_gitignore,
)
from tests.test_whatsapp import (
    test_normalizacao_telefone_anti_gorila,
    test_schemas_pydantic_anti_gorila_whatsapp,
    test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento,
)

if __name__ == "__main__":
    test_filtro_por_dia_especifico()
    test_filtro_por_mes_atual()
    test_regra_de_ouro_100_porcento_localhost()
    test_schema_banco_possui_observacao_por_item()
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item()
    test_pedidos_e_orcamentos_com_numeros_decimais()
    test_pilares_gemini_e_gitignore()
    test_normalizacao_telefone_anti_gorila()
    test_schemas_pydantic_anti_gorila_whatsapp()
    test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento()
    print("Todos os testes passaram com sucesso (0 erros)!")
