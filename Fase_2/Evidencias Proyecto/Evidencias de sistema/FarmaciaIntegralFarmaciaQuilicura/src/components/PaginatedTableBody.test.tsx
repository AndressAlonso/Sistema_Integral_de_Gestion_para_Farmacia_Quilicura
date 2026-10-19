import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import PaginatedTableBody from './PaginatedTableBody'
afterEach(cleanup)
function Table({ count }: { count: number }) {
  return <table><PaginatedTableBody columns={1} total={count}>{Array.from({ length: count }, (_, i) => <tr key={i}><td>Registro {i + 1}</td></tr>)}</PaginatedTableBody></table>
}
describe('Paginación administrativa', () => {
  it('muestra 15 por página, navega y permite 25, 50 y 100', () => {
    render(<Table count={115} />)
    const body = () => document.querySelector('tbody')!
    expect(within(body()).getAllByRole('row')).toHaveLength(15)
    expect(screen.getByText('Mostrando 1–15 de 115')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Mostrando 16–30 de 115')).toBeTruthy()
    for (const size of [25, 50, 100]) {
      fireEvent.change(screen.getByLabelText('Filas por página'), { target: { value: String(size) } })
      expect(within(body()).getAllByRole('row')).toHaveLength(size)
      expect(screen.getByText(`Mostrando 1–${size} de 115`)).toBeTruthy()
    }
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Mostrando 101–115 de 115')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Siguiente' }).hasAttribute('disabled')).toBe(true)
  })
  it('vuelve a la primera página cuando cambian los resultados', () => {
    const view = render(<Table count={40} />)
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    view.rerender(<Table count={4} />)
    expect(screen.getByText('Mostrando 1–4 de 4')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Anterior' }).hasAttribute('disabled')).toBe(true)
  })
  it('conserva el mensaje vacío y muestra cero resultados', () => {
    render(<table><PaginatedTableBody columns={1} total={0}><tr><td>No hay registros</td></tr></PaginatedTableBody></table>)
    expect(screen.getByText('No hay registros')).toBeTruthy()
    expect(screen.getByText('Mostrando 0–0 de 0')).toBeTruthy()
  })
})
