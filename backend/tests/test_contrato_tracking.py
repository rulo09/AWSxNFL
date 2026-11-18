"""Prueba de propiedad: ida y vuelta JSON del modelo Tracking."""
from __future__ import annotations
import random
from backend.modelos import Tracking
from backend.tests.generadores import repetir


def _tracking_aleatorio(rng: random.Random) -> dict:
    cuadros = []
    for frame in range(1, rng.randint(1, 8) + 1):
        jugadores = [
            {
                "nflId": rng.randint(1, 99999),
                "equipo": rng.choice(["ofensiva", "defensiva"]),
                "x": round(rng.uniform(0, 120), 2),
                "y": round(rng.uniform(0, 53.3), 2),
            }
            for _ in range(rng.randint(0, 22))
        ]
        balon = None
        if rng.random() < 0.5:
            balon = {"x": round(rng.uniform(0, 120), 2), "y": round(rng.uniform(0, 53.3), 2)}
        cuadros.append({"frame": frame, "jugadores": jugadores, "balon": balon})
    eventos = [
        {"frame": rng.randint(1, 8), "evento": rng.choice(["ball_snap", "pass_forward", "tackle", "línea"])}
        for _ in range(rng.randint(0, 4))
    ]
    return {"eventos": eventos, "cuadros": cuadros}


def test_propiedad_30_ida_y_vuelta_json_tracking():
    # Feature: failed-plays-coach-app, Property 30
    # Validates: Requirements 12.1, 12.6
    vistos_nulo = []

    def prueba(rng: random.Random) -> None:
        original = Tracking.model_validate(_tracking_aleatorio(rng))
        texto = original.model_dump_json()
        vuelta = Tracking.model_validate_json(texto)
        assert vuelta == original
        assert vuelta.model_dump() == original.model_dump()
        vistos_nulo.extend(c.balon is None for c in original.cuadros)

    repetir(prueba)
    assert any(vistos_nulo) and not all(vistos_nulo)
