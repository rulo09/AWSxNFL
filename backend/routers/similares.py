"""Router similares: Similar_Finder (jugadas efectivas de otros equipos)."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend import datos
from backend.modelos import Similares

router = APIRouter(prefix="/api")

MINIMO_COINCIDENCIAS = 5
LIMITE_SIMILARES = 20
TOLERANCIA_INICIAL = 2
TOLERANCIA_RELAJADA = 4

COLUMNAS_SIMILAR = [
    "gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
    "formacion", "personal", "cobertura",
]


def etiqueta_confianza(n: int) -> str:
    """baja para 1-4, media para 5-14, alta para 15 o más (Requisito 9.2)."""
    if n >= 15:
        return "alta"
    if n >= 5:
        return "media"
    return "baja"


def _nulo(valor) -> bool:
    return valor is None or bool(pd.isna(valor))


def buscar_similares(
    jugada: dict, efectivas: pd.DataFrame, misma_cobertura: bool
) -> tuple[pd.DataFrame, list[str], dict]:
    """Selecciona jugadas efectivas similares y relaja criterios si hay pocas.

    Devuelve (similares, criteriosRelajados, info) con info = {"tolerancia": int}.
    Nunca relaja down, equipo distinto ni misma_cobertura (7.3-7.9).
    """
    relajados: list[str] = []
    activos = {"personnelO": True, "offenseFormation": True, "cobertura": bool(misma_cobertura)}
    tolerancia = TOLERANCIA_INICIAL

    # Criterios con valor nulo en la jugada solicitada se descartan desde el inicio (7.8).
    if _nulo(jugada.get("formacion")):
        activos["offenseFormation"] = False
        relajados.append("offenseFormation")
    if _nulo(jugada.get("personal")):
        activos["personnelO"] = False
        relajados.append("personnelO")
    if misma_cobertura and _nulo(jugada.get("cobertura")):
        activos["cobertura"] = False
        relajados.append("pff_passCoverage")

    base = (efectivas["equipo"] != jugada["equipo"]) & (efectivas["down"] == jugada["down"])

    def seleccionar() -> pd.DataFrame:
        mascara = base & ((efectivas["yardsToGo"] - jugada["yardsToGo"]).abs() <= tolerancia)
        if activos["offenseFormation"]:
            mascara &= efectivas["formacion"] == jugada["formacion"]
        if activos["personnelO"]:
            mascara &= efectivas["personal"] == jugada["personal"]
        if activos["cobertura"]:
            mascara &= efectivas["cobertura"] == jugada["cobertura"]
        return efectivas[mascara]

    seleccion = seleccionar()
    # Orden de relajación (7.9): personnelO, yardsToGo, offenseFormation.
    for paso in ("personnelO", "yardsToGo", "offenseFormation"):
        if len(seleccion) >= MINIMO_COINCIDENCIAS:
            break
        if paso == "yardsToGo":
            tolerancia = TOLERANCIA_RELAJADA
            relajados.append("yardsToGo")
        elif activos[paso]:
            activos[paso] = False
            relajados.append(paso)
        else:
            continue  # ya descartado por valor nulo: no se lista dos veces
        seleccion = seleccionar()

    seleccion = (
        seleccion.sort_values(["playResult", "gameId", "playId"], ascending=[False, True, True])
        .head(LIMITE_SIMILARES)
        .reset_index(drop=True)
    )
    return seleccion, relajados, {"tolerancia": tolerancia}


def _a_dicts(similares: pd.DataFrame) -> list[dict]:
    return [datos.a_jugada(fila) for fila in similares[COLUMNAS_SIMILAR].to_dict("records")]


POSICIONES_RUTA = ("WR", "TE", "RB", "FB")
LIMITE_ALINEACIONES = 10
_UMBRALES_EFECTIVA = {1: 0.4, 2: 0.6, 3: 1.0, 4: 1.0}


def _filtrar_rutas(pff: pd.DataFrame) -> pd.DataFrame:
    """Filas de ruta de pase de WR, TE, RB y FB con alineación conocida (8.1-8.3)."""
    if pff is None or pff.empty or "officialPosition" not in pff.columns:
        return pd.DataFrame(columns=["gameId", "playId", "pff_positionLinedUp", "pff_role"])
    mascara = (
        (pff["pff_role"] == "Pass Route")
        & pff["officialPosition"].isin(POSICIONES_RUTA)
        & pff["pff_positionLinedUp"].notna()
    )
    return pff[mascara]


def _distribucion(valores: pd.Series, total: int) -> list[dict]:
    """Porcentaje con 1 decimal sobre `total` (len(similares)); orden: conteo desc, valor asc."""
    conteo = valores.dropna().value_counts()
    filas = sorted(conteo.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return [
        {"valor": str(v), "porcentaje": round(100 * int(n) / total, 1), "nMuestra": total}
        for v, n in filas
    ]


def _top3(valores: pd.Series) -> list[str]:
    conteo = valores.dropna().value_counts()
    filas = sorted(conteo.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return [str(v) for v, _ in filas[:3]]


def construir_grupo_8_5(jugada: dict, tolerancia: int) -> pd.DataFrame:
    """Grupo amplio de 8.5: otros equipos, mismo down y yardsToGo dentro de la tolerancia.

    Devuelve columnas formacion, playResult, efectiva (bool) y yardsToGo.
    """
    plays = datos.todas_las_jugadas()
    columnas = ["formacion", "playResult", "efectiva", "yardsToGo"]
    if plays is None or plays.empty:
        return pd.DataFrame(columns=columnas)
    df = plays.rename(columns={"possessionTeam": "equipo", "offenseFormation": "formacion"})
    df = df[df["down"].isin([1, 2, 3, 4])]
    df = df[
        (df["equipo"] != jugada["equipo"])
        & (df["down"] == jugada["down"])
        & ((df["yardsToGo"] - jugada["yardsToGo"]).abs() <= tolerancia)
    ].copy()
    umbral = df["down"].map(_UMBRALES_EFECTIVA)
    df["efectiva"] = (
        df["razon"].isna()
        & (df["passResult"] == "C")
        & (df["playResult"] >= umbral * df["yardsToGo"])
    )
    return df[columnas]


def construir_comparacion(
    jugada: dict, similares: pd.DataFrame, grupo_8_5: pd.DataFrame, tolerancia: int
) -> dict:
    """Datos de comparación del Requisito 8 (distribuciones, alineaciones, éxito, top3)."""
    total = len(similares)
    pff = _filtrar_rutas(datos._pff)

    # Alineaciones de la jugada solicitada (8.8: sin filas pff -> rutasDisponibles false).
    pff_total = datos._pff
    if pff_total is not None and not pff_total.empty:
        tiene_pff = bool(
            ((pff_total["gameId"] == jugada["gameId"]) & (pff_total["playId"] == jugada["playId"])).any()
        )
    else:
        tiene_pff = False
    alineacion_solicitada: list[str] = []
    alineaciones: list[dict] = []
    top3_alineacion: list[str] = []
    if tiene_pff:
        propias = pff[(pff["gameId"] == jugada["gameId"]) & (pff["playId"] == jugada["playId"])]
        alineacion_solicitada = sorted(str(p) for p in propias["pff_positionLinedUp"])
        if total:
            claves = similares[["gameId", "playId"]].drop_duplicates()
            rutas = pff.merge(claves, on=["gameId", "playId"], how="inner")
            if not rutas.empty:
                grupos = rutas.groupby(["pff_positionLinedUp", "pff_role"]).size().reset_index(name="conteo")
                grupos = grupos.sort_values(["conteo", "pff_positionLinedUp"], ascending=[False, True])
                alineaciones = [
                    {"posicion": str(f.pff_positionLinedUp), "rol": str(f.pff_role), "conteo": int(f.conteo)}
                    for f in grupos.head(LIMITE_ALINEACIONES).itertuples()
                ]
                top3_alineacion = [
                    a["posicion"] for a in sorted(alineaciones, key=lambda a: (-a["conteo"], a["posicion"]))[:3]
                ]

    distribucion = {"formacion": [], "personal": [], "cobertura": []}
    top3 = {"formacion": [], "personal": [], "alineacion": top3_alineacion}
    if total:
        for campo in ("formacion", "personal", "cobertura"):
            distribucion[campo] = _distribucion(similares[campo], total)
        top3["formacion"] = _top3(similares["formacion"])
        top3["personal"] = _top3(similares["personal"])

    exito: list[dict] = []
    if grupo_8_5 is not None and not grupo_8_5.empty:
        grupo = grupo_8_5
        if "yardsToGo" in grupo.columns and not _nulo(jugada.get("yardsToGo")):
            grupo = grupo[(grupo["yardsToGo"] - jugada["yardsToGo"]).abs() <= tolerancia]
        grupo = grupo[grupo["formacion"].notna() & grupo["playResult"].notna()]
        for formacion, g in grupo.groupby("formacion"):
            n = len(g)
            exito.append({
                "formacion": str(formacion),
                "tasaExito": round(100 * float(g["efectiva"].sum()) / n, 1),
                "yardasPromedio": round(float(g["playResult"].mean()), 1),
                "nMuestra": int(n),
            })
        exito.sort(key=lambda e: (-e["nMuestra"], e["formacion"]))

    return {
        "solicitada": {
            "formacion": jugada.get("formacion"),
            "personal": jugada.get("personal"),
            "alineacion": alineacion_solicitada,
        },
        "distribucion": distribucion,
        "alineaciones": alineaciones,
        "rutasDisponibles": tiene_pff,
        "exitoPorFormacion": exito,
        "top3": top3,
    }


LIMITE_SUGERENCIAS = 5
LIMITE_TEXTO = 280


def _recortar(texto: str) -> str:
    return texto[:LIMITE_TEXTO]


def _valor_mas_comun(valores: pd.Series) -> tuple[str, int] | None:
    """Valor más frecuente (empates por orden alfabético) y su conteo, o None."""
    conteo = valores.dropna().value_counts()
    if conteo.empty:
        return None
    valor, n = sorted(conteo.items(), key=lambda kv: (-kv[1], str(kv[0])))[0]
    return str(valor), int(n)


def _candidato(texto: str, evidencia: str, n: int) -> dict:
    return {
        "texto": _recortar(texto),
        "evidencia": _recortar(evidencia),
        "nMuestra": int(n),
        "confianza": etiqueta_confianza(int(n)),
    }


def generar_sugerencias(jugada: dict, similares: pd.DataFrame, comparacion: dict) -> list[dict]:
    """Hasta 5 sugerencias con plantillas fijas (Requisito 9).

    Orden de generación: formación, personal, cobertura, alineación, ganancia promedio.
    nMuestra cuenta jugadas dentro de `similares`, por lo que nunca supera len(similares).
    """
    total = len(similares)
    if total == 0:
        return []
    candidatos: list[dict] = []

    # 1. Formación más común.
    comun = _valor_mas_comun(similares["formacion"])
    if comun:
        x, n = comun
        evidencia = f"{n} de {total} jugadas efectivas similares usaron {x}"
        exito = next((e for e in comparacion.get("exitoPorFormacion", []) if e["formacion"] == x), None)
        if exito:
            evidencia += (
                f"; éxito de la formación {exito['tasaExito']} % "
                f"en {exito['nMuestra']} jugadas del mismo down."
            )
        else:
            evidencia += "."
        candidatos.append(_candidato(f"Considerar la formación {x}.", evidencia, n))

    # 2. Personal más común.
    comun = _valor_mas_comun(similares["personal"])
    if comun:
        x, n = comun
        candidatos.append(_candidato(
            f"Considerar el personal {x}.",
            f"{n} de {total} jugadas efectivas similares usaron personal {x}.",
            n,
        ))

    # 3. Cobertura rival más común.
    comun = _valor_mas_comun(similares["cobertura"])
    if comun:
        x, n = comun
        candidatos.append(_candidato(
            f"Tener en cuenta la cobertura rival {x}.",
            f"{n} de {total} jugadas efectivas similares enfrentaron la cobertura {x}.",
            n,
        ))

    # 4. Alineación más común en datos de ruta (solo si hay rutas disponibles).
    if comparacion.get("rutasDisponibles"):
        pff = _filtrar_rutas(datos._pff)
        claves = similares[["gameId", "playId"]].drop_duplicates()
        rutas = pff.merge(claves, on=["gameId", "playId"], how="inner")
        if not rutas.empty:
            por_jugada = rutas[["gameId", "playId", "pff_positionLinedUp"]].drop_duplicates()
            comun = _valor_mas_comun(por_jugada["pff_positionLinedUp"])
            if comun:
                x, n = comun
                candidatos.append(_candidato(
                    f"Considerar un receptor alineado en {x}.",
                    f"{n} de {total} jugadas efectivas similares tuvieron una ruta desde la alineación {x}.",
                    n,
                ))

    # 5. Mayor ganancia promedio entre las formaciones presentes.
    con_formacion = similares[similares["formacion"].notna()]
    if not con_formacion.empty:
        medias = con_formacion.groupby("formacion")["playResult"].mean()
        mejor = sorted(medias.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]
        grupo = con_formacion[con_formacion["formacion"] == mejor]
        n = len(grupo)
        y = round(float(grupo["playResult"].mean()), 1)
        candidatos.append(_candidato(
            f"Ganancia promedio de {y} yardas con {mejor}.",
            f"Promedio de {y} yardas en {n} de {total} jugadas efectivas similares con la formación {mejor}.",
            n,
        ))

    candidatos = [c for c in candidatos if c["nMuestra"] > 0]
    candidatos.sort(key=lambda c: -c["nMuestra"])  # sort estable: empates conservan el orden
    return candidatos[:LIMITE_SUGERENCIAS]


@router.get("/jugadas/{gameId}/{playId}/similares", response_model=Similares)
def obtener_similares(gameId: int, playId: int, misma_cobertura: bool = False) -> dict:
    jugada = datos.obtener_jugada(gameId, playId)
    if jugada is None:
        raise HTTPException(status_code=404, detail="Jugada no encontrada.")
    similares, relajados, info = buscar_similares(jugada, datos.jugadas_efectivas(), misma_cobertura)
    tolerancia = info["tolerancia"]
    grupo = construir_grupo_8_5(jugada, tolerancia)
    comparacion = construir_comparacion(jugada, similares, grupo, tolerancia)
    return {
        "similares": _a_dicts(similares),
        "sugerencias": generar_sugerencias(jugada, similares, comparacion),
        "criteriosRelajados": relajados,
        "comparacion": comparacion,
    }
