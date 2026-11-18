"""API de la aplicación. Ejecuta: .venv/bin/uvicorn backend.main:app --reload"""
import os
from pathlib import Path


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()

import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from backend import datos  # noqa: E402
from backend.routers import ia, jugadas, repeticion, similares  # noqa: E402

logger = logging.getLogger("backend")

DIST_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Si falta un CSV, cargar() lanza RuntimeError con el nombre del archivo
    # y el arranque se aborta.
    datos.cargar()
    yield


app = FastAPI(title="Hackathon NFL UNAM", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def manejar_validacion(request: Request, exc: RequestValidationError):
    campo = "solicitud"
    errores = exc.errors()
    if errores:
        loc = [str(p) for p in errores[0].get("loc", ())]
        if loc and loc[0] in ("query", "path", "body", "header", "cookie"):
            loc = loc[1:]
        if loc:
            campo = ".".join(loc)
    return JSONResponse(
        status_code=422,
        content={"detail": f"El valor del campo '{campo}' no es válido."},
    )


@app.exception_handler(Exception)
async def manejar_excepcion(request: Request, exc: Exception):
    logger.error("Error no controlado: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno. Intenta de nuevo."},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(jugadas.router)
app.include_router(repeticion.router)
app.include_router(similares.router)
app.include_router(ia.router)

# Debe ir al final para no tapar la API.
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="dashboard")
