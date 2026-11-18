# Implementation Plan: Failed Plays Coach App

## Overview

The plan follows the work split in the requirements (Requirement 13) and the design. Step 0 creates the shared skeleton once. Then Person A and Person B work in parallel in their own files. The plan ends with integration and final verification.

Every task carries an owner label: **Persona A**, **Persona B** or **Compartido** (shared files, created once in step 0 or edited once by one person during integration).

Rules applied to every task (`.kiro/steering/rules.md`):

- Python 3.12 and TypeScript only, inside the fixed stack. No new Python or npm dependency and no version change. Property tests use plain pytest with seeded generators (`hypothesis` is not in the stack).
- The Dashboard calls the API with `fetch('api/<ruta>')`, never with a leading slash. No `localhost`, `127.0.0.1` or absolute URLs in `dashboard/src/`.
- `data/` is read-only. The app writes nothing to disk. All user-facing texts are in Spanish.
- Tailwind 3 syntax only.
- No git or branch tasks (Requirement 13.7).

## Tasks

- [x] 1. Step 0: shared skeleton (Compartido)
  - [x] 1.1 Create `backend/modelos.py` with the Pydantic models (Compartido)
    - Define `Jugada`, `Evento`, `JugadorFrame`, `Balon`, `Cuadro`, `Tracking`, `JugadaSimilar`, `Sugerencia`, `Comparacion`, `Similares`, `SolicitudRecomendacion` (`sugerencias` with `max_length=20`) and `Recomendacion`, with the field names and types from the design.
    - Nullable fields (`formacion`, `personal`, `cobertura`, `balon`) are `X | None`.
    - _Requirements: 1.8, 12.1_

  - [x] 1.2 Create `dashboard/src/api/tipos.ts` (Compartido)
    - Define `Jugada`, `Tracking` (with `Evento`, `Cuadro`, `JugadorFrame`, `Balon`), `Similares` (with `JugadaSimilar`, `Sugerencia`, `Comparacion`), `Filtros` and `Recomendacion`, with the same field names and types as `modelos.py`.
    - Add the runtime type guards `esJugada`, `esTracking`, `esSimilares` (and `esRecomendacion`).
    - _Requirements: 1.8, 12.2, 12.3_

  - [x] 1.3 Create the shared test helpers `backend/tests/generadores.py` and `backend/tests/conftest.py` (Compartido)
    - `generadores.py`: the `repetir(prueba, n=100, semilla=2023)` loop helper and seeded generators for plays tables (include `down` 0, NaN, `passResult` `R` and missing, null `formacion`/`personal`/`cobertura`, tied `playResult`), scouting rows, tracking frames and personnel texts.
    - `conftest.py`: a `TestClient` fixture, a fixture that replaces the `datos` module state with a generated table, and a `monkeypatch` stub for `boto3`/`strands` so no test needs credentials or calls Bedrock.
    - Create `backend/tests/__init__.py` if the layout needs it.
    - _Requirements: 13.1_

  - [x] 1.4 Create the backend stubs with frozen signatures (Compartido)
    - `backend/datos.py`: the public functions from the design (`cargar`, `clasificar_fallas`, `parsear_personal`, `formatear_personal`, `obtener_jugada`, `jugadas_fallidas`, `jugadas_efectivas`, `todas_las_jugadas`, `alineaciones`) with docstrings. `obtener_jugada` returns `None` until Person A implements it.
    - `backend/tracking.py`: `leer_tracking`, `normalizar`, `a_modelo` stubs with docstrings.
    - `backend/routers/__init__.py` and the four routers `jugadas.py`, `similares.py`, `repeticion.py`, `ia.py`, each with an empty `APIRouter(prefix="/api")`.
    - _Requirements: 1.3, 1.4, 13.1_

  - [x] 1.5 Create `dashboard/src/api/cliente.ts` (Compartido)
    - Implement `obtener<T>(ruta, { señal, timeoutMs, validar })` calling `fetch('api/' + ruta)` (no leading slash).
    - Abort after `timeoutMs`, reject on non-2xx, parse JSON and apply the optional type guard `validar`, rejecting with a Spanish "no se pudieron leer los datos" error when it fails.
    - Add a `publicar` helper for `POST api/recomendacion` with a timeout.
    - _Requirements: 1.5, 1.6, 12.3_

  - [x] 1.6 Create `backend/main.py` (Compartido)
    - Define and call `cargar_env()` (exact code from the rules) before any import that uses boto3.
    - `lifespan` handler that calls `datos.cargar()` and aborts startup naming the missing file.
    - Register the four routers, `GET /health` returning `{"status": "ok"}`, and the shared `RequestValidationError` handler (Spanish message naming the field) and the generic exception handler (Spanish JSON, no stack trace or paths).
    - Mount `dashboard/dist` with `StaticFiles(html=True)` at `/` last, only if the directory exists.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.13, 11.3, 11.4, 11.6, 11.7_

  - [x] 1.7 Create `dashboard/vite.config.ts` settings, `App.tsx` and the empty component folders (Compartido)
    - `vite.config.ts`: keep `base: './'` and add the proxy `/api` to `http://localhost:8000`.
    - Create `Filtros/`, `ListaJugadas/`, `Similares/`, `Repeticion/`, `Recomendacion/` under `dashboard/src/components/`, each with an `index.tsx` placeholder that exports a default component with the props from the design.
    - `App.tsx`: own `filtros` and `seleccion` state, hold the `sugerencias` handed from `Similares/` to `Recomendacion/`, and lay out the five panels. Components do not import each other.
    - _Requirements: 1.5, 1.7, 1.12, 4.11, 11.8_

  - [x] 1.8 Write smoke tests for the skeleton (Compartido)
    - `GET /health` returns `{"status": "ok"}`; every route except `/health` starts with `/api/`; the four routers are registered.
    - _Requirements: 1.1, 1.3, 1.4_

- [x] 2. Checkpoint - Skeleton complete
  - Ensure all tests pass, ask the user if questions arise. Both people start their own track only after this checkpoint.

- [x] 3. Person A track: data loading and failure classification
  - [x] 3.1 Implement `backend/datos.py` (Persona A)
    - `EQUIPOS` (32 abbreviations including `LA`, `LAC`, `LV`, `WAS`), `cargar()` loading `games.csv`, `plays.csv`, `players.csv` and `pffScoutingData.csv` once, raising `RuntimeError("No se encontró el archivo <nombre>")` when one is missing.
    - `clasificar_fallas` with `numpy.select` and the precedence `intercepcion`, `sack`, `incompleto`, `perdida_de_yardas`, `sin_conversion`; numeric coercion, `down` 0 and invalid rows without reason; `descripcion` in Spanish of at most 200 characters with `down`, `yardsToGo` and the `razon` code.
    - `parsear_personal` and `formatear_personal`; invalid text gives `None` and keeps the original `personal`.
    - Build `_plays`, `_fallidas` (sorted by `gameId`, `playId`, with renamed columns), `_efectivas` (thresholds 0.4, 0.6, 1.0, 1.0), `_pff` (joined with `players.officialPosition`) and `_equipos_con_fallas`.
    - `a_jugada(row)` helper that maps NaN, `pd.NA` and `None` to `None` and numpy integers to `int`; implement `obtener_jugada` (returns a dict with at least `equipo`, or `None`), `jugadas_fallidas`, `jugadas_efectivas`, `todas_las_jugadas`, `alineaciones`.
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 7.1, 11.2, 11.4, 12.4, 12.9, 12.10_

  - [x] 3.2 Write property test for the failure classifier against the reference rules (Persona A)
    - File `backend/tests/test_clasificador.py`. **Property 1: Failure classification matches the reference rules**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9**

  - [x] 3.3 Write property test for the failure description (Persona A)
    - File `backend/tests/test_clasificador.py`. **Property 2: Failure description content**
    - **Validates: Requirements 2.8**

  - [x] 3.4 Write property test for idempotence and row order independence (Persona A)
    - File `backend/tests/test_clasificador.py`. **Property 3: Classification is idempotent and independent of row order**
    - **Validates: Requirements 2.10, 2.11**

  - [x] 3.5 Write property test for invalid rows (Persona A)
    - File `backend/tests/test_clasificador.py`. **Property 4: Invalid rows are skipped without affecting others**
    - **Validates: Requirements 2.12**

  - [x] 3.6 Write property test for the personnel round trip (Persona A)
    - File `backend/tests/test_personal.py`. **Property 32: Personnel round trip**
    - **Validates: Requirements 12.9, 12.10**

  - [x] 3.7 Write example tests with the real CSV files (Persona A)
    - File `backend/tests/test_datos_real.py`. Check the 35 rows with `down` 0 and none is a Failed_Play, the five `razon` values appear, `passResult` values are `C, I, S, R, IN`, `cargar()` on a temporary folder without `plays.csv` names `plays.csv`, and startup loading takes under 30 s.
    - _Requirements: 2.1, 8.2, 11.3, 11.4_

- [x] 4. Person A track: filters and listing endpoints
  - [x] 4.1 Implement `backend/routers/jugadas.py` (Persona A)
    - `GET /api/filtros`: downs `[1,2,3,4]`, the five reasons, teams sorted by abbreviation without duplicates with `nombre` from `EQUIPOS` or `null`; 500 with the Spanish message when data is not loaded.
    - `GET /api/jugadas?down=&razon=&equipo=`: manual validation with Spanish 422 messages naming the parameter, exact case-sensitive `equipo`, boolean mask over `_fallidas`, `[]` with 200 when nothing matches.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 4.2 Write property test for the team list (Persona A)
    - File `backend/tests/test_jugadas.py`. **Property 5: Team list is the sorted set of teams with failed plays**
    - **Validates: Requirements 3.2, 3.4**

  - [x] 4.3 Write property test for the listing (Persona A)
    - File `backend/tests/test_jugadas.py`. **Property 6: Listing returns exactly the matching plays in a fixed order**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.6, 4.7**

  - [x] 4.4 Write property test for invalid filter values (Persona A)
    - File `backend/tests/test_jugadas.py`. **Property 7: Invalid filter values are rejected**
    - **Validates: Requirements 4.5**

  - [x] 4.5 Write property test for NaN serialization (Persona A)
    - File `backend/tests/test_jugadas.py`. **Property 29: No NaN in JSON output**
    - **Validates: Requirements 12.4**

  - [x] 4.6 Write example tests for filters and listing with real data (Persona A)
    - File `backend/tests/test_jugadas_ejemplos.py`. `GET /api/filtros` in under 2 s with downs `[1,2,3,4]` and teams absent from `EQUIPOS` returning `nombre: null`; `GET /api/jugadas` for an unknown team returns `[]` with 200; worst-case filter combination in under 1 s.
    - _Requirements: 3.1, 3.3, 4.4, 4.8_

- [x] 5. Person A track: similar plays, comparison and suggestions
  - [x] 5.1 Implement similar play selection in `backend/routers/similares.py` (Persona A)
    - `buscar_similares` with the base mask (other team, same `down`), tolerance 2, `formacion` and `personal` criteria, optional `misma_cobertura` (never relaxed), null-value drops, relaxation order `personnelO`, `yardsToGo` (tolerance 4), `offenseFormation` stopping at 5 matches, order by `playResult` desc, `gameId`, `playId` and limit 20.
    - `etiqueta_confianza(n)`; endpoint `GET /api/jugadas/{gameId}/{playId}/similares` with 404 `"Jugada no encontrada."`.
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 7.12, 7.13, 7.14, 9.2_

  - [x] 5.2 Implement `construir_comparacion` in `backend/routers/similares.py` (Persona A)
    - Route data filter (`Pass Route` and `WR`, `TE`, `RB`, `FB`), top 10 alignments (count desc, then `pff_positionLinedUp` asc), `solicitada.alineacion`, `rutasDisponibles`.
    - Distributions with 1 decimal and `nMuestra`, `exitoPorFormacion` over the wider group, `top3` per attribute.
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.8, 8.9_

  - [x] 5.3 Implement `generar_sugerencias` and wire the endpoint response in `backend/routers/similares.py` (Persona A)
    - Five fixed Spanish templates in generation order, discard `nMuestra == 0`, stable sort by `nMuestra` desc, cut to 5, `texto` and `evidencia` of at most 280 characters, `confianza` from `etiqueta_confianza`.
    - Return `{similares, sugerencias, criteriosRelajados, comparacion}`; empty lists with 200 when nothing matches.
    - _Requirements: 7.2, 7.13, 9.1, 9.2, 9.3, 9.4, 9.5, 9.8, 9.9, 9.10_

  - [x] 5.4 Write property test for the effective play rule (Persona A)
    - File `backend/tests/test_similares_criterios.py`. **Property 12: Effective play rule**
    - **Validates: Requirements 7.1**

  - [x] 5.5 Write property test for the active similarity criteria (Persona A)
    - File `backend/tests/test_similares_criterios.py`. **Property 13: Similar plays satisfy the active criteria**
    - **Validates: Requirements 7.3, 7.4, 7.5, 7.6, 7.14**

  - [x] 5.6 Write property test for the coverage criterion (Persona A)
    - File `backend/tests/test_similares_criterios.py`. **Property 14: Coverage criterion is never relaxed**
    - **Validates: Requirements 7.7**

  - [x] 5.7 Write property test for the relaxation order (Persona A)
    - File `backend/tests/test_similares_criterios.py`. **Property 15: Relaxation follows the fixed order and stops when enough plays match**
    - **Validates: Requirements 7.8, 7.9**

  - [x] 5.8 Write property test for the similar list limit and order (Persona A)
    - File `backend/tests/test_similares_criterios.py`. **Property 16: Similar list is limited and ordered**
    - **Validates: Requirements 7.2, 7.10, 7.11**

  - [x] 5.9 Write property test for route data (Persona A)
    - File `backend/tests/test_comparacion.py`. **Property 17: Route data contains only route runners**
    - **Validates: Requirements 8.1, 8.2**

  - [x] 5.10 Write property test for the top alignments (Persona A)
    - File `backend/tests/test_comparacion.py`. **Property 18: Top alignments are the 10 most frequent combinations**
    - **Validates: Requirements 8.3**

  - [x] 5.11 Write property test for distribution percentages (Persona A)
    - File `backend/tests/test_comparacion.py`. **Property 19: Distribution percentages are consistent**
    - **Validates: Requirements 8.4**

  - [x] 5.12 Write property test for success rate and average yards (Persona A)
    - File `backend/tests/test_comparacion.py`. **Property 20: Success rate and average yards**
    - **Validates: Requirements 8.5**

  - [x] 5.13 Write property test for the suggestion format (Persona A)
    - File `backend/tests/test_sugerencias.py`. **Property 21: Suggestion format**
    - **Validates: Requirements 9.1, 9.5**

  - [x] 5.14 Write property test for the confidence label (Persona A)
    - File `backend/tests/test_sugerencias.py`. **Property 22: Confidence label follows the sample size**
    - **Validates: Requirements 9.2, 9.3**

  - [x] 5.15 Write property test for suggestion count and order (Persona A)
    - File `backend/tests/test_sugerencias.py`. **Property 23: Suggestion count and order**
    - **Validates: Requirements 9.4**

  - [x] 5.16 Write property test for the sample bound (Persona A)
    - File `backend/tests/test_sugerencias.py`. **Property 24: Suggestion samples are bounded by the similar plays**
    - **Validates: Requirements 9.9**

  - [x] 5.17 Write property test for determinism (Persona A)
    - File `backend/tests/test_sugerencias.py`. **Property 25: Suggestions are deterministic**
    - **Validates: Requirements 9.10**

  - [x] 5.18 Write example tests for the similares endpoint (Persona A)
    - File `backend/tests/test_similares_ejemplos.py`. Unknown play gives 404 with the Spanish message; a play with no candidates gives 200 with empty `similares` and `sugerencias`; missing route data sets `rutasDisponibles` to false and keeps the rest of the comparison.
    - _Requirements: 7.12, 7.13, 8.8, 9.8_

  - [x] 5.19 Write property test for the JSON round trip of Jugada and Similares (Persona A)
    - File `backend/tests/test_contrato_a.py`. **Property 30: JSON round trip of the contract models** (Jugada and Similares part, including `null` fields)
    - **Validates: Requirements 12.1, 12.6**

- [x] 6. Person A track: dashboard components
  - [x] 6.1 Implement `Filtros/` (Persona A)
    - Props `{valor, onCambio}`. Load `api/filtros` once with `obtener`, show three Spanish-labeled selects (down, razón, equipo as `nombre (abbr)` or `abbr`). On error show a Spanish message and keep the selects usable with empty options.
    - _Requirements: 1.5, 1.12, 3.1, 3.3, 4.9_

  - [x] 6.2 Implement `ListaJugadas/` (Persona A)
    - Props `{filtros, seleccionada, onSeleccionar}`. Request `api/jugadas?...` on each `filtros` change with a 10 s timeout and the `esJugada` guard, replace the list, show "No hay jugadas fallidas con estos filtros" when empty, mark the selected row with `aria-selected` and a highlight, show "Sin dato" for null `formacion`, `personal`, `cobertura`.
    - On failure or invalid shape show a Spanish error and keep the previous list and filters.
    - _Requirements: 4.9, 4.10, 4.11, 4.12, 12.3, 12.5_

  - [x] 6.3 Implement `Similares/` table, relaxed criteria and suggestions (Persona A)
    - Props `{jugada, onSugerencias}`. Request `api/jugadas/{g}/{p}/similares` (and again with `misma_cobertura=true` when the "Misma cobertura" checkbox is checked), abort the previous request when `jugada` changes and ignore stale responses.
    - Show the table of similar plays, the note "Criterios relajados: ...", each suggestion with `texto`, `evidencia`, `nMuestra` and the visible `baja|media|alta` label, plus "Muestra pequeña" for `baja`, or "No hay sugerencias disponibles" when empty. Call `onSugerencias` with the loaded suggestions.
    - _Requirements: 4.11, 7.8, 7.9, 9.6, 9.7, 9.8, 12.3, 12.5_

  - [x] 6.4 Implement the `Similares/` comparison view (Persona A)
    - Add `Comparacion.tsx` in `Similares/` and use it from `Similares/index.tsx`. Side-by-side formation, personnel and alignment of the requested play and the 3 most frequent values (`top3`), the sample size next to every percentage or average, the Recharts chart of success rate per formation, the message when `rutasDisponibles` is false, and the fixed note "Los datos contienen solo jugadas de pase; 'corredores' se refiere a RB y receptores en ruta" in `text-xs` or larger.
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

- [x] 7. Checkpoint - Person A track complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Person B track: tracking reader
  - [x] 8.1 Implement `backend/tracking.py` (Persona B)
    - `leer_tracking` reads only `data/tracking/tracking_<gameId>.csv` with `usecols=COLUMNAS`, filters by `playId`, returns `None` when the file or the play is missing, coerces numeric cells with `errors="coerce"`, drops rows without `frameId`.
    - `normalizar` (`left`: `x' = 120 - x`, `y' = 53.3 - y`; `right` unchanged); clamp players to 0-120 and 0-53.3, ball not clamped, round to 2 decimals.
    - `a_modelo`: one `cuadros` entry per `frameId` ascending, at most 22 players, `equipo` `ofensiva`/`defensiva`, `balon` or `null`, `eventos` without empty, `None` or duplicate pairs, sorted by `frame`. Keep a `functools.lru_cache(maxsize=16)` over `(game_id, play_id)`.
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 11.5, 12.7, 12.8_

  - [x] 8.2 Write property test for coordinate normalization and clamping (Persona B)
    - File `backend/tests/test_tracking_coords.py`. **Property 8: Normalized player coordinates stay on the field and follow the direction rule**
    - **Validates: Requirements 5.4, 5.5, 5.10**

  - [x] 8.3 Write property test for the normalization inverse (Persona B)
    - File `backend/tests/test_tracking_coords.py`. **Property 9: Normalization is its own inverse**
    - **Validates: Requirements 5.11**

  - [x] 8.4 Write property test for the Tracking structure (Persona B)
    - File `backend/tests/test_tracking_modelo.py`. **Property 10: Tracking object structure**
    - **Validates: Requirements 5.3, 5.6, 5.7**

  - [x] 8.5 Write property test for event extraction (Persona B)
    - File `backend/tests/test_tracking_modelo.py`. **Property 11: Event extraction**
    - **Validates: Requirements 5.8**

  - [x] 8.6 Write property test for bad tracking cells (Persona B)
    - File `backend/tests/test_tracking_csv.py`. **Property 31: Tracking parsing tolerates bad cells** (temporary files with `tmp_path`, never in `data/`)
    - **Validates: Requirements 12.7, 12.8**

  - [x] 8.7 Write property test for the JSON round trip of Tracking (Persona B)
    - File `backend/tests/test_contrato_tracking.py`. **Property 30: JSON round trip of the contract models** (Tracking part, including `balon: null`)
    - **Validates: Requirements 12.1, 12.6**

  - [x] 8.8 Write example tests with real tracking files (Persona B)
    - File `backend/tests/test_tracking_real.py`. One real play from `tracking_2021090900.csv`: 200 in under 2 s, `read_csv` called once with the allowed `usecols` (spy), ball rows in `balon`; missing game file and missing `playId` both give 404. Mean-x check over at least 30 real plays: mean offensive x at `pass_forward` (or last frame) minus mean x at `ball_snap` is greater than 0.
    - _Requirements: 5.1, 5.2, 5.9, 5.12, 5.13, 11.5_

- [x] 9. Person B track: tracking endpoint
  - [x] 9.1 Implement `backend/routers/repeticion.py` (Persona B)
    - `GET /api/jugadas/{gameId}/{playId}/tracking` as a plain `def` endpoint. Call `datos.obtener_jugada` for the offense team, then `tracking.leer_tracking`. Unknown play or `None` result gives 404 `"No se encontraron datos de tracking para esta jugada."`. `gameId` is parsed as `int` before building the file name.
    - _Requirements: 5.1, 5.9, 5.13_

  - [x] 9.2 Write example tests for the tracking endpoint (Persona B)
    - File `backend/tests/test_repeticion.py`. Unknown play gives 404, missing file gives 404 with the Spanish message, a non-integer `gameId` gives 422 in Spanish, and `data/` is not written.
    - _Requirements: 5.9, 1.9_

- [x] 10. Person B track: AI recommendation endpoint
  - [x] 10.1 Implement `backend/routers/ia.py` (Persona B)
    - `construir_respaldo(jugada, sugerencias)` with fixed Spanish templates (fixed text for an empty list, at most 1,500 characters) and a prompt builder that uses only the received data and instructs the model to cite sample sizes and not to invent figures.
    - `POST /api/recomendacion` with `SolicitudRecomendacion`. Compute the fallback first, import `strands` and `boto3` lazily, create `boto3.client("bedrock-runtime", region_name=region)` only with the region, read `BEDROCK_MODEL_ID` (default `us.amazon.nova-pro-v1:0`) and `AWS_REGION` (default `us-east-1`), call the model in a worker thread with `asyncio.wait_for(..., timeout=20)`. Any error, timeout or empty text returns 200 with the fallback and `generado_por_ia: false`; log only the exception class name.
    - Confirm the `BedrockModel` constructor arguments against `strands-agents 1.64.0` without adding dependencies, and never read, check or pass `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` or `AWS_SESSION_TOKEN`.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

  - [x] 10.2 Write property test for the fallback text (Persona B)
    - File `backend/tests/test_ia.py`. **Property 26: Fallback text is deterministic and bounded** (AI client mocked to fail)
    - **Validates: Requirements 10.1, 10.7, 10.8**

  - [x] 10.3 Write property test for the prompt contents (Persona B)
    - File `backend/tests/test_ia.py`. **Property 27: Prompt uses only the received data**
    - **Validates: Requirements 10.6**

  - [x] 10.4 Write property test for invalid recommendation bodies (Persona B)
    - File `backend/tests/test_ia.py`. **Property 28: Invalid recommendation bodies never reach the model**
    - **Validates: Requirements 10.9**

  - [x] 10.5 Write example tests for the recommendation endpoint with a stub Agent (Persona B)
    - File `backend/tests/test_ia_ejemplos.py`. Valid body gives 200 and `generado_por_ia: true`; a stub that raises and a stub that sleeps past a reduced timeout give the fallback; `boto3.client` is called once with `("bedrock-runtime", region_name=<AWS_REGION or us-east-1>)` and nothing else; the model id defaults to `us.amazon.nova-pro-v1:0`.
    - _Requirements: 10.2, 10.3, 10.4, 10.7_

- [x] 11. Person B track: dashboard components
  - [x] 11.1 Implement `Repeticion/` field and tracking load (Persona B)
    - Props `{jugada}`. State `tracking`, `estado` (`cargando | error | listo | sinDatos`). Load `api/jugadas/{gameId}/{playId}/tracking` with `AbortController` and a 10 s timeout, show "Cargando repetición" while pending and a Spanish error message on failure. Abort the previous request and reset when `jugada` changes.
    - SVG with viewBox `0 0 120 53.3`, end zones (0-10 and 110-120), yard lines every 5 yards (heavier every 10) and sidelines. Players as `<circle>` with one color for offense and another for defense, the ball as a non-circular shape. Show a Spanish message when `cuadros` is empty.
    - _Requirements: 1.5, 6.1, 6.2, 6.9, 6.10, 6.12, 6.13, 12.3_

  - [x] 11.2 Implement `Repeticion/` playback controls and timeline (Persona B)
    - Add `Controles.tsx` and `LineaTiempo.tsx` in `Repeticion/` and use them from `index.tsx`. A single `setInterval(100)` active only while playing, stopping at the last frame, restart from frame 0 when playing on the last frame, pause on the current frame.
    - Slider `<input type="range" step=1>` over frame indices, event markers for `ball_snap` ("Snap"), `pass_forward` ("Pase") and result events ("Resultado"); clicking a marker moves the frame without changing the playing state. Disable play, pause and slider when there are no frames.
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.11, 6.13_

  - [x] 11.3 Implement `Recomendacion/` (Persona B)
    - Props `{jugada, sugerencias}`. Send nothing until the user presses "Generar recomendación", exactly one `POST api/recomendacion` per press with a 25 s timeout. While pending show "Generando recomendación" and disable the button.
    - Show the text with the label "Generado con IA" or "Resumen automático (IA no disponible)". On error, timeout or non-200 show "Recomendación no disponible" and re-enable the button. Clear the previous recommendation when the selected play changes and ignore responses for an old play. Show a Spanish AI-unavailable message without changing the other panels.
    - _Requirements: 1.5, 10.10, 10.11, 10.12, 10.13, 10.14, 11.1_

- [x] 12. Checkpoint - Person B track complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Integration (Compartido)
  - [x] 13.1 Wire and review `dashboard/src/App.tsx` with the finished components (Compartido)
    - One person makes this single edit and notifies the other before and after (Requirement 13.4). Confirm that `filtros` changes do not clear `seleccion`, that `Similares/` hands `sugerencias` to `Recomendacion/` without a second request, and that a failed AI call leaves the filters, list, replay and Similares panel unchanged.
    - Confirm that `grep` finds no `fetch('/`, `localhost`, `127.0.0.1`, `http://` or `https://` in `dashboard/src/` and fix any occurrence.
    - _Requirements: 1.5, 1.6, 4.11, 11.1, 13.4_

  - [x] 13.2 Write backend integration tests (Compartido)
    - File `backend/tests/test_integracion.py`. A route forced to raise returns the Spanish JSON without a traceback and the next request works; the hashes of the files in `data/` are the same before and after the run; the full flow filtros, jugadas, tracking, similares and recomendacion (stubbed AI) works with the real data.
    - _Requirements: 1.9, 1.10, 1.13, 11.6_

  - [x] 13.3 Write the dashboard path check test (Compartido)
    - File `backend/tests/test_dashboard_rutas.py`. Scan `dashboard/src/` and fail on `fetch('/`, `localhost`, `127.0.0.1`, `http://` or `https://`.
    - _Requirements: 1.5, 1.6_

- [x] 14. Final verification (Compartido)
  - [x] 14.1 Run `vite build` and fix build errors (Compartido)
    - Run `npm run build` in `dashboard/` (type-checks and runs `vite build`). Fix any TypeScript or build error in the owner's files, confirm `dashboard/dist` exists with relative asset paths, and confirm the Backend serves it at `/` together with the API.
    - _Requirements: 11.7, 11.8_

  - [x] 14.2 Run `sh .hackathon/setup.sh --check` and fix reported problems (Compartido)
    - Rerun until the command exits with code 0 and reports no failed checks. Do not add dependencies or change the folder structure to pass it.
    - _Requirements: 13.5, 13.6_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Owner labels follow Requirement 13: Persona A edits only `backend/datos.py`, `backend/routers/jugadas.py`, `backend/routers/similares.py` and `Filtros/`, `ListaJugadas/`, `Similares/`. Persona B edits only `backend/tracking.py`, `backend/routers/repeticion.py`, `backend/routers/ia.py` and `Repeticion/`, `Recomendacion/`. Test files follow the owner of the code they test.
- The design names `test_datos.py`, `test_jugadas.py`, `test_similares.py`, `test_tracking.py` and `test_ia.py`. This plan splits them by topic so that tasks in the same wave never write the same file.
- Property tests are plain pytest tests with seeded generators and at least 100 iterations, with the property number in a comment `Feature: failed-plays-coach-app, Property N`.
- Component behavior in the Dashboard is verified with the manual checklist from the design (loading and error texts, animation controls, timeline markers, "Sin dato", the 12 px note, button disabling, one POST per press).
- This plan covers design and planning artifacts only. Implementation starts by opening this file and clicking "Start task" next to a task item.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5"] },
    { "id": 2, "tasks": ["1.6", "1.7"] },
    { "id": 3, "tasks": ["1.8", "3.1", "6.1", "6.2", "6.3", "8.1", "10.1", "11.1", "11.3"] },
    { "id": 4, "tasks": ["3.2", "3.6", "3.7", "4.1", "5.1", "6.4", "8.2", "8.4", "8.6", "8.7", "8.8", "9.1", "10.2", "10.5", "11.2"] },
    { "id": 5, "tasks": ["3.3", "4.2", "4.6", "5.2", "5.4", "8.3", "8.5", "9.2", "10.3", "13.1"] },
    { "id": 6, "tasks": ["3.4", "4.3", "5.3", "5.5", "5.9", "10.4", "13.3"] },
    { "id": 7, "tasks": ["3.5", "4.4", "5.6", "5.10", "5.13", "5.18", "5.19", "13.2"] },
    { "id": 8, "tasks": ["4.5", "5.7", "5.11", "5.14"] },
    { "id": 9, "tasks": ["5.8", "5.12", "5.15"] },
    { "id": 10, "tasks": ["5.16"] },
    { "id": 11, "tasks": ["5.17"] },
    { "id": 12, "tasks": ["14.1"] },
    { "id": 13, "tasks": ["14.2"] }
  ]
}
```
