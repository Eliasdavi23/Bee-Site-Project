"""Normalização, validação e formatação de telefones para WhatsApp (foco em números do Brasil)."""
import re
from urllib.parse import quote

DDI_BRASIL = "55"
_NAO_DIGITOS = re.compile(r"\D+")


def apenas_digitos(valor) -> str:
    return _NAO_DIGITOS.sub("", str(valor or ""))


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


def normalizar_telefone(valor) -> str | None:
    """
    Converte o que o funcionário digitar para o padrão internacional só com dígitos.

    Exemplos aceitos -> "5511988887777":
        "(11) 98888-7777", "11 9 8888 7777", "+55 11 98888-7777", "011 98888-7777"
    Retorna None quando não é possível ter certeza de que o número é válido.
    """
    bruto = str(valor or "").strip()
    if not bruto:
        return None

    digitos = apenas_digitos(bruto)
    internacional = bruto.startswith("+") or digitos.startswith("00")

    if digitos.startswith("00"):
        digitos = digitos[2:]
    elif not internacional and digitos.startswith("0"):
        digitos = digitos.lstrip("0")  # zero de discagem interurbana
        if len(digitos) in (12, 13) and not digitos.startswith(DDI_BRASIL):
            digitos = digitos[2:]  # código de operadora (ex.: 0 21 11 9xxxx-xxxx)

    if internacional and not digitos.startswith(DDI_BRASIL):
        return digitos if 10 <= len(digitos) <= 15 else None

    if len(digitos) in (10, 11):
        digitos = DDI_BRASIL + digitos

    return _validar_brasil(digitos)


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
    if not numero:
        return str(valor or "").strip()
    if numero.startswith(DDI_BRASIL) and len(numero) in (12, 13):
        ddd, resto = numero[2:4], numero[4:]
        return f"+55 ({ddd}) {resto[:-4]}-{resto[-4:]}"
    return f"+{numero}"


def link_whatsapp(telefone: str, texto: str = "") -> str:
    """Link oficial de clique para conversar (abre o WhatsApp Web/App com o texto preenchido)."""
    numero = normalizar_telefone(telefone) or apenas_digitos(telefone)
    link = f"https://wa.me/{numero}"
    texto = (texto or "").strip()
    return f"{link}?text={quote(texto)}" if texto else link
