"""Pruebas de propiedades del clasificador de fallas (`datos.clasificar_fallas`).

Pytest simple con generadores con semilla (sin hypothesis).
Las propiedades 2, 3 y 4 se agregan en este mismo archivo (tareas 3.3 a 3.5).
"""
from __future__ import annotations

import math
import random

import pandas as pd

from backend import datos
from backend.tests.generadores import (
    PASS_RESULTS,
    generar_jugadas,
    razon_referencia,
    repetir,
)

RAZONES = {"intercepcion", "sack", "incompleto", "perdida_de_yardas", "sin_conversion"}


def _tabla_rangos_diseno(rng: random.Random) -> pd.DataFrame:
    """Tabla con los rangos del diseño: down 0-4, yardsToGo 1-30, playResult -15 a 80."""
    n = rng.randint(0, 60)
    filas = [
        {
            "gameId": 2021090000 + rng.randint(1, 3),
            "playId": i + 1,
            "down": rng.randint(0, 4),
            "yardsToGo": rng.randint(1, 30),
            "playResult": rng.randint(-15, 80),
            "passResult": rng.choice(PASS_RESULTS + [None]),
        }
        for i in range(n)
    ]
    return pd.DataFrame(
        filas, columns=["gameId", "playId", "down", "yardsToGo", "playResult", "passResult"]
    )


def _verificar_contra_referencia(tabla: pd.DataFrame) -> None:
    antes = tabla.copy()
    salida = datos.clasificar_fallas(tabla)
    assert len(salida) == len(tabla)
    assert salida.index.equals(tabla.index)
    for idx, fila in tabla.iterrows():
        esperada = razon_referencia(fila)
        obtenida = salida.at[idx, "razon"]
        if esperada is None:
            assert obtenida is None or pd.isna(obtenida), f"fila {idx}: no debía tener razón, dio {obtenida!r}"
        else:
            assert obtenida == esperada, f"fila {idx}: esperada {esperada!r}, obtenida {obtenida!r}"
        # A lo sumo una razón por jugada, y siempre un código conocido.
        assert isinstance(obtenida, str) or obtenida is None or (
            isinstance(obtenida, float) and math.isnan(obtenida)
        )
        if isinstance(obtenida, str):
            assert obtenida in RAZONES
        # down 0 nunca es falla.
        if fila["down"] == 0:
            assert obtenida is None or pd.isna(obtenida)
    # La entrada no se modifica.
    pd.testing.assert_frame_equal(tabla, antes)


def test_propiedad_1_clasificacion_coincide_con_reglas_de_referencia():
    """Feature: failed-plays-coach-app, Property 1

    Property 1: Failure classification matches the reference rules.
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9**
    """

    def iteracion(rng: random.Random) -> None:
        _verificar_contra_referencia(generar_jugadas(rng))
        _verificar_contra_referencia(_tabla_rangos_diseno(rng))

    repetir(iteracion, n=100)


def _verificar_descripcion(tabla: pd.DataFrame) -> None:
    salida = datos.clasificar_fallas(tabla)
    for idx in salida.index:
        razon = salida.at[idx, "razon"]
        desc = salida.at[idx, "descripcion"]
        if not isinstance(razon, str):
            assert desc is None or pd.isna(desc), f"fila {idx}: sin razón no debe tener descripción"
            continue
        assert isinstance(desc, str)
        assert len(desc) <= 200
        assert str(int(salida.at[idx, "down"])) in desc
        assert str(int(salida.at[idx, "yardsToGo"])) in desc
        assert razon in desc
        # Texto en español.
        assert "yardas por ganar" in desc
        assert "Razón de falla" in desc


def test_propiedad_2_descripcion_de_falla():
    """Feature: failed-plays-coach-app, Property 2

    Property 2: Failure description content.
    **Validates: Requirements 2.8**
    """

    def iteracion(rng: random.Random) -> None:
        _verificar_descripcion(generar_jugadas(rng))
        _verificar_descripcion(_tabla_rangos_diseno(rng))

    repetir(iteracion, n=100)


def _razones_por_clave(salida: pd.DataFrame) -> dict:
    return {
        (int(g), int(p)): (r if isinstance(r, str) else None)
        for g, p, r in zip(salida["gameId"], salida["playId"], salida["razon"])
    }


def _verificar_idempotencia_y_orden(tabla: pd.DataFrame, rng: random.Random) -> None:
    primera = datos.clasificar_fallas(tabla)
    segunda = datos.clasificar_fallas(tabla)
    # Idempotencia (2.10): clasificar dos veces da resultados idénticos.
    pd.testing.assert_frame_equal(primera, segunda)
    # Reclasificar la salida tampoco cambia la razón.
    tercera = datos.clasificar_fallas(primera.drop(columns=["razon", "descripcion"], errors="ignore"))
    pd.testing.assert_frame_equal(primera, tercera)

    # Independencia del orden (2.11): una permutación aleatoria da la misma razón por (gameId, playId).
    orden = list(range(len(tabla)))
    rng.shuffle(orden)
    permutada = tabla.iloc[orden]
    salida_perm = datos.clasificar_fallas(permutada)
    assert _razones_por_clave(salida_perm) == _razones_por_clave(primera)


def test_propiedad_3_clasificacion_idempotente_e_independiente_del_orden():
    """Feature: failed-plays-coach-app, Property 3

    Property 3: Classification is idempotent and independent of row order.
    **Validates: Requirements 2.10, 2.11**
    """

    def iteracion(rng: random.Random) -> None:
        _verificar_idempotencia_y_orden(generar_jugadas(rng), rng)
        _verificar_idempotencia_y_orden(_tabla_rangos_diseno(rng), rng)

    repetir(iteracion, n=100)


CAMPOS_NUMERICOS = ["gameId", "playId", "down", "yardsToGo", "playResult"]


def _corromper(tabla: pd.DataFrame, rng: random.Random) -> tuple[pd.DataFrame, list]:
    """Vuelve inválidas (NaN, None o texto no numérico) algunas filas; devuelve la tabla y sus índices."""
    sucia = tabla.copy().astype({c: object for c in CAMPOS_NUMERICOS})
    invalidas = []
    for idx in sucia.index:
        if rng.random() < 0.3:
            campo = rng.choice(CAMPOS_NUMERICOS)
            sucia.at[idx, campo] = rng.choice([math.nan, None, "abc", "", "N/A"])
            invalidas.append(idx)
    return sucia, invalidas


def _nulo(valor) -> bool:
    return valor is None or (not isinstance(valor, str) and pd.isna(valor))


def test_propiedad_4_filas_invalidas_se_omiten_sin_afectar_a_las_demas():
    """Feature: failed-plays-coach-app, Property 4

    Property 4: Invalid rows are skipped without affecting others.
    **Validates: Requirements 2.12**
    """

    def iteracion(rng: random.Random) -> None:
        base = generar_jugadas(rng, n=rng.randint(0, 40), con_invalidas=False)
        sucia, invalidas = _corromper(base, rng)
        salida = datos.clasificar_fallas(sucia)
        assert len(salida) == len(sucia)

        # Las filas inválidas no tienen razón.
        for idx in invalidas:
            assert _nulo(salida.at[idx, "razon"]), f"fila inválida {idx} tiene razón {salida.at[idx, 'razon']!r}"

        # Las demás filas dan lo mismo que si se quitan las inválidas.
        validas = sucia.drop(index=invalidas)
        salida_validas = datos.clasificar_fallas(validas)
        assert len(salida_validas) == len(validas)
        for idx in validas.index:
            for col in ("razon", "descripcion"):
                a, b = salida.at[idx, col], salida_validas.at[idx, col]
                assert (_nulo(a) and _nulo(b)) or a == b, f"fila {idx} columna {col}: {a!r} != {b!r}"

    repetir(iteracion, n=100)
