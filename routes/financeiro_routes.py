from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from routes.auth_routes import auth_required
from services.financeiro_service import (
    obter_dados_resumo_financeiro,
    buscar_contas_pagar,
    inserir_conta_pagar,
    marcar_conta_paga,
    deletar_conta_pagar,
    buscar_clientes_devedores
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

USUARIOS_PERMITIDOS = ["admin", "Thaissa", "Michel"]

def verificar_acesso_financeiro(request: Request) -> str:
    user = auth_required(request)
    if not user or user.lower().strip() not in [u.lower() for u in USUARIOS_PERMITIDOS]:
        raise HTTPException(status_code=403, detail="Acesso não autorizado ao módulo financeiro.")
    return user

class ContaPagarCreate(BaseModel):
    descricao: str
    categoria: Optional[str] = "Geral"
    valor: float
    data_vencimento: str

# ROTA DA PÁGINA
@router.get("/financeiro", response_class=HTMLResponse)
def page_financeiro(request: Request):
    try:
        user = verificar_acesso_financeiro(request)
        return templates.TemplateResponse(
            request=request,
            name="financeiro.html",
            context={"page": "financeiro", "user": user}
        )
    except HTTPException:
        return HTMLResponse("<script>alert('Acesso restrito ao Financeiro!'); window.location.href='/pedidos';</script>")

# APIS ENDPOINTS
@router.get("/api/financeiro/resumo")
def api_resumo_financeiro(request: Request, periodo: str = "mes_atual", data: str | None = None):
    verificar_acesso_financeiro(request)
    return obter_dados_resumo_financeiro(periodo=periodo, data_especifica=data)

@router.get("/api/financeiro/contas-pagar")
def api_listar_contas_pagar(request: Request, data: str | None = None):
    verificar_acesso_financeiro(request)
    return buscar_contas_pagar(data_vencimento=data)

@router.post("/api/financeiro/contas-pagar")
def api_criar_conta_pagar(conta: ContaPagarCreate, request: Request):
    verificar_acesso_financeiro(request)
    inserir_conta_pagar(conta.descricao, conta.categoria, conta.valor, conta.data_vencimento)
    return {"message": "Conta a pagar registrada com sucesso!"}

@router.put("/api/financeiro/contas-pagar/{conta_id}/quitar")
def api_quitar_conta_pagar(conta_id: int, request: Request):
    verificar_acesso_financeiro(request)
    marcar_conta_paga(conta_id)
    return {"message": "Conta marcada como PAGA!"}

@router.delete("/api/financeiro/contas-pagar/{conta_id}")
def api_excluir_conta_pagar(conta_id: int, request: Request):
    verificar_acesso_financeiro(request)
    deletar_conta_pagar(conta_id)
    return {"message": "Conta removida com sucesso!"}

@router.get("/api/financeiro/clientes-devedores")
def api_listar_clientes_devedores(request: Request, periodo: str = "mes_atual", data: str | None = None):
    verificar_acesso_financeiro(request)
    return buscar_clientes_devedores(periodo=periodo, data_especifica=data)
