from fastapi import APIRouter, Request, Depends
from config.database import get_connection
from routes.auth_routes import auth_required

router = APIRouter()

@router.get("/api/usuarios")
def api_listar_usuarios(user: str = Depends(auth_required)):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM usuarios")
        usuarios = [{"id": row["id"], "nome": row["nome"]} for row in cursor.fetchall()]
        conn.close()
        return usuarios
    except Exception as e:
        print(f"Erro ao buscar usuarios: {e}")
        return []

@router.post("/api/validar-senha")
async def api_validar_senha(request: Request, user: str = Depends(auth_required)):
    try:
        dados = await request.json()
        nome = str(dados.get("nome", "")).strip()
        senha = str(dados.get("senha", "")).strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE nome=?", (nome,))
        row = cursor.fetchone()
        conn.close()

        if row and str(row["senha"]).strip() == senha:
            return {"valido": True}
        return {"valido": False}
    except Exception as e:
        print(f"Erro ao validar senha: {e}")
        return {"valido": False}