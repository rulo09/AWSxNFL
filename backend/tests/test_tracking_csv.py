"""Pruebas de propiedades de la lectura de tracking con celdas inválidas."""
from __future__ import annotations
import random
import pandas as pd
from backend import tracking
from backend.tests.generadores import generar_tracking, repetir
def test_propiedad_31_parseo_tolera_celdas_malas(tmp_path):
    # Feature: failed-plays-coach-app, Property 31
    # Validates: Requirements 12.7, 12.8
    contador = {"n": 0}
    def prueba(rng: random.Random) -> None:
        ofensivo = rng.choice(["TB", "KC"])
        play_id = rng.randint(1, 99)
        df = generar_tracking(rng, play_id=play_id, equipo_ofensivo=ofensivo, con_celdas_malas=True)
        # Columna `time` con texto inválido en algunas filas (se ignora al leer).
        df["time"] = [rng.choice(["2023-09-10T13:00:00", "abc", "", "NA"]) for _ in range(len(df))]
        # Cada iteración usa su propio directorio temporal (fuera de data/).
        contador["n"] += 1
        carpeta = tmp_path / f"it{contador['n']}"
        (carpeta / "tracking").mkdir(parents=True)
        df.to_csv(carpeta / "tracking" / "tracking_1.csv", index=False)
        resultado = tracking.leer_tracking(1, play_id, ofensivo, data_dir=carpeta)
        num = {c: pd.to_numeric(df[c], errors="coerce") for c in ("frameId", "x", "y")}
        validos = df[num["frameId"].notna()].copy()
        validos["frameId"] = num["frameId"][validos.index].astype(int)
        validos["x"], validos["y"] = num["x"][validos.index], num["y"][validos.index]
        if validos.empty:
            assert resultado is None
            return
        assert resultado is not None
        # Las filas con frameId inválido se descartan; las demás conservan su cuadro.
        assert [c["frame"] for c in resultado["cuadros"]] == sorted(validos["frameId"].unique())
        for c in resultado["cuadros"]:
            filas = validos[validos["frameId"] == c["frame"]]
            jug = filas[(filas["team"] != "football") & filas["x"].notna() & filas["y"].notna()]
            assert len(c["jugadores"]) == jug["nflId"].nunique()
            futbol = filas[(filas["team"] == "football") & filas["x"].notna() & filas["y"].notna()]
            assert (c["balon"] is None) == futbol.empty
        # Los eventos vacíos y 'None' no cuentan como evento.
        for e in resultado["eventos"]:
            assert e["evento"] not in ("", "None")
    repetir(prueba, n=100)
