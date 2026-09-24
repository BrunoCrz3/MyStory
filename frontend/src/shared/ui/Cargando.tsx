export function Cargando({ que }: { que: string }) {
  return (
    <p role="status" aria-live="polite">
      Cargando {que}…
    </p>
  )
}
