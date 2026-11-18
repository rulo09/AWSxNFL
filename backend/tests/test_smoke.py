"""Pruebas de humo del esqueleto: /health, prefijo /api y routers registrados.

Validates: Requirements 1.1, 1.3, 1.4
"""
from __future__ import annotations

from fastapi.routing import APIRoute, APIRouter
from starlette.routing import Mount

from backend import main
from backend.routers import ia, jugadas, repeticion, similares

ROUTERS = {"jugadas": jugadas, "similares": similares, "repeticion": repeticion, "ia": ia}


def test_health_responde_ok(cliente):
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_toda_ruta_salvo_health_empieza_con_api():
    rutas = [r for r in main.app.routes if isinstance(r, APIRoute)]
    assert any(r.path == "/health" for r in rutas)
    # Se ignoran documentación (/docs, /openapi.json, /redoc) y montajes estáticos.
    ignoradas = {"/health", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
    for ruta in main.app.routes:
        if isinstance(ruta, Mount) or ruta.path in ignoradas:
            continue
        assert ruta.path.startswith("/api/"), ruta.path


def test_cuatro_routers_registrados_con_prefijo_api():
    paths_app = {r.path for r in main.app.routes if isinstance(r, APIRoute)}
    for nombre, modulo in ROUTERS.items():
        router = getattr(modulo, "router", None)
        assert isinstance(router, APIRouter), nombre
        assert router.prefix == "/api", nombre
        # Cada ruta declarada por el router debe estar en la app.
        for ruta in router.routes:
            assert ruta.path in paths_app, (nombre, ruta.path)
    # main importa los cuatro módulos y los incluye.
    for nombre, modulo in ROUTERS.items():
        assert getattr(main, nombre) is modulo
