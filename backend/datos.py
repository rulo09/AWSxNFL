"""Data_Loader y Failure_Classifier (Persona A implementa los cuerpos).

Las firmas públicas están congeladas. El estado privado (`_plays`, `_fallidas`,
`_efectivas`, `_pff`, `_equipos_con_fallas`) lo llenan `cargar()` y las
fixtures de `backend/tests/conftest.py`.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Abreviatura -> nombre completo (32 equipos, con las abreviaturas de games.csv).
EQUIPOS: dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Football Team",
}

_plays: pd.DataFrame = pd.DataFrame()
_fallidas: pd.DataFrame = pd.DataFrame()
_efectivas: pd.DataFrame = pd.DataFrame()
_pff: pd.DataFrame = pd.DataFrame()
_equipos_con_fallas: list[str] = []

_COLS_NUM = ["gameId", "playId", "down", "yardsToGo", "playResult"]
_ENTEROS = set(_COLS_NUM) | {"nflId"}
_RENOMBRES = {
    "possessionTeam": "equipo",
    "defensiveTeam": "rival",
    "offenseFormation": "formacion",
    "personnelO": "personal",
    "pff_passCoverage": "cobertura",
}
_UMBRALES = {1: 0.4, 2: 0.6, 3: 1.0, 4: 1.0}
_ETIQUETAS = {
    "intercepcion": "pase interceptado",
    "sack": "capturado (sack)",
    "incompleto": "pase incompleto",
    "perdida_de_yardas": "pérdida de yardas",
    "sin_conversion": "sin conversión de down",
}
_ARCHIVOS = ["games.csv", "plays.csv", "players.csv", "pffScoutingData.csv"]
_PERSONAL_RE = re.compile(r"^\s*(\d+)\s+([A-Z]+)\s*$")


def cargar(data_dir: Path = DATA_DIR) -> None:
    """Carga los CSV una sola vez y construye las tablas en memoria.

    Lanza `RuntimeError("No se encontró el archivo <nombre>")` si falta un CSV.
    """
    global _plays, _fallidas, _efectivas, _pff, _equipos_con_fallas
    data_dir = Path(data_dir)
    for nombre in _ARCHIVOS:
        if not (data_dir / nombre).is_file():
            raise RuntimeError(f"No se encontró el archivo {nombre}")
    games = pd.read_csv(data_dir / "games.csv")
    plays = pd.read_csv(data_dir / "plays.csv")
    players = pd.read_csv(data_dir / "players.csv", usecols=["nflId", "officialPosition"])
    pff = pd.read_csv(data_dir / "pffScoutingData.csv")

    faltantes = set(plays["gameId"].dropna()) - set(games["gameId"])
    if faltantes:
        raise RuntimeError("plays.csv contiene gameId que no existen en games.csv")

    plays = clasificar_fallas(plays)
    plays["personal_conteos"] = [parsear_personal(t) for t in plays["personnelO"]]
    plays = plays.reset_index(drop=True)

    fallidas = plays[plays["razon"].notna()].copy()
    fallidas[_COLS_NUM] = fallidas[_COLS_NUM].astype("int64")
    fallidas = fallidas.sort_values(["gameId", "playId"]).rename(columns=_RENOMBRES).reset_index(drop=True)

    umbral = plays["down"].map(_UMBRALES)
    mascara = (
        plays["razon"].isna()
        & plays["down"].isin(list(_UMBRALES))
        & (plays["passResult"] == "C")
        & (plays["playResult"] >= umbral * plays["yardsToGo"])
    )
    efectivas = plays[mascara].copy()
    efectivas[_COLS_NUM] = efectivas[_COLS_NUM].astype("int64")
    efectivas = efectivas.rename(columns=_RENOMBRES).reset_index(drop=True)

    pff = pff.merge(players.drop_duplicates("nflId"), on="nflId", how="left")

    _plays = plays
    _fallidas = fallidas
    _efectivas = efectivas
    _pff = pff
    _equipos_con_fallas = sorted(fallidas["equipo"].dropna().unique().tolist())


def clasificar_fallas(plays: pd.DataFrame) -> pd.DataFrame:
    """Devuelve `plays` con las columnas `razon` (str o None) y `descripcion`.

    Función pura, determinista e idempotente. Precedencia: intercepcion, sack,
    incompleto, perdida_de_yardas, sin_conversion.
    """
    df = plays.copy()
    for col in _COLS_NUM:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    valido = df[_COLS_NUM].notna().all(axis=1) & df["down"].isin([1, 2, 3, 4])
    pr = df["passResult"]
    down, ytg, res = df["down"], df["yardsToGo"], df["playResult"]
    condiciones = [
        (pr == "IN").to_numpy(),
        (pr == "S").to_numpy(),
        (pr == "I").to_numpy(),
        (res < 0).to_numpy(),
        (down.isin([3, 4]) & (res < ytg)).to_numpy(),
    ]
    codigos = list(_ETIQUETAS)
    razon = np.select(condiciones, codigos, default="")
    razon = np.where(valido.to_numpy(), razon, "")
    df["razon"] = pd.Series([str(r) if r else None for r in razon], index=df.index, dtype=object)
    desc = []
    for r, d, y in zip(df["razon"], down, ytg):
        if r is None:
            desc.append(None)
        else:
            t = f"Down {int(d)} y {int(y)} yardas por ganar. Razón de falla: {r} ({_ETIQUETAS[r]})."
            desc.append(t[:200])
    df["descripcion"] = pd.Series(desc, index=df.index, dtype=object)
    return df


def parsear_personal(texto: str | None) -> dict[str, int] | None:
    """Convierte '1 RB, 1 TE, 3 WR' en {'RB': 1, 'TE': 1, 'WR': 3}.

    Devuelve None si el texto es nulo o algún token no es válido.
    """
    if not isinstance(texto, str):
        return None
    conteos: dict[str, int] = {}
    for token in texto.split(","):
        m = _PERSONAL_RE.match(token)
        if not m:
            return None
        pos = m.group(2)
        if pos in conteos:
            return None
        conteos[pos] = int(m.group(1))
    return conteos or None


def formatear_personal(conteos: dict[str, int]) -> str:
    """Convierte conteos en '<n> <POS>' separados por ', ' en orden de inserción."""
    return ", ".join(f"{n} {pos}" for pos, n in conteos.items())


def _limpio(v):
    if v is None or v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if math.isnan(v) else float(v)
    if isinstance(v, np.str_):
        return str(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def a_jugada(row) -> dict:
    """Convierte una fila en dict: NaN/pd.NA/None -> None y enteros numpy -> int."""
    items = row.items() if hasattr(row, "items") else dict(row).items()
    salida = {}
    for k, v in items:
        v = _limpio(v)
        if k in _ENTEROS and isinstance(v, float) and v.is_integer():
            v = int(v)
        salida[k] = v
    return salida


_CAMPOS_JUGADA = [
    "gameId", "playId", "equipo", "rival", "down", "yardsToGo", "razon", "descripcion",
    "formacion", "personal", "cobertura",
]


def obtener_jugada(game_id: int, play_id: int) -> dict | None:
    """Devuelve la jugada como dict (al menos `equipo`) o None si no existe."""
    plays = _plays
    if plays is None or plays.empty:
        return None
    sel = plays[(plays["gameId"] == game_id) & (plays["playId"] == play_id)]
    if sel.empty:
        return None
    fila = sel.iloc[0].rename(_RENOMBRES)
    d = a_jugada(fila)
    return {c: d.get(c) for c in _CAMPOS_JUGADA} | {"playResult": d.get("playResult")}


def jugadas_fallidas() -> pd.DataFrame:
    """Tabla de jugadas fallidas ordenada por gameId, playId."""
    return _fallidas


def jugadas_efectivas() -> pd.DataFrame:
    """Tabla de jugadas efectivas (regla de efectividad del Requisito 7.1)."""
    return _efectivas


def todas_las_jugadas() -> pd.DataFrame:
    """Todas las jugadas con `razon` y `descripcion`."""
    return _plays


def alineaciones(game_id: int, play_id: int) -> pd.DataFrame:
    """Filas de pffScoutingData (con officialPosition) de una jugada."""
    pff = _pff
    if pff is None or pff.empty:
        return pff
    return pff[(pff["gameId"] == game_id) & (pff["playId"] == play_id)]
