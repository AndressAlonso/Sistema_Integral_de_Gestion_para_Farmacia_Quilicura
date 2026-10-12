import { Children, useId, useState, type ReactNode } from 'react'
import './pagination.css'

export default function PaginatedTableBody({ children, total, columns }: { children: ReactNode; total: number; columns: number }) {
  const rows = Children.toArray(children)
  const signature = rows.map(row => typeof row === 'object' && row !== null && 'key' in row ? row.key : '').join('|')
  const [navigation, setNavigation] = useState({ signature, page: 1, size: 15 })
  if (navigation.signature !== signature) setNavigation({ ...navigation, signature, page: 1 })
  const pages = Math.max(1, Math.ceil(total / navigation.size))
  const page = navigation.signature === signature ? Math.min(navigation.page, pages) : 1
  const start = (page - 1) * navigation.size
  const labelId = useId()
  return <><tbody>{total ? rows.slice(start, start + navigation.size) : rows}</tbody>
    <tfoot><tr><td colSpan={columns}><nav className="table-pagination" aria-label="Paginación del listado">
      <label htmlFor={labelId}>Filas por página<select id={labelId} value={navigation.size} onChange={event => setNavigation({ signature, page: 1, size: Number(event.target.value) })}>{[15, 25, 50, 100].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
      <span role="status">Mostrando {total ? start + 1 : 0}–{Math.min(start + navigation.size, total)} de {total}</span>
      <div><button type="button" disabled={page <= 1} onClick={() => setNavigation({ ...navigation, signature, page: page - 1 })}>Anterior</button><span>Página {page} de {pages}</span><button type="button" disabled={page >= pages} onClick={() => setNavigation({ ...navigation, signature, page: page + 1 })}>Siguiente</button></div>
    </nav></td></tr></tfoot></>
}
