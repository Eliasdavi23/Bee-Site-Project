from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ConfigDict, Field
from services import pdf_service
from services.whatsapp import atendimento
from services.whatsapp.telefone import normalizar_telefone
from services.whatsapp.mensagens import formatar_moeda
from pydantic import BaseModel

from config.database import get_connection
from routes.auth_routes import auth_required
from services.db_utils import anexar_itens_em_lote, listar_imagens_pedido_db, listar_itens_pedido_db
from services.orcamento_services import (
    _salvar_itens_orcamento,
    atualizar_orcamento_db,
    buscar_orcamento_por_id_db,
    calcular_totais_orcamento,
)

router = APIRouter(prefix="/api/orcamentos", tags=["Orçamentos"])


class ItemOrcamentoSchema(BaseModel):
    produto_id: int
    quantidade: float | str = 1.0
    preco_unitario: float | str = 0.0
    observacao: Optional[str] = ""


class OrcamentoDadosSchema(BaseModel):
    cliente_id: int
    usuario: Optional[str] = "Sistema"
    atendente: Optional[str] = "Sistema"
    status_producao: Optional[str] = "ORCAMENTO"
    desconto: Optional[float | str] = 0.0
    observacao: Optional[str] = ""
    itens: List[ItemOrcamentoSchema]


class EnviarOrcamentoWhatsAppSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    telefone: Optional[str] = Field(default="", max_length=40)
    mensagem: Optional[str] = Field(default="", max_length=1500)


class EnviarOrcamentoEmailSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: Optional[str] = Field(default="", max_length=120)
    assunto: Optional[str] = Field(default="", max_length=200)
    mensagem: Optional[str] = Field(default="", max_length=2000)


class OrcamentoCreateSchema(BaseModel):
    dados: OrcamentoDadosSchema


class OrcamentoUpdateSchema(BaseModel):
    dados: OrcamentoDadosSchema


@router.get("")
def listar_orcamentos(user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                p.*,
                c.nome AS cliente_nome,
                c.documento AS cliente_documento,
                c.telefone AS cliente_telefone,
                c.email AS cliente_email,
                c.endereco AS cliente_endereco
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.tipo = 'ORCAMENTO'
            ORDER BY p.id DESC
            """
        )
        orcamentos = [dict(row) for row in cursor.fetchall()]
        return anexar_itens_em_lote(cursor, orcamentos)
    except Exception as e:
        print(f"Erro ao listar orçamentos: {e}")
        return []
    finally:
        conn.close()


@router.get("/{orcamento_id}")
def obter_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    orcamento = buscar_orcamento_por_id_db(orcamento_id)
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    return orcamento


@router.get("/{orcamento_id}/itens")
def listar_itens_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    return listar_itens_pedido_db(orcamento_id)


@router.get("/{orcamento_id}/imagens")
def listar_imagens_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    return listar_imagens_pedido_db(orcamento_id)


@router.post("")
async def criar_orcamento(payload: OrcamentoCreateSchema, user: str = Depends(auth_required)):
    dados_orcamento = payload.dados
    if not dados_orcamento.itens:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um produto ao orçamento.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        desconto_val, valor_total_liquido = calcular_totais_orcamento(
            dados_orcamento.itens, dados_orcamento.desconto
        )
        usuario_responsavel = (dados_orcamento.usuario or dados_orcamento.atendente or user or "Sistema").strip()

        cursor.execute(
            """
            INSERT INTO pedidos (
                cliente_id, valor_total, valor_pago, desconto,
                status_producao, status_pagamento, forma_pagamento,
                observacao, data, usuario_nome, tipo
            )
            VALUES (?, ?, 0.0, ?, 'PENDENTE', 'PENDENTE', '', ?, ?, ?, 'ORCAMENTO')
            """,
            (
                dados_orcamento.cliente_id,
                valor_total_liquido,
                desconto_val,
                (dados_orcamento.observacao or "").strip(),
                data_atual,
                usuario_responsavel,
            ),
        )
        orcamento_id = cursor.lastrowid
        _salvar_itens_orcamento(cursor, orcamento_id, dados_orcamento.itens)
        conn.commit()
        return {"sucesso": True, "mensagem": "Orçamento criado com sucesso!", "id": orcamento_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar orçamento: {str(e)}")
    finally:
        conn.close()


@router.post("/{orcamento_id}/converter-venda")
def converter_orcamento_em_venda(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, status_producao FROM pedidos WHERE id = ?", (orcamento_id,))
        orcamento = cursor.fetchone()
        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        st_prod = (orcamento["status_producao"] or "PENDENTE").upper()
        if st_prod in ("ORCAMENTO", "ORÇAMENTO", ""):
            st_prod = "PENDENTE"

        cursor.execute("UPDATE pedidos SET tipo = 'VENDA', status_producao = ? WHERE id = ?", (st_prod, orcamento_id))
        conn.commit()
        return {"sucesso": True, "mensagem": "Orçamento aprovado e convertido em venda com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.put("/{orcamento_id}")
def atualizar_orcamento(orcamento_id: int, payload: OrcamentoUpdateSchema, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM pedidos WHERE id = ? AND tipo = 'ORCAMENTO'", (orcamento_id,))
        existe = cursor.fetchone()
    finally:
        conn.close()

    if not existe:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado ou já convertido em venda.")

    dados = payload.dados
    usuario_responsavel = (dados.usuario or dados.atendente or user or "Sistema").strip()
    try:
        atualizar_orcamento_db(orcamento_id, dados, usuario_responsavel)
        return {"sucesso": True, "mensagem": f"Orçamento #{orcamento_id} atualizado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar orçamento: {str(e)}")


@router.delete("/{orcamento_id}")
def excluir_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))
        cursor.execute("DELETE FROM pedido_imagens WHERE pedido_id = ?", (orcamento_id,))
        cursor.execute("DELETE FROM pedidos WHERE id = ? AND tipo = 'ORCAMENTO'", (orcamento_id,))
        conn.commit()
        return {"sucesso": True, "mensagem": "Orçamento excluído com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/{orcamento_id}/pdf")
def baixar_orcamento_pdf(orcamento_id: int, user: str = Depends(auth_required)):
    """Gera e retorna o PDF oficial do orçamento para visualização ou download."""
    orcamento = buscar_orcamento_por_id_db(orcamento_id)
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    try:
        pdf_bytes = pdf_service.gerar_pdf_orcamento(orcamento)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Orcamento_{orcamento_id}.pdf"'},
    )


@router.post("/{orcamento_id}/enviar-whatsapp")
def enviar_orcamento_whatsapp_api(
    orcamento_id: int,
    payload: Optional[EnviarOrcamentoWhatsAppSchema] = None,
    user: str = Depends(auth_required),
):
    """Gera o PDF do orçamento e o envia diretamente pelo WhatsApp para o cliente."""
    orcamento = buscar_orcamento_por_id_db(orcamento_id)
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    tel_bruto = (payload.telefone if payload and payload.telefone else "") or orcamento.get("cliente_telefone") or ""
    telefone = normalizar_telefone(tel_bruto, aceitar_sem_ddd=True)
    if not telefone:
        raise HTTPException(
            status_code=400,
            detail="O cliente não possui um telefone de WhatsApp válido cadastrado. Informe um número com DDD.",
        )

    try:
        pdf_bytes = pdf_service.gerar_pdf_orcamento(orcamento)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if payload and payload.mensagem and payload.mensagem.strip():
        texto_envio = payload.mensagem.strip()
    else:
        cli_nome = (orcamento.get("cliente_nome") or "Cliente").strip()
        total_fmt = formatar_moeda(orcamento.get("valor_total"))
        dados_emp = repo.dados_empresa() if hasattr(repo, "dados_empresa") else {}
        nome_emp_wa = (dados_emp.get("nome_empresa") or "").strip() or "BEE Gráfica"
        texto_envio = (
            f"*Orçamento #{orcamento_id} - {nome_emp_wa}*\n\n"
            f"Olá, {cli_nome}! Segue em anexo a sua proposta comercial em PDF no valor total de {total_fmt}.\n\n"
            f"Qualquer dúvida sobre acabamento ou prazos, estamos à disposição por aqui!"
        )

    res = atendimento.enviar_arquivo(
        arquivo_bytes=pdf_bytes,
        nome_arquivo=f"Orcamento_{orcamento_id}.pdf",
        legenda=texto_envio,
        usuario=user or "Atendente",
        mime_type="application/pdf",
        tipo_midia="documento",
        pedido_id=orcamento_id,
        cliente_id=orcamento.get("cliente_id"),
        telefone_manual=telefone,
        raise_on_error=False,
    )

    return {
        "sucesso": True,
        "enviado": bool(res.get("enviado")),
        "mensagem": "Orçamento em PDF enviado com sucesso pelo WhatsApp!" if res.get("enviado") else (res.get("erro") or "PDF gerado com sucesso. WhatsApp desconectado via QR Code no momento."),
        "midia_url": res.get("midia_url"),
        "link_web": res.get("link_web"),
        "telefone": res.get("telefone"),
        "orcamento_id": orcamento_id,
        "conversa_id": res.get("conversa_id"),
    }


@router.post("/{orcamento_id}/enviar-email")
def enviar_orcamento_email_api(
    orcamento_id: int,
    payload: Optional[EnviarOrcamentoEmailSchema] = None,
    user: str = Depends(auth_required),
):
    """Gera o PDF do orçamento e o dispara como anexo de e-mail para o cliente."""
    orcamento = buscar_orcamento_por_id_db(orcamento_id)
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    dest_email = (payload.email if payload and payload.email else "") or orcamento.get("cliente_email") or ""
    if not dest_email or "@" not in dest_email:
        raise HTTPException(status_code=400, detail="E-mail de destinatário inválido ou não informado no cadastro do cliente.")

    try:
        pdf_bytes = pdf_service.gerar_pdf_orcamento(orcamento)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    import os, smtplib
    from email.message import EmailMessage

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_sender = os.getenv("SMTP_FROM", smtp_user or "orcamentos@beegrafica.local")

    if not smtp_host:
        url_pdf, _ = pdf_service.salvar_pdf_orcamento_disco(orcamento)
        return {
            "sucesso": False,
            "configurado": False,
            "mensagem": "Servidor SMTP não configurado nas variáveis de ambiente (.env). O PDF foi gerado e salvo para download local.",
            "pdf_url": url_pdf,
            "email_destinatario": dest_email,
        }

    try:
        msg = EmailMessage()
        msg["Subject"] = (payload.assunto if payload and payload.assunto else "") or f"Orçamento #{orcamento_id} - BEE Gráfica"
        msg["From"] = smtp_sender
        msg["To"] = dest_email

        corpo = (payload.mensagem if payload and payload.mensagem else "") or (
            f"Olá, {orcamento.get('cliente_nome', 'Cliente')}!\n\n"
            f"Segue em anexo a sua proposta comercial referente ao Orçamento #{orcamento_id}.\n\n"
            f"Atenciosamente,\nBee Gráfica Digital"
        )
        msg.set_content(corpo)
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"Orcamento_{orcamento_id}.pdf")

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)

        return {
            "sucesso": True,
            "mensagem": f"Orçamento #{orcamento_id} enviado por e-mail com sucesso para {dest_email}!",
            "email_destinatario": dest_email,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao disparar e-mail: {str(exc)}")
