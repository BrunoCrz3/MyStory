// Rutas del frontend (spec 2 § 4). La de lectura es CL-01 de spec1.md § 4.4: el backend la
// abre con Playwright, así que no se cambia sin cambiar aquella spec.
export const rutas = {
  entrevista: () => '/',
  novela: (novelId: string) => `/novelas/${novelId}`,
  progreso: (novelId: string, generacionId: string) => `/novelas/${novelId}/generaciones/${generacionId}`,
  lectura: (novelId: string, version: number) => `/novelas/${novelId}/versiones/${version}`,
  capitulo: (numero: number) => `#capitulo-${numero}`,
} as const

export const PLANTILLAS_DE_RUTA = {
  entrevista: '/',
  novela: '/novelas/:novelId',
  progreso: '/novelas/:novelId/generaciones/:generacionId',
  lectura: '/novelas/:novelId/versiones/:version',
} as const
