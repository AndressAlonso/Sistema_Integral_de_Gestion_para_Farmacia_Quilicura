import { orderStateLabel } from './orders.api'
import './order-progress.css'

const steps = ['PENDIENTE_PAGO', 'PAGADO', 'EN_PREPARACION', 'LISTO_PARA_RETIRO']

export default function OrderProgress({ status, compact = false }: { status: string; compact?: boolean }) {
  const current = steps.indexOf(status)
  return (
  <div className={`customer-order-progress${compact ? " is-compact" : ""}`}>
    <p className="customer-order-progress-heading">Estado del pedido <strong>{orderStateLabel(status)}</strong></p>
    {current >= 0 ? <ol className="customer-order-steps" aria-label="Avance del pedido">
      {steps.map((step, index) => <li key={step} className={index < current ? 'is-complete' : index === current ? 'is-current' : ''} aria-current={index === current ? 'step' : undefined}>
        <span className="customer-order-step-dot" aria-hidden="true">{index < current ? '✓' : index + 1}</span>
        <span className="customer-order-step-label">{orderStateLabel(step)}<small>{index === current ? 'Estado actual' : index < current ? 'Completado' : 'Pendiente'}</small></span>
      </li>)}
    </ol> : <p className="customer-order-progress-exception">{status === 'CANCELADO' ? 'Este pedido fue cancelado y no continuará su preparación.' : 'El seguimiento por etapas no está disponible para este estado.'}</p>}
  </div>
  )
}
