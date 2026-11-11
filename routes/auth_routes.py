import time
import urllib.parse
from typing import Dict, List, Optional
from fastapi import APIRouter, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer

from services.auth_service import (
    authenticate_user,
    get_user_canonical_name,
    listar_usuarios_ativos,
)

router = APIRouter()

SECRET_KEY = "sua_chave_secreta_empresa_123"
serializer = URLSafeTimedSerializer(SECRET_KEY)
templates = Jinja2Templates(directory="templates")

USUARIO_ADMIN = "admin"
SENHA_ADMIN = "123456"

# Protecao contra forca bruta em memoria
# Armazena timestamps de tentativas incorretas por chave (ip ou username)
FAILED_ATTEMPTS: Dict[str, List[float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_PERIOD_SECONDS = 30


def _is_rate_limited(identifier: str) -> bool:
    agora = time.time()
    tentativas = FAILED_ATTEMPTS.get(identifier, [])
    # Mantem apenas tentativas dos ultimos 60 segundos
    tentativas = [t for t in tentativas if agora - t < 60]
    FAILED_ATTEMPTS[identifier] = tentativas
    return len(tentativas) >= MAX_FAILED_ATTEMPTS


def _record_failed_attempt(identifier: str):
    agora = time.time()
    tentativas = FAILED_ATTEMPTS.get(identifier, [])
    tentativas.append(agora)
    FAILED_ATTEMPTS[identifier] = tentativas


def _reset_failed_attempts(identifier: str):
    FAILED_ATTEMPTS.pop(identifier, None)


def get_current_user(request: Request) -> Optional[str]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        # Validade maxima de 30 dias para sessao
        user = serializer.loads(session_token, max_age=86400 * 30)
        return str(user).strip() if user else None
    except Exception:
        return None


def auth_required(request: Request):
    user = get_current_user(request)
    if not user:
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada ou não autenticada."
            )
        target = str(request.url.path)
        if request.url.query:
            target += f"?{request.url.query}"
        encoded_next = urllib.parse.quote(target)
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/login?next={encoded_next}"}
        )
    return user


def _sanitize_next_url(next_url: Optional[str]) -> str:
    if not next_url:
        return "/pedidos"
    clean = str(next_url).strip()
    # Evita Open Redirect (deve comecar com / e nao com //)
    if clean.startswith("/") and not clean.startswith("//"):
        return clean
    return "/pedidos"


@router.get("/login", response_class=HTMLResponse)
def page_login(request: Request, error: Optional[str] = None, next: Optional[str] = None):
    if get_current_user(request):
        return RedirectResponse(url=_sanitize_next_url(next), status_code=302)

    usuarios_rapidos = listar_usuarios_ativos()

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": error,
            "next": next or "",
            "usuarios_rapidos": usuarios_rapidos,
        }
    )


@router.post("/login")
def process_login(
    request: Request,
    response: Response,
    username: str = Form(""),
    password: str = Form(""),
    lembrar: Optional[str] = Form(None),
    next: Optional[str] = Form(None),
):
    user_input = (username or "").strip()
    pass_input = (password or "").strip()
    client_ip = request.client.host if request.client else "local"
    identifier = f"{client_ip}:{user_input.lower()}"

    usuarios_rapidos = listar_usuarios_ativos()

    if _is_rate_limited(identifier) or _is_rate_limited(client_ip):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Muitas tentativas incorretas. Por segurança, aguarde 30 segundos antes de tentar novamente.",
                "username": user_input,
                "next": next or "",
                "usuarios_rapidos": usuarios_rapidos,
            },
            status_code=429
        )

    if not user_input or not pass_input:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Por favor, preencha o usuário e a senha.",
                "username": user_input,
                "next": next or "",
                "usuarios_rapidos": usuarios_rapidos,
            }
        )

    # Validacao de credenciais com suporte a usuarios do banco e admin
    if authenticate_user(user_input, pass_input):
        _reset_failed_attempts(identifier)
        _reset_failed_attempts(client_ip)

        nome_efetivo = get_user_canonical_name(user_input)
        token = serializer.dumps(nome_efetivo)

        target_url = _sanitize_next_url(next)
        res = RedirectResponse(url=target_url, status_code=303)

        # 30 dias se 'lembrar', senao 7 dias
        max_age = 86400 * 30 if lembrar else 86400 * 7

        res.set_cookie(
            key="session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=max_age,
            secure=False
        )
        return res

    # Falha de autenticacao: registra tentativa
    _record_failed_attempt(identifier)
    _record_failed_attempt(client_ip)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Usuário ou senha incorretos.",
            "username": user_input,
            "next": next or "",
            "usuarios_rapidos": usuarios_rapidos,
        }
    )


@router.get("/logout")
def logout(response: Response):
    res = RedirectResponse(url="/login", status_code=302)
    res.delete_cookie(key="session")
    return res
