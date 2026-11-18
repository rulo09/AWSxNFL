"""Tracking_Reader: lee un archivo de tracking por solicitud y arma el modelo Tracking."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLUMNAS = ["playId", "frameId", "nflId", "team", "x", "y", "event", "playDirection"]

LARGO_CAMPO = 120.0
ANCHO_CAMPO = 53.3
MAX_JUGADORES = 22


def leer_tracking(game_id: int, play_id: int, equipo_ofensivo: str, data_dir: Path = DATA_DIR) -> dict | None:
    """Lee `tracking_<gameId>.csv` y devuelve el modelo Tracking como dict.

    Devuelve None si falta el archivo o la jugada.
    """
    return _leer_cacheado(int(game_id), int(play_id), equipo_ofensivo, str(data_dir))


@lru_cache(maxsize=16)
def _leer_cacheado(game_id: int, play_id: int, equipo_ofensivo: str, data_dir: str) -> dict | None:
    ruta = Path(data_dir) / "tracking" / f"tracking_{game_id}.csv"
    if not ruta.is_file():
        return None
    df = pd.read_csv(
        ruta,
        usecols=COLUMNAS,
        dtype={"team": "string", "event": "string", "playDirection": "string"},
        keep_default_na=False,
        na_values=[""],
    )
    df["playId"] = pd.to_numeric(df["playId"], errors="coerce")
    df = df[df["playId"] == play_id]
    if df.empty:
        return None
    df = df.copy()
    for col in ("frameId", "nflId", "x", "y"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["frameId"])
    if df.empty:
        return None
    return a_modelo(df, equipo_ofensivo)


def normalizar(x, y, direccion: str) -> tuple:
    """Normaliza coordenadas: 'left' -> (120 - x, 53.3 - y); otro valor queda igual."""
    if direccion == "left":
        return LARGO_CAMPO - x, ANCHO_CAMPO - y
    return x, y


def _limitar(valor: float, maximo: float) -> float:
    return min(max(valor, 0.0), maximo)


def a_modelo(df: pd.DataFrame, equipo_ofensivo: str) -> dict:
    """Convierte las filas de una jugada en {'eventos': [...], 'cuadros': [...]}."""
    direccion = "right"
    if "playDirection" in df.columns:
        validas = df["playDirection"].dropna()
        if len(validas):
            direccion = str(validas.iloc[0]).strip()

    df = df.dropna(subset=["frameId"]).sort_values("frameId", kind="stable")

    cuadros = []
    eventos = set()
    for frame_id, grupo in df.groupby("frameId", sort=True):
        frame = int(frame_id)
        jugadores = []
        vistos = set()
        balon = None
        for fila in grupo.itertuples(index=False):
            equipo = fila.team
            x, y = fila.x, fila.y
            if pd.notna(equipo) and equipo == "football":
                if balon is None and pd.notna(x) and pd.notna(y):
                    bx, by = normalizar(float(x), float(y), direccion)
                    balon = {"x": round(bx, 2), "y": round(by, 2)}
            elif (
                pd.notna(fila.nflId)
                and pd.notna(x)
                and pd.notna(y)
                and int(fila.nflId) not in vistos
                and len(jugadores) < MAX_JUGADORES
            ):
                nfl_id = int(fila.nflId)
                vistos.add(nfl_id)
                px, py = normalizar(float(x), float(y), direccion)
                jugadores.append(
                    {
                        "nflId": nfl_id,
                        "equipo": "ofensiva" if equipo == equipo_ofensivo else "defensiva",
                        "x": round(_limitar(px, LARGO_CAMPO), 2),
                        "y": round(_limitar(py, ANCHO_CAMPO), 2),
                    }
                )
            ev = fila.event
            if pd.notna(ev):
                ev = str(ev).strip()
                if ev and ev != "None":
                    eventos.add((frame, ev))
        cuadros.append({"frame": frame, "jugadores": jugadores, "balon": balon})

    return {
        "eventos": [{"frame": f, "evento": e} for f, e in sorted(eventos)],
        "cuadros": cuadros,
    }
