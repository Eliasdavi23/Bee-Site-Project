"""
Módulo de atendimento via WhatsApp.

Organização:
    telefone.py      -> normalização/validação de números (anti-gorila)
    config.py        -> leitura das variáveis de ambiente (.env)
    seguranca.py     -> limite de taxa, limpeza de texto, validação de token/assinatura
    mensagens.py     -> textos prontos (funcionam mesmo sem IA)
    provedores.py    -> envio: link wa.me (manual), Evolution API ou Cloud API oficial
    repositorio.py   -> acesso ao banco (conversas e mensagens)
    contexto.py      -> dados do cliente/pedidos que a IA pode usar
    atendimento.py   -> regras do atendimento (receber, sugerir, responder, enviar)
    notificacoes.py  -> mensagens prontas de pedido/orçamento e aviso de status
"""
