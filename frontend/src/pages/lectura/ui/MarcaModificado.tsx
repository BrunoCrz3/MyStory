/** Se pinta solo si el backend dice `modificado: true`; el frontend no compara versiones. */
export function MarcaModificado({ modificado }: { modificado: boolean | undefined }) {
  if (!modificado) return null
  return (
    <span data-testid="capitulo-modificado" className="marca-modificado">
      Modificado en esta versión
    </span>
  )
}
