
def normalizar_status_producao(status: str | None) -> str:
    """Normaliza o status de producao removendo underscores, acentos e espacos extras."""
    if not status:
        return "PENDENTE"
    st = str(status).strip().upper().replace("_", " ")
    st = " ".join(st.split())
    st = st.replace("EM PRODUÇÃO", "EM PRODUCAO")
    st = st.replace("ESPERANDO INSTALAÇÃO", "ESPERANDO INSTALACAO")
    st = st.replace("ORÇAMENTO", "ORCAMENTO")
    return st
"""
Textos prontos para o WhatsApp.

Funcionam sem IA (garantia de atendimento mesmo com a internet/IA fora do ar)
e servem de base para a IA reescrever quando ela estiver disponível.
"""

STATUS_LEGIVEL = {
    "PENDENTE": "foi recebido e está na fila de produção",
    "EM PRODUCAO": "já está em produção",
    "EM PRODUÇÃO": "já está em produção",
    "EM_PRODUCAO": "já está em produção",
    "EM_PRODUÇÃO": "já está em produção",
    "AGUARDANDO RETIRADA": "está pronto e aguardando a sua retirada",
    "AGUARDANDO_RETIRADA": "está pronto e aguardando a sua retirada",
    "ESPERANDO INSTALACAO": "está pronto e aguardando o agendamento da instalação",
    "ESPERANDO INSTALAÇÃO": "está pronto e aguardando o agendamento da instalação",
    "ESPERANDO_INSTALACAO": "está pronto e aguardando o agendamento da instalação",
    "FINALIZADO": "foi finalizado",
    "CANCELADO": "foi cancelado",
}

# Status que merecem aviso automático ao cliente
STATUS_AVISAVEIS = (
    "EM PRODUCAO", "EM PRODUÇÃO", "EM_PRODUCAO", "EM_PRODUÇÃO",
    "AGUARDANDO RETIRADA", "AGUARDANDO_RETIRADA",
    "ESPERANDO INSTALACAO", "ESPERANDO INSTALAÇÃO", "ESPERANDO_INSTALACAO",
    "FINALIZADO"
)

TIPOS_MENSAGEM = {
    "status_pedido": "Status do pedido",
    "cobranca": "Lembrete de pagamento",
    "orcamento": "Envio de orçamento",
    "saudacao": "Mensagem livre para o cliente",
}


def formatar_moeda(valor) -> str:
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        numero = 0.0
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def primeiro_nome(nome: str) -> str:
    partes = str(nome or "").strip().split()
    return partes[0].capitalize() if partes else ""


def _saudacao(nome_cliente: str) -> str:
    nome = primeiro_nome(nome_cliente)
    return f"Olá, {nome}!" if nome else "Olá!"


def _assinatura(empresa: dict) -> str:
    return f"\n\n_{empresa.get('nome_empresa') or 'Equipe de atendimento'}_"


def _resumo_itens(itens: list[dict], limite: int = 6) -> str:
    linhas = []
    for item in itens[:limite]:
        qtd = item.get("quantidade") or 1
        qtd_txt = f"{qtd:g}" if isinstance(qtd, (int, float)) else str(qtd)
        linhas.append(f"• {qtd_txt}x {item.get('nome_produto') or 'Item'}")
    if len(itens) > limite:
        linhas.append(f"• ... e mais {len(itens) - limite} item(ns)")
    return "\n".join(linhas)


def msg_status_pedido(pedido: dict, empresa: dict) -> str:
    status_raw = str(pedido.get("status_producao") or "PENDENTE")
    status = normalizar_status_producao(status_raw)
    frase = STATUS_LEGIVEL.get(status, f"está com o status: {status.lower()}")
    texto = f"{_saudacao(pedido.get('cliente_nome'))}\n\nSeu pedido *#{pedido['id']}* {frase}."
    itens = pedido.get("itens") or []
    if itens:
        texto += f"\n\n{_resumo_itens(itens)}"
    if status == "AGUARDANDO RETIRADA" and empresa.get("endereco_empresa"):
        texto += f"\n\nRetirada em: {empresa['endereco_empresa']}"
    saldo = round(float(pedido.get("valor_total") or 0) - float(pedido.get("valor_pago") or 0), 2)
    if saldo > 0 and status in ("AGUARDANDO RETIRADA", "ESPERANDO INSTALACAO", "FINALIZADO"):
        texto += f"\nSaldo a pagar: *{formatar_moeda(saldo)}*"
    texto += "\n\nQualquer dúvida, é só responder esta mensagem."
    return texto + _assinatura(empresa)


def msg_cobranca(pedido: dict, empresa: dict) -> str:
    saldo = round(float(pedido.get("valor_total") or 0) - float(pedido.get("valor_pago") or 0), 2)
    texto = f"{_saudacao(pedido.get('cliente_nome'))}\n\n"
    if saldo <= 0:
        texto += f"Consta aqui que o pedido *#{pedido['id']}* está quitado. Muito obrigado!"
    else:
        texto += (
            f"Passando para lembrar do saldo do pedido *#{pedido['id']}*:\n"
            f"Total: {formatar_moeda(pedido.get('valor_total'))}\n"
            f"Pago: {formatar_moeda(pedido.get('valor_pago'))}\n"
            f"*Saldo: {formatar_moeda(saldo)}*\n\n"
            "Se já fez o pagamento, por favor desconsidere e nos envie o comprovante. "
        )
    return texto + _assinatura(empresa)


def msg_orcamento(orcamento: dict, empresa: dict) -> str:
    texto = f"{_saudacao(orcamento.get('cliente_nome'))}\n\nSegue o seu orçamento *#{orcamento['id']}*:\n\n"
    itens = orcamento.get("itens") or []
    if itens:
        texto += _resumo_itens(itens) + "\n\n"
    desconto = float(orcamento.get("desconto") or 0)
    if desconto > 0:
        texto += f"Desconto: {formatar_moeda(desconto)}\n"
    texto += f"*Total: {formatar_moeda(orcamento.get('valor_total'))}*"
    if orcamento.get("observacao"):
        texto += f"\n{orcamento['observacao']}"
    texto += "\n\nPosso confirmar o pedido para você?"
    return texto + _assinatura(empresa)


def msg_saudacao(cliente: dict, empresa: dict) -> str:
    return f"{_saudacao(cliente.get('nome'))}\n\nTudo bem? Aqui é da {empresa.get('nome_empresa') or 'nossa empresa'}." + _assinatura(empresa)


def msg_aguarde_atendente(empresa: dict) -> str:
    return (
        "Recebemos sua mensagem! \n"
        "Um atendente vai responder você em breve."
        + _assinatura(empresa)
    )
