import os
import json
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from config.database import get_connection
from routes.auth_routes import auth_required

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("")
def listar_pedidos(user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    # FILTRO IMPORTANTE: Traz apenas pedidos que são do tipo 'VENDA' para o painel de vendas/dashboard
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
    WHERE p.tipo = 'VENDA' OR p.tipo IS NULL OR p.tipo = ''
    ORDER BY p.id DESC
""")
    pedidos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pedidos

@router.get("/{pedido_id}/itens")
def listar_itens_pedido(pedido_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
    itens = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return itens

@router.get("/{pedido_id}/imagens")
def listar_imagens_pedido(pedido_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
    imagens = [row["caminho_arquivo"] for row in cursor.fetchall()]
    conn.close()
    return imagens

@router.post("")
async def salvar_pedido(
    dados: str = Form(...),
    imagens: List[UploadFile] = File([]),
    user: str = Depends(auth_required)
):
    try:
        payload = json.loads(dados)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Dados do pedido inválidos (JSON malformado).")

    pedido_id = payload.get("id")
    cliente_id = payload.get("cliente_id")
    valor_total = payload.get("valor_total", 0.0)
    valor_pago = payload.get("valor_pago", 0.0)
    desconto = payload.get("desconto", 0.0)
    status_producao = payload.get("status_producao", "PENDENTE")
    status_pagamento = payload.get("status_pagamento", "PENDENTE")
    forma_pagamento = payload.get("forma_pagamento", "")
    observacao = payload.get("observacao", "")
    usuario_nome = payload.get("usuario_nome", "Sistema")
    produtos = payload.get("produtos", [])
    imagens_mantidas = payload.get("imagens_mantidas", [])

    conn = get_connection()
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if pedido_id:
        # Atualiza pedido existente mantendo o tipo original dele
        cursor.execute("""
            UPDATE pedidos 
            SET cliente_id = ?, valor_total = ?, valor_pago = ?, desconto = ?, 
                status_producao = ?, status_pagamento = ?, forma_pagamento = ?, 
                observacao = ?, usuario_nome = ?
            WHERE id = ?
        """, (cliente_id, valor_total, valor_pago, desconto, status_producao, status_pagamento, forma_pagamento, observacao, usuario_nome, pedido_id))
        
        # Remove itens antigos para inserir os atualizados
        cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
        
        # Gerenciamento de imagens: apagar do disco as que não foram mantidas
        cursor.execute("SELECT id, caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
        imagens_antigas = cursor.fetchall()
        for img_antiga in imagens_antigas:
            if img_antiga["caminho_arquivo"] not in imagens_mantidas:
                file_path = img_antiga["caminho_arquivo"].lstrip("/")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                cursor.execute("DELETE FROM pedido_imagens WHERE id = ?", (img_antiga["id"],))
    else:
        # Cria novo pedido explicitamente como VENDA (já que esta rota é exclusiva de vendas do balcão/dashboard)
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, valor_total, valor_pago, desconto, status_producao, status_pagamento, forma_pagamento, observacao, data, usuario_nome, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VENDA')
        """, (cliente_id, valor_total, valor_pago, desconto, status_producao, status_pagamento, forma_pagamento, observacao, data_atual, usuario_nome))
        
        pedido_id = cursor.lastrowid

    # Salva itens do pedido
    for item in produtos:
        subtotal = (item.get("quantidade", 1) * item.get("preco_unitario", 0.0))
        cursor.execute("""
            INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pedido_id, item.get("produto_id"), item.get("nome_produto"), item.get("quantidade", 1), item.get("preco_unitario", 0.0), subtotal))

    # Salva novas imagens enviadas via upload
    for img in imagens:
        if img.filename:
            file_extension = os.path.splitext(img.filename)[1]
            unique_filename = f"pedido_{pedido_id}_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)
                
            cursor.execute("""
                INSERT INTO pedido_imagens (pedido_id, caminho_arquivo) VALUES (?, ?)
            """, (pedido_id, f"/{file_path}"))

    conn.commit()
    conn.close()
    return {"sucesso": True, "mensagem": "Pedido salvo com sucesso!", "id": pedido_id}

@router.delete("/imagens/{imagem_id}")
def deletar_imagem_pedido(imagem_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedido_imagens WHERE id = ?", (imagem_id,))
    img = cursor.fetchone()
    
    if img:
        img_dict = dict(img)
        file_path = img_dict["caminho_arquivo"].lstrip("/")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        cursor.execute("DELETE FROM pedido_imagens WHERE id = ?", (imagem_id,))
        conn.commit()
        conn.close()
        return {"sucesso": True, "mensagem": "Imagem removida com sucesso!"}
    
    conn.close()
    raise HTTPException(status_code=404, detail="Imagem não encontrada")

@router.delete("/{pedido_id}")
def deletar_pedido(pedido_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Deleta arquivos físicos das imagens vinculadas
    cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
    imagens = cursor.fetchall()
    for img in imagens:
        path = img["caminho_arquivo"].lstrip("/")
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    cursor.execute("DELETE FROM itens_pedido WHERE pedido_id = ?", (pedido_id,))
    cursor.execute("DELETE FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
    cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
    
    conn.commit()
    conn.close()
    return {"sucesso": True, "mensagem": "Pedido excluído com sucesso!"}