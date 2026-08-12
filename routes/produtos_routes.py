from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from routes.auth_routes import auth_required
from controllers.produto_controller import ProdutoController

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class ProdutoSchema(BaseModel):
    nome: str
    preco_venda: float = 0.0
    quantidade: int = 0

@router.get("/produtos", response_class=HTMLResponse)
def page_produtos(request: Request):
    user = auth_required(request)
    return templates.TemplateResponse(
        request=request,
        name="produtos.html",
        context={"page": "produtos", "user": user}
    )

@router.get("/api/produtos")
def listar_produtos():
    try:
        return ProdutoController.listar_todos()
    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/produtos")
def criar_produto(p: ProdutoSchema):
    try:
        ProdutoController.salvar(
            nome=p.nome,
            preco_venda=p.preco_venda,
            quantidade=p.quantidade
        )
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro ao criar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/produtos/{produto_id}")
def atualizar_produto(produto_id: int, p: ProdutoSchema):
    try:
        ProdutoController.atualizar(
            p_id=produto_id,
            nome=p.nome,
            preco_venda=p.preco_venda,
            quantidade=p.quantidade
        )
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro ao atualizar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/produtos/{produto_id}")
def excluir_produto(produto_id: int):
    try:
        ProdutoController.excluir(produto_id)
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro ao excluir produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))