import { useEffect, useRef, useState } from 'react'
import { publicar } from '../../api/cliente'
import type { Jugada, Recomendacion as RecomendacionResp, Sugerencia } from '../../api/tipos'

interface Props {
  jugada: Jugada | null
  sugerencias: Sugerencia[]
}

type Estado =
  | { tipo: 'inicial' }
  | { tipo: 'pendiente' }
  | { tipo: 'listo'; datos: RecomendacionResp }
  | { tipo: 'error' }

const TIMEOUT_MS = 25000

export default function Recomendacion({ jugada, sugerencias }: Props) {
  const [estado, setEstado] = useState<Estado>({ tipo: 'inicial' })
  const control = useRef<AbortController | null>(null)
  const pendiente = useRef(false)
  // Identificador de solicitud: una respuesta solo se aplica si sigue vigente.
  const vigente = useRef(0)

  const gameId = jugada?.gameId
  const playId = jugada?.playId

  // Al cambiar la jugada seleccionada: limpia y descarta la solicitud en curso.
  useEffect(() => {
    vigente.current += 1
    control.current?.abort()
    control.current = null
    pendiente.current = false
    setEstado({ tipo: 'inicial' })
  }, [gameId, playId])

  useEffect(
    () => () => {
      vigente.current += 1
      control.current?.abort()
    },
    [],
  )

  const generar = () => {
    if (!jugada || pendiente.current) return
    pendiente.current = true
    const id = ++vigente.current
    const ctl = new AbortController()
    control.current = ctl
    setEstado({ tipo: 'pendiente' })
    publicar(jugada, sugerencias, { señal: ctl.signal, timeoutMs: TIMEOUT_MS })
      .then((datos) => {
        if (id !== vigente.current) return
        pendiente.current = false
        setEstado({ tipo: 'listo', datos })
      })
      .catch(() => {
        if (id !== vigente.current) return
        pendiente.current = false
        setEstado({ tipo: 'error' })
      })
  }

  const enCurso = estado.tipo === 'pendiente'

  return (
    <section aria-label="Recomendación" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 before:h-5 before:w-1 before:rounded-full before:bg-indigo-500 before:content-['']">Recomendación</h2>
      <button
        type="button"
        onClick={generar}
        disabled={enCurso || !jugada}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:opacity-70"
      >
        Generar recomendación
      </button>
      {enCurso && (
        <p role="status" className="mt-3 animate-pulse text-sm text-slate-600">
          Generando recomendación
        </p>
      )}
      {estado.tipo === 'error' && (
        <p role="alert" className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          Recomendación no disponible
        </p>
      )}
      {estado.tipo === 'listo' && (
        <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/60 p-4">
          <p className="mb-2 inline-block rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800">
            {estado.datos.generado_por_ia ? 'Generado con IA' : 'Resumen automático (IA no disponible)'}
          </p>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-800">{estado.datos.recomendacion}</p>
        </div>
      )}
    </section>
  )
}
