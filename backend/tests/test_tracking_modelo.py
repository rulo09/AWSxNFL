"""Pruebas de propiedades de `tracking.a_modelo` (estructura y eventos)."""
from __future__ import annotations

import random

from backend import tracking
from backend.tests.generadores import generar_tracking, repetir


def _decimales_ok(valor: float) -> bool:
    return round(valor, 2) == valor


def test_propiedad_10_estructura_del_tracking():
    # Feature: failed-plays-coach-app, Property 10
    # Validates: Requirements 5.3, 5.6, 5.7
    def prueba(rng: random.Random) -> None:
        ofensivo = rng.choice(["TB", "DEF", "KC"])
        df = generar_tracking(rng, play_id=rng.randint(1, 99), equipo_ofensivo=ofensivo)
        modelo = tracking.a_modelo(df, ofensivo)
        cuadros = modelo["cuadros"]

        frames_esperados = sorted({int(f) for f in df["frameId"]})
        assert [c["frame"] for c in cuadros] == frames_esperados
        direccion = df["playDirection"].iloc[0] if len(df) else "right"

        for c in cuadros:
            assert type(c["frame"]) is int
            filas = df[df["frameId"] == c["frame"]]
            assert len(c["jugadores"]) <= 22
            equipos_por_id = {
                int(r.nflId): r.team for r in filas.itertuples() if r.team != "football"
            }
            assert len(c["jugadores"]) == len(equipos_por_id)
            for j in c["jugadores"]:
                assert type(j["nflId"]) is int
                assert j["nflId"] in equipos_por_id
                esperado = "ofensiva" if equipos_por_id[j["nflId"]] == ofensivo else "defensiva"
                assert j["equipo"] == esperado
                assert _decimales_ok(j["x"]) and _decimales_ok(j["y"])
            futbol = filas[filas["team"] == "football"]
            if futbol.empty:
                assert c["balon"] is None
            else:
                bx, by = tracking.normalizar(
                    float(futbol["x"].iloc[0]), float(futbol["y"].iloc[0]), direccion
                )
                assert c["balon"] == {"x": round(bx, 2), "y": round(by, 2)}

    repetir(prueba, n=100)


def test_propiedad_11_extraccion_de_eventos():
    # Feature: failed-plays-coach-app, Property 11
    # Validates: Requirements 5.8
    def prueba(rng: random.Random) -> None:
        ofensivo = rng.choice(["TB", "DEF", "KC"])
        df = generar_tracking(rng, play_id=rng.randint(1, 99), equipo_ofensivo=ofensivo)
        if rng.random() < 0.2:
            # Columna sin eventos reales: vacíos, espacios, 'None' y nulos.
            df["event"] = [rng.choice(["", "  ", "None", None]) for _ in range(len(df))]

        eventos = tracking.a_modelo(df, ofensivo)["eventos"]

        esperados = set()
        for fila in df.itertuples():
            ev = fila.event
            if ev is None or (isinstance(ev, float) and ev != ev):
                continue
            ev = str(ev).strip()
            if ev and ev != "None":
                esperados.add((int(fila.frameId), ev))

        pares = [(e["frame"], e["evento"]) for e in eventos]
        assert all(e["evento"] and e["evento"] != "None" for e in eventos)
        assert all(e["evento"] is not None for e in eventos)
        assert len(pares) == len(set(pares))
        assert pares == sorted(pares)
        assert [p[0] for p in pares] == sorted(p[0] for p in pares)
        assert set(pares) == esperados
        if not esperados:
            assert eventos == []

    repetir(prueba, n=100)
