"""
Geração de mensagens prontas (com IA ou modelo fixo) para Pedidos, Orçamentos e Clientes,
além do disparo automático quando o status de produção de um pedido muda.
"""
import logging

from services import ia_service
from services.whatsapp import atendimento, contexto
from services.whatsapp import repositorio as repo
from services.whatsapp.mensagens import (
    normalizar_status_producao,
    STATUS_AVISAVEIS,
    TIPOS_MENSAGEM,
    msg_cobranca,
    msg_orcamento,
    msg_saudacao,
    msg_status_pedido,
)
from services.whatsapp.seguranca import limpar_texto
from services.whatsapp.telefone import formatar_exibicao, link_whatsapp, link_whatsapp_web, normalizar_telefone

logger = logging.getLogger("uvicorn.error")

INSTRUCAO_REFINAMENTO = """Você redige mensagens curtas de WhatsApp para clientes de uma gráfica ({empresa}).
Regras obrigatórias:
1. Reescreva a MENSAGEM BASE de forma simpática, clara e natural para WhatsApp (máximo 6 linhas).
2. Mantenha EXATAMENTE os números de pedido/orçamento, quantidades, itens e valores em R$. Nunca altere valores nem invente descontos ou prazos.
3. Devolva apenas o texto final da mensagem, sem aspas e sem explicações."""


def _refinar_com_ia(texto_base: str, instrucao_extra: str, empresa: dict) -> tuple[str, str]:
    """Tenta polir o texto com a IA; se a IA não estiver ativa, devolve o texto_base intacto."""
    prompt = f"MENSAGEM BASE:\n{texto_base}"
    if instrucao_extra:
        prompt += f"\n\nOBSERVAÇÃO DO ATENDENTE (incorporar sem mudar valores):\n{instrucao_extra[:300]}"
    try:
        refinado = ia_service.gerar_texto(
            prompt,
            INSTRUCAO_REFINAMENTO.format(empresa=empresa.get("nome_empresa") or "Gráfica"),
            max_tokens=450,
        )
        limpo = limpar_texto(refinado, atendimento.LIMITE_TEXTO_ENVIO)
        if limpo:
            return limpo, "ia"
    except ia_service.IAIndisponivel:
        pass
    return texto_base, "modelo"


def gerar_rascunho(
    tipo: str,
    pedido_id: int | None = None,
    cliente_id: int | None = None,
    telefone_manual: str = "",
    usar_ia: bool = True,
    instrucao_extra: str = "",
) -> dict:
    """
    Prepara o texto e os dados do destinatário para o modal de WhatsApp
    nas telas de Pedidos, Orçamentos, Clientes e Atendimento.
    """
    tipo = (tipo or "status_pedido").strip().lower()
    if tipo not in TIPOS_MENSAGEM:
        raise atendimento.ErroAtendimento("Tipo de mensagem inválido.")

    empresa = repo.dados_empresa()
    nome_cliente = ""
    telefone_bruto = (telefone_manual or "").strip()

    if tipo in ("status_pedido", "cobranca", "orcamento"):
        if not pedido_id:
            raise atendimento.ErroAtendimento("Selecione um pedido ou orçamento.")
        registro = contexto.obter_pedido_completo(pedido_id)
        if not registro:
            raise atendimento.ErroAtendimento("Registro não encontrado.")
        nome_cliente = registro.get("cliente_nome") or "Cliente"
        telefone_bruto = telefone_bruto or (registro.get("cliente_telefone") or "")
        cliente_id = registro.get("cliente_id")

        if tipo == "cobranca":
            texto_base = msg_cobranca(registro, empresa)
        elif tipo == "orcamento" or str(registro.get("tipo") or "").upper() == "ORCAMENTO":
            texto_base = msg_orcamento(registro, empresa)
            tipo = "orcamento"
        else:
            texto_base = msg_status_pedido(registro, empresa)
    else:
        if pedido_id and not cliente_id:
            registro = contexto.obter_pedido_completo(pedido_id)
            cliente_id = registro.get("cliente_id") if registro else None
        if cliente_id:
            cliente = contexto.obter_cliente(cliente_id)
            if not cliente:
                raise atendimento.ErroAtendimento("Cliente não encontrado.")
            nome_cliente = cliente.get("nome") or "Cliente"
            telefone_bruto = telefone_bruto or (cliente.get("telefone") or "")
            texto_base = msg_saudacao(cliente, empresa)
        else:
            nome_cliente = "Contato WhatsApp"
            texto_base = msg_saudacao({"nome": ""}, empresa)

    telefone = normalizar_telefone(telefone_bruto, aceitar_sem_ddd=True)
    origem = "modelo"
    texto_final = texto_base
    if usar_ia:
        texto_final, origem = _refinar_com_ia(texto_base, limpar_texto(instrucao_extra, 300), empresa)

    return {
        "tipo": tipo,
        "titulo_tipo": TIPOS_MENSAGEM[tipo],
        "pedido_id": pedido_id,
        "cliente_id": cliente_id,
        "cliente_nome": nome_cliente,
        "telefone_bruto": telefone_bruto,
        "telefone_valido": bool(telefone),
        "telefone_exibicao": formatar_exibicao(telefone or telefone_bruto) or "Sem telefone",
        "texto": texto_final,
        "origem": origem,
        "link": link_whatsapp(telefone, texto_final) if telefone else "",
        "link_web": link_whatsapp_web(telefone, texto_final) if telefone else "",
    }


def notificar_mudanca_status(
    pedido_id: int,
    status_anterior: str | None,
    novo_status: str | None,
    usuario: str = "Sistema",
) -> dict | None:
    """
    Chamado quando um pedido é salvo ou tem seu status alterado.
    - Só dispara se o status realmente mudou para um status relevante.
    - Se o provedor for automático (Evolution/Cloud), envia em segundo plano e registra na conversa.
    - No modo link (híbrido), devolve os links wa.me e WhatsApp Web prontos.
    """
    antigo = normalizar_status_producao(status_anterior) if status_anterior else ""
    novo = normalizar_status_producao(novo_status) if novo_status else ""
    if not novo or novo == antigo or novo not in STATUS_AVISAVEIS:
        return None

    if not repo.ler_config_bool(atendimento.CHAVE_AVISO_STATUS, padrao=True):
        return None

    pedido = contexto.obter_pedido_completo(pedido_id)
    if not pedido or str(pedido.get("tipo") or "VENDA").upper() == "ORCAMENTO":
        return None

    telefone = normalizar_telefone(pedido.get("cliente_telefone"), aceitar_sem_ddd=True)
    if not telefone:
        return None

    empresa = repo.dados_empresa()
    texto = msg_status_pedido(pedido, empresa)

    try:
        resultado = atendimento.enviar_mensagem(
            texto_bruto=texto,
            usuario=usuario or "Sistema",
            pedido_id=pedido_id,
            autor=repo.AUTOR_SISTEMA,
            assumir_conversa=False,
        )
        resultado["texto"] = texto
        resultado["cliente_nome"] = pedido.get("cliente_nome") or "Cliente"
        resultado["novo_status"] = novo
        return resultado
    except Exception as exc:
        logger.warning("Não foi possível preparar aviso de status do pedido #%s: %s", pedido_id, exc)
        return {
            "enviado": False,
            "modo": "link",
            "link": link_whatsapp(telefone, texto),
            "link_web": link_whatsapp_web(telefone, texto),
            "texto": texto,
            "cliente_nome": pedido.get("cliente_nome") or "Cliente",
            "telefone_exibicao": formatar_exibicao(telefone),
            "novo_status": novo,
        }
