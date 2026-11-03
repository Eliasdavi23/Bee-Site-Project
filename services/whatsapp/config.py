"""Configuração do WhatsApp lida do ambiente (.env). Nenhuma credencial fica no código."""
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("uvicorn.error")

PROVEDOR_LINK = "link"
PROVEDOR_EVOLUTION = "evolution"
PROVEDOR_CLOUD = "cloud"
PROVEDORES_VALIDOS = (PROVEDOR_LINK, PROVEDOR_EVOLUTION, PROVEDOR_CLOUD)


def _env(nome: str, padrao: str = "") -> str:
    return (os.getenv(nome) or padrao).strip()


@dataclass(frozen=True)
class ConfigWhatsApp:
    provedor_solicitado: str
    webhook_token: str
    evolution_url: str
    evolution_api_key: str
    evolution_instancia: str
    cloud_token: str
    cloud_phone_number_id: str
    cloud_app_secret: str
    cloud_verify_token: str
    cloud_api_versao: str
    timeout_segundos: float

    @property
    def pendencias(self) -> list[str]:
        """Lista o que falta no .env para o provedor escolhido funcionar."""
        if self.provedor_solicitado == PROVEDOR_EVOLUTION:
            obrigatorios = {
                "WHATSAPP_EVOLUTION_URL": self.evolution_url,
                "WHATSAPP_EVOLUTION_API_KEY": self.evolution_api_key,
                "WHATSAPP_EVOLUTION_INSTANCIA": self.evolution_instancia,
                "WHATSAPP_WEBHOOK_TOKEN": self.webhook_token,
            }
        elif self.provedor_solicitado == PROVEDOR_CLOUD:
            obrigatorios = {
                "WHATSAPP_CLOUD_TOKEN": self.cloud_token,
                "WHATSAPP_CLOUD_PHONE_NUMBER_ID": self.cloud_phone_number_id,
                "WHATSAPP_CLOUD_APP_SECRET": self.cloud_app_secret,
                "WHATSAPP_CLOUD_VERIFY_TOKEN": self.cloud_verify_token,
            }
        else:
            return []
        return [nome for nome, valor in obrigatorios.items() if not valor]

    @property
    def provedor(self) -> str:
        """Provedor efetivo: se faltar configuração, cai com segurança para o modo link."""
        if self.provedor_solicitado != PROVEDOR_LINK and self.pendencias:
            return PROVEDOR_LINK
        return self.provedor_solicitado

    @property
    def automatico(self) -> bool:
        return self.provedor != PROVEDOR_LINK


def carregar_config() -> ConfigWhatsApp:
    provedor = _env("WHATSAPP_PROVIDER", PROVEDOR_LINK).lower()
    if provedor not in PROVEDORES_VALIDOS:
        logger.warning("WHATSAPP_PROVIDER inválido (%s). Usando modo 'link'.", provedor)
        provedor = PROVEDOR_LINK

    try:
        timeout = min(max(float(_env("WHATSAPP_TIMEOUT_SEGUNDOS", "15")), 3.0), 60.0)
    except ValueError:
        timeout = 15.0

    return ConfigWhatsApp(
        provedor_solicitado=provedor,
        webhook_token=_env("WHATSAPP_WEBHOOK_TOKEN"),
        evolution_url=_env("WHATSAPP_EVOLUTION_URL").rstrip("/"),
        evolution_api_key=_env("WHATSAPP_EVOLUTION_API_KEY"),
        evolution_instancia=_env("WHATSAPP_EVOLUTION_INSTANCIA"),
        cloud_token=_env("WHATSAPP_CLOUD_TOKEN"),
        cloud_phone_number_id=_env("WHATSAPP_CLOUD_PHONE_NUMBER_ID"),
        cloud_app_secret=_env("WHATSAPP_CLOUD_APP_SECRET"),
        cloud_verify_token=_env("WHATSAPP_CLOUD_VERIFY_TOKEN"),
        cloud_api_versao=_env("WHATSAPP_CLOUD_API_VERSION", "v23.0"),
        timeout_segundos=timeout,
    )
