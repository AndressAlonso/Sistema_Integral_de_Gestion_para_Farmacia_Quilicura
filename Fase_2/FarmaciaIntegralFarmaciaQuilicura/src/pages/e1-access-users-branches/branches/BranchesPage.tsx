// HU: E1-H5 — Crear, actualizar y desactivar sucursales
import { useState } from 'react'
import { Link } from 'react-router-dom'
import logo from '../../../assets/logo-farmacia-quilicura.jpg'
import { deactivationIssues, initialBranches, type Branch } from './branches.mock'
import BranchDialog from './BranchDialog'
import '../sprint-one.css'

type Editor = { mode: 'create' | 'edit' | 'deactivate'; branch: Branch | null }

export default function BranchesPage() {
  const [branches, setBranches] = useState(initialBranches)
  const [editor, setEditor] = useState<Editor | null>(null)
  const [message, setMessage] = useState('')
  function save(name: string, address: string) {
    if (editor?.mode === 'edit' && editor.branch) {
      const id = editor.branch.id
      setBranches((current) => current.map((branch) => branch.id === id ? { ...branch, name, address } : branch))
      setMessage('Cambios guardados en esta demostración.')
    } else {
      setBranches((current) => [...current, { id: `SUC-${String(current.length + 1).padStart(3, '0')}`, name, address, active: true, openRegisters: 0, pendingOrders: 0, pendingTransfers: 0 }])
      setMessage('Sucursal creada en esta demostración.')
    }
    setEditor(null)
  }
  function deactivate() {
    if (!editor?.branch || deactivationIssues(editor.branch).length > 0) return
    const id = editor.branch.id
    setBranches((current) => current.map((branch) => branch.id === id ? { ...branch, active: false } : branch))
    setMessage('Sucursal desactivada en esta demostración. Su registro se conserva.')
    setEditor(null)
  }
  return (
    <div className="s1 s1-shell">
      <aside className="s1-sidebar">
        <img className="s1-logo" src={logo} alt="Farmacia Quilicura — Cuidando tu salud" />
        <p className="s1-sidebar-label">ADMINISTRACIÓN</p>
        <Link className="s1-nav" to="/admin/branches" aria-current="page"><span className="s1-nav-icon" aria-hidden="true">⌂</span>Sucursales</Link>
        <div className="s1-sidebar-bottom"><Link className="s1-button" to="/login">Volver al inicio de sesión</Link><p>SIGFQ · Diseño del Sprint 1</p></div>
      </aside>
      <div className="s1-shell-content">
        <header className="s1-topbar"><span>Administración / Sucursales</span><div className="s1-profile"><span className="s1-avatar" aria-hidden="true">A</span><span>Administrador de ejemplo</span></div></header>
        <main className="s1-content">
          <p className="s1-kicker">Ubicaciones operativas</p>
          <div className="s1-heading"><div><h1>Sucursales</h1><p>Administra las ubicaciones de Farmacia Quilicura.</p></div><button className="s1-button primary" onClick={() => { setMessage(''); setEditor({ mode: 'create', branch: null }) }}><span aria-hidden="true">+</span>Nueva sucursal</button></div>
          <p className="s1-notice">Prototipo visual con datos ficticios. Puedes crear, editar y probar la desactivación; los cambios se reinician al salir de esta pantalla o recargarla.</p>
          {message && <p className="s1-success" role="status">{message}</p>}
          <section className="s1-branch-panel" aria-labelledby="branch-list-title">
            <div className="s1-panel-head"><div><h2 id="branch-list-title">Directorio de sucursales</h2><p>Ubicaciones activas e inactivas del sistema.</p></div><span className="s1-count">{branches.length} sucursales</span></div>
            <div className="s1-table-wrap" tabIndex={0} role="region" aria-label="Listado de sucursales">
              <table><thead><tr><th scope="col">Sucursal</th><th scope="col">Dirección</th><th scope="col">Estado</th><th scope="col">Acciones</th></tr></thead>
                <tbody>{branches.map((branch) => <tr key={branch.id}><th scope="row">{branch.name}<small>{branch.id}</small></th><td className="s1-address">{branch.address || 'Sin dirección registrada'}</td><td><span className={branch.active ? 's1-state' : 's1-state inactive'}>{branch.active ? 'Activa' : 'Inactiva'}</span></td><td><div className="s1-actions"><button className="s1-button" aria-label={`Editar ${branch.name}`} onClick={() => setEditor({ mode: 'edit', branch })}>Editar</button>{branch.active && <button className="s1-button danger" aria-label={`Desactivar ${branch.name}`} onClick={() => setEditor({ mode: 'deactivate', branch })}>Desactivar</button>}</div></td></tr>)}</tbody>
              </table>
            </div>
            <p className="s1-panel-foot">Las sucursales inactivas conservan su registro. La desactivación no elimina información.</p>
          </section>
          <section className="s1-check-note"><h2>Desactivación controlada</h2><p>No se puede desactivar una sucursal con cajas abiertas, pedidos pendientes o transferencias pendientes que impidan el cierre. Prueba con Sucursal A para ver la confirmación y con Sucursal B para ver el bloqueo.</p></section>
          <p style={{ marginTop: 25, fontSize: 12 }}><Link to="/login">← Revisar diseño de inicio de sesión</Link></p>
        </main>
      </div>
      {editor && <BranchDialog key={`${editor.mode}-${editor.branch?.id ?? 'new'}`} {...editor} onClose={() => setEditor(null)} onSave={save} onDeactivate={deactivate} />}
    </div>
  )
}

