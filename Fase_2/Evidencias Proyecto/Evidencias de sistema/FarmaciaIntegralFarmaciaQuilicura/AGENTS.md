# AGENTS.md
# Sistema Integral de Gestión para Farmacia Quilicura — SIGFQ

Este archivo contiene el contexto funcional, técnico y metodológico
del proyecto SIGFQ.

Codex debe leer este archivo completo antes de analizar, crear,
modificar, eliminar o reorganizar código del proyecto.

---

# 1. IDENTIDAD DEL PROYECTO

Nombre:

Sistema Integral de Gestión para Farmacia Quilicura

Sigla:

SIGFQ

Tipo:

Proyecto APT / Capstone de Ingeniería en Informática.

Institución:

Duoc UC
Escuela de Informática y Telecomunicaciones

Sección:

Capstone 004D

Fecha de inicio:

10/08/2026

Fecha de término planificada:

11/12/2026

Docente:

Juan Andres Hernandez Aliaga

Patrocinador principal:

Farmacia Quilicura / Representante de la farmacia

Equipo:

- Andrés Alvarado
- Jesús Lozano
- Martín Rodríguez

---

# 2. PRINCIPIO FUNDAMENTAL PARA CODEX

NO INVENTAR FUNCIONALIDADES.

Toda funcionalidad implementada debe poder relacionarse con:

- una Épica;
- una Historia de Usuario;
- un criterio de aceptación;
- una regla de negocio documentada;
- o una tarea técnica necesaria para hacer posible lo anterior.

Si una funcionalidad no aparece en este documento o en la
documentación del repositorio:

NO implementarla automáticamente.

Primero informar que no está documentada.

---

# 3. FUENTES DE VERDAD

El orden de prioridad para resolver contradicciones será:

1. Historias de Usuario finales.
2. Criterios de aceptación finales.
3. Reglas de negocio confirmadas.
4. Documento de visión.
5. Arquitectura definida.
6. Product Backlog.
7. Sprint Backlog.
8. Código existente.

El código NO tiene prioridad sobre una regla de negocio documentada.

Si código y documentación difieren, informar la inconsistencia antes
de alterar una regla funcional.

---

# 4. VISIÓN DEL PROYECTO

Desarrollar una plataforma integral de gestión para Farmacia
Quilicura que permita centralizar e integrar las principales
operaciones de sus sucursales mediante una única fuente de
información.

La solución debe mejorar:

- control del inventario;
- trazabilidad de movimientos;
- gestión de ventas presenciales;
- ventas online;
- disponibilidad de información para administración.

La plataforma busca reemplazar procesos actualmente fragmentados y
manuales mediante una solución:

- centralizada;
- segura;
- escalable;
- multisucursal.

Debe soportar las sucursales existentes y facilitar la incorporación
de nuevas ubicaciones en el futuro.

---

# 5. PROBLEMÁTICA

Actualmente existen procesos fragmentados entre las sucursales.

Problemas principales:

## Información fragmentada

Las sucursales utilizan instalaciones y bases de datos independientes.

Esto dificulta obtener una visión global y actualizada de las
operaciones.

## Inventario

No existe una visión centralizada y confiable del inventario de todas
las sucursales.

## Transferencias

Parte de las transferencias entre sucursales se registra manualmente.

Esto puede provocar:

- diferencias de stock;
- pérdida de trazabilidad;
- dificultad para determinar responsabilidades;
- información desactualizada.

## Ventas

El negocio depende principalmente del canal presencial.

No existe un canal de venta online completamente integrado con el
inventario.

## Administración

La fragmentación dificulta:

- obtener indicadores;
- revisar operaciones;
- auditar acciones;
- tomar decisiones basadas en información centralizada.

---

# 6. GRUPOS OBJETIVO

El sistema está orientado a:

## Personal administrativo

Necesita gestionar y consultar información operacional y
administrativa.

## Vendedores / Cajeros

Necesitan realizar ventas presenciales utilizando información de
inventario y precios centralizada.

## Encargados de inventario y recepción

Necesitan:

- consultar stock;
- recibir mercadería;
- gestionar lotes;
- controlar vencimientos;
- realizar transferencias;
- mantener trazabilidad.

## Administradores / responsables de la farmacia

Necesitan:

- indicadores;
- información consolidada;
- auditoría;
- control multisucursal.

## Clientes

Necesitan:

- consultar catálogo;
- consultar disponibilidad;
- comprar productos permitidos online;
- seleccionar sucursal de retiro;
- pagar;
- recibir información del pedido;
- retirar mediante QR.

---

# 7. NECESIDADES PRINCIPALES

El sistema debe permitir:

- centralizar información de las sucursales;
- controlar inventario y stock;
- digitalizar transferencias;
- mejorar trazabilidad;
- integrar ventas presenciales y online;
- facilitar consulta administrativa;
- controlar lotes y vencimientos;
- gestionar pedidos;
- procesar pagos;
- gestionar retiros;
- mantener auditoría.

---

# 8. PRODUCTO

SIGFQ será una plataforma integral de gestión para una farmacia
multisucursal.

Los diferentes componentes estarán conectados a un backend y una
base de datos central.

Componentes principales:

## Backoffice administrativo

Permitirá gestionar:

- sucursales;
- productos;
- categorías;
- precios;
- inventario;
- usuarios;
- roles;
- permisos;
- promociones;
- movimientos;
- auditoría;
- indicadores.

## Punto de Venta — POS

Permitirá realizar ventas presenciales utilizando el inventario
centralizado.

## Gestión de inventario multisucursal

Cada sucursal tendrá su propio inventario lógico, pero toda la
información utilizará una única plataforma y base de datos.

## Transferencias

Permitirá mover productos entre sucursales manteniendo trazabilidad.

## E-commerce

Existirá una tienda online integrada al inventario.

Los productos sujetos a receta pueden visualizarse online pero su
compra se restringe al canal presencial.

## Pedidos y retiro

Los pedidos online serán preparados para retiro en una sucursal
seleccionada.

Se utilizará un código QR para validar el retiro.

## Aplicación móvil

Existirá una aplicación móvil de apoyo operacional.

No es una aplicación destinada principalmente a clientes.

Sus funciones documentadas son:

- escaneo de códigos de barra para apoyar el POS;
- escaneo de códigos QR para retiro de pedidos.

## Seguridad y auditoría

La plataforma utilizará:

- usuarios;
- roles;
- permisos;
- trazabilidad;
- auditoría de operaciones sensibles.

---

# 9. VALOR DEL PROYECTO

El proyecto busca conseguir:

- información centralizada;
- información actualizada;
- mayor control de inventario;
- reducción de procesos manuales;
- mayor trazabilidad;
- integración entre sucursales;
- incorporación del canal online;
- mejor apoyo a toma de decisiones;
- escalabilidad para futuras sucursales.

---

# 10. ARQUITECTURA TECNOLÓGICA DOCUMENTADA

La arquitectura definida oficialmente es:

## Arquitectura

Monolito modular.

No transformar a microservicios salvo decisión explícita posterior.

## Frontend web

React + TypeScript.

El proyecto web utiliza actualmente:

- React;
- TypeScript;
- Vite.

## Backend

FastAPI.

Lenguaje:

Python.

## Base de datos

PostgreSQL.

## Aplicación móvil

Flutter.

## Control de versiones

Git + GitHub.

## Pasarela de pago

Flow.

---

# 11. ESTRUCTURA GENERAL RECOMENDADA DEL REPOSITORIO

SistemaIntegralFarmaciaQuilicura/

- frontend/
- backend/
- mobile/
- database/
- docs/
- AGENTS.md
- README.md

No mezclar código móvil dentro del frontend web.

No mezclar backend dentro del frontend.

---

# 12. ESTRUCTURA DEL FRONTEND

El frontend debe organizarse principalmente por funcionalidad.

frontend/src/

- app/
  - router/
  - layouts/

- features/
  - auth/
  - users/
  - branches/
  - catalog/
  - inventory/
  - transfers/
  - pos/
  - ecommerce/
  - orders/
  - administration/

- shared/
  - components/
  - hooks/
  - services/
  - types/
  - utils/
  - constants/

- assets/

Dentro de una feature se pueden utilizar:

- pages/
- components/
- services/
- hooks/
- types/

No es obligatorio crear todas esas carpetas si están vacías o no son
necesarias.

---

# 13. RELACIÓN ENTRE FEATURES Y ÉPICAS

E1:
- auth
- users
- branches

E2:
- catalog

E3:
- inventory

E4:
- transfers

E5:
- pos

E6:
- ecommerce

E7:
- orders
- payments si posteriormente se justifica como módulo separado

E8:
- mobile

E9:
- administration
- audit
- dashboard

---

# 14. ROLES SCRUM

## Product Owner

Responsabilidades:

- definir la visión del producto;
- priorizar el Product Backlog;
- representar las necesidades del cliente;
- validar valor de negocio.

Nombre:

NO ASIGNADO FORMALMENTE EN LA DOCUMENTACIÓN ACTUAL.

No inventar un nombre.

## Scrum Master

Responsabilidades:

- facilitar Scrum;
- organizar y facilitar ceremonias;
- ayudar a resolver impedimentos;
- apoyar al equipo en la aplicación de Scrum.

Nombre:

NO ASIGNADO FORMALMENTE EN LA DOCUMENTACIÓN ACTUAL.

No inventar un nombre.

## Equipo de Desarrollo

Responsabilidades:

- diseñar;
- desarrollar;
- integrar;
- probar;
- entregar las funcionalidades comprometidas en cada Sprint.

Integrantes del proyecto:

- Andrés Alvarado
- Jesús Lozano
- Martín Rodríguez

## Stakeholders

Responsabilidades:

- entregar requerimientos;
- validar necesidades;
- proporcionar retroalimentación.

Stakeholder principal:

Farmacia Quilicura / representante de la farmacia.

Otros stakeholders funcionales:

- administradores;
- personal de farmacia;
- vendedores/cajeros;
- encargados de inventario;
- clientes.

---

# 15. PRIORIZACIÓN

Se utiliza MoSCoW.

Orden de Épicas:

1. E1 — Must
2. E2 — Must
3. E3 — Must
4. E4 — Must
5. E5 — Must
6. E6 — Must
7. E7 — Must
8. E9 — Should
9. E8 — Should

Las épicas Must representan el núcleo del sistema.

Las Should entregan valor adicional y pueden ajustar su profundidad
según avance del proyecto.

---

# 16. ÉPICAS

## E1 — Gestión de usuarios, acceso y sucursales

Controla:

- autenticación;
- usuarios internos;
- roles;
- permisos;
- asignación de sucursal;
- administración de sucursales.

## E2 — Gestión de catálogo, precios y promociones

Controla:

- productos;
- categorías;
- códigos de barra;
- precios;
- historial de precios;
- promociones;
- productos sujetos a receta.

## E3 — Gestión de inventario multisucursal

Controla:

- stock físico;
- stock reservado;
- stock disponible;
- lotes;
- vencimientos;
- FEFO;
- stock mínimo;
- movimientos.

## E4 — Transferencias, recepción y ajustes de inventario

Controla:

- solicitudes de transferencia;
- autorización;
- despacho;
- stock en tránsito;
- recepción;
- recepción de mercadería;
- ajustes.

## E5 — Punto de Venta y gestión de caja

Controla:

- búsqueda y escaneo;
- carrito POS;
- promociones;
- venta;
- medios de pago;
- comprobantes;
- apertura;
- cierre;
- anulaciones;
- devoluciones.

## E6 — Comercio electrónico y clientes

Controla:

- catálogo online;
- cuentas de cliente;
- compra como invitado;
- carrito;
- checkout;
- sucursal de retiro;
- historial de pedidos.

## E7 — Gestión de pedidos, pagos y retiro

Controla:

- creación de pedido;
- reserva;
- pagos Flow;
- transferencias automáticas;
- preparación;
- notificaciones;
- retiro QR.

## E8 — Aplicación móvil de apoyo operacional

Controla:

- conexión del móvil al POS;
- escaneo de códigos de barra;
- escaneo de QR de retiro.

Es Should.

No es el sistema principal.

## E9 — Administración, auditoría e indicadores

Controla:

- dashboard;
- indicadores;
- auditoría;
- filtros por sucursal;
- filtros por periodo.

---

# 17. REGLAS GENERALES DE INVENTARIO

Debe distinguirse siempre:

stock físico

stock reservado

stock disponible

Regla:

stock disponible = stock físico - stock reservado

Nunca permitir cantidades negativas.

Las reservas NO representan salida física inmediata.

---

# 18. LOTES Y FEFO

Los productos pueden estar asociados a:

- lote;
- fecha de vencimiento;
- sucursal.

Al seleccionar stock para una salida debe utilizarse FEFO:

First Expired, First Out.

Se prioriza el lote vendible que venza antes.

Un lote vencido no puede venderse.

Alertas:

Más de 30 días:
- sin alerta.

16 a 30 días:
- Próximo a vencer.

1 a 15 días:
- Crítico.

Fecha vencida o alcanzada:
- Vencido.

---

# 19. PROMOCIONES

Las promociones pueden ser:

- porcentuales;
- precio fijo.

Pueden aplicarse:

- directamente a producto;
- mediante categoría.

Si existen múltiples promociones válidas para el mismo producto:

NO acumularlas.

Debe aplicarse únicamente la que produzca el menor precio final para
el cliente.

---

# 20. PRODUCTOS CON RECETA

Los productos sujetos a receta:

PUEDEN:

- visualizarse online;
- mostrar precio;
- mostrar información;
- mostrar disponibilidad.

NO PUEDEN:

- agregarse al carrito online;
- comprarse mediante e-commerce.

El backend también debe validar esta regla.

No confiar solo en la interfaz.

---

# 21. TRANSFERENCIAS

Una transferencia manual sigue conceptualmente:

Solicitada

→ Reserva en origen

→ Autorizada

→ Despachada

→ En tránsito

→ Recibida

Cuando se solicita:

se reservan unidades.

NO se reduce todavía el stock físico.

Cuando se despacha:

- se descuenta stock físico del origen;
- se libera la reserva;
- pasa a stock en tránsito.

Cuando se recibe:

- se elimina condición de tránsito;
- se incorpora al inventario destino.

Si se rechaza antes del despacho:

se libera la reserva.

---

# 22. TRANSFERENCIAS AUTOMÁTICAS POR PEDIDOS

Si un cliente selecciona una sucursal de retiro que no posee todo el
stock requerido pero otra sucursal sí lo posee:

el sistema puede generar automáticamente una transferencia
relacionada con el pedido.

Esta transferencia NO requiere aprobación manual adicional.

El pedido NO puede pasar a Listo para retiro mientras el stock
requerido no haya sido recibido.

---

# 23. POS

El POS debe permitir:

- buscar productos;
- escanear código de barra;
- agregar productos;
- validar stock;
- calcular promociones;
- seleccionar medio de pago;
- finalizar venta.

Medios de pago documentados:

- efectivo;
- débito;
- crédito;
- transferencia.

No permitir finalizar venta sin caja abierta.

---

# 24. CAJA

Para abrir caja:

el cajero informa monto inicial.

El monto puede ser cero.

La sesión queda asociada a:

- usuario;
- sucursal;
- fecha/hora.

Para cerrar caja:

registrar:

- total por medio de pago;
- monto inicial;
- efectivo esperado;
- efectivo contado;
- diferencia;
- cantidad de ventas;
- ticket promedio.

---

# 25. COMPROBANTE

El comprobante interno debe incluir:

- sucursal;
- venta;
- fecha;
- cajero;
- productos;
- promociones;
- total;
- medio de pago.

Debe indicar claramente:

COMPROBANTE SIN VALIDEZ TRIBUTARIA.

No implementar facturación tributaria electrónica salvo requisito
posterior explícito.

---

# 26. E-COMMERCE

Puede comprar:

- cliente registrado;
- invitado.

Un invitado necesita como mínimo:

- nombre;
- correo electrónico.

NO es obligatorio exigir:

- contraseña;
- dirección;
- teléfono.

Una compra como invitado NO crea automáticamente una cuenta.

---

# 27. PEDIDOS

Al crear pedido:

debe reservarse el stock.

Esto reduce stock disponible.

No debe disminuir indebidamente stock físico.

La operación debe ser segura frente a concurrencia.

Nunca permitir sobreventa de las últimas unidades.

---

# 28. FLOW Y PAGOS

La pasarela online es:

Flow.

La confirmación válida debe procesarse en backend.

Cuando el pago queda confirmado:

- pedido → Pagado;
- registrar pago;
- registrar venta online una única vez;
- conservar la reserva necesaria para preparación.

La integración debe ser idempotente.

Una notificación repetida NO puede duplicar:

- pedido;
- pago;
- venta;
- inventario.

---

# 29. PAGO NO CONFIRMADO

Existe una reserva temporal durante el proceso de pago.

Si:

- el pago es rechazado;
- el pago es cancelado;
- no existe confirmación dentro de 15 minutos;

entonces:

- marcar pago como no confirmado;
- cancelar pedido pendiente;
- liberar inmediatamente reserva;
- no generar venta;
- no generar movimientos de salida.

---

# 30. PREPARACIÓN DEL PEDIDO

Solo puede marcarse:

Listo para retiro

cuando todo el stock necesario se encuentre físicamente disponible
en la sucursal seleccionada.

Si existe transferencia pendiente:

no permitir marcarlo como listo.

---

# 31. QR DE RETIRO — REGLA CRÍTICA

REGLA ACTUAL:

EL QR NO VENCE POR EL PASO DEL TIEMPO.

Mientras:

- el pedido esté Pagado;
- esté Listo para retiro;
- no haya sido retirado;

el QR continúa válido.

NO implementar:

- expiración después de 5 días;
- liberación automática por vencimiento del QR;
- regeneración obligatoria por tiempo;
- bloqueo temporal por antigüedad.

El QR deja de servir cuando:

- es inválido;
- fue alterado;
- no corresponde al pedido;
- el pedido ya fue retirado.

El retiro debe registrarse de manera atómica.

Después de retirar:

pedido → Retirado.

No permitir segundo retiro.

---

# 32. CORREOS DE RETIRO

Cuando un pedido pasa a:

Listo para retiro

enviar correo con:

- número de pedido;
- productos;
- total;
- sucursal;
- comprobante;
- código QR.

Puede enviarse posteriormente un recordatorio.

El recordatorio:

- utiliza nuevamente el mismo QR;
- no cambia estado;
- no cambia validez;
- no genera un pedido nuevo.

---

# 33. ACLARACIÓN SOBRE E8-H2

Existe una redacción heredada en E8-H2 donde se menciona:

"el token no existe, está vencido o ya fue utilizado".

Esta frase entra en conflicto con la regla final de E7-H5 y E7-H6.

Para implementación debe utilizarse la regla actual:

EL QR DE UN PEDIDO PAGADO Y LISTO PARA RETIRO NO VENCE POR EL PASO
DEL TIEMPO.

Por tanto, Codex NO debe implementar expiración temporal del QR.

Debe tratar como inválido un QR cuando:

- no exista;
- haya sido manipulado;
- no corresponda al pedido;
- el pedido ya haya sido retirado.

---

# 34. AUDITORÍA

Registrar operaciones sensibles.

Ejemplos:

- ajustes;
- transferencias;
- cambios de precio;
- anulaciones;
- devoluciones;
- operaciones administrativas relevantes.

Registrar al menos:

- usuario;
- fecha/hora;
- tipo de acción;
- referencia a operación afectada.

No permitir borrar auditoría mediante funciones administrativas
normales.

---

# 35. HISTORIAS DE USUARIO

# E1 — Gestión de usuarios, acceso y sucursales

---

## E1-H1

Rol:

Usuario interno.

Funcionalidad:

Iniciar sesión en la plataforma.

Objetivo:

Acceder de forma segura a las funciones autorizadas.

### AC1 — Credenciales válidas

Contexto:

Existe un usuario activo con credenciales registradas.

Evento:

Ingresa correo y contraseña correctos.

Resultado:

El sistema autentica al usuario y muestra las funciones
correspondientes a sus permisos.

### AC2 — Credenciales inválidas

Contexto:

El usuario ingresa datos incorrectos o su cuenta está inactiva.

Evento:

Intenta iniciar sesión.

Resultado:

El sistema rechaza el acceso y muestra un mensaje sin revelar
información sensible.

---

## E1-H2

Rol:

Administrador.

Funcionalidad:

Crear, actualizar y desactivar usuarios internos.

Objetivo:

Mantener controlados los accesos del personal.

### AC1 — Creación de usuario

Contexto:

Datos obligatorios válidos y correo no registrado.

Evento:

Administrador guarda usuario.

Resultado:

Crear cuenta y dejarla disponible según estado y rol.

### AC2 — Correo duplicado

Contexto:

Ya existe una cuenta con el correo.

Evento:

Se intenta guardar usuario nuevo.

Resultado:

Rechazar duplicidad e informar conflicto.

---

## E1-H3

Rol:

Administrador.

Funcionalidad:

Asignar roles y permisos.

Objetivo:

Restringir operaciones según responsabilidad.

### AC1 — Operación autorizada

Si posee permiso requerido:

backend permite operación y registra responsable cuando corresponda.

### AC2 — Operación no autorizada

Si no posee permiso:

backend rechaza la acción incluso si se intenta acceso directo.

---

## E1-H4

Rol:

Administrador.

Funcionalidad:

Asignar sucursal a usuario interno.

Objetivo:

Contextualizar operaciones.

### AC1 — Sucursal asignada

Las operaciones dependientes de ubicación utilizan la sucursal
asignada.

### AC2 — Cambio de sucursal

Administrador puede cambiar la sucursal sin modificar el rol.

---

## E1-H5

Rol:

Administrador.

Funcionalidad:

Crear, actualizar y desactivar sucursales.

Objetivo:

Mantener las ubicaciones operativas.

### AC1 — Sucursal válida

Crear o actualizar sucursal cuando datos obligatorios sean válidos.

### AC2 — Desactivación controlada

No desactivar mientras existan:

- cajas abiertas;
- pedidos pendientes;
- transferencias pendientes que impidan cierre.

Al desactivar:

- impedir operaciones nuevas;
- conservar histórico;
- conservar trazabilidad.

---

# E2 — Catálogo, precios y promociones

## E2-H1

Rol:

Administrador.

Funcionalidad:

Gestionar productos, categorías y códigos de barra.

Objetivo:

Catálogo único para todos los canales.

### AC1

Producto válido queda disponible para:

- inventario;
- POS;
- e-commerce;

según estado.

### AC2

Código de barra duplicado:

rechazar asociación e informar conflicto.

---

## E2-H2

Rol:

Administrador.

Funcionalidad:

Actualizar precio base.

Objetivo:

Mantener precios centralizados e historial.

### AC1

Al cambiar precio registrar:

- precio anterior;
- precio nuevo;
- fecha;
- usuario responsable.

Aplicar nuevo precio a todos los canales.

### AC2

Mostrar historial completo de cambios.

---

## E2-H3

Rol:

Administrador.

Funcionalidad:

Configurar promociones porcentuales o precio fijo.

### AC1

Una promoción válida posee:

- tipo;
- valor;
- inicio;
- término.

Aplicarla durante vigencia.

### AC2

Si varias promociones son aplicables:

compararlas y utilizar exclusivamente la que produzca mayor
descuento / menor precio final.

No acumular descuentos.

---

## E2-H4

Rol:

Administrador / Químico farmacéutico.

Funcionalidad:

Marcar productos sujetos a receta.

### AC1

Mostrar producto online pero impedir agregar al carrito.

### AC2

Backend debe rechazar intento de compra directo aunque se manipule
frontend.

---

# E3 — Inventario multisucursal

## E3-H1

Rol:

Encargado de inventario.

Funcionalidad:

Consultar stock por sucursal.

### AC1

Mostrar:

- físico;
- reservado;
- disponible.

Disponible = físico - reservado.

### AC2

Nunca mostrar o permitir stock negativo.

---

## E3-H2

Rol:

Encargado de inventario.

Funcionalidad:

Gestionar lotes y vencimientos.

### AC1

Registrar asociación:

- sucursal;
- producto;
- lote;
- vencimiento;
- unidades.

### AC2

Utilizar FEFO para salida.

---

## E3-H3

Rol:

Administrador.

Funcionalidad:

Configurar stock mínimo por producto y sucursal.

### AC1

Si disponible <= mínimo:

mostrar alerta.

### AC2

Si disponible > mínimo:

no mostrar alerta.

---

## E3-H4

Rol:

Administrador.

Funcionalidad:

Consultar movimientos y vencimientos.

### AC1

Movimiento debe registrar:

- tipo;
- cantidad;
- sucursal;
- producto/lote;
- usuario;
- fecha.

### AC2

Clasificación de vencimiento:

16-30 días:
Próximo a vencer.

1-15:
Crítico.

Vencido:
no vendible.

---

# E4 — Transferencias, recepción y ajustes

## E4-H1

Rol:

Encargado de inventario.

Funcionalidad:

Solicitar transferencia.

### AC1

Con stock suficiente:

crear transferencia Solicitada y reservar unidades.

### AC2

Con stock insuficiente:

rechazar cantidad y evitar negativos.

### AC3

Al despacho:

- descontar físico origen;
- liberar reserva;
- registrar stock en tránsito.

---

## E4-H2

Rol:

Administrador.

Funcionalidad:

Aprobar o rechazar transferencia manual.

### AC1

Aprobación habilita despacho.

### AC2

Usuario sin permiso no puede aprobar.

### AC3

Rechazo:

- estado Rechazada;
- liberar reservas;
- mantener trazabilidad.

---

## E4-H3

Rol:

Encargado de inventario de sucursal destino.

Funcionalidad:

Confirmar recepción.

### AC1

Stock en tránsito no cuenta como disponible en destino.

### AC2

Al recibir:

- incorporar cantidades;
- eliminar tránsito;
- cerrar transferencia;
- registrar movimiento.

---

## E4-H4

Rol:

Encargado de inventario.

Funcionalidad:

Recepción de mercadería.

### AC1

Requiere:

- documento;
- sucursal;
- productos;
- cantidades;
- lotes;
- vencimientos.

### AC2

Con datos incompletos:

no afectar inventario.

---

## E4-H5

Rol:

Administrador / Encargado de inventario.

Funcionalidad:

Ajuste manual con motivo.

### AC1

Registrar:

- producto;
- sucursal/lote;
- cantidad;
- motivo;
- valor anterior;
- valor nuevo;
- usuario;
- fecha.

### AC2

Rechazar si:

- produce stock negativo;
- no existe motivo.

---

# E5 — POS y caja

## E5-H1

Rol:

Vendedor / Cajero.

Funcionalidad:

Buscar o escanear productos.

### AC1

Producto vendible con stock:

permitir agregar.

### AC2

Sin disponibilidad:

informar y no permitir exceder stock.

---

## E5-H2

Rol:

Vendedor / Cajero.

Funcionalidad:

Aplicar promociones automáticamente.

### AC1

Aplicar promoción vigente.

### AC2

Sin promoción:

usar precio base.

No permitir descuentos manuales del cajero.

### AC3

Con múltiples promociones:

utilizar la que produzca menor precio final.

---

## E5-H3

Rol:

Vendedor / Cajero.

Funcionalidad:

Finalizar venta.

### AC1

Con stock y caja abierta:

registrar venta y medio de pago y descontar inventario una sola vez.

### AC2

Con caja cerrada:

impedir finalización.

---

## E5-H4

Rol:

Vendedor / Cajero.

Funcionalidad:

Comprobante interno.

### AC1

Generar comprobante con datos de venta.

### AC2

Indicar:

SIN VALIDEZ TRIBUTARIA.

---

## E5-H5

Rol:

Vendedor / Cajero.

Funcionalidad:

Abrir/cerrar caja.

### AC1

Apertura:

registrar monto inicial, incluso cero.

### AC2

Cierre:

registrar indicadores y diferencias.

---

## E5-H6

Rol:

Administrador.

Funcionalidad:

Anulaciones/devoluciones.

### AC1

Mantener venta original y registrar reversa relacionada.

Registrar:

- usuario;
- fecha;
- motivo.

### AC2

No permitir devolver más unidades que las compradas.

Reintegrar stock solo cuando condiciones lo permitan.

---

# E6 — E-commerce y clientes

## E6-H1

Rol:

Visitante / Cliente.

Funcionalidad:

Consultar catálogo y disponibilidad por sucursal.

### AC1

Mostrar:

- nombre;
- precio;
- información;
- disponibilidad.

### AC2

Producto sujeto a receta:

visible pero compra presencial.

---

## E6-H2

Rol:

Cliente.

Funcionalidad:

Registrarse e iniciar sesión.

### AC1

Registro requiere:

- nombre;
- correo;
- contraseña.

### AC2

Credenciales inválidas:

rechazar sin exponer información sensible.

---

## E6-H3

Rol:

Invitado.

Funcionalidad:

Comprar sin cuenta.

### AC1

Requerir como mínimo:

- nombre;
- correo.

### AC2

No crear cuenta automática ni historial de usuario.

---

## E6-H4

Rol:

Cliente / Invitado.

Funcionalidad:

Gestionar carrito y sucursal de retiro.

### AC1

Recalcular y validar disponibilidad al cambiar cantidades o avanzar.

### AC2

Pedido queda asociado a sucursal seleccionada aunque necesite
transferencia.

---

## E6-H5

Rol:

Cliente registrado.

Funcionalidad:

Historial de pedidos online.

### AC1

Mostrar exclusivamente sus pedidos web.

### AC2

Ventas POS no se agregan automáticamente al historial web.

---

# E7 — Pedidos, pagos y retiro

## E7-H1

Rol:

Cliente / Invitado.

Funcionalidad:

Crear pedido con reserva.

### AC1

Reservar stock al crear pedido.

### AC2

Proteger concurrencia transaccionalmente y evitar sobreventa.

---

## E7-H2

Rol:

Cliente / Invitado.

Funcionalidad:

Pagar mediante Flow.

### AC1

Pago confirmado:

- pedido Pagado;
- registrar pago;
- registrar venta una sola vez;
- conservar reserva.

### AC2

Notificación repetida:

idempotencia completa.

### AC3

Pago rechazado/cancelado/no confirmado en 15 minutos:

- cancelar pendiente;
- liberar reserva;
- no generar venta;
- no generar salida.

---

## E7-H3

Rol:

Encargado de pedidos.

Funcionalidad:

Transferencia automática asociada a pedido.

### AC1

Generarla cuando otra sucursal posee stock necesario.

Sin autorización manual adicional.

### AC2

No marcar listo antes de recibir stock.

---

## E7-H4

Rol:

Personal de farmacia.

Funcionalidad:

Preparar pedido.

### AC1

Con stock completo:

permitir Listo para retiro.

### AC2

Con transferencia pendiente:

impedir estado Listo.

---

## E7-H5

Rol:

Cliente / Invitado.

Funcionalidad:

Notificaciones de retiro.

### AC1

Al Listo para retiro:

enviar correo con QR e información.

QR sigue válido mientras:

- Pagado;
- Listo;
- no retirado.

### AC2

Recordatorio:

reenviar mismo QR sin alterar estado ni validez.

---

## E7-H6

Rol:

Personal de farmacia.

Funcionalidad:

Validar QR y registrar retiro.

### AC1

QR válido:

registrar retiro atómicamente.

Pedido → Retirado.

### AC2

Código inválido o pedido retirado:

rechazar.

REGLA:

QR de pedido Pagado + Listo para retiro NO vence por paso del tiempo.

---

# E8 — Aplicación móvil

## E8-H1

Rol:

Vendedor / Cajero.

Funcionalidad:

Vincular móvil al POS y escanear código de barra.

### AC1

POS activo + código de vinculación válido:

asociar dispositivo temporalmente.

### AC2

Escaneo válido:

enviar producto a sesión POS y agregarlo al carrito.

---

## E8-H2

Rol:

Personal de farmacia.

Funcionalidad:

Escanear QR de retiro.

### AC1

QR reconocido:

consultar backend y mostrar información para entrega.

### AC2

QR no válido:

informar que no puede entregarse y no modificar estado.

Aplicar la regla vigente:

NO considerar vencimiento temporal.

---

# E9 — Administración, auditoría e indicadores

## E9-H1

Rol:

Administrador / Socio.

Funcionalidad:

Dashboard operacional.

### AC1

Mostrar como mínimo:

- ventas;
- medios de pago;
- ticket promedio;
- stock bajo;
- próximos a vencer.

### AC2

Consolidar datos de múltiples sucursales.

---

## E9-H2

Rol:

Administrador / Socio.

Funcionalidad:

Consultar auditoría.

### AC1

Mostrar:

- usuario;
- fecha/hora;
- acción;
- referencia.

### AC2

No permitir eliminación mediante administración normal.

---

## E9-H3

Rol:

Administrador / Socio.

Funcionalidad:

Filtrar indicadores y auditoría.

### AC1

Filtro sucursal.

### AC2

Filtro periodo.

Recalcular resultados para rango seleccionado.

---

# 36. REGLAS DE IMPLEMENTACIÓN PARA CODEX

Antes de modificar código:

1. Leer AGENTS.md.
2. Identificar HU relacionada.
3. Identificar criterios de aceptación.
4. Revisar implementación existente.
5. Explicar impacto si el cambio es importante.
6. Implementar.
7. Ejecutar lint.
8. Ejecutar pruebas disponibles.
9. Ejecutar build.
10. Informar resultado.

---

# 37. NO HACER

Codex NO debe:

- inventar reglas;
- cambiar requisitos silenciosamente;
- cambiar stack sin autorización;
- convertir monolito modular en microservicios;
- introducir una segunda base de datos sin necesidad;
- duplicar lógica;
- implementar compras online de productos con receta;
- permitir stock negativo;
- vender lotes vencidos;
- acumular promociones si la regla indica elegir la mejor;
- permitir venta sin caja abierta;
- duplicar pagos Flow;
- duplicar ventas por webhook;
- permitir retirar un pedido dos veces;
- expirar QR por tiempo;
- eliminar auditoría;
- agregar funcionalidades que no estén solicitadas.

---

# 38. CONVENCIONES DE FRONTEND

Usar:

- TypeScript;
- componentes reutilizables;
- separación por features;
- nombres claros.

Evitar:

- `any` innecesario;
- componentes gigantes;
- lógica de negocio incrustada en componentes visuales;
- llamadas API duplicadas;
- estilos duplicados innecesariamente.

Las pantallas no tienen que corresponder 1:1 con HU.

Varias HU pueden compartir pantalla.

Ejemplo:

E5-H1
E5-H2
E5-H3

pueden formar parte de una misma pantalla POS.

---

# 39. CONVENCIONES BACKEND

Backend:

FastAPI.

Organización:

monolito modular.

Separar dominios lógicos como:

- auth;
- users;
- branches;
- catalog;
- inventory;
- transfers;
- sales;
- ecommerce;
- orders;
- payments;
- audit;
- dashboard.

La lógica crítica debe vivir en backend.

Especialmente:

- permisos;
- receta;
- stock;
- promociones;
- concurrencia;
- pagos;
- QR;
- auditoría.

No confiar únicamente en frontend.

---

# 40. BASE DE DATOS

PostgreSQL.

El modelo debe soportar de manera consistente:

- usuarios;
- roles;
- permisos;
- sucursales;
- productos;
- categorías;
- precios;
- historial de precios;
- promociones;
- inventario;
- lotes;
- movimientos;
- transferencias;
- reservas;
- ventas;
- detalles de venta;
- cajas;
- pedidos;
- detalles de pedido;
- pagos;
- auditoría.

Las operaciones críticas de inventario y pagos deben utilizar
transacciones cuando corresponda.

---

# 41. APLICACIÓN MÓVIL

Tecnología documentada:

Flutter.

La app es complementaria.

No duplicar todo el sistema administrativo en la app.

Funciones actuales:

E8-H1:
scanner de código de barra vinculado al POS.

E8-H2:
scanner de QR de retiro.

---

# 42. SEGURIDAD

Aplicar:

- autenticación;
- autorización;
- roles;
- permisos;
- validación backend;
- trazabilidad.

Nunca revelar información sensible mediante mensajes de error.

Las operaciones protegidas deben validarse en backend incluso si la
interfaz las oculta.

---

# 43. TRAZABILIDAD

Siempre que sea posible asociar código con HU.

Ejemplo:

E5-H3
→ PosPage
→ servicio de ventas
→ endpoint de venta
→ actualización inventario
→ prueba E5-H3

Comentarios con IDs de HU pueden utilizarse cuando aporten valor,
pero no llenar todo el código de comentarios redundantes.

---

# 44. ESTADO DOCUMENTAL

Las Historias de Usuario son la definición actual del producto.

Sus IDs deben mantenerse estables.

No renombrar:

E1-H1...
E9-H3

sin autorización.

El Product Backlog y Sprint Backlog futuros deben conservar esos IDs.

---

# 45. CAMPOS PENDIENTES

No inventar información documental faltante.

Actualmente pueden existir campos pendientes como:

- nombre específico del representante de farmacia;
- asignación nominal Product Owner;
- asignación nominal Scrum Master.

Si se requieren:

preguntar.

---

# 46. OBJETIVO FINAL DE CODEX

Ayudar a desarrollar SIGFQ respetando:

VISIÓN
↓
ÉPICAS
↓
HISTORIAS DE USUARIO
↓
CRITERIOS DE ACEPTACIÓN
↓
REGLAS DE NEGOCIO
↓
ARQUITECTURA
↓
CÓDIGO
↓
PRUEBAS

El software debe mantenerse alineado con la documentación del
proyecto y no al revés.