from config.database import get_connection


def authenticate_user(username: str, password: str) -> bool:
    username = (username or "").strip()
    password = (password or "").strip()

    if not username or not password:
        return False

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE nome = ?", (username,))
        row = cursor.fetchone()
        return bool(row and str(row["senha"]).strip() == password)
    finally:
        conn.close()
