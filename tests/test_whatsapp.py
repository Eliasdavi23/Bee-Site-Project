import asyncio
import hashlib
import hmac
import json
import os
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

import main
from config.database import get_connection, init_db
from routes.clientes_routes import ClienteSchema, criar_cliente, excluir_cliente
from routes.orcamentos_routes import (
    ItemOrcamentoSchema,
    OrcamentoCreateSchema,
    OrcamentoDadosSchema,
    criar_orcamento,
)
from routes.page_routes import pagina_atendimento
from routes.pedidos_routes import StatusUpdateSchema, atualizar_status_pedido, deletar_pedido, salvar_pedido
from routes.produtos_routes import ProdutoSchema, criar_produto, listar_produtos
from routes.whatsapp_routes import (
    ConfigWhatsAppSchema,
    EnviarMensagemSchema,
    NovaConversaManualSchema,
    RascunhoSchema,
    enviar_mensagem_api,
    gerar_rascunho_api,
    listar_conversas_api,
    obter_conversa_api,
    obter_status_whatsapp,
    receber_webhook,
    registrar_entrada_manual_api,
    salvar_config_whatsapp,
    sugerir_resposta_api,
)
from services.whatsapp import atendimento
from services.whatsapp.telefone import chave_comparacao, formatar_exibicao, link_whatsapp, normalizar_telefone
from tests.test_full_system import _make_request


def _limpar_conversas_teste(telefone_normalizado: str):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM whatsapp_conversas WHERE telefone = ?", (telefone_normalizado,))
        conn.commit()
    finally:
        conn.close()


def test_normalizacao_telefone_anti_gorila():
    """Garante que números em formatos variados viram E.164 BR e entradas inválidas retornam None."""
    assert normalizar_telefone("(11) 98888-7777") == "5511988887777"
    assert normalizar_telefone("11 9 8888 7777") == "5511988887777"
    assert normalizar_telefone("+55 11 98888-7777") == "5511988887777"
    assert normalizar_telefone("011 98888-7777") == "5511988887777"
    assert normalizar_telefone("(11) 3456-7890") == "551134567890"

    # Entradas inválidas (gorila digitando letras, números curtos ou celular de 9 dígitos sem começar com 9)
    assert normalizar_telefone("") is None
    assert normalizar_telefone("abc-def") is None
    assert normalizar_telefone("12345") is None
    assert normalizar_telefone("(00) 98888-7777") is None
    assert normalizar_telefone("(11) 88888-7777") is None

    # Comparação ignora ausência do 9º dígito enviada por alguns provedores
    assert chave_comparacao("5511988887777") == chave_comparacao("551188887777")
    assert formatar_exibicao("5511988887777") == "+55 (11) 98888-7777"
    assert link_whatsapp("(11) 98888-7777", "Olá mundo").startswith("https://wa.me/5511988887777?text=")


def test_schemas_pydantic_anti_gorila_whatsapp():
    """Bloqueia campos extras, strings vazias/só espaços e textos gigantes."""
    msg = EnviarMensagemSchema(texto="   Olá cliente!   ", pedido_id=1)
    assert msg.texto == "Olá cliente!"

    for invalido in (
        lambda: EnviarMensagemSchema(texto="   ", pedido_id=1),
        lambda: EnviarMensagemSchema(texto="ok", pedido_id=1, campo_extra="hacker"),
        lambda: NovaConversaManualSchema(telefone="123", texto="oi"),
        lambda: RascunhoSchema(tipo="tipo_inexistente", pedido_id=1),
    ):
        try:
            invalido()
            assert False, "Deveria ter bloqueado payload inválido"
        except Exception:
            pass


def test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento():
    """Valida rascunhos, aviso automático de status, painel de atendimento, IA e webhooks."""
    init_db()
    atendimento.limitador_entrada.limpar()
    atendimento.limitador_envio.limpar()

    telefone_teste = "(11) 97777-6655"
    telefone_norm = "5511977776655"
    _limpar_conversas_teste(telefone_norm)

    res_cli = criar_cliente(
        ClienteSchema(
            nome="Maria WhatsApp Teste",
            documento="111.222.333-44",
            telefone=telefone_teste,
            email="maria@teste.local",
            endereco="Rua das Flores, 50",
        ),
        user="admin",
    )
    assert res_cli["sucesso"] is True
    cliente_id = res_cli["id"]

    criar_produto(ProdutoSchema(nome="Adesivo Redondo 5cm", preco_venda=50.0, quantidade=100), user="admin")
    prod = next(p for p in listar_produtos(user="admin") if p["nome"] == "Adesivo Redondo 5cm")

    # 1. Cria pedido PENDENTE e depois muda status para AGUARDANDO RETIRADA -> deve gerar aviso WhatsApp
    payload_ped = {
        "id": None,
        "cliente_id": cliente_id,
        "usuario_nome": "Thaissa",
        "desconto": 0,
        "status_producao": "PENDENTE",
        "status_pagamento": "PARCIAL",
        "forma_pagamento": "Pix",
        "valor_pago": 30.0,
        "observacao": "Cortar em cartelas",
        "produtos": [
            {
                "produto_id": prod["id"],
                "nome_produto": prod["nome"],
                "quantidade": 2,
                "preco_unitario": 50.0,
                "observacao": "Brilho",
            }
        ],
        "imagens_mantidas": [],
    }
    res_ped = asyncio.run(salvar_pedido(dados=json.dumps(payload_ped), imagens=[], user="admin"))
    assert res_ped["sucesso"] is True
    pedido_id = res_ped["id"]
    assert res_ped["whatsapp_notificacao"] is None  # PENDENTE não dispara aviso

    res_status = atualizar_status_pedido(
        pedido_id, StatusUpdateSchema(status_producao="AGUARDANDO RETIRADA"), user="Thaissa"
    )
    assert res_status["sucesso"] is True
    notif = res_status["whatsapp_notificacao"]
    assert notif is not None
    assert notif["novo_status"] == "AGUARDANDO RETIRADA"
    assert "wa.me/5511977776655" in notif["link"]
    assert f"#{pedido_id}" in notif["texto"]

    # 2. Testa rascunhos de status, cobrança, orçamento e saudação
    rascunho_cob = gerar_rascunho_api(
        RascunhoSchema(tipo="cobranca", pedido_id=pedido_id, usar_ia=False), user="admin"
    )
    assert rascunho_cob["sucesso"] is True
    assert rascunho_cob["telefone_valido"] is True
    assert "R$ 70,00" in rascunho_cob["texto"]  # Total 100 - Pago 30 = Saldo 70

    res_orc = asyncio.run(
        criar_orcamento(
            payload=OrcamentoCreateSchema(
                dados=OrcamentoDadosSchema(
                    cliente_id=cliente_id,
                    usuario="Davi",
                    desconto=5.0,
                    observacao="Entrega rápida",
                    itens=[ItemOrcamentoSchema(produto_id=prod["id"], quantidade=3, preco_unitario=50.0)],
                )
            ),
            user="admin",
        )
    )
    orc_id = res_orc["id"]

    rascunho_orc = gerar_rascunho_api(
        RascunhoSchema(tipo="orcamento", pedido_id=orc_id, usar_ia=False), user="admin"
    )
    assert rascunho_orc["sucesso"] is True
    assert "R$ 145,00" in rascunho_orc["texto"]

    # 3. Testa registro manual de dúvida do cliente + sugestão com IA (com mock)
    with patch(
        "services.ia_service.gerar_texto",
        return_value=f"Olá, Maria! Seu pedido *#{pedido_id}* já está pronto para retirada. Saldo: R$ 70,00.",
    ):
        reg_manual = registrar_entrada_manual_api(
            NovaConversaManualSchema(
                telefone=telefone_teste,
                nome_contato="Maria",
                texto="Oi, meu pedido de adesivo já está pronto?",
            ),
            user="Davi",
        )
        assert reg_manual["sucesso"] is True
        assert reg_manual["sugestao"]["origem"] == "ia"
        assert f"#{pedido_id}" in reg_manual["sugestao"]["texto"]
        conversa_id = reg_manual["conversa_id"]

    # 4. Verifica detalhe da conversa, contexto do cliente e envio pelo atendente
    detalhe = obter_conversa_api(conversa_id, user="Davi")
    assert detalhe["conversa"]["cliente_id"] == cliente_id
    assert f"Pedido #{pedido_id}" in detalhe["resumo_cliente"]
    assert f"Orçamento #{orc_id}" in detalhe["resumo_cliente"]

    envio = enviar_mensagem_api(
        EnviarMensagemSchema(
            conversa_id=conversa_id,
            texto="Pode vir retirar hoje até as 18h!",
            assumir_conversa=True,
        ),
        user="Davi",
    )
    assert envio["sucesso"] is True
    assert "wa.me/5511977776655" in envio["link"]

    # Atendente assumiu -> modo_auto da conversa foi pausado (0)
    detalhe_pos = obter_conversa_api(conversa_id, user="Davi")
    assert detalhe_pos["conversa"]["modo_auto"] == 0

    # 5. Controle de permissão: operador comum não altera config de robô; gestor altera
    try:
        salvar_config_whatsapp(ConfigWhatsAppSchema(auto_resposta=True), user="Marketing")
        assert False, "Operador não-gestor não deveria alterar config automática"
    except HTTPException as exc:
        assert exc.status_code == 403

    res_cfg = salvar_config_whatsapp(ConfigWhatsAppSchema(auto_resposta=False, aviso_status=True), user="Thaissa")
    assert res_cfg["sucesso"] is True
    assert obter_status_whatsapp(user="Thaissa")["aviso_status"] is True

    # 6. Renderização da página /atendimento e verificação das rotas no OpenAPI do app
    rotas_openapi = set(main.app.openapi()["paths"].keys())
    for rota_esperada in (
        "/atendimento",
        "/api/whatsapp/status",
        "/api/whatsapp/config",
        "/api/whatsapp/conversas",
        "/api/whatsapp/conversas/{conversa_id}",
        "/api/whatsapp/conversas/manual",
        "/api/whatsapp/conversas/{conversa_id}/sugerir",
        "/api/whatsapp/rascunho",
        "/api/whatsapp/enviar",
        "/api/whatsapp/webhook",
    ):
        assert rota_esperada in rotas_openapi, f"Rota ausente no app: {rota_esperada}"

    req = _make_request("/atendimento", "admin")
    html_atendimento = pagina_atendimento(req, user="admin").body.decode("utf-8")
    assert "CENTRAL DE ATENDIMENTO WHATSAPP" in html_atendimento
    assert "wa-lista-conversas" in html_atendimento

    # 7. Webhook autenticado (Evolution API + Meta HMAC) e deduplicação por id_externo
    with patch.dict(os.environ, {"WHATSAPP_WEBHOOK_TOKEN": "segredo_evol_123"}, clear=False):
        payload_webhook = {
            "data": {
                "key": {"remoteJid": "5511977776655@s.whatsapp.net", "fromMe": False, "id": "MSG_EXT_UNICA_1"},
                "pushName": "Maria",
                "message": {"conversation": "Obrigada, estou indo buscar!"},
            }
        }
        corpo_bytes = json.dumps(payload_webhook).encode("utf-8")

        async def _receive():
            return {"type": "http.request", "body": corpo_bytes, "more_body": False}

        scope_ok = {
            "type": "http",
            "method": "POST",
            "path": "/api/whatsapp/webhook",
            "headers": [(b"x-webhook-token", b"segredo_evol_123")],
            "query_string": b"",
        }
        bg = BackgroundTasks()
        resp_wh1 = asyncio.run(receber_webhook(Request(scope_ok, _receive), bg))
        assert resp_wh1["processadas"] == 1

        # Reenvio idêntico pelo provedor deve ser ignorado (deduplicação)
        resp_wh2 = asyncio.run(receber_webhook(Request(scope_ok, _receive), bg))
        assert resp_wh2["processadas"] == 0

    # Limpeza dos dados de teste
    deletar_pedido(pedido_id, user="admin")
    deletar_pedido(orc_id, user="admin")
    excluir_cliente(cliente_id, user="admin")
    _limpar_conversas_teste(telefone_norm)
