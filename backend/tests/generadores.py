"""Ayudas compartidas de prueba: bucle `repetir` y generadores con semilla.

Solo pytest y numpy/pandas (sin hypothesis). Cada generador recibe un
`random.Random` para que cada iteración sea reproducible.
"""
from __future__ import annotations

import math
import random
from typing import Callable

import pandas as pd

SEMILLA = 2023
PASS_RESULTS = ["C", "I", "S", "R", "IN"]
EQUIPOS_PRUEBA = ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "DAL", "LA", "LAC", "LV", "TB", "WAS", "XYZ"]
FORMACIONES = ["SHOTGUN", "SINGLEBACK", "EMPTY", "I_FORM", "PISTOL", "JUMBO"]
PERSONALES = ["1 RB, 1 TE, 3 WR", "1 RB, 2 TE, 2 WR", "2 RB, 1 TE, 2 WR", "0 RB, 1 TE, 4 WR"]
COBERTURAS = ["Cover-1", "Cover-2", "Cover-3", "Quarters", "Man"]
POSICIONES_RUTA = ["WR", "TE", "RB", "FB"]
POSICIONES_OTRAS = ["QB", "T", "G", "C", "CB", "LB", "DE", "DT", "FS", "SS"]
ROLES = ["Pass", "Pass Block", "Pass Route", "Pass Rush", "Coverage"]
ALINEACIONES = ["SLWR", "SRWR", "WR", "SLiWR", "TE-L", "TE-R", "HB", "FB", "RWR", "LWR", "SRiWR"]
EVENTOS = ["ball_snap", "pass_forward", "pass_arrived", "tackle", "qb_sack", "touchdown", "out_of_bounds"]


def repetir(prueba: Callable[[random.Random], None], n: int = 100, semilla: int = SEMILLA) -> None:
    """Ejecuta `prueba(rng)` n veces con un generador distinto y reproducible.

    Si una iteración falla, el error indica el número de iteración y la semilla.
    """
    for i in range(n):
        rng = random.Random(f"{semilla}-{i}")
        try:
            prueba(rng)
        except AssertionError as e:
            raise AssertionError(f"Falló la iteración {i} (semilla {semilla}): {e}") from e


# --------------------------------------------------------------------------
# Tabla de jugadas
# --------------------------------------------------------------------------
def generar_jugadas(rng: random.Random, n: int | None = None, con_invalidas: bool = True) -> pd.DataFrame:
    """Tabla tipo plays.csv.

    Incluye down 0, NaN en campos numéricos, passResult 'R' y ausente,
    formacion/personal/cobertura nulos y playResult repetidos (empates).
    """
    n = rng.randint(0, 40) if n is None else n
    equipos = rng.sample(EQUIPOS_PRUEBA, k=rng.randint(2, 6))
    # Pocos valores de playResult para forzar empates.
    resultados = [rng.randint(-8, 40) for _ in range(rng.randint(2, 6))]
    filas = []
    for i in range(n):
        ofensivo = rng.choice(equipos)
        rival = rng.choice([e for e in equipos if e != ofensivo] or ["OPP"])
        fila = {
            "gameId": rng.randint(1, 4) * 1000 + 2021090000,
            "playId": i + 1,
            "possessionTeam": ofensivo,
            "defensiveTeam": rival,
            "down": rng.choice([0, 1, 2, 3, 4, 1, 2, 3, 3, 4]),
            "yardsToGo": rng.randint(1, 30),
            "playResult": rng.choice(resultados),
            "passResult": rng.choice(PASS_RESULTS + [None]),
            "offenseFormation": rng.choice(FORMACIONES + [None]),
            "personnelO": rng.choice(PERSONALES + [None]),
            "pff_passCoverage": rng.choice(COBERTURAS + [None]),
        }
        if con_invalidas:
            for campo in ("down", "yardsToGo", "playResult"):
                if rng.random() < 0.05:
                    fila[campo] = math.nan
        filas.append(fila)
    columnas = [
        "gameId", "playId", "possessionTeam", "defensiveTeam", "down", "yardsToGo",
        "playResult", "passResult", "offenseFormation", "personnelO", "pff_passCoverage",
    ]
    return pd.DataFrame(filas, columns=columnas)


def razon_referencia(fila) -> str | None:
    """Referencia independiente de la clasificación de fallas (precedencia de 2.7)."""
    try:
        down, ytg, res = float(fila["down"]), float(fila["yardsToGo"]), float(fila["playResult"])
    except (TypeError, ValueError):
        return None
    if any(math.isnan(v) for v in (down, ytg, res)) or down not in (1, 2, 3, 4):
        return None
    pr = fila["passResult"]
    if pr == "IN":
        return "intercepcion"
    if pr == "S":
        return "sack"
    if pr == "I":
        return "incompleto"
    if res < 0:
        return "perdida_de_yardas"
    if down in (3, 4) and res < ytg:
        return "sin_conversion"
    return None


def es_efectiva_referencia(fila) -> bool:
    """Referencia independiente de la regla de jugada efectiva (7.1)."""
    if razon_referencia(fila) is not None or fila["passResult"] != "C":
        return False
    down, ytg, res = fila["down"], fila["yardsToGo"], fila["playResult"]
    if any(pd.isna(v) for v in (down, ytg, res)) or int(down) not in (1, 2, 3, 4):
        return False
    umbral = {1: 0.4, 2: 0.6, 3: 1.0, 4: 1.0}[int(fila["down"])]
    return float(fila["playResult"]) >= umbral * float(fila["yardsToGo"])


def estado_datos(jugadas: pd.DataFrame, pff: pd.DataFrame | None = None) -> dict:
    """Construye el estado interno de `datos` desde una tabla, con la referencia.

    Claves: `_plays`, `_fallidas`, `_efectivas`, `_pff`, `_equipos_con_fallas`.
    """
    plays = jugadas.copy()
    plays["razon"] = [razon_referencia(f) for _, f in plays.iterrows()]
    plays["descripcion"] = [
        None if r is None else f"Down {int(f['down'])} y {int(f['yardsToGo'])} yardas por ganar. Razón de falla: {r}."
        for (_, f), r in zip(plays.iterrows(), plays["razon"])
    ]
    renombres = {
        "possessionTeam": "equipo", "defensiveTeam": "rival", "offenseFormation": "formacion",
        "personnelO": "personal", "pff_passCoverage": "cobertura",
    }
    fallidas = plays[plays["razon"].notna()].sort_values(["gameId", "playId"]).rename(columns=renombres)
    mascara = [es_efectiva_referencia(f) for _, f in plays.iterrows()]
    efectivas = plays[pd.Series(mascara, index=plays.index, dtype=bool)].rename(columns=renombres)
    if pff is None:
        pff = pd.DataFrame(columns=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp", "officialPosition"])
    return {
        "_plays": plays.reset_index(drop=True),
        "_fallidas": fallidas.reset_index(drop=True),
        "_efectivas": efectivas.reset_index(drop=True),
        "_pff": pff.reset_index(drop=True),
        "_equipos_con_fallas": sorted(fallidas["equipo"].unique().tolist()),
    }


# --------------------------------------------------------------------------
# Datos de scouting (pffScoutingData unido con players.officialPosition)
# --------------------------------------------------------------------------
def generar_scouting(rng: random.Random, claves: list[tuple[int, int]] | None = None, n: int | None = None) -> pd.DataFrame:
    """Filas de scouting con todos los roles y posiciones, algunas con valores nulos."""
    claves = claves or [(2021090001, rng.randint(1, 50))]
    n = rng.randint(0, 60) if n is None else n
    filas = []
    for i in range(n):
        g, p = rng.choice(claves)
        ruta = rng.random() < 0.5
        filas.append({
            "gameId": g,
            "playId": p,
            "nflId": 1000 + i,
            "pff_role": "Pass Route" if ruta else rng.choice(ROLES),
            "pff_positionLinedUp": rng.choice(ALINEACIONES + [None]),
            "officialPosition": rng.choice(POSICIONES_RUTA if ruta else POSICIONES_RUTA + POSICIONES_OTRAS),
        })
    return pd.DataFrame(
        filas, columns=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp", "officialPosition"]
    )


# --------------------------------------------------------------------------
# Tracking
# --------------------------------------------------------------------------
COLUMNAS_TRACKING = ["playId", "frameId", "nflId", "team", "x", "y", "event", "playDirection"]


def generar_tracking(
    rng: random.Random,
    play_id: int = 1,
    equipo_ofensivo: str = "TB",
    direccion: str | None = None,
    con_celdas_malas: bool = False,
) -> pd.DataFrame:
    """Cuadros de una jugada: hasta 22 jugadores y un balón opcional por cuadro.

    Las coordenadas pueden salir del campo. Los eventos son cadenas vacías,
    la cadena 'None' o nombres de evento (a veces repetidos en un cuadro).
    """
    direccion = direccion or rng.choice(["left", "right"])
    rival = "DEF" if equipo_ofensivo != "DEF" else "OTR"
    n_cuadros = rng.randint(1, 12)
    n_jug = rng.randint(0, 22)
    filas = []
    for f in range(1, n_cuadros + 1):
        evento_cuadro = rng.choice(EVENTOS + ["None", "None", ""])
        for j in range(n_jug):
            filas.append({
                "playId": play_id, "frameId": f, "nflId": 100 + j,
                "team": equipo_ofensivo if j % 2 == 0 else rival,
                "x": rng.uniform(-5, 125), "y": rng.uniform(-3, 57),
                "event": evento_cuadro if j == 0 else rng.choice(["None", evento_cuadro]),
                "playDirection": direccion,
            })
        if rng.random() < 0.8:
            filas.append({
                "playId": play_id, "frameId": f, "nflId": math.nan, "team": "football",
                "x": rng.uniform(-5, 125), "y": rng.uniform(-3, 57),
                "event": "None", "playDirection": direccion,
            })
    df = pd.DataFrame(filas, columns=COLUMNAS_TRACKING)
    if con_celdas_malas and len(df):
        for col in ("frameId", "x", "y"):
            for idx in rng.sample(range(len(df)), k=min(len(df), rng.randint(0, 3))):
                df[col] = df[col].astype(object)
                df.at[idx, col] = rng.choice(["NA", "abc", "", None])
    return df


# --------------------------------------------------------------------------
# Textos de personal
# --------------------------------------------------------------------------
POS_PERSONAL = ["RB", "TE", "WR", "QB", "OL", "DL", "LB", "DB", "FB"]


def generar_personal_valido(rng: random.Random) -> str:
    """Texto como '1 RB, 1 TE, 3 WR' con posiciones distintas."""
    posiciones = rng.sample(POS_PERSONAL, k=rng.randint(1, 5))
    return ", ".join(f"{rng.randint(0, 6)} {p}" for p in posiciones)


def generar_personal_invalido(rng: random.Random) -> str | None:
    """Texto que no cumple el formato '<n> <POS>' separado por comas."""
    return rng.choice([
        None, "", "   ", "abc", "1 RB 1 TE", "-1 RB", "1.5 RB", "x WR", "1 rb", "RB", "1 RB,, 2 WR", "1 RB, tres WR",
    ])
