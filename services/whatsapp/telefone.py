"""Normalização, validação e formatação de telefones para WhatsApp (foco em números do Brasil)."""
import os
import re
from urllib.parse import quote

DDI_BRASIL = "55"
_NAO_DIGITOS = re.compile(r"\D+")


def apenas_digitos(valor) -> str:
    return _NAO_DIGITOS.sub("", str(valor or ""))


def _ddd_padrao() -> str:
    ddd = apenas_digitos(os.getenv("WHATSAPP_DDD_PADRAO", "16"))
    return ddd[:2] if len(ddd) >= 2 and ddd[0] != "0" else "16"


def _validar_brasil(digitos: str) -> str | None:
    """Aceita 55 + DDD (2 dígitos, sem zero) + número de 8 ou 9 dígitos."""
    if not digitos.startswith(DDI_BRASIL) or len(digitos) not in (12, 13):
        return None
    ddd = digitos[2:4]
    if ddd[0] == "0":
        return None
    if len(digitos) == 13 and digitos[4] != "9":  # celular com 9 dígitos sempre começa com 9
        return None
    return digitos


def normalizar_telefone(valor, aceitar_sem_ddd: bool = False, permitir_id_whatsapp: bool = False) -> str | None:
    """
    Converte o que o funcionário digitar para o padrão internacional só com dígitos.

    Exemplos aceitos -> "5511988887777":
        "(11) 98888-7777", "11 9 8888 7777", "+55 11 98888-7777", "011 98888-7777"
    Se `aceitar_sem_ddd=True`, também aceita 8 ou 9 dígitos (ex.: "98888-7777") aplicando o DDD padrão.
    Se `permitir_id_whatsapp=True`, aceita identificadores numéricos internos do WhatsApp Multi-Device (LID 10-16 dígitos).
    """
    bruto = str(valor or "").strip()
    if not bruto:
        return None

    digitos = apenas_digitos(bruto)
    if not digitos:
        return None

    internacional = bruto.startswith("+") or digitos.startswith("00")

    if digitos.startswith("00"):
        digitos = digitos[2:]
    elif not internacional and digitos.startswith("0"):
        digitos = digitos.lstrip("0")  # zero de discagem interurbana
        if len(digitos) in (12, 13) and not digitos.startswith(DDI_BRASIL):
            digitos = digitos[2:]  # código de operadora (ex.: 0 21 11 9xxxx-xxxx)

    if internacional and not digitos.startswith(DDI_BRASIL):
        return digitos if 10 <= len(digitos) <= 15 else None

    if aceitar_sem_ddd and len(digitos) in (8, 9):
        digitos = DDI_BRASIL + _ddd_padrao() + digitos
    elif len(digitos) in (10, 11):
        digitos = DDI_BRASIL + digitos

    validado = _validar_brasil(digitos)
    if validado:
        return validado

    if permitir_id_whatsapp and 8 <= len(digitos) <= 16:
        return digitos

    return None


def chave_comparacao(valor) -> str | None:
    """
    Chave para descobrir se dois números são o mesmo contato.

    O WhatsApp às vezes entrega números do Brasil sem o 9º dígito, então
    comparamos DDD + últimos 8 dígitos.
    """
    numero = normalizar_telefone(valor)
    if not numero:
        return None
    if numero.startswith(DDI_BRASIL) and len(numero) in (12, 13):
        return numero[2:4] + numero[-8:]
    return numero


def formatar_exibicao(valor) -> str:
    numero = normalizar_telefone(valor)
    if numero and numero.startswith(DDI_BRASIL) and len(numero) in (12, 13):
        ddd, resto = numero[2:4], numero[4:]
        return f"+55 ({ddd}) {resto[:-4]}-{resto[-4:]}"
    if numero:
        return f"+{numero}"
    digitos = apenas_digitos(valor)
    if digitos and len(digitos) >= 13:
        return f"ID WhatsApp #{digitos[-6:]}"
    return str(valor or "").strip()


def link_whatsapp(telefone: str, texto: str = "") -> str:
    """Link oficial wa.me (universal para celular e desktop)."""
    numero = normalizar_telefone(telefone, aceitar_sem_ddd=True) or apenas_digitos(telefone)
    link = f"https://wa.me/{numero}"
    texto = (texto or "").strip()
    return f"{link}?text={quote(texto)}" if texto else link


def link_whatsapp_web(telefone: str, texto: str = "") -> str:
    """Link direto para o WhatsApp Web no navegador do PC (sem tela intermediária)."""
    numero = normalizar_telefone(telefone, aceitar_sem_ddd=True) or apenas_digitos(telefone)
    parametros = [f"phone={numero}"]
    texto = (texto or "").strip()
    if texto:
        parametros.append(f"text={quote(texto)}")
    return f"https://web.whatsapp.com/send?{'&'.join(parametros)}"
