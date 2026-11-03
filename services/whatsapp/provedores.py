"""
Provedores de envio do WhatsApp.

- link       -> não envia sozinho: gera o link wa.me para o funcionário clicar (sem conta externa)
- evolution  -> Evolution API (instalada no seu PC/servidor, conecta via QR Code)
- cloud      -> WhatsApp Cloud API oficial da Meta

Todos devolvem um ResultadoEnvio com o link wa.me como plano B,
assim o atendimento nunca trava se o envio automático falhar.
"""
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote

from services.whatsapp import config as cfg
from services.whatsapp.telefone import link_whatsapp

logger = logging.getLogger("uvicorn.error")


@dataclass
class ResultadoEnvio:
    enviado: bool          # True = saiu automaticamente pela API
    link: str              # link wa.me sempre disponível
    id_externo: str = ""
    erro: str = ""


class ErroProvedor(Exception):
    pass


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    corpo = json.dumps(payload).encode("utf-8")
    requisicao = urllib.request.Request(
        url, data=corpo, method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
            bruto = resposta.read(1_000_000)
    except urllib.error.HTTPError as exc:
        # Não registra corpo/cabeçalhos para não vazar tokens nos logs
        raise ErroProvedor(f"O provedor recusou o envio (HTTP {exc.code}).") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ErroProvedor("Não foi possível conectar ao provedor do WhatsApp.") from None
    try:
        return json.loads(bruto.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


class ProvedorLink:
    nome = cfg.PROVEDOR_LINK
    automatico = False

    def enviar_texto(self, telefone: str, texto: str) -> ResultadoEnvio:
        return ResultadoEnvio(enviado=False, link=link_whatsapp(telefone, texto))


class ProvedorEvolution:
    nome = cfg.PROVEDOR_EVOLUTION
    automatico = True

    def __init__(self, conf: cfg.ConfigWhatsApp):
        self.conf = conf

    def enviar_texto(self, telefone: str, texto: str) -> ResultadoEnvio:
        link = link_whatsapp(telefone, texto)
        url = f"{self.conf.evolution_url}/message/sendText/{quote(self.conf.evolution_instancia, safe='')}"
        try:
            dados = _post_json(
                url, {"number": telefone, "text": texto},
                {"apikey": self.conf.evolution_api_key}, self.conf.timeout_segundos,
            )
        except ErroProvedor as exc:
            logger.warning("Evolution API: %s", exc)
            return ResultadoEnvio(enviado=False, link=link, erro=str(exc))
        id_externo = str(((dados.get("key") or {}).get("id")) or "")
        return ResultadoEnvio(enviado=True, link=link, id_externo=id_externo)


class ProvedorCloud:
    nome = cfg.PROVEDOR_CLOUD
    automatico = True

    def __init__(self, conf: cfg.ConfigWhatsApp):
        self.conf = conf

    def enviar_texto(self, telefone: str, texto: str) -> ResultadoEnvio:
        link = link_whatsapp(telefone, texto)
        url = (
            f"https://graph.facebook.com/{self.conf.cloud_api_versao}/"
            f"{quote(self.conf.cloud_phone_number_id, safe='')}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": telefone,
            "type": "text",
            "text": {"preview_url": False, "body": texto},
        }
        try:
            dados = _post_json(
                url, payload,
                {"Authorization": f"Bearer {self.conf.cloud_token}"}, self.conf.timeout_segundos,
            )
        except ErroProvedor as exc:
            # Observação: fora da janela de 24h após a última mensagem do cliente,
            # a Meta só aceita mensagens de modelo (template) aprovadas.
            logger.warning("WhatsApp Cloud API: %s", exc)
            return ResultadoEnvio(enviado=False, link=link, erro=str(exc))
        mensagens = dados.get("messages") or [{}]
        return ResultadoEnvio(enviado=True, link=link, id_externo=str(mensagens[0].get("id") or ""))


def obter_provedor(conf: cfg.ConfigWhatsApp | None = None):
    conf = conf or cfg.carregar_config()
    if conf.provedor == cfg.PROVEDOR_EVOLUTION:
        return ProvedorEvolution(conf)
    if conf.provedor == cfg.PROVEDOR_CLOUD:
        return ProvedorCloud(conf)
    return ProvedorLink()
