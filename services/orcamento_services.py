from config.database import get_connection
from services.db_utils import parse_decimal


def _salvar_itens_orcamento(cursor, orcamento_id: int, itens) -> None:
    for item in itens:
        qtd = max(0.01, round(parse_decimal(item.quantidade, 1.0), 4))
        preco_unit = max(0.0, round(parse_decimal(item.preco_unitario, 0.0), 4))
        subtotal_item = round(qtd * preco_unit, 2)
        obs_item = (getattr(item, "observacao", "") or "").strip()

        cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item.produto_id,))
        prod_db = cursor.fetchone()
        nome_prod = prod_db["nome"] if prod_db else "Produto"

        cursor.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal, observacao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (orcamento_id, item.produto_id, nome_prod, qtd, preco_unit, subtotal_item, obs_item),
        )


def calcular_totais_orcamento(itens, desconto) -> tuple[float, float]:
    subtotal_geral = sum(
        round(
            max(0.01, round(parse_decimal(item.quantidade, 1.0), 4))
            * max(0.0, round(parse_decimal(item.preco_unitario, 0.0), 4)),
            2,
        )
        for item in itens
    )
    desconto_limpo = max(0.0, round(parse_decimal(desconto, 0.0), 2))
    valor_total_liquido = round(max(0.0, subtotal_geral - desconto_limpo), 2)
    return desconto_limpo, valor_total_liquido


def buscar_orcamento_por_id_db(orcamento_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.*, c.nome as cliente_nome,
                   c.documento as cliente_documento,
                   c.telefone as cliente_telefone,
                   c.email as cliente_email,
                   c.endereco as cliente_endereco
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.id = ? AND p.tipo = 'ORCAMENTO'
            """,
            (orcamento_id,),
        )
        orcamento = cursor.fetchone()
        if not orcamento:
            return None

        cursor.execute(
            "SELECT id, produto_id, nome_produto, quantidade, preco_unitario, subtotal, "
            "COALESCE(observacao, '') as observacao FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC",
            (orcamento_id,),
        )
        resultado = dict(orcamento)
        resultado["itens"] = [dict(row) for row in cursor.fetchall()]
        return resultado
    finally:
        conn.close()


def atualizar_orcamento_db(orcamento_id: int, dados, usuario_responsavel: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        desconto_limpo, valor_total_liquido = calcular_totais_orcamento(dados.itens, dados.desconto)

        cursor.execute(
            """
            UPDATE pedidos
            SET cliente_id = ?, valor_total = ?, desconto = ?, observacao = ?, usuario_nome = ?
            WHERE id = ?
            """,
            (
                dados.cliente_id,
                valor_total_liquido,
                desconto_limpo,
                (dados.observacao or "").strip(),
                usuario_responsavel,
                orcamento_id,
            ),
        )
        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))
        _salvar_itens_orcamento(cursor, orcamento_id, dados.itens)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
