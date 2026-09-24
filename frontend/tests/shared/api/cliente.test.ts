import { crearCliente } from '@/shared/api'

describe('cliente de la API', () => {
  it('pide con el fetch inyectado bajo el prefijo /api y tipa la respuesta', async () => {
    const pedidas: string[] = []
    const fetchInyectado = async (peticion: Request) => {
      pedidas.push(peticion.url)
      return new Response(
        JSON.stringify({ estado: 'ok', version_api: '1.1.0', gate_lean_activo: false, cerrar_el_paso: false }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    }
    const cliente = crearCliente({ fetch: fetchInyectado, origen: 'http://prueba.local' })

    const { data } = await cliente.GET('/salud')

    expect(pedidas).toEqual(['http://prueba.local/api/salud'])
    expect(data?.estado).toBe('ok')
  })
})
