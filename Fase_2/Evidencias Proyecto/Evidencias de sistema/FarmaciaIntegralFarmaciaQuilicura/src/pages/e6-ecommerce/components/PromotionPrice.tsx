import type { AppliedPromotion } from '../types/promotion'
import './promotion-price.css'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))
interface PromotionPriceProps {
  price: string
  basePrice?: string | null
  discount?: string
  promotion?: AppliedPromotion | null
}
export default function PromotionPrice({ price, basePrice, discount, promotion }: PromotionPriceProps) {
  const discounted = promotion && basePrice && Number(basePrice) > Number(price)
  return <div className="promotion-price-block">
    {discounted && <p className="promotion-original"><span>Precio normal: </span><del>{money(basePrice)}</del></p>}
    <p className="promotion-final"><span className="sr-only">{discounted ? 'Precio promocional: ' : 'Precio: '}</span>{money(price)}</p>
    {discounted && <><p className="promotion-badge">{promotion.kind === 'PERCENT' ? `${Number(promotion.value).toLocaleString('es-CL')} % de descuento` : 'Precio promocional fijo'}</p>
      <p className="promotion-saving">{promotion.name}{discount && Number(discount) > 0 ? ` · Ahorras ${money(discount)} por unidad` : ''}</p></>}
  </div>
}
