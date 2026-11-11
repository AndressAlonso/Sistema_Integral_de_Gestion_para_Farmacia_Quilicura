import { chileToday } from '../../utils/businessDate'
export { chileToday } from '../../utils/businessDate'
export interface OperationalFilters { branch_id: string; date_from: string; date_to: string }
export type PeriodPreset = 'today' | 'week' | 'month' | 'all'


export function presetDates(preset: PeriodPreset, today = chileToday()) {
  if (preset === 'all') return { date_from: '', date_to: '' }
  let start = today
  if (preset === 'month') start = today.slice(0, 8) + '01'
  if (preset === 'week') {
    const day = new Date(today + 'T12:00:00Z')
    day.setUTCDate(day.getUTCDate() - 6)
    start = day.toISOString().slice(0, 10)
  }
  return { date_from: start, date_to: today }
}

export function displayDate(value: string): string {
  return new Date(value + 'T12:00:00Z').toLocaleDateString('es-CL', {
    timeZone: 'UTC', day: 'numeric', month: 'short',
  })
}

export const initialDashboardFilters = (): OperationalFilters => ({
  branch_id: '', ...presetDates('month'),
})
