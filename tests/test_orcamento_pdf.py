import asyncio
import io
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))

from config.database import get_connection, init_db
from controllers.cliente_controller import ClienteController
from routes.produtos_routes import ProdutoSchema, criar_produto, listar_produtos
from routes.orcamentos_routes import (
    OrcamentoCreateSchema,
    OrcamentoDadosSchema,
    ItemOrcamentoSchema,
    EnviarOrcamentoWhatsAppSchema,
    EnviarOrcamentoEmailSchema,
    criar_orcamento,
    obter_orcamento,
    baixar_orcamento_pdf,
    enviar_orcamento_whatsapp_api,
    enviar_orcamento_email_api,
)
from services import pdf_service
from services.whatsapp import bridge_manager, repositorio as repo
from tests.test_whatsapp import NUMERO_TESTE, NUMERO_TESTE_FMT, PreservarConversaTeste


def test_gerador_pdf_orcamento_estrutura_e_validade():
    """Garante que o gerador de PDF produz documento A4 válido e completo."""
    dados_orc = {
        "id": 999,
        "data": "06/11/2026",
        "usuario_nome": "Thaissa",
        "cliente_nome": "Davi Elias Teste",
        "cliente_documento": "123.456.789-00",
        "cliente_telefone": NUMERO_TESTE_FMT,
        "cliente_email": "davi@teste.local",
        "cliente_endereco": "Rua do Teste, 100 - Franca/SP",
        "desconto": 15.0,
        "observacao": "Vinil adesivo fosco de alta durabilidade.",
        "itens": [
            {
                "nome_produto": "Adesivo Vinil 10x15cm",
                "quantidade": 100,
                "preco_unitario": 1.5,
                "observacao": "Corte reto com borda",
            },
            {
                "nome_produto": "Banner 80x120cm",
                "quantidade": 1,
                "preco_unitario": 80.0,
                "observacao": "Madeira e cordinha",
            },
        ],
    }

    pdf_bytes = pdf_service.gerar_pdf_orcamento(dados_orc)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes

    # Valida formatacao dinamica de localidade e telefone da empresa
    linha_completa = pdf_service.formatar_linha_contato_empresa({
        "cidade_empresa": "Franca",
        "estado_empresa": "SP",
        "telefone_empresa": "(16) 99710-0623",
    })
    assert linha_completa == "Franca / SP • Telefone/WhatsApp: (16) 99710-0623"

    linha_sem_estado = pdf_service.formatar_linha_contato_empresa({
        "cidade_empresa": "Franca",
        "telefone_empresa": "(16) 3103-5793",
    })
    assert linha_sem_estado == "Franca • Telefone/WhatsApp: (16) 3103-5793"

    linha_sem_tel = pdf_service.formatar_linha_contato_empresa({
        "cidade_empresa": "São Paulo",
        "estado_empresa": "SP",
    })
    assert linha_sem_tel == "São Paulo / SP"

    # Valida geracao com dados institucionais customizados
    empresa_custom = {
        "nome_empresa": "GRÁFICA MODELO",
        "subtitulo_empresa": "Impressão Digital & Brindes",
        "cidade_empresa": "Ribeirão Preto",
        "estado_empresa": "SP",
        "telefone_empresa": "(16) 3333-4444",
    }
    pdf_custom = pdf_service.gerar_pdf_orcamento(dados_orc, empresa=empresa_custom)
    assert isinstance(pdf_custom, bytes)
    assert len(pdf_custom) > 2000


def test_fluxo_completo_orcamento_pdf_e_disparo_whatsapp():
    """Cria orçamento no banco e valida download do PDF e envio automático via WhatsApp para 16 997100623."""
    init_db()
    with PreservarConversaTeste(NUMERO_TESTE):
        # 1. Cria cliente e produtos de teste
        cid = ClienteController.criar(
            nome="Cliente Proposta PDF",
            telefone=NUMERO_TESTE_FMT,
            email="cliente.proposta@teste.local",
            documento="333.444.555-66",
            endereco="Av. Brasil, 500",
        )
        criar_produto(ProdutoSchema(nome="Cartão Fidelidade 250g", preco_venda=65.0, quantidade=100), user="admin")
        prod = next(p for p in listar_produtos(user="admin") if p["nome"] == "Cartão Fidelidade 250g")
        pid = prod["id"]

        # 2. Cria orçamento oficial
        payload = OrcamentoCreateSchema(
            dados=OrcamentoDadosSchema(
                cliente_id=cid,
                usuario="Thaissa",
                desconto=5.0,
                observacao="Entregar com verniz localizado.",
                itens=[
                    ItemOrcamentoSchema(
                        produto_id=pid,
                        quantidade=2,
                        preco_unitario=65.0,
                        observacao="Verniz UV frente",
                    )
                ],
            )
        )
        res_cria = asyncio.run(criar_orcamento(payload, user="Thaissa"))
        assert res_cria["sucesso"] is True
        orcamento_id = res_cria["id"]

        try:
            # 3. Testa endpoint GET /{orcamento_id}/pdf
            res_pdf = baixar_orcamento_pdf(orcamento_id, user="Thaissa")
            assert res_pdf.status_code == 200
            assert res_pdf.media_type == "application/pdf"
            assert res_pdf.body.startswith(b"%PDF-")
            assert f"Orcamento_{orcamento_id}.pdf" in res_pdf.headers.get("Content-Disposition", "")

            # 4. Testa endpoint POST /{orcamento_id}/enviar-whatsapp simulando ponte conectada
            with patch(
                "services.whatsapp.bridge_manager.enviar_arquivo_via_bridge",
                return_value=(True, "WA_PDF_TEST_ID_123", ""),
            ):
                payload_wa = EnviarOrcamentoWhatsAppSchema(
                    telefone=NUMERO_TESTE,
                    mensagem="Olá! Segue o orçamento solicitado em anexo.",
                )
                res_wa = enviar_orcamento_whatsapp_api(orcamento_id, payload=payload_wa, user="Thaissa")

                assert res_wa["sucesso"] is True
                assert res_wa["enviado"] is True
                assert res_wa["orcamento_id"] == orcamento_id
                assert "enviado com sucesso" in res_wa["mensagem"].lower()

                # Verifica se a mensagem foi registrada no banco de dados da conversa
                conv_id = res_wa.get("conversa_id")
                assert conv_id is not None
                mensagens = repo.listar_mensagens(conv_id)
                msg_pdf = next((m for m in mensagens if m.get("id_externo") == "WA_PDF_TEST_ID_123"), None)
                assert msg_pdf is not None
                assert msg_pdf["midia_tipo"] == "documento"
                assert "Orcamento_" in msg_pdf["texto"]

            # 5. Testa fallback de e-mail quando SMTP não está configurado
            res_email = enviar_orcamento_email_api(
                orcamento_id,
                payload=EnviarOrcamentoEmailSchema(email="cliente.proposta@teste.local"),
                user="Thaissa",
            )
            assert res_email["sucesso"] is False
            assert res_email["configurado"] is False
            assert "pdf_url" in res_email
            assert res_email["pdf_url"].endswith(".pdf")

        finally:
            # Limpeza
            conn = get_connection()
            try:
                conn.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))
                conn.execute("DELETE FROM pedidos WHERE id = ?", (orcamento_id,))
                conn.execute("DELETE FROM produtos WHERE id = ?", (pid,))
                conn.execute("DELETE FROM clientes WHERE id = ?", (cid,))
                conn.commit()
            finally:
                conn.close()


if __name__ == "__main__":
    test_gerador_pdf_orcamento_estrutura_e_validade()
    test_fluxo_completo_orcamento_pdf_e_disparo_whatsapp()
    print("Testes de PDF de orcamento e envio WhatsApp passaram com sucesso (0 erros)!")
