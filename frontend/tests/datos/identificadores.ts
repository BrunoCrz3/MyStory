import { ejemploDeCuerpo, ejemploDeParametro, ejemploDeRespuesta } from '../apoyo/ejemplos'
import type { Esquemas } from '@/shared/api'

// Todos los identificadores salen de los ejemplos del contrato.
export const NOVEL_ID = ejemploDeParametro<string>('NovelId')
export const GENERACION_ID = ejemploDeRespuesta<Esquemas['Generacion']>(
  '/novelas/{novel_id}/generaciones/{generacion_id}', 'get', '200', 'enCurso',
).generacion_id
export const HECHO_ID = ejemploDeCuerpo<{ hecho_id: string }>(
  '/novelas/{novel_id}/solicitudes-cambio', 'post', 'porHecho',
).hecho_id
export const FRAGMENTO = ejemploDeCuerpo<{ fragmento: string }>(
  '/novelas/{novel_id}/solicitudes-cambio', 'post', 'porFragmento',
).fragmento
export const ENUNCIADO_NUEVO = ejemploDeCuerpo<{ enunciado_nuevo: string }>(
  '/novelas/{novel_id}/solicitudes-cambio', 'post', 'porHecho',
).enunciado_nuevo
export const SOLICITUD_ID = '5d0c3b1e-7a41-4e2f-9c6b-0a8f4e2d1b93'
export const GENERACION_DIRIGIDA_ID = '9b2e4d71-3c5a-4f08-8e1d-7a6c0f3b2e45'
