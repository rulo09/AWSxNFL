"""Prueba de propiedad: ida y vuelta JSON de los modelos Jugada y Similares."""
from __future__ import annotations
import random
from backend.modelos import Jugada, Similares
from backend.tests.generadores import repetir


def _opc(rng: random.Random, valores: list[str]) -> str | None:
    return None if rng.random() < 0.4 else rng.choice(valores)


FORM = ["SHOTGUN", "SINGLEBACK", "I_FORM", "EMPTY", "ñandú"]
PERS = ["1 RB, 1 TE, 3 WR", "2 RB, 1 TE, 2 WR"]
COB = ["Cover-3", "Cover-2", "Man", "Quarters"]


def _jugada(rng: random.Random) -> dict:
    return {
        "gameId": rng.randint(1, 10**10),
        "playId": rng.randint(1, 5000),
        "equipo": rng.choice(["KC", "BUF", "SF"]),
        "rival": rng.choice(["DEN", "MIA", "LA"]),
        "down": rng.randint(1, 4),
        "yardsToGo": rng.randint(1, 30),
        "razon": rng.choice(["Pase incompleto", "Pérdida de yardas", ""]),
        "descripcion": rng.choice(["(15:00) Pase corto \"x\"", "", "línea\nnueva"]),
        "formacion": _opc(rng, FORM),
        "personal": _opc(rng, PERS),
        "cobertura": _opc(rng, COB),
    }


def _similar(rng: random.Random) -> dict:
    return {
        "gameId": rng.randint(1, 10**10),
        "playId": rng.randint(1, 5000),
        "equipo": rng.choice(["KC", "BUF"]),
        "rival": rng.choice(["DEN", "MIA"]),
        "yardsToGo": rng.randint(1, 30),
        "playResult": rng.randint(-15, 80),
        "formacion": _opc(rng, FORM),
        "personal": _opc(rng, PERS),
        "cobertura": _opc(rng, COB),
    }


def _dist(rng: random.Random, valores: list[str]) -> list[dict]:
    return [
        {"valor": v, "porcentaje": round(rng.uniform(0, 100), 2), "nMuestra": rng.randint(0, 500)}
        for v in rng.sample(valores, rng.randint(0, len(valores)))
    ]


def _similares(rng: random.Random) -> dict:
    return {
        "similares": [_similar(rng) for _ in range(rng.randint(0, 5))],
        "sugerencias": [
            {
                "texto": "Probar otra formación",
                "evidencia": "Evidencia",
                "nMuestra": rng.randint(0, 100),
                "confianza": rng.choice(["baja", "media", "alta"]),
            }
            for _ in range(rng.randint(0, 4))
        ],
        "criteriosRelajados": rng.sample(["cobertura", "personal", "formacion"], rng.randint(0, 3)),
        "comparacion": {
            "solicitada": {
                "formacion": _opc(rng, FORM),
                "personal": _opc(rng, PERS),
                "alineacion": rng.sample(["QB", "RB", "WR", "TE"], rng.randint(0, 4)),
            },
            "distribucion": {
                "formacion": _dist(rng, FORM),
                "personal": _dist(rng, PERS),
                "cobertura": _dist(rng, COB),
            },
            "alineaciones": [
                {"posicion": rng.choice(["QB", "WR"]), "rol": rng.choice(["ofensiva", "defensiva"]),
                 "conteo": rng.randint(0, 50)}
                for _ in range(rng.randint(0, 4))
            ],
            "rutasDisponibles": rng.random() < 0.5,
            "exitoPorFormacion": [
                {"formacion": rng.choice(FORM), "tasaExito": round(rng.random(), 3),
                 "yardasPromedio": round(rng.uniform(-5, 20), 2), "nMuestra": rng.randint(0, 200)}
                for _ in range(rng.randint(0, 3))
            ],
            "top3": {
                "formacion": rng.sample(FORM, rng.randint(0, 3)),
                "personal": rng.sample(PERS, rng.randint(0, 2)),
                "alineacion": rng.sample(["QB", "RB", "WR", "TE"], rng.randint(0, 3)),
            },
        },
    }


def test_propiedad_30_ida_y_vuelta_json_jugada_y_similares():
    # Feature: failed-plays-coach-app, Property 30
    # Validates: Requirements 12.1, 12.6
    nulos = []

    def prueba(rng: random.Random) -> None:
        j = Jugada.model_validate(_jugada(rng))
        j2 = Jugada.model_validate_json(j.model_dump_json())
        assert j2 == j and j2.model_dump() == j.model_dump()

        s = Similares.model_validate(_similares(rng))
        s2 = Similares.model_validate_json(s.model_dump_json())
        assert s2 == s and s2.model_dump() == s.model_dump()

        nulos.append((j.formacion is None, j.personal is None, j.cobertura is None))
        nulos.extend((x.formacion is None, x.personal is None, x.cobertura is None) for x in s.similares)

    repetir(prueba)
    for i in range(3):
        col = [n[i] for n in nulos]
        assert any(col) and not all(col)
