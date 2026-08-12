from config.database import get_connection

def buscar_orcamento_por_id_db(orcamento_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.*, c.nome as cliente_nome 
        FROM pedidos p 
        LEFT JOIN clientes c ON p.cliente_id = c.id 
        WHERE p.id = ? AND p.tipo = 'ORCAMENTO'
    """, (orcamento_id,))
    orcamento = cursor.fetchone()
    
    if not orcamento:
        conn.close()
        return None
    
    cursor.execute("SELECT produto_id, quantidade, preco_unitario FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))
    itens = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    resultado = dict(orcamento)
    resultado["itens"] = itens
    return resultado

def atualizar_orcamento_db(orcamento_id: int, dados, usuario_responsavel: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    subtotal_geral = sum(item.quantidade * item.preco_unitario for item in dados.itens)
    valor_total_liquido = subtotal_geral - (dados.desconto or 0.0)
    if valor_total_liquido < 0:
        valor_total_liquido = 0.0

    try:
        cursor.execute("""
            UPDATE pedidos 
            SET cliente_id = ?, valor_total = ?, desconto = ?, observacao = ?, usuario_nome = ?
            WHERE id = ?
        """, (
            dados.cliente_id,
            valor_total_liquido,
            dados.desconto,
            dados.observacao,
            usuario_responsavel,
            orcamento_id
        ))

        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))

        for item in dados.itens:
            subtotal_item = item.quantidade * item.preco_unitario
            
            cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item.produto_id,))
            prod_db = cursor.fetchone()
            nome_prod = prod_db["nome"] if prod_db else "Produto"

            cursor.execute("""
                INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                orcamento_id,
                item.produto_id,
                nome_prod,
                item.quantidade,
                item.preco_unitario,
                subtotal_item
            ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()