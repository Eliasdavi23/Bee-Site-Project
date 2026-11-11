"""
Rotas HTTP do módulo de Atendimento WhatsApp + IA.

Inclui:
- Status e configurações do módulo (somente gestores alteram o modo automático)
- Listagem de destinatários (clientes + pedidos/orçamentos recentes) para iniciar conversa
- Listagem e detalhe de conversas + histórico de mensagens
- Registro manual de mensagem recebida (para uso no modo link / WhatsApp Web)
- Sugestão de resposta com IA (baseada nos pedidos/orçamentos reais do cliente)
- Rascunhos inteligentes para Pedidos, Orçamentos e Clientes
- Envio de mensagem (automático via Evolution/Cloud ou link WhatsApp Web / wa.me)
- Webhooks protegidos para Evolution API e WhatsApp Cloud API (Meta)
"""
import json
import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from config.database import get_connection
from routes.auth_routes import auth_required
from services import ia_service
from services.auth_service import is_gestor
from services.whatsapp import atendimento, bridge_manager, contexto, notificacoes
from services.whatsapp import repositorio as repo
from services.whatsapp.config import PROVEDOR_BRIDGE, PROVEDOR_CLOUD, PROVEDOR_EVOLUTION, carregar_config
from services.whatsapp.seguranca import assinatura_meta_valida, token_valido
from services.whatsapp.telefone import formatar_exibicao, link_whatsapp, link_whatsapp_web, normalizar_telefone

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp & Atendimento IA"])

LIMITE_BYTES_WEBHOOK = 10_000_000


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
    nao_lidas: Optional[int] = Field(default=None, ge=0, le=1000)
    atendente_nome: Optional[str] = Field(default=None, max_length=80)


class GerarPedidoSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    atendente: Optional[str] = Field(default="", max_length=80)


class NovaConversaManualSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    telefone: Optional[str] = Field(default="", max_length=40)
    texto: str = Field(..., min_length=1, max_length=2000)
    nome_contato: Optional[str] = Field(default="", max_length=80)
    cliente_id: Optional[int] = Field(default=None, ge=1)


class EnviarMensagemSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    texto: str = Field(..., min_length=1, max_length=1500)
    conversa_id: Optional[int] = Field(default=None, ge=1)
    pedido_id: Optional[int] = Field(default=None, ge=1)
    cliente_id: Optional[int] = Field(default=None, ge=1)
    telefone: Optional[str] = Field(default="", max_length=40)
    assumir_conversa: bool = False


class RascunhoSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tipo: Literal["status_pedido", "cobranca", "orcamento", "saudacao"] = "status_pedido"
    pedido_id: Optional[int] = Field(default=None, ge=1)
    cliente_id: Optional[int] = Field(default=None, ge=1)
    telefone: Optional[str] = Field(default="", max_length=40)
    usar_ia: bool = True
    instrucao_extra: Optional[str] = Field(default="", max_length=300)


# ---------------------------------------------------------------------------
# HELPERS DE FORMATAÇÃO
# ---------------------------------------------------------------------------
def _enriquecer_conversa(c: dict) -> dict:
    item = dict(c)
    tel = c.get("telefone") or ""
    item["telefone_exibicao"] = formatar_exibicao(tel)
    item["nome_exibicao"] = (
        c.get("cliente_nome")
        or c.get("nome_contato")
        or item["telefone_exibicao"]
    )
    item["link_direto"] = link_whatsapp(tel)
    item["link_web"] = link_whatsapp_web(tel)
    return item


# ---------------------------------------------------------------------------
# STATUS, CONFIGURAÇÃO E DESTINATÁRIOS
# ---------------------------------------------------------------------------
@router.get("/status")
def obter_status_whatsapp(request: Request = None, user: str = Depends(auth_required)):
    if request is not None:
        bridge_manager.atualizar_webhook_url(str(request.base_url))
    conf = carregar_config()
    bridge = bridge_manager.obter_status_bridge()
    if not bridge.get("bridge_rodando") and bridge.get("node_instalado"):
        bridge = bridge_manager.iniciar_bridge()
    provedor_efetivo = PROVEDOR_BRIDGE if bridge.get("conectado") and conf.provedor == "link" else conf.provedor
    envio_auto = conf.automatico or bool(bridge.get("conectado"))
    return {
        "provedor": provedor_efetivo,
        "provedor_solicitado": conf.provedor_solicitado,
        "envio_automatico_ativo": envio_auto,
        "pendencias_env": conf.pendencias,
        "bridge": bridge,
        "ia_ativa": True,
        "ia_gemini_ativa": ia_service.ia_configurada(),
        "modelo_ia": ia_service.modelo_configurado() if ia_service.ia_configurada() else "Assistente Interativa Local + Pedidos",
        "auto_resposta": False,
        "aviso_status": repo.ler_config_bool(atendimento.CHAVE_AVISO_STATUS, True),
        "usuario_gestor": is_gestor(user),
    }


@router.get("/bridge/status")
def obter_status_bridge_api(request: Request = None, user: str = Depends(auth_required)):
    if request is not None:
        bridge_manager.atualizar_webhook_url(str(request.base_url))
    return {"sucesso": True, **bridge_manager.obter_status_bridge()}


@router.post("/bridge/iniciar")
def iniciar_bridge_api(request: Request = None, user: str = Depends(auth_required)):
    if request is not None:
        bridge_manager.atualizar_webhook_url(str(request.base_url))
    return {"sucesso": True, **bridge_manager.iniciar_bridge()}


@router.post("/bridge/desconectar")
def desconectar_bridge_api(user: str = Depends(auth_required)):
    return {"sucesso": True, **bridge_manager.desconectar_bridge()}


@router.get("/destinatarios")
def listar_destinatarios_whatsapp(user: str = Depends(auth_required)):
    """Retorna clientes e pedidos/orçamentos recentes para iniciar conversa direto na aba WhatsApp."""
    conn = get_connection()
    try:
        clientes = [
            {
                "id": r["id"],
                "nome": r["nome"],
                "telefone": r["telefone"] or "",
                "telefone_valido": bool(normalizar_telefone(r["telefone"], aceitar_sem_ddd=True)),
            }
            for r in conn.execute("SELECT id, nome, telefone FROM clientes ORDER BY nome ASC").fetchall()
        ]
        pedidos = [
            {
                "id": r["id"],
                "cliente_id": r["cliente_id"],
                "cliente_nome": r["cliente_nome"] or "Cliente",
                "cliente_telefone": r["cliente_telefone"] or "",
                "tipo": (r["tipo"] or "VENDA").upper(),
                "status_producao": r["status_producao"] or "PENDENTE",
                "valor_total": r["valor_total"] or 0.0,
            }
            for r in conn.execute(
                "SELECT p.id, p.cliente_id, p.tipo, p.status_producao, p.valor_total, "
                "c.nome AS cliente_nome, c.telefone AS cliente_telefone "
                "FROM pedidos p LEFT JOIN clientes c ON c.id = p.cliente_id "
                "ORDER BY p.id DESC LIMIT 60"
            ).fetchall()
        ]
        return {"clientes": clientes, "pedidos": pedidos}
    finally:
        conn.close()


@router.post("/config")
def salvar_config_whatsapp(payload: ConfigWhatsAppSchema, user: str = Depends(auth_required)):
    if not is_gestor(user):
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


@router.get("/contador-nao-lidas")
def obter_contador_nao_lidas(user: str = Depends(auth_required)):
    """Retorna total de mensagens não lidas em tempo real para o badge global do menu lateral."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COALESCE(SUM(nao_lidas), 0) AS total FROM whatsapp_conversas").fetchone()
        return {"total_nao_lidas": int(row["total"]) if row else 0}
    finally:
        conn.close()


@router.get("/conversas/{conversa_id}")
def obter_conversa_api(
    conversa_id: int,
    marcar_lida: bool = Query(default=True),
    user: str = Depends(auth_required),
):
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    campos = {}
    if marcar_lida:
        campos["nao_lidas"] = 0
        conversa["nao_lidas"] = 0
    if user and user.strip() and not conversa.get("atendente_nome"):
        campos["atendente_nome"] = user.strip()
        conversa["atendente_nome"] = user.strip()
    if campos:
        repo.atualizar_conversa(conversa_id, **campos)
    return {
        "conversa": _enriquecer_conversa(conversa),
        "mensagens": repo.listar_mensagens(conversa_id),
        "resumo_cliente": contexto.montar_contexto_cliente(conversa.get("cliente_id")),
    }


@router.post("/conversas/marcar-todas-lidas")
def marcar_todas_conversas_lidas_api(user: str = Depends(auth_required)):
    """Marca todas as conversas do sistema como lidas (zera nao_lidas de todas as conversas)."""
    afetadas = repo.marcar_todas_conversas_como_lidas()
    return {"sucesso": True, "afetadas": afetadas}


@router.post("/conversas/{conversa_id}/marcar-nao-lida")
def marcar_conversa_nao_lida_api(conversa_id: int, user: str = Depends(auth_required)):
    """Marca manualmente a conversa como não lida (ping verde), como no WhatsApp."""
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    repo.atualizar_conversa(conversa_id, nao_lidas=1)
    return {"sucesso": True, "conversa_id": conversa_id, "nao_lidas": 1}


@router.post("/conversas/{conversa_id}/marcar-lida")
def marcar_conversa_lida_api(conversa_id: int, user: str = Depends(auth_required)):
    """Marca a conversa como lida (remove o ping verde)."""
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    repo.atualizar_conversa(conversa_id, nao_lidas=0)
    return {"sucesso": True, "conversa_id": conversa_id, "nao_lidas": 0}


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
    if payload.nao_lidas is not None:
        campos["nao_lidas"] = payload.nao_lidas
    if payload.atendente_nome is not None:
        campos["atendente_nome"] = payload.atendente_nome

    repo.atualizar_conversa(conversa_id, **campos)
    atualizada = repo.obter_conversa(conversa_id)
    return {"sucesso": True, "conversa": _enriquecer_conversa(atualizada)}


@router.post("/conversas/{conversa_id}/carregar-anteriores")
def carregar_mensagens_anteriores_api(conversa_id: int, user: str = Depends(auth_required)):
    """Solicita ao WhatsApp conectado (via ponte local) o carregamento de mensagens anteriores do chat."""
    conversa = repo.obter_conversa(conversa_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    mais_antiga = repo.obter_mensagem_mais_antiga(conversa_id)
    oldest_id = mais_antiga.get("id_externo") if mais_antiga else None
    oldest_from_me = mais_antiga.get("direcao") == repo.DIRECAO_SAIDA if mais_antiga else False
    oldest_ts = None
    if mais_antiga and mais_antiga.get("criada_em"):
        try:
            dt = datetime.strptime(mais_antiga["criada_em"], repo.FORMATO_DATA)
            oldest_ts = int(dt.timestamp())
        except Exception:
            oldest_ts = None

    tel = conversa.get("telefone") or ""
    resposta_bridge = bridge_manager.requisitar_historico_bridge(
        jid=tel,
        oldest_id=oldest_id,
        oldest_timestamp=oldest_ts,
        oldest_from_me=oldest_from_me,
        count=50,
    )
    return {
        "sucesso": bool(resposta_bridge.get("sucesso")),
        "solicitado": bool(resposta_bridge.get("solicitado")),
        "mensagem": resposta_bridge.get("mensagem") or resposta_bridge.get("erro") or "Histórico solicitado.",
        "conversa_id": conversa_id,
    }


@router.post("/conversas/manual")
def registrar_entrada_manual_api(payload: NovaConversaManualSchema, user: str = Depends(auth_required)):
    try:
        resultado = atendimento.registrar_mensagem_manual(
            telefone_bruto=payload.telefone or "",
            texto_bruto=payload.texto,
            nome_contato=payload.nome_contato or "",
            cliente_id=payload.cliente_id,
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


@router.post("/conversas/{conversa_id}/gerar-pedido")
def gerar_pedido_api(
    conversa_id: int,
    payload: Optional[GerarPedidoSchema] = None,
    user: str = Depends(auth_required),
):
    """
    Etapa 1: A IA analisa a conversa, cadastra o cliente (ou pergunta o nome no WhatsApp)
    e cria o pedido de venda com descrição e itens no sistema vinculado ao perfil do atendente logado.
    """
    try:
        atendente = (payload.atendente if (payload and payload.atendente) else user) or "Thaissa"
        resultado = atendimento.gerar_pedido_ia_conversa(conversa_id, usuario=atendente)
        return {"sucesso": True, **resultado}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/conversas/{conversa_id}/resumo-pedido")
def gerar_resumo_pedido_api(conversa_id: int, user: str = Depends(auth_required)):
    """
    Gera a Descrição do Pedido a partir da conversa com IA.
    Só é liberado DEPOIS que o pedido foi efetuado e o pagamento (50% ou 100%) foi registrado.
    """
    try:
        resumo = atendimento.gerar_resumo_descricao_pedido(conversa_id, salvar_no_pedido=True)
        return {"sucesso": True, **resumo}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/conversas/{conversa_id}/comprovante")
async def analisar_comprovante_api(
    conversa_id: int,
    arquivo: Optional[UploadFile] = File(default=None),
    legenda: str = Form(default=""),
    user: str = Depends(auth_required),
):
    """
    Etapa 2: Analisa uma imagem/comprovante enviada na conversa após solicitação de pagamento,
    marca automaticamente o pedido como 50% PAGO (ou PAGO 100%) e envia confirmação no WhatsApp.
    """
    try:
        img_bytes = None
        mime = "image/jpeg"
        nome_arq = "comprovante.jpg"
        if arquivo is not None:
            img_bytes = await arquivo.read()
            mime = arquivo.content_type or "image/jpeg"
            nome_arq = arquivo.filename or "comprovante.jpg"
        else:
            ult_msg = repo.obter_ultima_mensagem_midia(conversa_id, tipo="imagem")
            if ult_msg and ult_msg.get("midia_url"):
                caminho_local = ult_msg["midia_url"].lstrip("/")
                if os.path.exists(caminho_local):
                    try:
                        with open(caminho_local, "rb") as f:
                            img_bytes = f.read()
                        nome_arq = os.path.basename(caminho_local)
                    except OSError:
                        img_bytes = None

        resultado = atendimento.analisar_comprovante_e_atualizar_pedido(
            conversa_id=conversa_id,
            imagem_bytes=img_bytes,
            mime_type=mime,
            nome_arquivo=nome_arq,
            legenda=legenda,
        )
        if not resultado.get("atualizado"):
            raise HTTPException(status_code=400, detail=resultado.get("motivo") or "Comprovante não identificado.")
        return {"sucesso": True, **resultado}
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
            telefone_manual=payload.telefone or "",
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
            telefone_manual=payload.telefone or None,
            assumir_conversa=payload.assumir_conversa,
        )
        return {"sucesso": True, **resultado}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/conversas/{conversa_id}/enviar-imagem")
async def enviar_imagem_api(
    conversa_id: int,
    imagem: UploadFile = File(...),
    legenda: str = Form(default=""),
    user: str = Depends(auth_required),
):
    """Envia uma imagem pelo WhatsApp para o cliente da conversa selecionada."""
    try:
        corpo_img = await imagem.read()
        if not corpo_img:
            raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")
        if len(corpo_img) > 10_000_000:
            raise HTTPException(status_code=413, detail="A imagem excede o limite de 10MB.")

        resultado = atendimento.enviar_imagem(
            conversa_id=conversa_id,
            imagem_bytes=corpo_img,
            legenda=legenda,
            usuario=user or "Atendente",
            mime_type=imagem.content_type or "image/jpeg",
            nome_arquivo=imagem.filename or "imagem.jpg",
        )
        return {"sucesso": True, **resultado}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/conversas/{conversa_id}/enviar-arquivo")
async def enviar_arquivo_api(
    conversa_id: int,
    arquivo: UploadFile = File(...),
    legenda: str = Form(default=""),
    user: str = Depends(auth_required),
):
    """Envia um arquivo (documento, foto ou áudio) pelo WhatsApp para o cliente."""
    try:
        corpo = await arquivo.read()
        if not corpo:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
        if len(corpo) > 25_000_000:
            raise HTTPException(status_code=413, detail="O arquivo excede o limite de 25MB.")

        nome_arq = arquivo.filename or "arquivo.pdf"
        mime = arquivo.content_type or "application/pdf"
        tipo = "imagem" if mime.startswith("image/") else ("audio" if mime.startswith("audio/") else "documento")

        resultado = atendimento.enviar_arquivo(
            conversa_id=conversa_id,
            arquivo_bytes=corpo,
            nome_arquivo=nome_arq,
            legenda=legenda,
            usuario=user or "Atendente",
            mime_type=mime,
            tipo_midia=tipo,
        )
        return {"sucesso": True, **resultado}
    except atendimento.ErroAtendimento as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/mensagens/{mensagem_id}/carregar-midia")
def carregar_midia_mensagem_api(mensagem_id: int, user: str = Depends(auth_required)):
    """Tenta baixar e disponibilizar o arquivo/áudio de uma mensagem existente no sistema."""
    msg = repo.obter_mensagem_por_id(mensagem_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

    if msg.get("midia_url"):
        return {
            "sucesso": True,
            "midia_url": msg["midia_url"],
            "midia_tipo": msg.get("midia_tipo") or "arquivo",
            "ja_carregado": True,
        }

    id_ext = msg.get("id_externo")
    if not id_ext:
        raise HTTPException(status_code=400, detail="Esta mensagem não possui identificador no WhatsApp.")

    conv = repo.obter_conversa(msg["conversa_id"])
    link_web = link_whatsapp_web(conv.get("telefone") or "") if conv else "https://web.whatsapp.com"

    # 1. Tenta baixar via ponte usando o ID da mensagem
    resp_bridge = bridge_manager.baixar_midia_mensagem_bridge(id_ext)
    if resp_bridge.get("sucesso") and resp_bridge.get("midia_base64"):
        import base64
        corpo = base64.b64decode(resp_bridge["midia_base64"])
        tipo = resp_bridge.get("midia_tipo") or ("audio" if "audio" in (msg.get("texto") or "").lower() else "documento")
        nome = resp_bridge.get("nome_arquivo") or ("audio.ogg" if tipo == "audio" else "documento.pdf")
        mime = resp_bridge.get("mime_type") or ("audio/ogg" if tipo == "audio" else "application/pdf")
        url = atendimento.salvar_midia_whatsapp_bytes(corpo, nome, mime, "wa_in")
        if url:
            repo.atualizar_midia_mensagem(mensagem_id, url, tipo)
            return {
                "sucesso": True,
                "midia_url": url,
                "midia_tipo": tipo,
                "nome_arquivo": nome,
            }

    # 2. Se a mensagem não estava no cache da ponte, solicita o histórico da conversa ao WhatsApp
    if conv:
        tel = conv.get("telefone") or ""
        bridge_manager.requisitar_historico_bridge(jid=tel, oldest_id=id_ext, count=30)

    return {
        "sucesso": False,
        "solicitado": True,
        "mensagem": "Buscando arquivo no WhatsApp... Aguarde alguns instantes e tente novamente.",
        "link_web": link_web,
    }


# ---------------------------------------------------------------------------
# WEBHOOKS PÚBLICOS (EVOLUTION API + META WHATSAPP CLOUD API)
# ---------------------------------------------------------------------------
def _extrair_evento_evolution(dados: dict, aceitar_from_me: bool = False) -> tuple[str, str, str, str, bool] | None:
    """Extrai (telefone, texto, nome_contato, id_externo, from_me) do payload da Evolution API / Ponte Local."""
    bloco = dados.get("data") if isinstance(dados.get("data"), dict) else dados
    key = bloco.get("key") if isinstance(bloco.get("key"), dict) else {}
    from_me = bool(key.get("fromMe"))
    if from_me and not aceitar_from_me:
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
    return telefone, str(texto), nome, id_ext, from_me


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
    elif token_valido(token_header, bridge_manager.token_interno_bridge()):
        autenticado = True

    if not autenticado:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook não autorizado.")

    try:
        dados = json.loads(corpo.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido.") from None

    if not isinstance(dados, dict):
        return {"recebido": True, "processadas": 0}

    bloco_interno = dados.get("data") if isinstance(dados.get("data"), dict) else dados
    if bloco_interno.get("evento_tipo") == "ligacao":
        ev = _extrair_evento_evolution(dados)
        if ev:
            telefone, _, nome, id_ext, _ = ev
            reg_lig = atendimento.processar_ligacao_recebida(
                telefone,
                nome,
                id_ext or None,
                ja_respondida_pela_bridge=bool(bloco_interno.get("resposta_automatica_enviada")),
            )
            return {"recebido": True, "processadas": 1 if reg_lig else 0, "tipo": "ligacao"}

    # Sincronização em lote de conversas da ponte local
    if bloco_interno.get("evento_tipo") == "conversas_lote":
        chats = bloco_interno.get("chats") or []
        cadastradas = 0
        for c in chats:
            if not isinstance(c, dict):
                continue
            tel_bruto = str(c.get("jid") or "").split("@")[0].split(":")[0]
            nome = str(c.get("nome") or "")
            ts = c.get("timestamp")
            dt_str = None
            if ts and isinstance(ts, (int, float)) and ts > 1_000_000_000:
                try:
                    dt_str = datetime.fromtimestamp(float(ts)).strftime(repo.FORMATO_DATA)
                except Exception:
                    dt_str = None
            tel_norm, cid = atendimento._resolver_identificador_entrada(tel_bruto, nome)
            if tel_norm:
                repo.obter_ou_criar_conversa(tel_norm, nome_contato=nome, cliente_id=cid, ultima_mensagem_em=dt_str)
                cadastradas += 1
        return {"recebido": True, "conversas_cadastradas": cadastradas}

    # Sincronização em lote de mensagens da ponte local (alta velocidade)
    if bloco_interno.get("evento_tipo") == "mensagens_lote":
        items = bloco_interno.get("items") or []
        total_proc = 0
        comprovantes = []
        for item in items:
            if not isinstance(item, dict):
                continue
            ev = _extrair_evento_evolution({"data": item}, aceitar_from_me=True)
            if not ev:
                continue
            tel, txt, nm, idx, from_me = ev
            ts = item.get("messageTimestamp") or item.get("timestamp")
            reg = atendimento.processar_mensagem_recebida(
                telefone_bruto=tel,
                texto_bruto=txt,
                nome_contato=nm,
                id_externo=idx or None,
                from_me=from_me,
                midia_tipo=str(item.get("midia_tipo") or ""),
                midia_mime=str(item.get("midia_mime") or ""),
                midia_nome=str(item.get("midia_nome") or ""),
                midia_base64=str(item.get("midia_base64") or ""),
                timestamp_msg=ts,
            )
            if reg:
                total_proc += 1
                if reg.get("comprovante") and reg["comprovante"].get("atualizado"):
                    comprovantes.append(reg["comprovante"])
        return {"recebido": True, "processadas": total_proc, "comprovantes": comprovantes}

    eventos: list[tuple[str, str, str, str, bool]] = []
    if "entry" in dados or conf.provedor_solicitado == PROVEDOR_CLOUD:
        for tel, txt, nm, idx in _extrair_eventos_cloud(dados):
            eventos.append((tel, txt, nm, idx, False))
    if not eventos and ("data" in dados or "key" in dados or conf.provedor_solicitado == PROVEDOR_EVOLUTION):
        ev = _extrair_evento_evolution(dados, aceitar_from_me=bool(bloco_interno.get("evento_tipo") == "mensagem"))
        if ev:
            eventos.append(ev)

    processadas = 0
    comprovantes_processados = []
    ts_unico = bloco_interno.get("messageTimestamp") or bloco_interno.get("timestamp")
    for telefone, texto, nome, id_ext, from_me in eventos:
        reg = atendimento.processar_mensagem_recebida(
            telefone,
            texto,
            nome,
            id_ext or None,
            from_me=from_me,
            midia_tipo=str(bloco_interno.get("midia_tipo") or ""),
            midia_mime=str(bloco_interno.get("midia_mime") or ""),
            midia_nome=str(bloco_interno.get("midia_nome") or ""),
            midia_base64=str(bloco_interno.get("midia_base64") or ""),
            timestamp_msg=ts_unico,
        )
        if reg:
            processadas += 1
            if reg.get("comprovante") and reg["comprovante"].get("atualizado"):
                comprovantes_processados.append(reg["comprovante"])

    return {"recebido": True, "processadas": processadas, "comprovantes": comprovantes_processados}
