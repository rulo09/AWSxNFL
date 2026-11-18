"""Pruebas de ejemplo con archivos de tracking reales (data/ es solo lectura)."""
from __future__ import annotations

import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import datos, tracking
from backend.main import app

GAME_ID = 2021090900
_ESTADO = ["_plays", "_fallidas", "_efectivas", "_pff", "_equipos_con_fallas"]


@pytest.fixture(scope="module")
def real():
    """Carga data/ una vez (el endpoint necesita `datos`) y restaura el estado."""
    previo = {n: getattr(datos, n) for n in _ESTADO}
    datos.cargar()
    try:
        yield
    finally:
        for n, v in previo.items():
            setattr(datos, n, v)
        tracking._leer_cacheado.cache_clear()


@pytest.fixture()
def cliente(real):
    tracking._leer_cacheado.cache_clear()
    yield TestClient(app)  # sin lifespan: los datos ya están cargados
    tracking._leer_cacheado.cache_clear()


def _play_ids_con_datos() -> list[int]:
    plays = datos.todas_las_jugadas()
    ids = plays.loc[plays["gameId"] == GAME_ID, "playId"].astype(int).tolist()
    assert ids, "no hay jugadas del juego de prueba en plays.csv"
    return ids


def test_jugada_real_200_rapida_con_usecols_y_balon(cliente, monkeypatch):
    play_id = _play_ids_con_datos()[0]
    llamadas = []
    original = pd.read_csv

    def espia(*args, **kwargs):
        llamadas.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(tracking.pd, "read_csv", espia)
    t0 = time.perf_counter()
    r = cliente.get(f"/api/jugadas/{GAME_ID}/{play_id}/tracking")
    segundos = time.perf_counter() - t0
    assert r.status_code == 200
    assert segundos < 2
    assert len(llamadas) == 1
    assert set(llamadas[0][1]["usecols"]) <= set(tracking.COLUMNAS)
    cuerpo = r.json()
    assert cuerpo["cuadros"]
    assert any(c["balon"] is not None for c in cuerpo["cuadros"])
    for c in cuerpo["cuadros"]:
        assert len(c["jugadores"]) <= 22


def test_archivo_de_juego_inexistente_da_404(cliente, tmp_path):
    # Sin archivo de tracking, la lectura devuelve None (data_dir vacío)...
    assert tracking.leer_tracking(GAME_ID, _play_ids_con_datos()[0], "TB", data_dir=tmp_path) is None
    # ...y el endpoint responde 404 con el mensaje en español para un juego sin archivo.
    r = cliente.get("/api/jugadas/1999010100/1/tracking")
    assert r.status_code == 404
    assert r.json()["detail"] == "No se encontraron datos de tracking para esta jugada."


def test_playid_ausente_en_archivo_da_404(cliente):
    # El archivo existe pero la jugada no está en él.
    assert tracking.leer_tracking(GAME_ID, 999999, "TB") is None
    r = cliente.get(f"/api/jugadas/{GAME_ID}/999999/tracking")
    assert r.status_code == 404
    assert r.json()["detail"] == "No se encontraron datos de tracking para esta jugada."


def test_ofensiva_avanza_en_x_entre_snap_y_pase():
    tracking._leer_cacheado.cache_clear()
    ruta = datos.DATA_DIR / "tracking" / f"tracking_{GAME_ID}.csv"
    crudo = pd.read_csv(ruta, usecols=["playId"])
    ids = sorted(crudo["playId"].unique().tolist())
    plays = pd.read_csv(datos.DATA_DIR / "plays.csv", usecols=["gameId", "playId", "possessionTeam"])
    plays = plays[plays["gameId"] == GAME_ID].set_index("playId")["possessionTeam"]
    diffs = []
    for pid in ids:
        if pid not in plays.index:
            continue
        m = tracking.leer_tracking(GAME_ID, int(pid), plays[pid])
        if m is None:
            continue
        frames = {}
        for e in m["eventos"]:
            frames.setdefault(e["evento"], e["frame"])
        if "ball_snap" not in frames:
            continue
        fin = frames.get("pass_forward", m["cuadros"][-1]["frame"])
        por_frame = {c["frame"]: c for c in m["cuadros"]}

        def media(frame):
            xs = [j["x"] for j in por_frame[frame]["jugadores"] if j["equipo"] == "ofensiva"]
            return sum(xs) / len(xs) if xs else None

        a, b = media(frames["ball_snap"]), media(fin)
        if a is not None and b is not None:
            diffs.append(b - a)
    assert len(diffs) >= 30
    assert sum(diffs) / len(diffs) > 0
    tracking._leer_cacheado.cache_clear()
