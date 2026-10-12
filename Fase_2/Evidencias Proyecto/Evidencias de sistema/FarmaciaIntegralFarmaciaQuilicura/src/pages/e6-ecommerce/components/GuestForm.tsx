import { type FormEvent } from 'react'
import { useGuest } from '../hooks/useGuest'

export default function GuestForm({ busy, onSubmit, onEdit }: { busy: boolean; onSubmit: () => Promise<void>; onEdit: () => void }) {
  const { guest, update } = useGuest()
  function submit(event: FormEvent) { event.preventDefault(); void onSubmit() }
  return <form className="guest-form" onSubmit={submit} aria-busy={busy}>
    <label htmlFor="guest-name">Nombre<input id="guest-name" autoComplete="off" required maxLength={150} value={guest.name} disabled={busy} onChange={e => { update({ ...guest, name: e.target.value }); onEdit() }} /></label>
    <label htmlFor="guest-email">Correo electrónico<input id="guest-email" type="email" autoComplete="off" required maxLength={254} value={guest.email} disabled={busy} onChange={e => { update({ ...guest, email: e.target.value }); onEdit() }} /></label>
    <button type="submit" disabled={busy}>{busy ? 'Revisando…' : 'Revisar datos y carrito'}</button>
  </form>
}
