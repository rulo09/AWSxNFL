"""Pruebas de propiedades de los criterios de jugadas similares (Persona A)."""
from __future__ import annotations

import pandas as pd

from backend import datos
from backend.tests import generadores
from backend.tests.generadores import es_efectiva_referencia, generar_jugadas, repetir


def _escribir_csv(carpeta, jugadas: pd.DataFrame) -> None:
    """Escribe en `carpeta` los cuatro CSV mínimos que lee `datos.cargar`."""
    jugadas.to_csv(carpeta / "plays.csv", index=False)
    pd.DataFrame({"gameId": sorted(jugadas["gameId"].unique())}).to_csv(carpeta / "games.csv", index=False)
    pd.DataFrame({"nflId": [1], "officialPosition": ["WR"]}).to_csv(carpeta / "players.csv", index=False)
    pd.DataFrame(
        columns=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"]
    ).to_csv(carpeta / "pffScoutingData.csv", index=False)


def test_propiedad_12_regla_de_jugada_efectiva(tmp_path, monkeypatch):
    """Feature: failed-plays-coach-app, Property 12

    **Validates: Requirements 7.1**

    Una jugada es efectiva exactamente cuando la referencia independiente lo dice.
    """
    for nombre in ("_plays", "_fallidas", "_efectivas", "_pff", "_equipos_con_fallas"):
        monkeypatch.setattr(datos, nombre, getattr(datos, nombre))
    total = {"efectivas": 0}

    def prueba(rng):
        jugadas = generar_jugadas(rng, n=rng.randint(1, 40))
        carpeta = tmp_path / f"it{rng.random()}"
        carpeta.mkdir()
        _escribir_csv(carpeta, jugadas)
        datos.cargar(carpeta)

        esperadas = {
            (int(f["gameId"]), int(f["playId"]))
            for _, f in jugadas.iterrows()
            if es_efectiva_referencia(f)
        }
        obtenidas_df = datos.jugadas_efectivas()
        obtenidas = set(zip(obtenidas_df["gameId"].astype(int), obtenidas_df["playId"].astype(int)))
        assert len(obtenidas) == len(obtenidas_df), "hay jugadas efectivas duplicadas"
        assert obtenidas == esperadas, f"sobran {obtenidas - esperadas}, faltan {esperadas - obtenidas}"
        total["efectivas"] += len(esperadas)

    repetir(prueba, n=100, semilla=generadores.SEMILLA)
    assert total["efectivas"] > 0, "el generador nunca produjo jugadas efectivas"


def test_propiedad_13_similares_cumplen_criterios_activos():
    """Feature: failed-plays-coach-app, Property 13

    **Validates: Requirements 7.3, 7.4, 7.5, 7.6, 7.14**

    Toda jugada devuelta es de otro equipo, tiene el mismo down, no es la
    solicitada y cumple los criterios que siguen activos tras la relajación.
    """
    from backend.routers.similares import buscar_similares

    total = {"con_resultados": 0, "relajadas": 0}

    def prueba(rng):
        jugadas = generar_jugadas(rng, n=rng.randint(20, 80))
        estado = generadores.estado_datos(jugadas)
        efectivas = estado["_efectivas"]
        validas = estado["_plays"][
            estado["_plays"]["down"].isin([1, 2, 3, 4]) & estado["_plays"]["yardsToGo"].notna()
        ]
        if validas.empty:
            return
        fila = validas.iloc[rng.randrange(len(validas))]
        jugada = {
            "gameId": int(fila["gameId"]), "playId": int(fila["playId"]),
            "equipo": fila["possessionTeam"], "rival": fila["defensiveTeam"],
            "down": fila["down"], "yardsToGo": fila["yardsToGo"],
            "formacion": fila["offenseFormation"], "personal": fila["personnelO"],
            "cobertura": fila["pff_passCoverage"],
        }
        misma_cobertura = rng.random() < 0.5

        similares, relajados, info = buscar_similares(jugada, efectivas, misma_cobertura)

        tolerancia = 4 if "yardsToGo" in relajados else 2
        assert info["tolerancia"] == tolerancia
        assert len(similares) <= 20
        if relajados:
            total["relajadas"] += 1
        claves = list(zip(similares["gameId"], similares["playId"]))
        assert len(set(claves)) == len(claves), "hay jugadas repetidas"
        for _, s in similares.iterrows():
            assert s["equipo"] != jugada["equipo"]
            assert s["down"] == jugada["down"]
            assert (int(s["gameId"]), int(s["playId"])) != (jugada["gameId"], jugada["playId"])
            assert abs(s["yardsToGo"] - jugada["yardsToGo"]) <= tolerancia
            if "offenseFormation" not in relajados:
                assert s["formacion"] == jugada["formacion"]
            if "personnelO" not in relajados:
                assert s["personal"] == jugada["personal"]
            if misma_cobertura and "pff_passCoverage" not in relajados:
                assert s["cobertura"] == jugada["cobertura"]
        total["con_resultados"] += len(similares) > 0

    repetir(prueba, n=150, semilla=generadores.SEMILLA)
    assert total["con_resultados"] > 0, "el generador nunca produjo similares"
    assert total["relajadas"] > 0, "nunca se relajó ningún criterio"


def test_propiedad_14_cobertura_nunca_se_relaja():
    """Feature: failed-plays-coach-app, Property 14

    **Validates: Requirements 7.7**

    Con `misma_cobertura=true` y cobertura no nula, toda similar tiene la misma
    cobertura y `pff_passCoverage` nunca aparece en `criteriosRelajados`.
    """
    from backend.routers.similares import buscar_similares

    total = {"verificadas": 0, "con_resultados": 0}

    def prueba(rng):
        jugadas = generar_jugadas(rng, n=rng.randint(20, 80))
        estado = generadores.estado_datos(jugadas)
        efectivas = estado["_efectivas"]
        plays = estado["_plays"]
        validas = plays[
            plays["down"].isin([1, 2, 3, 4])
            & plays["yardsToGo"].notna()
            & plays["pff_passCoverage"].notna()
        ]
        if validas.empty:
            return
        fila = validas.iloc[rng.randrange(len(validas))]
        jugada = {
            "gameId": int(fila["gameId"]), "playId": int(fila["playId"]),
            "equipo": fila["possessionTeam"], "rival": fila["defensiveTeam"],
            "down": fila["down"], "yardsToGo": fila["yardsToGo"],
            "formacion": fila["offenseFormation"], "personal": fila["personnelO"],
            "cobertura": fila["pff_passCoverage"],
        }

        similares, relajados, _ = buscar_similares(jugada, efectivas, True)

        assert "pff_passCoverage" not in relajados
        assert (similares["cobertura"] == jugada["cobertura"]).all()
        total["verificadas"] += 1
        total["con_resultados"] += len(similares) > 0

    repetir(prueba, n=150, semilla=generadores.SEMILLA)
    assert total["verificadas"] >= 100, "pocas iteraciones con cobertura no nula"
    assert total["con_resultados"] > 0, "el generador nunca produjo similares"


def test_propiedad_15_relajacion_orden_fijo_y_se_detiene():
    """Feature: failed-plays-coach-app, Property 15

    **Validates: Requirements 7.8, 7.9**

    Los pasos de relajación aplicados son un prefijo del orden personnelO,
    yardsToGo, offenseFormation (omitiendo los ya descartados por valor nulo),
    ningún paso se aplica si ya había 5 coincidencias, y los criterios nulos
    de la jugada solicitada siempre se listan.
    """
    from backend.routers.similares import buscar_similares

    orden = ["personnelO", "yardsToGo", "offenseFormation"]
    permitidos = set(orden) | {"pff_passCoverage"}
    total = {"verificadas": 0, "con_pasos": 0, "con_nulos": 0, "detenidas": 0}

    def contar(efectivas, jugada, misma_cobertura, usa_personal, tol, usa_formacion):
        """Referencia independiente: cuenta coincidencias fila por fila."""
        n = 0
        for _, e in efectivas.iterrows():
            if e["equipo"] == jugada["equipo"] or e["down"] != jugada["down"]:
                continue
            if abs(e["yardsToGo"] - jugada["yardsToGo"]) > tol:
                continue
            if usa_formacion and e["formacion"] != jugada["formacion"]:
                continue
            if usa_personal and e["personal"] != jugada["personal"]:
                continue
            if misma_cobertura and not pd.isna(jugada["cobertura"]) and e["cobertura"] != jugada["cobertura"]:
                continue
            n += 1
        return n

    def prueba(rng):
        jugadas = generar_jugadas(rng, n=rng.randint(500, 3000))
        estado = generadores.estado_datos(jugadas)
        efectivas = estado["_efectivas"]
        plays = estado["_plays"]
        validas = plays[plays["down"].isin([1, 2, 3, 4]) & plays["yardsToGo"].notna()]
        if validas.empty:
            return
        fila = validas.iloc[rng.randrange(len(validas))]
        jugada = {
            "gameId": int(fila["gameId"]), "playId": int(fila["playId"]),
            "equipo": fila["possessionTeam"], "rival": fila["defensiveTeam"],
            "down": fila["down"], "yardsToGo": fila["yardsToGo"],
            "formacion": fila["offenseFormation"], "personal": fila["personnelO"],
            "cobertura": fila["pff_passCoverage"],
        }
        misma_cobertura = rng.random() < 0.5

        similares, relajados, info = buscar_similares(jugada, efectivas, misma_cobertura)

        assert set(relajados) <= permitidos
        assert len(set(relajados)) == len(relajados), "identificador repetido"

        # Descartes iniciales por valor nulo (7.8).
        nulo_formacion = pd.isna(jugada["formacion"])
        nulo_personal = pd.isna(jugada["personal"])
        if nulo_formacion:
            assert "offenseFormation" in relajados
        if nulo_personal:
            assert "personnelO" in relajados
        if misma_cobertura and pd.isna(jugada["cobertura"]):
            assert "pff_passCoverage" in relajados
        if not misma_cobertura:
            assert "pff_passCoverage" not in relajados
        total["con_nulos"] += bool(nulo_formacion or nulo_personal)

        # Pasos aplicados = prefijo del orden sin los ya descartados por nulo.
        saltados = {"personnelO"} if nulo_personal else set()
        if nulo_formacion:
            saltados.add("offenseFormation")
        efectivo = [p for p in orden if p not in saltados]
        aplicados = [r for r in relajados if r in orden and r not in saltados]
        assert aplicados == efectivo[: len(aplicados)], f"orden inválido: {relajados}"
        total["con_pasos"] += bool(aplicados)

        # Estado antes de cada paso: debía haber menos de 5 coincidencias.
        usa_personal, usa_formacion, tol = not nulo_personal, not nulo_formacion, 2
        for paso in aplicados:
            antes = contar(efectivas, jugada, misma_cobertura, usa_personal, tol, usa_formacion)
            assert antes < 5, f"se aplicó {paso} con {antes} coincidencias"
            if paso == "personnelO":
                usa_personal = False
            elif paso == "yardsToGo":
                tol = 4
            else:
                usa_formacion = False
        assert info["tolerancia"] == tol

        # Parada: o hay 5 o más coincidencias, o se agotaron los pasos.
        final = contar(efectivas, jugada, misma_cobertura, usa_personal, tol, usa_formacion)
        if len(aplicados) < len(efectivo):
            assert final >= 5, "se detuvo con menos de 5 coincidencias y pasos pendientes"
            total["detenidas"] += 1
        assert len(similares) == min(final, 20)
        total["verificadas"] += 1

    repetir(prueba, n=150, semilla=generadores.SEMILLA)
    assert total["verificadas"] >= 100, "pocas iteraciones verificadas"
    assert total["con_pasos"] > 0, "nunca se relajó ningún criterio"
    assert total["detenidas"] > 0, "nunca se detuvo antes de agotar los pasos"


def test_propiedad_16_lista_similares_limitada_y_ordenada():
    """Feature: failed-plays-coach-app, Property 16

    **Validates: Requirements 7.2, 7.10, 7.11**

    `similares` tiene como máximo 20 elementos con los nueve campos y son las
    primeras 20 de todas las coincidencias ordenadas por playResult descendente,
    gameId ascendente y playId ascendente.
    """
    from backend.routers.similares import _a_dicts, buscar_similares

    campos = {"gameId", "playId", "equipo", "rival", "yardsToGo", "playResult",
              "formacion", "personal", "cobertura"}
    total = {"verificadas": 0, "truncadas": 0}

    def prueba(rng):
        jugadas = generar_jugadas(rng, n=rng.randint(500, 3000))
        estado = generadores.estado_datos(jugadas)
        efectivas = estado["_efectivas"]
        plays = estado["_plays"]
        validas = plays[plays["down"].isin([1, 2, 3, 4]) & plays["yardsToGo"].notna()]
        if validas.empty:
            return
        fila = validas.iloc[rng.randrange(len(validas))]
        jugada = {
            "gameId": int(fila["gameId"]), "playId": int(fila["playId"]),
            "equipo": fila["possessionTeam"], "rival": fila["defensiveTeam"],
            "down": fila["down"], "yardsToGo": fila["yardsToGo"],
            "formacion": fila["offenseFormation"], "personal": fila["personnelO"],
            "cobertura": fila["pff_passCoverage"],
        }
        misma_cobertura = rng.random() < 0.5

        similares, relajados, info = buscar_similares(jugada, efectivas, misma_cobertura)

        # Referencia independiente: todas las coincidencias con los criterios finales.
        coincidencias = []
        for _, e in efectivas.iterrows():
            if e["equipo"] == jugada["equipo"] or e["down"] != jugada["down"]:
                continue
            if abs(e["yardsToGo"] - jugada["yardsToGo"]) > info["tolerancia"]:
                continue
            if "offenseFormation" not in relajados and e["formacion"] != jugada["formacion"]:
                continue
            if "personnelO" not in relajados and e["personal"] != jugada["personal"]:
                continue
            if misma_cobertura and "pff_passCoverage" not in relajados \
                    and e["cobertura"] != jugada["cobertura"]:
                continue
            coincidencias.append((-float(e["playResult"]), int(e["gameId"]), int(e["playId"])))
        esperadas = sorted(coincidencias)[:20]

        assert len(similares) <= 20
        obtenidas = [
            (-float(s["playResult"]), int(s["gameId"]), int(s["playId"]))
            for _, s in similares.iterrows()
        ]
        assert obtenidas == esperadas, "no son las primeras 20 en el orden requerido"
        assert obtenidas == sorted(obtenidas), "orden inválido"
        for d in _a_dicts(similares):
            assert set(d) == campos
        total["verificadas"] += 1
        total["truncadas"] += len(coincidencias) > 20

    repetir(prueba, n=150, semilla=generadores.SEMILLA)
    assert total["verificadas"] >= 100, "pocas iteraciones verificadas"
    assert total["truncadas"] > 0, "nunca hubo más de 20 coincidencias"
