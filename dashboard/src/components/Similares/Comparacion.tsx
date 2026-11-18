import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Comparacion as ComparacionDatos, ValorDistribucion } from '../../api/tipos'

interface Props {
  comparacion: ComparacionDatos
}

const SIN_DATO = 'Sin dato'

function Distribucion({ titulo, valores }: { titulo: string; valores: ValorDistribucion[] }) {
  return (
    <div>
      <h5 className="text-sm font-medium">{titulo}</h5>
      {valores.length === 0 ? (
        <p className="text-sm text-gray-600">{SIN_DATO}</p>
      ) : (
        <ul className="text-sm text-gray-700">
          {valores.map((v) => (
            <li key={v.valor}>
              {v.valor}: {v.porcentaje.toFixed(1)}% (n={v.nMuestra})
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Lista({ valores }: { valores: string[] }) {
  return valores.length === 0 ? (
    <span>{SIN_DATO}</span>
  ) : (
    <span>{valores.join(', ')}</span>
  )
}

export default function Comparacion({ comparacion }: Props) {
  const { solicitada, distribucion, alineaciones, rutasDisponibles, exitoPorFormacion, top3 } = comparacion

  return (
    <div className="mt-4">
      <h3 className="font-semibold">Comparación con jugadas similares</h3>
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        <div className="rounded border border-gray-200 p-2">
          <h4 className="font-medium">Jugada solicitada</h4>
          <dl className="text-sm">
            <dt className="font-medium">Formación</dt>
            <dd>{solicitada.formacion ?? SIN_DATO}</dd>
            <dt className="font-medium">Personal</dt>
            <dd>{solicitada.personal ?? SIN_DATO}</dd>
            <dt className="font-medium">Alineación</dt>
            <dd>{solicitada.alineacion.length > 0 ? solicitada.alineacion.join(', ') : SIN_DATO}</dd>
          </dl>
        </div>
        <div className="rounded border border-gray-200 p-2">
          <h4 className="font-medium">Jugadas similares efectivas</h4>
          <p className="text-sm">
            <span className="font-medium">Top 3 formación:</span> <Lista valores={top3.formacion} />
          </p>
          <p className="text-sm">
            <span className="font-medium">Top 3 personal:</span> <Lista valores={top3.personal} />
          </p>
          <p className="text-sm">
            <span className="font-medium">Top 3 alineación:</span> <Lista valores={top3.alineacion} />
          </p>
          <Distribucion titulo="Formación" valores={distribucion.formacion} />
          <Distribucion titulo="Personal" valores={distribucion.personal} />
          {distribucion.cobertura.length > 0 && (
            <Distribucion titulo="Cobertura" valores={distribucion.cobertura} />
          )}
          <div>
            <h5 className="text-sm font-medium">Alineación (rutas)</h5>
            {!rutasDisponibles ? (
              <p role="status" className="text-sm text-amber-800">
                No hay datos de rutas para esta jugada.
              </p>
            ) : alineaciones.length === 0 ? (
              <p className="text-sm text-gray-600">{SIN_DATO}</p>
            ) : (
              <ul className="text-sm text-gray-700">
                {alineaciones.map((a) => (
                  <li key={`${a.posicion}-${a.rol}`}>
                    {a.posicion} ({a.rol}): {a.conteo} jugadas
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <h4 className="mt-4 font-medium">Tasa de éxito por formación</h4>
      {exitoPorFormacion.length === 0 ? (
        <p className="text-sm text-gray-600">No hay datos de éxito por formación.</p>
      ) : (
        <>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={exitoPorFormacion} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="formacion" tick={{ fontSize: 12 }} />
                <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(v: unknown) => [`${Number(v).toFixed(1)}%`, 'Tasa de éxito']}
                  labelFormatter={(l: unknown, p: ReadonlyArray<{ payload?: { nMuestra?: number } }>) =>
                    `${String(l)} (n=${p?.[0]?.payload?.nMuestra ?? 0})`
                  }
                />
                <Bar dataKey="tasaExito" name="Tasa de éxito" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="text-sm text-gray-700">
            {exitoPorFormacion.map((e) => (
              <li key={e.formacion}>
                {e.formacion}: éxito {e.tasaExito.toFixed(1)}%, yardas promedio {e.yardasPromedio.toFixed(1)} (n=
                {e.nMuestra})
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-2 text-xs text-gray-700">
        Los datos contienen solo jugadas de pase; 'corredores' se refiere a RB y receptores en ruta
      </p>
    </div>
  )
}
