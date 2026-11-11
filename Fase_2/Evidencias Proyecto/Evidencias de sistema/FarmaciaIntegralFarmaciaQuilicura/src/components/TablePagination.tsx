import { useId } from 'react'
import './pagination.css'

interface Props {
  total: number
  page: number
  size: number
  busy?: boolean
  onPageChange: (page: number) => void
  onSizeChange: (size: number) => void
}

export default function TablePagination({ total, page, size, busy = false, onPageChange, onSizeChange }: Props) {
  const labelId = useId()
  const pages = Math.max(1, Math.ceil(total / size))
  const start = (page - 1) * size
  return <nav className="table-pagination" aria-label="Paginación del listado" aria-busy={busy}>
    <label htmlFor={labelId}>Filas por página<select id={labelId} value={size} disabled={busy} onChange={event => onSizeChange(Number(event.target.value))}>{[15, 25, 50, 100].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
    <span role="status">Mostrando {total ? start + 1 : 0}–{Math.min(start + size, total)} de {total}</span>
    <div><button type="button" disabled={busy || page <= 1} onClick={() => onPageChange(page - 1)}>Anterior</button><span>Página {page} de {pages}</span><button type="button" disabled={busy || page >= pages} onClick={() => onPageChange(page + 1)}>Siguiente</button></div>
  </nav>
}
