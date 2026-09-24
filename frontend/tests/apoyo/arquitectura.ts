// Reglas de CA-14 sobre el código de src/: sin `any`, sin importar de tests/, y las
// fronteras de Feature-Sliced Design (capas hacia abajo, sin cruces entre páginas, y
// siempre por el index.ts de la slice o del segmento).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, posix, relative, resolve, sep } from 'node:path'

const RANGO: Record<string, number> = { shared: 0, entities: 1, features: 2, pages: 3, app: 4 }

function sinComentariosNiCadenas(codigo: string): string {
  return codigo
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '')
    .replace(/(['"`])(?:\\.|(?!\1)[^\\\n])*\1/g, "''")
}

function importaciones(codigo: string): string[] {
  const patron = /(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)|import\s+['"]([^'"]+)['"]/g
  return [...codigo.matchAll(patron)].map((m) => m[1] ?? m[2] ?? m[3] ?? '')
}

function resolverDestino(fichero: string, especificador: string): string | null {
  if (especificador.startsWith('@/')) return posix.join('src', especificador.slice(2))
  if (especificador.startsWith('.')) return posix.normalize(posix.join(posix.dirname(fichero), especificador))
  return null // paquete de node_modules
}

export function violaciones(fichero: string, codigo: string): string[] {
  const halladas: string[] = []
  if (/\bany\b/.test(sinComentariosNiCadenas(codigo))) halladas.push(`${fichero}: usa any`)

  const [, capa, slice] = fichero.split('/')
  for (const especificador of importaciones(codigo)) {
    const destino = resolverDestino(fichero, especificador)
    if (destino === null) continue
    const partes = destino.split('/')
    if (partes[0] !== 'src') {
      halladas.push(`${fichero}: importa de fuera de src/ (${especificador})`)
      continue
    }
    const [, capaDestino, sliceDestino] = partes
    if (capaDestino === 'widgets') halladas.push(`${fichero}: importa de widgets/ (${especificador})`)
    if (capa === undefined || capaDestino === undefined) continue
    const rango = RANGO[capa] ?? -1
    const rangoDestino = RANGO[capaDestino] ?? -1
    if (rangoDestino > rango) {
      halladas.push(`${fichero}: ${capa}/ importa de una capa superior, ${capaDestino}/ (${especificador})`)
      continue
    }
    const mismaSlice = capaDestino === capa && sliceDestino === slice
    if (mismaSlice || capaDestino === 'app') continue
    if (capaDestino === capa && capa !== 'shared') {
      halladas.push(`${fichero}: cruza a otra slice de ${capa}/ (${especificador})`)
      continue
    }
    if (partes.length > 3) {
      halladas.push(`${fichero}: se salta el index.ts de ${partes.slice(0, 3).join('/')} (${especificador})`)
    }
  }
  return halladas
}

export function ficherosDeSrc(): { ruta: string; codigo: string }[] {
  const raiz = resolve(process.cwd())
  const recorrer = (dir: string): string[] =>
    readdirSync(dir).flatMap((nombre) => {
      const ruta = join(dir, nombre)
      return statSync(ruta).isDirectory() ? recorrer(ruta) : /\.tsx?$/.test(nombre) ? [ruta] : []
    })
  return recorrer(join(raiz, 'src')).map((ruta) => ({
    ruta: relative(raiz, ruta).split(sep).join('/'),
    codigo: readFileSync(ruta, 'utf-8'),
  }))
}
