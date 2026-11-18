import { useEffect, useRef, useState } from 'react'
import { obtener } from '../../api/cliente'
import { esSimilares } from '../../api/tipos'
import Comparacion from './Comparacion'
import type { Jugada, Similares as SimilaresDatos, Sugerencia } from '../../api/tipos'

interface Props {
  jugada: Jugada | null
  onSugerencias: (s: Sugerencia[]) => void
}

const SIN_DATO = 'Sin dato'
const TIMEOUT_MS = 10000

export default function Similares({ jugada, onSugerencias }: Props) {
  const [datos, setDatos] = useState<SimilaresDatos | null>(null)
  const [mismaCobertura, setMismaCobertura] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const alSugerencias = useRef(onSugerencias)
  alSugerencias.current = onSugerencias
  const claveAnterior = useRef<string | null>(null)

  const gameId = jugada?.gameId
  const playId = jugada?.playId

  useEffect(() => {
    const clave = gameId === undefined ? null : `${gameId}/${playId}`
    const cambioJugada = clave !== claveAnterior.current
    claveAnterior.current = clave
    if (cambioJugada) {
      setDatos(null)
      alSugerencias.current([])
    }
    setError(null)
    if (clave === null) {
      setCargando(false)
      return
    }

    const control = new AbortController()
    setCargando(true)
    const ruta = `jugadas/${gameId}/${playId}/similares` + (mismaCobertura ? '?misma_cobertura=true' : '')
    obtener<SimilaresDatos>(ruta, { señal: control.signal, timeoutMs: TIMEOUT_MS, validar: esSimilares })
      .then((d) => {
        if (control.signal.aborted) return
        setDatos(d)
        setCargando(false)
        alSugerencias.current(d.sugerencias)
      })
      .catch((e: unknown) => {
        if (control.signal.aborted) return
        setCargando(false)
        setError(e instanceof Error ? e.message : 'No se pudieron leer los datos.')
      })
    return () => control.abort()
  }, [gameId, playId, mismaCobertura])

  return (
    <section aria-label="Jugadas similares" className="rounded border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold">Jugadas similares efectivas</h2>
      {!jugada ? (
        <p className="text-sm text-gray-600">Selecciona una jugada fallida.</p>
      ) : (
        <>
          <label className="my-2 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={mismaCobertura}
              onChange={(e) => setMismaCobertura(e.target.checked)}
            />
            Misma cobertura
          </label>
          {cargando && <p className="text-sm text-gray-600">Cargando jugadas similares...</p>}
          {error && (
            <p role="alert" className="text-sm text-red-700">
              {error}
            </p>
          )}
          {datos && (
            <>
              {datos.criteriosRelajados.length > 0 && (
                <p className="mb-2 text-sm text-amber-800">
                  Criterios relajados: {datos.criteriosRelajados.join(', ')}
                </p>
              )}
              {datos.similares.length === 0 ? (
                <p className="text-sm text-gray-600">No hay jugadas similares efectivas.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="p-1">Equipo</th>
                        <th className="p-1">Rival</th>
                        <th className="p-1">Yardas por ganar</th>
                        <th className="p-1">Resultado (yardas)</th>
                        <th className="p-1">Formación</th>
                        <th className="p-1">Personal</th>
                        <th className="p-1">Cobertura</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datos.similares.map((s) => (
                        <tr key={`${s.gameId}-${s.playId}`} className="border-b">
                          <td className="p-1">{s.equipo}</td>
                          <td className="p-1">{s.rival}</td>
                          <td className="p-1">{s.yardsToGo}</td>
                          <td className="p-1">{s.playResult}</td>
                          <td className="p-1">{s.formacion ?? SIN_DATO}</td>
                          <td className="p-1">{s.personal ?? SIN_DATO}</td>
                          <td className="p-1">{s.cobertura ?? SIN_DATO}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <Comparacion comparacion={datos.comparacion} />
              <h3 className="mt-4 font-semibold">Sugerencias</h3>
              {datos.sugerencias.length === 0 ? (
                <p className="text-sm text-gray-600">No hay sugerencias disponibles</p>
              ) : (
                <ul className="space-y-2">
                  {datos.sugerencias.map((s, i) => (
                    <li key={i} className="rounded border border-gray-200 p-2 text-sm">
                      <p className="font-medium">{s.texto}</p>
                      <p className="text-gray-700">{s.evidencia}</p>
                      <p className="text-gray-700">
                        Muestra: {s.nMuestra} jugadas. Confianza: <strong>{s.confianza}</strong>
                        {s.confianza === 'baja' && (
                          <span className="ml-2 rounded bg-amber-100 px-1 text-amber-900">Muestra pequeña</span>
                        )}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}
    </section>
  )
}
