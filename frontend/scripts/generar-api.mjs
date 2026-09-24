// Genera src/shared/api/schema.d.ts desde specs/openapi.yaml. Es la única fuente de los
// tipos del cliente: no se escriben a mano. La prueba de contrato llama a la misma función.
import { writeFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'

export const RUTA_CONTRATO = fileURLToPath(new URL('../../specs/openapi.yaml', import.meta.url))
export const RUTA_TIPOS = fileURLToPath(new URL('../src/shared/api/schema.d.ts', import.meta.url))

const CABECERA = `/**
 * Generado por scripts/generar-api.mjs desde specs/openapi.yaml. No editar a mano:
 * se regenera con \`npm run gen:api\` y la prueba de contrato falla si difiere.
 */

`

export async function generarTipos() {
  // Un campo con `default` no es obligatorio en el contrato: si no llega, lo pone el backend.
  // `openapi-typescript` 7 lo hace obligatorio salvo que se le diga lo contrario.
  const ast = await openapiTS(pathToFileURL(RUTA_CONTRATO), { defaultNonNullable: false })
  return CABECERA + astToString(ast)
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(RUTA_TIPOS, await generarTipos())
  console.log(`Tipos generados en ${RUTA_TIPOS}`)
}
