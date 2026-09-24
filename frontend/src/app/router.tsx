import { Route, Routes } from 'react-router-dom'
import { EntrevistaPage } from '@/pages/entrevista'
import { LecturaPage, RedireccionNovela } from '@/pages/lectura'
import { ProgresoPage } from '@/pages/progreso'
import { PLANTILLAS_DE_RUTA } from '@/shared/config'

export function Rutas() {
  return (
    <Routes>
      <Route path={PLANTILLAS_DE_RUTA.entrevista} element={<EntrevistaPage />} />
      <Route path={PLANTILLAS_DE_RUTA.progreso} element={<ProgresoPage />} />
      <Route path={PLANTILLAS_DE_RUTA.novela} element={<RedireccionNovela />} />
      <Route path={PLANTILLAS_DE_RUTA.lectura} element={<LecturaPage />} />
    </Routes>
  )
}
