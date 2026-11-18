"""Pruebas de integración del backend con los CSV reales de data/ (solo lectura).

Requisitos: 1.9, 1.10 (data/ no cambia), 1.13 (flujo completo), 11.6 (error genérico en español).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import datos, tracking
from backend.main import app

DATA = Path(__file__).resolve().parent.parent.parent / "data"
_ESTADO = ["_plays", "_fallidas", "_efectivas", "_pff", "_equipos_con_fallas"]
MSG_500 = "Ocurrió un error interno. Intenta de nuevo."


def _hashes() -> dict[str, str]:
    resultado = {}
    for p in sorted(DATA.rglob("*")):
        if p.is_file():
            h = hashlib.sha256()
            with p.open("rb") as f:
                for bloque in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloque)
            resultado[str(p.relative_to(DATA))] = h.hexdigest()
    return resultado


@pytest.fixture(scope="module")
def real():
    """Carga data/ una vez, comprueba los hashes de data/ al terminar y restaura el estado."""
    antes = _hashes()
    previo = {n: getattr(datos, n) for n in _ESTADO}
    datos.cargar()
    try:
        yield antes
    finally:
        for n, v in previo.items():
            setattr(datos, n, v)
        tracking._leer_cacheado.cache_clear()
    assert _hashes() == antes, "data/ cambió durante las pruebas"


@pytest.fixture()
def api(real):
    tracking._leer_cacheado.cache_clear()
    return TestClient(app, raise_server_exceptions=False)  # sin lifespan: datos ya cargados


def test_ruta_que_falla_da_json_en_espanol_y_la_siguiente_funciona(api, monkeypatch):
    def explota():
        raise ValueError("secreto /ruta/interna.py")

    monkeypatch.setattr(datos, "jugadas_fallidas", explota)
    r = api.get("/api/filtros")
    assert r.status_code == 500
    assert r.json() == {"detail": MSG_500}
    assert "Traceback" not in r.text and "secreto" not in r.text and ".py" not in r.text

    monkeypatch.undo()
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/api/filtros").status_code == 200


def test_flujo_completo_con_datos_reales(api, ia_stub):
    ia_stub.configurar(texto="Recomendación simulada.")

    r = api.get("/api/filtros")
    assert r.status_code == 200
    filtros = r.json()
    assert filtros["downs"] == [1, 2, 3, 4] and filtros["equipos"]

    r = api.get("/api/jugadas", params={"down": 3, "razon": "incompleto"})
    assert r.status_code == 200
    lista = r.json()
    assert lista and all(j["down"] == 3 and j["razon"] == "incompleto" for j in lista)

    # Primera jugada de la lista con archivo de tracking disponible.
    elegida = next(j for j in lista if (DATA / "tracking" / f"tracking_{j['gameId']}.csv").is_file())
    g, p = elegida["gameId"], elegida["playId"]

    r = api.get(f"/api/jugadas/{g}/{p}/tracking")
    assert r.status_code == 200
    assert r.json()

    r = api.get(f"/api/jugadas/{g}/{p}/similares")
    assert r.status_code == 200
    cuerpo = r.json()
    assert {"similares", "sugerencias", "criteriosRelajados", "comparacion"} <= set(cuerpo)
    assert all(s["equipo"] != elegida["equipo"] for s in cuerpo["similares"])

    r = api.post("/api/recomendacion", json={"jugada": elegida, "sugerencias": cuerpo["sugerencias"]})
    assert r.status_code == 200
    assert r.json() == {"recomendacion": "Recomendación simulada.", "generado_por_ia": True}


def test_data_solo_lectura_tras_usar_la_api(api, real):
    api.get("/api/filtros")
    api.get("/api/jugadas")
    assert _hashes() == real
