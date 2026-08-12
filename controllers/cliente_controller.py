from config.database import get_connection
from services.db_utils import fetch_all_as_dicts

class ClienteController:

    @staticmethod
    def listar_todos():
        return fetch_all_as_dicts("SELECT * FROM clientes ORDER BY id DESC")

    @staticmethod
    def salvar(nome="", telefone="", email="", c_id=None):
        conn = get_connection()
        cursor = conn.cursor()
        
        if c_id:
            cursor.execute(
                "UPDATE clientes SET nome=?, telefone=?, email=? WHERE id=?",
                (nome, telefone, email, c_id)
            )
        else:
            # O SQLite gera o ID incremental automaticamente
            cursor.execute(
                "INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)",
                (nome, telefone, email)
            )
            
        conn.commit()
        conn.close()

    @staticmethod
    def atualizar(c_id, nome, telefone, email):
        ClienteController.salvar(nome=nome, telefone=telefone, email=email, c_id=c_id)

    @staticmethod
    def excluir(c_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id=?", (c_id,))
        conn.commit()
        conn.close()