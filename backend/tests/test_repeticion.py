"""Pruebas de ejemplo del endpoint de tracking (repetición animada).

Requisitos: 5.9 (404 sin jugada o sin archivo), 1.9 (422 en español, data/ solo lectura).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend import tracking

DATA = Path(__file__).resolve().parent.parent.parent / "data"
MSG_404 = "No se encontraron datos de tracking para esta jugada."


def _instantanea(raiz: Path) -> dict[str, tuple[int, int]]:
    return {str(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(raiz.rglob("*")) if p.is_file()}


@pytest.fixture
def jugada_generada(datos_generados):
    plays = datos_generados["_plays"]
    fila = plays.iloc[0]
    return int(fila["gameId"]), int(fila["playId"])


@pytest.fixture
def tracking_en_directorio_vacio(monkeypatch, tmp_path):
    """Hace que la lectura real busque en un directorio sin archivos de tracking."""
    original = tracking.leer_tracking
    monkeypatch.setattr(
        tracking, "leer_tracking",
        lambda g, p, e, data_dir=tmp_path: original(g, p, e, data_dir=data_dir),
    )
    return tmp_path


def test_jugada_desconocida_da_404(cliente, jugada_generada):
    game_id, play_id = jugada_generada
    r = cliente.get(f"/api/jugadas/{game_id}/{play_id + 987654}/tracking")
    assert r.status_code == 404
    assert r.json() == {"detail": MSG_404}


def test_archivo_faltante_da_404_en_espanol(cliente, jugada_generada, tracking_en_directorio_vacio):
    game_id, play_id = jugada_generada
    r = cliente.get(f"/api/jugadas/{game_id}/{play_id}/tracking")
    assert r.status_code == 404
    assert r.json() == {"detail": MSG_404}


def test_game_id_no_entero_da_422_en_espanol(cliente):
    r = cliente.get("/api/jugadas/abc/1/tracking")
    assert r.status_code == 422
    assert r.json() == {"detail": "El valor del campo 'gameId' no es válido."}


def test_data_no_se_modifica(cliente, jugada_generada, tracking_en_directorio_vacio):
    if not DATA.is_dir():
        pytest.skip("No existe data/")
    antes = _instantanea(DATA)
    game_id, play_id = jugada_generada
    cliente.get(f"/api/jugadas/{game_id}/{play_id}/tracking")
    cliente.get(f"/api/jugadas/{game_id}/{play_id + 987654}/tracking")
    cliente.get("/api/jugadas/abc/1/tracking")
    assert _instantanea(DATA) == antes
