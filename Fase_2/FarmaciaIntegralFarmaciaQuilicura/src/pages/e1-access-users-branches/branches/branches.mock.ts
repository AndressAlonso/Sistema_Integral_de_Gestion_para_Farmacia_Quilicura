export interface Branch {
  id: string
  name: string
  address: string
  active: boolean
  openRegisters: number
  pendingOrders: number
  pendingTransfers: number
}
export const initialBranches: Branch[] = [
  { id: 'SUC-001', name: 'Sucursal A', address: 'Dirección de ejemplo 100, Quilicura', active: true, openRegisters: 0, pendingOrders: 0, pendingTransfers: 0 },
  { id: 'SUC-002', name: 'Sucursal B', address: 'Dirección de ejemplo 200, Quilicura', active: true, openRegisters: 1, pendingOrders: 2, pendingTransfers: 1 },
  { id: 'SUC-003', name: 'Sucursal C', address: 'Dirección de ejemplo 300, Quilicura', active: false, openRegisters: 0, pendingOrders: 0, pendingTransfers: 0 },
]
export function deactivationIssues(branch: Branch) {
  return [
    ...(branch.openRegisters > 0 ? [`${branch.openRegisters} caja(s) abierta(s)`] : []),
    ...(branch.pendingOrders > 0 ? [`${branch.pendingOrders} pedido(s) pendiente(s)`] : []),
    ...(branch.pendingTransfers > 0 ? [`${branch.pendingTransfers} transferencia(s) pendiente(s) que impiden el cierre`] : []),
  ]
}

