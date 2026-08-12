from datetime import datetime, timedelta


def construir_filtro_periodo(periodo: str = "mes_atual", data_especifica: str | None = None, table_alias: str = "p"):
    hoje = datetime.now()
    coluna_ref = f"{table_alias}.data" if table_alias else "data"

    if periodo == "dia_especifico" and data_especifica:
        return f"strftime('%Y-%m-%d', {coluna_ref}) = ?", [data_especifica]

    if periodo == "mes_atual":
        return f"strftime('%Y-%m', {coluna_ref}) = ?", [hoje.strftime('%Y-%m')]

    if periodo == "mes_anterior":
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes_ant = primeiro_dia_mes - timedelta(days=1)
        return f"strftime('%Y-%m', {coluna_ref}) = ?", [ultimo_dia_mes_ant.strftime('%Y-%m')]

    if periodo == "7_dias":
        data_limite = (hoje - timedelta(days=7)).strftime('%Y-%m-%d')
        return f"{coluna_ref} >= ?", [f"{data_limite} 00:00:00"]

    if periodo == "ano":
        return f"strftime('%Y', {coluna_ref}) = ?", [hoje.strftime('%Y')]

    return f"strftime('%Y-%m', {coluna_ref}) = ?", [hoje.strftime('%Y-%m')]
