import PromotionPrice from '../e6-ecommerce/components/PromotionPrice'
import type { AppliedPromotion } from '../e6-ecommerce/types/promotion'

export default function PosPrice({ price, basePrice, promotion }: { price: string; basePrice?: string; promotion?: AppliedPromotion | null }) {
  const applied = !!promotion && !!basePrice && Number(basePrice) > Number(price)
  return <div className="pos-price">
    {applied && <strong className="pos-promotion-label">Promoción aplicada</strong>}
    <PromotionPrice price={price} basePrice={basePrice} promotion={promotion}
      discount={applied ? (Number(basePrice) - Number(price)).toFixed(2) : undefined} />
  </div>
}
