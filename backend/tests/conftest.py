"""Fixtures compartidas. Ninguna prueba necesita credenciales ni llama a Bedrock."""
from __future__ import annotations

import random
import sys
import types

import pytest

from backend.tests import generadores


class _AgenteFalso:
    """Sustituto de strands.Agent. Se configura con `ia_stub`."""

    config = {"texto": "Recomendación de prueba.", "error": None, "espera": 0.0}

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs

    def __call__(self, prompt, *args, **kwargs):
        import time

        _AgenteFalso.config["prompts"].append(prompt)
        if _AgenteFalso.config["espera"]:
            time.sleep(_AgenteFalso.config["espera"])
        if _AgenteFalso.config["error"] is not None:
            raise _AgenteFalso.config["error"]
        return _AgenteFalso.config["texto"]


class IAStub:
    """Controla el comportamiento del Agent falso y registra las llamadas."""

    def __init__(self):
        self.llamadas_cliente: list[tuple[tuple, dict]] = []
        self.prompts: list[str] = []
        self.modelos: list[dict] = []
        _AgenteFalso.config = {"texto": "Recomendación de prueba.", "error": None, "espera": 0.0, "prompts": self.prompts}

    def configurar(self, texto: str | None = None, error: Exception | None = None, espera: float | None = None):
        if texto is not None:
            _AgenteFalso.config["texto"] = texto
        _AgenteFalso.config["error"] = error
        if espera is not None:
            _AgenteFalso.config["espera"] = espera


@pytest.fixture(autouse=True)
def ia_stub(monkeypatch):
    """Reemplaza `boto3` y `strands` en sys.modules para toda prueba.

    `boto3.client(...)` solo registra los argumentos. `strands.Agent` devuelve
    el texto configurado, falla o espera según `ia_stub.configurar(...)`.
    """
    stub = IAStub()

    boto3 = types.ModuleType("boto3")

    def client(*args, **kwargs):
        stub.llamadas_cliente.append((args, kwargs))
        return object()

    boto3.client = client

    class _BedrockModel:
        def __init__(self, *args, **kwargs):
            stub.modelos.append(kwargs)

    strands = types.ModuleType("strands")
    strands.Agent = _AgenteFalso
    modelos = types.ModuleType("strands.models")
    modelos.BedrockModel = _BedrockModel
    strands.models = modelos

    monkeypatch.setitem(sys.modules, "boto3", boto3)
    monkeypatch.setitem(sys.modules, "strands", strands)
    monkeypatch.setitem(sys.modules, "strands.models", modelos)
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    return stub


@pytest.fixture
def cliente():
    """TestClient de la app. Sin `with`, así no corre el lifespan ni carga data/."""
    from fastapi.testclient import TestClient

    from backend.main import app

    return TestClient(app)


@pytest.fixture
def rng() -> random.Random:
    return random.Random(generadores.SEMILLA)


@pytest.fixture
def poner_datos(monkeypatch):
    """Devuelve una función que reemplaza el estado del módulo `datos`.

    Uso: `poner_datos(tabla_jugadas, pff=None)` y devuelve el estado aplicado.
    Los atributos se restauran al terminar la prueba.
    """

    def _poner(jugadas, pff=None) -> dict:
        from backend import datos

        estado = generadores.estado_datos(jugadas, pff)
        for nombre, valor in estado.items():
            monkeypatch.setattr(datos, nombre, valor, raising=False)
        return estado

    return _poner


@pytest.fixture
def datos_generados(rng, poner_datos):
    """Estado de `datos` con una tabla generada (con semilla fija)."""
    jugadas = generadores.generar_jugadas(rng, n=40)
    claves = [(int(g), int(p)) for g, p in zip(jugadas["gameId"], jugadas["playId"])] or None
    return poner_datos(jugadas, generadores.generar_scouting(rng, claves=claves))
