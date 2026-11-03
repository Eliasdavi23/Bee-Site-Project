"""Proteções anti-gorila: limite de taxa, limpeza de texto e validação de origem dos webhooks."""
import hashlib
import hmac
import re
import threading
import time
from collections import defaultdict, deque

LIMITE_TEXTO_MENSAGEM = 2000
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_LINHAS_EM_EXCESSO = re.compile(r"\n{4,}")


def limpar_texto(texto, limite: int = LIMITE_TEXTO_MENSAGEM) -> str:
    """Remove caracteres de controle, excesso de linhas em branco e corta textos gigantes."""
    texto = _CONTROLE.sub("", str(texto or "")).replace("\r\n", "\n").replace("\r", "\n")
    texto = _LINHAS_EM_EXCESSO.sub("\n\n\n", texto).strip()
    return texto[:limite].rstrip()


def token_valido(recebido: str | None, esperado: str) -> bool:
    """Comparação em tempo constante. Sem token configurado, nada é aceito."""
    if not esperado or not recebido:
        return False
    return hmac.compare_digest(recebido.encode("utf-8"), esperado.encode("utf-8"))


def assinatura_meta_valida(corpo: bytes, cabecalho: str | None, app_secret: str) -> bool:
    """Valida o cabeçalho X-Hub-Signature-256 enviado pela Meta (WhatsApp Cloud API)."""
    if not app_secret or not cabecalho or not cabecalho.startswith("sha256="):
        return False
    esperado = hmac.new(app_secret.encode("utf-8"), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(cabecalho[len("sha256="):], esperado)


class LimitadorTaxa:
    """Janela deslizante em memória: no máximo `max_eventos` por `janela_segundos` para cada chave."""

    def __init__(self, max_eventos: int, janela_segundos: float):
        self.max_eventos = max_eventos
        self.janela = janela_segundos
        self._eventos: dict[str, deque] = defaultdict(deque)
        self._trava = threading.Lock()

    def permitir(self, chave: str) -> bool:
        agora = time.monotonic()
        with self._trava:
            fila = self._eventos[chave]
            while fila and agora - fila[0] > self.janela:
                fila.popleft()
            if len(fila) >= self.max_eventos:
                return False
            fila.append(agora)
            if len(self._eventos) > 5000:  # evita crescer sem limite na memória
                vencidas = [k for k, v in self._eventos.items() if not v or agora - v[-1] > self.janela]
                for antiga in vencidas:
                    del self._eventos[antiga]
            return True

    def limpar(self) -> None:
        with self._trava:
            self._eventos.clear()
