from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from routes.auth_routes import auth_required

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def root(user: str = Depends(auth_required)):
    return RedirectResponse(url="/pedidos")


@router.get("/pedidos", response_class=HTMLResponse)
def page_pedidos(request: Request, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="pedidos.html",
        context={"page": "pedidos", "user": user}
    )


@router.get("/produtos", response_class=HTMLResponse)
def page_produtos(request: Request, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="produtos.html",
        context={"page": "produtos", "user": user}
    )


@router.get("/clientes", response_class=HTMLResponse)
def page_clientes(request: Request, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="clientes.html",
        context={"page": "clientes", "user": user}
    )


@router.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"page": "dashboard", "user": user}
    )


@router.get("/imprimir", response_class=HTMLResponse)
def page_imprimir(request: Request, id: Optional[int] = None, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="imprimir.html",
        context={
            "page": "imprimir",
            "user": user,
            "pedido_id": id if id is not None else ""
        }
    )


@router.get("/orcamentos", response_class=HTMLResponse)
def pagina_orcamentos(request: Request, user: str = Depends(auth_required)):
    return templates.TemplateResponse(
        request=request,
        name="orcamentos.html",
        context={"page": "orcamentos", "user": user}
    )
