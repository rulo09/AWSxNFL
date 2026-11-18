"""Router ia: AI_Service. Recomendación en español con Bedrock Nova (opcional)."""

import asyncio
import logging
import os

from fastapi import APIRouter

from backend.modelos import Jugada, Recomendacion, Sugerencia, SolicitudRecomendacion

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

MAX_CARACTERES = 1500
TIMEOUT_SEGUNDOS = 20
SIN_SUGERENCIAS = "No hay sugerencias disponibles para esta jugada."

SISTEMA = (
    "Eres un asistente de análisis para entrenadores de fútbol americano. "
    "Responde siempre en español, en un máximo de 1500 caracteres. "
    "Usa solo los datos que recibes en el mensaje. "
    "Cita el tamaño de muestra (nMuestra) de cada sugerencia que menciones. "
    "No inventes cifras, porcentajes ni jugadas que no estén en los datos."
)


def construir_respaldo(jugada: Jugada, sugerencias: list[Sugerencia]) -> str:
    """Texto fijo en español, sin IA. Máximo 1500 caracteres."""
    if not sugerencias:
        return SIN_SUGERENCIAS
    lineas = [
        f"Jugada fallida: {jugada.equipo} vs {jugada.rival}, "
        f"{jugada.down} down y {jugada.yardsToGo} yardas por ganar "
        f"(razón: {jugada.razon}).",
        "Sugerencias basadas en jugadas efectivas similares:",
    ]
    for i, s in enumerate(sugerencias, start=1):
        lineas.append(
            f"{i}. {s.texto} {s.evidencia} (muestra: {s.nMuestra}, confianza {s.confianza})."
        )
    return "\n".join(lineas)[:MAX_CARACTERES]


def construir_prompt(jugada: Jugada, sugerencias: list[Sugerencia]) -> str:
    """Prompt con los datos recibidos únicamente."""
    partes = [
        "Datos de la jugada fallida:",
        f"- Equipo: {jugada.equipo}; rival: {jugada.rival}",
        f"- Down: {jugada.down}; yardas por ganar: {jugada.yardsToGo}",
        f"- Razón de la falla: {jugada.razon}",
        f"- Descripción: {jugada.descripcion}",
        f"- Formación: {jugada.formacion or 'Sin dato'}; "
        f"personal: {jugada.personal or 'Sin dato'}; "
        f"cobertura: {jugada.cobertura or 'Sin dato'}",
        "",
        "Sugerencias calculadas a partir de jugadas efectivas similares:",
    ]
    if not sugerencias:
        partes.append("- (ninguna)")
    for s in sugerencias:
        partes.append(
            f"- {s.texto} | Evidencia: {s.evidencia} | nMuestra: {s.nMuestra} | "
            f"confianza: {s.confianza}"
        )
    partes += [
        "",
        "Redacta una recomendación breve para el entrenador, en español, "
        "citando el nMuestra de cada sugerencia que uses y sin agregar cifras que no estén arriba.",
    ]
    return "\n".join(partes)


def generar_con_ia(prompt: str) -> str:
    """Llama a Bedrock Nova con Strands. Bloqueante; se ejecuta en un hilo."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    modelo_id = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")

    import boto3
    from strands import Agent
    from strands.models import BedrockModel

    cliente = boto3.client("bedrock-runtime", region_name=region)
    # BedrockModel (strands-agents 1.64.0) no acepta `client`: solo boto_session,
    # boto_client_config, region_name, endpoint_url, api_key y model_config.
    # Se pasa solo la región y se sustituye su cliente por el creado con la región.
    modelo = BedrockModel(model_id=modelo_id, region_name=region)
    modelo.client = cliente
    agente = Agent(model=modelo, system_prompt=SISTEMA, callback_handler=None)
    return str(agente(prompt)).strip()


@router.post("/recomendacion", response_model=Recomendacion)
async def recomendacion(solicitud: SolicitudRecomendacion) -> Recomendacion:
    respaldo = construir_respaldo(solicitud.jugada, solicitud.sugerencias)
    try:
        prompt = construir_prompt(solicitud.jugada, solicitud.sugerencias)
        texto = await asyncio.wait_for(
            asyncio.to_thread(generar_con_ia, prompt), timeout=TIMEOUT_SEGUNDOS
        )
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)):
            raise
        logger.warning("Fallo la generación con IA: %s", type(exc).__name__)
        return Recomendacion(recomendacion=respaldo, generado_por_ia=False)
    if not texto or not texto.strip():
        return Recomendacion(recomendacion=respaldo, generado_por_ia=False)
    return Recomendacion(recomendacion=texto[:MAX_CARACTERES], generado_por_ia=True)
