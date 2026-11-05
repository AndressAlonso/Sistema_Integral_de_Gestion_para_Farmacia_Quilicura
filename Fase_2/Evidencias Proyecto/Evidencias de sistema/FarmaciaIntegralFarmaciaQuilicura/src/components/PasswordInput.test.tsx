import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import PasswordInput from './PasswordInput'

afterEach(cleanup)

it('muestra y oculta sin cambiar la contraseña ni enviar el formulario', () => {
  const submit = vi.fn(event => event.preventDefault())
  render(<form onSubmit={submit}><label htmlFor="qa-password">Contraseña</label><PasswordInput id="qa-password" defaultValue="Valor-ficticio-2026" /></form>)
  const input = screen.getByLabelText('Contraseña') as HTMLInputElement
  expect(input.type).toBe('password')
  fireEvent.click(screen.getByRole('button', { name: 'Mostrar contraseña' }))
  expect(input.type).toBe('text')
  expect(input.value).toBe('Valor-ficticio-2026')
  fireEvent.click(screen.getByRole('button', { name: 'Ocultar contraseña' }))
  expect(input.type).toBe('password')
  expect(submit).not.toHaveBeenCalled()
})

it('permite mostrar la confirmación por separado y respeta el estado ocupado', () => {
  const { rerender } = render(<><PasswordInput id="password" /><PasswordInput id="confirmation" toggleLabel="confirmación de contraseña" /></>)
  fireEvent.click(screen.getByRole('button', { name: 'Mostrar confirmación de contraseña' }))
  expect(document.getElementById('password')?.getAttribute('type')).toBe('password')
  expect(document.getElementById('confirmation')?.getAttribute('type')).toBe('text')
  rerender(<PasswordInput id="password" disabled />)
  expect((screen.getByRole('button', { name: 'Mostrar contraseña' }) as HTMLButtonElement).disabled).toBe(true)
})
