import { StrictMode } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import Notification from './Notification'

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

it('mantiene los errores hasta cerrarlos y muestra un mensaje nuevo', () => {
  vi.useFakeTimers()
  const view = render(<Notification message="No se guardó el producto" />)
  act(() => vi.advanceTimersByTime(30000))
  expect(screen.getByRole('alert').textContent).toContain('No se guardó el producto')
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar notificación' }))
  expect(screen.getByRole('alert').classList.contains('is-closing')).toBe(true)
  act(() => vi.advanceTimersByTime(200))
  expect(screen.queryByRole('alert')).toBeNull()
  view.rerender(<Notification message="Revisa la conexión" />)
  expect(screen.getByRole('alert').textContent).toContain('Revisa la conexión')
})

it('pausa el cierre automático mientras se lee el aviso', () => {
  vi.useFakeTimers()
  render(<Notification kind="success" message="Usuario guardado" />)
  fireEvent.mouseEnter(screen.getByRole('status'))
  act(() => vi.advanceTimersByTime(10000))
  expect(screen.getByRole('status')).toBeTruthy()
  fireEvent.mouseLeave(screen.getByRole('status'))
  act(() => vi.advanceTimersByTime(8000))
  expect(screen.getByRole('status').classList.contains('is-closing')).toBe(true)
  act(() => vi.advanceTimersByTime(200))
  expect(screen.queryByRole('status')).toBeNull()
})

it('evita duplicados, apila mensajes y limpia el registro al desmontarse', () => {
  const view = render(<StrictMode><Notification message="Error compartido" /><Notification message="Error compartido" /><Notification kind="info" message="Otro aviso" /></StrictMode>)
  expect(screen.getAllByRole('alert')).toHaveLength(1)
  expect(Number.parseInt(screen.getByRole('status').style.top)).toBeGreaterThan(20)
  view.unmount()
  render(<Notification message="Nuevo aviso" />)
  expect(screen.getByRole('alert').style.top).toBe('20px')
})

it('no muestra notificaciones de un modal cerrado', () => {
  const view = render(<dialog><Notification message="Error del modal" /></dialog>)
  expect(screen.queryByRole('alert')).toBeNull()
  view.unmount()
  render(<dialog open><Notification message="Error del modal" /></dialog>)
  expect(screen.getByRole('alert').textContent).toContain('Error del modal')
})

it('cierra sin esperar animaciones cuando se solicita movimiento reducido', () => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })))
  render(<Notification message="Aviso accesible" />)
  fireEvent.click(screen.getByRole('button', { name: 'Cerrar notificación' }))
  expect(screen.queryByRole('alert')).toBeNull()
})
