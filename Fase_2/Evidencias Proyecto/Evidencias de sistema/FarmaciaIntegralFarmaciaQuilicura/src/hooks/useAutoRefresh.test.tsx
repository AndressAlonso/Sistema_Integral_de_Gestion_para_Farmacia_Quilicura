import { act, cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import useAutoRefresh from './useAutoRefresh'

function Screen({ refresh, enabled = true }: { refresh: () => void | Promise<void>; enabled?: boolean }) {
  useAutoRefresh(refresh, enabled)
  return <input aria-label="Borrador" defaultValue="Conservar" />
}
beforeEach(() => { vi.useFakeTimers(); vi.spyOn(document, 'hidden', 'get').mockReturnValue(false); vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true) })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks() })
it('consulta periódicamente, conserva el formulario y limpia temporizadores', async () => {
  const refresh = vi.fn()
  const view = render(<Screen refresh={refresh} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
  expect(refresh).toHaveBeenCalledTimes(1)
  expect((view.getByLabelText('Borrador') as HTMLInputElement).value).toBe('Conservar')
  view.unmount()
  await act(async () => { await vi.advanceTimersByTimeAsync(40_000) })
  expect(refresh).toHaveBeenCalledTimes(1)
})
it('pausa mientras se edita, está oculto, sin conexión o deshabilitado', async () => {
  const refresh = vi.fn()
  const view = render(<Screen refresh={refresh} />)
  view.getByLabelText('Borrador').focus()
  await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
  expect(refresh).not.toHaveBeenCalled()
  view.getByLabelText('Borrador').blur()
  vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
  await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
  expect(refresh).not.toHaveBeenCalled()
  vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  fireEvent(window, new Event('focus'))
  expect(refresh).not.toHaveBeenCalled()
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  view.rerender(<Screen refresh={refresh} enabled={false} />)
  fireEvent(window, new Event('online'))
  expect(refresh).not.toHaveBeenCalled()
  view.rerender(<Screen refresh={refresh} />)
  await act(async () => { fireEvent(window, new Event('online')) })
  expect(refresh).toHaveBeenCalledTimes(1)
})
it('no superpone consultas y usa el callback actualizado', async () => {
  let resolve!: () => void
  const refresh = vi.fn(() => new Promise<void>(done => { resolve = done }))
  const view = render(<Screen refresh={refresh} />)
  await act(async () => { fireEvent(window, new Event('focus')) })
  await act(async () => { await vi.advanceTimersByTimeAsync(40_000) })
  expect(refresh).toHaveBeenCalledTimes(1)
  await act(async () => { resolve() })
  const next = vi.fn()
  view.rerender(<Screen refresh={next} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
  expect(next).toHaveBeenCalledTimes(1)
})
