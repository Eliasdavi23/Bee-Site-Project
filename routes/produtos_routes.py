from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from routes.auth_routes import auth_required
from controllers.produto_controller import ProdutoController

router = APIRouter()


class ProdutoSchema(BaseModel):
    nome: str
    preco_venda: float = 0.0
    quantidade: int = 0


@router.get("/api/produtos")
def listar_produtos(user: str = Depends(auth_required)):
    try:
        produtos = ProdutoController.listar_todos()
        # Garante compatibilidade tanto com preco_venda quanto preco
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
            preco_venda=max(0.0, float(p.preco_venda or 0.0)),
            quantidade=max(0, int(p.quantidade or 0))
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
            preco_venda=max(0.0, float(p.preco_venda or 0.0)),
            quantidade=max(0, int(p.quantidade or 0))
        )
        return {"status": "ok", "sucesso": True}
    except Exception as e:
        print(f"Erro ao atualizar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/produtos/{produto_id}")
def excluir_produto(produto_id: int, user: str = Depends(auth_required)):
    try:
        ProdutoController.excluir(produto_id)
        return {"status": "ok", "sucesso": True}
    except Exception as e:
        print(f"Erro ao excluir produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))
