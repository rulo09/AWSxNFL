import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Comparacion as ComparacionDatos, ValorDistribucion } from '../../api/tipos'

interface Props {
  comparacion: ComparacionDatos
}

const SIN_DATO = 'Sin dato'

function Distribucion({ titulo, valores }: { titulo: string; valores: ValorDistribucion[] }) {
  return (
    <div>
      <h5 className="mt-2 text-sm font-semibold text-slate-800">{titulo}</h5>
      {valores.length === 0 ? (
        <p className="text-sm text-slate-600">{SIN_DATO}</p>
      ) : (
        <ul className="text-sm text-slate-700">
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
    <div className="mt-6 border-t border-slate-200 pt-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Comparación con jugadas similares</h3>
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h4 className="mb-2 font-semibold text-slate-900">Jugada solicitada</h4>
          <dl className="text-sm">
            <dt className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">Formación</dt>
            <dd>{solicitada.formacion ?? SIN_DATO}</dd>
            <dt className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">Personal</dt>
            <dd>{solicitada.personal ?? SIN_DATO}</dd>
            <dt className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">Alineación</dt>
            <dd>{solicitada.alineacion.length > 0 ? solicitada.alineacion.join(', ') : SIN_DATO}</dd>
          </dl>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h4 className="mb-2 font-semibold text-slate-900">Jugadas similares efectivas</h4>
          <p className="text-sm">
            <span className="font-medium text-slate-800">Top 3 formación:</span> <Lista valores={top3.formacion} />
          </p>
          <p className="text-sm">
            <span className="font-medium text-slate-800">Top 3 personal:</span> <Lista valores={top3.personal} />
          </p>
          <p className="text-sm">
            <span className="font-medium text-slate-800">Top 3 alineación:</span> <Lista valores={top3.alineacion} />
          </p>
          <Distribucion titulo="Formación" valores={distribucion.formacion} />
          <Distribucion titulo="Personal" valores={distribucion.personal} />
          {distribucion.cobertura.length > 0 && (
            <Distribucion titulo="Cobertura" valores={distribucion.cobertura} />
          )}
          <div>
            <h5 className="mt-2 text-sm font-semibold text-slate-800">Alineación (rutas)</h5>
            {!rutasDisponibles ? (
              <p role="status" className="text-sm rounded-lg bg-amber-50 px-3 py-2 text-amber-800">
                No hay datos de rutas para esta jugada.
              </p>
            ) : alineaciones.length === 0 ? (
              <p className="text-sm text-slate-600">{SIN_DATO}</p>
            ) : (
              <ul className="text-sm text-slate-700">
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

      <h4 className="mt-6 mb-2 font-semibold text-slate-900">Tasa de éxito por formación</h4>
      {exitoPorFormacion.length === 0 ? (
        <p className="text-sm text-slate-600">No hay datos de éxito por formación.</p>
      ) : (
        <>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={exitoPorFormacion} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="formacion" tick={{ fontSize: 12 }} />
                <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(v: unknown) => [`${Number(v).toFixed(1)}%`, 'Tasa de éxito']}
                  labelFormatter={(l: unknown, p: ReadonlyArray<{ payload?: { nMuestra?: number } }>) =>
                    `${String(l)} (n=${p?.[0]?.payload?.nMuestra ?? 0})`
                  }
                />
                <Bar dataKey="tasaExito" name="Tasa de éxito" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="text-sm text-slate-700">
            {exitoPorFormacion.map((e) => (
              <li key={e.formacion}>
                {e.formacion}: éxito {e.tasaExito.toFixed(1)}%, yardas promedio {e.yardasPromedio.toFixed(1)} (n=
                {e.nMuestra})
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-2 text-xs text-slate-600">
        Los datos contienen solo jugadas de pase; 'corredores' se refiere a RB y receptores en ruta
      </p>
    </div>
  )
}
