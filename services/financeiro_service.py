from calendar import monthrange
from datetime import date, datetime
from config.database import get_connection
from services.periodo_service import construir_filtro_periodo


def normalizar_forma_pagamento(forma_raw: str) -> str:
    """Normaliza as variações do nome da forma de pagamento para as chaves do resumo."""
    if not forma_raw:
        return ""

    texto = str(forma_raw).strip().upper()

    if "PIX" in texto:
        return "PIX"
    elif "CREDIT" in texto or "CRÉDIT" in texto:
        return "CREDITO"
    elif "DEBIT" in texto or "DÉBIT" in texto:
        return "DEBITO"
    elif "DINHEIRO" in texto or "ESPECIE" in texto or "ESPÉCIE" in texto:
        return "DINHEIRO"
    elif "LINK" in texto:
        return "LINK"

    return ""


def obter_dados_resumo_financeiro(periodo: str = "mes_atual", data_especifica: str | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        filtro_data, params = construir_filtro_periodo(periodo=periodo, data_especifica=data_especifica, table_alias="")

        # 1. Total Recebido no Mês por Forma de Pagamento (apenas vendas aprovadas)
        cursor.execute(f"""
            SELECT forma_pagamento, SUM(valor_pago) as total
            FROM pedidos
            WHERE {filtro_data}
              AND (tipo = 'VENDA' OR tipo IS NULL OR tipo = '')
              AND UPPER(COALESCE(status_producao, '')) NOT IN ('ORCAMENTO', 'ORÇAMENTO')
              AND UPPER(COALESCE(status_pagamento, '')) != 'ORCAMENTO'
            GROUP BY forma_pagamento
        """, params)

        entradas_raw = cursor.fetchall()
        entradas_detalhadas = {"PIX": 0.0, "CREDITO": 0.0, "DEBITO": 0.0, "DINHEIRO": 0.0, "LINK": 0.0}
        total_recebido_mes = 0.0

        for row in entradas_raw:
            forma_bruta = row["forma_pagamento"]
            chave = normalizar_forma_pagamento(forma_bruta)
            valor = float(row["total"] or 0)

            if chave in entradas_detalhadas:
                entradas_detalhadas[chave] += valor

            total_recebido_mes += valor

        # 2. Total a Receber de Clientes (apenas vendas aprovadas)
        cursor.execute(f"""
            SELECT SUM(valor_total - valor_pago) as total_pendente
            FROM pedidos
            WHERE status_pagamento != 'PAGO' 
              AND (valor_total - valor_pago) > 0
              AND {filtro_data}
              AND (tipo = 'VENDA' OR tipo IS NULL OR tipo = '')
              AND UPPER(COALESCE(status_producao, '')) NOT IN ('ORCAMENTO', 'ORÇAMENTO')
              AND UPPER(COALESCE(status_pagamento, '')) != 'ORCAMENTO'
        """, params)
        row_pendente = cursor.fetchone()
        total_a_receber = float(row_pendente["total_pendente"] or 0) if row_pendente else 0.0

        # 3. Contas a Pagar no Mês (Total e Pendentes)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'PENDENTE' THEN valor ELSE 0 END) as total_pendente,
                SUM(CASE WHEN status = 'PAGO' THEN valor ELSE 0 END) as total_pago
            FROM contas_a_pagar
            WHERE strftime('%Y-%m', data_vencimento) = ?
        """, (datetime.now().strftime('%Y-%m'),))
        row_contas = cursor.fetchone()
        contas_a_pagar_pendentes = float(row_contas["total_pendente"] or 0) if row_contas else 0.0
        contas_a_pagar_pagas = float(row_contas["total_pago"] or 0) if row_contas else 0.0

        return {
            "entradas_detalhadas": entradas_detalhadas,
            "total_recebido_mes": total_recebido_mes,
            "total_a_receber_clientes": total_a_receber,
            "contas_a_pagar_pendentes": contas_a_pagar_pendentes,
            "contas_a_pagar_pagas": contas_a_pagar_pagas,
            "saldo_previsto": total_recebido_mes + total_a_receber - (contas_a_pagar_pendentes + contas_a_pagar_pagas)
        }
    finally:
        conn.close()


def buscar_contas_pagar(data_vencimento: str | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if data_vencimento:
            cursor.execute("""
                SELECT * FROM contas_a_pagar
                WHERE date(data_vencimento) = date(?)
                ORDER BY status DESC, data_vencimento ASC
            """, (data_vencimento,))
        else:
            cursor.execute("SELECT * FROM contas_a_pagar ORDER BY status DESC, data_vencimento ASC")

        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def inserir_conta_pagar(descricao: str, categoria: str, valor: float, data_vencimento: str, recorrente: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        dia_vencimento = datetime.strptime(data_vencimento[:10], '%Y-%m-%d').day if recorrente else None
        cursor.execute("""
            INSERT INTO contas_a_pagar (descricao, categoria, valor, data_vencimento, status, recorrente, dia_vencimento)
            VALUES (?, ?, ?, ?, 'PENDENTE', ?, ?)
        """, (descricao, categoria, valor, data_vencimento, int(recorrente), dia_vencimento))
        conn.commit()
    finally:
        conn.close()


def marcar_conta_paga(conta_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        hoje = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("SELECT * FROM contas_a_pagar WHERE id = ?", (conta_id,))
        conta = cursor.fetchone()
        if not conta or conta['status'] == 'PAGO':
            return False

        cursor.execute("""
            UPDATE contas_a_pagar 
            SET status = 'PAGO', data_pagamento = ? 
            WHERE id = ?
        """, (hoje, conta_id))

        if conta['recorrente']:
            vencimento_atual = datetime.strptime(conta['data_vencimento'][:10], '%Y-%m-%d').date()
            proximo_mes = vencimento_atual.month % 12 + 1
            proximo_ano = vencimento_atual.year + (1 if vencimento_atual.month == 12 else 0)
            dia_preferido = conta['dia_vencimento'] or vencimento_atual.day
            proximo_vencimento = date(
                proximo_ano,
                proximo_mes,
                min(dia_preferido, monthrange(proximo_ano, proximo_mes)[1])
            ).isoformat()

            cursor.execute("""
                INSERT INTO contas_a_pagar (descricao, categoria, valor, data_vencimento, status, recorrente, dia_vencimento)
                VALUES (?, ?, ?, ?, 'PENDENTE', 1, ?)
            """, (
                conta['descricao'], conta['categoria'], conta['valor'], proximo_vencimento, dia_preferido
            ))

        conn.commit()
        return True
    finally:
        conn.close()


def deletar_conta_pagar(conta_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contas_a_pagar WHERE id = ?", (conta_id,))
        conn.commit()
    finally:
        conn.close()


def buscar_clientes_devedores(periodo: str = "mes_atual", data_especifica: str | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        filtro_data, params = construir_filtro_periodo(periodo=periodo, data_especifica=data_especifica, table_alias="")

        cursor.execute(f"""
            SELECT p.id as pedido_id, c.nome as cliente_nome, p.valor_total, p.valor_pago, 
                   (p.valor_total - p.valor_pago) as valor_pendente, p.data
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.status_pagamento != 'PAGO' 
              AND (p.valor_total - p.valor_pago) > 0
              AND {filtro_data}
              AND (p.tipo = 'VENDA' OR p.tipo IS NULL OR p.tipo = '')
              AND UPPER(COALESCE(p.status_producao, '')) NOT IN ('ORCAMENTO', 'ORÇAMENTO')
              AND UPPER(COALESCE(p.status_pagamento, '')) != 'ORCAMENTO'
            ORDER BY p.id DESC
        """, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
