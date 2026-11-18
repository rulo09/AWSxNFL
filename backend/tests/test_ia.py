"""Pruebas de propiedades del router de IA (sin credenciales ni llamadas a Bedrock)."""
from __future__ import annotations

import random

from backend.modelos import Jugada, Sugerencia
from backend.routers import ia
from backend.tests.generadores import (
    COBERTURAS,
    EQUIPOS_PRUEBA,
    FORMACIONES,
    PERSONALES,
    repetir,
)

RAZONES = ["intercepcion", "sack", "incompleto", "perdida_de_yardas", "sin_conversion"]


def _texto(rng: random.Random, largo: bool = False) -> str:
    palabras = ["pase", "corrida", "ñandú", "cobertura", "línea", "yardas", "ofensiva", "éxito"]
    n = rng.randint(80, 200) if largo else rng.randint(1, 12)
    return " ".join(rng.choice(palabras) for _ in range(n))


def _jugada(rng: random.Random) -> Jugada:
    return Jugada(
        gameId=rng.randint(2021090000, 2021109999),
        playId=rng.randint(1, 4000),
        equipo=rng.choice(EQUIPOS_PRUEBA),
        rival=rng.choice(EQUIPOS_PRUEBA),
        down=rng.randint(1, 4),
        yardsToGo=rng.randint(1, 30),
        razon=rng.choice(RAZONES),
        descripcion=_texto(rng),
        formacion=rng.choice(FORMACIONES + [None]),
        personal=rng.choice(PERSONALES + [None]),
        cobertura=rng.choice(COBERTURAS + [None]),
    )


def _sugerencias(rng: random.Random) -> list[Sugerencia]:
    n = rng.choice([0, 1, 2, 20, rng.randint(0, 20)])
    largo = rng.random() < 0.3  # fuerza textos que superan el límite
    return [
        Sugerencia(
            texto=_texto(rng, largo),
            evidencia=_texto(rng, largo),
            nMuestra=rng.randint(0, 500),
            confianza=rng.choice(["baja", "media", "alta"]),
        )
        for _ in range(n)
    ]


# Feature: failed-plays-coach-app, Property 26
# Property 26: Fallback text is deterministic and bounded
# **Validates: Requirements 10.1, 10.7, 10.8**
def test_propiedad_26_respaldo_determinista_y_acotado(cliente, ia_stub):
    ia_stub.configurar(error=RuntimeError("fallo simulado de Bedrock"))

    def prueba(rng: random.Random) -> None:
        jugada = _jugada(rng)
        sugerencias = _sugerencias(rng)

        texto = ia.construir_respaldo(jugada, sugerencias)
        assert texto and texto.strip()
        assert len(texto) <= 1500
        # Determinista: misma entrada, mismo texto (también con copias de los objetos).
        assert ia.construir_respaldo(jugada, sugerencias) == texto
        assert ia.construir_respaldo(jugada.model_copy(), [s.model_copy() for s in sugerencias]) == texto
        if not sugerencias:
            assert texto == "No hay sugerencias disponibles para esta jugada."

        # Con el cliente de IA fallando, el endpoint devuelve el mismo respaldo.
        cuerpo = {
            "jugada": jugada.model_dump(),
            "sugerencias": [s.model_dump() for s in sugerencias],
        }
        r = cliente.post("/api/recomendacion", json=cuerpo)
        assert r.status_code == 200
        datos = r.json()
        assert datos["generado_por_ia"] is False
        assert datos["recomendacion"] == texto

    repetir(prueba, n=100)


# Feature: failed-plays-coach-app, Property 27
# Property 27: Prompt uses only the received data
# **Validates: Requirements 10.6**
def test_propiedad_27_prompt_solo_con_datos_recibidos():
    import re

    def prueba(rng: random.Random) -> None:
        jugada = _jugada(rng)
        sugerencias = _sugerencias(rng)
        prompt = ia.construir_prompt(jugada, sugerencias)

        for s in sugerencias:
            assert s.texto in prompt
            assert f"nMuestra: {s.nMuestra}" in prompt
        # Instrucción de citar tamaños de muestra y no inventar cifras.
        assert "nMuestra" in prompt
        assert "sin agregar cifras que no estén arriba" in prompt

        # Toda cifra del prompt proviene de la entrada (las instrucciones fijas no tienen cifras).
        # Se quitan primero los textos de entrada (equipo, formación, etc.), que pueden traer dígitos.
        restante = prompt
        textos = [jugada.equipo, jugada.rival, jugada.razon, jugada.descripcion,
                  jugada.formacion, jugada.personal, jugada.cobertura]
        for s in sugerencias:
            textos += [s.texto, s.evidencia, s.confianza]
        for t in sorted((t for t in textos if t), key=len, reverse=True):
            restante = restante.replace(t, "")
        permitidas = {str(jugada.down), str(jugada.yardsToGo)}
        permitidas |= {str(s.nMuestra) for s in sugerencias}
        assert set(re.findall(r"\d+", restante)) <= permitidas
        # Identificadores internos que no se recibieron como dato de redacción no se filtran.
        assert str(jugada.gameId) not in prompt

    repetir(prueba, n=100)


# Feature: failed-plays-coach-app, Property 28
# Property 28: Invalid recommendation bodies never reach the model
# **Validates: Requirements 10.9**
def test_propiedad_28_cuerpos_invalidos_no_llegan_al_modelo(cliente, ia_stub):
    import json

    valores_invalidos = ["abc", [1, 2], {"x": 1}, None]

    def cuerpo_valido(rng: random.Random) -> dict:
        return {
            "jugada": _jugada(rng).model_dump(),
            "sugerencias": [s.model_dump() for s in _sugerencias(rng)][:20],
        }

    def prueba(rng: random.Random) -> None:
        cuerpo = cuerpo_valido(rng)
        tipo = rng.choice(["sin_jugada", "campo_tipo", "campo_tipo_sugerencia", "mas_de_20", "json_invalido", "no_objeto"])
        contenido = None

        if tipo == "sin_jugada":
            cuerpo.pop("jugada")
        elif tipo == "campo_tipo":
            campo = rng.choice(["gameId", "playId", "down", "yardsToGo", "equipo", "rival", "razon", "descripcion"])
            textual = campo in ("equipo", "rival", "razon", "descripcion")
            cuerpo["jugada"][campo] = rng.choice(valores_invalidos[1:3] if textual else valores_invalidos[:3] + [None])
        elif tipo == "campo_tipo_sugerencia":
            if not cuerpo["sugerencias"]:
                cuerpo["sugerencias"] = [{"texto": "t", "evidencia": "e", "nMuestra": 1, "confianza": "alta"}]
            campo = rng.choice(["texto", "evidencia", "nMuestra", "confianza"])
            # "abc" es un str válido para texto y evidencia; solo se usa en campos no textuales.
            validos_texto = campo in ("texto", "evidencia")
            cuerpo["sugerencias"][0][campo] = rng.choice(valores_invalidos[1:3] if validos_texto else valores_invalidos[:3])
        elif tipo == "mas_de_20":
            base = {"texto": "t", "evidencia": "e", "nMuestra": 1, "confianza": "alta"}
            cuerpo["sugerencias"] = [dict(base) for _ in range(rng.randint(21, 40))]
        elif tipo == "json_invalido":
            texto = json.dumps(cuerpo)
            contenido = texto[: rng.randint(1, max(1, len(texto) - 1))] + "{"
        else:
            cuerpo = rng.choice([[], "texto", 5, None])

        if contenido is not None:
            r = cliente.post("/api/recomendacion", content=contenido, headers={"Content-Type": "application/json"})
        else:
            r = cliente.post("/api/recomendacion", json=cuerpo)

        assert r.status_code == 422, tipo
        detalle = r.json()["detail"]
        assert isinstance(detalle, str) and "no es válido" in detalle
        # Ni boto3 ni Agent ni BedrockModel fueron invocados.
        assert ia_stub.llamadas_cliente == []
        assert ia_stub.modelos == []
        assert ia_stub.prompts == []

    repetir(prueba, n=100)
