import { screen, waitFor } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { ejemploDeEsquema, ejemploDeProblema } from '../../apoyo/ejemplos'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { RutaActual } from '../../apoyo/ruta-actual'
import { GENERACION_ID, NOVEL_ID } from '../../datos/identificadores'
import { crearNovela, generacionEnCurso } from '../../datos/novela'
import { aBriefCompleto } from '@/pages/entrevista/model/formulario'
import { rellenarConBrief } from './formulario'

const VALIDAR = '/briefs/validacion'
const CREAR = '/novelas'
const LANZAR = '/novelas/{novel_id}/generaciones'

const valido = {
  valido: true,
  datos_faltantes: [],
  contradicciones: [],
  fragmentos_sospechosos: [],
  hechos_extraidos: [],
} satisfies Esquemas['ResultadoValidacionBrief']

function montar(lanzar: { status: number; cuerpo: unknown } = { status: 202, cuerpo: generacionEnCurso() }) {
  const prueba = crearFetchDePrueba()
  prueba.responder('get', CREAR, {
    status: 200,
    cuerpo: { items: [{ novel_id: NOVEL_ID, titulo: 'La vuelta de la Alondra', estado: 'Publicada', version_vigente: 2, creada_en: '2026-09-23T10:00:00Z' }], total: 1 },
  })
  prueba.responder('post', VALIDAR, { status: 200, cuerpo: valido })
  prueba.responder('post', CREAR, { status: 201, cuerpo: { ...crearNovela(null), estado: 'Configurando' } })
  prueba.responder('post', LANZAR, lanzar)
  return renderizar(
    <>
      <Rutas />
      <RutaActual />
    </>,
    { ruta: '/', prueba },
  )
}

const brief = () => ejemploDeEsquema<Esquemas['BriefNovela']>('BriefNovela')

describe('entrevista: formulario y crear (CA-04)', () => {
  it('validar envía el mismo objeto que el ejemplo BriefNovela del contrato', async () => {
    const { prueba, usuario } = montar()
    await rellenarConBrief(usuario, brief())

    await usuario.click(screen.getByRole('button', { name: 'Validar' }))

    await waitFor(() => expect(prueba.peticionesA('post', VALIDAR)).toHaveLength(1))
    expect(prueba.peticionesA('post', VALIDAR)[0]?.cuerpo).toEqual(brief())
  }, 20_000)

  it('con valido: true crea la novela, lanza la generación y navega al progreso', async () => {
    const { prueba, usuario } = montar()
    const crearYGenerar = screen.getByRole('button', { name: 'Crear y generar' })
    expect(crearYGenerar).toBeDisabled()

    await rellenarConBrief(usuario, brief())
    await usuario.click(screen.getByRole('button', { name: 'Validar' }))
    await waitFor(() => expect(crearYGenerar).toBeEnabled())
    await usuario.click(crearYGenerar)

    expect(await screen.findByText(`/novelas/${NOVEL_ID}/generaciones/${GENERACION_ID}`)).toBeInTheDocument()
    // Solo los POST: al navegar, la página de progreso empieza a sondear por su cuenta.
    expect(prueba.peticiones.filter((p) => p.metodo === 'POST').map((p) => `${p.metodo} ${p.plantilla}`)).toEqual([
      `POST ${VALIDAR}`,
      `POST ${CREAR}`,
      `POST ${LANZAR}`,
    ])
    expect(prueba.peticionesA('post', CREAR)[0]?.cuerpo).toEqual(brief())
  }, 20_000)

  it('tras editar un campo, «Crear y generar» vuelve a deshabilitarse', async () => {
    const { usuario } = montar()
    await rellenarConBrief(usuario, brief())
    await usuario.click(screen.getByRole('button', { name: 'Validar' }))
    const crearYGenerar = screen.getByRole('button', { name: 'Crear y generar' })
    await waitFor(() => expect(crearYGenerar).toBeEnabled())

    await usuario.type(screen.getByLabelText('Tono'), ' y tierno')

    expect(crearYGenerar).toBeDisabled()
  }, 20_000)

  it('un 409 al lanzar se muestra con enlace a la generación que corre', async () => {
    const { usuario } = montar({ status: 409, cuerpo: ejemploDeProblema('Conflicto') })
    await rellenarConBrief(usuario, brief())
    await usuario.click(screen.getByRole('button', { name: 'Validar' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crear y generar' })).toBeEnabled())
    await usuario.click(screen.getByRole('button', { name: 'Crear y generar' }))

    expect(await screen.findByRole('link', { name: /ver su progreso/i })).toBeInTheDocument()
  }, 20_000)

  it('la lista de novelas enlaza a cada una', async () => {
    montar()
    expect(await screen.findByRole('link', { name: /La vuelta de la Alondra/ })).toHaveAttribute('href', `/novelas/${NOVEL_ID}`)
  })
})

describe('del brief parcial al completo', () => {
  it('el ejemplo completo pasa tal cual', () => {
    expect(aBriefCompleto(brief())).toEqual(brief())
  })

  it('el ejemplo parcial del contrato, sin nombre ni género, no pasa', () => {
    expect(aBriefCompleto(ejemploDeEsquema<Esquemas['BriefNovelaParcial']>('BriefNovelaParcial'))).toBeNull()
  })
})
