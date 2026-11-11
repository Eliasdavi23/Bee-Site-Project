from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import socket
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# PILAR 3: GERENCIAMENTO DE SEGREDOS (.env via python-dotenv)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Mantém compatibilidade caso python-dotenv ainda não esteja instalado no venv
    pass

# ---------------------------------------------------------------------------
# PILAR 2: SDK OFICIAL GOOGLE GENAI (google-genai)
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import errors as genai_errors
except ImportError:
    genai = None  # type: ignore[assignment]
    genai_errors = None  # type: ignore[assignment]

from config.database import init_db
from routes.auth_routes import router as auth_router
from routes.page_routes import router as page_router
from routes.usuarios_routes import router as usuarios_router
from routes.produtos_routes import router as produtos_router
from routes.clientes_routes import router as clientes_router
from routes.pedidos_routes import router as pedidos_router
from routes.dashboard_routes import router as dashboard_router
from routes.financeiro_routes import router as financeiro_router
from routes.orcamentos_routes import router as orcamentos_router
from routes.whatsapp_routes import router as whatsapp_router
from services import ia_service

logger = logging.getLogger("uvicorn.error")

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
GITIGNORE_REQUIRED_ENTRIES = (
    ".env",
    "__pycache__/",
    "venv/",
    "whatsapp_bridge/node_modules/",
    "whatsapp_bridge/auth_info/",
)


# ---------------------------------------------------------------------------
# PILAR 4: VERIFICAÇÃO AUTOMÁTICA DO .gitignore NO LIFESPAN
# ---------------------------------------------------------------------------
def garantir_seguranca_gitignore(caminho_raiz: Path | None = None) -> None:
    """
    Garante que o arquivo .gitignore exista na raiz do projeto e contenha
    as regras críticas (.env, __pycache__/ e venv/) para bloquear vazamento
    acidental de credenciais em um git push.
    """
    base_dir = caminho_raiz or Path(__file__).resolve().parent
    gitignore_path = base_dir / ".gitignore"

    linhas_existentes: set[str] = set()
    conteudo_atual = ""

    if gitignore_path.exists():
        conteudo_atual = gitignore_path.read_text(encoding="utf-8")
        linhas_existentes = {linha.strip() for linha in conteudo_atual.splitlines() if linha.strip()}

    faltantes = [item for item in GITIGNORE_REQUIRED_ENTRIES if item not in linhas_existentes]

    if not gitignore_path.exists() or faltantes:
        prefixo = ""
        if conteudo_atual and not conteudo_atual.endswith("\n"):
            prefixo = "\n"
        bloco_novo = "\n".join(faltantes) + "\n" if faltantes else ""
        with gitignore_path.open("a", encoding="utf-8") as arquivo:
            if prefixo or bloco_novo:
                arquivo.write(f"{prefixo}{bloco_novo}")
        logger.info("Proteção Git: .gitignore verificado/atualizado com %s", faltantes or "todas as entradas")


def obter_cliente_gemini():
    """
    Inicializa o client do Google Gemini lendo exclusivamente GEMINI_API_KEY ou GOOGLE_API_KEY
    das variáveis de ambiente (nunca hardcoded no código-fonte).
    """
    if genai is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O pacote oficial 'google-genai' não está instalado no servidor.",
        )

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A chave GEMINI_API_KEY não está configurada no ambiente (.env).",
        )

    return genai.Client(api_key=api_key)


def obter_ip_rede_local() -> str:
    """Detecta automaticamente o IPv4 da placa de rede local (ex.: 192.168.x.x)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida da aplicação: protege o .gitignore, inicializa o banco e exibe o IP da rede local."""
    garantir_seguranca_gitignore()
    init_db()
    app.state.gemini_api_key_loaded = bool((os.getenv("GEMINI_API_KEY") or "").strip())
    ip_rede = obter_ip_rede_local()
    app.state.ip_rede_local = ip_rede
    logger.info("============================================================")
    logger.info("SISTEMA GRAFICA ONLINE!")
    logger.info("Acesso neste PC:       http://127.0.0.1:8000")
    logger.info("Acesso na Rede Local:  http://%s:8000", ip_rede)
    logger.info("============================================================")
    yield


# ---------------------------------------------------------------------------
# PILAR 1: SEGURANÇA ANTI-GORILAS (Pydantic c/ strip_whitespace e limites)
# ---------------------------------------------------------------------------
class PromptRequest(BaseModel):
    """
    Modelo de entrada blindado contra payloads vazios, apenas espaços
    ou strings gigantescas que poderiam exaurir memória/CPU do Uvicorn.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Texto da pergunta ou instrução enviada ao modelo Gemini.",
    )


class ConsultaIARequest(BaseModel):
    """Aceita {"pergunta": "texto"} na rota /consultar-ia com validação anti-gorilas."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    pergunta: str = Field(
        ...,
        min_length=2,
        max_length=4000,
        description="Pergunta do funcionário para o Assistente Bee.",
    )


class PromptResponse(BaseModel):
    modelo: str
    resposta: str


garantir_seguranca_gitignore()
init_db()

app = FastAPI(
    title="Sistema Interno da Empresa",
    version="2.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Registra os roteadores do sistema
app.include_router(auth_router)
app.include_router(page_router)
app.include_router(usuarios_router)
app.include_router(produtos_router)
app.include_router(clientes_router)
app.include_router(pedidos_router)
app.include_router(dashboard_router)
app.include_router(financeiro_router)
app.include_router(orcamentos_router)
app.include_router(whatsapp_router)


@app.post(
    "/api/gemini",
    response_model=PromptResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inteligência Artificial"],
)
async def gerar_conteudo_gemini(payload: PromptRequest) -> PromptResponse:
    """
    Endpoint resiliente integrado ao modelo gemini-3.8-flash.
    Captura falhas de rede/timeout e erros de upstream sem vazar tracebacks internos.
    """
    client = obter_cliente_gemini()

    try:
        if hasattr(client, "interactions"):
            interaction = client.interactions.create(
                model=GEMINI_MODEL_NAME,
                input=payload.prompt,
                store=False,
            )
            texto = (getattr(interaction, "output_text", None) or "").strip()
        else:
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=payload.prompt,
            )
            texto = (getattr(response, "text", None) or "").strip()
        if not texto:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="O modelo de IA retornou uma resposta vazia.",
            )
        return PromptResponse(modelo=GEMINI_MODEL_NAME, resposta=texto)

    except HTTPException:
        raise
    except TimeoutError as exc:
        logger.warning("Timeout na chamada ao Gemini: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo limite excedido ao aguardar resposta da IA.",
        ) from None
    except Exception as exc:
        # Se for um erro específico da API do Gemini (ex: cota, indisponibilidade upstream), retorna 502
        if genai_errors is not None and isinstance(exc, genai_errors.APIError):
            logger.error("Erro na API Google Gemini (status=%s)", getattr(exc, "code", "desconhecido"))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha de comunicação com o serviço Google Gemini (Bad Gateway).",
            ) from None

        logger.error("Erro inesperado ao processar requisição Gemini: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitação de IA.",
        ) from None


@app.post(
    "/consultar-ia",
    response_model=PromptResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inteligência Artificial"],
)
async def consultar_ia_widget(payload: ConsultaIARequest) -> PromptResponse:
    """
    Rota consumida pelo widget flutuante Assistente Bee no frontend.
    Se a IA em nuvem estiver configurada e funcional, utiliza o Google Gemini.
    Caso contrário ou em caso de sobrecarga/instabilidade da rede externa, utiliza o
    Assistente Local Inteligente para responder com base nos dados reais da gráfica, sem falhar.
    """
    if ia_service.ia_configurada():
        try:
            return await gerar_conteudo_gemini(PromptRequest(prompt=payload.pergunta))
        except Exception as exc:
            logger.warning("Falha ou sobrecarga na IA em nuvem (%s), utilizando Assistente Local", exc.__class__.__name__)

    resposta_local = ia_service.consultar_assistente_local(payload.pergunta)
    return PromptResponse(modelo="Assistente Local Bee", resposta=resposta_local)


if __name__ == "__main__":
    import uvicorn

    ip_local = obter_ip_rede_local()
    logger.info("Iniciando Uvicorn escutando em todas as interfaces (0.0.0.0:8000)...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
