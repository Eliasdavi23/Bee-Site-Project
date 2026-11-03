"""
Rotas HTTP do módulo de Atendimento WhatsApp + IA.

Inclui:
- Status e configurações do módulo (somente gestores alteram o modo automático)
- Listagem e detalhe de conversas + histórico de mensagens
- Registro manual de mensagem recebida (para uso no modo link wa.me)
- Sugestão de resposta com IA (baseada nos pedidos/orçamentos reais do cliente)
- Rascunhos inteligentes para Pedidos, Orçamentos e Clientes
- Envio de mensagem (automático via Evolution/Cloud ou link wa.me)
- Webhooks protegidos para Evolution API e WhatsApp Cloud API (Meta)
"""
import json
import logging
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from services import ia_service
from routes.auth_routes import auth_required
from services.whatsapp import atendimento, contexto, notificacoes
from services.whatsapp import repositorio as repo
from services.whatsapp.config import PROVEDOR_CLOUD, PROVEDOR_EVOLUTION, carregar_config
from services.whatsapp.seguranca import assinatura_meta_valida, token_valido
from services.whatsapp.telefone import formatar_exibicao, link_whatsapp

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp & Atendimento IA"])

USUARIOS_GESTORES = {"admin", "thaissa", "michel", "thaissa/michel"}
LIMITE_BYTES_WEBHOOK = 256_000


# ---------------------------------------------------------------------------
# SCHEMAS PYDANTIC (BLINDAGEM ANTI-GORILA)
# ---------------------------------------------------------------------------
class ConfigWhatsAppSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auto_resposta: Optional[bool] = None
    aviso_status: Optional[bool] = None


class ConversaUpdateSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    modo_auto: Optional[bool] = None
    precisa_atendente: Optional[bool] = None
    cliente_id: Optional[int] = Field(default=None, ge=1)
    nome_contato: Optional[str] = Field(default=None, max_length=80)


class NovaConversaManualSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    telefone: str = Field(..., min_length=8, max_length=30)
    texto: str = Field(..., min_length=1, max_length=2000)
    nome_contato: Optional[str] = Field(default="", max_length=80)


class EnviarMensagemSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    texto: str = Field(..., min_length=1, max_length=1500)
    conversa_id: Optional[int] = Field(default=None, ge=1)
    pedido_id: Optional[int] = Field(default=None, ge=1)
    cliente_id: Optional[int] = Field(default=None, ge=1)
    assumir_conversa: bool = False


class RascunhoSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tipo: Literal["status_pedido", "cobranca", "orcamento", "saudacao"] = "status_pedido"
    pedido_id: Optional[int] = Field(default=None, ge=1)
    cliente_id: Optional[int] = Field(default=None, ge=1)
    usar_ia: bool = True
    instrucao_extra: Optional[str] = Field(default="", max_length=300)


# ---------------------------------------------------------------------------
# HELPERS DE FORMATAÇÃO
# ---------------------------------------------------------------------------
def _enriquecer_conversa(c: dict) -> dict:
    item = dict(c)
    item["telefone_exibicao"] = formatar_exibicao(c.get("telefone"))
    item["nome_exibicao"] = (
        c.get("cliente_nome")
        or c.get("nome_contato")
        or item["telefone_exibicao"]
    )
    item["link_direto"] = link_whatsapp(c.get("telefone") or "")
    return item


# ---------------------------------------------------------------------------
# STATUS E CONFIGURAÇÃO DO MÓDULO
# ---------------------------------------------------------------------------
@router.get("/status")
def obter_status_whatsapp(user: str = Depends(auth_required)):
    conf = carregar_config()
    return {
        "provedor": conf.provedor,
        "provedor_solicitado": conf.provedor_solicitado,
        "envio_automatico_ativo": conf.automatico,
        "pendencias_env": conf.pendencias,
        "ia_ativa": ia_service.ia_configurada(),
        "modelo_ia": ia_service.modelo_configurado(),
        "auto_resposta": repo.ler_config_bool(atendimento.CHAVE_AUTO_RESPOSTA, False),
        "aviso_status": repo.ler_config_bool(atendimento.CHAVE_AVISO_STATUS, True),
        "usuario_gestor": (user or "").strip().lower() in USUARIOS_GESTORES,
    }


@router.post("/config")
def salvar_config_whatsapp(payload: ConfigWhatsAppSchema, user: str = Depends(auth_required)):
    if (user or "").strip().lower() not in USUARIOS_GESTORES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas gestores podem alterar as configurações automáticas do WhatsApp.",
        )
    if payload.auto_resposta is not None:
        repo.salvar_config_bool(atendimento.CHAVE_AUTO_RESPOSTA, payload.auto_resposta)
    if payload.aviso_status is not None:
        repo.salvar_config_bool(atendimento.CHAVE_AVISO_STATUS, payload.aviso_status)
    return {"sucesso": True, **obter_status_whatsapp(user=user)}


# ---------------------------------------------------------------------------
# CONVERSAS E PAINEL DE ATENDIMENTO
# ---------------------------------------------------------------------------
@router.get("/conversas")
def listar_conversas_api(
    busca: str = Query(default="", max_length=100),
    user: str = Depends(auth_required),
):
    conversas = [_enriquecer_conversa(c) for c in repo.listar_conversas(busca)]
    total_nao_lidas = sum(int(c.get("nao_lidas") or 0) for c in conversas)
    total_pendentes = sum(1 for c in conversas if c.get("precisa_atendente"))
    return {
        "conversas": conversas,
        "total_nao_lidas": total_nao_lidas,
        "total_precisa_atendente": total_pendentes,
    }


@router.get("/conversas/{conversa_id}")
def obter_conversa_api(conversa_id: int, user: str = Depends(auth_required)):
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    repo.atualizar_conversa(conversa_id, nao_lidas=0)
    conversa["nao_lidas"] = 0
    return {
        "conversa": _enriquecer_conversa(conversa),
        "mensagens": repo.listar_mensagens(conversa_id),
        "resumo_cliente": contexto.montar_contexto_cliente(conversa.get("cliente_id")),
    }


@router.patch("/conversas/{conversa_id}")
def atualizar_conversa_api(
    conversa_id: int,
    payload: ConversaUpdateSchema,
    user: str = Depends(auth_required),
):
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    campos = {}
    if payload.modo_auto is not None:
        campos["modo_auto"] = 1 if payload.modo_auto else 0
    if payload.precisa_atendente is not None:
        campos["precisa_atendente"] = 1 if payload.precisa_atendente else 0
    if payload.cliente_id is not None:
        if not contexto.obter_cliente(payload.cliente_id):
            raise HTTPException(status_code=400, detail="Cliente informado não existe.")
        campos["cliente_id"] = payload.cliente_id
    if payload.nome_contato is not None:
        campos["nome_contato"] = payload.nome_contato

    repo.atualizar_conversa(conversa_id, **campos)
    atualizada = repo.obter_conversa(conversa_id)
    return {"sucesso": True, "conversa": _enriquecer_conversa(atualizada)}


@router.post("/conversas/manual")
def registrar_entrada_manual_api(payload: NovaConversaManualSchema, user: str = Depends(auth_required)):
    try:
        resultado = atendimento.registrar_mensagem_manual(
            payload.telefone, payload.texto, payload.nome_contato or ""
        )
        sugestao = atendimento.gerar_sugestao(resultado["conversa_id"])
        return {"sucesso": True, **resultado, "sugestao": sugestao}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/conversas/{conversa_id}/sugerir")
def sugerir_resposta_api(conversa_id: int, user: str = Depends(auth_required)):
    try:
        sugestao = atendimento.gerar_sugestao(conversa_id)
        return {"sucesso": True, **sugestao}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ---------------------------------------------------------------------------
# RASCUNHOS E ENVIO (PEDIDOS, ORÇAMENTOS, CLIENTES E ATENDIMENTO)
# ---------------------------------------------------------------------------
@router.post("/rascunho")
def gerar_rascunho_api(payload: RascunhoSchema, user: str = Depends(auth_required)):
    try:
        dados = notificacoes.gerar_rascunho(
            tipo=payload.tipo,
            pedido_id=payload.pedido_id,
            cliente_id=payload.cliente_id,
            usar_ia=payload.usar_ia,
            instrucao_extra=payload.instrucao_extra or "",
        )
        return {"sucesso": True, **dados}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/enviar")
def enviar_mensagem_api(payload: EnviarMensagemSchema, user: str = Depends(auth_required)):
    try:
        resultado = atendimento.enviar_mensagem(
            texto_bruto=payload.texto,
            usuario=user or "Atendente",
            conversa_id=payload.conversa_id,
            pedido_id=payload.pedido_id,
            cliente_id=payload.cliente_id,
            assumir_conversa=payload.assumir_conversa,
        )
        return {"sucesso": True, **resultado}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ---------------------------------------------------------------------------
# WEBHOOKS PÚBLICOS (EVOLUTION API + META WHATSAPP CLOUD API)
# ---------------------------------------------------------------------------
def _extrair_evento_evolution(dados: dict) -> tuple[str, str, str, str] | None:
    """Extrai (telefone, texto, nome_contato, id_externo) do payload da Evolution API."""
    bloco = dados.get("data") if isinstance(dados.get("data"), dict) else dados
    key = bloco.get("key") if isinstance(bloco.get("key"), dict) else {}
    if key.get("fromMe"):
        return None
    remote_jid = str(key.get("remoteJid") or bloco.get("from") or "")
    if "@g.us" in remote_jid or "status@broadcast" in remote_jid:
        return None  # ignora grupos e status

    telefone = remote_jid.split("@")[0]
    msg = bloco.get("message") if isinstance(bloco.get("message"), dict) else {}
    texto = (
        msg.get("conversation")
        or (msg.get("extendedTextMessage") or {}).get("text")
        or (msg.get("imageMessage") or {}).get("caption")
        or bloco.get("text")
        or ""
    )
    nome = str(bloco.get("pushName") or bloco.get("notifyName") or "")
    id_ext = str(key.get("id") or bloco.get("id") or "")
    return telefone, str(texto), nome, id_ext


def _extrair_eventos_cloud(dados: dict) -> list[tuple[str, str, str, str]]:
    """Extrai lista de (telefone, texto, nome_contato, id_externo) do webhook da Meta."""
    eventos = []
    for entry in dados.get("entry") or []:
        for change in (entry or {}).get("changes") or []:
            valor = (change or {}).get("value") or {}
            contatos = {
                str(c.get("wa_id") or ""): str((c.get("profile") or {}).get("name") or "")
                for c in (valor.get("contacts") or [])
                if isinstance(c, dict)
            }
            for m in valor.get("messages") or []:
                if not isinstance(m, dict):
                    continue
                telefone = str(m.get("from") or "")
                tipo = m.get("type")
                if tipo == "text":
                    texto = str((m.get("text") or {}).get("body") or "")
                elif tipo == "button":
                    texto = str((m.get("button") or {}).get("text") or "")
                elif tipo == "interactive":
                    inter = m.get("interactive") or {}
                    texto = str(
                        (inter.get("button_reply") or {}).get("title")
                        or (inter.get("list_reply") or {}).get("title")
                        or ""
                    )
                else:
                    continue
                eventos.append((telefone, texto, contatos.get(telefone, ""), str(m.get("id") or "")))
    return eventos


@router.get("/webhook")
def verificar_webhook_meta(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
):
    """Desafio de verificação exigido pela Meta ao cadastrar o webhook da Cloud API."""
    conf = carregar_config()
    esperado = conf.cloud_verify_token or conf.webhook_token
    if hub_mode == "subscribe" and token_valido(hub_verify_token, esperado):
        return PlainTextResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificação inválido.")


@router.post("/webhook")
async def receber_webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe mensagens da Evolution API ou da WhatsApp Cloud API com verificação criptográfica."""
    conf = carregar_config()
    corpo = await request.body()
    if len(corpo) > LIMITE_BYTES_WEBHOOK:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload muito grande.")

    # Validação de autenticidade do webhook
    assinatura = request.headers.get("X-Hub-Signature-256")
    token_header = (
        request.headers.get("X-Webhook-Token")
        or request.headers.get("apikey")
        or request.query_params.get("token")
    )

    autenticado = False
    if conf.cloud_app_secret and assinatura_meta_valida(corpo, assinatura, conf.cloud_app_secret):
        autenticado = True
    elif conf.webhook_token and token_valido(token_header, conf.webhook_token):
        autenticado = True

    if not autenticado:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook não autorizado.")

    try:
        dados = json.loads(corpo.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido.") from None

    if not isinstance(dados, dict):
        return {"recebido": True, "processadas": 0}

    eventos: list[tuple[str, str, str, str]] = []
    if "entry" in dados or conf.provedor_solicitado == PROVEDOR_CLOUD:
        eventos.extend(_extrair_eventos_cloud(dados))
    if not eventos and ("data" in dados or "key" in dados or conf.provedor_solicitado == PROVEDOR_EVOLUTION):
        ev = _extrair_evento_evolution(dados)
        if ev:
            eventos.append(ev)

    processadas = 0
    for telefone, texto, nome, id_ext in eventos:
        reg = atendimento.processar_mensagem_recebida(telefone, texto, nome, id_ext or None)
        if reg:
            processadas += 1
            if reg["responder"]:
                background_tasks.add_task(
                    atendimento.responder_automaticamente, reg["conversa_id"], reg["mensagem_id"]
                )

    return {"recebido": True, "processadas": processadas}
