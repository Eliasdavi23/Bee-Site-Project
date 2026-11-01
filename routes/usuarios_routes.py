from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from config.database import get_connection
from routes.auth_routes import auth_required

router = APIRouter()


class UsuarioCreateSchema(BaseModel):
    nome: str
    senha: str


class ConfiguracoesSchema(BaseModel):
    nome_empresa: Optional[str] = "BEE GRÁFICA & COMUNICAÇÃO VISUAL"
    subtitulo_empresa: Optional[str] = "Soluções Gráficas & Impressão Digital"
    documento_empresa: Optional[str] = ""
    telefone_empresa: Optional[str] = ""
    email_empresa: Optional[str] = ""
    endereco_empresa: Optional[str] = ""
    modelo_impressao_padrao: Optional[str] = "os"
    obs_padrao_impressao: Optional[str] = "Obrigado pela preferência!"


@router.get("/api/usuarios")
def api_listar_usuarios():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM usuarios WHERE nome IS NOT NULL AND TRIM(nome) != '' ORDER BY nome ASC")
        rows = cursor.fetchall()
        return [row["nome"] for row in rows]
    except Exception as e:
        print(f"Erro ao buscar usuarios: {e}")
        return []
    finally:
        conn.close()


@router.get("/api/usuarios/detalhes")
def api_listar_usuarios_detalhes(user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM usuarios WHERE nome IS NOT NULL AND TRIM(nome) != '' ORDER BY id ASC")
        return [{"id": row["id"], "nome": row["nome"]} for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erro ao buscar detalhes de usuarios: {e}")
        return []
    finally:
        conn.close()


@router.post("/api/usuarios")
def api_criar_usuario(payload: UsuarioCreateSchema, user: str = Depends(auth_required)):
    nome = (payload.nome or "").strip()
    senha = (payload.senha or "").strip()
    if not nome or not senha:
        raise HTTPException(status_code=400, detail="Informe o nome e a senha do atendente.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome, senha) VALUES (?, ?) ON CONFLICT(nome) DO UPDATE SET senha=excluded.senha",
            (nome, senha)
        )
        conn.commit()
        return {"sucesso": True, "mensagem": "Atendente salvo com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar atendente: {str(e)}")
    finally:
        conn.close()


@router.delete("/api/usuarios/{usuario_id}")
def api_remover_usuario(usuario_id: int, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
        return {"sucesso": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/api/validar-senha")
async def api_validar_senha(request: Request, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        dados = await request.json()
        nome = str(dados.get("nome", "")).strip()
        senha = str(dados.get("senha", "")).strip()

        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE nome=?", (nome,))
        row = cursor.fetchone()

        if row and str(row["senha"]).strip() == senha:
            return {"valido": True}
        return {"valido": False}
    except Exception as e:
        print(f"Erro ao validar senha: {e}")
        return {"valido": False}
    finally:
        conn.close()


@router.get("/api/configuracoes")
def api_obter_configuracoes():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chave, valor FROM configuracoes")
        rows = cursor.fetchall()
        return {row["chave"]: row["valor"] for row in rows}
    except Exception as e:
        print(f"Erro ao buscar configuracoes: {e}")
        return {}
    finally:
        conn.close()


@router.post("/api/configuracoes")
def api_salvar_configuracoes(payload: ConfiguracoesSchema, user: str = Depends(auth_required)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        dados: Dict[str, str] = {
            "nome_empresa": (payload.nome_empresa or "BEE GRÁFICA & COMUNICAÇÃO VISUAL").strip(),
            "subtitulo_empresa": (payload.subtitulo_empresa or "Soluções Gráficas & Impressão Digital").strip(),
            "documento_empresa": (payload.documento_empresa or "").strip(),
            "telefone_empresa": (payload.telefone_empresa or "").strip(),
            "email_empresa": (payload.email_empresa or "").strip(),
            "endereco_empresa": (payload.endereco_empresa or "").strip(),
            "modelo_impressao_padrao": (payload.modelo_impressao_padrao or "os").strip(),
            "obs_padrao_impressao": (payload.obs_padrao_impressao or "").strip(),
        }
        for chave, valor in dados.items():
            cursor.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
                (chave, valor)
            )
        conn.commit()
        return {"sucesso": True, "mensagem": "Configurações salvas com sucesso!", "configuracoes": dados}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")
    finally:
        conn.close()
