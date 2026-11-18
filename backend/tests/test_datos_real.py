"""Pruebas de ejemplo con los CSV reales de data/ (solo lectura)."""
from __future__ import annotations

import time

import pandas as pd
import pytest

from backend import datos

_ESTADO = ["_plays", "_fallidas", "_efectivas", "_pff", "_equipos_con_fallas"]


@pytest.fixture(scope="module")
def real():
    """Carga data/ una vez, mide el tiempo y restaura el estado del módulo."""
    previo = {n: getattr(datos, n) for n in _ESTADO}
    t0 = time.perf_counter()
    datos.cargar()
    segundos = time.perf_counter() - t0
    try:
        yield segundos
    finally:
        for n, v in previo.items():
            setattr(datos, n, v)


def test_35_filas_down_0_y_ninguna_es_fallida(real):
    plays = datos.todas_las_jugadas()
    down0 = plays[plays["down"] == 0]
    assert len(down0) == 35
    assert down0["razon"].isna().all()
    fallidas = datos.jugadas_fallidas()
    assert not (fallidas["down"] == 0).any()
    assert set(fallidas["down"].unique()) <= {1, 2, 3, 4}


def test_aparecen_las_cinco_razones(real):
    razones = set(datos.jugadas_fallidas()["razon"].unique())
    assert razones == {"intercepcion", "sack", "incompleto", "perdida_de_yardas", "sin_conversion"}


def test_valores_de_pass_result():
    plays = pd.read_csv(datos.DATA_DIR / "plays.csv", usecols=["passResult"])
    valores = set(plays["passResult"].dropna().unique())
    assert valores == {"C", "I", "S", "R", "IN"}


def test_cargar_sin_plays_csv_nombra_plays_csv(tmp_path):
    for nombre in ("games.csv", "players.csv", "pffScoutingData.csv"):
        (tmp_path / nombre).write_text("", encoding="utf-8")
    with pytest.raises(RuntimeError, match=r"plays\.csv"):
        datos.cargar(tmp_path)


def test_carga_inicial_menor_a_30_segundos(real):
    assert real < 30
