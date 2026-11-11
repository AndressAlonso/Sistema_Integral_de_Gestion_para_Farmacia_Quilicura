import { Children, cloneElement, isValidElement, useState, type ReactElement, type ReactNode } from 'react'
import TablePagination from './TablePagination'
import './pagination.css'

export default function PaginatedTableBody({ children, total, columns, labels }: { children: ReactNode; total: number; columns: number; labels?: string[] }) {
  const rows = Children.toArray(children)
  const signature = rows.map(row => typeof row === 'object' && row !== null && 'key' in row ? row.key : '').join('|')
  const [navigation, setNavigation] = useState({ signature, page: 1, size: 15 })
  if (navigation.signature !== signature) setNavigation({ ...navigation, signature, page: 1 })
  const pages = Math.max(1, Math.ceil(total / navigation.size))
  const page = navigation.signature === signature ? Math.min(navigation.page, pages) : 1
  const start = (page - 1) * navigation.size
  const visibleRows = total ? rows.slice(start, start + navigation.size) : rows
  const labeledRows = labels ? visibleRows.map(row => {
    if (!isValidElement<{ children?: ReactNode }>(row)) return row
    return cloneElement(row, {}, Children.map(row.props.children, (cell, index) => {
      if (!isValidElement<{ colSpan?: number; 'data-label'?: string }>(cell) || cell.props.colSpan) return cell
      return cloneElement(cell as ReactElement<{ 'data-label'?: string }>, { 'data-label': labels[index] })
    }))
  }) : visibleRows
  return <><tbody>{labeledRows}</tbody>
    <tfoot><tr><td colSpan={columns}><TablePagination total={total} page={page} size={navigation.size}
      onPageChange={next => setNavigation({ ...navigation, signature, page: next })}
      onSizeChange={size => setNavigation({ signature, page: 1, size })} /></td></tr></tfoot></>
}
