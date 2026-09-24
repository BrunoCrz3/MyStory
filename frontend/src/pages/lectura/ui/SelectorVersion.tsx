import { useNavigate } from 'react-router-dom'
import type { Esquemas } from '@/shared/api'
import { rutas } from '@/shared/config'
import { useVersiones } from '../api/lectura'

function etiqueta(version: Esquemas['VersionResumen']): string {
  const partes = [`Versión ${version.version}`]
  if (version.motivo) partes.push(version.motivo)
  if (version.capitulos_modificados.length > 0) {
    partes.push(`cambian ${version.capitulos_modificados.join(', ')}`)
  }
  return partes.join(' · ')
}

export function SelectorVersion({ novelId, version }: { novelId: string; version: number }) {
  const versiones = useVersiones(novelId)
  const navegar = useNavigate()
  if (!versiones.isSuccess) return null
  return (
    <label className="selector-version" data-controles="">
      Versión{' '}
      <select
        aria-label="Versión"
        value={String(version)}
        onChange={(evento) => navegar(rutas.lectura(novelId, Number(evento.target.value)))}
      >
        {versiones.data.map((resumen) => (
          <option key={resumen.version} value={resumen.version}>
            {etiqueta(resumen)}
          </option>
        ))}
      </select>
    </label>
  )
}
