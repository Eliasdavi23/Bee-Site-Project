"""
Busca dos dados do sistema usados no atendimento.

Privacidade: a IA só recebe dados do cliente dono daquele telefone,
nunca de outros clientes.
"""
from config.database import get_connection
from services.whatsapp.mensagens import STATUS_LEGIVEL, formatar_moeda
from services.whatsapp.telefone import chave_comparacao, normalizar_telefone

LIMITE_PEDIDOS_CONTEXTO = 5
LIMITE_ORCAMENTOS_CONTEXTO = 3


def localizar_cliente_por_telefone(telefone: str) -> dict | None:
    chave = chave_comparacao(telefone)
    if not chave:
        return None
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nome, telefone FROM clientes WHERE COALESCE(telefone, '') != '' ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    for row in rows:
        if chave_comparacao(row["telefone"]) == chave:
            return dict(row)
    return None


def obter_cliente(cliente_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def obter_pedido_completo(pedido_id: int) -> dict | None:
    """Pedido ou orçamento com dados do cliente e itens."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT p.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone "
            "FROM pedidos p LEFT JOIN clientes c ON c.id = p.cliente_id WHERE p.id = ?",
            (pedido_id,),
        ).fetchone()
        if not row:
            return None
        pedido = dict(row)
        pedido["itens"] = [
            dict(r) for r in conn.execute(
                "SELECT nome_produto, quantidade, preco_unitario, subtotal, observacao "
                "FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC",
                (pedido_id,),
            ).fetchall()
        ]
        return pedido
    finally:
        conn.close()


def telefone_do_cliente(cliente: dict | None) -> str | None:
    return normalizar_telefone((cliente or {}).get("telefone") or (cliente or {}).get("cliente_telefone"))


def _linha_pedido(p: dict, itens: list[str]) -> str:
    saldo = round(float(p["valor_total"] or 0) - float(p["valor_pago"] or 0), 2)
    status = str(p["status_producao"] or "PENDENTE").upper()
    return (
        f"- Pedido #{p['id']} ({p['data'] or 'sem data'}): {', '.join(itens) or 'sem itens'} | "
        f"status: {status} ({STATUS_LEGIVEL.get(status, status.lower())}) | "
        f"total {formatar_moeda(p['valor_total'])}, pago {formatar_moeda(p['valor_pago'])}, "
        f"saldo {formatar_moeda(max(saldo, 0))} | pagamento: {p['status_pagamento'] or 'PENDENTE'}"
    )


def listar_pedidos_recentes_cliente(cliente_id: int | None, limite: int = LIMITE_PEDIDOS_CONTEXTO) -> list[dict]:
    """Retorna os pedidos de venda recentes do cliente com seus itens."""
    if not cliente_id:
        return []
    conn = get_connection()
    try:
        pedidos = [
            dict(r)
            for r in conn.execute(
                "SELECT id, data, valor_total, valor_pago, status_producao, status_pagamento "
                "FROM pedidos WHERE cliente_id = ? AND (tipo = 'VENDA' OR tipo IS NULL OR tipo = '') "
                "ORDER BY id DESC LIMIT ?",
                (cliente_id, limite),
            ).fetchall()
        ]
        for p in pedidos:
            p["itens"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT nome_produto, quantidade FROM itens_pedido WHERE pedido_id = ? ORDER BY id LIMIT 6",
                    (p["id"],),
                ).fetchall()
            ]
        return pedidos
    finally:
        conn.close()


def listar_orcamentos_recentes_cliente(cliente_id: int | None, limite: int = LIMITE_ORCAMENTOS_CONTEXTO) -> list[dict]:
    """Retorna os orçamentos recentes do cliente com seus itens."""
    if not cliente_id:
        return []
    conn = get_connection()
    try:
        orcamentos = [
            dict(r)
            for r in conn.execute(
                "SELECT id, data, valor_total, desconto, observacao "
                "FROM pedidos WHERE cliente_id = ? AND tipo = 'ORCAMENTO' "
                "ORDER BY id DESC LIMIT ?",
                (cliente_id, limite),
            ).fetchall()
        ]
        for o in orcamentos:
            o["itens"] = [
                dict(r)
                for r in conn.execute(
                    "SELECT nome_produto, quantidade FROM itens_pedido WHERE pedido_id = ? ORDER BY id LIMIT 6",
                    (o["id"],),
                ).fetchall()
            ]
        return orcamentos
    finally:
        conn.close()


def montar_contexto_cliente(cliente_id: int | None) -> str:
    """Resumo em texto dos pedidos/orçamentos recentes do cliente, para a IA consultar."""
    if not cliente_id:
        return "Contato NÃO cadastrado no sistema (nenhum pedido vinculado a este telefone)."

    conn = get_connection()
    try:
        cliente = conn.execute("SELECT id, nome FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
        if not cliente:
            return "Contato NÃO cadastrado no sistema."

        def _buscar(tipo_sql: str, limite: int) -> list[dict]:
            return [dict(r) for r in conn.execute(
                "SELECT id, data, valor_total, valor_pago, status_producao, status_pagamento "
                f"FROM pedidos WHERE cliente_id = ? AND {tipo_sql} ORDER BY id DESC LIMIT ?",
                (cliente_id, limite),
            ).fetchall()]

        pedidos = _buscar("(tipo = 'VENDA' OR tipo IS NULL OR tipo = '')", LIMITE_PEDIDOS_CONTEXTO)
        orcamentos = _buscar("tipo = 'ORCAMENTO'", LIMITE_ORCAMENTOS_CONTEXTO)

        def _itens(pedido_id: int) -> list[str]:
            return [
                f"{r['quantidade']:g}x {r['nome_produto']}" for r in conn.execute(
                    "SELECT nome_produto, quantidade FROM itens_pedido WHERE pedido_id = ? ORDER BY id LIMIT 6",
                    (pedido_id,),
                ).fetchall()
            ]

        linhas = [f"Cliente cadastrado: {cliente['nome']} (código {cliente['id']})."]
        linhas.append("Pedidos recentes:" if pedidos else "Nenhum pedido registrado.")
        linhas += [_linha_pedido(p, _itens(p["id"])) for p in pedidos]
        if orcamentos:
            linhas.append("Orçamentos em aberto:")
            linhas += [
                f"- Orçamento #{o['id']} ({o['data'] or 'sem data'}): {', '.join(_itens(o['id']))} | "
                f"total {formatar_moeda(o['valor_total'])}"
                for o in orcamentos
            ]
        return "\n".join(linhas)
    finally:
        conn.close()
