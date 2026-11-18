import type { Jugada, Recomendacion, Sugerencia } from './tipos';
import { esRecomendacion } from './tipos';

export interface OpcionesObtener<T> {
  señal?: AbortSignal;
  timeoutMs?: number;
  validar?: (x: unknown) => x is T;
}

const MSG_DATOS = 'No se pudieron leer los datos.';
const MSG_TIEMPO = 'La solicitud tardó demasiado. Intenta de nuevo.';
const MSG_RED = 'No se pudo conectar con el servidor.';

/** Error de red, tiempo agotado, estado no 2xx o forma de datos inválida. */
export class ErrorApi extends Error {
  constructor(mensaje: string, public estado?: number) {
    super(mensaje);
    this.name = 'ErrorApi';
  }
}

async function solicitar(
  ruta: string,
  init: RequestInit,
  señal?: AbortSignal,
  timeoutMs?: number,
): Promise<unknown> {
  const control = new AbortController();
  let vencido = false;
  const alAbortar = () => control.abort();
  if (señal) {
    if (señal.aborted) control.abort();
    else señal.addEventListener('abort', alAbortar, { once: true });
  }
  const temporizador =
    timeoutMs !== undefined
      ? setTimeout(() => {
          vencido = true;
          control.abort();
        }, timeoutMs)
      : undefined;

  try {
    const respuesta = await fetch('api/' + ruta.replace(/^\/+/, ''), { ...init, signal: control.signal });
    if (!respuesta.ok) throw new ErrorApi(`Error del servidor (${respuesta.status}).`, respuesta.status);
    try {
      return await respuesta.json();
    } catch {
      throw new ErrorApi(MSG_DATOS, respuesta.status);
    }
  } catch (e) {
    if (e instanceof ErrorApi) throw e;
    if (vencido) throw new ErrorApi(MSG_TIEMPO);
    // Cancelación del llamador: se propaga tal cual para que pueda ignorarla.
    if (señal?.aborted) throw e;
    throw new ErrorApi(MSG_RED);
  } finally {
    if (temporizador !== undefined) clearTimeout(temporizador);
    señal?.removeEventListener('abort', alAbortar);
  }
}

export async function obtener<T>(ruta: string, opciones: OpcionesObtener<T> = {}): Promise<T> {
  const datos = await solicitar(ruta, {}, opciones.señal, opciones.timeoutMs);
  if (opciones.validar && !opciones.validar(datos)) throw new ErrorApi(MSG_DATOS);
  return datos as T;
}

export function publicar(
  jugada: Jugada,
  sugerencias: Sugerencia[],
  opciones: { señal?: AbortSignal; timeoutMs?: number } = {},
): Promise<Recomendacion> {
  return solicitar(
    'recomendacion',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jugada, sugerencias }),
    },
    opciones.señal,
    opciones.timeoutMs ?? 25000,
  ).then((datos) => {
    if (!esRecomendacion(datos)) throw new ErrorApi(MSG_DATOS);
    return datos;
  });
}
