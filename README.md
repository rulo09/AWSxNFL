# Failed Plays Coach App

Aplicación web para entrenadores, construida con los datos del NFL Big Data Bowl (temporada 2021, semanas 1 a 8, solo jugadas de pase). El entrenador elige un down, una razón de falla y un equipo, revisa las jugadas ofensivas fallidas, reproduce una en 2D y recibe recomendaciones basadas en jugadas efectivas de otros equipos en situaciones similares.

## Pregunta

**¿Qué hicieron otros equipos, en situaciones comparables, en las jugadas de pase que sí funcionaron, y que un equipo no hizo en las jugadas de pase que le fallaron?**

Concretamente, para cada jugada fallida de un equipo:

1. ¿Por qué falló (intercepción, sack, incompleto, pérdida de yardas o sin conversión)?
2. ¿Qué formación, personal, cobertura rival y alineación de receptores usaron otros equipos cuando la misma situación (mismo down, distancia parecida) terminó en una jugada efectiva?
3. ¿Qué tan confiable es esa comparación, según cuántas jugadas la respaldan?

El usuario es un entrenador ofensivo. La salida es una lista corta de sugerencias, cada una con su evidencia y su tamaño de muestra, no una predicción.

## Datos

Los datos están en `data/` y son de solo lectura. Cubren la temporada 2021, semanas 1 a 8, y solo incluyen jugadas de pase.

| Archivo | Contenido | Para qué se usa |
|---|---|---|
| `games.csv` | 122 partidos, 32 equipos | Validar que cada jugada pertenece a un partido |
| `players.csv` | 1,679 jugadores (posición, estatura, peso, universidad) | Obtener `officialPosition` de cada jugador |
| `plays.csv` | 8,557 jugadas de pase con situación, formación, cobertura y resultado | Clasificar fallas, buscar jugadas similares |
| `pffScoutingData.csv` | Rol y alineación de cada jugador en cada jugada (PFF) | Comparar alineaciones y rutas |
| `tracking/tracking_<gameId>.csv` | Posición, velocidad y orientación por cuadro, a 10 cuadros por segundo | Repetición 2D |

Columnas principales de `plays.csv`: `down`, `yardsToGo`, `passResult`, `playResult`, `possessionTeam`, `offenseFormation`, `personnelO`, `pff_passCoverage`.

Resultado de la clasificación sobre los datos reales: 4,028 jugadas fallidas y 3,646 jugadas efectivas.

### Limitaciones de los datos

- Solo hay jugadas de pase. Por eso "corredores" se refiere a RB y receptores en ruta, no a jugadas terrestres.
- Son 8 semanas de una temporada, así que algunas combinaciones de situación, formación y personal tienen pocas jugadas.
- `formacion`, `personal` y `cobertura` pueden venir vacíos. En ese caso el criterio se omite y se informa.
- Hay 35 jugadas con `down = 0`. Se excluyen.
- El tracking pesa cerca de 800 MB. El backend lee solo el archivo del partido que se pide.

## Método

### 1. Clasificar las fallas

| Razón | Regla |
|---|---|
| `intercepcion` | `passResult = IN` |
| `sack` | `passResult = S` |
| `incompleto` | `passResult = I` |
| `perdida_de_yardas` | `playResult < 0` |
| `sin_conversion` | down 3 o 4 y `playResult < yardsToGo` |

Si aplican varias reglas, gana la primera en este orden: intercepción, sack, incompleto, pérdida de yardas, sin conversión. Las jugadas con `down = 0` y las filas con valores inválidos no reciben razón. La clasificación es determinista y no depende del orden de las filas.

### 2. Definir qué es una jugada efectiva

Es una jugada que no falló, con pase completo (`passResult = C`) y que avanzó al menos:

- 40 % de `yardsToGo` en down 1.
- 60 % de `yardsToGo` en down 2.
- 100 % de `yardsToGo` en down 3 o 4.

### 3. Buscar jugadas similares

Para una jugada fallida se buscan jugadas efectivas de **otros equipos** con:

1. El mismo down.
2. `yardsToGo` dentro de ±2 yardas.
3. La misma formación ofensiva.
4. El mismo personal ofensivo.
5. Opcionalmente, la misma cobertura rival (este criterio nunca se relaja).

Si hay menos de 5 coincidencias, se relajan los criterios en este orden: personal, distancia (±4 yardas) y formación. Se detiene en cuanto hay 5 o más. Los criterios relajados se muestran al usuario. Se devuelven como máximo 20 jugadas, ordenadas por yardas ganadas.

### 4. Comparar formaciones y rutas

Con las jugadas similares se calcula:

- La distribución (en %) de formación, personal y cobertura, siempre con el tamaño de muestra.
- Las 10 alineaciones de corredores de ruta (WR, TE, RB, FB) más frecuentes, con los datos de PFF.
- La tasa de éxito y las yardas promedio por formación, sobre un grupo más amplio: otros equipos, mismo down y distancia dentro de la tolerancia aplicada.

### 5. Generar sugerencias y medir su confianza

Se generan hasta 5 sugerencias con plantillas fijas en español (formación, personal, cobertura rival, alineación y ganancia promedio por formación). Se ordenan por tamaño de muestra. Las mismas entradas siempre producen las mismas sugerencias.

| Muestra (`nMuestra`) | Etiqueta |
|---|---|
| menos de 5 | `baja` (se muestra "Muestra pequeña") |
| de 5 a 14 | `media` |
| 15 o más | `alta` |

### 6. Recomendación en texto con IA (opcional)

`POST /api/recomendacion` recibe la jugada fallida y las sugerencias ya calculadas, y pide a un modelo de lenguaje en Amazon Bedrock (Nova Pro, con Strands Agents) que las redacte como una recomendación breve para el entrenador.

- **Solo usa lo que recibe.** El prompt contiene únicamente la jugada y las sugerencias. Se le indica responder en español, en un máximo de 1,500 caracteres, citar el `nMuestra` de cada sugerencia y no inventar cifras.
- **Siempre hay respuesta.** Si la IA falla, devuelve texto vacío, no hay credenciales o tarda más de 20 segundos, el backend responde con un resumen fijo armado con plantilla y marca `generado_por_ia = false`. La interfaz muestra "Generado con IA" o "Resumen automático (IA no disponible)" según corresponda.
- **La IA no sostiene el análisis.** Filtros, jugadas, repetición, similares y sugerencias se calculan sin IA. Si la IA no está disponible, solo cambia el texto de la recomendación.
- **Validación.** Un cuerpo inválido, o con más de 20 sugerencias, se rechaza con error 422 antes de llamar al modelo.
- **Costo y control.** La llamada ocurre solo cuando el entrenador pulsa "Generar recomendación", una vez por clic.

### 7. Repetición 2D

El tracking de la jugada se normaliza para que la ofensiva avance siempre hacia `x` creciente (si `playDirection = left`, `x' = 120 - x` y `y' = 53.3 - y`). Las coordenadas de los jugadores se limitan al campo (0 a 120 y 0 a 53.3). Se anima a 10 cuadros por segundo, con línea de tiempo y marcas de Snap, Pase y Resultado.

### Qué no hace este método

- No predice la probabilidad de éxito de una jugada ni establece causalidad. Muestra qué se hizo en situaciones comparables.
- No considera la calidad de los jugadores, el clima ni el marcador.
- Con muestras pequeñas, la sugerencia se marca como `baja` y debe leerse como una pista, no como una conclusión.

## Qué hace la aplicación

1. **Filtros.** Down (1 a 4), razón de falla y equipo ofensivo.
2. **Jugadas fallidas.** Lista con situación, formación, personal y cobertura.
3. **Repetición 2D.** Cancha en SVG con los 22 jugadores y el balón.
4. **Jugadas similares.** Tabla, criterios relajados y comparación con gráfica.
5. **Sugerencias con confianza.** Evidencia, muestra y etiqueta.
6. **Recomendación.** Texto con IA o con plantilla.

Todos los textos de la interfaz están en español.

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
.kiro/          Reglas del proyecto y especificación
```

La API vive bajo `/api/...`. El servidor entrega el build del dashboard y la API en la misma URL y puerto. El dashboard llama a la API con rutas relativas sin diagonal inicial, por ejemplo `fetch('api/filtros')`, porque se publica en una subruta.

### Endpoints

| Método y ruta | Descripción |
|---|---|
| `GET /health` | Estado del servicio |
| `GET /api/filtros` | Downs, razones y equipos disponibles |
| `GET /api/jugadas` | Jugadas fallidas filtradas por `down`, `razon` y `equipo` |
| `GET /api/jugadas/{gameId}/{playId}/tracking` | Tracking normalizado de una jugada |
| `GET /api/jugadas/{gameId}/{playId}/similares` | Jugadas efectivas similares, comparación y sugerencias |
| `POST /api/recomendacion` | Recomendación en texto, con IA o con plantilla |

## Cómo ejecutar

Requisitos: Python 3.12 en `.venv` y Node 22.

Verificar el entorno:

```sh
sh .hackathon/setup.sh --check
```

(En Windows: `.\.hackathon\setup.cmd --check`.)

Un solo puerto, con el build del dashboard:

```sh
cd dashboard && npm install && npm run build && cd ..
.venv/bin/uvicorn backend.main:app --port 8000
```

Abrir http://localhost:8000. En Windows usa `.venv\Scripts\uvicorn`.

Desarrollo, en dos terminales:

```sh
# Backend (puerto 8000)
.venv/bin/uvicorn backend.main:app --reload

# Frontend (Vite, con proxy de /api hacia el puerto 8000)
cd dashboard
npm run dev
```

Pruebas:

```sh
.venv/bin/python -m pytest backend/tests -q
```

#### Activar la IA

1. Copia `.env.example` como `.env` en la raíz del proyecto.
2. Pega las llaves temporales del workshop: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `AWS_SESSION_TOKEN`. Valen unas horas.
3. Opcional: `AWS_REGION` (por defecto `us-east-1`) y `BEDROCK_MODEL_ID` (por defecto `us.amazon.nova-pro-v1:0`).
4. Reinicia el backend, porque `.env` se lee al arrancar.

`.env` no se versiona ni se incluye en el .zip de entrega, y las llaves nunca van en el código ni en este README. En AWS las credenciales vienen del rol y no se usan llaves. Sin credenciales, o con llaves vencidas, la aplicación usa el resumen con plantilla.

## Reparto del trabajo

| Persona A | Persona B |
|---|---|
| `backend/datos.py` | `backend/tracking.py` |
| `backend/routers/jugadas.py` | `backend/routers/repeticion.py` |
| `backend/routers/similares.py` | `backend/routers/ia.py` |
| Componentes `Filtros/`, `ListaJugadas/`, `Similares/` | Componentes `Repeticion/`, `Recomendacion/` |

Los archivos compartidos (`backend/main.py`, `dashboard/src/App.tsx`, `dashboard/src/api/tipos.ts`, `dashboard/vite.config.ts`) se crearon en el paso 0 y después se cambian de común acuerdo.

## Entrega

```sh
sh .hackathon/setup.sh --entregar
```

Antes de entregar, `--check` debe pasar sin errores.
