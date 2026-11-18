"""Pruebas de ejemplo del endpoint de similares con datos sintéticos.

Valida los Requisitos 7.12, 7.13, 8.8 y 9.8.
"""
from __future__ import annotations

import pandas as pd

from backend.tests.generadores import generar_scouting

JUEGO = 2021090001
COLUMNAS = [
    "gameId", "playId", "possessionTeam", "defensiveTeam", "down", "yardsToGo", "playResult",
    "passResult", "offenseFormation", "personnelO", "pff_passCoverage",
]


def _jugada(play_id, equipo, rival, pass_result, resultado):
    return {
        "gameId": JUEGO, "playId": play_id, "possessionTeam": equipo, "defensiveTeam": rival,
        "down": 2, "yardsToGo": 10, "playResult": resultado, "passResult": pass_result,
        "offenseFormation": "SHOTGUN", "personnelO": "1 RB, 1 TE, 3 WR", "pff_passCoverage": "Cover-3",
    }


def _tabla(*filas):
    return pd.DataFrame(list(filas), columns=COLUMNAS)


def test_jugada_desconocida_da_404_en_espanol(cliente, poner_datos):
    poner_datos(_tabla(_jugada(1, "ARI", "BAL", "I", 0)))
    r = cliente.get(f"/api/jugadas/{JUEGO}/999/similares")
    assert r.status_code == 404
    assert r.json() == {"detail": "Jugada no encontrada."}


def test_jugada_sin_candidatas_da_200_con_listas_vacias(cliente, poner_datos):
    # Única jugada efectiva es del mismo equipo, por lo que no hay candidatas.
    poner_datos(_tabla(_jugada(1, "ARI", "BAL", "I", 0), _jugada(2, "ARI", "BAL", "C", 9)))
    r = cliente.get(f"/api/jugadas/{JUEGO}/1/similares")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["similares"] == []
    assert cuerpo["sugerencias"] == []


def test_sin_datos_de_ruta_marca_rutas_no_disponibles_y_conserva_comparacion(cliente, poner_datos, rng):
    jugadas = _tabla(
        _jugada(1, "ARI", "BAL", "I", 0),
        _jugada(2, "BAL", "ARI", "C", 9),
        _jugada(3, "BUF", "ARI", "C", 12),
    )
    # Scouting solo para las similares; la jugada solicitada (playId 1) no tiene filas.
    pff = generar_scouting(rng, claves=[(JUEGO, 2), (JUEGO, 3)], n=30)
    poner_datos(jugadas, pff)

    r = cliente.get(f"/api/jugadas/{JUEGO}/1/similares")
    assert r.status_code == 200
    comp = r.json()["comparacion"]
    assert comp["rutasDisponibles"] is False
    assert comp["alineaciones"] == []
    assert comp["solicitada"]["alineacion"] == []
    # El resto de la comparación se conserva.
    assert len(r.json()["similares"]) == 2
    assert comp["distribucion"]["formacion"][0]["valor"] == "SHOTGUN"
    assert comp["distribucion"]["formacion"][0]["porcentaje"] == 100.0
    assert comp["top3"]["formacion"] == ["SHOTGUN"]
    assert [e["formacion"] for e in comp["exitoPorFormacion"]] == ["SHOTGUN"]
