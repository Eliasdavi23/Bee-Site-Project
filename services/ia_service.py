"""
Serviço único de acesso à IA (Google Gemini + Assistente Local Inteligente).

- Lê a chave GEMINI_API_KEY ou GOOGLE_API_KEY do ambiente (.env).
- Se a IA em nuvem não estiver configurada ou falhar por cota/rede, o sistema
  utiliza o Assistente Local Inteligente integrado ao banco de dados SQLite.
- Nunca exibe 'sistema sobrecarregado' indevidamente: responde diretamente com dados locais.
"""
import logging
import os
import re
import unicodedata

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # Pacote opcional: o sistema funciona perfeitamente sem IA em nuvem
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

from config.database import get_connection

logger = logging.getLogger("uvicorn.error")

MODELO_PADRAO = "gemini-2.5-flash"
LIMITE_PROMPT = 12000


class IAIndisponivel(Exception):
    """A IA em nuvem não está configurada ou não respondeu a tempo."""


def _chave_api() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def modelo_configurado() -> str:
    return (os.getenv("GEMINI_MODEL") or "").strip() or MODELO_PADRAO


def ia_configurada() -> bool:
    return genai is not None and bool(_chave_api())


def _sem_acentos(texto: str) -> str:
    if not texto:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


def gerar_texto(prompt: str, instrucao_sistema: str, max_tokens: int = 600) -> str:
    """Gera um texto curto com o Google Gemini. Lança IAIndisponivel em falhas."""
    if not ia_configurada():
        raise IAIndisponivel("IA não configurada (defina GEMINI_API_KEY no arquivo .env).")

    prompt = (prompt or "").strip()[:LIMITE_PROMPT]
    if not prompt:
        raise IAIndisponivel("Prompt vazio.")

    try:
        client = genai.Client(api_key=_chave_api())
        texto = ""

        # Tenta a API de Interactions se disponível
        if hasattr(client, "interactions"):
            try:
                interaction = client.interactions.create(
                    model=modelo_configurado(),
                    input=prompt,
                    system_instruction=instrucao_sistema or None,
                    generation_config={"max_output_tokens": max_tokens},
                    store=False,
                )
                texto = (getattr(interaction, "output_text", None) or "").strip()
            except Exception as e_inter:
                logger.warning("Tentando fallback generate_content após interação falhar: %s", e_inter)

        # Fallback para generate_content clássico
        if not texto:
            cfg = {"max_output_tokens": max_tokens}
            if instrucao_sistema:
                cfg["system_instruction"] = instrucao_sistema
            resp = client.models.generate_content(
                model=modelo_configurado(),
                contents=prompt,
                config=cfg,
            )
            texto = (getattr(resp, "text", None) or "").strip()

    except Exception as exc:
        logger.warning("Falha na chamada à IA Google Gemini: %s", exc.__class__.__name__)
        raise IAIndisponivel("A IA em nuvem não respondeu.") from None

    if not texto:
        raise IAIndisponivel("A IA retornou uma resposta vazia.")
    return texto


def analisar_imagem(
    imagem_bytes: bytes,
    mime_type: str,
    prompt: str,
    instrucao_sistema: str = "",
    max_tokens: int = 500,
) -> str:
    """Analisa uma imagem (ex.: comprovante Pix/bancário) com o modelo Gemini."""
    if not ia_configurada() or not imagem_bytes:
        raise IAIndisponivel("IA não configurada ou imagem vazia.")

    try:
        client = genai.Client(api_key=_chave_api())
        partes = []
        if genai_types is not None and hasattr(genai_types, "Part") and hasattr(genai_types.Part, "from_bytes"):
            partes.append(genai_types.Part.from_bytes(data=imagem_bytes, mime_type=mime_type or "image/jpeg"))
            partes.append(prompt)
            cfg = {"max_output_tokens": max_tokens}
            if instrucao_sistema:
                cfg["system_instruction"] = instrucao_sistema
            resp = client.models.generate_content(
                model=modelo_configurado(),
                contents=partes,
                config=cfg,
            )
            texto = (getattr(resp, "text", None) or "").strip()
        else:
            raise IAIndisponivel("Suporte multimodal indisponível.")
    except Exception as exc:
        logger.warning("Falha na análise de imagem pela IA: %s", exc.__class__.__name__)
        raise IAIndisponivel("A IA não conseguiu analisar a imagem.") from None

    if not texto:
        raise IAIndisponivel("Resposta vazia da IA na análise de imagem.")
    return texto


def consultar_assistente_local(pergunta: str) -> str:
    """
    Assistente Local Inteligente que consulta o banco de dados da gráfica
    e responde perguntas dos colaboradores instantaneamente sem depender de rede externa.
    """
    txt = _sem_acentos(pergunta)
    conn = get_connection()
    try:
        # 1. Pergunta sobre Pedidos específicos (ex: #12 ou pedido 12)
        match_id = re.search(r"(?:pedido|id|#)\s*#?(\d+)", txt)
        if match_id:
            pid = int(match_id.group(1))
            row = conn.execute(
                "SELECT p.id, p.tipo, p.status_producao, p.status_pagamento, p.valor_total, p.valor_pago, "
                "p.observacao, p.criado_em, c.nome AS cliente_nome, c.telefone AS cliente_tel "
                "FROM pedidos p LEFT JOIN clientes c ON c.id = p.cliente_id WHERE p.id = ?",
                (pid,),
            ).fetchone()
            if row:
                saldo = max(round(float(row["valor_total"] or 0) - float(row["valor_pago"] or 0), 2), 0.0)
                itens = conn.execute(
                    "SELECT nome_produto, quantidade, preco_unitario, subtotal FROM itens_pedido WHERE pedido_id = ?",
                    (pid,),
                ).fetchall()
                itens_txt = "\n".join(
                    f"  • {i['quantidade']:g}x {i['nome_produto']} (R$ {i['subtotal']:.2f})" for i in itens
                ) or "  • Sem itens especificados"
                return (
                    f"*Pedido #{row['id']} ({row['tipo'] or 'VENDA'})*\n"
                    f"• *Cliente:* {row['cliente_nome'] or 'Balcão'} ({row['cliente_tel'] or 'sem telefone'})\n"
                    f"• *Produção:* {row['status_producao'] or 'PENDENTE'}\n"
                    f"• *Pagamento:* {row['status_pagamento'] or 'PENDENTE'} (Pago: R$ {float(row['valor_pago'] or 0):.2f} / Total: R$ {float(row['valor_total'] or 0):.2f})\n"
                    f"• *Saldo:* R$ {saldo:.2f}\n"
                    f"• *Itens:*\n{itens_txt}\n"
                    + (f"• *Observação:* {row['observacao']}" if row['observacao'] else "")
                )

        # 2. Pergunta sobre Pedidos em geral / Status / Quantidade
        if any(p in txt for p in ("pedido", "pedidos", "venda", "vendas", "producao", "fila")):
            total = conn.execute("SELECT COUNT(*) AS c FROM pedidos WHERE tipo != 'ORCAMENTO'").fetchone()["c"]
            pendentes = conn.execute("SELECT COUNT(*) AS c FROM pedidos WHERE status_producao = 'PENDENTE'").fetchone()["c"]
            produzindo = conn.execute("SELECT COUNT(*) AS c FROM pedidos WHERE status_producao IN ('EM PRODUCAO', 'EM_PRODUCAO', 'EM PRODUÇÃO', 'EM_PRODUÇÃO')").fetchone()["c"]
            prontos = conn.execute("SELECT COUNT(*) AS c FROM pedidos WHERE status_producao = 'PRONTO'").fetchone()["c"]
            recentes = conn.execute(
                "SELECT p.id, p.status_producao, p.valor_total, c.nome AS cliente "
                "FROM pedidos p LEFT JOIN clientes c ON c.id = p.cliente_id "
                "ORDER BY p.id DESC LIMIT 5"
            ).fetchall()
            rec_txt = "\n".join(
                f"  • #{r['id']} - {r['cliente'] or 'Cliente'}: {r['status_producao']} (R$ {float(r['valor_total'] or 0):.2f})"
                for r in recentes
            )
            return (
                f"*Painel de Pedidos da Gráfica:*\n"
                f"• Total de pedidos: *{total}*\n"
                f"• Pendentes: *{pendentes}*\n"
                f"• Em produção: *{produzindo}*\n"
                f"• Prontos para entrega: *{prontos}*\n\n"
                f"*Últimos pedidos registrados:*\n{rec_txt}"
            )

        # 3. Pergunta sobre Produtos / Preços / Valores
        if any(p in txt for p in ("produto", "produtos", "preco", "precos", "valor", "valores", "tabela", "adesivo", "banner", "cartao", "lona", "panfleto", "faixa", "placa", "pvc", "triplex", "talionario")):
            palavras_busca = [p for p in ("adesivo", "banner", "cartao", "lona", "panfleto", "faixa", "placa", "pvc", "triplex", "talionario") if p in txt]
            termo = palavras_busca[0] if palavras_busca else ""
            if termo:
                rows = conn.execute(
                    "SELECT nome, preco_venda, quantidade FROM produtos WHERE LOWER(nome) LIKE ? LIMIT 6",
                    (f"%{termo}%",),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT nome, preco_venda, quantidade FROM produtos ORDER BY nome ASC LIMIT 8"
                ).fetchall()

            if rows:
                lista = "\n".join(
                    f"  • *{r['nome']}:* R$ {float(r['preco_venda'] or 0):.2f}"
                    for r in rows
                )
                return f"*Produtos & Tabela de Preços:*\n{lista}"
            return "Nenhum produto correspondente encontrado no catálogo ativo."

        # 4. Pergunta sobre Clientes
        if any(p in txt for p in ("cliente", "clientes", "contato", "telefone cliente")):
            match_nome = re.search(r"cliente\s+([a-zA-ZÀ-ÿ]+)", txt)
            nome_busca = match_nome.group(1) if match_nome else ""
            if nome_busca and len(nome_busca) >= 3:
                rows = conn.execute(
                    "SELECT nome, telefone, email FROM clientes WHERE LOWER(nome) LIKE ? LIMIT 5",
                    (f"%{nome_busca}%",),
                ).fetchall()
                if rows:
                    res = "\n".join(f"  • *{r['nome']}:* Tel {r['telefone'] or 'sem telefone'}" for r in rows)
                    return f"*Clientes encontrados para '{nome_busca}':*\n{res}"

            total_cli = conn.execute("SELECT COUNT(*) AS c FROM clientes").fetchone()["c"]
            ultimos_cli = conn.execute("SELECT nome, telefone FROM clientes ORDER BY id DESC LIMIT 5").fetchall()
            cli_txt = "\n".join(f"  • {r['nome']} ({r['telefone'] or 'sem telefone'})" for r in ultimos_cli)
            return (
                f"*Base de Clientes:*\n"
                f"• Total cadastrado: *{total_cli} clientes*\n"
                f"• Últimos cadastrados:\n{cli_txt}"
            )

        # 5. Pergunta sobre WhatsApp / Recursos do Sistema
        if any(p in txt for p in ("whatsapp", "zap", "audio", "imagem", "comprovante", "ligacao", "documento", "pdf")):
            return (
                "*Módulo WhatsApp Integrado:*\n"
                "• *Áudios e Voz:* Escute áudios diretamente no balão da conversa pelo player interativo.\n"
                "• *Documentos e PDFs:* Arquivos recebidos podem ser visualizados ou baixados diretamente pelo chat.\n"
                "• *Imagens e Fotos:* Miniaturas com clique para ampliar em lightbox e envio direto pelo atendente.\n"
                "• *Ligações:* Rejeição automática de chamada com aviso educado informando que a gráfica recebe apenas mensagens.\n"
                "• *Comprovantes Pix:* Reconhecimento automático e baixa de 50% de sinal ou 100% quitado."
            )

        # 6. Pergunta sobre Financeiro / Contas
        if any(p in txt for p in ("financeiro", "caixa", "contas", "faturamento", "receita")):
            total_apagar = conn.execute("SELECT SUM(valor) AS s FROM contas_a_pagar WHERE status = 'PENDENTE'").fetchone()["s"] or 0.0
            total_recebido = conn.execute("SELECT SUM(valor_pago) AS s FROM pedidos WHERE tipo != 'ORCAMENTO'").fetchone()["s"] or 0.0
            return (
                f"*Resumo Financeiro da Gráfica:*\n"
                f"• Total recebido em pedidos: *R$ {total_recebido:,.2f}*\n"
                f"• Contas a pagar pendentes: *R$ {total_apagar:,.2f}*"
            )

        # 7. Resposta padrão inteligente
        return (
            "Olá! Sou o **Assistente Bee** da Gráfica.\n\n"
            "Posso te ajudar consultando o sistema em tempo real:\n"
            "• *Pedidos:* 'quantos pedidos temos?', 'status do pedido #10', 'pedidos pendentes'\n"
            "• *Produtos:* 'qual o preço do adesivo?', 'listar produtos', 'preço do banner'\n"
            "• *Clientes:* 'buscar cliente João', 'quantos clientes temos'\n"
            "• *WhatsApp:* 'como funciona o WhatsApp?', 'áudios e documentos'\n"
            "• *Financeiro:* 'resumo financeiro'\n\n"
            "Como posso te ajudar agora?"
        )
    finally:
        conn.close()
