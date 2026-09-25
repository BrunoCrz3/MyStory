// @vitest-environment node
import { readFileSync } from 'node:fs'
import { parse } from 'yaml'
import { generarTipos, RUTA_CONTRATO, RUTA_TIPOS } from '../../../scripts/generar-api.mjs'

const sinRetornos = (texto: string) => texto.replace(/\r\n/g, '\n')

describe('cliente generado desde specs/openapi.yaml (CA-01)', () => {
  it('el schema.d.ts commiteado coincide con lo que genera el contrato', async () => {
    const generado = await generarTipos()
    const commiteado = readFileSync(RUTA_TIPOS, 'utf-8')
    expect(sinRetornos(commiteado)).toBe(sinRetornos(generado))
  })

  it('se genera desde la versión 1.2.0 del contrato', () => {
    const contrato = parse(readFileSync(RUTA_CONTRATO, 'utf-8')) as { info: { version: string } }
    expect(contrato.info.version).toBe('1.2.0')
  })
})
