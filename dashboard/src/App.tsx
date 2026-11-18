import { useCallback, useState } from 'react'
import type { Filtros as FiltrosValor, Jugada, Sugerencia } from './api/tipos'
import Filtros from './components/Filtros'
import ListaJugadas from './components/ListaJugadas'
import Recomendacion from './components/Recomendacion'
import Repeticion from './components/Repeticion'
import Similares from './components/Similares'

export default function App() {
  const [filtros, setFiltros] = useState<FiltrosValor>({})
  const [seleccion, setSeleccion] = useState<Jugada | null>(null)
  const [sugerencias, setSugerencias] = useState<Sugerencia[]>([])

  const alSeleccionar = useCallback((j: Jugada) => {
    // Similares vacía las sugerencias cuando cambia la jugada; aquí no se tocan
    // para no perderlas al volver a pulsar la jugada ya seleccionada.
    setSeleccion(j)
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
    <header className="bg-gradient-to-r from-navy-900 to-navy-700 shadow-lg">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Entrenador de jugadas fallidas</h1>
        <p className="mt-1 text-sm text-indigo-200">
          Revisa jugadas de pase fallidas y compáralas con jugadas efectivas de otros equipos.
        </p>
      </div>
    </header>
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">

      <Filtros valor={filtros} onCambio={setFiltros} />

      <div className="grid gap-6 lg:grid-cols-2">
        <ListaJugadas filtros={filtros} seleccionada={seleccion} onSeleccionar={alSeleccionar} />
        <Repeticion jugada={seleccion} />
      </div>

      <Similares jugada={seleccion} onSugerencias={setSugerencias} />
      <Recomendacion jugada={seleccion} sugerencias={sugerencias} />
    </main>
    </div>
  )
}
