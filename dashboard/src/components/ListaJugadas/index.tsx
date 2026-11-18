import { useEffect, useState } from 'react'
import { obtener } from '../../api/cliente'
import { esJugada } from '../../api/tipos'
import type { Filtros, Jugada } from '../../api/tipos'

interface Props {
  filtros: Filtros
  seleccionada: Jugada | null
  onSeleccionar: (j: Jugada) => void
}

const SIN_DATO = 'Sin dato'

const esListaJugadas = (x: unknown): x is Jugada[] => Array.isArray(x) && x.every(esJugada)

function construirRuta(f: Filtros): string {
  const p = new URLSearchParams()
  if (f.down !== undefined) p.set('down', String(f.down))
  if (f.razon) p.set('razon', f.razon)
  if (f.equipo) p.set('equipo', f.equipo)
  const q = p.toString()
  return q ? `jugadas?${q}` : 'jugadas'
}

export default function ListaJugadas({ filtros, seleccionada, onSeleccionar }: Props) {
  // null = aún no hay una respuesta válida; se conserva la última lista válida.
  const [jugadas, setJugadas] = useState<Jugada[] | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { down, razon, equipo } = filtros

  useEffect(() => {
    const control = new AbortController()
    setCargando(true)
    obtener<Jugada[]>(construirRuta({ down, razon, equipo }), {
      señal: control.signal,
      timeoutMs: 10000,
      validar: esListaJugadas,
    })
      .then((lista) => {
        if (control.signal.aborted) return
        setJugadas(lista)
        setError(null)
        setCargando(false)
      })
      .catch(() => {
        if (control.signal.aborted) return
        setError('No se pudieron cargar las jugadas. Se conserva la lista anterior.')
        setCargando(false)
      })
    return () => control.abort()
  }, [down, razon, equipo])

  const esSeleccionada = (j: Jugada) =>
    seleccionada !== null && seleccionada.gameId === j.gameId && seleccionada.playId === j.playId

  return (
    <section aria-label="Jugadas fallidas" className="rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold">Jugadas fallidas</h2>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {cargando && (
        <p role="status" className="mt-2 text-sm text-gray-600">
          Cargando jugadas
        </p>
      )}
      {jugadas !== null && jugadas.length === 0 && (
        <p className="mt-2 text-sm text-gray-600">No hay jugadas fallidas con estos filtros</p>
      )}
      {jugadas !== null && jugadas.length > 0 && (
        <ul role="listbox" aria-label="Lista de jugadas fallidas" className="mt-2 max-h-96 space-y-1 overflow-y-auto">
          {jugadas.map((j) => {
            const activa = esSeleccionada(j)
            return (
              <li
                key={`${j.gameId}-${j.playId}`}
                role="option"
                aria-selected={activa}
                tabIndex={0}
                onClick={() => onSeleccionar(j)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSeleccionar(j)
                  }
                }}
                className={`cursor-pointer rounded border p-2 text-sm ${
                  activa ? 'border-blue-600 bg-blue-100' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="font-medium">
                  {j.equipo} vs {j.rival}: down {j.down}, {j.yardsToGo} yardas por ganar
                </div>
                <div className="text-gray-700">{j.descripcion}</div>
                <div className="text-xs text-gray-600">
                  Formación: {j.formacion ?? SIN_DATO} · Personal: {j.personal ?? SIN_DATO} · Cobertura:{' '}
                  {j.cobertura ?? SIN_DATO}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
