# Requirements Document

## Introduction

Failed Plays Coach App is a coach-oriented web application built on the NFL Big Data Bowl 2023 data (2021 season, weeks 1-8, pass plays only). A coach picks a down, a failure reason and a team, reviews the matching failed offensive plays, replays a selected play in 2D, and receives recommendations based on effective plays from other teams in similar situations. An optional AI layer (Amazon Bedrock Nova through Strands Agents) rewrites the recommendations in natural language. The application works completely without the AI layer.

All user-facing texts are in Spanish. The data in `data/` is read-only. The backend is FastAPI with pandas and numpy; the frontend is React 18, Vite 5, TypeScript, Tailwind 3 and Recharts. No new dependencies, no Docker, and no reliance on writing to disk.

Work split:
- Person A: `backend/datos.py`, `backend/routers/jugadas.py` (`GET /api/filtros`, `GET /api/jugadas`), `backend/routers/similares.py` (`GET /api/jugadas/{gameId}/{playId}/similares`), frontend components `Filtros/`, `ListaJugadas/`, `Similares/`.
- Person B: `backend/tracking.py`, `backend/routers/repeticion.py` (`GET /api/jugadas/{gameId}/{playId}/tracking`), `backend/routers/ia.py` (`POST /api/recomendacion`), frontend components `Repeticion/`, `Recomendacion/`.
- Shared files (`backend/main.py`, `dashboard/src/App.tsx`, `dashboard/src/api/tipos.ts`, `dashboard/vite.config.ts`) are created once in a step 0 skeleton before the two people work in parallel.

## Glossary

- **App**: The complete Failed Plays Coach App (backend plus dashboard).
- **Backend**: The FastAPI application exposed as `app` in `backend/main.py`.
- **Dashboard**: The React frontend in `dashboard/`.
- **Data_Loader**: The module `backend/datos.py` that loads and derives data from `games.csv`, `plays.csv`, `players.csv` and `pffScoutingData.csv`.
- **Tracking_Reader**: The module `backend/tracking.py` that reads one play from one `tracking_<gameId>.csv` file.
- **Jugada**: A pass play with fields `gameId, playId, equipo, rival, down, yardsToGo, razon, descripcion, formacion, personal, cobertura`. `equipo` is the offensive team (`possessionTeam`), `rival` is the defensive team, `formacion` is `offenseFormation`, `personal` is `personnelO`, `cobertura` is `pff_passCoverage`.
- **Failed_Play**: A Jugada with `down` in 1-4 for which at least one failure rule applies.
- **Razon_Falla**: The failure reason of a Failed_Play, one of `incompleto`, `intercepcion`, `sack`, `sin_conversion`, `perdida_de_yardas`.
- **Failure_Classifier**: The component of the Data_Loader that derives Razon_Falla.
- **Effective_Play**: A Jugada from the data that satisfies the effectiveness rule in Requirement 6.
- **Similar_Finder**: The component of `backend/routers/similares.py` that selects Effective_Plays from other teams and builds suggestions.
- **Sugerencia**: A structured suggestion `{texto, evidencia, nMuestra}` with a confidence label.
- **Etiqueta_Confianza**: A confidence label derived from `nMuestra`: `baja`, `media` or `alta`.
- **Replay_Viewer**: The Dashboard component `Repeticion/` that draws the 2D replay.
- **Normalized_Coordinates**: Tracking coordinates transformed so that the offense always moves toward increasing x.
- **Frame_Event**: A tracking event such as `ball_snap`, `pass_forward` or a result event, tied to a `frameId`.
- **AI_Service**: The module `backend/routers/ia.py` that calls Amazon Bedrock Nova through Strands Agents and boto3.
- **Texto_Respaldo**: A rule-based natural-language recommendation text generated without AI.
- **Filter_Panel**: The Dashboard component `Filtros/` containing the down, reason and team selectors.
- **Play_List**: The Dashboard component `ListaJugadas/`.
- **Similares_Panel**: The Dashboard component `Similares/`.
- **Recommendation_Panel**: The Dashboard component `Recomendacion/`.

## Requirements

### Requirement 1: Project Skeleton and Platform Contract

**User Story:** As a team member, I want a shared skeleton set up once, so that Person A and Person B can work in parallel on the same computer without conflicts.

#### Acceptance Criteria

1. WHEN a client sends `GET /health` to the Backend, THE Backend SHALL respond within 500 ms with a JSON body equal to `{"status": "ok"}`, using the `app` object exposed in `backend/main.py`.
2. THE Backend SHALL define the `cargar_env()` function from the project rules at the top of `backend/main.py`, before any import that uses boto3, and SHALL call it before the first such import.
3. THE Backend SHALL register every API route except `GET /health` under the `/api/` prefix.
4. THE Backend SHALL register exactly the four routers `jugadas`, `similares`, `repeticion` and `ia` from `backend/main.py`, so that Person A and Person B edit only their own router files after the skeleton exists.
5. THE Dashboard SHALL call the API only with relative paths without a leading slash, in the form `fetch('api/<ruta>')`.
6. THE Dashboard SHALL contain zero occurrences of `localhost`, `127.0.0.1` or absolute URLs (strings beginning with `http://` or `https://`) in files under `dashboard/src/`.
7. THE `dashboard/vite.config.ts` SHALL define `base: './'` and a proxy that forwards `/api` to `http://localhost:8000`.
8. THE `dashboard/src/api/tipos.ts` SHALL define the TypeScript types `Jugada`, `Tracking` and `Similares`, each with the same field names and types as the shared contract in Requirements 4, 5 and 7.
9. THE App SHALL read files in `data/` using paths relative to the project root and SHALL NOT modify, create or delete any file in `data/`.
10. THE App SHALL compute all derived data at startup or on request and SHALL NOT write any file to disk.
11. THE App SHALL declare no Python or npm dependency, and no version of one, other than those fixed in `.kiro/steering/rules.md`.
12. THE Dashboard SHALL render every user-facing text in Spanish.
13. IF a `data/` file is missing or unreadable when the Backend reads it, THEN THE Backend SHALL return an error response for the affected request, SHALL keep running, and SHALL leave all other routes operational.

### Requirement 2: Failure Classification

**User Story:** As a coach, I want each pass play labeled with a clear failure reason, so that I can study why drives stalled.

#### Acceptance Criteria

1. THE Failure_Classifier SHALL exclude plays with `down` equal to 0 from the set of Failed_Plays, even when another failure rule would apply.
2. WHEN `passResult` equals `IN`, THE Failure_Classifier SHALL mark the play as a failure with reason `intercepcion`.
3. WHEN `passResult` equals `S`, THE Failure_Classifier SHALL mark the play as a failure with reason `sack`.
4. WHEN `passResult` equals `I`, THE Failure_Classifier SHALL mark the play as a failure with reason `incompleto`.
5. WHEN `down` is 3 or 4 and `playResult` is less than `yardsToGo`, THE Failure_Classifier SHALL mark the play as a failure with reason `sin_conversion`.
6. WHEN `playResult` is less than 0, THE Failure_Classifier SHALL mark the play as a failure with reason `perdida_de_yardas`.
7. WHERE more than one failure rule applies to a play, THE Failure_Classifier SHALL assign exactly one Razon_Falla using the precedence `intercepcion`, then `sack`, then `incompleto`, then `perdida_de_yardas`, then `sin_conversion`.
8. WHEN a play is marked as a Failed_Play, THE Failure_Classifier SHALL assign a `descripcion` written in Spanish that contains the `down` value, the `yardsToGo` value, and the assigned Razon_Falla, with a maximum length of 200 characters.
9. WHEN a play does not satisfy any failure rule, THE Failure_Classifier SHALL leave the play out of the Failed_Play set.
10. FOR ALL plays in `plays.csv`, THE Failure_Classifier SHALL produce at most one Razon_Falla per play, and classifying the same input twice SHALL produce the same result (idempotence).
11. THE Failure_Classifier SHALL treat each play as identified by the pair `gameId` and `playId`.
12. IF a play has a missing or non-numeric value in `down`, `yardsToGo`, or `playResult`, or a missing `gameId` or `playId`, THEN THE Failure_Classifier SHALL skip that play, leave it out of the Failed_Play set, and continue classifying the remaining plays without altering them.

### Requirement 3: Filters Endpoint

**User Story:** As a coach, I want the available down, reason and team options, so that I can build a valid filter selection.

#### Acceptance Criteria

1. WHEN a client requests `GET /api/filtros`, THE Backend SHALL return a JSON response within 2 seconds containing three lists: the downs (the integers 1, 2, 3 and 4 in ascending order), the five Razon_Falla values, and the offensive team abbreviations present in the Failed_Play set.
2. WHEN a client requests `GET /api/filtros`, THE Backend SHALL return the team list sorted in ascending alphabetical order by abbreviation, with no duplicate teams.
3. WHEN a client requests `GET /api/filtros`, THE Backend SHALL return each team with its abbreviation and, IF `games.csv` provides a full display name for that team, the full display name. IF `games.csv` does not provide a full display name for that team, THEN THE Backend SHALL return that team with its abbreviation only.
4. IF the Failed_Play set contains no plays for a team, THEN THE Backend SHALL omit that team from the team list.
5. IF the data files cannot be loaded, THEN THE Backend SHALL respond with HTTP status 500 and a JSON body containing a Spanish error message indicating that the data could not be loaded, and THE Backend SHALL return no partial lists.

### Requirement 4: Failed Plays Listing

**User Story:** As a coach, I want to filter failed plays by down, reason and team, so that I can see only the plays relevant to my question.

#### Acceptance Criteria

1. WHEN a client requests `GET /api/jugadas` with the optional query parameters `down`, `razon` and `equipo`, THE Backend SHALL return the Jugadas of the Failed_Play set that match every provided parameter, comparing `equipo` as an exact, case-sensitive match against the team abbreviation.
2. WHERE a query parameter is omitted, THE Backend SHALL not restrict results by that parameter.
3. WHEN the Backend returns a Jugada, THE Backend SHALL include the fields `gameId, playId, equipo, rival, down, yardsToGo, razon, descripcion, formacion, personal, cobertura`, and SHALL return each field that has no source value as null.
4. WHEN no Failed_Play matches the parameters, THE Backend SHALL return an empty list with HTTP status 200.
5. IF `down` is not an integer from 1 to 4, or `razon` is not one of the five Razon_Falla values, THEN THE Backend SHALL respond with HTTP status 422 and a Spanish error message that names the invalid parameter, and SHALL return no Jugadas.
6. THE Backend SHALL return the Jugadas in ascending order by `gameId` and then ascending order by `playId`, and the same request SHALL return the same order on every call.
7. WHEN the filters are applied, THE Backend SHALL return only Jugadas whose `down`, `razon` and `equipo` equal each provided value (invariant).
8. WHEN startup data loading has finished, THE Backend SHALL respond to `GET /api/jugadas` within 1 second for any filter combination.
9. WHEN the user changes a selection in the Filter_Panel, THE Dashboard SHALL send a new `GET /api/jugadas` request with the current selections and SHALL replace the Play_List contents with the response within 1 second of receiving it.
10. WHEN the response list is empty, THE Play_List SHALL show the Spanish text "No hay jugadas fallidas con estos filtros".
11. WHEN the user selects a play in the Play_List, THE Dashboard SHALL load the Replay_Viewer, the Similares_Panel and the Recommendation_Panel for that play, and SHALL mark that play as selected in the Play_List.
12. IF the request for the list fails or does not respond within 10 seconds, THEN THE Dashboard SHALL show a Spanish error message, SHALL keep the previous filter selection, and SHALL keep the previously displayed Play_List contents.

### Requirement 5: Tracking Endpoint

**User Story:** As a coach, I want the tracking data of one play, so that I can watch it replayed.

#### Acceptance Criteria

1. WHEN a client requests `GET /api/jugadas/{gameId}/{playId}/tracking` and `tracking_<gameId>.csv` exists and contains at least 1 row where `playId` matches, THE Tracking_Reader SHALL read only the file `tracking_<gameId>.csv` and only the rows where `playId` matches.
2. WHEN THE Tracking_Reader reads `tracking_<gameId>.csv`, THE Tracking_Reader SHALL read it using `usecols` restricted to the columns needed to build the Tracking object and SHALL NOT load the tracking data of any other game.
3. WHEN a tracking request succeeds, THE Backend SHALL return a Tracking object `{eventos: [{frame, evento}], cuadros: [{frame, jugadores: [{nflId, equipo, x, y}], balon: {x, y}}]}` in which `frame` is an integer equal to `frameId`, `nflId` is an integer, `equipo` is a string, and `x` and `y` are numbers rounded to 2 decimal places.
4. WHEN `playDirection` of the play is `left`, THE Tracking_Reader SHALL transform each player and ball coordinate to `x' = 120 - x` and `y' = 53.3 - y`.
5. WHEN `playDirection` of the play is `right`, THE Tracking_Reader SHALL keep each player and ball coordinate unchanged.
6. WHEN a tracking request succeeds, THE Tracking_Reader SHALL return in `cuadros` exactly one entry per distinct `frameId` of the play, ordered by ascending `frame`, with 0 to 22 entries in `jugadores` and one `balon` position per entry (or `null` when the ball has no row in that frame).
7. WHEN a tracking request succeeds, THE Tracking_Reader SHALL set the `equipo` of each player to `ofensiva` if the `team` value equals the possession team abbreviation of the play, and to `defensiva` otherwise, and SHALL place rows with `team` equal to `football` in `balon` and not in `jugadores`.
8. WHEN a tracking request succeeds, THE Tracking_Reader SHALL return in `eventos` one entry for each row whose `event` value is neither empty nor the literal string `None`, with the `frameId` of that row as `frame`, in ascending `frame` order, without duplicate (`frame`, `evento`) pairs, and SHALL return an empty list if the play has no such rows.
9. IF `tracking_<gameId>.csv` does not exist, or contains no rows for the requested `playId`, THEN THE Backend SHALL respond with HTTP status 404 and a Spanish error message indicating that the tracking data was not found, and SHALL NOT modify any stored data.
10. WHEN THE Tracking_Reader normalizes a play, THE Tracking_Reader SHALL return every x within 0 to 120 inclusive and every y within 0 to 53.3 inclusive for players on the field (invariant), clamping values outside those ranges.
11. FOR ALL plays, applying the normalization transform twice SHALL return the original coordinates within a tolerance of 0.01 (round-trip property).
12. FOR ALL plays taken together, THE Tracking_Reader SHALL produce normalized coordinates where the mean x of offensive players at the `pass_forward` frame (or at the last frame of the play if the play has no `pass_forward` event) is greater than their mean x at the `ball_snap` frame, evaluated as the average over the set of plays and not play by play.
13. WHEN a client requests the tracking of one play, THE Backend SHALL respond within 2 seconds, measured from request receipt to the last byte of the response.

### Requirement 6: 2D Replay

**User Story:** As a coach, I want to watch the failed play on a field, so that I can understand what happened on the field.

#### Acceptance Criteria

1. WHEN a play is selected, THE Replay_Viewer SHALL request its tracking data and, within 1000 ms of receiving the data, draw a football field in SVG with yard lines, end zones and sidelines.
2. WHEN a tracking frame is displayed, THE Replay_Viewer SHALL draw each player present in that frame (maximum 22) as a circle whose fill color is one color for offense and a different color for defense, and SHALL draw the ball as a non-circular shape.
3. WHEN the user activates the play control while the animation is paused, THE Replay_Viewer SHALL start the animation from the current frame. WHEN the user activates the pause control while the animation is playing, THE Replay_Viewer SHALL stop the animation on the current frame.
4. WHILE the animation is playing, THE Replay_Viewer SHALL advance one tracking frame every 100 ms (±20 ms), matching the 10 frames per second of the data.
5. THE Replay_Viewer SHALL provide a timeline slider whose range runs from the first frame to the last frame of the play, in steps of one frame.
6. THE Replay_Viewer SHALL mark on the timeline the frame of the event `ball_snap`, the frame of the event `pass_forward`, and the frame of each result event present in the play. The result events are `pass_arrived`, `pass_outcome_caught`, `pass_outcome_incomplete`, `pass_outcome_interception`, `qb_sack`, `fumble`, `tackle`, `out_of_bounds`, `touchdown` and `autoevent_*` variants.
7. WHEN the user selects an event marker on the timeline, THE Replay_Viewer SHALL move the playback position to the frame of that event within 100 ms. IF the animation was playing, THEN it SHALL continue playing from that frame. IF it was paused, THEN it SHALL remain paused on that frame.
8. WHEN the animation reaches the last frame, THE Replay_Viewer SHALL stop playing, keep showing the last frame, and show the play control as available to restart. WHEN the user activates the play control on the last frame, THE Replay_Viewer SHALL restart the animation from the first frame.
9. WHILE the tracking request is pending, THE Replay_Viewer SHALL show the Spanish text "Cargando repetición".
10. IF the tracking request fails or does not respond within 10 seconds, THEN THE Replay_Viewer SHALL remove the loading text, show a Spanish error message indicating that the replay could not be loaded, and keep the Play_List, Similares_Panel and Recommendation_Panel responsive to user selection.
11. THE Replay_Viewer SHALL show the event names in Spanish in the timeline labels: "Snap" for `ball_snap`, "Pase" for `pass_forward`, and "Resultado" for each result event.
12. WHEN the selected play changes, THE Replay_Viewer SHALL cancel any pending tracking request for the previous play, reset the playback to the first frame in a paused state, and show only the data of the newly selected play.
13. IF the tracking data of a play contains no frames, THEN THE Replay_Viewer SHALL show a Spanish message indicating that the play has no tracking data, and SHALL disable the play control, the pause control and the timeline slider.

### Requirement 7: Similar Effective Plays

**User Story:** As a coach, I want effective plays from other teams in the same situation, so that I can see what worked for them.

#### Acceptance Criteria

1. THE Similar_Finder SHALL classify a Jugada as an Effective_Play IF the play is not a Failed_Play, `passResult` equals `C`, and `playResult` is at least 40% of `yardsToGo` on down 1, at least 60% of `yardsToGo` on down 2, or at least 100% of `yardsToGo` on down 3 or 4.
2. WHEN a client requests `GET /api/jugadas/{gameId}/{playId}/similares`, THE Backend SHALL return HTTP status 200 with an object `{similares: [...], sugerencias: [{texto, evidencia, nMuestra, confianza}], criteriosRelajados: [...]}`, where `texto` and `evidencia` are non-empty strings and `nMuestra` is an integer from 1 to 20 equal to the number of plays in `similares` supporting that suggestion.
3. THE Similar_Finder SHALL select only Effective_Plays whose offensive team differs from the offensive team of the requested play.
4. THE Similar_Finder SHALL select only Effective_Plays with the same `down` as the requested play.
5. THE Similar_Finder SHALL select only Effective_Plays whose `yardsToGo` differs from that of the requested play by at most 2 yards, inclusive.
6. THE Similar_Finder SHALL select only Effective_Plays with the same `offenseFormation` and the same `personnelO` as the requested play.
7. WHERE the client passes the query parameter `misma_cobertura=true`, THE Similar_Finder SHALL additionally require the same `pff_passCoverage` as the requested play, and SHALL NOT relax this criterion under criterion 9.
8. IF the requested play has a null `offenseFormation`, `personnelO` or `pff_passCoverage` value, THEN THE Similar_Finder SHALL treat the corresponding criterion as dropped, and SHALL list it in `criteriosRelajados`.
9. IF fewer than 5 Effective_Plays match all criteria, THEN THE Similar_Finder SHALL relax the criteria one step at a time in this order until at least 5 Effective_Plays match or all steps are applied: (1) drop `personnelO`, (2) widen the `yardsToGo` tolerance to 4 yards, (3) drop `offenseFormation`. THE Backend SHALL list each applied step in `criteriosRelajados` using the identifiers `personnelO`, `yardsToGo` and `offenseFormation`, and SHALL return an empty `criteriosRelajados` list when no step was applied.
10. THE Backend SHALL return each element of `similares` with the fields `gameId`, `playId`, `equipo`, `rival`, `yardsToGo`, `playResult`, `formacion`, `personal` and `cobertura`.
11. THE Backend SHALL limit `similares` to at most 20 plays, selected and ordered by `playResult` descending, then by `gameId` ascending, then by `playId` ascending.
12. IF the requested `gameId` and `playId` do not exist, THEN THE Backend SHALL respond with HTTP status 404 and an error message in Spanish indicating that the play was not found.
13. IF no Effective_Play matches after all applicable relaxations, THEN THE Backend SHALL respond with HTTP status 200 and empty lists in `similares` and `sugerencias`.
14. FOR ALL returned similar plays, `equipo` SHALL differ from the `equipo` of the requested play, and `down` SHALL equal the `down` of the requested play (invariant).

### Requirement 8: Formation and Route Comparison

**User Story:** As a coach, I want to compare the formations and routes of my failed play against effective plays, so that I can see what the other teams did differently.

#### Acceptance Criteria

1. WHEN a comparison is requested for a play, THE Similar_Finder SHALL obtain, for the requested play and for each similar play, the offensive alignment from the `pffScoutingData.csv` fields `pff_positionLinedUp` and `pff_role`, joined with the player position from `players.csv`.
2. THE Similar_Finder SHALL treat as route data only the rows with `pff_role` equal to `Pass Route` and a player position in `WR`, `TE`, `RB` or `FB`, and SHALL exclude rows with `pff_role` equal to `Pass`, `Pass Block`, `Pass Rush` or `Coverage`.
3. WHEN the similar plays have been determined, THE Similar_Finder SHALL count how many times each combination of `pff_positionLinedUp` and `pff_role` occurs among the similar plays, and SHALL return the 10 most frequent combinations in descending order of count, with ties broken alphabetically by `pff_positionLinedUp`.
4. WHEN the similar plays have been determined, THE Similar_Finder SHALL calculate the share of similar plays, as a percentage with 1 decimal place, for each value of `offenseFormation`, of `personnelO` and, where `pff_passCoverage` is available for the play, of `pff_passCoverage`.
5. WHEN the similar plays have been determined, THE Similar_Finder SHALL calculate, for each `offenseFormation` value, the success rate as a percentage with 1 decimal place and the average `playResult` in yards with 1 decimal place, over all plays of other teams with the same `down` and a `yardsToGo` within the applied tolerance, regardless of outcome. A play counts as a success when it is an Effective_Play.
6. WHEN the Similar_Finder returns a comparison, THE Similares_Panel SHALL show side by side the `offenseFormation`, `personnelO` and `pff_positionLinedUp` alignments of the requested play and the 3 most frequent values of each among the similar plays.
7. THE Similares_Panel SHALL show the Spanish text "Los datos contienen solo jugadas de pase; 'corredores' se refiere a RB y receptores en ruta" in the same panel section as the comparison, with a font size of at least 12 px.
8. IF `pffScoutingData.csv` has no rows for a play, THEN THE Similar_Finder SHALL omit the route comparison for that play, SHALL return all other comparison data unchanged, and SHALL mark the route comparison as unavailable so that the Similares_Panel shows a message indicating that route data is missing for that play.
9. THE Similares_Panel SHALL show, next to each percentage or average, the sample size as the number of plays used in the calculation.

### Requirement 9: Structured Suggestions with Confidence

**User Story:** As a coach, I want suggestions with evidence and a confidence level, so that I know how much to trust each one.

#### Acceptance Criteria

1. WHEN the Backend receives a request for similar plays, THE Similar_Finder SHALL generate each Sugerencia in the form `{texto, evidencia, nMuestra, confianza}`, where `texto` is in Spanish and has 1 to 280 characters, `evidencia` is a non-empty string of 1 to 280 characters that names the metric and the comparison group, and `nMuestra` is an integer equal to the number of similar plays supporting the Sugerencia.
2. WHEN the Similar_Finder generates a Sugerencia, THE Similar_Finder SHALL assign Etiqueta_Confianza `baja` IF `nMuestra` is from 1 to 4, `media` IF `nMuestra` is from 5 to 14, and `alta` IF `nMuestra` is 15 or more, and SHALL store it in the field `confianza`.
3. WHEN the Backend returns Sugerencias, THE Backend SHALL include the Etiqueta_Confianza of each Sugerencia in the response.
4. WHEN the Similar_Finder generates Sugerencias for a request, THE Similar_Finder SHALL return at most 5 Sugerencias, ordered by `nMuestra` descending. IF two Sugerencias have the same `nMuestra`, THEN THE Similar_Finder SHALL order them by their position of generation, so the order is the same on every request.
5. IF the `nMuestra` supporting a candidate Sugerencia is 0, THEN THE Similar_Finder SHALL discard the candidate and not include it in the response.
6. WHEN the Similares_Panel receives Sugerencias, THE Similares_Panel SHALL show each Sugerencia with its `texto`, its `evidencia`, its `nMuestra` and its Etiqueta_Confianza as a text label (`baja`, `media` or `alta`) that is visible without user interaction.
7. WHEN a Sugerencia has Etiqueta_Confianza `baja`, THE Similares_Panel SHALL show the label "Muestra pequeña" adjacent to that Sugerencia.
8. IF the Similar_Finder generates 0 Sugerencias for a request, THEN THE Backend SHALL return an empty list of Sugerencias with no error, and THE Similares_Panel SHALL show a message stating that no suggestions are available.
9. FOR ALL Sugerencias returned in a response, `nMuestra` SHALL be less than or equal to the length of `similares` in that same response (invariant).
10. WHEN the Backend receives two requests with the same play and the same parameters and no change in the underlying data, THE Backend SHALL return identical Sugerencias (same `texto`, `evidencia`, `nMuestra`, `confianza` and order) in both responses (determinism).

### Requirement 10: AI Recommendation (Optional)

**User Story:** As a coach, I want the recommendations explained in natural language, so that I can read them quickly.

#### Acceptance Criteria

1. WHEN a client sends `POST /api/recomendacion` with a valid Jugada and a list of 0 to 20 Sugerencias, THE AI_Service SHALL return HTTP status 200 with a JSON object containing the Spanish text `recomendacion` (1 to 1,500 characters) and a boolean `generado_por_ia`.
2. THE AI_Service SHALL call Amazon Bedrock Nova only through Strands Agents and a boto3 client created as `boto3.client("bedrock-runtime", region_name=region)`.
3. THE AI_Service SHALL read the model from `BEDROCK_MODEL_ID` with default `us.amazon.nova-pro-v1:0` and the region from `AWS_REGION` with default `us-east-1`.
4. THE AI_Service SHALL NOT read, check, require or pass `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` or `AWS_SESSION_TOKEN`, and SHALL NOT log credentials.
5. THE AI_Service SHALL use no AWS service other than Amazon Bedrock.
6. THE AI_Service SHALL build the prompt only from the play data and the Sugerencias received, and SHALL instruct the model to cite the sample size (number of plays) of each Sugerencia it mentions and not to state any figure absent from the received data.
7. IF the AI call fails, does not return a response within 20 seconds, or is not configured, THEN THE AI_Service SHALL return HTTP status 200 with `recomendacion` set to the Texto_Respaldo and `generado_por_ia` set to false.
8. THE AI_Service SHALL generate the Texto_Respaldo from the Sugerencias with fixed Spanish templates, without calling any external service, and with the same output for the same input. IF the list of Sugerencias is empty, THEN THE AI_Service SHALL generate a fixed Spanish text stating that there are no suggestions available.
9. IF the request body is missing, is not valid JSON, lacks the Jugada, or contains a field of the wrong type, THEN THE AI_Service SHALL respond with HTTP status 422 and a Spanish error message identifying the invalid field, and SHALL NOT call Amazon Bedrock.
10. WHILE the recommendation request is pending, THE Recommendation_Panel SHALL show the Spanish text "Generando recomendación" and SHALL disable the "Generar recomendación" button.
11. WHEN the response has `generado_por_ia` equal to true, THE Recommendation_Panel SHALL show the `recomendacion` text with the label "Generado con IA".
12. WHEN the response has `generado_por_ia` equal to false, THE Recommendation_Panel SHALL show the `recomendacion` text with the label "Resumen automático (IA no disponible)".
13. IF the request from the Dashboard fails, does not return a response within 25 seconds, or returns a non-200 status, THEN THE Recommendation_Panel SHALL show the Spanish text "Recomendación no disponible", SHALL re-enable the "Generar recomendación" button, and the rest of the Dashboard SHALL remain operable.
14. THE Dashboard SHALL send no request to `POST /api/recomendacion` until the user presses a button labeled "Generar recomendación", and SHALL send exactly one request per press.

### Requirement 11: Graceful Degradation and Performance

**User Story:** As a coach, I want the app to keep working when a part fails, so that one failure does not block my analysis.

#### Acceptance Criteria

1. IF the AI_Service is unavailable (no response within 10 seconds, a connection error, or an error response), THEN THE App SHALL keep the filters, the Play_List, the Replay_Viewer and the Similares_Panel fully functional, SHALL show a Spanish message in the AI area indicating that the AI is unavailable, and SHALL keep the current filter selection and the selected play unchanged.
2. WHEN the Backend starts, THE Data_Loader SHALL load `games.csv`, `plays.csv`, `players.csv` and `pffScoutingData.csv` once and keep the derived tables in memory for the lifetime of the Backend process.
3. WHEN the Backend starts, THE Backend SHALL complete the startup data loading within 30 seconds and then start accepting requests.
4. IF any of the four CSV files is missing or unreadable at startup, THEN THE Backend SHALL stop startup and SHALL report an error that names the missing file.
5. WHEN a request needs tracking data, THE Tracking_Reader SHALL load the tracking file of exactly one game and SHALL NOT load more than one tracking file per request.
6. IF an unhandled error occurs in an endpoint, THEN THE Backend SHALL respond with a JSON body containing a Spanish message and SHALL NOT include stack traces or file paths, and the Backend SHALL keep running and serve the next request.
7. WHEN the Dashboard is built with `vite build`, THE build SHALL produce `dashboard/dist`, and THE Backend SHALL serve `dashboard/dist` together with the API on the same URL and port.
8. THE Dashboard SHALL use the relative base `./` so that all assets (scripts, styles and images) load without errors when the app is published under a subpath.

### Requirement 12: Data Parsing and Round-Trip Contracts

**User Story:** As a developer, I want the data models serialized and parsed reliably, so that the Backend and the Dashboard agree on the contract.

#### Acceptance Criteria

1. WHEN the Backend returns a Jugada, Tracking or Similares object, THE Backend SHALL serialize it as JSON using Pydantic models whose field names and types match the shared contract.
2. WHEN the Dashboard receives a JSON response containing a Jugada, Tracking or Similares object, THE Dashboard SHALL parse it into the TypeScript types in `dashboard/src/api/tipos.ts`.
3. IF a JSON response fails to parse into the expected TypeScript type, THEN THE Dashboard SHALL discard the response, SHALL keep previously displayed data unchanged, and SHALL show an error message indicating the data could not be read.
4. IF a value in `formacion`, `personal` or `cobertura` is NaN or missing, THEN THE Backend SHALL serialize it as `null` and SHALL NOT emit the literal `NaN` anywhere in the JSON output.
5. WHEN `formacion`, `personal` or `cobertura` is `null`, THE Dashboard SHALL show the Spanish text "Sin dato" in place of that value.
6. FOR ALL valid Jugada, Tracking and Similares objects, serializing to JSON and parsing back SHALL produce an object equal to the original in every field, with `null` values preserved as `null` (round-trip property).
7. WHEN the Tracking_Reader reads a tracking file, THE Tracking_Reader SHALL treat an empty `event` value and the literal string `None` as no event, SHALL parse `time` as an ISO-8601 timestamp (for example 2021-09-10T00:26:31Z), and SHALL parse all other numeric columns as numbers.
8. IF a `time` value is not a valid ISO-8601 timestamp or a numeric column value is not a valid number, THEN THE Tracking_Reader SHALL store that value as missing, SHALL keep the remaining fields of the row, and SHALL continue reading the file.
9. WHEN the Data_Loader reads a `personnelO` value (for example "1 RB, 1 TE, 3 WR"), THE Data_Loader SHALL parse it into one non-negative integer count per position group, and a formatter SHALL print the counts back into the same text, so that parsing, then printing, then parsing produces equal counts (round-trip property).
10. IF a `personnelO` value cannot be parsed, THEN THE Data_Loader SHALL keep the original text, SHALL mark the personnel counts for that row as missing, and SHALL continue the load without stopping.

### Requirement 13: Delivery Coordination

**User Story:** As a team, I want a clear split of work and a defined order, so that two people can finish the app in parallel without version control.

#### Acceptance Criteria

1. WHEN the team starts delivery work, THE team SHALL complete every step 0 skeleton item listed in Requirement 1 before Person A or Person B begins editing any file in their own modules.
2. THE Person A modules SHALL own only `backend/datos.py`, `backend/routers/jugadas.py`, `backend/routers/similares.py` and the folders `Filtros/`, `ListaJugadas/` and `Similares/`, and Person B SHALL NOT edit these files or folders.
3. THE Person B modules SHALL own only `backend/tracking.py`, `backend/routers/repeticion.py`, `backend/routers/ia.py` and the folders `Repeticion/` and `Recomendacion/`, and Person A SHALL NOT edit these files or folders.
4. WHEN a file outside the Person A and Person B ownership lists (a shared file) needs a change after step 0, THE team SHALL make the change as a single edit by one person and SHALL notify the other person before that edit is made and again when it is complete.
5. WHEN the team prepares the final delivery, THE team SHALL run `sh .hackathon/setup.sh --check` and SHALL confirm that the command exits with code 0 and reports no failed checks.
6. IF `sh .hackathon/setup.sh --check` exits with a non-zero code, THEN THE team SHALL fix the reported problems and rerun the check until it exits with code 0 before declaring the app delivered.
7. THE team SHALL NOT include git or branch tasks (such as commit, branch, merge, pull request or push) in the work plan.
