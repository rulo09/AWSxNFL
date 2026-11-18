"""Pruebas de ejemplo de filtros y jugadas con los CSV reales de data/ (solo lectura).

Valida los Requisitos 3.1, 3.3, 4.4 y 4.8.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend import datos

_ESTADO = ["_plays", "_fallidas", "_efectivas", "_pff", "_equipos_con_fallas"]


@pytest.fixture(scope="module")
def real():
    """Carga data/ una vez y restaura el estado del módulo al terminar."""
    previo = {n: getattr(datos, n) for n in _ESTADO}
    datos.cargar()
    try:
        yield
    finally:
        for n, v in previo.items():
            setattr(datos, n, v)


@pytest.fixture
def api(real):
    from backend.main import app

    return TestClient(app)


def test_filtros_responde_en_menos_de_2s_con_downs_1_a_4(api):
    t0 = time.perf_counter()
    r = api.get("/api/filtros")
    segundos = time.perf_counter() - t0
    assert r.status_code == 200
    assert segundos < 2.0
    cuerpo = r.json()
    assert cuerpo["downs"] == [1, 2, 3, 4]
    assert len(cuerpo["equipos"]) > 0


def test_equipo_ausente_de_EQUIPOS_devuelve_nombre_null_con_datos_reales(api):
    equipos = api.get("/api/filtros").json()["equipos"]
    for e in equipos:
        esperado = datos.EQUIPOS.get(e["abbr"])
        assert e["nombre"] == esperado
    if not any(e["nombre"] is None for e in equipos):
        pytest.skip("Todos los equipos reales están en EQUIPOS; se cubre con el estado parcheado.")


def test_equipo_ausente_de_EQUIPOS_devuelve_nombre_null_con_estado_parcheado(api, monkeypatch):
    fallidas = datos.jugadas_fallidas().copy()
    fallidas.loc[fallidas.index[0], "equipo"] = "ZZZ"
    monkeypatch.setattr(datos, "_fallidas", fallidas)
    equipos = api.get("/api/filtros").json()["equipos"]
    por_abbr = {e["abbr"]: e["nombre"] for e in equipos}
    assert "ZZZ" in por_abbr and por_abbr["ZZZ"] is None
    assert [e["abbr"] for e in equipos] == sorted(por_abbr)
    assert any(n is not None for n in por_abbr.values())


def test_equipo_desconocido_devuelve_lista_vacia_con_200(api):
    r = api.get("/api/jugadas", params={"equipo": "ZZZ"})
    assert r.status_code == 200
    assert r.json() == []


def test_peor_combinacion_de_filtros_responde_en_menos_de_1s(api):
    fallidas = datos.jugadas_fallidas()
    combinaciones = [
        {},
        {"down": 1},
        {"down": 3, "razon": "incompleto"},
    ]
    # Equipo con más jugadas fallidas, combinado con los otros dos filtros.
    top = fallidas["equipo"].value_counts().index[0]
    fila = fallidas[fallidas["equipo"] == top].iloc[0]
    combinaciones.append({"down": int(fila["down"]), "razon": fila["razon"], "equipo": top})
    combinaciones.append({"equipo": top})
    for params in combinaciones:
        t0 = time.perf_counter()
        r = api.get("/api/jugadas", params=params)
        segundos = time.perf_counter() - t0
        assert r.status_code == 200, params
        assert segundos < 1.0, (params, segundos)
    assert len(api.get("/api/jugadas").json()) == len(fallidas)
