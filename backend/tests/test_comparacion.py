"""Pruebas de propiedades de la comparación de jugadas similares (Persona A)."""
from __future__ import annotations

import pandas as pd

from backend import datos
from backend.routers.similares import construir_comparacion
from backend.tests import generadores
from backend.tests.generadores import POSICIONES_RUTA, generar_scouting, repetir


def test_propiedad_17_datos_de_ruta_solo_corredores_de_ruta(monkeypatch):
    """Feature: failed-plays-coach-app, Property 17

    **Validates: Requirements 8.1, 8.2**

    Para cualquier tabla de scouting con todos los roles y posiciones, los datos
    de ruta de la comparación son exactamente las filas con `pff_role` igual a
    `Pass Route` y posición en WR, TE, RB o FB.
    """
    visto = {"alineaciones": 0, "excluidas": 0}

    def prueba(rng):
        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(3, 8))]
        pff = generar_scouting(rng, claves=claves, n=rng.randint(0, 120))
        monkeypatch.setattr(datos, "_pff", pff)

        solicitada = claves[0]
        otras = [c for c in claves[1:] if rng.random() < 0.8]
        similares = pd.DataFrame(
            [
                {
                    "gameId": g, "playId": p, "equipo": "XYZ", "rival": "ABC", "yardsToGo": 5,
                    "playResult": 7, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR", "cobertura": None,
                }
                for g, p in otras
            ],
            columns=["gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
                     "formacion", "personal", "cobertura"],
        )
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR",
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])

        comp = construir_comparacion(jugada, similares, grupo, 2)

        # Referencia independiente: filas de ruta de corredores con alineación conocida.
        def es_ruta(f) -> bool:
            return (
                f["pff_role"] == "Pass Route"
                and f["officialPosition"] in POSICIONES_RUTA
                and pd.notna(f["pff_positionLinedUp"])
            )

        filas = [f for _, f in pff.iterrows()]
        hay_pff = any((f["gameId"], f["playId"]) == solicitada for f in filas)
        assert comp["rutasDisponibles"] == hay_pff

        if not hay_pff:
            assert comp["alineaciones"] == []
            assert comp["solicitada"]["alineacion"] == []
            return

        # Alineación de la jugada solicitada (8.2).
        esperada_sol = sorted(
            str(f["pff_positionLinedUp"]) for f in filas if (f["gameId"], f["playId"]) == solicitada and es_ruta(f)
        )
        assert comp["solicitada"]["alineacion"] == esperada_sol

        # Datos de ruta de las similares (8.1): conteo por posición alineada.
        claves_sim = set(otras)
        conteo: dict[str, int] = {}
        for f in filas:
            if (f["gameId"], f["playId"]) in claves_sim and es_ruta(f):
                conteo[str(f["pff_positionLinedUp"])] = conteo.get(str(f["pff_positionLinedUp"]), 0) + 1
            elif (f["gameId"], f["playId"]) in claves_sim:
                visto["excluidas"] += 1
        esperadas = sorted(conteo.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        obtenidas = [(a["posicion"], a["conteo"]) for a in comp["alineaciones"]]
        assert obtenidas == esperadas, f"obtenidas {obtenidas}, esperadas {esperadas}"
        assert all(a["rol"] == "Pass Route" for a in comp["alineaciones"])
        visto["alineaciones"] += len(obtenidas)

    repetir(prueba, n=100, semilla=generadores.SEMILLA)
    assert visto["alineaciones"] > 0, "el generador nunca produjo alineaciones"
    assert visto["excluidas"] > 0, "el generador nunca produjo filas que deban excluirse"


def test_propiedad_18_top_alineaciones_son_las_10_combinaciones_mas_frecuentes(monkeypatch):
    """Feature: failed-plays-coach-app, Property 18

    **Validates: Requirements 8.3**

    Para cualquier dato de ruta, las alineaciones devueltas son como máximo 10,
    sus conteos no aumentan, los empates se ordenan alfabéticamente por
    `pff_positionLinedUp` y cada conteo es el número de filas con esa combinación.
    """
    visto = {"con_diez": 0, "con_empate": 0}

    def prueba(rng):
        base = 2021090000
        claves = [(base + 1, p) for p in range(1, rng.randint(3, 10))]
        pff = generar_scouting(rng, claves=claves, n=rng.randint(20, 250))
        monkeypatch.setattr(datos, "_pff", pff)

        solicitada = claves[0]
        otras = claves[1:]
        similares = pd.DataFrame(
            [
                {
                    "gameId": g, "playId": p, "equipo": "XYZ", "rival": "ABC", "yardsToGo": 5,
                    "playResult": 7, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR", "cobertura": None,
                }
                for g, p in otras
            ],
            columns=["gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
                     "formacion", "personal", "cobertura"],
        )
        jugada = {
            "gameId": solicitada[0], "playId": solicitada[1], "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR",
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])

        comp = construir_comparacion(jugada, similares, grupo, 2)
        if not comp["rutasDisponibles"]:
            return
        obtenidas = comp["alineaciones"]

        # Referencia independiente: conteo de filas por posición alineada.
        claves_sim = set(otras)
        conteo: dict[str, int] = {}
        for _, f in pff.iterrows():
            if (
                (f["gameId"], f["playId"]) in claves_sim
                and f["pff_role"] == "Pass Route"
                and f["officialPosition"] in POSICIONES_RUTA
                and pd.notna(f["pff_positionLinedUp"])
            ):
                conteo[f["pff_positionLinedUp"]] = conteo.get(f["pff_positionLinedUp"], 0) + 1

        assert len(obtenidas) <= 10
        assert len(obtenidas) == min(10, len(conteo))
        conteos = [a["conteo"] for a in obtenidas]
        assert conteos == sorted(conteos, reverse=True)
        pares = [(-a["conteo"], a["posicion"]) for a in obtenidas]
        assert pares == sorted(pares)
        for a in obtenidas:
            assert a["conteo"] == conteo[a["posicion"]]
        # Ninguna combinación omitida supera a la última devuelta.
        if len(conteo) > 10:
            omitidas = set(conteo) - {a["posicion"] for a in obtenidas}
            ultima = (-obtenidas[-1]["conteo"], obtenidas[-1]["posicion"])
            assert all((-conteo[k], k) > ultima for k in omitidas)
            visto["con_diez"] += 1
        if len(set(conteos)) < len(conteos):
            visto["con_empate"] += 1

    repetir(prueba, n=100, semilla=generadores.SEMILLA)
    assert visto["con_empate"] > 0, "el generador nunca produjo empates"


def test_propiedad_19_porcentajes_de_distribucion_son_consistentes(monkeypatch):
    """Feature: failed-plays-coach-app, Property 19

    **Validates: Requirements 8.4**

    Para cualquier lista no vacía de jugadas similares, cada porcentaje es
    `100 * conteo / len(similares)` con 1 decimal, `nMuestra` es `len(similares)`
    y, por atributo, la suma de porcentajes no supera 100.0 más 0.05 por valor.
    """
    visto = {"con_nulos": 0, "varios_valores": 0}
    formaciones = ["SHOTGUN", "EMPTY", "SINGLEBACK", "I_FORM", "PISTOL", "JUMBO"]
    personales = ["1 RB, 1 TE, 3 WR", "2 RB, 1 TE, 2 WR", "1 RB, 2 TE, 2 WR", "0 RB, 1 TE, 4 WR"]
    coberturas = ["Cover-3", "Cover-1", "Quarters", "Cover-2"]

    def prueba(rng):
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, n=0))
        n = rng.randint(1, 40)
        filas = [
            {
                "gameId": 2021090000 + i, "playId": i, "equipo": "XYZ", "rival": "ABC", "yardsToGo": 5,
                "playResult": rng.randint(-5, 30),
                "formacion": rng.choice(formaciones),
                "personal": rng.choice(personales),
                "cobertura": rng.choice(coberturas + [None, None]),
            }
            for i in range(1, n + 1)
        ]
        similares = pd.DataFrame(filas)
        jugada = {
            "gameId": 1, "playId": 1, "equipo": "ABC", "down": 2,
            "yardsToGo": 5, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR",
        }
        grupo = pd.DataFrame(columns=["formacion", "playResult", "efectiva", "yardsToGo"])

        dist = construir_comparacion(jugada, similares, grupo, 2)["distribucion"]

        for campo in ("formacion", "personal", "cobertura"):
            esperado: dict[str, int] = {}
            for f in filas:
                if f[campo] is not None:
                    esperado[f[campo]] = esperado.get(f[campo], 0) + 1
            items = dist[campo]
            assert {i["valor"] for i in items} == set(esperado)
            for i in items:
                assert i["nMuestra"] == n
                assert i["porcentaje"] == round(100 * esperado[i["valor"]] / n, 1)
                assert abs(i["porcentaje"] * 10 - round(i["porcentaje"] * 10)) < 1e-6  # 1 decimal
            assert sum(i["porcentaje"] for i in items) <= 100.0 + 0.05 * len(items) + 1e-9
            if campo == "cobertura" and sum(esperado.values()) < n:
                visto["con_nulos"] += 1
            if len(items) > 1:
                visto["varios_valores"] += 1

    repetir(prueba, n=100, semilla=generadores.SEMILLA)
    assert visto["con_nulos"] > 0, "el generador nunca produjo coberturas nulas"
    assert visto["varios_valores"] > 0


def test_propiedad_20_tasa_de_exito_y_yardas_promedio(monkeypatch):
    """Feature: failed-plays-coach-app, Property 20

    **Validates: Requirements 8.5**

    Para cualquier grupo amplio y tolerancia, por formación `tasaExito` es el
    porcentaje de jugadas efectivas con 1 decimal (entre 0.0 y 100.0),
    `yardasPromedio` es la media de `playResult` con 1 decimal y `nMuestra` es
    el tamaño del grupo de esa formación (yardsToGo dentro de la tolerancia).
    """
    visto = {"formaciones": 0, "mixtas": 0, "fuera_de_tolerancia": 0}
    formaciones = ["SHOTGUN", "EMPTY", "SINGLEBACK", "I_FORM", "PISTOL"]

    def prueba(rng):
        monkeypatch.setattr(datos, "_pff", generar_scouting(rng, n=0))
        tolerancia = rng.randint(0, 4)
        ytg = rng.randint(1, 15)
        n = rng.randint(1, 60)
        filas = [
            {
                "formacion": rng.choice(formaciones),
                "playResult": rng.randint(-8, 40),
                "efectiva": rng.random() < 0.5,
                "yardsToGo": ytg + rng.randint(-tolerancia - 3, tolerancia + 3),
            }
            for _ in range(n)
        ]
        grupo = pd.DataFrame(filas, columns=["formacion", "playResult", "efectiva", "yardsToGo"])
        jugada = {
            "gameId": 1, "playId": 1, "equipo": "ABC", "down": 2,
            "yardsToGo": ytg, "formacion": "SHOTGUN", "personal": "1 RB, 1 TE, 3 WR",
        }
        similares = pd.DataFrame(
            columns=["gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
                     "formacion", "personal", "cobertura"],
        )

        exito = construir_comparacion(jugada, similares, grupo, tolerancia)["exitoPorFormacion"]

        dentro = [f for f in filas if abs(f["yardsToGo"] - ytg) <= tolerancia]
        if len(dentro) < n:
            visto["fuera_de_tolerancia"] += 1
        esperado: dict[str, list[dict]] = {}
        for f in dentro:
            esperado.setdefault(f["formacion"], []).append(f)

        assert {e["formacion"] for e in exito} == set(esperado)
        for e in exito:
            g = esperado[e["formacion"]]
            assert e["nMuestra"] == len(g)
            assert 0.0 <= e["tasaExito"] <= 100.0
            assert e["tasaExito"] == round(100 * sum(1 for f in g if f["efectiva"]) / len(g), 1)
            assert e["yardasPromedio"] == round(sum(f["playResult"] for f in g) / len(g), 1)
            visto["formaciones"] += 1
            if 0.0 < e["tasaExito"] < 100.0:
                visto["mixtas"] += 1

    repetir(prueba, n=100, semilla=generadores.SEMILLA)
    assert visto["formaciones"] > 0
    assert visto["mixtas"] > 0, "el generador nunca produjo tasas intermedias"
    assert visto["fuera_de_tolerancia"] > 0, "el generador nunca produjo jugadas fuera de tolerancia"
