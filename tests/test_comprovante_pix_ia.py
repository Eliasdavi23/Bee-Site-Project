import json
from unittest.mock import patch
from config.database import init_db, get_connection
import services.whatsapp.atendimento as atendimento
from services.whatsapp.atendimento import validar_valor_comprovante_pix
import services.whatsapp.repositorio as repo
from tests.test_whatsapp import PreservarConversaTeste, NUMERO_TESTE


def test_validacao_estrita_valor_comprovante_pix():
    """Testa a validação matemática estrita de valores em pedidos novos e parciais."""
    pedido_novo = {
        "id": 101,
        "valor_total": 100.0,
        "valor_pago": 0.0,
        "status_pagamento": "PENDENTE",
    }

    # 1. Sinal de 50% exato (R$ 50,00) -> APROVADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 50.0)
    assert aprovado is True
    assert perc == 50
    assert "50%" in mot

    # 2. Tolerância bancária de centavos (R$ 49,98 ou R$ 50,03) -> APROVADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 50.03)
    assert aprovado is True
    assert perc == 50

    # 3. Pagamento total de 100% exato (R$ 100,00) -> APROVADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 100.0)
    assert aprovado is True
    assert perc == 100

    # 4. REGRA ESTRITA: Valor divergente (R$ 35,00) -> REJEITADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 35.0)
    assert aprovado is False
    assert perc == 0
    assert "divergente" in mot.lower()
    assert "R$ 35,00" in mot
    assert "R$ 50,00" in mot
    assert "R$ 100,00" in mot

    # 5. REGRA ESTRITA: Valor divergente maior mas não integral (R$ 80,00) -> REJEITADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 80.0)
    assert aprovado is False
    assert "divergente" in mot.lower()

    # 6. Valor zero ou negativo -> REJEITADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_novo, 0.0)
    assert aprovado is False

    # 7. Pedido com 50% já pago aguardando quitação do saldo restante
    pedido_parcial = {
        "id": 102,
        "valor_total": 200.0,
        "valor_pago": 100.0,
        "status_pagamento": "50% PAGO",
    }
    # Quitação exata de R$ 100,00 restante -> APROVADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_parcial, 100.0)
    assert aprovado is True
    assert perc == 100

    # Divergência no saldo restante (R$ 50,00 quando deve R$ 100,00) -> REJEITADO
    aprovado, perc, mot = validar_valor_comprovante_pix(pedido_parcial, 50.0)
    assert aprovado is False
    assert "divergente" in mot.lower()


def test_ia_visao_rejeita_comprovante_com_valor_divergente():
    """Valida que a IA (Gemini multimodal) rejeita o comprovante se o valor extraído divergir do pedido."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_via_bridge", return_value=(True, "TEST_EXT_DIV", "")
    ):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Cliente Teste Divergencia")
        repo.atualizar_conversa(conv["id"], cliente_id=None, aguardando_nome=0)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO clientes (nome, telefone) VALUES (?, ?)",
                ("Cliente Divergencia", NUMERO_TESTE)
            )
            cid = cur.lastrowid
            conn.commit()

            repo.atualizar_conversa(conv["id"], cliente_id=cid)

            # Pedido de R$ 150,00 (sinal 50% = R$ 75,00)
            cur.execute(
                "INSERT INTO pedidos (cliente_id, valor_total, valor_pago, status_pagamento, status_producao) "
                "VALUES (?, 150.0, 0.0, 'PENDENTE', 'PENDENTE')",
                (cid,)
            )
            pid = cur.lastrowid
            conn.commit()

            repo.registrar_mensagem(
                conv["id"],
                repo.DIRECAO_SAIDA,
                repo.AUTOR_ATENDENTE,
                "Chave Pix: teste@bee.com. Valor R$ 150,00 (50% de entrada: R$ 75,00).",
                repo.STATUS_ENVIADA
            )

            # Simula Gemini lendo comprovante com valor de R$ 30,00 (divergente de R$ 75,00 e R$ 150,00)
            resposta_ia_divergente = json.dumps({
                "eh_comprovante": True,
                "valor": 30.0,
                "tipo_pagamento": "PIX",
                "autenticacao_id": "AUTH9999",
                "resumo": "Pix de R$ 30,00"
            })

            img_bytes = b"FAKE_PIX_IMAGE_BYTES"
            with patch("services.ia_service.ia_configurada", return_value=True), patch(
                "services.ia_service.analisar_imagem", return_value=resposta_ia_divergente
            ):
                res = atendimento.analisar_comprovante_e_atualizar_pedido(
                    conversa_id=conv["id"],
                    imagem_bytes=img_bytes,
                    mime_type="image/jpeg",
                    nome_arquivo="comprovante_divergente.jpg",
                    legenda="Enviei o comprovante",
                )

            # Verifica rejeição estrita
            assert res["atualizado"] is False
            assert res["divergencia"] is True
            assert "divergente" in res["motivo"].lower()
            assert res["valor_detectado"] == 30.0

            # O pedido no banco DEVE permanecer inalterado como PENDENTE e valor_pago = 0.0
            ped_db = conn.execute("SELECT status_pagamento, valor_pago FROM pedidos WHERE id = ?", (pid,)).fetchone()
            assert ped_db["status_pagamento"] == "PENDENTE"
            assert ped_db["valor_pago"] == 0.0

            # Verifica se foi registrado aviso interno de divergência
            mensagens = repo.listar_mensagens(conv["id"], limite=5)
            textos = [m["texto"] for m in mensagens]
            assert any("REJEITADO por divergência de valor" in t for t in textos)

            # Limpeza
            conn.execute("DELETE FROM pedidos WHERE id = ?", (pid,))
            conn.execute("DELETE FROM clientes WHERE id = ?", (cid,))
            conn.commit()
        finally:
            conn.close()


def test_ia_visao_aprova_comprovante_com_valor_exato():
    """Valida que a IA (Gemini multimodal) aprova o comprovante quando o valor bate exatamente com o sinal de 50%."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE), patch(
        "services.whatsapp.bridge_manager.enviar_via_bridge", return_value=(True, "TEST_EXT_OK", "")
    ):
        conv = repo.obter_ou_criar_conversa(NUMERO_TESTE, "Cliente Teste Aprovado")
        repo.atualizar_conversa(conv["id"], cliente_id=None, aguardando_nome=0)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO clientes (nome, telefone) VALUES (?, ?)",
                ("Cliente Aprovado", NUMERO_TESTE)
            )
            cid = cur.lastrowid
            conn.commit()

            repo.atualizar_conversa(conv["id"], cliente_id=cid)

            # Pedido de R$ 120,00 (sinal 50% = R$ 60,00)
            cur.execute(
                "INSERT INTO pedidos (cliente_id, valor_total, valor_pago, status_pagamento, status_producao) "
                "VALUES (?, 120.0, 0.0, 'PENDENTE', 'PENDENTE')",
                (cid,)
            )
            pid = cur.lastrowid
            conn.commit()

            repo.registrar_mensagem(
                conv["id"],
                repo.DIRECAO_SAIDA,
                repo.AUTOR_ATENDENTE,
                "Chave Pix: teste@bee.com. Total R$ 120,00.",
                repo.STATUS_ENVIADA
            )

            # Simula Gemini lendo comprovante com valor exato de R$ 60,00
            resposta_ia_exata = json.dumps({
                "eh_comprovante": True,
                "valor": 60.0,
                "tipo_pagamento": "PIX",
                "autenticacao_id": "AUTH6000",
                "resumo": "Pix de R$ 60,00 realizado via Inter"
            })

            img_bytes = b"FAKE_PIX_IMAGE_BYTES"
            with patch("services.ia_service.ia_configurada", return_value=True), patch(
                "services.ia_service.analisar_imagem", return_value=resposta_ia_exata
            ):
                res = atendimento.analisar_comprovante_e_atualizar_pedido(
                    conversa_id=conv["id"],
                    imagem_bytes=img_bytes,
                    mime_type="image/jpeg",
                    nome_arquivo="comprovante_60.jpg",
                    legenda="Enviei o sinal",
                )

            # Verifica aprovação
            assert res["atualizado"] is True
            assert res["divergencia"] is False
            assert res["percentual"] == 50
            assert res["valor_pago"] == 60.0

            # O pedido no banco DEVE estar atualizado para 50% PAGO e EM PRODUCAO
            ped_db = conn.execute("SELECT status_pagamento, status_producao, valor_pago FROM pedidos WHERE id = ?", (pid,)).fetchone()
            assert ped_db["status_pagamento"] == "50% PAGO"
            assert ped_db["status_producao"] == "EM PRODUCAO"
            assert ped_db["valor_pago"] == 60.0

            # Limpeza
            conn.execute("DELETE FROM pedidos WHERE id = ?", (pid,))
            conn.execute("DELETE FROM clientes WHERE id = ?", (cid,))
            conn.commit()
        finally:
            conn.close()
