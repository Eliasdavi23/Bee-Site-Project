import os
import json
import shutil
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

class OrcamentoDadosSchema(BaseModel):
    cliente_id: int
    usuario: Optional[str] = "Sistema"
    atendente: Optional[str] = "Sistema"
    desconto: Optional[float] = 0.0
    observacao: Optional[str] = ""
    itens: List[ItemOrcamentoSchema]

class OrcamentoCreateSchema(BaseModel):
    dados: OrcamentoDadosSchema

class OrcamentoUpdateSchema(BaseModel):
    dados: OrcamentoDadosSchema

# ROTAS

@router.get("")
def listar_orcamentos(user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, c.nome as cliente_nome 
        FROM pedidos p 
        LEFT JOIN clientes c ON p.cliente_id = c.id 
        WHERE p.tipo = 'ORCAMENTO'
        ORDER BY p.id DESC
    """)
    orcamentos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orcamentos

@router.get("/{orcamento_id}")
def obter_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    orcamento = buscar_orcamento_por_id_db(orcamento_id)
    if not orcamento:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    return orcamento

@router.get("/{orcamento_id}/itens")
def listar_itens_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (orcamento_id,))
    itens = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return itens

@router.get("/{orcamento_id}/imagens")
def listar_imagens_orcamento(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (orcamento_id,))
    imagens = [row["caminho_arquivo"] for row in cursor.fetchall()]
    conn.close()
    return imagens

@router.post("")
async def criar_orcamento(
    payload: OrcamentoCreateSchema,
    user: str = Depends(auth_required)
):
    conn = get_connection()
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dados_orcamento = payload.dados

    subtotal_geral = sum(item.quantidade * item.preco_unitario for item in dados_orcamento.itens)
    valor_total_liquido = subtotal_geral - (dados_orcamento.desconto or 0.0)
    if valor_total_liquido < 0:
        valor_total_liquido = 0.0

    usuario_responsavel = dados_orcamento.usuario or dados_orcamento.atendente or "Sistema"

    cursor.execute("""
        INSERT INTO pedidos (cliente_id, valor_total, valor_pago, desconto, status_producao, status_pagamento, forma_pagamento, observacao, data, usuario_nome, tipo)
        VALUES (?, ?, 0.0, ?, 'PENDENTE', 'PENDENTE', '', ?, ?, ?, 'ORCAMENTO')
    """, (
        dados_orcamento.cliente_id, 
        valor_total_liquido, 
        dados_orcamento.desconto, 
        dados_orcamento.observacao, 
        data_atual, 
        usuario_responsavel
    ))
    
    orcamento_id = cursor.lastrowid

    for item in dados_orcamento.itens:
        subtotal_item = item.quantidade * item.preco_unitario
        
        cursor.execute("SELECT nome FROM produtos WHERE id = ?", (item.produto_id,))
        prod_db = cursor.fetchone()
        nome_prod = prod_db["nome"] if prod_db else "Produto"

        cursor.execute("""
            INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            orcamento_id, 
            item.produto_id, 
            nome_prod, 
            item.quantidade, 
            item.preco_unitario, 
            subtotal_item
        ))

    conn.commit()
    conn.close()
    return {"sucesso": True, "mensagem": "Orçamento criado com sucesso!", "id": orcamento_id}

@router.post("/{orcamento_id}/converter-venda")
def converter_orcamento_em_venda(orcamento_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, tipo FROM pedidos WHERE id = ?", (orcamento_id,))
    orcamento = cursor.fetchone()
    
    if not orcamento:
        conn.close()
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    
    cursor.execute("""
        UPDATE pedidos 
        SET tipo = 'VENDA'
        WHERE id = ?
    """, (orcamento_id,))
    
    conn.commit()
    conn.close()
    return {"sucesso": True, "mensagem": "Orçamento aprovado e convertido em venda com sucesso!"}

@router.put("/{orcamento_id}")
def atualizar_orcamento(
    orcamento_id: int, 
    payload: OrcamentoUpdateSchema, 
    user: str = Depends(auth_required)
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos WHERE id = ? AND tipo = 'ORCAMENTO'", (orcamento_id,))
    existe = cursor.fetchone()
    conn.close()
    
    if not existe:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado ou já convertido em venda.")
    
    dados = payload.dados
    usuario_responsavel = dados.usuario or dados.atendente or "Sistema"

    try:
        atualizar_orcamento_db(orcamento_id, dados, usuario_responsavel)
        return {"sucesso": True, "mensagem": f"Orçamento #{orcamento_id} atualizado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar orçamento: {str(e)}")