"""Escanea dashboard/src/ y falla con rutas absolutas o hosts fijos.

**Validates: Requirements 1.5, 1.6**
"""
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent / "dashboard" / "src"
EXTENSIONES = {".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
PROHIBIDOS = ["fetch('/", 'fetch("/', "fetch(`/", "localhost", "127.0.0.1", "http://", "https://"]


def _archivos():
    return [p for p in SRC.rglob("*") if p.is_file() and p.suffix in EXTENSIONES]


def test_src_existe_y_tiene_archivos():
    assert SRC.is_dir()
    assert _archivos()


def test_sin_rutas_absolutas_ni_hosts():
    errores = []
    for p in _archivos():
        texto = p.read_text(encoding="utf-8", errors="replace")
        for n, linea in enumerate(texto.splitlines(), 1):
            for patron in PROHIBIDOS:
                if patron in linea:
                    errores.append(f"{p.relative_to(SRC)}:{n}: {patron}")
    assert not errores, "Rutas prohibidas en dashboard/src/:\n" + "\n".join(errores)
