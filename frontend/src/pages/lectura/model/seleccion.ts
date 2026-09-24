/**
 * El fragmento que el lector ha seleccionado dentro de `contenedor`, o `null` si la
 * selección está vacía o se sale de él: un fragmento que cruza capítulos no tiene un
 * `capitulo_origen` único.
 */
export function fragmentoSeleccionado(seleccion: Selection | null, contenedor: HTMLElement): string | null {
  if (!seleccion || seleccion.isCollapsed || seleccion.rangeCount === 0) return null
  const { anchorNode, focusNode } = seleccion
  if (!anchorNode || !focusNode || !contenedor.contains(anchorNode) || !contenedor.contains(focusNode)) return null
  const texto = seleccion.toString().trim()
  return texto === '' ? null : texto
}
