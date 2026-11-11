import os
from typing import Any, Iterable

from config.database import get_connection


def fetch_all_as_dicts(query: str, params: Iterable[Any] | None = None) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params or ()))
        colunas = [column[0] for column in cursor.description] if cursor.description else []
        return [dict(zip(colunas, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def parse_decimal(valor: Any, padrao: float = 0.0) -> float:
    """Converte números em formato brasileiro ('1.234,56', 'R$ 45,50') ou float/int para float."""
    if valor is None or valor == "":
        return padrao
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return padrao
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return padrao


def anexar_itens_em_lote(cursor, registros: list[dict]) -> list[dict]:
    """Anexa a lista `itens` a cada pedido ou orçamento usando uma única consulta SQL."""
    if not registros:
        return registros
    ids = [r["id"] for r in registros]
    placeholders = ",".join(["?"] * len(ids))
    cursor.execute(
        f"SELECT * FROM itens_pedido WHERE pedido_id IN ({placeholders}) ORDER BY id ASC",
        tuple(ids),
    )
    itens_por_pedido: dict[int, list[dict]] = {}
    for row in cursor.fetchall():
        item = dict(row)
        item["observacao"] = item.get("observacao") or ""
        itens_por_pedido.setdefault(item["pedido_id"], []).append(item)

    for reg in registros:
        reg["itens"] = itens_por_pedido.get(reg["id"], [])
    return registros


def listar_itens_pedido_db(pedido_id: int) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = ? ORDER BY id ASC", (pedido_id,))
        itens = []
        for row in cursor.fetchall():
            d = dict(row)
            d["observacao"] = d.get("observacao") or ""
            itens.append(d)
        return itens
    finally:
        conn.close()


def listar_imagens_pedido_db(pedido_id: int) -> list[str]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_arquivo FROM pedido_imagens WHERE pedido_id = ?", (pedido_id,))
        return [row["caminho_arquivo"] for row in cursor.fetchall()]
    finally:
        conn.close()


def remover_arquivo_local(caminho_relativo: str) -> None:
    path = (caminho_relativo or "").lstrip("/")
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
