import StoreIcon from './StoreIcon'
import type { PublicBranch } from '../types/catalog'

export default function BranchSelector({ branches, value, onChange }: {
  branches: PublicBranch[]; value: string; onChange: (value: string) => void
}) {
  return <label className="online-field online-branch-filter"><span className="store-label-icon"><StoreIcon name="location" />Consultar disponibilidad en</span>
    <select value={value} onChange={event => onChange(event.target.value)}>
      <option value="">Todas las sucursales</option>
      {branches.map(branch => <option key={branch.id} value={branch.id}>{branch.name}</option>)}
    </select>
  </label>
}