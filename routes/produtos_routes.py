from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from controllers.produto_controller import ProdutoController
from routes.auth_routes import auth_required
from services.db_utils import parse_decimal

router = APIRouter()


class ProdutoSchema(BaseModel):
    nome: str
    preco_venda: float | str = 0.0
    quantidade: float | str = 0.0


@router.get("/api/produtos")
def listar_produtos(user: str = Depends(auth_required)):
    try:
        produtos = ProdutoController.listar_todos()
        for p in produtos:
            p["preco"] = p.get("preco_venda", 0.0)
        return produtos
    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/produtos")
def criar_produto(p: ProdutoSchema, user: str = Depends(auth_required)):
    nome = (p.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="O nome do produto é obrigatório.")
    try:
        ProdutoController.salvar(
            nome=nome,
            preco_venda=max(0.0, round(parse_decimal(p.preco_venda, 0.0), 4)),
            quantidade=max(0.0, round(parse_decimal(p.quantidade, 0.0), 4)),
        )
        return {"status": "ok", "sucesso": True}
    except Exception as e:
        print(f"Erro ao criar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/produtos/{produto_id}")
def atualizar_produto(produto_id: int, p: ProdutoSchema, user: str = Depends(auth_required)):
    nome = (p.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="O nome do produto é obrigatório.")
    try:
        ProdutoController.atualizar(
            p_id=produto_id,
            nome=nome,
            preco_venda=max(0.0, round(parse_decimal(p.preco_venda, 0.0), 4)),
            quantidade=max(0.0, round(parse_decimal(p.quantidade, 0.0), 4)),
        )
        return {"status": "ok", "sucesso": True}
    except Exception as e:
        print(f"Erro ao atualizar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/produtos")
def excluir_todos_produtos(user: str = Depends(auth_required)):
    try:
        ProdutoController.excluir_todos()
        return {"status": "ok", "sucesso": True, "mensagem": "Todos os produtos foram removidos com sucesso."}
    except Exception as e:
        print(f"Erro ao excluir todos os produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/produtos/{produto_id}")
def excluir_produto(produto_id: int, user: str = Depends(auth_required)):
    try:
        ProdutoController.excluir(produto_id)
        return {"status": "ok", "sucesso": True}
    except Exception as e:
        print(f"Erro ao excluir produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))
