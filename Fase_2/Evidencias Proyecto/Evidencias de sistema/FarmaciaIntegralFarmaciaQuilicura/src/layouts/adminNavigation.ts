// Navegación compartida; las secciones pendientes no implementan otras HU.
export const adminNavigation = [
  {
    path: '/session',
    label: 'Resumen',
    icon: 'M3 10 12 3l9 7M5 9v12h14V9M9 21v-8h6v8',
  },
  {
    path: '/admin/inventory',
    label: 'Inventario',
    icon: 'm12 3 9 5-9 5-9-5 9-5ZM3 8v9l9 5 9-5V8M12 13v9',
  },
  {
    path: '/admin/products',
    label: 'Productos',
    icon: 'm9 15 6-6M5 19a5 5 0 0 1 0-7l7-7a5 5 0 0 1 7 7l-7 7a5 5 0 0 1-7 0Z',
  },
  {
    path: '/admin/transfers',
    label: 'Transferencias',
    icon: 'M4 7h15l-4-4m4 4-4 4M20 17H5l4-4m-4 4 4 4',
  },
  {
    path: '/admin/orders',
    label: 'Pedidos Online',
    icon: 'M3 3h2l3 13h11l3-9H6M9 21h.01M18 21h.01',
  },
  {
    path: '/admin/pos',
    label: 'POS / Ventas',
    icon: 'M5 3h14v18H5ZM8 7h8M8 11h8M8 15h3',
  },
  {
    path: '/admin/cash',
    label: 'Caja',
    icon: 'M3 8h18v13H3ZM7 8V4h10v4M7 13h10',
  },
  {
    path: '/admin/promotions',
    label: 'Promociones',
    icon: 'm3 12 9-9h9v9l-9 9-9-9ZM16 7h.01',
  },
  {
    path: '/admin/users',
    label: 'Usuarios',
    icon: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM17 4a4 4 0 0 1 0 7M22 21v-2a4 4 0 0 0-3-4',
  },
  {
    path: '/admin/audit',
    label: 'Auditoría',
    icon: 'M6 3h12v18H6ZM9 7h6M9 11h6M9 15h3',
  },
  {
    path: '/admin/reports',
    label: 'Reportes',
    icon: 'M4 21V11M10 21V3M16 21v-7M22 21V7',
  },
  {
    path: '/admin/branches',
    label: 'Sucursales',
    icon: 'M3 21h18M5 21V5h14v16M9 9h2M13 9h2M9 13h2M13 13h2',
  },
] as const

// Las pantallas funcionales conservan sus permisos del backend.
const pagePermissions: Readonly<Record<string, string>> = {
  '/admin/users': 'usuarios.gestionar',
  '/admin/branches': 'sucursales.gestionar',
  '/admin/inventory': 'inventario.consultar',
}

// Visibilidad de pantallas en blanco según las responsabilidades acordadas.
// No concede permisos para operaciones futuras.
const placeholderRoles: Readonly<Record<string, readonly string[]>> = {
  '/admin/products': ['ADMINISTRADOR', 'QUIMICO_FARMACEUTICO'],
  '/admin/transfers': ['ADMINISTRADOR', 'ENCARGADO_INVENTARIO'],
  '/admin/orders': ['ADMINISTRADOR', 'ENCARGADO_PEDIDOS'],
  '/admin/pos': ['ADMINISTRADOR', 'VENDEDOR_CAJERO'],
  '/admin/cash': ['ADMINISTRADOR', 'VENDEDOR_CAJERO'],
  '/admin/promotions': ['ADMINISTRADOR'],
  '/admin/audit': ['ADMINISTRADOR', 'SOCIO'],
  '/admin/reports': ['ADMINISTRADOR', 'SOCIO'],
}

export function canAccessAdminPage(path: string, permissions: readonly string[], roles: readonly string[]): boolean {
  if (path === '/session') return true
  const required = pagePermissions[path]
  if (required !== undefined) return permissions.includes(required)
  return placeholderRoles[path]?.some(role => roles.includes(role)) ?? false
}
