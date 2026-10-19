export interface AppliedPromotion {
  code: string
  name: string
  kind: 'PERCENT' | 'FIXED_PRICE'
  value: string
}
