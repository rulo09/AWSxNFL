"""Pruebas de propiedades de las sugerencias (Persona A)."""
from __future__ import annotations

import pandas as pd

from backend import datos
from backend.tests import generadores
from backend.routers.similares import construir_comparacion, generar_sugerencias
from backend.tests.generadores import (
    COBERTURAS,
    FORMACIONES,
    PERSONALES,
    generar_scouting,
    repetir,
)

COLUMNAS = ["gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
            "formacion", "personal", "cobertura"]
PLANTILLAS_ES = (
    "Considerar la formación",
    "Considerar el personal",
    "Tener en cuenta la cobertura rival",
    "Considerar un receptor alineado en",
    "Ganancia promedio de",
)
CONFIANZAS = {"alta", "media", "baja"}


def _similares(rng, claves) -> pd.DataFrame:
    filas = [
        {
            "gameId": g, "playId": p, "equipo": "XYZ", "rival": "ABC",
            "yardsToGo": rng.randint(1, 15), "playResult": rng.randint(0, 40),
            "formacion": rng.choice(FORMACIONES + [None]),
            "personal": rng.choice(PERSONALES + [None]),
            "cobertura": rng.choice(COBERTURAS + [None]),
        }
        for g, p in claves
    ]
    return pd.DataFrame(filas, columns=COLUMNAS)


def test_propiedad_21_formato_de_sugerencias(monkeypatch):
    """Feature: failed-plays-coach-app, Property 21

    **Validates: Requirements 9.1, 9.5**

    Para cualquier conjunto de similares, cada sugerencia tiene `texto` y
    `evidencia` no vacíos de hasta 280 caracteres, en español, `nMuestra` entero
    de al menos 1 (y no mayor que la cantidad de similares) y `confianza`.
    """
    visto = {"sugerencias": 0}

    def prueba(rng):
        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(2, 40))]
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, claves=claves, n=rng.randint(0, 100)))
        solicitada, otras = claves[0], claves[1:]
        similares = _similares(rng, otras)
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": PERSONALES[0],
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])
        comparacion = construir_comparacion(jugada, similares, grupo, 2)

        sugerencias = generar_sugerencias(jugada, similares, comparacion)

        assert len(sugerencias) <= 5
        for s in sugerencias:
            assert isinstance(s["texto"], str) and 0 < len(s["texto"]) <= 280
            assert isinstance(s["evidencia"], str) and 0 < len(s["evidencia"]) <= 280
            assert s["texto"].startswith(PLANTILLAS_ES)
            assert "jugadas efectivas similares" in s["evidencia"]
            assert isinstance(s["nMuestra"], int) and not isinstance(s["nMuestra"], bool)
            assert 1 <= s["nMuestra"] <= len(similares)
            assert s.get("confianza") in CONFIANZAS
        visto["sugerencias"] += len(sugerencias)

    repetir(prueba, n=100)
    assert visto["sugerencias"] > 0


def _esperada(n: int) -> str:
    return "baja" if n <= 4 else "media" if n <= 14 else "alta"


def test_propiedad_22_etiqueta_de_confianza_sigue_el_tamano_de_muestra(monkeypatch):
    """Feature: failed-plays-coach-app, Property 22

    **Validates: Requirements 9.2, 9.3**

    Para cualquier n >= 1, `etiqueta_confianza(n)` es baja (1-4), media (5-14) o
    alta (15 o más), y cada sugerencia generada lleva la etiqueta que
    corresponde a su `nMuestra`.
    """
    from backend.routers.similares import etiqueta_confianza

    for n in (1, 4, 5, 14, 15, 16):
        assert etiqueta_confianza(n) == _esperada(n)

    visto = {"sugerencias": 0, "etiquetas": set()}

    def prueba(rng):
        n = rng.choice([rng.randint(1, 4), rng.randint(5, 14), rng.randint(15, 500)])
        assert etiqueta_confianza(n) == _esperada(n)

        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(2, 40))]
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, claves=claves, n=rng.randint(0, 100)))
        solicitada, otras = claves[0], claves[1:]
        similares = _similares(rng, otras)
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": PERSONALES[0],
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])
        comparacion = construir_comparacion(jugada, similares, grupo, 2)

        for s in generar_sugerencias(jugada, similares, comparacion):
            assert s["confianza"] == _esperada(s["nMuestra"])
            visto["etiquetas"].add(s["confianza"])
            visto["sugerencias"] += 1

    repetir(prueba, n=150)
    assert visto["sugerencias"] > 0


def test_propiedad_23_cantidad_y_orden_de_sugerencias(monkeypatch):
    """Feature: failed-plays-coach-app, Property 23

    **Validates: Requirements 9.4**

    Para cualquier solicitud, se devuelven como máximo 5 sugerencias, ordenadas
    por `nMuestra` descendente; las de igual `nMuestra` conservan el orden de
    generación (formación, personal, cobertura, alineación, ganancia promedio).
    """
    orden_generacion = {p: i for i, p in enumerate(PLANTILLAS_ES)}
    visto = {"sugerencias": 0, "empates": 0}

    def prueba(rng):
        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(2, 40))]
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, claves=claves, n=rng.randint(0, 100)))
        solicitada, otras = claves[0], claves[1:]
        similares = _similares(rng, otras)
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": PERSONALES[0],
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])
        comparacion = construir_comparacion(jugada, similares, grupo, 2)

        sugerencias = generar_sugerencias(jugada, similares, comparacion)

        assert len(sugerencias) <= 5
        indices = [
            next(i for p, i in orden_generacion.items() if s["texto"].startswith(p))
            for s in sugerencias
        ]
        for a, b, ia, ib in zip(sugerencias, sugerencias[1:], indices, indices[1:]):
            assert a["nMuestra"] >= b["nMuestra"]
            if a["nMuestra"] == b["nMuestra"]:
                assert ia < ib
                visto["empates"] += 1
        visto["sugerencias"] += len(sugerencias)

    repetir(prueba, n=150)
    assert visto["sugerencias"] > 0
    assert visto["empates"] > 0


def test_propiedad_24_muestras_acotadas_por_los_similares(monkeypatch):
    """Feature: failed-plays-coach-app, Property 24

    **Validates: Requirements 9.9**

    Para cualquier respuesta, cada `nMuestra` es como máximo la cantidad de
    jugadas en `similares`.
    """
    visto = {"sugerencias": 0}

    def prueba(rng):
        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(2, 40))]
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, claves=claves, n=rng.randint(0, 100)))
        solicitada, otras = claves[0], claves[1:]
        similares = _similares(rng, otras)
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": PERSONALES[0],
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])
        comparacion = construir_comparacion(jugada, similares, grupo, 2)

        for s in generar_sugerencias(jugada, similares, comparacion):
            assert s["nMuestra"] <= len(similares)
            visto["sugerencias"] += 1

    repetir(prueba, n=150)
    assert visto["sugerencias"] > 0


def test_propiedad_25_las_sugerencias_son_deterministas(cliente, poner_datos):
    """Feature: failed-plays-coach-app, Property 25

    **Validates: Requirements 9.10**

    Para cualquier solicitud, dos respuestas sobre los mismos datos, y una más
    con las filas en orden aleatorio, son idénticas (`similares`, `sugerencias`
    y `criteriosRelajados`), incluso al barajar también las filas de scouting.
    """
    visto = {"con_sugerencias": 0, "barajadas": 0}

    def prueba(rng):
        # Sin NaN numéricos: esta propiedad solo mide determinismo (9.10).
        jugadas = generadores.generar_jugadas(rng, n=rng.randint(100, 300), con_invalidas=False)
        claves = [(int(g), int(p)) for g, p in zip(jugadas["gameId"], jugadas["playId"])]
        pff = generar_scouting(rng, claves=claves, n=rng.randint(50, 400))
        # La jugada solicitada tiene down, yardsToGo y playResult válidos, como en los datos reales.
        validas = jugadas.dropna(subset=["down", "yardsToGo", "playResult"])
        validas = validas[validas["down"] >= 1]
        fila = validas.iloc[rng.randrange(len(validas))]
        g, p = int(fila["gameId"]), int(fila["playId"])
        url = f"/api/jugadas/{g}/{p}/similares"
        params = {"misma_cobertura": rng.random() < 0.3}

        poner_datos(jugadas, pff)
        r1 = cliente.get(url, params=params)
        r2 = cliente.get(url, params=params)
        assert r1.status_code == 200
        assert r1.json() == r2.json()

        semilla = rng.randint(0, 10**6)
        poner_datos(
            jugadas.sample(frac=1, random_state=semilla),
            pff.sample(frac=1, random_state=semilla),
        )
        r3 = cliente.get(url, params=params)
        assert r3.status_code == 200
        c1, c3 = r1.json(), r3.json()
        assert c1["similares"] == c3["similares"]
        assert c1["sugerencias"] == c3["sugerencias"]
        assert c1["criteriosRelajados"] == c3["criteriosRelajados"]
        assert c1 == c3
        visto["barajadas"] += 1
        visto["con_sugerencias"] += len(c1["sugerencias"]) > 0

    repetir(prueba, n=100)
    assert visto["barajadas"] == 100
    assert visto["con_sugerencias"] > 0, "el generador nunca produjo sugerencias"
