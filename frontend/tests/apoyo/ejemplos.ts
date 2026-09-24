// Ejemplos leídos de specs/openapi.yaml en cada ejecución: si el contrato cambia un
// ejemplo, las pruebas lo ven sin tocar nada aquí.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parse } from 'yaml'
import type { Esquemas } from '@/shared/api'

type Nodo = Record<string, unknown>

const contrato = parse(
  readFileSync(resolve(process.cwd(), '../specs/openapi.yaml'), 'utf-8'),
) as Nodo

function bajar(nodo: unknown, ...claves: string[]): unknown {
  let actual = nodo
  for (const clave of claves) {
    if (typeof actual !== 'object' || actual === null || !(clave in actual)) {
      throw new Error(`El contrato no tiene ${claves.join(' › ')} (falla en «${clave}»)`)
    }
    actual = (actual as Nodo)[clave]
  }
  return actual
}

/** `copia` para que una prueba que muta un ejemplo no ensucie a la siguiente. */
const copia = <T>(valor: unknown): T => structuredClone(valor) as T

export function ejemploDeRespuesta<T>(ruta: string, metodo: string, status: string, nombre: string): T {
  const contenido = bajar(contrato, 'paths', ruta, metodo, 'responses', status, 'content') as Nodo
  const medio = Object.values(contenido)[0]
  return copia<T>(bajar(medio, 'examples', nombre, 'value'))
}

export function ejemploDeCuerpo<T>(ruta: string, metodo: string, nombre: string): T {
  return copia<T>(bajar(contrato, 'paths', ruta, metodo, 'requestBody', 'content', 'application/json', 'examples', nombre, 'value'))
}

export function ejemploDeEsquema<T>(nombre: string): T {
  return copia<T>(bajar(contrato, 'components', 'schemas', nombre, 'example'))
}

export function ejemploDeProblema(nombre: string): Esquemas['Problema'] {
  return copia(bajar(contrato, 'components', 'responses', nombre, 'content', 'application/problem+json', 'example'))
}

export function ejemploDeParametro<T>(nombre: string): T {
  return copia<T>(bajar(contrato, 'components', 'parameters', nombre, 'example'))
}
