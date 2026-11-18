// Tipos de la API. Nombres y tipos idénticos a backend/modelos.py.

export interface Jugada {
  gameId: number;
  playId: number;
  equipo: string;
  rival: string;
  down: number;
  yardsToGo: number;
  razon: string;
  descripcion: string;
  formacion: string | null;
  personal: string | null;
  cobertura: string | null;
}

export interface Evento {
  frame: number;
  evento: string;
}

export interface JugadorFrame {
  nflId: number;
  equipo: 'ofensiva' | 'defensiva';
  x: number;
  y: number;
}

export interface Balon {
  x: number;
  y: number;
}

export interface Cuadro {
  frame: number;
  jugadores: JugadorFrame[];
  balon: Balon | null;
}

export interface Tracking {
  eventos: Evento[];
  cuadros: Cuadro[];
}

export interface JugadaSimilar {
  gameId: number;
  playId: number;
  equipo: string;
  rival: string;
  yardsToGo: number;
  playResult: number;
  formacion: string | null;
  personal: string | null;
  cobertura: string | null;
}

export type Confianza = 'baja' | 'media' | 'alta';

export interface Sugerencia {
  texto: string;
  evidencia: string;
  nMuestra: number;
  confianza: Confianza;
}

export interface Solicitada {
  formacion: string | null;
  personal: string | null;
  alineacion: string[];
}

export interface ValorDistribucion {
  valor: string;
  porcentaje: number;
  nMuestra: number;
}

export interface Distribucion {
  formacion: ValorDistribucion[];
  personal: ValorDistribucion[];
  cobertura: ValorDistribucion[];
}

export interface AlineacionConteo {
  posicion: string;
  rol: string;
  conteo: number;
}

export interface ExitoFormacion {
  formacion: string;
  tasaExito: number;
  yardasPromedio: number;
  nMuestra: number;
}

export interface Top3 {
  formacion: string[];
  personal: string[];
  alineacion: string[];
}

export interface Comparacion {
  solicitada: Solicitada;
  distribucion: Distribucion;
  alineaciones: AlineacionConteo[];
  rutasDisponibles: boolean;
  exitoPorFormacion: ExitoFormacion[];
  top3: Top3;
}

export interface Similares {
  similares: JugadaSimilar[];
  sugerencias: Sugerencia[];
  criteriosRelajados: string[];
  comparacion: Comparacion;
}

export interface Filtros {
  down?: number;
  razon?: string;
  equipo?: string;
}

export interface Recomendacion {
  recomendacion: string;
  generado_por_ia: boolean;
}

// ---------- Guardas de tipo en tiempo de ejecución ----------

type Obj = Record<string, unknown>;

const esObj = (x: unknown): x is Obj =>
  typeof x === 'object' && x !== null && !Array.isArray(x);
const esNum = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x);
const esEntero = (x: unknown): x is number => esNum(x) && Number.isInteger(x);
const esStr = (x: unknown): x is string => typeof x === 'string';
const esStrONull = (x: unknown): boolean => x === null || esStr(x);
const esArr = (x: unknown, f: (e: unknown) => boolean): boolean =>
  Array.isArray(x) && x.every(f);

const esEvento = (x: unknown): x is Evento =>
  esObj(x) && esEntero(x.frame) && esStr(x.evento);

const esXY = (x: unknown): boolean => esObj(x) && esNum(x.x) && esNum(x.y);

const esJugadorFrame = (x: unknown): x is JugadorFrame =>
  esObj(x) &&
  esEntero(x.nflId) &&
  (x.equipo === 'ofensiva' || x.equipo === 'defensiva') &&
  esNum(x.x) &&
  esNum(x.y);

const esCuadro = (x: unknown): x is Cuadro =>
  esObj(x) &&
  esEntero(x.frame) &&
  esArr(x.jugadores, esJugadorFrame) &&
  (x.balon === null || esXY(x.balon));

export function esJugada(x: unknown): x is Jugada {
  return (
    esObj(x) &&
    esEntero(x.gameId) &&
    esEntero(x.playId) &&
    esStr(x.equipo) &&
    esStr(x.rival) &&
    esEntero(x.down) &&
    esEntero(x.yardsToGo) &&
    esStr(x.razon) &&
    esStr(x.descripcion) &&
    esStrONull(x.formacion) &&
    esStrONull(x.personal) &&
    esStrONull(x.cobertura)
  );
}

export function esTracking(x: unknown): x is Tracking {
  return esObj(x) && esArr(x.eventos, esEvento) && esArr(x.cuadros, esCuadro);
}

const esJugadaSimilar = (x: unknown): x is JugadaSimilar =>
  esObj(x) &&
  esEntero(x.gameId) &&
  esEntero(x.playId) &&
  esStr(x.equipo) &&
  esStr(x.rival) &&
  esEntero(x.yardsToGo) &&
  esEntero(x.playResult) &&
  esStrONull(x.formacion) &&
  esStrONull(x.personal) &&
  esStrONull(x.cobertura);

const esSugerencia = (x: unknown): x is Sugerencia =>
  esObj(x) &&
  esStr(x.texto) &&
  esStr(x.evidencia) &&
  esEntero(x.nMuestra) &&
  (x.confianza === 'baja' || x.confianza === 'media' || x.confianza === 'alta');

const esStrArr = (x: unknown): boolean => esArr(x, esStr);

const esValorDistribucion = (x: unknown): boolean =>
  esObj(x) && esStr(x.valor) && esNum(x.porcentaje) && esEntero(x.nMuestra);

const esComparacion = (x: unknown): x is Comparacion => {
  if (!esObj(x)) return false;
  const s = x.solicitada;
  const d = x.distribucion;
  const t = x.top3;
  return (
    esObj(s) &&
    esStrONull(s.formacion) &&
    esStrONull(s.personal) &&
    esStrArr(s.alineacion) &&
    esObj(d) &&
    esArr(d.formacion, esValorDistribucion) &&
    esArr(d.personal, esValorDistribucion) &&
    esArr(d.cobertura, esValorDistribucion) &&
    esArr(
      x.alineaciones,
      (a) => esObj(a) && esStr(a.posicion) && esStr(a.rol) && esEntero(a.conteo),
    ) &&
    typeof x.rutasDisponibles === 'boolean' &&
    esArr(
      x.exitoPorFormacion,
      (e) =>
        esObj(e) &&
        esStr(e.formacion) &&
        esNum(e.tasaExito) &&
        esNum(e.yardasPromedio) &&
        esEntero(e.nMuestra),
    ) &&
    esObj(t) &&
    esStrArr(t.formacion) &&
    esStrArr(t.personal) &&
    esStrArr(t.alineacion)
  );
};

export function esSimilares(x: unknown): x is Similares {
  return (
    esObj(x) &&
    esArr(x.similares, esJugadaSimilar) &&
    esArr(x.sugerencias, esSugerencia) &&
    esStrArr(x.criteriosRelajados) &&
    esComparacion(x.comparacion)
  );
}

export function esRecomendacion(x: unknown): x is Recomendacion {
  return esObj(x) && esStr(x.recomendacion) && typeof x.generado_por_ia === 'boolean';
}
