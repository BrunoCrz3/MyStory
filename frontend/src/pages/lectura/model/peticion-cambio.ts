import type { Esquemas } from '@/shared/api'

/** Desde dónde pide el lector el cambio: un hecho del canon o un fragmento seleccionado. */
export type OrigenCambio =
  | { tipo: 'hecho'; hecho: Esquemas['Hecho']; capitulo: number }
  | { tipo: 'fragmento'; fragmento: string; capitulo: number }

/**
 * El cuerpo de `crearSolicitudCambio`. El contrato exige exactamente uno de `hecho_id` o
 * `fragmento` con un `oneOf` que el tipo generado no expresa (`& (unknown | unknown)`);
 * `OrigenCambio` es lo que lo garantiza aquí.
 */
export function cuerpoDeSolicitud(origen: OrigenCambio, enunciadoNuevo: string): Esquemas['NuevaSolicitudCambio'] {
  return origen.tipo === 'hecho'
    ? { hecho_id: origen.hecho.hecho_id, enunciado_nuevo: enunciadoNuevo, capitulo_origen: origen.capitulo }
    : { fragmento: origen.fragmento, enunciado_nuevo: enunciadoNuevo, capitulo_origen: origen.capitulo }
}
