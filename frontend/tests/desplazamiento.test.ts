// @vitest-environment node
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

/**
 * Ninguna hoja de estilo impide desplazar la página hasta el final (TO-063): el documento, el
 * `body` y la raíz de React no llevan una altura de pantalla ni un `overflow` oculto. `jsdom` no
 * mide la maquetación; en el navegador lo comprueba la aserción `desplazamiento` de
 * `render_visual`.
 */
const SRC = resolve(__dirname, '../src')
const CONTENEDORES = /(^|[\s,>])(html|body|:root|#root)(?=[\s,{:.[]|$)/
const BLOQUEA = /(overflow(-y)?\s*:\s*(hidden|clip))|((^|;|\s)(height|max-height)\s*:\s*100d?vh)/

function hojas(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? hojas(join(dir, e.name)) : e.name.endsWith('.css') ? [join(dir, e.name)] : [],
  )
}

export function bloqueos(css: string): string[] {
  const sinComentarios = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const reglas = [...sinComentarios.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  return reglas
    .filter(([, selector, cuerpo]) => CONTENEDORES.test(selector!.trim()) && BLOQUEA.test(cuerpo!))
    .map(([, selector]) => selector!.trim())
}

describe('el desplazamiento vertical no se bloquea (TO-063)', () => {
  it('la regla detecta una altura de pantalla con overflow oculto', () => {
    expect(bloqueos('html, body { height: 100%; overflow: hidden; }')).toEqual(['html, body'])
    expect(bloqueos('@media screen { #root { height: 100vh; } }')).toEqual(['#root'])
    expect(bloqueos('.panel-cambio { max-height: 70vh; overflow-y: auto; }')).toEqual([])
    expect(bloqueos('body { margin: 0 auto; max-width: 60rem; }')).toEqual([])
  })

  it('ninguna hoja de src/ lo hace', () => {
    const encontrados = hojas(SRC).flatMap((f) =>
      bloqueos(readFileSync(f, 'utf-8')).map((s) => `${relative(SRC, f)}: ${s}`),
    )
    expect(encontrados).toEqual([])
  })
})
