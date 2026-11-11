from services.whatsapp.mensagens import normalizar_status_producao
import json
import os
import shutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from config.database import get_connection
from routes.auth_routes import auth_required
from services.db_utils import (
    anexar_itens_em_lote,
    listar_imagens_pedido_db,
    listar_itens_pedido_db,
    parse_decimal,
    remover_arquivo_local,
)
from services.whatsapp.notificacoes import notificar_mudanca_status

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class StatusUpdateSchema(BaseModel):
    status_producao: Optional[str] = None
    status_pagamento: Optional[str] = None


def _processar_itens_entrada(produtos: list[dict]) -> tuple[list[dict], float]:
    itens_processados = []
    subtotal_calculado = 0.0
    for item in produtos:
        try:
            prod_id = int(item.get("produto_id")) if item.get("produto_id") else None
        except (TypeError, ValueError):
            prod_id = None

        qtd = max(0.01, round(parse_decimal(item.get("quantidade"), 1.0), 4))
        preco_unit = max(0.0, round(parse_decimal(item.get("preco_unitario"), 0.0), 4))
        subtotal_item = round(qtd * preco_unit, 2)
        subtotal_calculado += subtotal_item

        itens_processados.append({
            "produto_id": prod_id,
            "nome_produto": str(item.get("nome_produto") or "").strip(),
            "quantidade": qtd,
            "preco_unitario": preco_unit,
            "subtotal": subtotal_item,
            "observacao": str(item.get("observacao") or "").strip(),
        })
    return itens_processados, subtotal_calculado


@router.get("")
def listar_pedidos(user: str = Depends(auth_required)):
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
            WHERE p.tipo = 'VENDA' OR p.tipo IS NULL OR p.tipo = ''
            ORDER BY p.id DESC
            """
        )
        pedidos = [dict(row) for row in cursor.fetchall()]
        return anexar_itens_em_lote(cursor, pedidos)
    except Exception as e:
        print(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()


@router.get("/{pedido_id}")
def obter_pedido(pedido_id: int, user: str = Depends(auth_required)):
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
            WHERE p.id = ?
            """,
            (pedido_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")
        pedido = dict(row)
        cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC", (pedido_id,))
        pedido["itens"] = [dict(r) for r in cursor.fetchall()]
        return pedido
    finally:
        conn.close()


@router.get("/{pedido_id}/itens")
def listar_itens_pedido(pedido_id: int, user: str = Depends(auth_required)):
    try:
        return listar_itens_pedido_db(pedido_id)
    except Exception as e:
        print(f"Erro ao listar itens do pedido #{pedido_id}: {e}")
        return []


@router.get("/{pedido_id}/imagens")
def listar_imagens_pedido(pedido_id: int, user: str = Depends(auth_required)):
    try:
        return listar_imagens_pedido_db(pedido_id)
    except Exception as e:
        print(f"Erro ao listar imagens do pedido #{pedido_id}: {e}")
        return []


@router.post("")
async def salvar_pedido(
    dados: str = Form(...),
    imagens: List[UploadFile] = File([]),
    user: str = Depends(auth_required),
):
    try:
        payload = json.loads(dados)
    except Exception:
        return {"sucesso": False, "erro": "Dados do pedido inválidos (JSON malformado)."}

    pedido_id = payload.get("id")
    cliente_id = payload.get("cliente_id")
    if not cliente_id:
        return {"sucesso": False, "erro": "Selecione um cliente válido para o pedido."}

    produtos = payload.get("produtos") or []
    if not produtos:
        return {"sucesso": False, "erro": "Adicione pelo menos um item ao pedido."}

    desconto = max(0.0, round(parse_decimal(payload.get("desconto"), 0.0), 2))
    valor_pago = max(0.0, round(parse_decimal(payload.get("valor_pago"), 0.0), 2))
    status_producao = normalizar_status_producao(payload.get("status_producao"))
    status_pagamento = str(payload.get("status_pagamento") or "PENDENTE").strip().upper()
    forma_pagamento = str(payload.get("forma_pagamento") or "").strip()
    observacao = str(payload.get("observacao") or "").strip()
    usuario_nome = str(payload.get("usuario_nome") or user or "Sistema").strip()
    imagens_mantidas = payload.get("imagens_mantidas") or []

    itens_processados, subtotal_calculado = _processar_itens_entrada(produtos)
    valor_total = round(max(0.0, subtotal_calculado - desconto), 2)
    if status_pagamento == "PAGO" and valor_pago == 0.0 and valor_total > 0.0:
        valor_pago = valor_total

    conn = get_connection()
    try:
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_anterior = None

        if pedido_id:
            row_ant = cursor.execute("SELECT status_producao FROM pedidos WHERE id = ?", (int(pedido_id),)).fetchone()
            status_anterior = row_ant["status_producao"] if row_ant else None

            cursor.execute(
                """
                UPDATE pedidos
                SET cliente_id = ?, valor_total = ?, valor_pago = ?, desconto = ?,
                    status_producao = ?, status_pagamento = ?, forma_pagamento = ?,
                    observacao = ?, usuario_nome = ?
                WHERE id = ?
                """,
                (
                    int(cliente_id), valor_total, valor_pago, desconto,
                    status_producao, status_pagamento, forma_pagamento,
                    observacao, usuario_nome, int(pedido_id),
                ),
            )
            cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (int(pedido_id),))

            cursor.execute("SELECT id, caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (int(pedido_id),))
            for img_antiga in cursor.fetchall():
                if img_antiga["caminho_arquivo"] not in imagens_mantidas:
                    remover_arquivo_local(img_antiga["caminho_arquivo"])
                    cursor.execute("DELETE FROM pedido_imagens WHERE id = ?", (img_antiga["id"],))
        else:
            cursor.execute(
                """
                INSERT INTO pedidos (
                    cliente_id, valor_total, valor_pago, desconto,
                    status_producao, status_pagamento, forma_pagamento,
                    observacao, data, usuario_nome, tipo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VENDA')
                """,
                (
                    int(cliente_id), valor_total, valor_pago, desconto,
                    status_producao, status_pagamento, forma_pagamento,
                    observacao, data_atual, usuario_nome,
                ),
            )
            pedido_id = cursor.lastrowid

        for item in itens_processados:
            nome_prod = item["nome_produto"]
            if not nome_prod and item["produto_id"]:
                cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item["produto_id"],))
                row_prod = cursor.fetchone()
                nome_prod = row_prod["nome"] if row_prod else "Produto"
            if not nome_prod:
                nome_prod = "Produto / Serviço"

            cursor.execute(
                """
                INSERT INTO itens_pedido (
                    pedido_id, produto_id, nome_produto, quantidade,
                    preco_unitario, subtotal, observacao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(pedido_id),
                    item["produto_id"],
                    nome_prod,
                    item["quantidade"],
                    item["preco_unitario"],
                    item["subtotal"],
                    item["observacao"],
                ),
            )

        for img in imagens:
            if img and img.filename:
                file_extension = os.path.splitext(img.filename)[1]
                unique_filename = (
                    f"pedido_{pedido_id}_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}{file_extension}"
                )
                file_path = os.path.join(UPLOAD_DIR, unique_filename).replace("\\", "/")
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(img.file, buffer)
                cursor.execute(
                    "INSERT INTO pedido_imagens (pedido_id, caminho_arquivo) VALUES (?, ?)",
                    (int(pedido_id), f"/{file_path}"),
                )

        conn.commit()
        notificacao = notificar_mudanca_status(int(pedido_id), status_anterior, status_producao, usuario=usuario_nome)
        return {
            "sucesso": True,
            "mensagem": "Pedido salvo com sucesso!",
            "id": pedido_id,
            "whatsapp_notificacao": notificacao,
        }
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar pedido: {e}")
        return {"sucesso": False, "erro": f"Erro interno ao salvar pedido: {str(e)}"}
    finally:
        conn.close()


@router.patch("/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, payload: StatusUpdateSchema, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, valor_total, valor_pago, status_producao FROM pedidos WHERE id = ?", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado.")

        status_anterior = pedido["status_producao"]
        if payload.status_producao:
            cursor.execute(
                "UPDATE pedidos SET status_producao = ? WHERE id = ?",
                (normalizar_status_producao(payload.status_producao), pedido_id),
            )
        if payload.status_pagamento:
            novo_st_pag = payload.status_pagamento.strip().upper()
            if novo_st_pag == "PAGO":
                cursor.execute(
                    "UPDATE pedidos SET status_pagamento = ?, valor_pago = valor_total WHERE id = ?",
                    (novo_st_pag, pedido_id),
                )
            elif novo_st_pag == "PENDENTE":
                cursor.execute(
                    "UPDATE pedidos SET status_pagamento = ?, valor_pago = 0.0 WHERE id = ?",
                    (novo_st_pag, pedido_id),
                )
            else:
                cursor.execute(
                    "UPDATE pedidos SET status_pagamento = ? WHERE id = ?",
                    (novo_st_pag, pedido_id),
                )
        conn.commit()
        notificacao = (
            notificar_mudanca_status(pedido_id, status_anterior, payload.status_producao, usuario=user or "Sistema")
            if payload.status_producao else None
        )
        return {"sucesso": True, "whatsapp_notificacao": notificacao}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/imagens/{imagem_id}")
def deletar_imagem_pedido(imagem_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pedido_imagens WHERE id = ?", (imagem_id,))
        img = cursor.fetchone()
        if not img:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")

        remover_arquivo_local(img["caminho_arquivo"])
        cursor.execute("DELETE FROM pedido_imagens WHERE id = ?", (imagem_id,))
        conn.commit()
        return {"sucesso": True, "mensagem": "Imagem removida com sucesso!"}
    finally:
        conn.close()


@router.delete("/{pedido_id}")
def deletar_pedido(pedido_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
        for img in cursor.fetchall():
            remover_arquivo_local(img["caminho_arquivo"])

        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
        cursor.execute("DELETE FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
        return {"sucesso": True, "mensagem": "Pedido excluído com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
