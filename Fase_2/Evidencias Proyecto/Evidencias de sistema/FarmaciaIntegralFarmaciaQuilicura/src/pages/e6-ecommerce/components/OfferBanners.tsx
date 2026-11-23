import { Link } from 'react-router-dom'
import type { PublicProduct } from '../types/catalog'
import StoreIcon from './StoreIcon'
import './offer-banners.css'

const money = (value: string) => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 2 }).format(Number(value))

export default function OfferBanners({ products }: { products: PublicProduct[] }) {
  const offers = products.filter(product => product.promotion && Number(product.base_price) > Number(product.price)).slice(0, 3)
  if (!offers.length) return <section className="store-offers" aria-label="Explora nuestra tienda">
    <div className="store-offer-banners">
      <a className="store-offer-banner store-offer-tone-0" href="#store-products"><div className="store-offer-copy"><span className="store-offer-kicker">TU BIENESTAR, CADA DÍA</span><h3>Encuentra lo que necesitas</h3><p className="store-offer-campaign">Explora productos, compara precios y consulta disponibilidad.</p><span className="store-offer-action">Explorar catálogo <span aria-hidden="true">→</span></span></div><div className="store-offer-art" aria-hidden="true"><StoreIcon name="orders" /></div></a>
      <a className="store-offer-banner store-offer-tone-1" href="#store-how"><div className="store-offer-copy"><span className="store-offer-kicker">CERCA DE TI</span><h3>Compra aquí. Retira en tu sucursal.</h3><p className="store-offer-campaign">Elige tu sucursal al comprar y espera el aviso de retiro.</p><span className="store-offer-action">Cómo comprar <span aria-hidden="true">→</span></span></div><div className="store-offer-art" aria-hidden="true"><StoreIcon name="location" /></div></a>
    </div>
  </section>

  return <section className="store-offers" aria-labelledby="store-offers-title">
    <div className="store-offers-heading"><div><p>PRECIOS QUE SE NOTAN</p><h2 id="store-offers-title">Un buen momento para ahorrar</h2></div><span><StoreIcon name="offer" />Promociones vigentes</span></div>
    <div className="store-offer-banners">
      {offers.map((product, index) => <Link key={product.id} className={`store-offer-banner store-offer-tone-${index}`} to={`/tienda/productos/${encodeURIComponent(product.id)}`} aria-label={`Ver oferta: ${product.name}`}>
        <div className="store-offer-copy">
          <span className="store-offer-kicker"><StoreIcon name="offer" />{product.promotion!.kind === 'PERCENT' ? `${Number(product.promotion!.value).toLocaleString('es-CL')}% de descuento` : 'Precio especial'}</span>
          <h3>{product.name}</h3>
          <p className="store-offer-campaign">{product.promotion!.name}</p>
          <div className="store-offer-prices"><strong>{money(product.price)}</strong><del>{money(product.base_price!)}</del></div>
          <span className="store-offer-action">Ver oferta <span aria-hidden="true">→</span></span>
          {product.requires_prescription && <small>Con receta · Compra presencial</small>}
        </div>
        <div className="store-offer-art" aria-hidden="true">{product.image_url ? <img src={product.image_url} alt="" loading="lazy" onError={event => { event.currentTarget.style.display = 'none' }} /> : <StoreIcon name="offer" />}</div>
      </Link>)}
    </div>
  </section>
}
