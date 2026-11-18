import { useEffect, useState } from 'react'
import { obtener } from '../../api/cliente'
import type { Filtros as FiltrosValor } from '../../api/tipos'

interface Props {
  valor: FiltrosValor
  onCambio: (f: FiltrosValor) => void
}

interface Equipo {
  abbr: string
  nombre: string | null
}

interface Opciones {
  downs: number[]
  razones: string[]
  equipos: Equipo[]
}

const VACIAS: Opciones = { downs: [], razones: [], equipos: [] }

const ETIQUETA_RAZON: Record<string, string> = {
  incompleto: 'Pase incompleto',
  intercepcion: 'Intercepción',
  sack: 'Captura (sack)',
  sin_conversion: 'Sin conversión',
  perdida_de_yardas: 'Pérdida de yardas',
}

function esOpciones(x: unknown): x is Opciones {
  if (typeof x !== 'object' || x === null) return false
  const o = x as Record<string, unknown>
  return (
    Array.isArray(o.downs) &&
    o.downs.every((d) => typeof d === 'number') &&
    Array.isArray(o.razones) &&
    o.razones.every((r) => typeof r === 'string') &&
    Array.isArray(o.equipos) &&
    o.equipos.every((e) => {
      if (typeof e !== 'object' || e === null) return false
      const q = e as Record<string, unknown>
      return typeof q.abbr === 'string' && (q.nombre === null || typeof q.nombre === 'string')
    })
  )
}

function etiquetaEquipo(e: Equipo): string {
  return e.nombre ? `${e.nombre} (${e.abbr})` : e.abbr
}

const CLASE_SELECT = 'rounded border border-gray-300 bg-white px-2 py-1 text-sm'

export default function Filtros({ valor, onCambio }: Props) {
  const [opciones, setOpciones] = useState<Opciones>(VACIAS)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const control = new AbortController()
    obtener<Opciones>('filtros', { señal: control.signal, timeoutMs: 10000, validar: esOpciones })
      .then((o) => {
        setOpciones(o)
        setError(null)
      })
      .catch(() => {
        if (control.signal.aborted) return
        setOpciones(VACIAS)
        setError('No se pudieron cargar las opciones de filtros.')
      })
    return () => control.abort()
  }, [])

  const cambiar = (campo: keyof FiltrosValor, texto: string) => {
    const siguiente: FiltrosValor = { ...valor }
    if (texto === '') {
      delete siguiente[campo]
    } else if (campo === 'down') {
      siguiente.down = Number(texto)
    } else {
      siguiente[campo] = texto
    }
    onCambio(siguiente)
  }

  return (
    <section aria-label="Filtros" className="rounded border border-gray-200 bg-white p-4">
      <h2 className="mb-2 text-lg font-semibold">Filtros</h2>
      <div className="flex flex-wrap gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Down
          <select
            className={CLASE_SELECT}
            value={valor.down === undefined ? '' : String(valor.down)}
            onChange={(e) => cambiar('down', e.target.value)}
          >
            <option value="">Todos</option>
            {opciones.downs.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Razón del fallo
          <select
            className={CLASE_SELECT}
            value={valor.razon ?? ''}
            onChange={(e) => cambiar('razon', e.target.value)}
          >
            <option value="">Todas</option>
            {opciones.razones.map((r) => (
              <option key={r} value={r}>
                {ETIQUETA_RAZON[r] ?? r}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Equipo
          <select
            className={CLASE_SELECT}
            value={valor.equipo ?? ''}
            onChange={(e) => cambiar('equipo', e.target.value)}
          >
            <option value="">Todos</option>
            {opciones.equipos.map((e) => (
              <option key={e.abbr} value={e.abbr}>
                {etiquetaEquipo(e)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </section>
  )
}
