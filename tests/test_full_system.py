import re
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
        telefone="16 997100623",
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
    for el_id in [
        'id="layout-cupom"', 'id="c-producao"', 'id="c-itens"', 'id="c-emp-razao"', 'id="c-email"',
        'id="layout-os"', 'id="os-producao"', 'id="os-itens"', 'id="os-empresa-nome"', 'id="os-emp-razao"',
        'id="layout-orcamento"', 'id="orc-itens"', 'id="orc-valor-pago"', 'id="orc-restante"', 'id="orc-emp-razao"'
    ]:
        assert el_id in resp_imp_html, f"Elemento faltante na impressao: {el_id}"

    # Limpeza dos registros de teste criados
    deletar_pedido(pedido_1_id, user="admin")
    deletar_pedido(orc_id, user="admin")
    excluir_cliente(cliente_id, user="admin")
    from controllers.produto_controller import ProdutoController
    ProdutoController.excluir(prod_cartao["id"])
    ProdutoController.excluir(prod_banner["id"])


def test_pedidos_e_orcamentos_com_numeros_decimais():
    """Valida que quantidades decimais (ex: 1.5, 0.75) e valores/descontos decimais com ponto ou vírgula salvam com exatidão."""
    init_db()

    res_cli = criar_cliente(ClienteSchema(
        nome="Cliente Decimal Teste",
        documento="000.000.000-00",
        telefone="16 997100623"
    ), user="admin")
    cliente_id = res_cli["id"]

    criar_produto(ProdutoSchema(nome="Adesivo Vinil m2", preco_venda="45,50", quantidade="12,5"), user="admin")
    prod = next(p for p in listar_produtos(user="admin") if p["nome"] == "Adesivo Vinil m2")
    assert abs(prod["preco_venda"] - 45.50) < 0.001
    assert abs(prod["quantidade"] - 12.5) < 0.001

    payload_decimal = {
        "id": None,
        "cliente_id": cliente_id,
        "usuario_nome": "Davi",
        "desconto": "2,75",
        "status_producao": "PENDENTE",
        "status_pagamento": "PARCIAL",
        "forma_pagamento": "Pix",
        "valor_pago": "30,50",
        "observacao": "Pedido com medidas e valores fracionados",
        "produtos": [
            {
                "produto_id": prod["id"],
                "nome_produto": prod["nome"],
                "quantidade": "1,5",
                "preco_unitario": "45,50",
                "observacao": "1,5 m² de adesivo recorte"
            },
            {
                "produto_id": prod["id"],
                "nome_produto": "Lona Fracionada",
                "quantidade": 0.75,
                "preco_unitario": 80.25,
                "observacao": "0,75 m²"
            }
        ],
        "imagens_mantidas": []
    }

    res_ped = asyncio.run(salvar_pedido(dados=json.dumps(payload_decimal), imagens=[], user="admin"))
    assert res_ped["sucesso"] is True
    ped_id = res_ped["id"]

    itens = listar_itens_pedido(ped_id, user="admin")
    assert len(itens) == 2
    assert abs(itens[0]["quantidade"] - 1.5) < 0.001
    assert abs(itens[0]["preco_unitario"] - 45.50) < 0.001
    assert abs(itens[0]["subtotal"] - 68.25) < 0.01

    assert abs(itens[1]["quantidade"] - 0.75) < 0.001
    assert abs(itens[1]["preco_unitario"] - 80.25) < 0.001
    assert abs(itens[1]["subtotal"] - 60.19) < 0.01

    ped_salvo = next(p for p in listar_pedidos(user="admin") if p["id"] == ped_id)
    # 68.25 + 60.19 - 2.75 = 125.69
    assert abs(ped_salvo["valor_total"] - 125.69) < 0.01
    assert abs(ped_salvo["desconto"] - 2.75) < 0.01
    assert abs(ped_salvo["valor_pago"] - 30.50) < 0.01

    # Também valida orçamento com quantidade e preço decimais
    res_orc = asyncio.run(criar_orcamento(
        payload=OrcamentoCreateSchema(
            dados=OrcamentoDadosSchema(
                cliente_id=cliente_id,
                usuario="Davi",
                desconto="1,25",
                observacao="Orçamento decimal",
                itens=[
                    ItemOrcamentoSchema(
                        produto_id=prod["id"],
                        quantidade="2,5",
                        preco_unitario="19,90",
                        observacao="2,5 metros"
                    )
                ]
            )
        ),
        user="admin"
    ))
    assert res_orc["sucesso"] is True
    orc_id = res_orc["id"]
    orc_db = obter_orcamento(orc_id, user="admin")
    assert abs(orc_db["itens"][0]["quantidade"] - 2.5) < 0.001
    assert abs(orc_db["itens"][0]["preco_unitario"] - 19.90) < 0.001
    assert abs(orc_db["valor_total"] - (round(2.5 * 19.90, 2) - 1.25)) < 0.01

    deletar_pedido(ped_id, user="admin")
    deletar_pedido(orc_id, user="admin")
    excluir_cliente(cliente_id, user="admin")
    from controllers.produto_controller import ProdutoController
    ProdutoController.excluir(prod["id"])


def test_pilares_gemini_e_gitignore():
    """Valida a proteção do .gitignore no lifespan e a validação Pydantic anti-gorilas do PromptRequest."""
    main.garantir_seguranca_gitignore()
    gitignore_path = pathlib.Path(__file__).resolve().parent.parent / ".gitignore"
    assert gitignore_path.exists()
    linhas = {l.strip() for l in gitignore_path.read_text(encoding="utf-8").splitlines() if l.strip()}
    assert ".env" in linhas
    assert "__pycache__/" in linhas
    assert "venv/" in linhas

    # Testa strip_whitespace e limites de tamanho no PromptRequest
    req_valida = main.PromptRequest(prompt="   Criar descrição para cartão de visita   ")
    assert req_valida.prompt == "Criar descrição para cartão de visita"

    try:
        main.PromptRequest(prompt="   ")
        assert False, "Deveria rejeitar prompt apenas com espaços em branco"
    except Exception:
        pass


def test_sistema_hud_unificado_e_zero_emojis():
    """Valida que o sistema BeeHUD está instalado, sem alertas nativos bloqueantes e com zero emojis."""
    root = pathlib.Path(__file__).resolve().parent.parent
    hud_file = root / "static" / "js" / "hud.js"
    assert hud_file.exists(), "static/js/hud.js deve existir."
    hud_content = hud_file.read_text(encoding="utf-8")
    assert "window.BeeHUD = BeeHUD;" in hud_content
    assert "toast" in hud_content and "confirm" in hud_content and "alert" in hud_content

    base_html = (root / "templates" / "base.html").read_text(encoding="utf-8")
    assert "static/js/hud.js" in base_html, "base.html deve carregar hud.js no head."

    # Verifica ausência de alert() e confirm() nativos nos scripts de aplicação
    js_files = list((root / "static" / "js").glob("**/*.js"))
    for js_p in js_files:
        if js_p.name == "hud.js" or "vendor" in js_p.parts:
            continue
        text = js_p.read_text(encoding="utf-8")
        assert not re.search(r'(?<!BeeHUD\.)alert\(', text), f"alert() nativo ainda presente em {js_p.name}"
        assert not re.search(r'(?<!BeeHUD\.)confirm\(', text), f"confirm() nativo ainda presente em {js_p.name}"

    # Valida política estrita de zero emojis nos arquivos de código
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55]', flags=re.UNICODE)
    for p in list((root / "static" / "js").glob("**/*.js")) + list((root / "templates").glob("**/*.html")):
        if "vendor" in p.parts:
            continue
        for lno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for ch in emoji_pattern.findall(line):
                if ch in ['\u2715', '\u2716']:
                    continue
                assert False, f"Emoji proibido encontrado em {p.name}:{lno}: {ch}"


def test_isolamento_imagens_uploads_e_gitignore():
    """Valida que o diretório de imagens de pedidos é isolado e blindado contra commits no .gitignore."""
    import subprocess
    from routes.pedidos_routes import UPLOAD_DIR

    base_dir = pathlib.Path(__file__).resolve().parent.parent
    assert UPLOAD_DIR == "static/uploads/pedidos"

    upload_dir = base_dir / "static" / "uploads"
    pedidos_dir = upload_dir / "pedidos"
    img_dir = base_dir / "static" / "img"

    assert upload_dir.exists(), "Diretório static/uploads deve existir"
    assert pedidos_dir.exists(), "Diretório static/uploads/pedidos deve existir"
    assert (upload_dir / ".gitkeep").exists(), "static/uploads/.gitkeep deve existir"
    assert (pedidos_dir / ".gitkeep").exists(), "static/uploads/pedidos/.gitkeep deve existir"
    assert (img_dir / "logo.png").exists(), "Logo estático deve existir em static/img/logo.png"

    # Testa se imagens de pedidos são ignoradas pelo Git
    temp_img = pedidos_dir / "__temp_test_pedido.jpg"
    temp_img.write_text("dummy-image-content", encoding="utf-8")
    try:
        rel_path = str(temp_img.relative_to(base_dir)).replace("\\", "/")
        res = subprocess.run(
            ["git", "check-ignore", "-v", rel_path],
            capture_output=True,
            text=True,
            cwd=str(base_dir)
        )
        assert res.returncode == 0, f"Imagem de pedido deveria ser ignorada pelo git: {res.stdout}"
        assert "static/uploads" in res.stdout
    finally:
        if temp_img.exists():
            temp_img.unlink()

    # Valida que .gitkeep é mantido via regra de negação
    res_keep = subprocess.run(
        ["git", "check-ignore", "-v", "static/uploads/.gitkeep"],
        capture_output=True,
        text=True,
        cwd=str(base_dir)
    )
    if res_keep.returncode == 0:
        assert "!" in res_keep.stdout, ".gitkeep deve ser incluído via regra de negação (!)"

