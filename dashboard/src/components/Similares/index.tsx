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
    <section aria-label="Jugadas similares" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-800 before:h-5 before:w-1 before:rounded-full before:bg-indigo-500 before:content-['']">Jugadas similares efectivas</h2>
      {!jugada ? (
        <p className="text-sm text-slate-600">Selecciona una jugada fallida.</p>
      ) : (
        <>
          <label className="mb-3 flex w-fit cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
            <input
              className="h-4 w-4 rounded border-slate-300 accent-indigo-600 focus:ring-2 focus:ring-indigo-300"
              type="checkbox"
              checked={mismaCobertura}
              onChange={(e) => setMismaCobertura(e.target.checked)}
            />
            Misma cobertura
          </label>
          {cargando && <p className="text-sm text-slate-600">Cargando jugadas similares...</p>}
          {error && (
            <p role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          )}
          {datos && (
            <>
              {datos.criteriosRelajados.length > 0 && (
                <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Criterios relajados: {datos.criteriosRelajados.join(', ')}
                </p>
              )}
              {datos.similares.length === 0 ? (
                <p className="text-sm text-slate-600">No hay jugadas similares efectivas.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-sm text-slate-700">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
                        <th className="px-3 py-2 font-semibold">Equipo</th>
                        <th className="px-3 py-2 font-semibold">Rival</th>
                        <th className="px-3 py-2 font-semibold">Yardas por ganar</th>
                        <th className="px-3 py-2 font-semibold">Resultado (yardas)</th>
                        <th className="px-3 py-2 font-semibold">Formación</th>
                        <th className="px-3 py-2 font-semibold">Personal</th>
                        <th className="px-3 py-2 font-semibold">Cobertura</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datos.similares.map((s) => (
                        <tr key={`${s.gameId}-${s.playId}`} className="border-b border-slate-100 odd:bg-white even:bg-slate-50 transition hover:bg-indigo-50">
                          <td className="px-3 py-2">{s.equipo}</td>
                          <td className="px-3 py-2">{s.rival}</td>
                          <td className="px-3 py-2">{s.yardsToGo}</td>
                          <td className="px-3 py-2">{s.playResult}</td>
                          <td className="px-3 py-2">{s.formacion ?? SIN_DATO}</td>
                          <td className="px-3 py-2">{s.personal ?? SIN_DATO}</td>
                          <td className="px-3 py-2">{s.cobertura ?? SIN_DATO}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <Comparacion comparacion={datos.comparacion} />
              <h3 className="mt-6 text-sm font-semibold uppercase tracking-wide text-slate-500">Sugerencias</h3>
              {datos.sugerencias.length === 0 ? (
                <p className="text-sm text-slate-600">No hay sugerencias disponibles</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {datos.sugerencias.map((s, i) => (
                    <li key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                      <p className="font-semibold text-slate-900">{s.texto}</p>
                      <p className="text-slate-700">{s.evidencia}</p>
                      <p className="text-slate-700">
                        Muestra: {s.nMuestra} jugadas. Confianza: <strong className={`ml-1 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                          s.confianza === 'alta'
                            ? 'bg-emerald-100 text-emerald-800'
                            : s.confianza === 'media'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                        }`}>{s.confianza}</strong>
                        {s.confianza === 'baja' && (
                          <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Muestra pequeña</span>
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
