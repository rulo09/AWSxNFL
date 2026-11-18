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
    <section aria-label="Recomendación" className="rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold">Recomendación</h2>
      <button
        type="button"
        onClick={generar}
        disabled={enCurso || !jugada}
        className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
      >
        Generar recomendación
      </button>
      {enCurso && (
        <p role="status" className="mt-2 text-sm text-gray-600">
          Generando recomendación
        </p>
      )}
      {estado.tipo === 'error' && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          Recomendación no disponible
        </p>
      )}
      {estado.tipo === 'listo' && (
        <div className="mt-2">
          <p className="text-xs font-medium text-gray-600">
            {estado.datos.generado_por_ia ? 'Generado con IA' : 'Resumen automático (IA no disponible)'}
          </p>
          <p className="whitespace-pre-line text-sm">{estado.datos.recomendacion}</p>
        </div>
      )}
    </section>
  )
}
