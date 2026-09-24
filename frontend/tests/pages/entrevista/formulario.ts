// Rellena el formulario de la entrevista como lo haría el comprador.
import { screen, within } from '@testing-library/react'
import type { UserEvent } from '@testing-library/user-event'
import type { Esquemas } from '@/shared/api'

async function escribir(usuario: UserEvent, nombre: string | RegExp, valor: string) {
  const campo = screen.getByLabelText(nombre)
  await usuario.clear(campo)
  await usuario.click(campo)
  await usuario.paste(valor)
}

export async function rellenarConBrief(usuario: UserEvent, brief: Esquemas['BriefNovela']) {
  await escribir(usuario, 'Identificador del comprador', brief.comprador.identificador)
  if (brief.comprador.relacion_con_destinatario) {
    await escribir(usuario, 'Relación con el destinatario', brief.comprador.relacion_con_destinatario)
  }
  await escribir(usuario, 'Nombre', brief.destinatario.nombre)
  await escribir(usuario, 'Edad', String(brief.destinatario.edad))
  await escribir(usuario, /^Rasgos/, (brief.destinatario.rasgos ?? []).join('\n'))
  await escribir(usuario, /^Recuerdos/, (brief.destinatario.recuerdos ?? []).join('\n'))
  if (brief.destinatario.fecha_nacimiento) await escribir(usuario, 'Fecha de nacimiento', brief.destinatario.fecha_nacimiento)
  await usuario.selectOptions(screen.getByLabelText('Ocasión'), brief.ocasion.tipo)
  if (brief.ocasion.fecha) await escribir(usuario, 'Fecha de la ocasión', brief.ocasion.fecha)
  if (brief.ocasion.tono_esperado) await escribir(usuario, 'Tono esperado de la ocasión', brief.ocasion.tono_esperado)
  await escribir(usuario, 'Género', brief.genero)
  await escribir(usuario, 'Tono', brief.tono)
  await escribir(usuario, 'Dedicatoria', brief.dedicatoria.texto)
  if (brief.dedicatoria.firma) await escribir(usuario, 'Firma', brief.dedicatoria.firma)

  for (const [i, elemento] of (brief.elementos_personalizados ?? []).entries()) {
    await usuario.click(screen.getByRole('button', { name: 'Añadir elemento personalizado' }))
    await escribir(usuario, `Elemento personalizado ${i + 1}`, elemento.enunciado)
    const obligatorio = screen.getByRole('checkbox', { name: `Elemento ${i + 1} obligatorio` })
    if (elemento.obligatorio !== (obligatorio as HTMLInputElement).checked) await usuario.click(obligatorio)
  }
  await escribir(usuario, /^Temas excluidos/, (brief.temas_excluidos ?? []).join('\n'))
  await escribir(usuario, /^Palabras prohibidas/, (brief.palabras_prohibidas ?? []).join('\n'))
  await escribir(usuario, /^Reglas del mundo/, (brief.reglas_mundo ?? []).join('\n'))
  for (const [i, texto] of (brief.textos_libres ?? []).entries()) {
    await usuario.click(screen.getByRole('button', { name: 'Añadir texto libre' }))
    await escribir(usuario, `Texto libre ${i + 1}`, texto.contenido)
    if (texto.procedencia) await escribir(usuario, `Procedencia del texto libre ${i + 1}`, texto.procedencia)
  }
}

export const formulario = () => within(screen.getByRole('form', { name: 'Brief de la novela' }))
