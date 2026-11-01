from config.database import get_connection
from services.db_utils import fetch_all_as_dicts


class ProdutoController:

    @staticmethod
    def listar_todos():
        return fetch_all_as_dicts("SELECT * FROM produtos ORDER BY id DESC")

    @staticmethod
    def salvar(nome="", preco_venda=0, quantidade=0, p_id=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if p_id:
                cursor.execute(
                    "UPDATE produtos SET nome=?, preco_venda=?, quantidade=? WHERE id=?",
                    (nome, preco_venda, quantidade, p_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO produtos (nome, preco_venda, quantidade) VALUES (?, ?, ?)",
                    (nome, preco_venda, quantidade)
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def atualizar(p_id, nome, preco_venda, quantidade):
        ProdutoController.salvar(nome=nome, preco_venda=preco_venda, quantidade=quantidade, p_id=p_id)

    @staticmethod
    def excluir(p_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE itens_pedido SET produto_id = NULL WHERE produto_id = ?", (p_id,))
            cursor.execute("DELETE FROM produtos WHERE id=?", (p_id,))
            conn.commit()
        finally:
            conn.close()
