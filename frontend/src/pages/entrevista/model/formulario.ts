// Estado del formulario y su serialización. Es serialización, no dominio: no decide qué falta
// ni qué se contradice. Eso lo devuelve `validarBrief`, y el formulario lo pinta.
import type { Esquemas } from '@/shared/api'

type Parcial = Esquemas['BriefNovelaParcial']
type Completo = Esquemas['BriefNovela']
export type TipoOcasion = NonNullable<Esquemas['OcasionParcial']['tipo']>
type Voz = Esquemas['VozNarrativa']

export interface FilaElemento {
  enunciado: string
  obligatorio: boolean
}

export interface FilaTextoLibre {
  contenido: string
  procedencia: string
}

export interface EstadoFormulario {
  comprador: { identificador: string; relacion_con_destinatario: string }
  destinatario: { nombre: string; edad: string; rasgos: string; recuerdos: string; fecha_nacimiento: string }
  ocasion: { tipo: TipoOcasion | ''; fecha: string; tono_esperado: string }
  genero: string
  tono: string
  dedicatoria: { texto: string; firma: string }
  premisa: string
  elementos: FilaElemento[]
  temas_excluidos: string
  palabras_prohibidas: string
  reglas_mundo: string
  textos_libres: FilaTextoLibre[]
  voz: { persona: NonNullable<Voz['persona']> | ''; tiempo_verbal: NonNullable<Voz['tiempo_verbal']> | ''; focalizacion: NonNullable<Voz['focalizacion']> | '' }
}

export const FORMULARIO_VACIO: EstadoFormulario = {
  comprador: { identificador: '', relacion_con_destinatario: '' },
  destinatario: { nombre: '', edad: '', rasgos: '', recuerdos: '', fecha_nacimiento: '' },
  ocasion: { tipo: '', fecha: '', tono_esperado: '' },
  genero: '',
  tono: '',
  dedicatoria: { texto: '', firma: '' },
  premisa: '',
  elementos: [],
  temas_excluidos: '',
  palabras_prohibidas: '',
  reglas_mundo: '',
  textos_libres: [],
  voz: { persona: '', tiempo_verbal: '', focalizacion: '' },
}

/** El valor si no está vacío; si lo está, nada: un vacío no se envía. */
const texto = (valor: string): string | undefined => (valor.trim() === '' ? undefined : valor)

const lineas = (valor: string): string[] | undefined => {
  const lista = valor.split('\n').map((linea) => linea.trim()).filter((linea) => linea !== '')
  return lista.length === 0 ? undefined : lista
}

const entero = (valor: string): number | undefined => {
  if (valor.trim() === '') return undefined
  const numero = Number(valor)
  return Number.isInteger(numero) ? numero : undefined
}

/** Quita las claves `undefined` y devuelve `undefined` si no queda ninguna. */
function compacto<T extends object>(objeto: T): T | undefined {
  const entradas = Object.entries(objeto).filter(([, valor]) => valor !== undefined)
  return entradas.length === 0 ? undefined : (Object.fromEntries(entradas) as T)
}

/** El formulario como `BriefNovelaParcial`: lo que acepta `validarBrief` (TO-037). */
export function aBriefParcial(f: EstadoFormulario): Parcial {
  const elementos = f.elementos
    .filter((fila) => fila.enunciado.trim() !== '')
    .map((fila) => ({ enunciado: fila.enunciado, obligatorio: fila.obligatorio }))
  const textosLibres = f.textos_libres
    .filter((fila) => fila.contenido.trim() !== '')
    .map((fila) => compacto({ contenido: fila.contenido, procedencia: texto(fila.procedencia) }) ?? {})

  return (
    compacto<Parcial>({
      comprador: compacto({
        identificador: texto(f.comprador.identificador),
        relacion_con_destinatario: texto(f.comprador.relacion_con_destinatario),
      }),
      destinatario: compacto({
        nombre: texto(f.destinatario.nombre),
        edad: entero(f.destinatario.edad),
        rasgos: lineas(f.destinatario.rasgos),
        recuerdos: lineas(f.destinatario.recuerdos),
        fecha_nacimiento: texto(f.destinatario.fecha_nacimiento),
      }),
      ocasion: compacto({
        tipo: f.ocasion.tipo === '' ? undefined : f.ocasion.tipo,
        fecha: texto(f.ocasion.fecha),
        tono_esperado: texto(f.ocasion.tono_esperado),
      }),
      genero: texto(f.genero),
      tono: texto(f.tono),
      dedicatoria: compacto({ texto: texto(f.dedicatoria.texto), firma: texto(f.dedicatoria.firma) }),
      premisa: texto(f.premisa),
      elementos_personalizados: elementos.length === 0 ? undefined : elementos,
      temas_excluidos: lineas(f.temas_excluidos),
      palabras_prohibidas: lineas(f.palabras_prohibidas),
      reglas_mundo: lineas(f.reglas_mundo),
      textos_libres: textosLibres.length === 0 ? undefined : textosLibres,
      voz_narrativa: compacto({
        persona: f.voz.persona === '' ? undefined : f.voz.persona,
        tiempo_verbal: f.voz.tiempo_verbal === '' ? undefined : f.voz.tiempo_verbal,
        focalizacion: f.voz.focalizacion === '' ? undefined : f.voz.focalizacion,
      }),
    }) ?? {}
  )
}

type ElementoCompleto = Esquemas['ElementoPersonalizado']
type TextoLibreCompleto = Esquemas['TextoLibre']

const elementoCompleto = (e: Esquemas['ElementoPersonalizadoParcial']): ElementoCompleto | null =>
  e.enunciado !== undefined && e.obligatorio !== undefined ? { ...e, enunciado: e.enunciado, obligatorio: e.obligatorio } : null

const textoLibreCompleto = (t: Esquemas['TextoLibreParcial']): TextoLibreCompleto | null =>
  t.contenido !== undefined ? { ...t, contenido: t.contenido } : null

const sinNulos = <T>(lista: (T | null)[]): T[] | null => (lista.includes(null) ? null : lista.filter((x): x is T => x !== null))

/**
 * Estrecha el brief parcial al completo que exige `crearNovela`, sin `as`. Solo comprueba
 * que están los campos que el schema de `BriefNovela` hace obligatorios; no decide nada que
 * no haya decidido ya `valido: true`. Si falta alguno, `null`, y la página lo pinta como error.
 */
export function aBriefCompleto(p: Parcial): Completo | null {
  const { comprador, destinatario, ocasion, genero, tono, dedicatoria, elementos_personalizados, textos_libres, ...resto } = p
  if (!comprador?.identificador || !destinatario?.nombre || destinatario.edad === undefined) return null
  if (!ocasion?.tipo || !genero || !tono || !dedicatoria?.texto) return null
  const elementos = elementos_personalizados ? sinNulos(elementos_personalizados.map(elementoCompleto)) : undefined
  const textosLibres = textos_libres ? sinNulos(textos_libres.map(textoLibreCompleto)) : undefined
  if (elementos === null || textosLibres === null) return null

  return {
    ...resto,
    comprador: { ...comprador, identificador: comprador.identificador },
    destinatario: { ...destinatario, nombre: destinatario.nombre, edad: destinatario.edad },
    ocasion: { ...ocasion, tipo: ocasion.tipo },
    genero,
    tono,
    dedicatoria: { ...dedicatoria, texto: dedicatoria.texto },
    ...(elementos ? { elementos_personalizados: elementos } : {}),
    ...(textosLibres ? { textos_libres: textosLibres } : {}),
  }
}
