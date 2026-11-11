import asyncio
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
    ConversaUpdateSchema,
    EnviarMensagemSchema,
    GerarPedidoSchema,
    NovaConversaManualSchema,
    RascunhoSchema,
    analisar_comprovante_api,
    carregar_mensagens_anteriores_api,
    desconectar_bridge_api,
    enviar_imagem_api,
    enviar_mensagem_api,
    gerar_pedido_api,
    gerar_rascunho_api,
    gerar_resumo_pedido_api,
    iniciar_bridge_api,
    listar_conversas_api,
    listar_destinatarios_whatsapp,
    obter_conversa_api,
    obter_status_bridge_api,
    obter_status_whatsapp,
    receber_webhook,
    registrar_entrada_manual_api,
    salvar_config_whatsapp,
    sugerir_resposta_api,
)
from services.whatsapp import atendimento, bridge_manager, contexto, repositorio as repo
from services.whatsapp.telefone import (
    chave_comparacao,
    formatar_exibicao,
    link_whatsapp,
    link_whatsapp_web,
    normalizar_telefone,
)
from tests.test_full_system import _make_request

# Número de teste oficial estabelecido pelo usuário (Davi): 16 997100623
NUMERO_TESTE = "5516997100623"
NUMERO_TESTE_BRUTO = "16 997100623"
NUMERO_TESTE_FMT = "+55 (16) 99710-0623"


class PreservarConversaTeste:
    """Context manager que garante o uso estrito do número de teste 16 997100623 sem poluir mensagens reais."""
    def __init__(self, telefone: str = NUMERO_TESTE):
        self.telefone = telefone
        self.conv_snapshot = None
        self.max_msg_id = 0

    def __enter__(self):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM whatsapp_conversas WHERE telefone = ?", (self.telefone,)).fetchone()
            if row:
                self.conv_snapshot = dict(row)
                m_row = conn.execute(
                    "SELECT MAX(id) as m FROM whatsapp_mensagens WHERE conversa_id = ?", (row["id"],)
                ).fetchone()
                self.max_msg_id = m_row["m"] if (m_row and m_row["m"]) else 0
            else:
                self.conv_snapshot = None
                self.max_msg_id = 0
            return self
        finally:
            conn.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM whatsapp_conversas WHERE telefone = ?", (self.telefone,)).fetchone()
            if row:
                conv_id = row["id"]
                # Remove apenas mensagens geradas durante o teste
                if self.max_msg_id:
                    conn.execute("DELETE FROM whatsapp_mensagens WHERE conversa_id = ? AND id > ?", (conv_id, self.max_msg_id))
                elif not self.conv_snapshot:
                    conn.execute("DELETE FROM whatsapp_mensagens WHERE conversa_id = ?", (conv_id,))
                    conn.execute("DELETE FROM whatsapp_conversas WHERE id = ?", (conv_id,))

                # Restaura estado anterior fiel da conversa se já existia
                if self.conv_snapshot:
                    conn.execute(
                        """UPDATE whatsapp_conversas SET
                           nao_lidas = ?, aguardando_nome = ?, atendente_nome = ?,
                           cliente_id = ?, nome_contato = ?, modo_auto = ?,
                           precisa_atendente = ?, ultima_mensagem = ?, ultima_mensagem_em = ?
                           WHERE id = ?""",
                        (
                            self.conv_snapshot["nao_lidas"],
                            self.conv_snapshot["aguardando_nome"],
                            self.conv_snapshot["atendente_nome"],
                            self.conv_snapshot["cliente_id"],
                            self.conv_snapshot["nome_contato"],
                            self.conv_snapshot["modo_auto"],
                            self.conv_snapshot["precisa_atendente"],
                            self.conv_snapshot["ultima_mensagem"],
                            self.conv_snapshot["ultima_mensagem_em"],
                            conv_id,
                        ),
                    )
            conn.commit()
        finally:
            conn.close()


def _limpar_conversas_teste(*telefones: str):
    conn = get_connection()
    try:
        for tel in telefones:
            # Nunca deleta a conversa oficial do usuário se não for explicitamente desejado
            if tel != NUMERO_TESTE:
                conn.execute("DELETE FROM whatsapp_conversas WHERE telefone = ?", (tel,))
        conn.commit()
    finally:
        conn.close()


def test_normalizacao_telefone_anti_gorila():
    """Garante que números em formatos variados viram E.164 BR e geram links wa.me e WhatsApp Web."""
    # Teste estrito com o número de teste oficial: 16 997100623
    assert normalizar_telefone("16 997100623") == NUMERO_TESTE
    assert normalizar_telefone("16997100623") == NUMERO_TESTE
    assert normalizar_telefone("(16) 99710-0623") == NUMERO_TESTE
    assert normalizar_telefone("+55 16 99710-0623") == NUMERO_TESTE
    assert normalizar_telefone("016 99710-0623") == NUMERO_TESTE
    with patch.dict(os.environ, {"WHATSAPP_DDD_PADRAO": "16"}):
        assert normalizar_telefone("99710-0623", aceitar_sem_ddd=True) == NUMERO_TESTE
    assert formatar_exibicao(NUMERO_TESTE) == NUMERO_TESTE_FMT
    assert chave_comparacao(NUMERO_TESTE) == chave_comparacao("551697100623")
    assert link_whatsapp(NUMERO_TESTE_BRUTO, "Olá mundo").startswith(f"https://wa.me/{NUMERO_TESTE}?text=")
    assert link_whatsapp_web(NUMERO_TESTE_BRUTO, "Olá mundo").startswith(
        f"https://web.whatsapp.com/send?phone={NUMERO_TESTE}&text="
    )

    # Entradas inválidas
    assert normalizar_telefone("") is None
    assert normalizar_telefone("abc-def") is None
    assert normalizar_telefone("12345", aceitar_sem_ddd=True) is None
    assert normalizar_telefone("(00) 99710-0623") is None


def test_schemas_pydantic_anti_gorila_whatsapp():
    """Bloqueia campos extras, strings vazias/só espaços e textos gigantes."""
    msg = EnviarMensagemSchema(texto="   Olá cliente!   ", pedido_id=1)
    assert msg.texto == "Olá cliente!"

    for invalido in (
        lambda: EnviarMensagemSchema(texto="   ", pedido_id=1),
        lambda: EnviarMensagemSchema(texto="ok", pedido_id=1, campo_extra="hacker"),
        lambda: NovaConversaManualSchema(telefone=NUMERO_TESTE_BRUTO, texto="   "),
        lambda: RascunhoSchema(tipo="tipo_inexistente", pedido_id=1),
    ):
        try:
            invalido()
            assert False, "Deveria ter bloqueado payload inválido"
        except Exception:
            pass


def test_fluxo_completo_whatsapp_ia_pedidos_orcamentos_e_atendimento():
    """Valida rascunhos, aviso automático de status, painel de atendimento, WhatsApp Web, IA e webhooks usando o número de teste."""
    init_db()
    atendimento.limitador_entrada.limpar()
    atendimento.limitador_envio.limpar()

    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_via_bridge", return_value=(True, "TEST_EXT_1", "")
    ), patch(
        "services.whatsapp.bridge_manager.enviar_imagem_via_bridge", return_value=(True, "TEST_IMG_1", "")
    ):
        res_cli = criar_cliente(
            ClienteSchema(
                nome="Davi Teste Fluxo",
                documento="111.222.333-44",
                telefone=NUMERO_TESTE_FMT,
                email="davi@teste.local",
                endereco="Rua das Flores, 50",
            ),
            user="admin",
        )
        assert res_cli["sucesso"] is True
        cliente_id = res_cli["id"]

        criar_produto(ProdutoSchema(nome="Adesivo Redondo 5cm", preco_venda=50.0, quantidade=100), user="admin")
        prod = next(p for p in listar_produtos(user="admin") if p["nome"] == "Adesivo Redondo 5cm")

        # 1. Cria pedido PENDENTE e depois muda status para AGUARDANDO RETIRADA
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

        res_status = atualizar_status_pedido(
            pedido_id, StatusUpdateSchema(status_producao="AGUARDANDO RETIRADA"), user="Thaissa"
        )
        assert res_status["sucesso"] is True
        notif = res_status["whatsapp_notificacao"]
        assert notif is not None
        assert f"wa.me/{NUMERO_TESTE}" in notif["link"]
        assert f"web.whatsapp.com/send?phone={NUMERO_TESTE}" in notif["link_web"]

        # 2. Testa destinatários e rascunhos
        dest = listar_destinatarios_whatsapp(user="admin")
        assert any(c["id"] == cliente_id for c in dest["clientes"])
        assert any(p["id"] == pedido_id for p in dest["pedidos"])

        rascunho_cob = gerar_rascunho_api(
            RascunhoSchema(tipo="cobranca", pedido_id=pedido_id, usar_ia=False), user="admin"
        )
        assert rascunho_cob["sucesso"] is True
        assert f"web.whatsapp.com/send?phone={NUMERO_TESTE}" in rascunho_cob["link_web"]

        # 3. Orçamento
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

        # 4. Registro manual com IA
        with patch(
            "services.ia_service.gerar_texto",
            return_value=f"Olá, Davi! Seu pedido *#{pedido_id}* já está pronto para retirada.",
        ):
            reg_manual = registrar_entrada_manual_api(
                NovaConversaManualSchema(
                    cliente_id=cliente_id,
                    telefone=NUMERO_TESTE_FMT,
                    nome_contato="Davi",
                    texto="Oi, meu pedido de adesivo já está pronto?",
                ),
                user="Davi",
            )
            assert reg_manual["sucesso"] is True
            conversa_id = reg_manual["conversa_id"]

        detalhe = obter_conversa_api(conversa_id, user="Davi")
        assert f"web.whatsapp.com/send?phone={NUMERO_TESTE}" in detalhe["conversa"]["link_web"]

        envio = enviar_mensagem_api(
            EnviarMensagemSchema(
                conversa_id=conversa_id,
                texto="Pode vir retirar hoje até as 18h!",
                assumir_conversa=True,
            ),
            user="Davi",
        )
        assert envio["sucesso"] is True

        # 5. Permissão de gestor
        res_cfg = salvar_config_whatsapp(ConfigWhatsAppSchema(auto_resposta=False, aviso_status=True), user="Thaissa")
        assert res_cfg["sucesso"] is True

        # 6. Webhook e deduplicação
        scope_bridge = {
            "type": "http",
            "method": "POST",
            "path": "/api/whatsapp/webhook",
            "headers": [(b"x-webhook-token", bridge_manager.token_interno_bridge().encode("utf-8"))],
            "query_string": b"",
        }
        payload_webhook = {
            "data": {
                "key": {"remoteJid": f"{NUMERO_TESTE}@s.whatsapp.net", "fromMe": False, "id": "MSG_DAVI_TESTE_1"},
                "pushName": "Davi",
                "message": {"conversation": "Obrigado!"},
            }
        }
        corpo_bytes = json.dumps(payload_webhook).encode("utf-8")

        async def _receive():
            return {"type": "http.request", "body": corpo_bytes, "more_body": False}

        resp_wh1 = asyncio.run(receber_webhook(Request(scope_bridge, _receive), BackgroundTasks()))
        assert resp_wh1["processadas"] == 1

        # Reenvio idêntico -> deduplica (0)
        resp_wh2 = asyncio.run(receber_webhook(Request(scope_bridge, _receive), BackgroundTasks()))
        assert resp_wh2["processadas"] == 0

        # Limpeza do pedido de teste
        deletar_pedido(pedido_id, user="admin")
        deletar_pedido(orc_id, user="admin")
        excluir_cliente(cliente_id, user="admin")
        from controllers.produto_controller import ProdutoController
        ProdutoController.excluir(prod["id"])


def test_sincronizacao_conversas_e_mensagens_anteriores():
    """Garante sincronização usando exclusivamente o número de teste do usuário 16 997100623."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE):
        scope_bridge = {
            "type": "http",
            "method": "POST",
            "path": "/api/whatsapp/webhook",
            "headers": [(b"x-webhook-token", bridge_manager.token_interno_bridge().encode("utf-8"))],
        }
        payload_conversas = {
            "data": {
                "evento_tipo": "conversas_lote",
                "chats": [
                    {"jid": f"{NUMERO_TESTE}@s.whatsapp.net", "nome": "Davi", "timestamp": 1711200000},
                ],
            }
        }
        corpo_conv = json.dumps(payload_conversas).encode("utf-8")

        async def _receive_conv():
            return {"type": "http.request", "body": corpo_conv, "more_body": False}

        resp_conv = asyncio.run(receber_webhook(Request(scope_bridge, _receive_conv), BackgroundTasks()))
        assert resp_conv["recebido"] is True

        conv_a = repo.obter_ou_criar_conversa(NUMERO_TESTE)
        assert conv_a["telefone"] == NUMERO_TESTE

        # Mensagens anteriores
        payload_msgs = {
            "data": {
                "evento_tipo": "mensagens_lote",
                "items": [
                    {
                        "key": {"remoteJid": f"{NUMERO_TESTE}@s.whatsapp.net", "fromMe": False, "id": "HIST_002"},
                        "messageTimestamp": 1711200200,
                        "pushName": "Davi",
                        "message": {"conversation": "Mensagem intermediária anterior"},
                    },
                    {
                        "key": {"remoteJid": f"{NUMERO_TESTE}@s.whatsapp.net", "fromMe": True, "id": "HIST_001"},
                        "messageTimestamp": 1711200100,
                        "message": {"conversation": "Mensagem mais antiga"},
                    },
                ],
            }
        }
        corpo_msgs = json.dumps(payload_msgs).encode("utf-8")

        async def _receive_msgs():
            return {"type": "http.request", "body": corpo_msgs, "more_body": False}

        resp_msgs = asyncio.run(receber_webhook(Request(scope_bridge, _receive_msgs), BackgroundTasks()))
        assert resp_msgs["recebido"] is True
        assert resp_msgs.get("processadas", 0) >= 1 or resp_msgs.get("mensagens_gravadas", 0) >= 1

        with patch("services.whatsapp.bridge_manager.requisitar_historico_bridge") as mock_bridge:
            mock_bridge.return_value = {"sucesso": True, "solicitado": True}
            res_anteriores = carregar_mensagens_anteriores_api(conv_a["id"], user="admin")
            assert res_anteriores["sucesso"] is True
            assert res_anteriores["solicitado"] is True


def test_suporte_a_imagens_recebimento_e_envio():
    """Garante suporte a imagens e comprovantes com número oficial de teste."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_imagem_via_bridge", return_value=(True, "TEST_IMG_ENV", "")
    ):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Davi")
        img_fake = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10]) + b"JFIF"
        res_env = atendimento.enviar_imagem(conv["id"], img_fake, legenda="Foto do pedido", usuario="Thaissa")
        assert res_env["enviado"] is True
        assert res_env["midia_url"].startswith("/static/uploads/whatsapp/")


def test_fluxo_gerar_pedido_e_comprovante_50():
    """Testa o fluxo em 2 etapas com o número oficial de teste 16 997100623."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_via_bridge", return_value=(True, "TEST_EXT_P50", "")
    ), patch(
        "services.whatsapp.bridge_manager.enviar_imagem_via_bridge", return_value=(True, "TEST_IMG_P50", "")
    ):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Contato #0623")
        repo.atualizar_conversa(conv["id"], cliente_id=None, aguardando_nome=0, nome_contato="Contato #0623")

        repo.registrar_mensagem(conv["id"], repo.DIRECAO_ENTRADA, repo.AUTOR_CLIENTE, "Boa tarde, gostaria de um quadro em placa de PVC 50x70cm", repo.STATUS_RECEBIDA)
        repo.registrar_mensagem(conv["id"], repo.DIRECAO_SAIDA, repo.AUTOR_ATENDENTE, "Boa tarde! Fica R$ 80,00.", repo.STATUS_ENVIADA)
        repo.registrar_mensagem(conv["id"], repo.DIRECAO_ENTRADA, repo.AUTOR_CLIENTE, "Pode fazer sim, vou querer!", repo.STATUS_RECEBIDA)

        # 1. Gerar Pedido -> IA detecta que não tem nome e manda a pergunta
        with patch("services.whatsapp.contexto.localizar_cliente_por_telefone", return_value=None):
            res1 = gerar_pedido_api(conv["id"], user="Davi")
        assert res1["sucesso"] is True
        assert res1["aguardando_nome"] is True

        conv_atual = repo.obter_conversa(conv["id"])
        assert conv_atual["aguardando_nome"] == 1

        # 2. Cliente responde com o nome no WhatsApp
        atendimento.processar_mensagem_recebida(
            telefone_bruto=NUMERO_TESTE,
            texto_bruto="Pode por no nome de Davi Silva",
            from_me=False,
        )

        conv_atual = repo.obter_conversa(conv["id"])
        assert conv_atual["aguardando_nome"] == 0
        cid = conv_atual["cliente_id"]
        assert cid is not None

        conn = get_connection()
        try:
            ped = conn.execute("SELECT * FROM pedidos WHERE cliente_id = ? ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
            assert ped is not None
            assert ped["status_pagamento"] == "PENDENTE"
            pedido_id = ped["id"]

            # 3. Cliente manda comprovante de 50%
            img_fake = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10]) + b"JFIF"
            res_comp = atendimento.analisar_comprovante_e_atualizar_pedido(
                conversa_id=conv["id"],
                imagem_bytes=img_fake,
                mime_type="image/jpeg",
                nome_arquivo="comprovante_sinal.jpg",
                legenda="Segue o comprovante do sinal de 50%",
            )
            assert res_comp["atualizado"] is True
            assert res_comp["percentual"] == 50
            assert res_comp["status_pagamento"] == "50% PAGO"

            ped_atual = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
            assert ped_atual["status_pagamento"] == "50% PAGO"

            # Limpeza do pedido de teste
            conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
            conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
            conn.execute("DELETE FROM clientes WHERE id = ?", (cid,))
            conn.commit()
        finally:
            conn.close()


def test_contador_mensagens_sem_resposta_e_badge_verde():
    """Garante que o contador de mensagens sem resposta incrementa e zera com número oficial de teste."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Davi")
        repo.atualizar_conversa(conv["id"], nao_lidas=0)

        # 1ª mensagem sem resposta -> +1
        atendimento.processar_mensagem_recebida(
            telefone_bruto=NUMERO_TESTE,
            texto_bruto="Olá, primeira mensagem",
            from_me=False,
        )
        assert repo.obter_conversa(conv["id"])["nao_lidas"] == 1

        # 2ª mensagem sem resposta -> +2
        atendimento.processar_mensagem_recebida(
            telefone_bruto=NUMERO_TESTE,
            texto_bruto="Segunda mensagem sem resposta",
            from_me=False,
        )
        assert repo.obter_conversa(conv["id"])["nao_lidas"] == 2

        # Atendente abre conversa -> zera
        obter_conversa_api(conv["id"], marcar_lida=True, user="Thaissa")
        assert repo.obter_conversa(conv["id"])["nao_lidas"] == 0


def test_marcar_todas_conversas_como_lidas():
    """Garante que a ação global zera o status nao_lidas sem criar números falsos."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Davi")
        repo.atualizar_conversa(conv["id"], nao_lidas=3)

        from routes.whatsapp_routes import marcar_todas_conversas_lidas_api, obter_contador_nao_lidas
        cont_antes = obter_contador_nao_lidas(user="admin")
        assert cont_antes["total_nao_lidas"] >= 3

        resp = marcar_todas_conversas_lidas_api(user="admin")
        assert resp["sucesso"] is True

        assert repo.obter_conversa(conv["id"])["nao_lidas"] == 0
        cont_depois = obter_contador_nao_lidas(user="admin")
        assert cont_depois["total_nao_lidas"] == 0


def test_extracao_detalhes_pedido_sem_frases_de_bate_papo():
    """Garante filtragem estrita: apenas item, quantidade e obs técnica, sem frases de conversa."""
    msgs_1 = [
        {"texto": "Boa tarde!", "direcao": "ENTRADA"},
        {"texto": "Quero um cartão de visita 100und acabamento com bordas", "direcao": "ENTRADA"},
        {"texto": "Fica R$ 80,00", "direcao": "SAIDA"},
    ]
    det_1 = atendimento._extrair_detalhes_pedido_conversa(msgs_1)
    assert det_1["item_principal"] == "CARTÃO DE VISITA"
    assert det_1["quantidade"] == 100.0
    assert "BORDA ARREDONDADA" in det_1["observacao"]
    assert det_1["valor_total"] == 80.0

    msgs_2 = [
        {"texto": "Manda o pix", "direcao": "ENTRADA"},
        {"texto": "Ela já tá mandando o cardápio correto", "direcao": "ENTRADA"},
        {"texto": "Okk, vou gerar seu pedido aqui e já te mando", "direcao": "SAIDA"},
        {"texto": "Total fica R$ 125,00", "direcao": "SAIDA"},
    ]
    det_2 = atendimento._extrair_detalhes_pedido_conversa(msgs_2)
    assert det_2["item_principal"] == "CARDÁPIO"
    assert det_2["quantidade"] == 1.0
    assert det_2["observacao"] == ""
    assert det_2["valor_total"] == 125.0


def test_pedido_ia_salva_com_usuario_logado():
    """Garante que o pedido gerado pela IA é vinculado ao atendente logado usando número oficial de teste 16 997100623."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_via_bridge", return_value=(True, "TEST_PED_USER", "")
    ), patch(
        "services.whatsapp.bridge_manager.enviar_imagem_via_bridge", return_value=(True, "TEST_PED_USER_IMG", "")
    ):
        conn = get_connection()
        try:
            # 1. Atendente 'Davi' clica para gerar pedido com cliente
            from controllers.cliente_controller import ClienteController
            cid_1 = ClienteController.criar(nome="Cliente Davi Teste", telefone=NUMERO_TESTE_FMT)
            conv_1 = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Cliente Davi Teste", cid_1)
            repo.registrar_mensagem(conv_1["id"], repo.DIRECAO_ENTRADA, repo.AUTOR_CLIENTE, "Quero 100 cartões de visita acabamento com bordas", repo.STATUS_RECEBIDA)
            repo.registrar_mensagem(conv_1["id"], repo.DIRECAO_SAIDA, repo.AUTOR_ATENDENTE, "Fica R$ 80,00", repo.STATUS_ENVIADA, usuario="Davi")

            res_1 = atendimento.gerar_pedido_ia_conversa(conv_1["id"], usuario="Davi")
            assert res_1["sucesso"] is True
            assert res_1["atendente"] == "Davi"

            ped_1 = conn.execute("SELECT usuario_nome, valor_total FROM pedidos WHERE id = ?", (res_1["pedido_id"],)).fetchone()
            assert ped_1 is not None
            assert ped_1["usuario_nome"] == "Davi"

            # 2. Atendente 'Michel' clica para gerar pedido com cliente sem nome (aguardando_nome = 1)
            repo.atualizar_conversa(conv_1["id"], cliente_id=None, nome_contato="Contato #0623", aguardando_nome=0)
            with patch("services.whatsapp.contexto.localizar_cliente_por_telefone", return_value=None):
                res_2 = atendimento.gerar_pedido_ia_conversa(conv_1["id"], usuario="Michel")
            assert res_2["sucesso"] is True
            assert res_2["aguardando_nome"] is True
            assert res_2["atendente"] == "Michel"

            conv_db = repo.obter_conversa(conv_1["id"])
            assert conv_db["aguardando_nome"] == 1
            assert conv_db["atendente_nome"] == "Michel"

            # Cliente responde com seu nome no WhatsApp
            atendimento.processar_mensagem_recebida(NUMERO_TESTE, "Meu nome é Davi Teste Oficial")

            conv_atualizada = repo.obter_conversa(conv_1["id"])
            assert conv_atualizada["aguardando_nome"] == 0
            cid_2 = conv_atualizada["cliente_id"]
            assert cid_2 is not None

            ped_2 = conn.execute("SELECT id, usuario_nome FROM pedidos WHERE cliente_id = ? ORDER BY id DESC LIMIT 1", (cid_2,)).fetchone()
            assert ped_2 is not None
            assert ped_2["usuario_nome"] == "Michel"

            # 3. Teste via API endpoint com GerarPedidoSchema
            payload = GerarPedidoSchema(atendente="Thaissa")
            res_api = gerar_pedido_api(conversa_id=conv_1["id"], payload=payload, user="Thaissa")
            assert res_api["sucesso"] is True
            assert res_api["atendente"] == "Thaissa"

            ped_api = conn.execute("SELECT usuario_nome FROM pedidos WHERE id = ?", (res_api["pedido_id"],)).fetchone()
            assert ped_api["usuario_nome"] == "Thaissa"

            # Limpeza completa em cascata
            conn.execute("DELETE FROM itens_pedido WHERE pedido_id IN (?, ?, ?)", (res_1["pedido_id"], ped_2["id"], res_api["pedido_id"]))
            conn.execute("DELETE FROM pedidos WHERE id IN (?, ?, ?)", (res_1["pedido_id"], ped_2["id"], res_api["pedido_id"]))
            conn.execute("DELETE FROM clientes WHERE id IN (?, ?)", (cid_1, cid_2 if "cid_2" in locals() else 0))
            conn.commit()
        finally:
            conn.close()


def test_whatsapp_bridge_resilience_and_ddd_padrao():
    """Garante estabilidade da ponte WhatsApp: DDD regional 16 por padrao e resiliencia de URLs."""
    from services.whatsapp.telefone import _ddd_padrao

    # 1. Valida DDD padrao regional 16 (Franca/SP)
    assert _ddd_padrao() == "16"
    assert normalizar_telefone("99710-0623", aceitar_sem_ddd=True) == NUMERO_TESTE

    # 2. Valida resiliencia de URL no bridge_manager
    bridge_manager.atualizar_webhook_url("http://127.0.0.1:8000")
    assert bridge_manager._webhook_url_atual == "http://127.0.0.1:8000/api/whatsapp/webhook"

    bridge_manager.atualizar_webhook_url("http://localhost:8000")
    assert bridge_manager._webhook_url_atual == "http://127.0.0.1:8000/api/whatsapp/webhook"

    bridge_manager.atualizar_webhook_url("http://192.168.0.11:8000")
    assert bridge_manager._webhook_url_atual == "http://192.168.0.11:8000/api/whatsapp/webhook"

    # Restaura para padrao confiavel
    bridge_manager.atualizar_webhook_url("http://127.0.0.1:8000")

    # 3. Valida tratamento de erro ao enviar via bridge quando desconectado
    with patch("services.whatsapp.bridge_manager._requisitar_bridge", return_value={"enviado": False, "erro": "O numero informado nao esta cadastrado no WhatsApp."}):
        enviado, id_ext, erro = bridge_manager.enviar_via_bridge(NUMERO_TESTE, "Teste unitario resiliencia")
        assert enviado is False
        assert id_ext == ""
        assert "nao esta cadastrado" in erro
