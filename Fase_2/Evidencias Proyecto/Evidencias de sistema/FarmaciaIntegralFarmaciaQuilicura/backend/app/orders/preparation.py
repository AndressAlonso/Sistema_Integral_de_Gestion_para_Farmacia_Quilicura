"""E7-H4: preparación sin consumir las reservas comprometidas del pedido."""
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.models import EventoAuditoria, Sucursal, Transferencia
from app.orders.models import PedidoOnline
from app.orders.service import summary
from app.orders.transfers import lock_order, reservation_rows
from app.transfers.repository import TransferRepository

STATES = ("PENDIENTE_PAGO", "PAGADO", "EN_PREPARACION", "LISTO_PARA_RETIRO", "CANCELADO")
PAID_STATES = ("PAGADO", "EN_PREPARACION", "LISTO_PARA_RETIRO")


class PreparationService:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def authorize(actor, branch_id=None, change=False):
        if (not actor.is_active or "pedidos.consultar" not in actor.permissions
                or (change and "pedidos.preparar" not in actor.permissions)):
            raise HTTPException(403, "No tienes permiso para gestionar estos pedidos.")
        if branch_id is not None and "ADMINISTRADOR" not in actor.roles and actor.branch_id != branch_id:
            raise HTTPException(403, "Solo puedes gestionar pedidos de tu sucursal de retiro.")

    def list(self, actor, state, branch_id, page, limit, states=None, sort="newest", branch_ids=None):
        self.authorize(actor, branch_id)
        if branch_id and branch_ids:
            raise HTTPException(422, "Utiliza un filtro de sucursal único o múltiple, no ambos.")
        for selected_branch in branch_ids or []:
            self.authorize(actor, selected_branch)
        if state and states:
            raise HTTPException(422, "Utiliza un filtro de estado único o múltiple, no ambos.")
        selected_states = states if states is not None else ([state] if state else [])
        if any(value not in STATES for value in selected_states):
            raise HTTPException(422, "Selecciona un estado de pedido válido.")
        with self.factory() as db:
            query = select(PedidoOnline)
            selected = branch_id if "ADMINISTRADOR" in actor.roles else actor.branch_id
            if selected:
                query = query.where(PedidoOnline.sucursal_id == selected)
            if branch_ids:
                query = query.where(PedidoOnline.sucursal_id.in_(branch_ids))
            if selected_states:
                query = query.where(PedidoOnline.estado.in_(selected_states))
            total = db.scalar(select(func.count()).select_from(query.subquery()))
            ordering = []
            if sort in ("state_asc", "state_desc"):
                rank = case({value: index for index, value in enumerate(STATES)}, value=PedidoOnline.estado)
                ordering.append(rank.asc() if sort == "state_asc" else rank.desc())
            elif sort in ("branch_asc", "branch_desc"):
                query = query.join(Sucursal, Sucursal.id == PedidoOnline.sucursal_id)
                name = func.lower(Sucursal.nombre)
                ordering.append(name.asc() if sort == "branch_asc" else name.desc())
            rows = db.scalars(query.order_by(*ordering, PedidoOnline.creado_en.desc(), PedidoOnline.id)
                              .offset((page - 1) * limit).limit(limit))
            branches = select(Sucursal).order_by(Sucursal.nombre)
            if "ADMINISTRADOR" not in actor.roles:
                branches = branches.where(Sucursal.id == actor.branch_id)
            return {"orders": [summary(row) for row in rows], "total": total,
                    "page": page, "limit": limit,
                    "branches": [{"id": b.id, "name": b.nombre} for b in db.scalars(branches)]}

    @staticmethod
    def transfers(db, order):
        return list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == order.id)
                               .order_by(Transferencia.solicitada_en, Transferencia.id)))

    @staticmethod
    def ready_problem(db, order, transfers, lock=False):
        if any(t.estado != "RECIBIDA" for t in transfers):
            return "Falta recibir una transferencia del pedido."
        rows = reservation_rows(db, order.id)
        quantities = defaultdict(int)
        today = datetime.now(timezone.utc).date()
        for reserve, lot, inventory in rows:
            if inventory.sucursal_id != order.sucursal_id:
                return "Falta stock reservado en la sucursal de retiro."
            if lock:
                product = TransferRepository.product(db, inventory.producto_id)
                inventory = TransferRepository.inventory(db, inventory.producto_id, inventory.sucursal_id)
                db.refresh(lot)
            else:
                product = inventory.producto
            reserved = TransferRepository.reserved_lots(db, inventory.id)
            if (not product.activo or not lot.activo or lot.fecha_vencimiento <= today
                    or lot.cantidad < reserved.get(lot.id, 0)
                    or inventory.stock_fisico < inventory.stock_reservado
                    or inventory.stock_reservado < sum(reserved.values())):
                return "Revisa las reservas y los lotes: el stock del pedido no está completo o no es apto."
            quantities[reserve.detalle_id] += reserve.cantidad
        if dict(quantities) != {d.id: d.cantidad for d in order.detalles}:
            return "Las reservas no cubren todos los productos del pedido."
        return None

    def detail(self, db, actor, order):
        self.authorize(actor, order.sucursal_id)
        transfers = self.transfers(db, order)
        problem = self.ready_problem(db, order, transfers) if order.estado in PAID_STATES else None
        actions = []
        if "pedidos.preparar" in actor.permissions and order.sucursal.activa:
            if order.estado == "PAGADO":
                actions.append("preparation")
            elif order.estado == "EN_PREPARACION" and not problem:
                actions.append("ready")
        events = db.scalars(select(EventoAuditoria).where(
            EventoAuditoria.referencia_historica == f"Pedido {order.id}",
            EventoAuditoria.accion.in_(("E7-H4_ESTADO", "E7-H3_PAGO_SIMULADO")))
            .order_by(EventoAuditoria.secuencia))
        return summary(order) | {
            "customer": {"name": order.nombre, "email": order.correo},
            "actions": actions, "ready_blocked_reason": problem,
            "transfers": [{"id": t.id, "status": t.estado,
                           "origin": t.origen.nombre, "destination": t.destino.nombre} for t in transfers],
            "history": [{"at": e.ocurrido_en, "actor": e.datos_cambio.get("usuario_nombre", "Sistema"),
                         "previous": e.datos_cambio.get("anterior"),
                         "status": e.datos_cambio.get("nuevo", e.datos_cambio.get("resultado"))}
                        for e in events],
        }

    def get(self, actor, order_id):
        self.authorize(actor)
        with self.factory() as db:
            order = db.get(PedidoOnline, order_id)
            if order is None:
                raise HTTPException(404, "No se encontró el pedido.")
            return self.detail(db, actor, order)

    def change(self, actor, order_id, action, expected_state):
        self.authorize(actor, change=True)
        target, source = ("EN_PREPARACION", "PAGADO") if action == "preparation" else ("LISTO_PARA_RETIRO", "EN_PREPARACION")
        with self.factory.begin() as db:
            order = lock_order(db, order_id)
            self.authorize(actor, order.sucursal_id, change=True)
            # Un reintento de la misma transición no vuelve a escribir historial.
            if order.estado == target and expected_state == source:
                return self.detail(db, actor, order)
            if order.estado != source or expected_state != source:
                raise HTTPException(409, "El estado del pedido cambió o no permite esta acción. Actualiza el detalle.")
            branches = TransferRepository.branches(db, [order.sucursal_id])
            if not branches or not branches[0].activa:
                raise HTTPException(409, "La sucursal de retiro está inactiva.")
            if action == "ready":
                problem = self.ready_problem(db, order, self.transfers(db, order), lock=True)
                if problem:
                    raise HTTPException(409, problem)
            order.estado = target
            db.add(EventoAuditoria(origen_actor="USUARIO_INTERNO", accion="E7-H4_ESTADO",
                referencia_historica=f"Pedido {order.id}", usuario_id=actor.id, sucursal_id=order.sucursal_id,
                datos_cambio={"pedido_id": str(order.id), "anterior": source, "nuevo": target,
                              "usuario_nombre": actor.name}))
            db.flush()
            return self.detail(db, actor, order)
