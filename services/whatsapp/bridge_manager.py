"""
Gerenciador da Ponte Local WhatsApp (QR Code em tempo real).

Controla o processo local em `whatsapp_bridge/server.js`, instala dependências npm
automaticamente na primeira vez, mantém o token e a URL do webhook sincronizados e
faz a ponte HTTP segura em 127.0.0.1:3001.
"""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("uvicorn.error")

BRIDGE_PORT = int(os.getenv("WHATSAPP_BRIDGE_PORT") or "3001")
BRIDGE_BASE_URL = f"http://127.0.0.1:{BRIDGE_PORT}"
BRIDGE_DIR = Path(__file__).resolve().parent.parent.parent / "whatsapp_bridge"


def _gerar_token_padrao() -> str:
    semente = f"bee-whatsapp-bridge-{BRIDGE_DIR}".encode("utf-8")
    return hashlib.sha256(semente).hexdigest()[:48]


BRIDGE_TOKEN = (os.getenv("WHATSAPP_WEBHOOK_TOKEN") or "").strip() or _gerar_token_padrao()

_trava = threading.Lock()
_processo: subprocess.Popen | None = None
_instalando_npm = False
_erro_inicializacao = ""
_webhook_url_atual = os.getenv("FASTAPI_WEBHOOK_URL", "http://127.0.0.1:8000/api/whatsapp/webhook").strip()


def token_interno_bridge() -> str:
    return BRIDGE_TOKEN


def atualizar_webhook_url(base_url: str) -> None:
    """Atualiza a URL real do FastAPI (ex.: http://192.168.0.11:8000/api/whatsapp/webhook)."""
    global _webhook_url_atual
    limpa = (base_url or "").strip().rstrip("/")
    if limpa.startswith("http"):
        if "127.0.0.1" in limpa or "localhost" in limpa:
            _webhook_url_atual = "http://127.0.0.1:8000/api/whatsapp/webhook"
        else:
            _webhook_url_atual = f"{limpa}/api/whatsapp/webhook"


def localizar_node() -> tuple[str | None, str | None]:
    """Localiza `node.exe` e `npm.cmd` mesmo se o PATH do terminal ainda não tiver atualizado."""
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")

    candidatos_dirs = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "nodejs",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs",
        Path(os.environ.get("APPDATA", "")) / "nvm",
    ]
    for pasta in candidatos_dirs:
        if not node_path and (pasta / "node.exe").exists():
            node_path = str(pasta / "node.exe")
        if not npm_path and (pasta / "npm.cmd").exists():
            npm_path = str(pasta / "npm.cmd")

    return node_path, npm_path


def _requisitar_bridge(metodo: str, rota: str, payload: dict | None = None, timeout: float = 4.0) -> dict | None:
    url = f"{BRIDGE_BASE_URL}{rota}"
    dados = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "X-Bridge-Token": BRIDGE_TOKEN}
    req = urllib.request.Request(url, data=dados, method=metodo, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            bruto = resp.read(500_000)
            return json.loads(bruto.decode("utf-8") or "{}")
    except urllib.error.HTTPError as http_err:
        try:
            bruto = http_err.read(500_000)
            return json.loads(bruto.decode("utf-8") or "{}")
        except Exception:
            return {"sucesso": False, "erro": f"HTTP {http_err.code}: {http_err.reason}"}
    except Exception:
        return None


def sincronizar_config_bridge() -> None:
    """Garante que o processo Node.js em execução tenha o token e a URL de webhook atuais."""
    _requisitar_bridge(
        "POST",
        "/config",
        payload={"webhook_url": _webhook_url_atual, "bridge_token": BRIDGE_TOKEN},
        timeout=1.5,
    )


def obter_status_bridge() -> dict:
    """Consulta o estado atual da Ponte Local e do QR Code."""
    node_bin, _ = localizar_node()
    dados = _requisitar_bridge("GET", "/status", timeout=2.0)
    if dados and isinstance(dados, dict):
        if dados.get("webhook_url") != _webhook_url_atual:
            sincronizar_config_bridge()
        return {
            "node_instalado": True,
            "bridge_rodando": True,
            "conectado": bool(dados.get("conectado")),
            "status": dados.get("status") or "desconectado",
            "numero": dados.get("numero") or "",
            "nome": dados.get("nome") or "",
            "qr_data_url": dados.get("qr_data_url") or "",
            "ultimo_erro": dados.get("ultimo_erro") or _erro_inicializacao,
        }

    if _instalando_npm:
        status_txt = "instalando_dependencias"
    elif not node_bin:
        status_txt = "node_ausente"
    else:
        status_txt = "parado"

    return {
        "node_instalado": bool(node_bin),
        "bridge_rodando": False,
        "conectado": False,
        "status": status_txt,
        "numero": "",
        "nome": "",
        "qr_data_url": "",
        "ultimo_erro": _erro_inicializacao,
    }


def _instalar_e_subir_em_background(node_bin: str, npm_bin: str | None) -> None:
    global _processo, _instalando_npm, _erro_inicializacao
    try:
        env = os.environ.copy()
        env["BRIDGE_PORT"] = str(BRIDGE_PORT)
        env["WHATSAPP_BRIDGE_TOKEN"] = BRIDGE_TOKEN
        env["FASTAPI_WEBHOOK_URL"] = _webhook_url_atual
        pasta_node = str(Path(node_bin).parent)
        if pasta_node not in env.get("PATH", ""):
            env["PATH"] = f"{pasta_node};{env.get('PATH', '')}"

        node_modules = BRIDGE_DIR / "node_modules" / "@whiskeysockets" / "baileys"
        if not node_modules.exists():
            if not npm_bin:
                _erro_inicializacao = "O npm não foi encontrado junto ao Node.js."
                return
            _instalando_npm = True
            _erro_inicializacao = ""
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                [npm_bin, "install", "--ignore-scripts", "--no-audit", "--no-fund"],
                cwd=str(BRIDGE_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=creation_flags,
            )
            _instalando_npm = False
            if res.returncode != 0:
                _erro_inicializacao = f"Falha ao instalar pacotes da ponte: {(res.stderr or '')[:200]}"
                return

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _processo = subprocess.Popen(
            [node_bin, "server.js"],
            cwd=str(BRIDGE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        _erro_inicializacao = ""
    except Exception as exc:
        _instalando_npm = False
        _erro_inicializacao = f"Erro ao iniciar ponte local: {exc}"
        logger.warning("Falha ao subir whatsapp_bridge: %s", exc)


def iniciar_bridge() -> dict:
    """Garante que o servidor da Ponte Local esteja rodando e retorna o status."""
    global _erro_inicializacao
    _erro_inicializacao = ""
    status_atual = obter_status_bridge()
    if status_atual["bridge_rodando"] or _instalando_npm:
        sincronizar_config_bridge()
        return status_atual

    node_bin, npm_bin = localizar_node()
    if not node_bin:
        return status_atual

    with _trava:
        if _processo is None or _processo.poll() is not None:
            threading.Thread(
                target=_instalar_e_subir_em_background,
                args=(node_bin, npm_bin),
                daemon=True,
            ).start()

    return obter_status_bridge()


def desconectar_bridge() -> dict:
    """Desconecta o aparelho atual e força a geração de um novo QR Code."""
    _requisitar_bridge("POST", "/logout", payload={}, timeout=5.0)
    return obter_status_bridge()


def enviar_via_bridge(telefone: str, texto: str) -> tuple[bool, str, str]:
    """
    Tenta enviar a mensagem diretamente pela Ponte Local conectada.
    Retorna (enviado, id_externo, erro).
    """
    sincronizar_config_bridge()
    dados = _requisitar_bridge(
        "POST",
        "/send",
        payload={"number": telefone, "text": texto},
        timeout=12.0,
    )
    if not dados:
        return False, "", "Ponte local não está respondendo."
    if dados.get("enviado"):
        return True, str(dados.get("id_externo") or ""), ""
    return False, "", str(dados.get("erro") or "WhatsApp desconectado.")


def enviar_imagem_via_bridge(
    telefone: str,
    imagem_bytes: bytes,
    legenda: str = "",
    mime_type: str = "image/jpeg",
) -> tuple[bool, str, str]:
    """Tenta enviar uma imagem diretamente pela Ponte Local conectada."""
    sincronizar_config_bridge()
    import base64
    b64 = base64.b64encode(imagem_bytes).decode("ascii") if imagem_bytes else ""
    dados = _requisitar_bridge(
        "POST",
        "/send-image",
        payload={
            "number": telefone,
            "caption": legenda,
            "image_base64": b64,
            "mime_type": mime_type or "image/jpeg",
        },
        timeout=20.0,
    )
    if not dados:
        return False, "", "Ponte local não está respondendo."
    if dados.get("enviado"):
        return True, str(dados.get("id_externo") or ""), ""
    return False, "", str(dados.get("erro") or "Falha ao enviar imagem pelo WhatsApp.")


def enviar_arquivo_via_bridge(
    telefone: str,
    arquivo_bytes: bytes,
    nome_arquivo: str = "documento.pdf",
    legenda: str = "",
    mime_type: str = "application/pdf",
    tipo_midia: str = "documento",
) -> tuple[bool, str, str]:
    """Tenta enviar um documento/arquivo diretamente pela Ponte Local conectada."""
    sincronizar_config_bridge()
    import base64
    b64 = base64.b64encode(arquivo_bytes).decode("ascii") if arquivo_bytes else ""
    dados = _requisitar_bridge(
        "POST",
        "/send-file",
        payload={
            "number": telefone,
            "file_base64": b64,
            "file_name": nome_arquivo,
            "caption": legenda,
            "mime_type": mime_type or "application/pdf",
            "media_type": tipo_midia or "documento",
        },
        timeout=25.0,
    )
    if not dados:
        return False, "", "Ponte local não está respondendo."
    if dados.get("enviado"):
        return True, str(dados.get("id_externo") or ""), ""
    return False, "", str(dados.get("erro") or "Falha ao enviar arquivo pelo WhatsApp.")


def requisitar_historico_bridge(
    jid: str,
    oldest_id: str | None = None,
    oldest_timestamp: int | None = None,
    oldest_from_me: bool = False,
    count: int = 50,
) -> dict:
    """Solicita ao WhatsApp conectado via QR Code a busca de mensagens anteriores sob demanda."""
    sincronizar_config_bridge()
    dados = _requisitar_bridge(
        "POST",
        "/fetch-history",
        payload={
            "jid": jid,
            "oldest_id": oldest_id or "",
            "oldest_timestamp": oldest_timestamp,
            "oldest_from_me": oldest_from_me,
            "count": count,
        },
        timeout=10.0,
    )
    return dados or {"sucesso": False, "erro": "Ponte local não está respondendo."}


def baixar_midia_mensagem_bridge(id_externo: str) -> dict:
    """Solicita à ponte o download da mídia de uma mensagem a partir do seu id_externo."""
    sincronizar_config_bridge()
    dados = _requisitar_bridge(
        "POST",
        "/download-media",
        payload={"id": id_externo},
        timeout=15.0,
    )
    return dados or {"sucesso": False, "erro": "Ponte local não está respondendo."}
