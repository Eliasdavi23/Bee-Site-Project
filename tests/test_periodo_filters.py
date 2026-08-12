from services.periodo_service import construir_filtro_periodo


def test_filtro_por_dia_especifico():
    condicao, params = construir_filtro_periodo(periodo="dia_especifico", data_especifica="2024-05-20")

    assert condicao == "strftime('%Y-%m-%d', p.data) = ?"
    assert params == ["2024-05-20"]


def test_filtro_por_mes_atual():
    condicao, params = construir_filtro_periodo(periodo="mes_atual")

    assert condicao == "strftime('%Y-%m', p.data) = ?"
    assert len(params) == 1
    assert params[0].count("-") == 1
