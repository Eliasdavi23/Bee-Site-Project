from config.database import get_connection
from services.db_utils import fetch_all_as_dicts


class ClienteController:

    @staticmethod
    def listar_todos() -> list[dict]:
        return fetch_all_as_dicts("SELECT * FROM clientes ORDER BY id DESC")

    @staticmethod
    def criar(nome: str, documento: str = "", telefone: str = "", email: str = "", endereco: str = "") -> int:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO clientes (nome, documento, telefone, email, endereco) VALUES (?, ?, ?, ?, ?)",
                (nome, documento, telefone, email, endereco),
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def atualizar(
        c_id: int, nome: str, documento: str = "", telefone: str = "", email: str = "", endereco: str = ""
    ) -> None:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE clientes SET nome=?, documento=?, telefone=?, email=?, endereco=? WHERE id=?",
                (nome, documento, telefone, email, endereco, c_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def excluir(c_id: int) -> None:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE pedidos SET cliente_id = NULL WHERE cliente_id = ?", (c_id,))
            cursor.execute("DELETE FROM clientes WHERE id=?", (c_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
