import type { Esquemas } from '@/shared/api'
import { ENUNCIADO_NUEVO, GENERACION_DIRIGIDA_ID, NOVEL_ID, SOLICITUD_ID } from './identificadores'
import { HECHOS_CAPITULO_3 } from './lectura'
import { generacionEnCurso } from './novela'

const base = {
  solicitud_id: SOLICITUD_ID,
  novel_id: NOVEL_ID,
  enunciado_nuevo: ENUNCIADO_NUEVO,
  capitulo_origen: 3,
  estado: 'pendiente-de-confirmacion',
  analisis_impacto: { capitulos_afectados: [3, 7], hechos_derivados: [] },
  version_resultante: null,
} satisfies Esquemas['SolicitudCambio']

export const SOLICITUD_POR_HECHO = {
  ...base,
  hecho_afectado: HECHOS_CAPITULO_3[0],
  hecho_candidato: null,
} satisfies Esquemas['SolicitudCambio']

export const HECHO_CANDIDATO = 'El perro se llama Luna'

export const SOLICITUD_POR_FRAGMENTO = {
  ...base,
  hecho_candidato: HECHO_CANDIDATO,
} satisfies Esquemas['SolicitudCambio']

export const generacionDirigida = (): Esquemas['Generacion'] => ({
  ...generacionEnCurso(),
  generacion_id: GENERACION_DIRIGIDA_ID,
  tipo: 'dirigida',
  estado: 'Regenerando',
  capitulos_a_regenerar: [3, 7],
})
