import { screen, waitFor } from '@testing-library/react'
import { Rutas } from '@/app'
import type { Esquemas } from '@/shared/api'
import { crearFetchDePrueba } from '../../apoyo/fetch-de-prueba'
import { renderizar } from '../../apoyo/render'
import { generacionDirigida } from '../../datos/cambio'
import { GENERACION_DIRIGIDA_ID, NOVEL_ID } from '../../datos/identificadores'
import { generacionPublicada } from '../../datos/novela'
import { responderVersiones } from '../../datos/responder-lectura'

function montar(generaciones: Esquemas['Generacion'][], candidatas: readonly number[] = []) {
  const prueba = crearFetchDePrueba()
  responderVersiones(prueba, { 2: [], 3: [3, 7] }, candidatas)
  prueba.responder('get', '/novelas/{novel_id}/generaciones', { status: 200, cuerpo: generaciones })
  return prueba
}

async function lecturaLista() {
  const lectura = screen.getByTestId('lectura')
  await waitFor(() => expect(lectura).toHaveAttribute('data-estado', 'lista'))
  return lectura
}

describe('lectura: aviso de regeneración en curso', () => {
  it('con una regeneración en curso avisa y enlaza a su progreso', async () => {
    const prueba = montar([generacionDirigida(), generacionPublicada()])
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
    await lecturaLista()
    const aviso = await screen.findByRole('status', { name: /regeneración en curso/i })
    expect(aviso).toHaveAttribute('data-controles')
    expect(screen.getByRole('link', { name: /ver el progreso/i })).toHaveAttribute(
      'href',
      `/novelas/${NOVEL_ID}/generaciones/${GENERACION_DIRIGIDA_ID}`,
    )
  })

  it('sin generación en curso no avisa', async () => {
    const prueba = montar([generacionPublicada()])
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
    await lecturaLista()
    await waitFor(() => expect(prueba.peticionesA('get', '/novelas/{novel_id}/generaciones')).not.toHaveLength(0))
    expect(screen.queryByRole('status', { name: /regeneración en curso/i })).not.toBeInTheDocument()
  })

  it('no avisa, ni pregunta, sobre la candidata que el gate está pintando', async () => {
    const prueba = montar([generacionDirigida(), generacionPublicada()], [3])
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/3`, prueba })
    await lecturaLista()
    expect(prueba.peticionesA('get', '/novelas/{novel_id}/generaciones')).toHaveLength(0)
    expect(screen.queryByRole('status', { name: /regeneración en curso/i })).not.toBeInTheDocument()
  })

  it('si falla la consulta de generaciones, la lectura sigue lista y sin aviso', async () => {
    const prueba = montar([])
    prueba.responder('get', '/novelas/{novel_id}/generaciones', {
      status: 500,
      cuerpo: { type: '/problemas/error-interno', title: 'Error interno', status: 500 },
    })
    renderizar(<Rutas />, { ruta: `/novelas/${NOVEL_ID}/versiones/2`, prueba })
    await lecturaLista()
    expect(screen.queryByRole('status', { name: /regeneración en curso/i })).not.toBeInTheDocument()
  })
})
