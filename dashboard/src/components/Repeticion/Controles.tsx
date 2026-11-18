interface Props {
  reproduciendo: boolean
  deshabilitado: boolean
  onReproducir(): void
  onPausar(): void
}

export default function Controles({ reproduciendo, deshabilitado, onReproducir, onPausar }: Props) {
  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={onReproducir}
        disabled={deshabilitado || reproduciendo}
        className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-offset-1 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        Reproducir
      </button>
      <button
        type="button"
        onClick={onPausar}
        disabled={deshabilitado || !reproduciendo}
        className="rounded-lg border border-slate-300 bg-white px-4 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Pausar
      </button>
    </div>
  )
}
