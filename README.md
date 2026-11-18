# Failed Plays Coach App

Aplicación web para entrenadores, construida con los datos del NFL Big Data Bowl (temporada 2021, semanas 1 a 8, solo jugadas de pase). El entrenador elige un down, una razón de falla y un equipo, revisa las jugadas ofensivas fallidas, reproduce una en 2D y recibe recomendaciones basadas en jugadas efectivas de otros equipos en situaciones similares.


> **Estado:** en construcción. Hoy el repositorio contiene el esqueleto de la plantilla (`GET /health` y un dashboard base). Las funciones descritas abajo son el alcance planeado.

## Qué hace

1. **Filtros.** Selecciona down (1 a 4), razón de falla y equipo ofensivo.
2. **Jugadas fallidas.** Lista las jugadas que cumplen los filtros, con situación, formación, personal y cobertura.
3. **Repetición 2D.** Dibuja la cancha en SVG y anima a los 22 jugadores y el balón a 10 cuadros por segundo, con línea de tiempo y marcas de eventos (Snap, Pase, Resultado).
4. **Jugadas similares.** Busca jugadas efectivas de otros equipos con el mismo down, distancia parecida, misma formación y mismo personal. Si hay menos de 5, relaja los criterios y lo informa.
5. **Comparación de formaciones y rutas.** Con los datos de PFF compara alineaciones y rutas de la jugada fallida contra las de las jugadas efectivas.
6. **Sugerencias con confianza.** Cada sugerencia indica su evidencia, el tamaño de muestra y una etiqueta de confianza.

Todos los textos de la interfaz están en español.

### Razones de falla

| Razón | Regla |
|---|---|
| `intercepcion` | `passResult = IN` |
| `sack` | `passResult = S` |
| `incompleto` | `passResult = I` |
| `perdida_de_yardas` | `playResult < 0` |
| `sin_conversion` | down 3 o 4 y `playResult < yardsToGo` |

Si aplican varias reglas, gana la primera en este orden: intercepción, sack, incompleto, pérdida de yardas, sin conversión. Las jugadas con `down = 0` se excluyen.

### Jugada efectiva

Es una jugada que no falló, con pase completo (`passResult = C`) y que avanzó al menos:

- 40 % de `yardsToGo` en down 1.
- 60 % de `yardsToGo` en down 2.
- 100 % de `yardsToGo` en down 3 o 4.

### Confianza de las sugerencias

| Muestra (`nMuestra`) | Etiqueta |
|---|---|
| menos de 5 | `baja` (se muestra "Muestra pequeña") |
| de 5 a 14 | `media` |
| 15 o más | `alta` |

## Datos

Los datos están en `data/` y son de solo lectura.

| Archivo | Contenido |
|---|---|
| `games.csv` | 122 partidos, 32 equipos |
| `players.csv` | 1,679 jugadores (posición, estatura, peso, universidad) |
| `plays.csv` | 8,557 jugadas de pase con situación, formación, cobertura y resultado |
| `pffScoutingData.csv` | Rol y alineación de cada jugador en cada jugada (PFF) |
| `tracking/tracking_<gameId>.csv` | Posición, velocidad y orientación por cuadro, a 10 cuadros por segundo |

El tracking pesa cerca de 800 MB. El backend lee solo el archivo del partido que se pide. Antes de comparar jugadas se normaliza la dirección para que la ofensiva avance siempre hacia `x` creciente.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI 0.115.14, Uvicorn 0.34.3, Pydantic 2.11.7 |
| Datos | pandas 2.2.3, numpy 2.1.3 |
| Frontend | React 18.3.1, Vite 5.4.21, TypeScript 5.7.3, Tailwind CSS 3.4.19, Recharts 3.10.1 |


No se usan otras dependencias ni Docker. Las reglas completas están en `.kiro/steering/rules.md`.

## Estructura

```
backend/        API en FastAPI (main.py expone app y GET /health)
dashboard/      Frontend en React; el build genera dashboard/dist
data/           Datos del Big Data Bowl (solo lectura)
.hackathon/     Herramientas de la plantilla
.kiro/          Reglas del proyecto
```

La API vive bajo `/api/...`. El servidor entrega el build del dashboard y la API en la misma URL y puerto. El dashboard llama a la API con rutas relativas sin diagonal inicial, por ejemplo `fetch('api/filtros')`, porque se publica en una subruta.

### Endpoints planeados

| Método y ruta | Descripción |
|---|---|
| `GET /health` | Estado del servicio |
| `GET /api/filtros` | Downs, razones y equipos disponibles |
| `GET /api/jugadas` | Jugadas fallidas filtradas por `down`, `razon` y `equipo` |
| `GET /api/jugadas/{gameId}/{playId}/tracking` | Tracking normalizado de una jugada |
| `GET /api/jugadas/{gameId}/{playId}/similares` | Jugadas efectivas similares y sugerencias |
| `POST /api/recomendacion` | Recomendación en texto, con IA o con plantilla |

## Cómo ejecutar

Requisitos: Python 3.12 en `.venv` y Node 22.

Verificar el entorno:

```powershell
.\.hackathon\setup.cmd --check
```

Desarrollo, en dos terminales:

```powershell
# Backend (puerto 8000)
.venv\Scripts\uvicorn backend.main:app --reload

# Frontend (Vite, con proxy de /api hacia el puerto 8000)
cd dashboard
npm install
npm run dev
```

Build del frontend:

```powershell
cd dashboard
npm run build
```

## Reparto del trabajo

| Persona A | Persona B |
|---|---|
| `backend/datos.py` | `backend/tracking.py` |
| `backend/routers/jugadas.py` | `backend/routers/repeticion.py` |
| `backend/routers/similares.py` | `backend/routers/ia.py` |
| Componentes `Filtros/`, `ListaJugadas/`, `Similares/` | Componentes `Repeticion/`, `Recomendacion/` |

Los archivos compartidos (`backend/main.py`, `dashboard/src/App.tsx`, `dashboard/src/api/tipos.ts`, `dashboard/vite.config.ts`) se crean una sola vez en el paso 0 y después se cambian de común acuerdo.

## Entrega

```powershell
.\.hackathon\setup.cmd --entregar
```

Antes de entregar, `--check` debe pasar sin errores.
