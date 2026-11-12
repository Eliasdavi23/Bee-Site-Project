from tests.test_periodo_filters import test_filtro_por_dia_especifico, test_filtro_por_mes_atual
from tests.test_full_system import (
    test_regra_de_ouro_100_porcento_localhost,
    test_schema_banco_possui_observacao_por_item,
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item,
    test_pedidos_e_orcamentos_com_numeros_decimais,
    test_pilares_gemini_e_gitignore,
    test_isolamento_imagens_uploads_e_gitignore,
    test_sistema_hud_unificado_e_zero_emojis,
)
from tests.test_whatsapp import (
    test_normalizacao_telefone_anti_gorila,
    test_schemas_pydantic_anti_gorila_whatsapp,
    test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento,
    test_sincronizacao_conversas_e_mensagens_anteriores,
    test_suporte_a_imagens_recebimento_e_envio,
    test_fluxo_gerar_pedido_e_comprovante_50,
    test_contador_mensagens_sem_resposta_e_badge_verde,
    test_marcar_todas_conversas_como_lidas,
    test_extracao_detalhes_pedido_sem_frases_de_bate_papo,
    test_pedido_ia_salva_com_usuario_logado,
    test_whatsapp_bridge_resilience_and_ddd_padrao,
)
from tests.test_orcamento_pdf import (
    test_gerador_pdf_orcamento_estrutura_e_validade,
    test_fluxo_completo_orcamento_pdf_e_disparo_whatsapp,
)

from tests.test_login_flow import (
    test_hash_e_verificacao_senhas,
    test_autenticacao_e_insensibilidade_a_maiusculas,
    test_validacao_sessao_e_redirecionamento_seguro,
    test_prevencao_open_redirect,
    test_protecao_forca_bruta_e_rate_limiting,
    test_login_sucesso_configura_cookies_corretamente,
)

from tests.test_comprovante_pix_ia import (
    test_validacao_estrita_valor_comprovante_pix,
    test_ia_visao_rejeita_comprovante_com_valor_divergente,
    test_ia_visao_aprova_comprovante_com_valor_exato,
)

if __name__ == "__main__":
    test_filtro_por_dia_especifico()
    test_filtro_por_mes_atual()
    test_regra_de_ouro_100_porcento_localhost()
    test_schema_banco_possui_observacao_por_item()
    test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item()
    test_pedidos_e_orcamentos_com_numeros_decimais()
    test_pilares_gemini_e_gitignore()
    test_isolamento_imagens_uploads_e_gitignore()
    test_sistema_hud_unificado_e_zero_emojis()
    test_normalizacao_telefone_anti_gorila()
    test_schemas_pydantic_anti_gorila_whatsapp()
    test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento()
    test_sincronizacao_conversas_e_mensagens_anteriores()
    test_suporte_a_imagens_recebimento_e_envio()
    test_fluxo_gerar_pedido_e_comprovante_50()
    test_contador_mensagens_sem_resposta_e_badge_verde()
    test_marcar_todas_conversas_como_lidas()
    test_extracao_detalhes_pedido_sem_frases_de_bate_papo()
    test_pedido_ia_salva_com_usuario_logado()
    test_whatsapp_bridge_resilience_and_ddd_padrao()
    test_gerador_pdf_orcamento_estrutura_e_validade()
    test_fluxo_completo_orcamento_pdf_e_disparo_whatsapp()
    test_hash_e_verificacao_senhas()
    test_autenticacao_e_insensibilidade_a_maiusculas()
    test_validacao_sessao_e_redirecionamento_seguro()
    test_prevencao_open_redirect()
    test_protecao_forca_bruta_e_rate_limiting()
    test_login_sucesso_configura_cookies_corretamente()
    test_validacao_estrita_valor_comprovante_pix()
    test_ia_visao_rejeita_comprovante_com_valor_divergente()
    test_ia_visao_aprova_comprovante_com_valor_exato()
    print("Todos os testes passaram com sucesso (0 erros)!")
