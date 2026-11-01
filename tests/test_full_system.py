import asyncio
import json
import pathlib
from starlette.requests import Request

import main
from config.database import get_connection, init_db
from routes.auth_routes import serializer
from routes.clientes_routes import ClienteSchema, criar_cliente, excluir_cliente, listar_clientes
from routes.produtos_routes import ProdutoSchema, criar_produto, listar_produtos
from routes.pedidos_routes import salvar_pedido, listar_pedidos, listar_itens_pedido, deletar_pedido
from routes.orcamentos_routes import (
    OrcamentoCreateSchema,
    OrcamentoUpdateSchema,
    OrcamentoDadosSchema,
    ItemOrcamentoSchema,
    criar_orcamento,
    obter_orcamento,
    atualizar_orcamento,
    converter_orcamento_em_venda
)
from routes.page_routes import page_pedidos, pagina_orcamentos, page_imprimir


def _make_request(path="/pedidos", username="admin"):
    token = serializer.dumps(username)
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"cookie", f"session={token}".encode("utf-8"))],
        "query_string": b"",
    }
    return Request(scope)


def test_regra_de_ouro_100_porcento_localhost():
    """Garante que nenhum template HTML carrega CDNs externos (https:// ou http://)."""
    templates_dir = pathlib.Path(__file__).resolve().parent.parent / "templates"
    for html_file in templates_dir.glob("*.html"):
        conteudo = html_file.read_text(encoding="utf-8")
        assert "https://cdn." not in conteudo, f"Dependência externa encontrada em {html_file.name}"
        assert "http://cdn." not in conteudo, f"Dependência externa encontrada em {html_file.name}"


def test_schema_banco_possui_observacao_por_item():
    """Confirma que a tabela itens_pedido possui a coluna observacao e configuracoes existe."""
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(itens_pedido)")
        colunas = [row[1] for row in cur.fetchall()]
        assert "observacao" in colunas
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes'")
        assert cur.fetchone() is not None
    finally:
        conn.close()


def test_fluxo_completo_multiplos_pedidos_com_observacoes_por_item():
    """Insere múltiplos pedidos variando quantidades e observações por item e valida persistência e histórico."""
    init_db()

    # 1. Cadastra cliente e produtos de teste
    res_cli = criar_cliente(ClienteSchema(
        nome="Gráfica Teste Validação LTDA",
        documento="12.345.678/0001-99",
        telefone="(11) 98888-7777",
        email="contato@graficateste.local",
        endereco="Rua Localhost, 100"
    ), user="admin")
    assert res_cli["sucesso"] is True
    cliente_id = res_cli["id"]

    criar_produto(ProdutoSchema(nome="Cartão de Visita Couché 300g", preco_venda=85.0, quantidade=50), user="admin")
    criar_produto(ProdutoSchema(nome="Banner Lona 440g", preco_venda=120.0, quantidade=20), user="admin")
    produtos_lista = listar_produtos(user="admin")
    prod_cartao = next(p for p in produtos_lista if "Cartão" in p["nome"])
    prod_banner = next(p for p in produtos_lista if "Banner" in p["nome"])

    # 2. Cria Pedido #1 com múltiplos itens e observações distintas por item
    payload_pedido_1 = {
        "id": None,
        "cliente_id": cliente_id,
        "usuario_nome": "Thaissa",
        "desconto": 5.0,
        "status_producao": "EM PRODUCAO",
        "status_pagamento": "PARCIAL",
        "forma_pagamento": "Pix",
        "valor_pago": 100.0,
        "observacao": "Cliente retira na sexta-feira às 14h",
        "produtos": [
            {
                "produto_id": prod_cartao["id"],
                "nome_produto": prod_cartao["nome"],
                "quantidade": 2,
                "preco_unitario": 85.0,
                "observacao": "Acabamento fosco + verniz localizado frente"
            },
            {
                "produto_id": prod_banner["id"],
                "nome_produto": prod_banner["nome"],
                "quantidade": 3,
                "preco_unitario": 120.0,
                "observacao": "Furar no canto com ilhós e bastão de madeira"
            }
        ],
        "imagens_mantidas": []
    }

    dados_ped1 = asyncio.run(salvar_pedido(dados=json.dumps(payload_pedido_1), imagens=[], user="admin"))
    assert dados_ped1["sucesso"] is True
    pedido_1_id = dados_ped1["id"]

    # 3. Verifica se os itens e observações foram salvos e aparecem no histórico
    itens_ped1 = listar_itens_pedido(pedido_1_id, user="admin")
    assert len(itens_ped1) == 2
    assert itens_ped1[0]["quantidade"] == 2
    assert itens_ped1[0]["observacao"] == "Acabamento fosco + verniz localizado frente"
    assert itens_ped1[1]["quantidade"] == 3
    assert itens_ped1[1]["observacao"] == "Furar no canto com ilhós e bastão de madeira"

    historico = listar_pedidos(user="admin")
    ped_no_historico = next(p for p in historico if p["id"] == pedido_1_id)
    assert ped_no_historico["valor_total"] == (2 * 85.0 + 3 * 120.0 - 5.0)
    assert len(ped_no_historico["itens"]) == 2
    assert ped_no_historico["itens"][0]["observacao"] == "Acabamento fosco + verniz localizado frente"

    # 4. Edita o pedido alterando quantidade e observação do item
    payload_pedido_1["id"] = pedido_1_id
    payload_pedido_1["produtos"][0]["quantidade"] = 4
    payload_pedido_1["produtos"][0]["observacao"] = "Laminação fosca frente e verso + cantos arredondados"
    res_edit = asyncio.run(salvar_pedido(dados=json.dumps(payload_pedido_1), imagens=[], user="admin"))
    assert res_edit["sucesso"] is True

    itens_atualizados = listar_itens_pedido(pedido_1_id, user="admin")
    assert itens_atualizados[0]["quantidade"] == 4
    assert itens_atualizados[0]["observacao"] == "Laminação fosca frente e verso + cantos arredondados"

    # 5. Testa Orçamento com observação por item, edição e conversão em venda
    res_orc = asyncio.run(criar_orcamento(
        payload=OrcamentoCreateSchema(
            dados=OrcamentoDadosSchema(
                cliente_id=cliente_id,
                usuario="Michel",
                desconto=0.0,
                observacao="Validade 7 dias",
                itens=[
                    ItemOrcamentoSchema(
                        produto_id=prod_banner["id"],
                        quantidade=5,
                        preco_unitario=115.0,
                        observacao="Medida 1,20m x 0,80m com ilhós reforçado"
                    )
                ]
            )
        ),
        user="admin"
    ))
    assert res_orc["sucesso"] is True
    orc_id = res_orc["id"]

    orc_detalhe = obter_orcamento(orc_id, user="admin")
    assert orc_detalhe["itens"][0]["observacao"] == "Medida 1,20m x 0,80m com ilhós reforçado"

    res_conv = converter_orcamento_em_venda(orc_id, user="admin")
    assert res_conv["sucesso"] is True

    # 6. Testa renderização das abas e da página de impressão
    req = _make_request("/imprimir", "admin")
    resp_ped_html = page_pedidos(req, user="admin").body.decode("utf-8")
    assert "tab-btn-historico" in resp_ped_html
    assert "tab-btn-novo" in resp_ped_html
    assert "tab-btn-config" in resp_ped_html

    resp_imp_html = page_imprimir(req, id=pedido_1_id, user="admin").body.decode("utf-8")
    assert "@media print" in resp_imp_html
    assert '[draggable="true"]' in resp_imp_html

    # Limpeza dos registros de teste criados
    deletar_pedido(pedido_1_id, user="admin")
    deletar_pedido(orc_id, user="admin")
    excluir_cliente(cliente_id, user="admin")
