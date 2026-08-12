from fastapi import APIRouter, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer
from typing import Optional

from config.database import get_connection
from services.auth_service import authenticate_user

router = APIRouter()

SECRET_KEY = "sua_chave_secreta_empresa_123"
serializer = URLSafeTimedSerializer(SECRET_KEY)
templates = Jinja2Templates(directory="templates")

USUARIO_ADMIN = "admin"
SENHA_ADMIN = "123456"

def get_current_user(request: Request) -> Optional[str]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user = serializer.loads(session_token, max_age=86400)
        return user
    except Exception:
        return None

def auth_required(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

@router.get("/login", response_class=HTMLResponse)
def page_login(request: Request, error: Optional[str] = None):
    if get_current_user(request):
        return RedirectResponse(url="/pedidos", status_code=302)
    
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error}
    )

@router.post("/login")
def process_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user_input = username.strip()
    pass_input = password.strip()

    if user_input == USUARIO_ADMIN and pass_input == SENHA_ADMIN:
        token = serializer.dumps(user_input)
        res = RedirectResponse(url="/pedidos", status_code=303)
        res.set_cookie(key="session", value=token, httponly=True, max_age=86400)
        return res

    if authenticate_user(user_input, pass_input):
        token = serializer.dumps(user_input)
        res = RedirectResponse(url="/pedidos", status_code=303)
        res.set_cookie(key="session", value=token, httponly=True, max_age=86400)
        return res

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Usuário ou senha incorretos."}
    )

@router.get("/logout")
def logout(response: Response):
    res = RedirectResponse(url="/login", status_code=302)
    res.delete_cookie(key="session")
    return res

# 💡 ROTA NOVA: Busca os usuários cadastrados no banco para popular os atendentes
@router.get("/api/usuarios")
def api_listar_usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT nome FROM usuarios WHERE nome IS NOT NULL AND nome != ''")
        rows = cursor.fetchall()
        conn.close()

        # Extrai os nomes da consulta
        nomes = [dict(r)["nome"] if isinstance(r, dict) else r["nome"] for r in rows] if rows else []
        return nomes
    except Exception as e:
        print(f"Erro ao buscar usuarios: {e}")
        return []