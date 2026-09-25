// Respuestas de lectura que el contrato no trae como ejemplo. `satisfies` las ata a los
// tipos generados: si se apartan del contrato, `npm run typecheck` rompe.
import type { Esquemas } from '@/shared/api'
import { ejemploDeEsquema } from '../apoyo/ejemplos'
import { ENUNCIADO_NUEVO, FRAGMENTO, HECHO_ID, NOVEL_ID } from './identificadores'

const brief = ejemploDeEsquema<Esquemas['BriefNovela']>('BriefNovela')
export const TITULO = 'La vuelta de la Alondra'
const NUMEROS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const

export function textoDeCapitulo(n: number): string {
  // El capítulo 3 contiene el fragmento del ejemplo porFragmento.
  return n === 3
    ? `Amanecía en el puerto. ${FRAGMENTO}, y el agua olía a sal.`
    : `Texto del capítulo ${n}. El mar seguía allí.`
}

export function crearVersion(
  version: number,
  modificados: readonly number[] = [],
  estado: Esquemas['Version']['estado'] = 'publicada',
) {
  return {
    version,
    novel_id: NOVEL_ID,
    estado,
    titulo: TITULO,
    publicada_en: '2026-09-23T10:30:00Z',
    version_anterior: version > 1 ? version - 1 : null,
    hash: `hash-v${version}`,
    dedicatoria: brief.dedicatoria,
    capitulos: NUMEROS.map((n) => ({
      numero: n,
      titulo: `Capítulo ${n}`,
      palabras: 1500,
      modificado: modificados.includes(n),
    })),
  } satisfies Esquemas['Version']
}

export function crearCapitulos(modificados: readonly number[] = []) {
  return NUMEROS.map((n) => ({
    numero: n,
    titulo: `Capítulo ${n}`,
    estado: 'Aceptado',
    texto: textoDeCapitulo(n),
    palabras: 1500,
    intentos: 0,
    modificado: modificados.includes(n),
  }) satisfies Esquemas['Capitulo'])
}

export const PORTADA = {
  titulo: TITULO,
  dedicatoria: brief.dedicatoria,
  destinatario: brief.destinatario.nombre,
  ocasion: brief.ocasion.tipo,
} satisfies Esquemas['Portada']

export const FICHA = {
  personajes: [
    { nombre: brief.destinatario.nombre, descripcion: 'Aprendió a navegar un verano.', capitulos: [2, 7] },
    { nombre: 'Nube', descripcion: 'El perro del puerto.', capitulos: [3] },
  ],
  lugares: [{ nombre: 'El puerto', descripcion: null, capitulos: [1, 3, 10] }],
} satisfies Esquemas['Ficha']

export const HECHOS_CAPITULO_3 = [
  {
    hecho_id: HECHO_ID,
    enunciado: 'El perro se llama Luna',
    estado: 'adoptado',
    origen: 'extraccion',
    capitulo_establece: 3,
    capitulos_usan: [3, 7],
    fragmento_soporte: FRAGMENTO,
  },
] satisfies Esquemas['Hecho'][]

export const VERSIONES = [
  { version: 2, publicada_en: '2026-09-23T11:00:00Z', version_anterior: 1, capitulos_modificados: [3, 7], motivo: ENUNCIADO_NUEVO },
  { version: 1, publicada_en: '2026-09-23T10:30:00Z', version_anterior: null, capitulos_modificados: [], motivo: null },
] satisfies Esquemas['VersionResumen'][]
