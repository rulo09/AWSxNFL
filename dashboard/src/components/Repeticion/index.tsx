import { useEffect, useRef, useState } from 'react'
import type { Jugada, Tracking } from '../../api/tipos'
import { esTracking } from '../../api/tipos'
import { obtener } from '../../api/cliente'
import Campo from './Campo'
import Controles from './Controles'
import LineaTiempo from './LineaTiempo'

interface Props {
  jugada: Jugada | null
}

type Estado = 'cargando' | 'error' | 'listo' | 'sinDatos'

const TIEMPO_MAX_MS = 10000
const MSG_ERROR = 'No se pudo cargar la repetición. Intenta de nuevo.'
const MSG_SIN_DATOS = 'Esta jugada no tiene datos de tracking.'

export default function Repeticion({ jugada }: Props) {
  const [tracking, setTracking] = useState<Tracking | null>(null)
  const [estado, setEstado] = useState<Estado>('cargando')
  const [frameActual, setFrameActual] = useState(0)
  const [reproduciendo, setReproduciendo] = useState(false)

  const gameId = jugada?.gameId
  const playId = jugada?.playId

  useEffect(() => {
    // Al cambiar la jugada se descartan los datos anteriores y se vuelve al cuadro 0.
    setTracking(null)
    setFrameActual(0)
    setReproduciendo(false)
    if (gameId === undefined || playId === undefined) {
      setEstado('sinDatos')
      return
    }
    setEstado('cargando')
    const control = new AbortController()
    obtener<Tracking>(`jugadas/${gameId}/${playId}/tracking`, {
      señal: control.signal,
      timeoutMs: TIEMPO_MAX_MS,
      validar: esTracking,
    })
      .then((datos) => {
        if (control.signal.aborted) return
        setTracking(datos)
        setEstado(datos.cuadros.length === 0 ? 'sinDatos' : 'listo')
      })
      .catch(() => {
        if (control.signal.aborted) return
        setEstado('error')
      })
    return () => control.abort()
  }, [gameId, playId])

  const cuadros = tracking?.cuadros ?? []
  const total = cuadros.length

  const frameRef = useRef(frameActual)
  frameRef.current = frameActual

  // Un único intervalo, activo solo mientras se reproduce.
  useEffect(() => {
    if (!reproduciendo) return
    const id = setInterval(() => {
      const siguiente = frameRef.current + 1
      if (siguiente >= total - 1) {
        setFrameActual(Math.max(total - 1, 0))
        setReproduciendo(false)
      } else {
        setFrameActual(siguiente)
      }
    }, 100)
    return () => clearInterval(id)
  }, [reproduciendo, total])

  const reproducir = () => {
    if (total === 0) return
    if (frameActual >= total - 1) setFrameActual(0)
    setReproduciendo(true)
  }

  const cuadro = cuadros[Math.min(frameActual, cuadros.length - 1)] ?? null

  return (
    <section aria-label="Repetición" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 before:h-5 before:w-1 before:rounded-full before:bg-indigo-500 before:content-['']">Repetición de la jugada</h2>
      {jugada === null && <p className="text-sm text-slate-600">Selecciona una jugada para ver la repetición.</p>}
      {jugada !== null && estado === 'cargando' && (
        <p role="status" className="text-sm text-slate-600">Cargando repetición</p>
      )}
      {jugada !== null && estado === 'error' && (
        <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{MSG_ERROR}</p>
      )}
      {jugada !== null && estado === 'sinDatos' && <p className="text-sm text-slate-600">{MSG_SIN_DATOS}</p>}
      {jugada !== null && estado === 'listo' && <Campo cuadro={cuadro} />}
      {jugada !== null && (estado === 'listo' || estado === 'sinDatos') && (
        <div className="mt-3 space-y-2">
          <Controles
            reproduciendo={reproduciendo}
            deshabilitado={total === 0}
            onReproducir={reproducir}
            onPausar={() => setReproduciendo(false)}
          />
          <LineaTiempo
            cuadros={cuadros}
            eventos={tracking?.eventos ?? []}
            frameActual={frameActual}
            onCambiar={setFrameActual}
          />
        </div>
      )}
    </section>
  )
}
