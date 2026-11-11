import asyncio
import re
from starlette.requests import Request
from starlette.datastructures import FormData
from starlette.exceptions import HTTPException

import routes.auth_routes as auth_routes
from routes.auth_routes import (
    get_current_user,
    auth_required,
    process_login,
    page_login,
    serializer,
    _sanitize_next_url,
    FAILED_ATTEMPTS,
)
from services.auth_service import (
    authenticate_user,
    hash_password,
    verify_password,
    get_user_canonical_name,
    is_gestor,
)


def _make_auth_request(path="/pedidos", token=None, client_ip="127.0.0.1", query=""):
    headers = []
    if token:
        headers.append((b"cookie", f"session={token}".encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": query.encode("utf-8"),
        "client": (client_ip, 12345),
    }
    return Request(scope)


def test_hash_e_verificacao_senhas():
    """Valida o hashing PBKDF2 com salt seguro e a compatibilidade retroativa com senhas antigas."""
    senha = "senha_secreta_grafica_2026"
    hash_pbkdf2 = hash_password(senha)
    assert hash_pbkdf2.startswith("pbkdf2:sha256:100000$"), "Formato de hash incorreto"
    assert verify_password(senha, hash_pbkdf2) is True
    assert verify_password("senha_errada", hash_pbkdf2) is False

    # Compatibilidade com senhas legadas em texto plano
    assert verify_password("123456", "123456") is True
    assert verify_password("123456", "654321") is False


def test_autenticacao_e_insensibilidade_a_maiusculas():
    """Garante que o atendente consiga logar independentemente da capitalização (ex: Davi vs davi)."""
    assert authenticate_user("admin", "123456") is True
    assert authenticate_user("ADMIN", "123456") is True
    assert authenticate_user("admin", "senha_invalida") is False

    assert get_user_canonical_name("admin") == "admin"
    assert is_gestor("admin") is True
    assert is_gestor("ADMIN") is True
    assert is_gestor("Thaissa") is True
    assert is_gestor("thaissa") is True


def test_validacao_sessao_e_redirecionamento_seguro():
    """Testa auth_required para rotas de tela (307 com next) e para rotas de API (401)."""
    # 1. Requisição autenticada
    token = serializer.dumps("Davi")
    req_ok = _make_auth_request("/pedidos", token=token)
    assert auth_required(req_ok) == "Davi"

    # 2. Requisição não autenticada para página
    req_sem_token = _make_auth_request("/imprimir", token=None, query="id=42")
    try:
        auth_required(req_sem_token)
        assert False, "Deveria redirecionar para login"
    except HTTPException as exc:
        assert exc.status_code == 307
        assert "/login?next=" in exc.headers.get("Location", "")
        assert "/imprimir" in exc.headers.get("Location", "")
        assert "id%3D42" in exc.headers.get("Location", "") or "id=42" in exc.headers.get("Location", "")

    # 3. Requisição não autenticada para API deve devolver 401
    req_api_sem_token = _make_auth_request("/api/pedidos", token=None)
    try:
        auth_required(req_api_sem_token)
        assert False, "Deveria rejeitar API sem autenticação com 401"
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Sessão expirada" in exc.detail


def test_prevencao_open_redirect():
    """Garante que redirecionamentos após o login permaneçam estritamente dentro da aplicação."""
    assert _sanitize_next_url("/pedidos") == "/pedidos"
    assert _sanitize_next_url("/imprimir?id=10") == "/imprimir?id=10"
    assert _sanitize_next_url("//externo.com/malicioso") == "/pedidos"
    assert _sanitize_next_url("https://malicioso.com") == "/pedidos"
    assert _sanitize_next_url("") == "/pedidos"


def test_protecao_forca_bruta_e_rate_limiting():
    """Simula tentativas consecutivas de login inválido e verifica se o bloqueio temporário é ativado."""
    FAILED_ATTEMPTS.clear()
    ip_teste = "192.168.1.100"

    class DummyResponse:
        def __init__(self):
            self.cookies = {}
        def set_cookie(self, **kwargs):
            self.cookies[kwargs["key"]] = kwargs

    req = _make_auth_request("/login", token=None, client_ip=ip_teste)

    # Executa 5 tentativas inválidas consecutivas
    for _ in range(5):
        resp = process_login(
            request=req,
            response=DummyResponse(),
            username="usuario_inexistente",
            password="123",
            lembrar=None,
            next="/pedidos"
        )
        assert resp.status_code == 200

    # A 6ª tentativa deve retornar 429 Too Many Requests
    resp_bloqueado = process_login(
        request=req,
        response=DummyResponse(),
        username="usuario_inexistente",
        password="123",
        lembrar=None,
        next="/pedidos"
    )
    assert resp_bloqueado.status_code == 429
    FAILED_ATTEMPTS.clear()


def test_login_sucesso_configura_cookies_corretamente():
    """Valida que o login com sucesso gera cookie HttpOnly com SameSite Lax e duração adequada."""
    req = _make_auth_request("/login", token=None, client_ip="127.0.0.1")

    class DummyResponse:
        def __init__(self):
            self.cookies = {}
        def set_cookie(self, **kwargs):
            self.cookies[kwargs["key"]] = kwargs

    res_normal = process_login(
        request=req,
        response=DummyResponse(),
        username="admin",
        password="123456",
        lembrar=None,
        next="/orcamentos"
    )
    assert res_normal.status_code == 303
    assert res_normal.headers["Location"] == "/orcamentos"
    cookie_header = res_normal.headers.get("set-cookie", "")
    assert "session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "samesite=lax" in cookie_header.lower()
