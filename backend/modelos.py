"""Modelos Pydantic de la API (nombres y tipos fijados en design.md)."""

from typing import Literal

from pydantic import BaseModel, Field


class Jugada(BaseModel):
    gameId: int
    playId: int
    equipo: str
    rival: str
    down: int
    yardsToGo: int
    razon: str
    descripcion: str
    formacion: str | None = None
    personal: str | None = None
    cobertura: str | None = None


class Evento(BaseModel):
    frame: int
    evento: str


class JugadorFrame(BaseModel):
    nflId: int
    equipo: Literal["ofensiva", "defensiva"]
    x: float
    y: float


class Balon(BaseModel):
    x: float
    y: float


class Cuadro(BaseModel):
    frame: int
    jugadores: list[JugadorFrame]
    balon: Balon | None = None


class Tracking(BaseModel):
    eventos: list[Evento]
    cuadros: list[Cuadro]


class JugadaSimilar(BaseModel):
    gameId: int
    playId: int
    equipo: str
    rival: str
    yardsToGo: int
    playResult: int
    formacion: str | None = None
    personal: str | None = None
    cobertura: str | None = None


class Sugerencia(BaseModel):
    texto: str
    evidencia: str
    nMuestra: int
    confianza: Literal["baja", "media", "alta"]


class Solicitada(BaseModel):
    formacion: str | None = None
    personal: str | None = None
    alineacion: list[str]


class ValorDistribucion(BaseModel):
    valor: str
    porcentaje: float
    nMuestra: int


class Distribucion(BaseModel):
    formacion: list[ValorDistribucion]
    personal: list[ValorDistribucion]
    cobertura: list[ValorDistribucion]


class AlineacionConteo(BaseModel):
    posicion: str
    rol: str
    conteo: int


class ExitoFormacion(BaseModel):
    formacion: str
    tasaExito: float
    yardasPromedio: float
    nMuestra: int


class Top3(BaseModel):
    formacion: list[str]
    personal: list[str]
    alineacion: list[str]


class Comparacion(BaseModel):
    solicitada: Solicitada
    distribucion: Distribucion
    alineaciones: list[AlineacionConteo]
    rutasDisponibles: bool
    exitoPorFormacion: list[ExitoFormacion]
    top3: Top3


class Similares(BaseModel):
    similares: list[JugadaSimilar]
    sugerencias: list[Sugerencia]
    criteriosRelajados: list[str]
    comparacion: Comparacion


class SolicitudRecomendacion(BaseModel):
    jugada: Jugada
    sugerencias: list[Sugerencia] = Field(max_length=20)


class Recomendacion(BaseModel):
    recomendacion: str
    generado_por_ia: bool
