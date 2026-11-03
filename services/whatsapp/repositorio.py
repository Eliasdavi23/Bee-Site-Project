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

CAMPOS_EDITAVEIS_CONVERSA = {"modo_auto", "precisa_atendente", "cliente_id", "nome_contato", "nao_lidas"}
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
            "('nome_empresa', 'telefone_empresa', 'endereco_empresa', 'subtitulo_empresa')"
        ).fetchall()
        return {row["chave"]: (row["valor"] or "").strip() for row in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CONVERSAS
# ---------------------------------------------------------------------------
def obter_ou_criar_conversa(telefone: str, nome_contato: str = "", cliente_id: int | None = None) -> dict:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO whatsapp_conversas (telefone, nome_contato, cliente_id, criada_em) "
            "VALUES (?, ?, ?, ?)",
            (telefone, nome_contato or "", cliente_id, agora()),
        )
        # Completa dados que estavam vazios sem sobrescrever o que o atendente já definiu
        conn.execute(
            "UPDATE whatsapp_conversas SET "
            "nome_contato = CASE WHEN COALESCE(nome_contato, '') = '' THEN ? ELSE nome_contato END, "
            "cliente_id = COALESCE(cliente_id, ?) WHERE telefone = ?",
            (nome_contato or "", cliente_id, telefone),
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
) -> int | None:
    """Grava a mensagem. Retorna None se ela já existia (webhook repetido pelo provedor)."""
    conn = get_connection()
    try:
        try:
            cursor = conn.execute(
                "INSERT INTO whatsapp_mensagens "
                "(conversa_id, direcao, autor, texto, status, id_externo, usuario, criada_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conversa_id, direcao, autor, texto, status, id_externo or None, usuario or "", agora()),
            )
        except sqlite3.IntegrityError:
            return None
        incremento_nao_lidas = 1 if direcao == DIRECAO_ENTRADA else 0
        conn.execute(
            "UPDATE whatsapp_conversas SET ultima_mensagem = ?, ultima_mensagem_em = ?, "
            "nao_lidas = CASE WHEN ? = 1 THEN nao_lidas + 1 ELSE 0 END WHERE id = ?",
            (texto[:160], agora(), incremento_nao_lidas, conversa_id),
        )
        conn.commit()
        return cursor.lastrowid
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


def listar_mensagens(conversa_id: int, limite: int = 200) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM whatsapp_mensagens WHERE conversa_id = ? ORDER BY id DESC LIMIT ?) "
            "ORDER BY id ASC",
            (conversa_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]
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
