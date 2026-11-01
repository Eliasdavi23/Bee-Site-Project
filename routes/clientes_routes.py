from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from config.database import get_connection
from routes.auth_routes import auth_required

router = APIRouter()


class ClienteSchema(BaseModel):
    nome: str
    documento: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""


@router.get("/api/clientes")
def listar_clientes(user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
        clientes = [dict(row) for row in cursor.fetchall()]
        return clientes
    except Exception as e:
        print(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()


@router.post("/api/clientes")
def criar_cliente(c: ClienteSchema, user: str = Depends(auth_required)):
    nome = (c.nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do cliente é obrigatório."}
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clientes (nome, documento, telefone, email, endereco)
            VALUES (?, ?, ?, ?, ?)
        """, (
            nome,
            (c.documento or "").strip(),
            (c.telefone or "").strip(),
            (c.email or "").strip(),
            (c.endereco or "").strip()
        ))
        conn.commit()
        return {"sucesso": True, "id": cursor.lastrowid}
    except Exception as e:
        conn.rollback()
        return {"sucesso": False, "erro": str(e)}
    finally:
        conn.close()


@router.put("/api/clientes/{cliente_id}")
def atualizar_cliente(cliente_id: int, c: ClienteSchema, user: str = Depends(auth_required)):
    nome = (c.nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do cliente é obrigatório."}
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET nome=?, documento=?, telefone=?, email=?, endereco=?
            WHERE id=?
        """, (
            nome,
            (c.documento or "").strip(),
            (c.telefone or "").strip(),
            (c.email or "").strip(),
            (c.endereco or "").strip(),
            cliente_id
        ))
        conn.commit()
        return {"sucesso": True}
    except Exception as e:
        conn.rollback()
        return {"sucesso": False, "erro": str(e)}
    finally:
        conn.close()


@router.delete("/api/clientes/{cliente_id}")
def excluir_cliente(cliente_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET cliente_id = NULL WHERE cliente_id = ?", (cliente_id,))
        cursor.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
        conn.commit()
        return {"sucesso": True}
    except Exception as e:
        conn.rollback()
        return {"sucesso": False, "erro": str(e)}
    finally:
        conn.close()
