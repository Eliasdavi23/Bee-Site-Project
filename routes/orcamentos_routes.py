import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from config.database import get_connection
from routes.auth_routes import auth_required
from services.orcamento_services import buscar_orcamento_por_id_db, atualizar_orcamento_db

router = APIRouter(prefix="/api/orcamentos", tags=["Orçamentos"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ItemOrcamentoSchema(BaseModel):
    produto_id: int
    quantidade: float = 1.0
    preco_unitario: float = 0.0
    observacao: Optional[str] = ""


class OrcamentoDadosSchema(BaseModel):
    cliente_id: int
    usuario: Optional[str] = "Sistema"
    atendente: Optional[str] = "Sistema"
    status_producao: Optional[str] = "ORCAMENTO"
    desconto: Optional[float] = 0.0
    observacao: Optional[str] = ""
    itens: List[ItemOrcamentoSchema]


class OrcamentoCreateSchema(BaseModel):
    dados: OrcamentoDadosSchema


class OrcamentoUpdateSchema(BaseModel):
    dados: OrcamentoDadosSchema


@router.get("")
def listar_orcamentos(user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
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
        """)
        orcamentos = [dict(row) for row in cursor.fetchall()]

        if orcamentos:
            orc_ids = [o["id"] for o in orcamentos]
            placeholders = ",".join(["?"] * len(orc_ids))
            cursor.execute(
                f"SELECT * FROM itens_pedido WHERE pedido_id IN ({placeholders}) ORDER BY id ASC",
                tuple(orc_ids)
            )
            itens_por_orc = {}
            for row in cursor.fetchall():
                d = dict(row)
                d["observacao"] = d.get("observacao") or ""
                itens_por_orc.setdefault(d["pedido_id"], []).append(d)
            for o in orcamentos:
                o["itens"] = itens_por_orc.get(o["id"], [])

        return orcamentos
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
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC", (orcamento_id,))
        itens = []
        for row in cursor.fetchall():
            d = dict(row)
            d["observacao"] = d.get("observacao") or ""
            itens.append(d)
        return itens
    finally:
        conn.close()


@router.get("/{orcamento_id}/imagens")
def listar_imagens_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (orcamento_id,))
        imagens = [row["caminho_arquivo"] for row in cursor.fetchall()]
        return imagens
    finally:
        conn.close()


@router.post("")
async def criar_orcamento(
    payload: OrcamentoCreateSchema,
    user: str = Depends(auth_required)
):
    dados_orcamento = payload.dados
    if not dados_orcamento.itens:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um produto ao orçamento.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subtotal_geral = sum(max(1.0, float(item.quantidade or 1)) * max(0.0, float(item.preco_unitario or 0)) for item in dados_orcamento.itens)
        desconto_val = max(0.0, float(dados_orcamento.desconto or 0.0))
        valor_total_liquido = round(max(0.0, subtotal_geral - desconto_val), 2)

        usuario_responsavel = (dados_orcamento.usuario or dados_orcamento.atendente or user or "Sistema").strip()

        cursor.execute("""
            INSERT INTO pedidos (
                cliente_id, valor_total, valor_pago, desconto,
                status_producao, status_pagamento, forma_pagamento,
                observacao, data, usuario_nome, tipo
            )
            VALUES (?, ?, 0.0, ?, 'PENDENTE', 'PENDENTE', '', ?, ?, ?, 'ORCAMENTO')
        """, (
            dados_orcamento.cliente_id,
            valor_total_liquido,
            desconto_val,
            (dados_orcamento.observacao or "").strip(),
            data_atual,
            usuario_responsavel
        ))

        orcamento_id = cursor.lastrowid

        for item in dados_orcamento.itens:
            qtd = max(1, int(round(float(item.quantidade or 1))))
            preco_unit = max(0.0, float(item.preco_unitario or 0.0))
            subtotal_item = round(qtd * preco_unit, 2)
            obs_item = (item.observacao or "").strip()

            cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item.produto_id,))
            prod_db = cursor.fetchone()
            nome_prod = prod_db["nome"] if prod_db else "Produto"

            cursor.execute("""
                INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal, observacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                orcamento_id,
                item.produto_id,
                nome_prod,
                qtd,
                preco_unit,
                subtotal_item,
                obs_item
            ))

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

        cursor.execute("""
            UPDATE pedidos 
            SET tipo = 'VENDA', status_producao = ?
            WHERE id = ?
        """, (st_prod, orcamento_id))

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
def atualizar_orcamento(
    orcamento_id: int,
    payload: OrcamentoUpdateSchema,
    user: str = Depends(auth_required)
):
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
