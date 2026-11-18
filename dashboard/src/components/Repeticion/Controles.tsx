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
        className="rounded bg-blue-700 px-3 py-1 text-sm text-white disabled:opacity-50"
      >
        Reproducir
      </button>
      <button
        type="button"
        onClick={onPausar}
        disabled={deshabilitado || !reproduciendo}
        className="rounded border border-gray-400 px-3 py-1 text-sm disabled:opacity-50"
      >
        Pausar
      </button>
    </div>
  )
}
