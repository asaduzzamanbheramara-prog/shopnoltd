import { BRAND } from '../config/brand'

export function Brand() {
  return (
    <a href="/" aria-label={BRAND.name} className="brand">
      <span className="brand__name">{BRAND.name}</span>
    </a>
  )
}
