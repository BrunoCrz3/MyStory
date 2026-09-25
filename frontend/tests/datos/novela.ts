import type { Esquemas } from '@/shared/api'
import { ejemploDeEsquema, ejemploDeRespuesta } from '../apoyo/ejemplos'
import { NOVEL_ID } from './identificadores'
import { TITULO } from './lectura'

export function crearNovela(versionVigente: number | null) {
  return {
    novel_id: NOVEL_ID,
    titulo: versionVigente === null ? null : TITULO,
    estado: versionVigente === null ? 'Escribiendo' : 'Publicada',
    version_vigente: versionVigente,
    total_capitulos: 10,
    creada_en: '2026-09-23T10:00:00Z',
    brief: ejemploDeEsquema<Esquemas['BriefNovela']>('BriefNovela'),
  } satisfies Esquemas['Novela']
}

export const generacionEnCurso = () =>
  ejemploDeRespuesta<Esquemas['Generacion']>('/novelas/{novel_id}/generaciones/{generacion_id}', 'get', '200', 'enCurso')

export const generacionDetenida = () =>
  ejemploDeRespuesta<Esquemas['Generacion']>('/novelas/{novel_id}/generaciones/{generacion_id}', 'get', '200', 'detenida')

/** La generación inicial ya terminada: la que dejó publicada la versión vigente. */
export const generacionPublicada = (): Esquemas['Generacion'] => ({
  ...generacionEnCurso(),
  estado: 'Publicada',
  es_terminal: true,
  intervalo_sondeo_segundos: null,
})
