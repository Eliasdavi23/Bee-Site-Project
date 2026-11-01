from config.database import get_connection


def buscar_orcamento_por_id_db(orcamento_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, c.nome as cliente_nome,
                   c.documento as cliente_documento,
                   c.telefone as cliente_telefone,
                   c.email as cliente_email,
                   c.endereco as cliente_endereco
            FROM pedidos p 
            LEFT JOIN clientes c ON p.cliente_id = c.id 
            WHERE p.id = ? AND p.tipo = 'ORCAMENTO'
        """, (orcamento_id,))
        orcamento = cursor.fetchone()

        if not orcamento:
            return None

        cursor.execute(
            "SELECT id, produto_id, nome_produto, quantidade, preco_unitario, subtotal, COALESCE(observacao, '') as observacao FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC",
            (orcamento_id,)
        )
        itens = [dict(row) for row in cursor.fetchall()]

        resultado = dict(orcamento)
        resultado["itens"] = itens
        return resultado
    finally:
        conn.close()


def atualizar_orcamento_db(orcamento_id: int, dados, usuario_responsavel: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        subtotal_geral = sum(max(1.0, float(item.quantidade or 1)) * max(0.0, float(item.preco_unitario or 0)) for item in dados.itens)
        valor_total_liquido = round(max(0.0, subtotal_geral - float(dados.desconto or 0.0)), 2)

        cursor.execute("""
            UPDATE pedidos 
            SET cliente_id = ?, valor_total = ?, desconto = ?, observacao = ?, usuario_nome = ?
            WHERE id = ?
        """, (
            dados.cliente_id,
            valor_total_liquido,
            float(dados.desconto or 0.0),
            (dados.observacao or "").strip(),
            usuario_responsavel,
            orcamento_id
        ))

        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))

        for item in dados.itens:
            qtd = max(1, int(round(float(item.quantidade or 1))))
            preco_unit = max(0.0, float(item.preco_unitario or 0.0))
            subtotal_item = round(qtd * preco_unit, 2)
            obs_item = (getattr(item, "observacao", "") or "").strip()

            cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item.produto_id,))
            prod_db = cursor.fetchone()
            nome_prod = prod_db["nome"] if prod_db else "Produto"

            cursor.execute("""
                INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal, observacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                orcamento_id,
                item.produto_id,
                nome_prod,
                qtd,
                preco_unit,
                subtotal_item,
                obs_item
            ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
