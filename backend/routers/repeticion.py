"""Router repeticion: tracking de una jugada para la repetición animada."""
from fastapi import APIRouter, HTTPException

from backend import datos, tracking

router = APIRouter(prefix="/api")

_MSG_404 = "No se encontraron datos de tracking para esta jugada."


@router.get("/jugadas/{gameId}/{playId}/tracking")
def obtener_tracking(gameId: int, playId: int) -> dict:
    jugada = datos.obtener_jugada(gameId, playId)
    if jugada is None:
        raise HTTPException(status_code=404, detail=_MSG_404)
    resultado = tracking.leer_tracking(gameId, playId, jugada.get("equipo"))
    if resultado is None:
        raise HTTPException(status_code=404, detail=_MSG_404)
    return resultado
