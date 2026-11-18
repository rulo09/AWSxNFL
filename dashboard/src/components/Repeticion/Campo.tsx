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
      className="w-full rounded border border-gray-300 bg-green-600"
    >
      <rect x={0} y={0} width={10} height={ALTO} fill="#14532d" />
      <rect x={110} y={0} width={10} height={ALTO} fill="#14532d" />
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
          r={0.9}
          fill={j.equipo === 'ofensiva' ? COLOR_OFENSIVA : COLOR_DEFENSIVA}
          stroke="#ffffff"
          strokeWidth={0.2}
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
