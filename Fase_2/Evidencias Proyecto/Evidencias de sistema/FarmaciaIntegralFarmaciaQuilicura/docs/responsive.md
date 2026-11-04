# Adaptación de la interfaz web

La tienda y el panel conservan las mismas operaciones y permisos. Los cambios
afectan la presentación y la navegación.

- Menú administrativo modal en anchos de hasta 800 px; conserva por separado la
  preferencia de expansión del escritorio. Permite Escape, cierre al navegar,
  recorrido circular con Tab y cierre al cambiar a escritorio.
- Navegación lateral desplazable en pantallas de poca altura.
- Menú compacto de la tienda en teléfonos; catálogo y carrito siguen visibles.
- Pedidos y auditoría se presentan como tarjetas cuando el contenedor es
  estrecho. Los filtros de sucursal y estado de pedidos permanecen disponibles.
- Línea de tiempo vertical en tarjetas estrechas, controles táctiles de al menos
  44 px en los grupos adaptados, formularios y acciones que pueden reorganizarse.
- POS y dashboard distribuyen sus columnas según el espacio real del panel.
- Diálogos limitados por el viewport dinámico, contenido central con ancho
  máximo en monitores grandes y respeto de la preferencia de movimiento reducido.

Las reglas compartidas están en `src/styles/responsive.css`, importado después
de la aplicación para complementar los estilos específicos de cada módulo.

## Verificación local

Revisión con Chrome mediante Playwright e interceptación de las API con datos
simulados; no se enviaron operaciones a producción.

- 18 rutas: catálogo público, producto, registro, login de cliente, carrito,
  confirmación, login interno, dashboard, auditoría, pedidos, usuarios,
  sucursales, productos, promociones, inventario, transferencias, POS y caja.
- Anchos comprobados: 320, 390, 768, 820, 1024, 1280, 1366, 1920, 2560 y
  3440 px. Revisión adicional a 844 × 390 y de diálogos a 768 × 390.
- Carrito con productos, historial del cliente autenticado, confirmación y
  filtros de fechas personalizados.
- Diez ventanas: usuario, roles, sucursal, producto, categoría, transferencia,
  detalle de pedido, retiro, detalle de auditoría e historial de ventas.
- Comprobaciones de desbordamiento horizontal, límites de las ventanas,
  errores JavaScript, navegación con teclado y cambio de tamaño.
- Las 132 pruebas existentes pasaron; se añadieron dos pruebas de regresión del
  menú administrativo. Compilación TypeScript/Vite y ESLint sin errores.

Las capturas y los scripts de exploración están en la carpeta local ignorada
`.responsive-check.local`. Esta revisión de tamaños en Chrome no sustituye una
prueba física de Safari/iOS, teclados virtuales o dispositivos Android concretos.
