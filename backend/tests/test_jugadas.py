"""Pruebas de propiedades de los endpoints de filtros y listado (routers/jugadas.py)."""
from __future__ import annotations

from backend import datos
from backend.tests import generadores
from backend.tests.generadores import repetir


# Feature: failed-plays-coach-app, Property 5
def test_propiedad_5_lista_de_equipos_es_el_conjunto_ordenado_con_fallas(cliente, poner_datos):
    """Property 5: Team list is the sorted set of teams with failed plays.

    **Validates: Requirements 3.2, 3.4**
    """
    iteraciones = {"con_fallas": 0}

    def prueba(rng):
        jugadas = generadores.generar_jugadas(rng, n=rng.randint(1, 40))
        estado = poner_datos(jugadas)
        esperado = sorted({f["possessionTeam"] for _, f in jugadas.iterrows()
                           if generadores.razon_referencia(f) is not None})
        if not esperado:
            # Sin jugadas fallidas el endpoint responde 500 (3.5); no aplica la propiedad.
            return
        iteraciones["con_fallas"] += 1
        resp = cliente.get("/api/filtros")
        assert resp.status_code == 200
        equipos = resp.json()["equipos"]
        abreviaturas = [e["abbr"] for e in equipos]
        assert abreviaturas == esperado
        assert abreviaturas == sorted(abreviaturas)
        assert len(set(abreviaturas)) == len(abreviaturas)
        assert abreviaturas == estado["_equipos_con_fallas"]
        for e in equipos:
            assert e["nombre"] == datos.EQUIPOS.get(e["abbr"])

    repetir(prueba, n=120)
    assert iteraciones["con_fallas"] >= 100


CAMPOS_JUGADA = {
    "gameId", "playId", "equipo", "rival", "down", "yardsToGo", "razon",
    "descripcion", "formacion", "personal", "cobertura",
}


# Feature: failed-plays-coach-app, Property 6
def test_propiedad_6_listado_devuelve_exactamente_las_jugadas_coincidentes_en_orden_fijo(cliente, poner_datos):
    """Property 6: Listing returns exactly the matching plays in a fixed order.

    **Validates: Requirements 4.1, 4.2, 4.3, 4.6, 4.7**
    """
    razones = ["incompleto", "intercepcion", "sack", "sin_conversion", "perdida_de_yardas"]
    estadisticas = {"con_resultados": 0, "con_filtros": 0}

    def prueba(rng):
        jugadas = generadores.generar_jugadas(rng, n=rng.randint(1, 40))
        poner_datos(jugadas)
        fallidas = [(f, generadores.razon_referencia(f)) for _, f in jugadas.iterrows()]
        fallidas = [(f, r) for f, r in fallidas if r is not None]

        params = {}
        if rng.random() < 0.6:
            params["down"] = rng.choice([1, 2, 3, 4])
        if rng.random() < 0.6:
            params["razon"] = rng.choice(razones)
        if rng.random() < 0.6:
            candidatos = sorted(set(jugadas["possessionTeam"])) + ["XYZ", "ZZZ"]
            equipo = rng.choice(candidatos)
            if rng.random() < 0.2:
                equipo = equipo.lower()  # coincidencia sensible a mayúsculas
            params["equipo"] = equipo

        esperado = sorted(
            (int(f["gameId"]), int(f["playId"]))
            for f, r in fallidas
            if ("down" not in params or int(f["down"]) == params["down"])
            and ("razon" not in params or r == params["razon"])
            and ("equipo" not in params or f["possessionTeam"] == params["equipo"])
        )

        resp = cliente.get("/api/jugadas", params=params)
        assert resp.status_code == 200
        cuerpo = resp.json()
        assert [(j["gameId"], j["playId"]) for j in cuerpo] == esperado
        for j in cuerpo:
            assert set(j) == CAMPOS_JUGADA
            if "down" in params:
                assert j["down"] == params["down"]
            if "razon" in params:
                assert j["razon"] == params["razon"]
            if "equipo" in params:
                assert j["equipo"] == params["equipo"]
        assert cliente.get("/api/jugadas", params=params).json() == cuerpo

        if params:
            estadisticas["con_filtros"] += 1
        if cuerpo:
            estadisticas["con_resultados"] += 1

    repetir(prueba, n=120)
    assert estadisticas["con_filtros"] >= 100
    assert estadisticas["con_resultados"] >= 20


# Feature: failed-plays-coach-app, Property 7
def test_propiedad_7_valores_de_filtro_invalidos_se_rechazan(cliente, poner_datos):
    """Property 7: Invalid filter values are rejected.

    **Validates: Requirements 4.5**
    """
    razones = {"incompleto", "intercepcion", "sack", "sin_conversion", "perdida_de_yardas"}
    letras = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-."

    def down_invalido(rng):
        tipo = rng.choice(["fuera_de_rango", "texto", "decimal"])
        if tipo == "fuera_de_rango":
            return str(rng.choice([rng.randint(-1000, 0), rng.randint(5, 1000)]))
        if tipo == "texto":
            return "".join(rng.choice(letras) for _ in range(rng.randint(1, 8)))
        return f"{rng.randint(1, 4)}.{rng.randint(1, 9)}"

    def razon_invalida(rng):
        while True:
            valor = "".join(rng.choice(letras + "0123456789 ") for _ in range(rng.randint(1, 12)))
            if valor.strip() and valor not in razones:
                return valor

    def prueba(rng):
        poner_datos(generadores.generar_jugadas(rng, n=rng.randint(1, 30)))
        casos = []
        if rng.random() < 0.5:
            casos.append(("down", down_invalido(rng)))
        if not casos or rng.random() < 0.5:
            casos.append(("razon", razon_invalida(rng)))
        params = dict(casos)
        if rng.random() < 0.3:
            params["equipo"] = "KC"  # filtro válido junto a uno inválido

        resp = cliente.get("/api/jugadas", params=params)
        assert resp.status_code == 422, params
        cuerpo = resp.json()
        assert not isinstance(cuerpo, list)
        mensaje = str(cuerpo["detail"])
        # El mensaje está en español y nombra al menos un parámetro inválido.
        assert any(f"'{nombre}'" in mensaje for nombre in params if nombre in ("down", "razon"))
        assert "parámetro" in mensaje.lower()
        assert "gameId" not in resp.text

    repetir(prueba, n=120)


# Feature: failed-plays-coach-app, Property 29
def test_propiedad_29_sin_nan_en_la_salida_json(cliente, poner_datos):
    """Property 29: No NaN in JSON output.

    **Validates: Requirements 12.4**
    """
    import math

    import pandas as pd

    columnas = ["offenseFormation", "personnelO", "pff_passCoverage"]
    ausentes = [math.nan, None, pd.NA]
    estadisticas = {"con_nulos": 0}

    def prueba(rng):
        jugadas = generadores.generar_jugadas(rng, n=rng.randint(1, 40)).astype(object)
        for col in columnas:
            for i in jugadas.index:
                if rng.random() < 0.4:
                    jugadas.at[i, col] = rng.choice(ausentes)
        poner_datos(jugadas)

        resp = cliente.get("/api/jugadas")
        assert resp.status_code == 200
        for token in ("NaN", "Infinity"):
            assert token not in resp.text
        cuerpo = resp.json()  # JSON estricto: sin NaN ni Infinity
        for j in cuerpo:
            for valor in j.values():
                assert not (isinstance(valor, float) and (math.isnan(valor) or math.isinf(valor)))
        esperado = {(int(f["gameId"]), int(f["playId"])): f for _, f in jugadas.iterrows()
                    if generadores.razon_referencia(f) is not None}
        for j in cuerpo:
            fila = esperado[(j["gameId"], j["playId"])]
            for campo, col in (("formacion", columnas[0]), ("personal", columnas[1]), ("cobertura", columnas[2])):
                if pd.isna(fila[col]):
                    assert j[campo] is None
                    estadisticas["con_nulos"] += 1
                else:
                    assert j[campo] == fila[col]

    repetir(prueba, n=120)
    assert estadisticas["con_nulos"] >= 100
