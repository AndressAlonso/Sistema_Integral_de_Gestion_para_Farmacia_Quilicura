// Explica los requisitos existentes del backend sin conceder accesos automáticamente.
export const permissionHints: Readonly<Record<string, string>> = {
  'roles.gestionar': 'Necesita también Gestionar usuarios internos para abrir y administrar los roles.',
  'inventario.configurar_minimo': 'Necesita Consultar inventario para configurar el aviso desde esta pantalla.',
  'inventario.gestionar_lotes': 'Necesita Consultar inventario para acceder a los lotes.',
  'inventario.registrar_entrada': 'Necesita Consultar inventario para abrir la recepción desde Inventario.',
  'inventario.ajustar': 'Necesita Consultar inventario y el rol Administrador o Encargado de inventario.',
  'transferencias.solicitar': 'Necesita Consultar transferencias para acceder al módulo.',
  'transferencias.autorizar': 'Necesita Consultar transferencias y el rol Administrador.',
  'transferencias.despachar': 'Necesita Consultar transferencias y estar asignado a la sucursal de origen.',
  'transferencias.recibir': 'Necesita Consultar transferencias y estar asignado a la sucursal de destino.',
  'pedidos.preparar': 'Necesita Consultar pedidos. Solo permite preparar pedidos pagados de la sucursal autorizada.',
  'pedidos.retirar': 'Necesita Consultar pedidos. Solo permite entregar pedidos pagados y listos de la sucursal autorizada.',
  'ventas.reversar': 'Necesita acceso al POS, caja abierta y el rol Administrador.',
  'catalogo.gestionar': 'Permite gestionar productos y categorías. Las promociones requieren además el rol Administrador.',
}
