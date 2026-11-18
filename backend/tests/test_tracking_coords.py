"""Pruebas de propiedades de coordenadas de tracking (Persona B)."""
from __future__ import annotations

import random

import pytest

from backend import tracking
from backend.tests.generadores import generar_tracking, repetir


def _limitar(v: float, maximo: float) -> float:
    return min(max(v, 0.0), maximo)


# Feature: failed-plays-coach-app, Property 8
# **Validates: Requirements 5.4, 5.5, 5.10**
def test_propiedad_8_coordenadas_normalizadas_dentro_del_campo():
    """Property 8: Normalized player coordinates stay on the field and follow the direction rule."""

    def prueba(rng: random.Random) -> None:
        # Regla de dirección sobre posiciones arbitrarias (incluso fuera del campo).
        x, y = rng.uniform(-50, 170), rng.uniform(-30, 90)
        nx, ny = tracking.normalizar(x, y, "left")
        assert nx == pytest.approx(120 - x) and ny == pytest.approx(53.3 - y)
        assert tracking.normalizar(x, y, "right") == (x, y)

        # Modelo completo: jugadores recortados al campo y consistentes con la regla.
        direccion = rng.choice(["left", "right"])
        df = generar_tracking(rng, equipo_ofensivo="TB", direccion=direccion)
        modelo = tracking.a_modelo(df, "TB")

        esperado = {}
        for fila in df[df["team"] != "football"].itertuples(index=False):
            px, py = tracking.normalizar(float(fila.x), float(fila.y), direccion)
            esperado[(int(fila.frameId), int(fila.nflId))] = (
                round(_limitar(px, 120.0), 2),
                round(_limitar(py, 53.3), 2),
            )

        for cuadro in modelo["cuadros"]:
            for j in cuadro["jugadores"]:
                assert 0 <= j["x"] <= 120, j
                assert 0 <= j["y"] <= 53.3, j
                assert (j["x"], j["y"]) == esperado[(cuadro["frame"], j["nflId"])]

    repetir(prueba, n=100)


# Feature: failed-plays-coach-app, Property 9
# **Validates: Requirements 5.11**
def test_propiedad_9_normalizacion_es_su_propia_inversa():
    """Property 9: Normalization is its own inverse."""

    def prueba(rng: random.Random) -> None:
        x, y = rng.uniform(0, 120), rng.uniform(0, 53.3)
        direccion = rng.choice(["left", "right"])
        nx, ny = tracking.normalizar(x, y, direccion)
        rx, ry = tracking.normalizar(nx, ny, direccion)
        assert abs(rx - x) <= 0.01 and abs(ry - y) <= 0.01

    repetir(prueba, n=100)
