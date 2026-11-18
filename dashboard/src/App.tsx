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
    <main className="mx-auto max-w-7xl space-y-4 p-4">
      <header>
        <h1 className="text-2xl font-bold">Entrenador de jugadas fallidas</h1>
        <p className="text-sm text-gray-600">
          Revisa jugadas de pase fallidas y compáralas con jugadas efectivas de otros equipos.
        </p>
      </header>

      <Filtros valor={filtros} onCambio={setFiltros} />

      <div className="grid gap-4 lg:grid-cols-2">
        <ListaJugadas filtros={filtros} seleccionada={seleccion} onSeleccionar={alSeleccionar} />
        <Repeticion jugada={seleccion} />
      </div>

      <Similares jugada={seleccion} onSugerencias={setSugerencias} />
      <Recomendacion jugada={seleccion} sugerencias={sugerencias} />
    </main>
  )
}
