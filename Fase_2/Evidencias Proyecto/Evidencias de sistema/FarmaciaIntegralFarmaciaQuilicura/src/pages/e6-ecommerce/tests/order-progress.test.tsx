import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import OrderHistoryItem from '../components/OrderHistoryItem'

afterEach(cleanup)
const order = { id: '1', number: 'WEB-1', created_at: '2026-10-27T12:00:00Z', status: 'PENDIENTE_PAGO', total: '1400', currency: 'CLP', pickup_branch: { id: '1', name: 'Centro' } }
const statuses = ['PENDIENTE_PAGO', 'PAGADO', 'EN_PREPARACION', 'LISTO_PARA_RETIRO', 'RETIRADO']

it.each(statuses)('marca la etapa actual correcta para %s', status => {
  render(<OrderHistoryItem order={{ ...order, status }} />)
  const stages = within(screen.getByRole('list', { name: 'Avance del pedido' })).getAllByRole('listitem')
  const index = statuses.indexOf(status)
  expect(stages).toHaveLength(5)
  expect(stages.filter(stage => stage.getAttribute('aria-current') === 'step')).toEqual([stages[index]])
  expect(stages.filter(stage => stage.textContent?.includes('Completado'))).toHaveLength(index)
})

it('no presenta un pedido cancelado como si siguiera avanzando', () => {
  render(<OrderHistoryItem order={{ ...order, status: 'CANCELADO' }} />)
  expect(screen.queryByRole('list', { name: 'Avance del pedido' })).toBeNull()
  expect(screen.getByText(/fue cancelado/)).toBeTruthy()
})

it('no inventa progreso para un estado desconocido', () => {
  render(<OrderHistoryItem order={{ ...order, status: 'OTRO' }} />)
  expect(screen.queryByText('Estado actual')).toBeNull()
  expect(screen.getByText(/no está disponible para este estado/)).toBeTruthy()
})

it('muestra el pago en revisión sin indicar que ya está pagado', () => {
  render(<OrderHistoryItem order={{ ...order, status: 'REVISION_PAGO' }} />)
  expect(screen.queryByRole('list', { name: 'Avance del pedido' })).toBeNull()
  expect(screen.getByText(/El pago está en revisión/)).toBeTruthy()
})
