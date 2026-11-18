"""Feature: failed-plays-coach-app, Property 32: Personnel round trip.

**Validates: Requirements 12.9, 12.10**
"""
from backend.datos import formatear_personal, parsear_personal
from backend.tests.generadores import generar_personal_invalido, generar_personal_valido, repetir

GRUPOS = ["RB", "TE", "WR", "QB", "OL", "DL", "LB", "DB"]


def test_personal_ida_y_vuelta():
    # Feature: failed-plays-coach-app, Property 32
    def prueba(rng):
        grupos = rng.sample(GRUPOS, k=rng.randint(1, len(GRUPOS)))
        conteos = {g: rng.randint(0, 9) for g in grupos}
        texto = formatear_personal(conteos)
        assert parsear_personal(texto) == conteos
        assert formatear_personal(parsear_personal(texto)) == texto

        valido = generar_personal_valido(rng)
        parseado = parsear_personal(valido)
        assert parseado is not None
        assert parsear_personal(formatear_personal(parseado)) == parseado

    repetir(prueba, n=100)


def test_personal_invalido_devuelve_none():
    # Feature: failed-plays-coach-app, Property 32
    def prueba(rng):
        assert parsear_personal(generar_personal_invalido(rng)) is None

    repetir(prueba, n=100)
