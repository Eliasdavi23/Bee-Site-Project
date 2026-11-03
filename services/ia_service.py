"""
Serviço único de acesso à IA (Google Gemini) para módulos internos.

- Lê a chave GEMINI_API_KEY somente do ambiente (.env), nunca do código.
- Não grava as conversas no Google (store=False), pois o contexto contém dados de clientes.
- Nunca lança erros HTTP: quem chama decide o que fazer quando a IA estiver fora do ar
  (o WhatsApp, por exemplo, cai automaticamente para mensagens prontas).
"""
import logging
import os

try:
    from google import genai
except ImportError:  # Pacote opcional: o sistema funciona sem IA
    genai = None  # type: ignore[assignment]

logger = logging.getLogger("uvicorn.error")

MODELO_PADRAO = "gemini-3.8-flash"
LIMITE_PROMPT = 12000


class IAIndisponivel(Exception):
    """A IA não está instalada, configurada ou não respondeu a tempo."""


def _chave_api() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def modelo_configurado() -> str:
    return (os.getenv("GEMINI_MODEL") or "").strip() or MODELO_PADRAO


def ia_configurada() -> bool:
    return genai is not None and bool(_chave_api())


def gerar_texto(prompt: str, instrucao_sistema: str, max_tokens: int = 600) -> str:
    """Gera um texto curto. Lança IAIndisponivel em qualquer falha (sem vazar detalhes internos)."""
    if not ia_configurada():
        raise IAIndisponivel("IA não configurada (instale google-genai e defina GEMINI_API_KEY).")

    prompt = (prompt or "").strip()[:LIMITE_PROMPT]
    if not prompt:
        raise IAIndisponivel("Prompt vazio.")

    try:
        client = genai.Client(api_key=_chave_api())
        interaction = client.interactions.create(
            model=modelo_configurado(),
            input=prompt,
            system_instruction=instrucao_sistema,
            generation_config={"max_output_tokens": max_tokens},
            store=False,
        )
        texto = (getattr(interaction, "output_text", None) or "").strip()
    except Exception as exc:  # Rede, cota, timeout, modelo inválido...
        logger.warning("Falha na chamada à IA: %s", exc.__class__.__name__)
        raise IAIndisponivel("A IA não respondeu.") from None

    if not texto:
        raise IAIndisponivel("A IA retornou uma resposta vazia.")
    return texto
