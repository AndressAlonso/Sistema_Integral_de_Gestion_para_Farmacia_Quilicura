import type { DashboardData } from './dashboard.api'

// Datos ficticios usados exclusivamente en pruebas.
export const dashboardFixture: DashboardData = {
  branches: [{ id: 'b1', name: 'Quilicura Centro' }, { id: 'b2', name: 'Lo Marcoleta' }],
  period: { date_from: '2026-11-01', date_to: '2026-11-07' },
  sales: { total: '1284500', count: 94, average: '13664.89', returns: '24000', net: '1260500' },
  daily: [143000, 189000, 164500, 221000, 179000, 256000, 132000].map((total, i) => ({
    date: `2026-11-0${i + 1}`, total: String(total), count: [11, 14, 12, 16, 13, 18, 10][i],
  })),
  payments: [
    { method: 'DEBITO', total: '590000', count: 40 }, { method: 'EFECTIVO', total: '340500', count: 28 },
    { method: 'MERCADOPAGO', total: '234000', count: 18 }, { method: 'CREDITO', total: '120000', count: 8 },
  ],
  by_branch: [{ id: 'b1', name: 'Quilicura Centro', total: '785000', count: 57 }, { id: 'b2', name: 'Lo Marcoleta', total: '499500', count: 37 }],
  top_products: [{ id: 'p1', name: 'Paracetamol 500 mg', quantity: 48 }, { id: 'p2', name: 'Ibuprofeno 400 mg', quantity: 36 }, { id: 'p3', name: 'Vitamina C 1000 mg', quantity: 24 }],
  movements: [{ type: 'VENTA', count: 110, physical: -186, reserved: 0 }],
  inventory: { as_of: '2026-11-07', low_count: 8, expiring_count: 4, expired_count: 1,
    low_stock: [
      { id: 'i1', name: 'Ibuprofeno 400 mg', branch: 'Quilicura Centro', available: 0, minimum: 10 },
      { id: 'i2', name: 'Loratadina 10 mg', branch: 'Lo Marcoleta', available: 3, minimum: 8 },
      { id: 'i3', name: 'Alcohol gel 500 ml', branch: 'Quilicura Centro', available: 4, minimum: 6 },
    ],
    expiring: [{ id: 'l1', name: 'Vitamina C 1000 mg', branch: 'Lo Marcoleta', lot: 'VC-2601', date: '2026-11-17', quantity: 12, days: 10 }],
  },
}
