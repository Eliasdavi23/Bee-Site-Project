"""Acesso ao banco de dados do atendimento WhatsApp (conversas, mensagens e configurações)."""
import sqlite3
from datetime import datetime, timedelta

from config.database import get_connection

DIRECAO_ENTRADA = "ENTRADA"
DIRECAO_SAIDA = "SAIDA"

AUTOR_CLIENTE = "CLIENTE"
AUTOR_IA = "IA"
AUTOR_ATENDENTE = "ATENDENTE"
AUTOR_SISTEMA = "SISTEMA"

STATUS_RECEBIDA = "RECEBIDA"
STATUS_ENVIADA = "ENVIADA"
STATUS_LINK = "ABERTA_NO_WHATSAPP"  # funcionário enviou manualmente pelo link wa.me
STATUS_FALHOU = "FALHOU"

CAMPOS_EDITAVEIS_CONVERSA = {"modo_auto", "precisa_atendente", "cliente_id", "nome_contato", "nao_lidas", "aguardando_nome", "atendente_nome"}
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"


def agora() -> str:
    return datetime.now().strftime(FORMATO_DATA)


# ---------------------------------------------------------------------------
# CONFIGURAÇÕES (tabela configuracoes)
# ---------------------------------------------------------------------------
def ler_config_bool(chave: str, padrao: bool = False) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
        return padrao if row is None else str(row["valor"]).strip() in ("1", "true", "True", "sim")
    finally:
        conn.close()


def salvar_config_bool(chave: str, valor: bool) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, "1" if valor else "0"),
        )
        conn.commit()
    finally:
        conn.close()


def dados_empresa() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT chave, valor FROM configuracoes WHERE chave IN "
            "('nome_empresa', 'telefone_empresa', 'endereco_empresa', 'subtitulo_empresa', 'cidade_empresa', 'estado_empresa')"
        ).fetchall()
        return {row["chave"]: (row["valor"] or "").strip() for row in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CONVERSAS
# ---------------------------------------------------------------------------
def obter_ou_criar_conversa(
    telefone: str,
    nome_contato: str = "",
    cliente_id: int | None = None,
    ultima_mensagem_em: str | None = None,
) -> dict:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO whatsapp_conversas (telefone, nome_contato, cliente_id, criada_em, ultima_mensagem_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (telefone, nome_contato or "", cliente_id, agora(), ultima_mensagem_em or agora()),
        )
        # Completa dados que estavam vazios sem sobrescrever o que o atendente já definiu
        conn.execute(
            "UPDATE whatsapp_conversas SET "
            "nome_contato = CASE WHEN COALESCE(nome_contato, '') = '' THEN ? ELSE nome_contato END, "
            "cliente_id = COALESCE(cliente_id, ?), "
            "ultima_mensagem_em = CASE WHEN ? IS NOT NULL AND COALESCE(ultima_mensagem_em, '') < ? THEN ? ELSE ultima_mensagem_em END "
            "WHERE telefone = ?",
            (nome_contato or "", cliente_id, ultima_mensagem_em, ultima_mensagem_em or "", ultima_mensagem_em or "", telefone),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM whatsapp_conversas WHERE telefone = ?", (telefone,)).fetchone())
    finally:
        conn.close()


def obter_conversa(conversa_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT wc.*, c.nome AS cliente_nome FROM whatsapp_conversas wc "
            "LEFT JOIN clientes c ON c.id = wc.cliente_id WHERE wc.id = ?",
            (conversa_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def listar_conversas(busca: str = "", limite: int = 100) -> list[dict]:
    termo = f"%{(busca or '').strip()}%"
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT wc.*, c.nome AS cliente_nome FROM whatsapp_conversas wc "
            "LEFT JOIN clientes c ON c.id = wc.cliente_id "
            "WHERE wc.telefone LIKE ? OR wc.nome_contato LIKE ? OR COALESCE(c.nome, '') LIKE ? "
            "ORDER BY wc.precisa_atendente DESC, COALESCE(wc.ultima_mensagem_em, wc.criada_em) DESC LIMIT ?",
            (termo, termo, termo, limite),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def atualizar_conversa(conversa_id: int, **campos) -> None:
    campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS_CONVERSA}
    if not campos:
        return
    atribuicoes = ", ".join(f"{nome} = ?" for nome in campos)  # nomes vêm da lista branca acima
    conn = get_connection()
    try:
        conn.execute(f"UPDATE whatsapp_conversas SET {atribuicoes} WHERE id = ?", (*campos.values(), conversa_id))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# MENSAGENS
# ---------------------------------------------------------------------------
def registrar_mensagem(
    conversa_id: int,
    direcao: str,
    autor: str,
    texto: str,
    status: str,
    id_externo: str | None = None,
    usuario: str = "",
    criada_em: str | None = None,
    midia_url: str = "",
    midia_tipo: str = "",
    incrementar_nao_lidas: bool = True,
) -> int | None:
    """Grava a mensagem. Se ela já existia por id_externo mas agora veio com mídia, atualiza a mídia."""
    data_msg = (criada_em or "").strip() or agora()
    conn = get_connection()
    try:
        try:
            cursor = conn.execute(
                "INSERT INTO whatsapp_mensagens "
                "(conversa_id, direcao, autor, texto, status, id_externo, usuario, criada_em, midia_url, midia_tipo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversa_id,
                    direcao,
                    autor,
                    texto,
                    status,
                    id_externo or None,
                    usuario or "",
                    data_msg,
                    midia_url or "",
                    midia_tipo or "",
                ),
            )
        except sqlite3.IntegrityError:
            if midia_url and id_externo:
                conn.execute(
                    "UPDATE whatsapp_mensagens SET midia_url = ?, midia_tipo = ? "
                    "WHERE id_externo = ? AND (midia_url IS NULL OR midia_url = '')",
                    (midia_url, midia_tipo or "imagem", id_externo),
                )
                conn.commit()
            return None
        incremento_nao_lidas = 1 if direcao == DIRECAO_ENTRADA and incrementar_nao_lidas else 0
        conn.execute(
            "UPDATE whatsapp_conversas SET "
            "ultima_mensagem = CASE WHEN COALESCE(ultima_mensagem_em, '') <= ? THEN ? ELSE ultima_mensagem END, "
            "ultima_mensagem_em = CASE WHEN COALESCE(ultima_mensagem_em, '') <= ? THEN ? ELSE ultima_mensagem_em END, "
            "nao_lidas = CASE "
            "    WHEN ? = 'SAIDA' THEN 0 "
            "    WHEN ? = 1 THEN COALESCE(nao_lidas, 0) + 1 "
            "    ELSE nao_lidas END "
            "WHERE id = ?",
            (data_msg, texto[:160], data_msg, data_msg, direcao, incremento_nao_lidas, conversa_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def obter_mensagem_por_id(mensagem_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM whatsapp_mensagens WHERE id = ?", (mensagem_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def obter_mensagem_por_id_externo(id_externo: str) -> dict | None:
    if not id_externo:
        return None
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM whatsapp_mensagens WHERE id_externo = ?", (id_externo,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def atualizar_midia_mensagem(mensagem_id: int, midia_url: str, midia_tipo: str = "imagem") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE whatsapp_mensagens SET midia_url = ?, midia_tipo = ? WHERE id = ?",
            (midia_url, midia_tipo, mensagem_id),
        )
        conn.commit()
    finally:
        conn.close()


def atualizar_midia_mensagem_por_id_externo(id_externo: str, midia_url: str, midia_tipo: str = "imagem") -> bool:
    if not id_externo or not midia_url:
        return False
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE whatsapp_mensagens SET midia_url = ?, midia_tipo = ? WHERE id_externo = ?",
            (midia_url, midia_tipo, id_externo),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def obter_ultima_mensagem_midia(conversa_id: int, tipo: str = "imagem") -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM whatsapp_mensagens WHERE conversa_id = ? "
            "AND (midia_tipo = ? OR midia_url LIKE '%.jpg' OR midia_url LIKE '%.png' OR midia_url LIKE '%.webp' OR midia_url LIKE '%.pdf') "
            "ORDER BY id DESC LIMIT 1",
            (conversa_id, tipo),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def recalcular_nao_lidas_conversas_pendentes() -> int:
    """
    Recalcula com precisão o contador de mensagens sem resposta para cada conversa:
    Conta quantas mensagens de ENTRADA o cliente enviou após a última mensagem de SAIDA da empresa.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE whatsapp_conversas 
            SET nao_lidas = (
                SELECT COUNT(*) FROM whatsapp_mensagens m
                WHERE m.conversa_id = whatsapp_conversas.id
                  AND m.id > COALESCE((
                      SELECT MAX(id) FROM whatsapp_mensagens 
                      WHERE conversa_id = whatsapp_conversas.id AND direcao = 'SAIDA'
                  ), 0)
                  AND m.direcao = 'ENTRADA'
            )
            """
        )
        conn.commit()
        return cur.rowcount
    except Exception:
        return 0
    finally:
        conn.close()


def marcar_todas_conversas_como_lidas() -> int:
    """Marca todas as conversas do sistema como lidas (zera o contador nao_lidas)."""
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE whatsapp_conversas SET nao_lidas = 0 WHERE nao_lidas > 0")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def atualizar_status_mensagem(mensagem_id: int, status: str, id_externo: str | None = None) -> None:
    conn = get_connection()
    try:
        try:
            conn.execute(
                "UPDATE whatsapp_mensagens SET status = ?, id_externo = COALESCE(?, id_externo) WHERE id = ?",
                (status, id_externo or None, mensagem_id),
            )
        except sqlite3.IntegrityError:
            conn.execute("UPDATE whatsapp_mensagens SET status = ? WHERE id = ?", (status, mensagem_id))
        conn.commit()
    finally:
        conn.close()


def listar_mensagens(conversa_id: int, limite: int = 1000) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM whatsapp_mensagens WHERE conversa_id = ? "
            "ORDER BY COALESCE(criada_em, '1970-01-01 00:00:00') DESC, id DESC LIMIT ?) "
            "ORDER BY COALESCE(criada_em, '1970-01-01 00:00:00') ASC, id ASC",
            (conversa_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def obter_mensagem_mais_antiga(conversa_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM whatsapp_mensagens WHERE conversa_id = ? AND id_externo IS NOT NULL "
            "ORDER BY COALESCE(criada_em, '9999-12-31 23:59:59') ASC, id ASC LIMIT 1",
            (conversa_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def contar_mensagens_recentes(conversa_id: int, autor: str, minutos: int) -> int:
    limite = (datetime.now() - timedelta(minutes=minutos)).strftime(FORMATO_DATA)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM whatsapp_mensagens "
            "WHERE conversa_id = ? AND autor = ? AND criada_em >= ?",
            (conversa_id, autor, limite),
        ).fetchone()
        return int(row["total"] or 0)
    finally:
        conn.close()


def houve_saida_recente(conversa_id: int, minutos: int) -> bool:
    limite = (datetime.now() - timedelta(minutes=minutos)).strftime(FORMATO_DATA)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM whatsapp_mensagens WHERE conversa_id = ? AND direcao = ? AND criada_em >= ? LIMIT 1",
            (conversa_id, DIRECAO_SAIDA, limite),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
