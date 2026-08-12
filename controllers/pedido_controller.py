import random
from config.database import get_connection
from services.db_utils import fetch_all_as_dicts

class PedidoController:

    @staticmethod
    def listar_todos():
        return fetch_all_as_dicts("""
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data DESC
        """)

    @staticmethod
    def salvar(cliente_id, valor_total, valor_pago, status_producao, status_pagamento, data, forma_pagamento="", desconto=0.0, usuario_nome="Sistema", observacao="", pedido_id=None):
        conn = get_connection()
        cursor = conn.cursor()
        
        if pedido_id:
            cursor.execute("""
                UPDATE pedidos 
                SET cliente_id=?, valor_total=?, valor_pago=?, desconto=?, usuario_nome=?, status_producao=?, status_pagamento=?, forma_pagamento=?, observacao=?
                WHERE id=?
            """, (cliente_id, valor_total, valor_pago, desconto, usuario_nome, status_producao, status_pagamento, forma_pagamento, observacao, pedido_id))
        else:
            novo_id = random.randint(100000, 999999)
            cursor.execute("""
                INSERT INTO pedidos (id, cliente_id, valor_total, valor_pago, desconto, usuario_nome, status_producao, status_pagamento, forma_pagamento, observacao, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (novo_id, cliente_id, valor_total, valor_pago, desconto, usuario_nome, status_producao, status_pagamento, forma_pagamento, observacao, data))
            
        conn.commit()
        conn.close()

    @staticmethod
    def excluir(pedido_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pedidos WHERE id=?", (pedido_id,))
        conn.commit()
        conn.close()