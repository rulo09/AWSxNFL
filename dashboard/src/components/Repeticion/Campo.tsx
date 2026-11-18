import type { Cuadro } from '../../api/tipos'

interface Props {
  cuadro: Cuadro | null
}

const ANCHO = 120
const ALTO = 53.3
const COLOR_OFENSIVA = '#2563eb'
const COLOR_DEFENSIVA = '#dc2626'

const lineasYardas: number[] = []
for (let x = 15; x <= 105; x += 5) lineasYardas.push(x)

/** Campo 2D en SVG (120 x 53.3 yardas, con zonas de anotación) y jugadores del cuadro dado. */
export default function Campo({ cuadro }: Props) {
  return (
    <svg
      viewBox={`0 0 ${ANCHO} ${ALTO}`}
      role="img"
      aria-label="Campo de futbol americano con la posición de los jugadores"
      className="w-full rounded-lg border border-emerald-900/30 bg-emerald-700 shadow-inner"
    >
      <defs>
        <linearGradient id="cesped" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2f8f4e" />
          <stop offset="1" stopColor="#237a40" />
        </linearGradient>
      </defs>
      <rect x={0} y={0} width={ANCHO} height={ALTO} fill="url(#cesped)" />
      {Array.from({ length: 10 }, (_, i) => (
        <rect key={`franja${i}`} x={10 + i * 10} y={0} width={10} height={ALTO} fill={i % 2 === 0 ? '#ffffff' : '#000000'} fillOpacity={0.04} />
      ))}
      <rect x={0} y={0} width={10} height={ALTO} fill="#1e3a8a" fillOpacity={0.55} />
      <rect x={110} y={0} width={10} height={ALTO} fill="#7f1d1d" fillOpacity={0.55} />
      {[10, 110].map((x) => (
        <line key={`gol${x}`} x1={x} y1={0} x2={x} y2={ALTO} stroke="#ffffff" strokeWidth={0.5} />
      ))}
      {lineasYardas.map((x) => (
        <line
          key={x}
          x1={x}
          y1={0}
          x2={x}
          y2={ALTO}
          stroke="#ffffff"
          strokeOpacity={x % 10 === 0 ? 0.9 : 0.5}
          strokeWidth={x % 10 === 0 ? 0.3 : 0.12}
        />
      ))}
      <line x1={0} y1={0.25} x2={ANCHO} y2={0.25} stroke="#ffffff" strokeWidth={0.5} />
      <line x1={0} y1={ALTO - 0.25} x2={ANCHO} y2={ALTO - 0.25} stroke="#ffffff" strokeWidth={0.5} />
      {cuadro?.jugadores.map((j) => (
        <circle
          key={j.nflId}
          cx={j.x}
          cy={j.y}
          r={1}
          fill={j.equipo === 'ofensiva' ? COLOR_OFENSIVA : COLOR_DEFENSIVA}
          stroke="#ffffff"
          strokeWidth={0.3}
        />
      ))}
      {cuadro?.balon && (
        <ellipse
          cx={cuadro.balon.x}
          cy={cuadro.balon.y}
          rx={0.9}
          ry={0.5}
          fill="#92400e"
          stroke="#ffffff"
          strokeWidth={0.15}
        />
      )}
    </svg>
  )
}
