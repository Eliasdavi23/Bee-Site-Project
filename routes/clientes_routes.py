from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from config.database import get_connection
from routes.auth_routes import auth_required

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class ClienteSchema(BaseModel):
    nome: str
    documento: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""

@router.get("/clientes", response_class=HTMLResponse)
def page_clientes(request: Request):
    user = auth_required(request)
    return templates.TemplateResponse(
        request=request,
        name="clientes.html",
        context={"page": "clientes", "user": user}
    )

@router.get("/api/clientes")
def listar_clientes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return clientes

@router.post("/api/clientes")
def criar_cliente(c: ClienteSchema):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Usando a coluna 'documento' que é a que realmente existe no banco
        cursor.execute("""
            INSERT INTO clientes (nome, documento, telefone, email, endereco)
            VALUES (?, ?, ?, ?, ?)
        """, (c.nome, c.documento, c.telefone, c.email, c.endereco))
        conn.commit()
        conn.close()
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@router.put("/api/clientes/{cliente_id}")
def atualizar_cliente(cliente_id: int, c: ClienteSchema):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clientes 
            SET nome=?, documento=?, telefone=?, email=?, endereco=?
            WHERE id=?
        """, (c.nome, c.documento, c.telefone, c.email, c.endereco, cliente_id))
        conn.commit()
        conn.close()
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@router.delete("/api/clientes/{cliente_id}")
def excluir_cliente(cliente_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
        conn.commit()
        conn.close()
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}