import { useState } from 'react'
import MetricIcon from './MetricIcon'
import { chileToday, displayDate, presetDates, type OperationalFilters as Filters, type PeriodPreset } from './filters'
import './operational-filters.css'

interface Props {
  branches: { id: string; name: string }[]
  value: Filters
  onChange: (value: Filters) => void
  allowAll?: boolean
}
const presets: { id: PeriodPreset; label: string }[] = [
  { id: 'today', label: 'Hoy' }, { id: 'week', label: '7 días' }, { id: 'month', label: 'Este mes' },
]
export default function OperationalFilters({ branches, value, onChange, allowAll = false }: Props) {
  const [custom, setCustom] = useState(false)
  const [draft, setDraft] = useState({ date_from: value.date_from, date_to: value.date_to })
  const [error, setError] = useState('')
  const today = chileToday()
  const options = allowAll ? [...presets, { id: 'all' as const, label: 'Todo el historial' }] : presets
  const selectedPreset = options.find(option => {
    const dates = presetDates(option.id, today)
    return dates.date_from === value.date_from && dates.date_to === value.date_to
  })?.id
  const choose = (preset: PeriodPreset) => {
    const dates = presetDates(preset, today)
    setCustom(false); setError(''); setDraft(dates)
    onChange({ ...value, ...dates })
  }
  return <section className="operational-filters" aria-label="Filtros de sucursal y período">
    <div className="operational-filter-row">
      <span className="operational-filter-label"><MetricIcon name="branch" />Sucursal</span>
      <div className="operational-chips" role="group" aria-label="Sucursal">
        {[{ id: '', name: 'Todas' }, ...branches].map(branch => <button type="button" key={branch.id} aria-pressed={value.branch_id === branch.id} onClick={() => onChange({ ...value, branch_id: branch.id })}>
          {value.branch_id === branch.id && <MetricIcon name="check" />}{branch.name}
        </button>)}
      </div>
    </div>
    <div className="operational-filter-row">
      <span className="operational-filter-label"><MetricIcon name="calendar" />Período</span>
      <div className="operational-periods" role="group" aria-label="Período">
        {options.map(option => <button type="button" key={option.id} aria-pressed={!custom && selectedPreset === option.id} onClick={() => choose(option.id)}>{option.label}</button>)}
        <button type="button" aria-expanded={custom} aria-controls="custom-period" aria-pressed={custom || !selectedPreset} onClick={() => { setDraft({ date_from: value.date_from || today, date_to: value.date_to || today }); setError(''); setCustom(open => !open) }}>Personalizado</button>
      </div>
      <span className="operational-range">{value.date_from ? `${displayDate(value.date_from)} — ${displayDate(value.date_to)} ${value.date_to.slice(0, 4)}` : 'Todas las fechas'} <small>· Chile</small></span>
    </div>
    {custom && <form id="custom-period" className="operational-custom" onSubmit={event => {
      event.preventDefault()
      if (!draft.date_from || !draft.date_to) { setError('Selecciona ambas fechas.'); return }
      if (draft.date_from > draft.date_to) { setError('La fecha inicial no puede ser posterior a la fecha final.'); return }
      if (!allowAll && (Date.parse(draft.date_to) - Date.parse(draft.date_from)) / 86400000 > 365) { setError('Selecciona un período de hasta 366 días.'); return }
      setError(''); setCustom(false); onChange({ ...value, ...draft })
    }}>
      <label>Desde<input type="date" required value={draft.date_from} onChange={event => setDraft({ ...draft, date_from: event.target.value })} /></label>
      <span aria-hidden="true">→</span>
      <label>Hasta<input type="date" required value={draft.date_to} onChange={event => setDraft({ ...draft, date_to: event.target.value })} /></label>
      <button type="submit">Aplicar período</button>
      {error && <span role="alert" className="operational-error">{error}</span>}
    </form>}
  </section>
}
