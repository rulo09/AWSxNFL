"""Router jugadas: filtros disponibles y lista de jugadas fallidas."""
from fastapi import APIRouter, HTTPException

from backend import datos
from backend.modelos import Jugada

router = APIRouter(prefix="/api")

DOWNS = [1, 2, 3, 4]
RAZONES = ["incompleto", "intercepcion", "sack", "sin_conversion", "perdida_de_yardas"]
_MSG_DATOS = "No se pudieron cargar los datos."


def _fallidas_o_500():
    fallidas = datos.jugadas_fallidas()
    if fallidas is None or fallidas.empty:
        raise HTTPException(status_code=500, detail=_MSG_DATOS)
    return fallidas


@router.get("/filtros")
def obtener_filtros() -> dict:
    fallidas = _fallidas_o_500()
    abreviaturas = sorted({str(e) for e in fallidas["equipo"].dropna().unique()})
    return {
        "downs": list(DOWNS),
        "razones": list(RAZONES),
        "equipos": [{"abbr": a, "nombre": datos.EQUIPOS.get(a)} for a in abreviaturas],
    }


@router.get("/jugadas", response_model=list[Jugada])
def listar_jugadas(
    down: str | None = None,
    razon: str | None = None,
    equipo: str | None = None,
) -> list[dict]:
    down_val = None
    if down is not None:
        try:
            down_val = int(down)
        except ValueError:
            down_val = None
        if down_val not in DOWNS:
            raise HTTPException(
                status_code=422,
                detail="El parámetro 'down' debe ser un entero entre 1 y 4.",
            )
    if razon is not None and razon not in RAZONES:
        raise HTTPException(
            status_code=422,
            detail="El parámetro 'razon' debe ser uno de: " + ", ".join(RAZONES) + ".",
        )

    fallidas = _fallidas_o_500()
    mascara = fallidas["gameId"].notna()
    if down_val is not None:
        mascara &= fallidas["down"] == down_val
    if razon is not None:
        mascara &= fallidas["razon"] == razon
    if equipo is not None:
        mascara &= fallidas["equipo"] == equipo

    columnas = [c for c in datos._CAMPOS_JUGADA if c in fallidas.columns]
    filas = fallidas.loc[mascara, columnas]
    return [datos.a_jugada(fila) for _, fila in filas.iterrows()]
