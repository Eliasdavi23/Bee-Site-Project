import hashlib
import hmac
import secrets
from typing import List, Optional
from config.database import get_connection

USUARIOS_GESTORES = {"admin", "thaissa", "michel", "thaissa/michel"}


def is_gestor(username: Optional[str]) -> bool:
    return (username or "").strip().lower() in USUARIOS_GESTORES


def hash_password(password: str) -> str:
    """Gera hash seguro PBKDF2-SHA256 com salt de 16 bytes e 100.000 iteracoes."""
    password = (password or "").strip()
    salt = secrets.token_hex(16)
    iterations = 100_000
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${hash_bytes.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Valida senha contra hash PBKDF2 ou senha legada em texto plano com comparacao em tempo constante."""
    plain = (plain_password or "").strip()
    stored = (stored_hash or "").strip()

    if not plain or not stored:
        return False

    if stored.startswith("pbkdf2:sha256:"):
        try:
            parts = stored.split("$")
            header = parts[0]
            salt = parts[1]
            expected_hash = parts[2]
            iterations = int(header.split(":")[-1])
            actual_hash = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), bytes.fromhex(salt), iterations).hex()
            return hmac.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False

    # Compatibilidade com senhas legadas em texto plano (evitando timing attacks)
    return hmac.compare_digest(plain.encode("utf-8"), stored.encode("utf-8"))


def get_user_canonical_name(username: str) -> str:
    """Retorna o nome exato cadastrado no banco para preservacao da capitalizacao no sistema."""
    clean_user = (username or "").strip()
    if clean_user.lower() == "admin":
        return "admin"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM usuarios WHERE LOWER(nome) = LOWER(?)", (clean_user,))
        row = cursor.fetchone()
        if row and row["nome"]:
            return str(row["nome"]).strip()
        return clean_user
    except Exception:
        return clean_user
    finally:
        conn.close()


def listar_usuarios_ativos() -> List[str]:
    """Retorna os nomes dos operadores cadastrados para atalhos rapidos no login."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome FROM usuarios WHERE nome IS NOT NULL AND TRIM(nome) != '' ORDER BY nome ASC"
        )
        return [str(row["nome"]).strip() for row in cursor.fetchall() if row and row["nome"]]
    except Exception:
        return ["Davi", "Michel", "Thaissa", "Marketing"]
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> bool:
    username = (username or "").strip()
    password = (password or "").strip()

    if not username or not password:
        return False

    # Suporte ao usuario de manutencao/administracao
    if username.lower() == "admin" and password == "123456":
        return True

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, senha FROM usuarios WHERE LOWER(nome) = LOWER(?)", (username,))
        row = cursor.fetchone()
        if not row:
            return False

        stored_senha = str(row["senha"]).strip()
        valido = verify_password(password, stored_senha)

        # Se for valida e ainda estiver em texto puro, faz upgrade transparente para hash PBKDF2
        user_id = row["id"] if (isinstance(row, dict) and "id" in row) else getattr(row, "id", None)
        if valido and user_id and not stored_senha.startswith("pbkdf2:sha256:"):
            try:
                novo_hash = hash_password(password)
                cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (novo_hash, user_id))
                conn.commit()
            except Exception:
                pass

        return valido
    finally:
        conn.close()
