from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from controllers.cliente_controller import ClienteController
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
    try:
        return ClienteController.listar_todos()
    except Exception as e:
        print(f"Erro ao listar clientes: {e}")
        return []


@router.post("/api/clientes")
def criar_cliente(c: ClienteSchema, user: str = Depends(auth_required)):
    nome = (c.nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do cliente é obrigatório."}
    try:
        novo_id = ClienteController.criar(
            nome=nome,
            documento=(c.documento or "").strip(),
            telefone=(c.telefone or "").strip(),
            email=(c.email or "").strip(),
            endereco=(c.endereco or "").strip(),
        )
        return {"sucesso": True, "id": novo_id}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


@router.put("/api/clientes/{cliente_id}")
def atualizar_cliente(cliente_id: int, c: ClienteSchema, user: str = Depends(auth_required)):
    nome = (c.nome or "").strip()
    if not nome:
        return {"sucesso": False, "erro": "O nome do cliente é obrigatório."}
    try:
        ClienteController.atualizar(
            c_id=cliente_id,
            nome=nome,
            documento=(c.documento or "").strip(),
            telefone=(c.telefone or "").strip(),
            email=(c.email or "").strip(),
            endereco=(c.endereco or "").strip(),
        )
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


@router.delete("/api/clientes/{cliente_id}")
def excluir_cliente(cliente_id: int, user: str = Depends(auth_required)):
    try:
        ClienteController.excluir(cliente_id)
        return {"sucesso": True}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
