import type { Cuadro, Evento } from '../../api/tipos'

interface Props {
  cuadros: Cuadro[]
  eventos: Evento[]
  frameActual: number
  onCambiar(indice: number): void
}

export function etiquetaEvento(evento: string): string | null {
  if (evento === 'ball_snap') return 'Snap'
  if (evento === 'pass_forward') return 'Pase'
  if (
    evento === 'pass_arrived' ||
    evento.startsWith('pass_outcome_') ||
    evento === 'qb_sack' ||
    evento === 'fumble' ||
    evento === 'tackle' ||
    evento === 'out_of_bounds' ||
    evento === 'touchdown' ||
    evento.startsWith('autoevent_')
  ) {
    return 'Resultado'
  }
  return null
}

export default function LineaTiempo({ cuadros, eventos, frameActual, onCambiar }: Props) {
  const n = cuadros.length
  const ultimo = Math.max(n - 1, 0)

  const marcadores = eventos.flatMap((e, i) => {
    const etiqueta = etiquetaEvento(e.evento)
    const indice = cuadros.findIndex((c) => c.frame === e.frame)
    if (etiqueta === null || indice < 0) return []
    return [{ clave: `${e.evento}-${e.frame}-${i}`, etiqueta, indice }]
  })

  return (
    <div className="mt-2">
      <div className="relative h-7" aria-label="Eventos de la jugada">
        {marcadores.map((m) => (
          <button
            key={m.clave}
            type="button"
            onClick={() => onCambiar(m.indice)}
            title={`${m.etiqueta} (cuadro ${m.indice})`}
            className="absolute -translate-x-1/2 whitespace-nowrap rounded-full border border-amber-300 bg-amber-100 px-2 text-xs font-medium text-amber-900 shadow-sm transition hover:bg-amber-200 focus:outline-none focus:ring-2 focus:ring-amber-300"
            style={{ left: `${ultimo === 0 ? 0 : (m.indice / ultimo) * 100}%` }}
          >
            {m.etiqueta}
          </button>
        ))}
      </div>
      <input
        type="range"
        min={0}
        max={ultimo}
        step={1}
        value={Math.min(frameActual, ultimo)}
        disabled={n === 0}
        onChange={(e) => onCambiar(Number(e.target.value))}
        aria-label="Cuadro de la jugada"
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
      />
    </div>
  )
}
