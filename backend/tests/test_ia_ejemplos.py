"""Pruebas de ejemplo del endpoint POST /api/recomendacion con el Agent falso.

Requisitos: 10.2, 10.3, 10.4, 10.7
"""
import pytest

from backend.routers import ia

CUERPO = {
    "jugada": {
        "gameId": 1,
        "playId": 10,
        "equipo": "KC",
        "rival": "BUF",
        "down": 3,
        "yardsToGo": 7,
        "razon": "Pase incompleto",
        "descripcion": "Pase profundo incompleto",
        "formacion": "SHOTGUN",
        "personal": "11",
        "cobertura": "Cover-3",
    },
    "sugerencias": [
        {
            "texto": "Probar formación SHOTGUN",
            "evidencia": "8 de 10 jugadas efectivas",
            "nMuestra": 10,
            "confianza": "media",
        }
    ],
}


def test_cuerpo_valido_usa_ia(cliente, ia_stub):
    ia_stub.configurar(texto="Texto de la IA.")
    r = cliente.post("/api/recomendacion", json=CUERPO)
    assert r.status_code == 200
    assert r.json() == {"recomendacion": "Texto de la IA.", "generado_por_ia": True}


def test_agent_que_falla_devuelve_respaldo(cliente, ia_stub):
    ia_stub.configurar(error=RuntimeError("falla"))
    r = cliente.post("/api/recomendacion", json=CUERPO)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["generado_por_ia"] is False
    solicitud = ia.SolicitudRecomendacion(**CUERPO)
    assert cuerpo["recomendacion"] == ia.construir_respaldo(solicitud.jugada, solicitud.sugerencias)


def test_agent_lento_supera_timeout_y_devuelve_respaldo(cliente, ia_stub, monkeypatch):
    monkeypatch.setattr(ia, "TIMEOUT_SEGUNDOS", 0.05)
    ia_stub.configurar(espera=0.5)
    r = cliente.post("/api/recomendacion", json=CUERPO)
    assert r.status_code == 200
    assert r.json()["generado_por_ia"] is False
    assert r.json()["recomendacion"]


def test_texto_vacio_devuelve_respaldo(cliente, ia_stub):
    ia_stub.configurar(texto="   ")
    r = cliente.post("/api/recomendacion", json=CUERPO)
    assert r.status_code == 200
    assert r.json()["generado_por_ia"] is False


@pytest.mark.parametrize("region_env, esperada", [(None, "us-east-1"), ("us-west-2", "us-west-2")])
def test_boto3_client_solo_con_region(cliente, ia_stub, monkeypatch, region_env, esperada):
    if region_env is None:
        monkeypatch.delenv("AWS_REGION", raising=False)
    else:
        monkeypatch.setenv("AWS_REGION", region_env)
    r = cliente.post("/api/recomendacion", json=CUERPO)
    assert r.status_code == 200
    assert ia_stub.llamadas_cliente == [(("bedrock-runtime",), {"region_name": esperada})]


def test_modelo_por_defecto(cliente, ia_stub, monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    cliente.post("/api/recomendacion", json=CUERPO)
    assert len(ia_stub.modelos) == 1
    assert ia_stub.modelos[0]["model_id"] == "us.amazon.nova-pro-v1:0"


def test_modelo_desde_variable_de_entorno(cliente, ia_stub, monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
    cliente.post("/api/recomendacion", json=CUERPO)
    assert ia_stub.modelos[0]["model_id"] == "us.amazon.nova-lite-v1:0"
