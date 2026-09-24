// @vitest-environment node
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { ficherosDeSrc, violaciones } from './apoyo/arquitectura'

describe('las reglas detectan lo que deben (CA-14)', () => {
  const casos: [string, string, string][] = [
    ['any como tipo', 'src/pages/lectura/ui/X.tsx', 'const a: any = 1'],
    ['any en as', 'src/pages/lectura/ui/X.tsx', 'const a = b as any'],
    ['import de tests', 'src/pages/lectura/ui/X.tsx', "import { x } from '../../../../tests/datos/lectura'"],
    ['shared importa de pages', 'src/shared/ui/X.tsx', "import { Lectura } from '@/pages/lectura'"],
    ['shared importa de app', 'src/shared/api/X.ts', "import { App } from '@/app'"],
    ['pages importa de app', 'src/pages/lectura/ui/X.tsx', "import { App } from '@/app'"],
    ['una página importa de otra', 'src/pages/lectura/ui/X.tsx', "import { Progreso } from '@/pages/progreso'"],
    ['página relativa a otra', 'src/pages/lectura/ui/X.tsx', "import { Progreso } from '../../progreso'"],
    ['saltarse el index de una página', 'src/app/router.tsx', "import { X } from '@/pages/lectura/ui/X'"],
    ['saltarse el index de un segmento de shared', 'src/pages/lectura/ui/X.tsx', "import { crearCliente } from '@/shared/api/cliente'"],
    ['importar de widgets', 'src/pages/lectura/ui/X.tsx', "import { W } from '@/widgets/w'"],
  ]
  it.each(casos)('%s', (_, fichero, codigo) => {
    expect(violaciones(fichero, codigo)).not.toEqual([])
  })

  it('no marca lo permitido', () => {
    expect(violaciones('src/app/router.tsx', "import { Lectura } from '@/pages/lectura'")).toEqual([])
    expect(violaciones('src/pages/lectura/ui/X.tsx', "import { useCliente } from '@/shared/api'\nimport { Y } from './Y'")).toEqual([])
    expect(violaciones('src/shared/ui/X.tsx', "import type { Esquemas } from '@/shared/api'")).toEqual([])
    expect(violaciones('src/pages/lectura/ui/X.tsx', '// cualquier compañía vale')).toEqual([])
  })
})

describe('src/ cumple las reglas (CA-14)', () => {
  it('ningún fichero de src/ las viola', () => {
    const todas = ficherosDeSrc().flatMap(({ ruta, codigo }) => violaciones(ruta, codigo))
    expect(todas).toEqual([])
  })

  it('no existe la capa widgets/', () => {
    expect(existsSync(resolve(process.cwd(), 'src/widgets'))).toBe(false)
  })
})
