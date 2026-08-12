from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from config.database import get_connection
from routes.auth_routes import auth_required
from services.periodo_service import construir_filtro_periodo

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    user = auth_required(request)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"page": "dashboard", "user": user}
    )

@router.get("/api/dashboard/estatisticas")
def obter_estatisticas(periodo: str = Query("mes_atual"), data: str | None = Query(None)):
    conn = get_connection()
    cursor = conn.cursor()

    # Filtro de data seguro e exclusão de orçamentos do dashboard
    where_conditions = [
        "(p.tipo = 'VENDA' OR p.tipo IS NULL OR p.tipo = '')",
        "UPPER(COALESCE(p.status_producao, '')) NOT IN ('ORCAMENTO', 'ORÇAMENTO')"
    ]

    filtro_data, params = construir_filtro_periodo(periodo=periodo, data_especifica=data)
    where_conditions.append(filtro_data)

    where_p = "WHERE " + " AND ".join(where_conditions)

    # --- A. KPIs SUPERIORES ---
    faturamento_total = 0.0
    total_pedidos = 0
    saldo_pendente = 0.0
    em_producao_count = 0

    try:
        cursor.execute(f"""
            SELECT 
                COALESCE(SUM(p.valor_total), 0) as faturamento_total,
                COUNT(p.id) as total_pedidos,
                COALESCE(SUM(CASE WHEN p.status_pagamento != 'PAGO' THEN (p.valor_total - COALESCE(p.valor_pago, 0)) ELSE 0 END), 0) as saldo_pendente
            FROM pedidos p
            {where_p}
        """, params)
        kpis_raw = cursor.fetchone()
        if kpis_raw:
            faturamento_total = float(kpis_raw["faturamento_total"] or 0)
            total_pedidos = int(kpis_raw["total_pedidos"] or 0)
            saldo_pendente = max(0.0, float(kpis_raw["saldo_pendente"] or 0))
    except Exception as e:
        print("Erro KPIs:", e)

    ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0.0

    # Fila de Produção (Correção da coluna)
    try:
        where_prod = f"{where_p} AND"
        cursor.execute(f"""
            SELECT COUNT(p.id) as fila_count 
            FROM pedidos p 
            {where_prod} UPPER(COALESCE(p.status_producao, '')) IN ('PENDENTE', 'EM PRODUCAO', 'EM PRODUÇÃO')
        """, params)
        res_prod = cursor.fetchone()
        if res_prod:
            em_producao_count = res_prod["fila_count"] or 0
    except Exception as e:
        print("Erro Fila Produção:", e)

    # --- B. FORMAS DE PAGAMENTO ---
    formas_pagamento = {}
    try:
        cursor.execute(f"""
            SELECT COALESCE(p.forma_pagamento, 'Outros') as forma, COALESCE(SUM(COALESCE(p.valor_pago, p.valor_total)), 0) as total
            FROM pedidos p
            {where_p}
            GROUP BY forma
        """, params)
        for row in cursor.fetchall():
            formas_pagamento[str(row["forma"]).strip().upper()] = float(row["total"] or 0)
    except Exception as e:
        print("Erro Formas Pagamento:", e)

    # --- C. TOP ATENDENTES ---
    top_atendentes = []
    try:
        cursor.execute(f"""
            SELECT COALESCE(p.usuario_nome, 'Atendente') as usuario_nome, COALESCE(SUM(p.valor_total), 0) as total_vendas, COUNT(p.id) as qtd_pedidos
            FROM pedidos p
            {where_p}
            GROUP BY usuario_nome
            ORDER BY total_vendas DESC
            LIMIT 5
        """, params)
        top_atendentes = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("Erro Top Atendentes:", e)

    # --- D. TOP PRODUTOS ---
    top_produtos = []
    try:
        cursor.execute(f"""
            SELECT ip.nome_produto, SUM(ip.quantidade) as qtd_total, SUM(ip.subtotal) as valor_total
            FROM itens_pedido ip
            JOIN pedidos p ON p.id = ip.pedido_id
            {where_p}
            GROUP BY ip.nome_produto
            ORDER BY qtd_total DESC
            LIMIT 5
        """, params)
        top_produtos = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("Erro Top Produtos:", e)

    # --- E. ÚLTIMOS 5 PEDIDOS (Correção da coluna) ---
    ultimos_pedidos = []
    try:
        cursor.execute(f"""
            SELECT p.id, COALESCE(c.nome, 'Cliente Avulso') as cliente_nome, p.valor_total, COALESCE(p.status_producao, 'PENDENTE') as status_producao
            FROM pedidos p
            LEFT JOIN clientes c ON c.id = p.cliente_id
            {where_p}
            ORDER BY p.id DESC
            LIMIT 5
        """, params)
        ultimos_pedidos = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print("Erro Últimos Pedidos:", e)

    # --- F. STATUS DA PRODUÇÃO (Correção da coluna) ---
    status_producao = {"PENDENTE": 0, "EM PRODUCAO": 0, "AGUARDANDO RETIRADA": 0, "ESPERANDO INSTALACAO": 0, "FINALIZADO": 0}
    try:
        cursor.execute(f"""
            SELECT UPPER(COALESCE(p.status_producao, 'PENDENTE')) as st, COUNT(p.id) as quantidade
            FROM pedidos p
            {where_p}
            GROUP BY st
        """, params)
        for row in cursor.fetchall():
            st = str(row["st"]).replace("EM PRODUÇÃO", "EM PRODUCAO")
            if st in status_producao:
                status_producao[st] = int(row["quantidade"] or 0)
    except Exception as e:
        print("Erro Status Produção:", e)

    conn.close()

    return {
        "kpis": {
            "faturamento_total": faturamento_total,
            "total_pedidos": total_pedidos,
            "ticket_medio": ticket_medio,
            "em_producao": em_producao_count,
            "saldo_pendente": saldo_pendente
        },
        "formas_pagamento": formas_pagamento,
        "top_atendentes": top_atendentes,
        "top_produtos": top_produtos,
        "ultimos_pedidos": ultimos_pedidos,
        "status_producao": status_producao
    }