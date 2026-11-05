import { useState, type InputHTMLAttributes } from 'react'
import './password-input.css'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  id: string
  toggleLabel?: string
}

export default function PasswordInput({ id, disabled, toggleLabel = 'contraseña', ...props }: Props) {
  const [visible, setVisible] = useState(false)
  return <div className="password-input">
    <input {...props} id={id} disabled={disabled} type={visible ? 'text' : 'password'} />
    <button type="button" disabled={disabled} aria-controls={id} aria-pressed={visible}
      aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${toggleLabel}`} onClick={() => setVisible(value => !value)}>
      {visible ? 'Ocultar' : 'Mostrar'}
    </button>
  </div>
}
